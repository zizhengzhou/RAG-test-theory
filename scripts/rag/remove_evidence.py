"""Remove an entry and all its DARW evidence artifacts, plus clean up source-page links."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from darw_schema import (
    chunk_manifest_path,
    is_allowed_route,
    parsed_manifest_path,
    parsed_markdown_path,
    safe_doc_id,
)


def _load_entries(rag_dir: Path) -> list[dict]:
    from bib_parser import parse_bibtex_file

    bib_path = rag_dir / "references.bib"
    if not bib_path.exists():
        return []
    return parse_bibtex_file(bib_path)


def _find_entry(entries: list[dict], key: str) -> dict | None:
    for e in entries:
        if e.get("ID") == key:
            return e
    return None


def find_evidence_files(rag_dir: Path, doc_id: str, citation_key: str) -> dict[str, Path | None]:
    return {
        "parsed_md": parsed_markdown_path(rag_dir, doc_id),
        "parsed_manifest": parsed_manifest_path(rag_dir, doc_id),
        "chunk_manifest": chunk_manifest_path(rag_dir, doc_id),
        "source_page": rag_dir / "summary" / "sources" / f"{citation_key}.md",
        "pdf": rag_dir / "reference" / "pdfs" / f"{citation_key}.pdf",
    }


def _clean_source_page_links(source_path: Path, *, dry_run: bool = False) -> list[str]:
    """Remove stale evidence references from source page frontmatter. Returns list of cleaned fields."""
    if not source_path.exists():
        return []

    text = source_path.read_text(encoding="utf-8")
    cleaned: list[str] = []

    # Strip out evidence-linked fields that are now stale
    fields_to_blank = [
        "source.primary_evidence",
        "source.original_pdf",
        "source.source_sha256",
        "source.parser",
        "source.parser_version",
        "source.parsed_at",
        "chunk_manifest",
        "quality.needs_human_review",
        "quality.metadata_conflicts",
    ]

    for field in fields_to_blank:
        key = field.split(".")[-1]
        pattern = re.compile(rf"^(\s*){key}:\s*.+$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(rf"\1{key}: ", text)
            cleaned.append(field)

    if cleaned and not dry_run:
        source_path.write_text(text, encoding="utf-8")
    return cleaned


def plan_removal(rag_dir: Path, key: str) -> dict:
    entries = _load_entries(rag_dir)
    entry = _find_entry(entries, key)

    doc_id = f"pdf:{key}"
    if entry:
        eprint = entry.get("eprint", "")
        if eprint:
            doc_id = safe_doc_id(f"arxiv:{eprint}")
        elif entry.get("doi"):
            doc_id = safe_doc_id(entry["doi"])
        else:
            doc_id = safe_doc_id(f"pdf:{key}")

    files = find_evidence_files(rag_dir, doc_id, key)
    existing = {k: v for k, v in files.items() if v and v.exists()}

    return {
        "key": key,
        "doc_id": doc_id,
        "entry_found": entry is not None,
        "files": existing,
        "all_files": files,
    }


def remove_evidence(rag_dir: Path, key: str, *, dry_run: bool = False) -> dict:
    plan = plan_removal(rag_dir, key)
    existing = plan["files"]
    log_lines: list[str] = []

    for label, path in existing.items():
        if label == "source_page":
            cleaned = _clean_source_page_links(path, dry_run=dry_run)
            action = "dry-run: would clean" if dry_run else "cleaned"
            if cleaned:
                log_lines.append(f"{action} source_page links: {', '.join(cleaned)}")
        else:
            action = "dry-run: would remove" if dry_run else "removed"
            log_lines.append(f"{action} {label}: {path.relative_to(rag_dir).as_posix()}")
            if not dry_run:
                path.unlink()

    return {"plan": plan, "log": log_lines}


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove an entry and its DARW evidence artifacts")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", required=True, help="citation key to remove")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="skip confirmation prompt")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    plan = plan_removal(rag_dir, args.key)

    if not plan["files"]:
        print(f"No evidence files found for {args.key}")
        if not plan["entry_found"]:
            print("Citation key not found in references.bib either.")
        return 1

    print(f"Remove plan for {args.key} (doc_id={plan['doc_id']}):")
    for label, path in sorted(plan["files"].items()):
        print(f"  {label}: {path.relative_to(rag_dir).as_posix()}")

    if args.dry_run:
        result = remove_evidence(rag_dir, args.key, dry_run=True)
        for line in result["log"]:
            print(line)
        print("[dry-run] no files modified")
        return 0

    if not args.yes:
        print("\nRun with --yes to confirm removal, or --dry-run to preview first.")
        return 2

    result = remove_evidence(rag_dir, args.key, dry_run=False)
    for line in result["log"]:
        print(line)
    print(f"Removed evidence for {args.key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
