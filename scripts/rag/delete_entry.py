"""Delete a RAG entry and all generated artifacts with a dry-run plan."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from bib_parser import parse_bibtex_file, render_bibtex
from common import append_log
from darw_schema import chunk_manifest_path, parsed_manifest_path, parsed_markdown_path
from metadata_normalizer import normalize_arxiv, normalize_doi, normalize_entry, normalize_title
from update_index import collect_edge_tags, ensure_category_page, rebuild_auto_block


@dataclass
class DeleteTarget:
    entry: dict[str, str]
    match_reason: str

    @property
    def key(self) -> str:
        return self.entry.get("ID", "")

    @property
    def doc_id(self) -> str:
        normalized = normalize_entry(self.entry)
        arxiv = str(normalized["arxiv"])
        doi = str(normalized["doi"])
        if arxiv:
            return f"arxiv:{arxiv}"
        if doi:
            return doi
        return f"pdf:{self.key}"


@dataclass
class DeletePlan:
    rag_dir: Path
    target: DeleteTarget | None = None
    ambiguous: list[DeleteTarget] = field(default_factory=list)
    files: dict[str, Path] = field(default_factory=dict)
    markdown_references: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.target.key if self.target else ""


def _manifest_path(rag_dir: Path) -> Path:
    return rag_dir / "references.bib"


def _load_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = _manifest_path(rag_dir)
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _match_entries(
    entries: list[dict[str, str]],
    *,
    key: str = "",
    doi: str = "",
    arxiv: str = "",
    title: str = "",
) -> list[DeleteTarget]:
    targets: list[DeleteTarget] = []
    doi = normalize_doi(doi)
    arxiv = normalize_arxiv(arxiv)
    title_norm = normalize_title(title)
    for entry in entries:
        normalized = normalize_entry(entry)
        if key and entry.get("ID", "").lower() == key.lower():
            targets.append(DeleteTarget(entry, "key"))
        elif doi and str(normalized["doi"]) == doi:
            targets.append(DeleteTarget(entry, "doi"))
        elif arxiv and str(normalized["arxiv"]) == arxiv:
            targets.append(DeleteTarget(entry, "arxiv"))
        elif title_norm:
            entry_title = str(normalized["title_norm"])
            if title_norm == entry_title:
                targets.append(DeleteTarget(entry, "title"))
            elif title_norm in entry_title or entry_title in title_norm:
                targets.append(DeleteTarget(entry, "title-substring"))
    return targets


def _existing_files(rag_dir: Path, target: DeleteTarget) -> dict[str, Path]:
    key = target.key
    doc_id = target.doc_id
    candidates = {
        "source_page": rag_dir / "summary" / "sources" / f"{key}.md",
        "pdf": rag_dir / "reference" / "pdfs" / f"{key}.pdf",
        "parsed_markdown": parsed_markdown_path(rag_dir, doc_id),
        "parsed_manifest": parsed_manifest_path(rag_dir, doc_id),
        "chunk_jsonl": chunk_manifest_path(rag_dir, doc_id),
    }
    arxiv = normalize_arxiv(target.entry.get("eprint") or target.entry.get("arxiv"))
    if arxiv:
        candidates["arxiv_source"] = rag_dir / "reference" / "arxiv_sources" / f"arxiv_{arxiv}.md"
        candidates["arxiv_manifest"] = rag_dir / "reference" / "arxiv_sources" / f"arxiv_{arxiv}.manifest.json"
    return {label: path for label, path in candidates.items() if path.exists()}


def _find_markdown_references(rag_dir: Path, key: str, doc_id: str) -> list[Path]:
    needles = [
        f"[[../sources/{key}]]",
        f"summary/sources/{key}.md",
        f"sources/{key}.md",
        f"../sources/{key}",
        f"[@{key}]",
        key,
        doc_id,
    ]
    refs: list[Path] = []
    source_path = rag_dir / "summary" / "sources" / f"{key}.md"
    for page in rag_dir.rglob("*.md"):
        if page == source_path:
            continue
        text = page.read_text(encoding="utf-8")
        if any(needle and needle in text for needle in needles):
            refs.append(page)
    return refs


def build_delete_plan(
    rag_dir: Path,
    *,
    key: str = "",
    doi: str = "",
    arxiv: str = "",
    title: str = "",
) -> DeletePlan:
    selectors = [bool(key), bool(doi), bool(arxiv), bool(title)]
    if sum(selectors) != 1:
        return DeletePlan(rag_dir=rag_dir, errors=["provide exactly one of --key, --doi, --arxiv, or --title"])
    entries = _load_entries(rag_dir)
    matches = _match_entries(entries, key=key, doi=doi, arxiv=arxiv, title=title)
    if not matches:
        return DeletePlan(rag_dir=rag_dir, errors=["no matching entry"])
    if len(matches) > 1:
        return DeletePlan(rag_dir=rag_dir, ambiguous=matches, errors=["ambiguous selector matched multiple entries"])
    target = matches[0]
    return DeletePlan(
        rag_dir=rag_dir,
        target=target,
        files=_existing_files(rag_dir, target),
        markdown_references=_find_markdown_references(rag_dir, target.key, target.doc_id),
    )


def _write_manifest_without(plan: DeletePlan) -> bool:
    manifest = _manifest_path(plan.rag_dir)
    if not manifest.exists() or not plan.target:
        return False
    entries = [entry for entry in parse_bibtex_file(manifest) if entry.get("ID") != plan.key]
    manifest.write_text("\n\n".join(render_bibtex(entry) for entry in entries).strip() + ("\n" if entries else ""), encoding="utf-8")
    return True


AUTO_BEGIN = "<!-- AUTO:BEGIN -->"
AUTO_END = "<!-- AUTO:END -->"


def _scrub_auto_references(path: Path, key: str) -> bool:
    text = path.read_text(encoding="utf-8")
    begin = text.find(AUTO_BEGIN)
    end = text.find(AUTO_END)
    if begin == -1 or end == -1 or end < begin:
        return False
    block = text[begin : end + len(AUTO_END)]
    lines = [line for line in block.splitlines() if key not in line]
    new_text = text[:begin] + "\n".join(lines) + text[end + len(AUTO_END) :]
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def _refresh_indexes(rag_dir: Path) -> int:
    tag_map = collect_edge_tags(rag_dir)
    updated = 0
    for category, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_category_page(rag_dir, category, tag)
            if rebuild_auto_block(page, category, tag, source_keys):
                updated += 1
    return updated


def apply_delete_plan(plan: DeletePlan) -> dict[str, int]:
    if not plan.target:
        raise ValueError("delete plan has no target")
    removed_files = 0
    manifest_changed = 1 if _write_manifest_without(plan) else 0
    for path in plan.files.values():
        if path.exists():
            path.unlink()
            removed_files += 1
    scrubbed_refs = 0
    for page in plan.markdown_references:
        if page.exists() and _scrub_auto_references(page, plan.key):
            scrubbed_refs += 1
    updated_indexes = _refresh_indexes(plan.rag_dir)
    append_log(
        plan.rag_dir,
        "delete-entry",
        f"key={plan.key}",
        f"manifest_changed={manifest_changed} removed_files={removed_files} scrubbed_refs={scrubbed_refs} updated_indexes={updated_indexes}",
    )
    return {
        "manifest_changed": manifest_changed,
        "removed_files": removed_files,
        "scrubbed_refs": scrubbed_refs,
        "updated_indexes": updated_indexes,
    }


def plan_as_dict(plan: DeletePlan) -> dict[str, object]:
    return {
        "rag_dir": str(plan.rag_dir),
        "target": {
            "key": plan.target.key,
            "doc_id": plan.target.doc_id,
            "match_reason": plan.target.match_reason,
            "title": plan.target.entry.get("title", ""),
        }
        if plan.target
        else None,
        "ambiguous": [
            {"key": target.key, "title": target.entry.get("title", ""), "match_reason": target.match_reason}
            for target in plan.ambiguous
        ],
        "files": {label: str(path) for label, path in plan.files.items()},
        "markdown_references": [str(path) for path in plan.markdown_references],
        "errors": plan.errors,
    }


def print_plan(plan: DeletePlan, as_json: bool = False) -> None:
    data = plan_as_dict(plan)
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    if plan.target:
        print(f"delete plan for {plan.key} doc_id={plan.target.doc_id} match={plan.target.match_reason}")
        print(f"- BibTeX entry: yes")
        for label, path in sorted(plan.files.items()):
            print(f"- {label}: {path}")
        print(f"- markdown references: {len(plan.markdown_references)}")
    if plan.ambiguous:
        print("ambiguous matches:")
        for target in plan.ambiguous:
            print(f"- {target.key}: {target.entry.get('title', '')}")
    for error in plan.errors:
        print(f"error: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delete a RAG entry and generated artifacts")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="")
    parser.add_argument("--doi", default="")
    parser.add_argument("--arxiv", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.dry_run and args.yes:
        print("choose only one of --dry-run or --yes")
        return 1
    rag_dir = Path(args.rag_dir).resolve()
    plan = build_delete_plan(rag_dir, key=args.key, doi=args.doi, arxiv=args.arxiv, title=args.title)
    print_plan(plan, as_json=args.json)
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    result = apply_delete_plan(plan)
    print(
        f"deleted: manifest_changed={result['manifest_changed']} removed_files={result['removed_files']} "
        f"scrubbed_refs={result['scrubbed_refs']} updated_indexes={result['updated_indexes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
