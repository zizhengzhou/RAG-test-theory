"""Import a Zotero RDF + files zip into the RAG knowledge base."""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

from bib_parser import render_bibtex, parse_bibtex_file
from dedup import entry_dedup_key
from pdf_validator import is_pdf
from rdf_parser import parse_rdf
from common import append_log
from temp_paths import local_temp_dir


def _sanitize_key(raw: str) -> str:
    """Sanitize a raw citation key: lowercase, strip braces, replace non-alnum with dash."""
    key = raw.replace("{", "").replace("}", "").strip().lower()
    key = re.sub(r"[^a-z0-9]+", "-", key).strip("-")
    return key or "entry"


def _unique_key(base: str, used: set[str]) -> str:
    """Return *base* if not in *used*, otherwise ``base-2``, ``base-3``, etc."""
    if base not in used:
        used.add(base)
        return base
    n = 2
    while f"{base}-{n}" in used:
        n += 1
    key = f"{base}-{n}"
    used.add(key)
    return key


def _resolve_pdf_path(att_path_str: str, tmp_path: Path) -> Path | None:
    """Find an attachment file inside the extracted zip tree by name."""
    att_name = Path(att_path_str).name
    for candidate in tmp_path.rglob("**/*"):
        if candidate.is_file() and candidate.name == att_name:
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Zotero RDF zip into RAG")
    parser.add_argument("--zip", required=True, dest="zip_path")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    zip_path = Path(args.zip_path).resolve()
    pdfs_dir = rag_dir / "reference" / "pdfs"
    imports_dir = rag_dir / "reference" / "imports"
    manifest_path = rag_dir / "references.bib"

    for d in (pdfs_dir, imports_dir):
        if not args.dry_run:
            d.mkdir(parents=True, exist_ok=True)

    with local_temp_dir("rag_zip_") as tmp_path:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)

        rdf_file = None
        for found in tmp_path.rglob("*.rdf"):
            rdf_file = found
            break

        if not rdf_file:
            print("No .rdf file found in zip")
            return 1

        print(f"rdf: {rdf_file.relative_to(tmp_path)}")
        items = parse_rdf(rdf_file)
        new_bib_entries: list[dict[str, str]] = []
        copied_pdfs = 0
        skipped_html = 0
        skipped_duplicate = 0

        existing_entries = parse_bibtex_file(manifest_path) if manifest_path.exists() else []

        # Existing dedup-key → BibTeX key mapping
        existing_dedup_map: dict[tuple[str, str], str] = {}
        for ee in existing_entries:
            dk = entry_dedup_key(ee)
            if dk not in existing_dedup_map:
                existing_dedup_map[dk] = ee.get("ID", "")

        # All known BibTeX keys (existing + already-used-in-batch) for collision avoidance
        used_keys: set[str] = {ee.get("ID", "") for ee in existing_entries}

        # Dedup keys already seen in this batch
        batch_dedup_keys: set[tuple[str, str]] = set()

        for i, item in enumerate(items):
            title = item["title"]
            doi = item["identifiers"].get("doi", "")
            arxiv = item["identifiers"].get("arxiv", "")
            authors = " and ".join(item["authors"])
            year = item["date"][:4] if item["date"] else ""

            # --- Key generation: prefer Zotero citation key, then author-year, then entry-N ---
            zotero_key = str(item.get("citation_key", "")).strip()
            if zotero_key:
                base_key = _sanitize_key(zotero_key)
            else:
                first_author = item["authors"][0] if item["authors"] else ""
                last_name = first_author.split(",")[0].strip().split()[-1] if first_author else ""
                if last_name and year:
                    base_key = _sanitize_key(last_name + year)
                else:
                    base_key = f"entry-{i + 1}"
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

            # --- Dedup: skip if already in existing entries or already in this batch ---
            dk = entry_dedup_key(entry)
            if dk in existing_dedup_map:
                pdf_key = existing_dedup_map[dk]
                print(f"  duplicate of existing: {title[:80]} → {pdf_key}")
            elif dk in batch_dedup_keys:
                print(f"  duplicate within import: {title[:80]}")
                skipped_duplicate += 1
                continue
            else:
                batch_dedup_keys.add(dk)
                new_bib_entries.append(entry)
                pdf_key = bib_key

            # --- Copy attachments ---
            for att in item["attachments"]:
                att_path_str = att.get("path", "")
                att_type = att.get("type", "")
                resolved = _resolve_pdf_path(att_path_str, tmp_path)
                if not resolved:
                    continue
                if is_pdf(resolved):
                    dest = pdfs_dir / f"{pdf_key}.pdf"
                    print(f"  PDF: {resolved.name} → {pdf_key}.pdf")
                    if not args.dry_run:
                        shutil.copy2(resolved, dest)
                        copied_pdfs += 1
                else:
                    print(f"  skip non-PDF: {resolved.name}")
                    skipped_html += 1

        # Append new BibTeX entries
        if new_bib_entries and not args.dry_run:
            with manifest_path.open("a", encoding="utf-8") as out:
                for entry in new_bib_entries:
                    out.write(render_bibtex(entry))
                    out.write("\n\n")

        report = (
            f"entries={len(items)} new_bib={len(new_bib_entries)} "
            f"skipped_dup={skipped_duplicate} pdfs={copied_pdfs} skipped_html={skipped_html}"
        )
        print(report)
        if args.dry_run:
            print("[dry-run] no files written")
        else:
            append_log(rag_dir, "import-zip", f"source={zip_path} dry_run={args.dry_run}", report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
