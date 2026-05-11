"""Import a Zotero RDF + files zip into the RAG knowledge base."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

from bib_parser import render_bibtex, parse_bibtex_file
from dedup import entry_dedup_key
from pdf_validator import is_pdf
from rdf_parser import parse_rdf
from common import append_log


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

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
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

        # Build bib entries first, then check dedup before copying PDFs
        # so we use the existing entry's key when an entry is already in the manifest
        existing_entries = parse_bibtex_file(manifest_path) if manifest_path.exists() else []
        existing_key_map: dict[tuple[str, str], str] = {}
        for ee in existing_entries:
            dk = entry_dedup_key(ee)
            if dk not in existing_key_map:
                existing_key_map[dk] = ee.get("ID", "")

        for i, item in enumerate(items):
            title = item["title"]
            doi = item["identifiers"].get("doi", "")
            arxiv = item["identifiers"].get("arxiv", "")
            authors = " and ".join(item["authors"])
            year = item["date"][:4] if item["date"] else ""
            first_author = item["authors"][0] if item["authors"] else ""
            last_name = first_author.split(",")[0].strip().split()[-1] if first_author else ""
            bib_key = (
                last_name.replace("{", "").replace("}", "").lower() + year
                if last_name and year
                else f"entry-{i + 1}"
            )

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

            new_bib_entries.append(entry)

            # Resolve dedup: use existing key for PDF naming if duplicate
            dk = entry_dedup_key(entry)
            pdf_key = existing_key_map.get(dk, bib_key)

            for att in item["attachments"]:
                att_path_str = att.get("path", "")
                att_type = att.get("type", "")
                resolved = None
                att_name = Path(att_path_str).name
                for candidate in tmp_path.rglob("**/*"):
                    if candidate.is_file() and candidate.name == att_name:
                        resolved = candidate
                        break
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

        # dedup and append BibTeX
        existing_dedup_keys = {entry_dedup_key(e) for e in existing_entries}
        unique = [e for e in new_bib_entries if entry_dedup_key(e) not in existing_dedup_keys]

        if unique and not args.dry_run:
            with manifest_path.open("a", encoding="utf-8") as out:
                for entry in unique:
                    out.write(render_bibtex(entry))
                    out.write("\n\n")

        report = f"entries={len(new_bib_entries)} new_bib={len(unique)} pdfs={copied_pdfs} skipped_html={skipped_html}"
        print(report)
        if args.dry_run:
            print("[dry-run] no files written")
        else:
            append_log(rag_dir, "import-zip", f"source={zip_path} dry_run={args.dry_run}", report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
