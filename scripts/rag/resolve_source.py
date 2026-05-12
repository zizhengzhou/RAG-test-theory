"""Resolve RAG references to primary evidence routes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from bib_parser import parse_bibtex_file
from darw_schema import ARXIV_SOURCE, PDF_PYMUPDF
from metadata_normalizer import normalize_arxiv, normalize_doi, normalize_entry
from pdf_validator import is_pdf
from sync_pdf import _resolve_file_paths


@dataclass(frozen=True)
class ResolvedSource:
    doc_id: str
    citation_key: str
    arxiv_id: str
    doi: str
    title: str
    pdf_path: str
    route: str
    needs_review: bool
    metadata_conflicts: list[str]

    @property
    def resolved(self) -> bool:
        return bool(self.route)


def _entry_year(entry: dict[str, str]) -> str:
    year = entry.get("year", "").strip()
    if year:
        return year
    date = entry.get("date", "").strip()
    return date[:4] if len(date) >= 4 else date


def _pdf_from_entry(entry: dict[str, str], rag_dir: Path) -> Path | None:
    key = entry.get("ID", "").strip()
    local_pdf = rag_dir / "reference" / "pdfs" / f"{key}.pdf"
    if local_pdf.exists() and is_pdf(local_pdf):
        return local_pdf
    file_field = entry.get("file", "")
    if file_field:
        paths = _resolve_file_paths(file_field)
        if paths:
            return paths[0]
    return None


def resolve_entry(entry: dict[str, str], rag_dir: Path, *, enrich_inspire: bool = False) -> ResolvedSource:
    normalized = normalize_entry(entry)
    key = str(normalized["key"] or entry.get("ID", "")).strip()
    title = str(normalized["title"] or entry.get("title", "")).replace("{", "").replace("}", "").strip()
    doi = normalize_doi(str(normalized["doi"] or entry.get("doi", "")))
    arxiv = normalize_arxiv(str(normalized["arxiv"] or entry.get("eprint", "") or entry.get("arxiv", "")))
    conflicts: list[str] = []
    needs_review = False

    if enrich_inspire and not arxiv:
        from external_search import search_inspire_by_identifier, search_inspire
        results = search_inspire_by_identifier(doi=doi, size=3) if doi else []
        if not results and title:
            results = search_inspire(title, size=3)
        candidates = [r for r in results if r.arxiv]
        if len(candidates) == 1:
            arxiv = normalize_arxiv(candidates[0].arxiv)
        elif len(candidates) > 1:
            needs_review = True
            conflicts.append("multiple INSPIRE arXiv candidates")

    pdf_path = _pdf_from_entry(entry, rag_dir)
    route = ""
    doc_id = ""
    if arxiv:
        route = ARXIV_SOURCE
        doc_id = f"arxiv:{arxiv}"
    elif pdf_path:
        route = PDF_PYMUPDF
        doc_id = doi or f"pdf:{key}"
    else:
        needs_review = True
        conflicts.append("no arXiv ID or valid PDF found")
        doc_id = doi or f"unresolved:{key}"

    return ResolvedSource(
        doc_id=doc_id,
        citation_key=key,
        arxiv_id=arxiv,
        doi=doi,
        title=title,
        pdf_path=str(pdf_path) if pdf_path else "",
        route=route,
        needs_review=needs_review,
        metadata_conflicts=conflicts,
    )


def load_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def resolve_key(rag_dir: Path, key: str, *, enrich_inspire: bool = False) -> ResolvedSource | None:
    for entry in load_entries(rag_dir):
        if entry.get("ID") == key:
            return resolve_entry(entry, rag_dir, enrich_inspire=enrich_inspire)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve RAG references to DARW evidence routes")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--enrich-inspire", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    entries = load_entries(rag_dir)
    if args.key:
        entries = [entry for entry in entries if entry.get("ID") == args.key]
    elif not args.all:
        print("provide --key or --all")
        return 1

    if not entries:
        print("no matching entries")
        return 1

    results = [resolve_entry(entry, rag_dir, enrich_inspire=args.enrich_inspire) for entry in entries]
    print(json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False))
    if args.dry_run:
        print("[dry-run] no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
