"""Scan a RAG update directory for merge conflicts against a base RAG."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bib_parser import parse_bibtex_file
from common import read_frontmatter


def _bib_keys(rag_dir: Path) -> set[str]:
    manifest = rag_dir / "references.bib"
    return {entry.get("ID", "") for entry in parse_bibtex_file(manifest)} if manifest.exists() else set()


def _doc_ids(rag_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    sources = rag_dir / "summary" / "sources"
    if not sources.is_dir():
        return result
    for page in sources.glob("*.md"):
        fm, _ = read_frontmatter(page)
        doc_id = str(fm.get("doc_id", ""))
        if doc_id:
            result[doc_id] = page.stem
    return result


def build_merge_report(base_rag: Path, update_rag: Path) -> dict[str, Any]:
    base_keys = _bib_keys(base_rag)
    update_keys = _bib_keys(update_rag)
    base_docs = _doc_ids(base_rag)
    update_docs = _doc_ids(update_rag)
    duplicate_keys = sorted(base_keys & update_keys)
    duplicate_doc_ids = sorted(set(base_docs) & set(update_docs))
    vocabulary_conflict = (base_rag / "vocabulary.md").exists() and (update_rag / "vocabulary.md").exists()
    return {
        "base_rag": str(base_rag),
        "update_rag": str(update_rag),
        "duplicate_citation_keys": duplicate_keys,
        "duplicate_doc_ids": [
            {"doc_id": doc_id, "base_key": base_docs[doc_id], "update_key": update_docs[doc_id]}
            for doc_id in duplicate_doc_ids
        ],
        "vocabulary_review_needed": vocabulary_conflict,
        "manual_review": bool(duplicate_keys or duplicate_doc_ids or vocabulary_conflict),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan RAG update merge conflicts")
    parser.add_argument("--base-rag", default="RAG")
    parser.add_argument("--update-rag", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_merge_report(Path(args.base_rag).resolve(), Path(args.update_rag).resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["manual_review"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
