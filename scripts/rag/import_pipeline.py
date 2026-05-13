"""Unified import pipeline for BibTeX, Zotero ZIP, and provider search."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from bib_parser import parse_bibtex, parse_bibtex_file, render_bibtex
from bib_update import apply_update_plan, build_update_plan, plan_entry_update
from common import append_log, ensure_rag_dirs
from darw_schema import chunk_manifest_path, parsed_manifest_path, parsed_markdown_path
from dedup import entry_dedup_key
from external_search import SearchResult, fetch_inspire_bibtex, search_inspire
from metadata_normalizer import normalize_entry
from pdf_downloader import download_arxiv_pdf
from pdf_validator import is_pdf
from rdf_parser import parse_rdf
from source_page_builder import body_skeleton, default_frontmatter, format_frontmatter
from sync_pdf import _match_by_slug, _resolve_file_paths
from update_index import collect_edge_tags, ensure_category_page, rebuild_auto_block
from zip_importer import _resolve_pdf_path, _sanitize_key, _unique_key


@dataclass
class ImportCandidate:
    entry: dict[str, str]
    source: str
    duplicate_of: str = ""
    duplicate_match: str = ""
    pdf_source: Path | None = None
    zip_path: Path | None = None
    zip_pdf_member: str = ""
    pdf_url: str = ""
    record_id: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.entry.get("ID", "unknown")

    @property
    def effective_key(self) -> str:
        return self.duplicate_of or self.key

    @property
    def arxiv(self) -> str:
        normalized = normalize_entry(self.entry)
        return str(normalized.get("arxiv") or "")

    @property
    def doi(self) -> str:
        normalized = normalize_entry(self.entry)
        return str(normalized.get("doi") or "")

    @property
    def doc_id(self) -> str:
        if self.arxiv:
            return f"arxiv:{self.arxiv}"
        return self.doi or self.effective_key

    @property
    def evidence_route(self) -> str:
        return "arxiv_source" if self.arxiv else "pdf_pymupdf"


@dataclass
class ImportPlan:
    rag_dir: Path
    candidates: list[ImportCandidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    enrich_inspire: bool = False

    @property
    def new_entries(self) -> list[ImportCandidate]:
        return [candidate for candidate in self.candidates if not candidate.duplicate_of]

    @property
    def duplicates(self) -> list[ImportCandidate]:
        return [candidate for candidate in self.candidates if candidate.duplicate_of]


def _load_existing(rag_dir: Path) -> list[dict[str, str]]:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _match_keys(entry: dict[str, str]) -> list[tuple[str, str]]:
    normalized = normalize_entry(entry)
    keys: list[tuple[str, str]] = []
    doi = str(normalized["doi"])
    arxiv = str(normalized["arxiv"])
    title = str(normalized["title_norm"])
    authors = ",".join(str(author) for author in normalized["authors"][:3])
    year = str(normalized["year"])
    if doi:
        keys.append(("doi", doi))
    if arxiv:
        keys.append(("arxiv", arxiv))
    if title:
        keys.append(("title", title))
    if authors or year:
        keys.append(("fallback", f"{authors}|{year}"))
    return keys or [entry_dedup_key(entry)]


def _existing_maps(entries: list[dict[str, str]]) -> tuple[dict[tuple[str, str], dict[str, str]], set[str]]:
    by_dedup: dict[tuple[str, str], dict[str, str]] = {}
    used_keys: set[str] = set()
    for entry in entries:
        used_keys.add(entry.get("ID", ""))
        for key in _match_keys(entry):
            by_dedup.setdefault(key, entry)
    return by_dedup, used_keys


def _find_match(
    keys: list[tuple[str, str]],
    candidates: dict[tuple[str, str], object],
) -> tuple[tuple[str, str], object] | tuple[None, None]:
    for key in keys:
        if key in candidates:
            return key, candidates[key]
    return None, None


def _dedup_candidates(
    raw_candidates: list[ImportCandidate],
    existing_entries: list[dict[str, str]],
) -> list[ImportCandidate]:
    existing_by_dedup, used_keys = _existing_maps(existing_entries)
    batch_seen: dict[tuple[str, str], ImportCandidate] = {}
    planned: list[ImportCandidate] = []
    for candidate in raw_candidates:
        match_keys = _match_keys(candidate.entry)
        match_key, existing = _find_match(match_keys, existing_by_dedup)
        if existing:
            candidate.duplicate_of = existing.get("ID", "")  # type: ignore[union-attr]
            candidate.duplicate_match = f"{match_key[0]}:{match_key[1]}" if match_key else ""
            candidate.notes.append("duplicate of existing manifest entry")
        else:
            match_key, batch_duplicate = _find_match(match_keys, batch_seen)
            if batch_duplicate:
                candidate.duplicate_of = batch_duplicate.effective_key  # type: ignore[union-attr]
                candidate.duplicate_match = f"{match_key[0]}:{match_key[1]}" if match_key else ""
                candidate.notes.append("duplicate within import batch")
                planned.append(candidate)
                continue
            key = candidate.key
            if key in used_keys:
                old_key = key
                candidate.entry["ID"] = _unique_key(_sanitize_key(key), used_keys)
                candidate.notes.append(f"renamed citation key conflict: {old_key} -> {candidate.key}")
            else:
                used_keys.add(key)
            for match_key in _match_keys(candidate.entry):
                batch_seen.setdefault(match_key, candidate)
        planned.append(candidate)
    return planned


def _bib_candidates(bib_path: Path) -> list[ImportCandidate]:
    candidates: list[ImportCandidate] = []
    for entry in parse_bibtex_file(bib_path):
        candidate = ImportCandidate(entry=entry, source=f"bib:{bib_path}")
        file_field = entry.get("file", "")
        if file_field:
            pdf_paths = _resolve_file_paths(file_field)
            if pdf_paths:
                candidate.pdf_source = pdf_paths[0]
                candidate.notes.append(f"matched BibTeX file PDF: {pdf_paths[0].name}")
            else:
                candidate.notes.append("BibTeX file field did not resolve to a local PDF")
        candidates.append(candidate)
    return candidates


def _zip_candidates(zip_path: Path, existing_entries: list[dict[str, str]]) -> list[ImportCandidate]:
    candidates: list[ImportCandidate] = []
    _, used_keys = _existing_maps(existing_entries)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)
        rdf_file = next(tmp_path.rglob("*.rdf"), None)
        if not rdf_file:
            raise ValueError(f"No .rdf file found in {zip_path}")
        for index, item in enumerate(parse_rdf(rdf_file)):
            title = item["title"]
            doi = item["identifiers"].get("doi", "")
            arxiv = item["identifiers"].get("arxiv", "")
            authors = " and ".join(item["authors"])
            year = item["date"][:4] if item["date"] else ""
            zotero_key = str(item.get("citation_key", "")).strip()
            if zotero_key:
                base_key = _sanitize_key(zotero_key)
            else:
                first_author = item["authors"][0] if item["authors"] else ""
                last_name = first_author.split(",")[0].strip().split()[-1] if first_author else ""
                base_key = _sanitize_key(last_name + year) if last_name and year else f"entry-{index + 1}"
            bib_key = _unique_key(base_key, used_keys)
            entry: dict[str, str] = {
                "ENTRYTYPE": "article",
                "ID": bib_key,
                "title": title,
                "author": authors,
                "year": year,
            }
            if doi:
                entry["doi"] = doi
            if arxiv:
                entry["eprint"] = arxiv
            if zotero_key:
                entry["zotero_key"] = zotero_key

            candidate = ImportCandidate(entry=entry, source=f"zip:{zip_path}")
            for attachment in item["attachments"]:
                resolved = _resolve_pdf_path(attachment.get("path", ""), tmp_path)
                if not resolved:
                    continue
                if is_pdf(resolved):
                    candidate.zip_path = zip_path
                    candidate.zip_pdf_member = resolved.relative_to(tmp_path).as_posix()
                    break
                candidate.notes.append(f"skip non-PDF attachment: {resolved.name}")
            candidates.append(candidate)
    return candidates


def _select_search_result(query: str, record_id: str, limit: int, select: int) -> SearchResult | None:
    if record_id:
        results = search_inspire(f"recid:{record_id}", size=1)
        return results[0] if results else None
    results = search_inspire(query, size=max(limit, select))
    if not results:
        return None
    index = select - 1
    if index < 0 or index >= len(results):
        raise ValueError(f"--select {select} is outside search result range 1..{len(results)}")
    return results[index]


def _search_candidate(query: str, record_id: str, limit: int, select: int) -> ImportCandidate | None:
    result = _select_search_result(query, record_id, limit, select)
    if not result:
        return None
    bibtex = fetch_inspire_bibtex(result.record_id)
    entries = parse_bibtex(bibtex)
    if not entries:
        raise ValueError(f"INSPIRE BibTeX could not be parsed for record {result.record_id}")
    candidate = ImportCandidate(
        entry=entries[0],
        source="inspire",
        pdf_url=result.pdf_url,
        record_id=result.record_id,
    )
    return candidate


def _attach_pdf_dir_matches(candidates: list[ImportCandidate], pdf_dir: Path) -> None:
    entries = [candidate.entry for candidate in candidates if candidate.pdf_source is None]
    if not entries:
        return
    matches = _match_by_slug(entries, pdf_dir)
    by_id = {entry.get("ID", ""): pdf_path for entry, pdf_path in matches}
    for candidate in candidates:
        if candidate.pdf_source is None and candidate.key in by_id:
            candidate.pdf_source = by_id[candidate.key]
            candidate.notes.append(f"matched local PDF: {by_id[candidate.key].name}")


def build_plan(args: argparse.Namespace) -> ImportPlan:
    rag_dir = Path(args.rag_dir).resolve()
    existing_entries = _load_existing(rag_dir)
    raw: list[ImportCandidate] = []
    errors: list[str] = []

    if args.bib:
        raw.extend(_bib_candidates(Path(args.bib).resolve()))
    if args.zip:
        try:
            raw.extend(_zip_candidates(Path(args.zip).resolve(), existing_entries))
        except ValueError as exc:
            errors.append(str(exc))
    if args.query or args.record_id:
        candidate = _search_candidate(args.query, args.record_id, args.limit, args.select)
        if candidate:
            raw.append(candidate)
        else:
            errors.append("no INSPIRE candidate selected")

    planned = _dedup_candidates(raw, existing_entries)
    if args.pdf_dir:
        _attach_pdf_dir_matches(planned, Path(args.pdf_dir).resolve())
    return ImportPlan(rag_dir=rag_dir, candidates=planned, errors=errors, enrich_inspire=bool(getattr(args, "enrich_inspire", False)))


def _source_path(rag_dir: Path, key: str) -> Path:
    return rag_dir / "summary" / "sources" / f"{key}.md"


def _pdf_path(rag_dir: Path, key: str) -> Path:
    return rag_dir / "reference" / "pdfs" / f"{key}.pdf"


def plan_as_dict(plan: ImportPlan) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for candidate in plan.candidates:
        key = candidate.effective_key
        pdf_target = _pdf_path(plan.rag_dir, key)
        source_target = _source_path(plan.rag_dir, key)
        enrichment = plan_entry_update(candidate.entry) if plan.enrich_inspire else None
        items.append(
            {
                "key": candidate.key,
                "effective_key": key,
                "title": candidate.entry.get("title", ""),
                "doi": candidate.doi,
                "arxiv": candidate.arxiv,
                "source": candidate.source,
                "record_id": candidate.record_id,
                "duplicate_of": candidate.duplicate_of,
                "duplicate_match": candidate.duplicate_match,
                "manifest_action": "skip-duplicate" if candidate.duplicate_of else "append",
                "pdf_action": _planned_pdf_action(candidate, pdf_target),
                "pdf_target": str(pdf_target),
                "evidence_route": candidate.evidence_route,
                "parsed_markdown": str(parsed_markdown_path(plan.rag_dir, candidate.doc_id)),
                "parsed_manifest": str(parsed_manifest_path(plan.rag_dir, candidate.doc_id)),
                "chunk_jsonl": str(chunk_manifest_path(plan.rag_dir, candidate.doc_id)),
                "source_page_action": "exists" if source_target.exists() else "create",
                "source_page": str(source_target),
                "vocabulary_action": "suggest-only",
                "edge_index_action": "refresh",
                "bib_enrichment": {
                    "enabled": plan.enrich_inspire,
                    "provider": enrichment.provider if enrichment else "inspire",
                    "provider_record_id": enrichment.provider_record_id if enrichment else "",
                    "changes": [change.__dict__ for change in enrichment.changes] if enrichment else [],
                    "conflicts": enrichment.conflicts if enrichment else [],
                    "needs_review": enrichment.needs_review if enrichment else False,
                },
                "notes": candidate.notes,
            }
        )
    return {
        "rag_dir": str(plan.rag_dir),
        "summary": {
            "candidates": len(plan.candidates),
            "new_entries": len(plan.new_entries),
            "duplicates": len(plan.duplicates),
            "errors": len(plan.errors),
        },
        "items": items,
        "errors": plan.errors,
    }


def _planned_pdf_action(candidate: ImportCandidate, pdf_target: Path) -> str:
    if pdf_target.exists():
        return "exists"
    if candidate.pdf_source or candidate.zip_pdf_member:
        return "copy"
    if candidate.arxiv:
        return "download-arxiv"
    if candidate.pdf_url:
        return "download-provider"
    return "missing"


def print_plan(plan: ImportPlan, as_json: bool = False) -> None:
    data = plan_as_dict(plan)
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    summary = data["summary"]
    print("import plan")
    print(
        f"- candidates={summary['candidates']} new={summary['new_entries']} "
        f"duplicates={summary['duplicates']} errors={summary['errors']}"
    )
    for item in data["items"]:
        print(
            f"- {item['effective_key']}: {item['manifest_action']} | pdf={item['pdf_action']} "
            f"| evidence={item['evidence_route']} | source={item['source_page_action']}"
        )
        title = str(item.get("title", "")).strip()
        if title:
            print(f"  title: {title}")
        if item["duplicate_of"]:
            print(f"  duplicate_of: {item['duplicate_of']} match={item['duplicate_match']}")
    for error in plan.errors:
        print(f"error: {error}")


def _write_source_if_missing(rag_dir: Path, entry: dict[str, str], key: str) -> bool:
    source_path = _source_path(rag_dir, key)
    if source_path.exists():
        return False
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_entry = dict(entry)
    source_entry["ID"] = key
    source_path.write_text(
        format_frontmatter(default_frontmatter(source_entry, rag_dir)) + body_skeleton(source_entry, rag_dir),
        encoding="utf-8",
    )
    return True


def _copy_zip_pdf(candidate: ImportCandidate, pdf_target: Path) -> bool:
    if not candidate.zip_path or not candidate.zip_pdf_member:
        return False
    pdf_target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(candidate.zip_path, "r") as zf:
            zf.extract(candidate.zip_pdf_member, tmp_path)
        extracted = tmp_path / candidate.zip_pdf_member
        if not is_pdf(extracted):
            raise ValueError(f"ZIP attachment is not a valid PDF: {candidate.zip_pdf_member}")
        shutil.copy2(extracted, pdf_target)
    return True


def _refresh_indexes(rag_dir: Path) -> int:
    tag_map = collect_edge_tags(rag_dir)
    updated = 0
    for category, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_category_page(rag_dir, category, tag)
            if rebuild_auto_block(page, category, tag, source_keys):
                updated += 1
    return updated


def apply_plan(plan: ImportPlan) -> dict[str, int]:
    ensure_rag_dirs(plan.rag_dir)
    manifest = plan.rag_dir / "references.bib"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.exists():
        manifest.write_text("", encoding="utf-8")

    appended = 0
    copied_pdfs = 0
    downloaded_pdfs = 0
    source_pages = 0
    with manifest.open("a", encoding="utf-8") as handle:
        for candidate in plan.new_entries:
            handle.write(render_bibtex(candidate.entry))
            handle.write("\n\n")
            appended += 1

    for candidate in plan.candidates:
        key = candidate.effective_key
        pdf_target = _pdf_path(plan.rag_dir, key)
        if not pdf_target.exists() and candidate.pdf_source:
            pdf_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate.pdf_source, pdf_target)
            copied_pdfs += 1
        elif not pdf_target.exists() and candidate.zip_pdf_member:
            if _copy_zip_pdf(candidate, pdf_target):
                copied_pdfs += 1
        elif not pdf_target.exists() and candidate.arxiv:
            download_arxiv_pdf(candidate.arxiv, pdf_target, dry_run=False)
            downloaded_pdfs += 1
        if _write_source_if_missing(plan.rag_dir, candidate.entry, key):
            source_pages += 1

    updated_indexes = _refresh_indexes(plan.rag_dir)
    if plan.enrich_inspire:
        update_plan = build_update_plan(plan.rag_dir, all_entries=True)
        bib_updates = apply_update_plan(update_plan) if update_plan.changed else 0
    else:
        bib_updates = 0
    append_log(
        plan.rag_dir,
        "import-pipeline",
        f"candidates={len(plan.candidates)}",
        (
            f"appended={appended} duplicates={len(plan.duplicates)} copied_pdfs={copied_pdfs} "
            f"downloaded_pdfs={downloaded_pdfs} source_pages={source_pages} bib_updates={bib_updates} "
            f"updated_indexes={updated_indexes}"
        ),
    )
    return {
        "appended": appended,
        "duplicates": len(plan.duplicates),
        "copied_pdfs": copied_pdfs,
        "downloaded_pdfs": downloaded_pdfs,
        "source_pages": source_pages,
        "bib_updates": bib_updates,
        "updated_indexes": updated_indexes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and apply a unified RAG import")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--bib", default="")
    parser.add_argument("--zip", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--record-id", default="")
    parser.add_argument("--pdf-dir", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--select", type=int, default=1)
    parser.add_argument("--enrich-inspire", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not any([args.bib, args.zip, args.query, args.record_id]):
        print("provide at least one of --bib, --zip, --query, or --record-id")
        return 1
    if args.dry_run and args.yes:
        print("choose only one of --dry-run or --yes")
        return 1

    try:
        plan = build_plan(args)
    except ValueError as exc:
        print(str(exc))
        return 1
    print_plan(plan, as_json=args.json)
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    result = apply_plan(plan)
    print(
        "applied: "
        f"appended={result['appended']} duplicates={result['duplicates']} "
        f"copied_pdfs={result['copied_pdfs']} downloaded_pdfs={result['downloaded_pdfs']} "
        f"source_pages={result['source_pages']} bib_updates={result['bib_updates']} "
        f"updated_indexes={result['updated_indexes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
