"""Check DARW evidence artifacts for staleness against source materials.

Detects:
- Source SHA256 mismatch (PDF/TeX changed since last parse)
- Parser version changes (re-parse needed)
- Missing parsed Markdown or manifests
- Source page references to stale hashes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import read_frontmatter
from darw_schema import chunk_manifest_path, parsed_manifest_path, parsed_markdown_path, safe_doc_id
from parsers import sha256_file


def _resolve_rag_path(rag_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else rag_dir / path


def check_entry(rag_dir: Path, key: str, entry: dict) -> list[str]:
    issues: list[str] = []

    eprint = entry.get("eprint", "")
    doi = entry.get("doi", "")
    if eprint:
        doc_id = safe_doc_id(f"arxiv:{eprint}")
    elif doi:
        doc_id = safe_doc_id(doi)
    else:
        doc_id = safe_doc_id(f"pdf:{key}")

    pm = parsed_manifest_path(rag_dir, doc_id)
    md = parsed_markdown_path(rag_dir, doc_id)
    cm = chunk_manifest_path(rag_dir, doc_id)
    sp = rag_dir / "summary" / "sources" / f"{key}.md"

    # 1. Parsed manifest missing
    if not pm.exists():
        issues.append(f"parsed manifest missing: {pm.relative_to(rag_dir).as_posix()}")
    else:
        try:
            data = json.loads(pm.read_text(encoding="utf-8"))
        except Exception:
            issues.append(f"parsed manifest unreadable: {pm.relative_to(rag_dir).as_posix()}")
            data = {}

        # 2. Parser version change
        current_parser_version = _get_current_parser_version(str(data.get("parser", "")))
        stored_version = str(data.get("parser_version", ""))
        if stored_version and current_parser_version and stored_version != current_parser_version:
            issues.append(
                f"parser version changed ({stored_version} -> {current_parser_version}), "
                f"re-parse needed for {key}"
            )

        # 3. Source hash mismatch
        source_hash = str(data.get("source_sha256", ""))
        original_pdf = str(data.get("original_pdf", ""))
        if source_hash and original_pdf:
            pdf_path = _resolve_rag_path(rag_dir, original_pdf)
            if pdf_path.exists():
                actual = sha256_file(pdf_path)
                if actual != source_hash:
                    issues.append(f"source SHA256 mismatch for {key} (PDF changed)")
            else:
                issues.append(f"original PDF missing for {key}: {original_pdf}")

    # 4. Parsed Markdown missing
    if not md.exists():
        issues.append(f"parsed Markdown missing: {md.relative_to(rag_dir).as_posix()}")

    # 5. Chunk manifest missing
    if not cm.exists():
        issues.append(f"chunk manifest missing: {cm.relative_to(rag_dir).as_posix()}")

    # 6. Source page references stale hashes
    if sp.exists():
        fm, _ = read_frontmatter(sp)
        source = fm.get("source")
        page_sha = ""
        if isinstance(source, dict):
            page_sha = str(source.get("source_sha256", ""))
        if pm.exists() and data:
            stored_sha = str(data.get("source_sha256", ""))
            if page_sha and stored_sha and page_sha != stored_sha:
                issues.append(f"source page source_sha256 stale for {key}")

    return issues


def _get_current_parser_version(parser_name: str) -> str:
    try:
        from parsers import _get_arxiv2md_version, _get_pymupdf4llm_version
        if parser_name == "arxiv2md":
            return _get_arxiv2md_version()
        if parser_name == "pymupdf4llm":
            return _get_pymupdf4llm_version()
        return ""
    except Exception:
        return ""


def check_all(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    bib_path = rag_dir / "references.bib"
    if not bib_path.exists():
        return ["references.bib missing"]

    from bib_parser import parse_bibtex_file
    entries = parse_bibtex_file(bib_path)
    for entry in entries:
        key = entry.get("ID", "")
        if not key:
            continue
        issues.extend(check_entry(rag_dir, key, entry))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DARW evidence staleness")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="", help="Check a single entry by citation key")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()

    if args.key:
        from bib_parser import parse_bibtex_file
        entries = parse_bibtex_file(rag_dir / "references.bib")
        entry = None
        for e in entries:
            if e.get("ID") == args.key:
                entry = e
                break
        if entry is None:
            print(f"Citation key '{args.key}' not found in references.bib")
            return 1
        issues = check_entry(rag_dir, args.key, entry)
    else:
        issues = check_all(rag_dir)

    if issues:
        print(f"Staleness issues found: {len(issues)}")
        for issue in issues:
            print(f"- [ ] {issue}")
        return 1
    print("No staleness issues found — all evidence is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
