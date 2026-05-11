"""Import a BibTeX file into the RAG references manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from bib_parser import parse_bibtex_file, render_bibtex
from dedup import compare_bibs, entry_dedup_key
from common import append_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Import BibTeX into RAG manifest")
    parser.add_argument("--bib", required=True, help="Source BibTeX file")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    bib_path = Path(args.bib).resolve()
    manifest_path = rag_dir / "references.bib"

    source_entries = parse_bibtex_file(bib_path)
    print(f"Parsed {len(source_entries)} entries from {bib_path}")

    if not manifest_path.exists():
        unique = source_entries
        duplicates = []
    else:
        duplicates = compare_bibs(manifest_path, bib_path)
        dup_keys = {entry_dedup_key(e) for e in duplicates}
        unique = [e for e in source_entries if entry_dedup_key(e) not in dup_keys]

    print(f"New entries: {len(unique)}, duplicates skipped: {len(duplicates)}")

    if args.dry_run:
        print("[dry-run] no files written")
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if unique:
            with manifest_path.open("a", encoding="utf-8") as out:
                for entry in unique:
                    out.write(render_bibtex(entry))
                    out.write("\n\n")

        append_log(
            rag_dir,
            "import-bib",
            f"source={bib_path} dry_run={args.dry_run}",
            f"new={len(unique)} skipped={len(duplicates)}",
        )

    print("import-bib complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
