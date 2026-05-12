"""Sync local PDFs into the RAG knowledge base.

Primary strategy: read the ``file`` field from BibTeX entries (Zotero export),
which contains absolute paths to PDFs on disk.
Fallback: scan a --pdf-dir and match by key / DOI slug / title slug.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from bib_parser import parse_bibtex_file
from metadata_normalizer import normalize_entry
from pdf_validator import is_pdf
from common import append_log, slugify


def _resolve_file_paths(file_field: str) -> list[Path]:
    """Parse the BibTeX ``file`` field, which may contain multiple
    semicolon-separated paths with BibTeX-style double-backslash escaping."""
    paths: list[Path] = []
    bs = chr(92)  # backslash
    for chunk in file_field.split(';'):
        chunk = chunk.strip()
        if not chunk:
            continue
        # BibTeX escaped backslashes: ``C\\:\\\\Users\\\\...`` → ``C:\Users\...``
        # Try multiple unescape strategies until we find a file that exists
        candidates = [
            chunk,
            chunk.replace(bs + bs, bs),
            chunk.replace(bs + bs, bs).replace(bs + ':', ':'),
        ]
        for cand in candidates:
            p = Path(cand)
            if p.exists() and is_pdf(p):
                paths.append(p)
                break
    return paths


def _copy_pdf(src: Path, dest_dir: Path, key: str, dry_run: bool) -> bool:
    dest = dest_dir / f"{key}.pdf"
    if dest.exists():
        return False
    if dry_run:
        if not dest_dir.exists():
            print(f"would create directory: {dest_dir}")
        print(f"would copy: {src} -> {dest}")
        return True
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _match_by_slug(entries: list[dict[str, str]], pdf_dir: Path) -> list[tuple[dict[str, str], Path]]:
    """Fallback: scan a directory and match PDFs to entries by name."""
    results: list[tuple[dict[str, str], Path]] = []
    pdf_files = [f for f in pdf_dir.rglob("*.pdf") if f.is_file() and is_pdf(f)]
    for entry in entries:
        normalized = normalize_entry(entry)
        key_slug = normalized["key"].lower()
        doi_slug = normalized["doi"].split("/")[-1] if normalized["doi"] else ""
        title_slug = slugify(str(normalized["title_norm"]))[:60]
        candidate: Path | None = None
        best_score = 0
        for pdf_path in pdf_files:
            pdf_name = pdf_path.stem.lower().replace("_", "-").replace(".", "-")
            score = 0
            if key_slug and key_slug in pdf_name:
                score = 100
            if doi_slug and doi_slug in pdf_name:
                score = max(score, 90)
            if title_slug and title_slug[:30] in pdf_name:
                score = max(score, 60)
            if score > best_score:
                best_score = score
                candidate = pdf_path
        if candidate:
            results.append((entry, candidate))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync local PDFs into RAG")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--pdf-dir", default="", help="Directory with source PDFs (fallback)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    manifest_path = rag_dir / "references.bib"
    pdfs_dir = rag_dir / "reference" / "pdfs"

    if not manifest_path.exists():
        print("No references.bib found; run import-bib first")
        return 1

    entries = parse_bibtex_file(manifest_path)
    copied = 0
    missing = 0

    # Strategy 1: use file field from BibTeX entries (most reliable)
    for entry in entries:
        key = entry.get("ID", "")
        file_field = entry.get("file", "")
        if not file_field:
            continue
        pdf_paths = _resolve_file_paths(file_field)
        if pdf_paths:
            if _copy_pdf(pdf_paths[0], pdfs_dir, key, args.dry_run):
                print(f"file: {key} -> {pdf_paths[0].name}")
                copied += 1
        else:
            missing += 1

    # Strategy 2: scan --pdf-dir for entries still without PDFs
    if args.pdf_dir:
        pdf_dir = Path(args.pdf_dir).resolve()
        without_pdf = [
            e for e in entries
            if not (pdfs_dir / f"{e.get('ID', '')}.pdf").exists()
        ]
        if without_pdf:
            matches = _match_by_slug(without_pdf, pdf_dir)
            for entry, pdf_path in matches:
                key = entry.get("ID", pdf_path.stem)
                if _copy_pdf(pdf_path, pdfs_dir, key, args.dry_run):
                    print(f"match: {key} -> {pdf_path.name}")
                    copied += 1

    if args.dry_run:
        print(f"would append log entry: sync-pdf dry_run={args.dry_run} copied={copied} missing={missing}")
    else:
        append_log(rag_dir, "sync-pdf", f"dry_run={args.dry_run}", f"copied={copied} missing={missing}")
    print(f"copied={copied} missing={missing} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
