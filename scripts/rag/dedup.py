"""Deduplication logic for RAG references."""

from __future__ import annotations

import argparse
from pathlib import Path

from bib_parser import parse_bibtex_file
from metadata_normalizer import normalize_entry


def entry_dedup_key(entry: dict[str, str]) -> tuple[str, str]:
    normalized = normalize_entry(entry)
    if normalized["doi"]:
        return ("doi", str(normalized["doi"]))
    if normalized["arxiv"]:
        return ("arxiv", str(normalized["arxiv"]))
    if normalized["title_norm"]:
        return ("title", str(normalized["title_norm"]))
    authors = ",".join(normalized["authors"][:3])
    return ("fallback", f"{authors}|{normalized['year']}")


def deduplicate_entries(entries: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    duplicates: list[dict[str, str]] = []
    for entry in entries:
        key = entry_dedup_key(entry)
        if key in seen:
            duplicates.append(entry)
            continue
        seen.add(key)
        unique.append(entry)
    return unique, duplicates


def compare_bibs(left: Path, right: Path) -> list[dict[str, str]]:
    left_entries = parse_bibtex_file(left)
    right_entries = parse_bibtex_file(right)
    left_keys = {entry_dedup_key(entry) for entry in left_entries}
    return [entry for entry in right_entries if entry_dedup_key(entry) in left_keys]


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate BibTeX entries")
    parser.add_argument("--bib", required=True)
    args = parser.parse_args()
    entries = parse_bibtex_file(Path(args.bib))
    unique, duplicates = deduplicate_entries(entries)
    print(f"unique={len(unique)} duplicates={len(duplicates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
