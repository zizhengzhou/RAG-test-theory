"""Validate DARW parsed evidence manifests and chunk manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from darw_schema import CHUNK_SCHEMA_VERSION, PARSED_EVIDENCE_SCHEMA_VERSION
from parsers import sha256_file


def _resolve_rag_path(rag_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else rag_dir / path


def validate_parsed_manifest(rag_dir: Path, manifest_path: Path) -> list[str]:
    issues: list[str] = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid parsed manifest JSON: {manifest_path}: {exc}"]

    if data.get("schema_version") != PARSED_EVIDENCE_SCHEMA_VERSION:
        issues.append(f"wrong parsed evidence schema in {manifest_path}: {data.get('schema_version')}")
    for field in ("doc_id", "citation_key", "route", "parser", "source_sha256", "parsed_markdown", "created_at"):
        if not data.get(field):
            issues.append(f"missing parsed manifest field '{field}' in {manifest_path}")

    parsed_value = str(data.get("parsed_markdown", ""))
    if parsed_value:
        parsed_path = _resolve_rag_path(rag_dir, parsed_value)
        if not parsed_path.exists():
            issues.append(f"parsed Markdown missing for {manifest_path}: {parsed_value}")

    source_hash = str(data.get("source_sha256", ""))
    original_pdf = str(data.get("original_pdf", ""))
    if source_hash and original_pdf:
        pdf_path = _resolve_rag_path(rag_dir, original_pdf)
        if pdf_path.exists():
            actual = sha256_file(pdf_path)
            if actual != source_hash:
                issues.append(f"source_sha256 mismatch in {manifest_path}: expected {source_hash} got {actual}")
    return issues


def _load_chunk_lines(chunk_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    issues: list[str] = []
    for line_no, line in enumerate(chunk_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except Exception as exc:
            issues.append(f"invalid chunk JSON in {chunk_path}:{line_no}: {exc}")
            continue
        if not isinstance(value, dict):
            issues.append(f"chunk record is not an object in {chunk_path}:{line_no}")
            continue
        records.append(value)
    return records, issues


def validate_chunk_manifest(rag_dir: Path, chunk_path: Path) -> list[str]:
    issues: list[str] = []
    records, parse_issues = _load_chunk_lines(chunk_path)
    issues.extend(parse_issues)
    seen: set[str] = set()
    parsed_text_cache: dict[str, str] = {}

    for record in records:
        chunk_id = str(record.get("chunk_id", ""))
        if record.get("schema_version") != CHUNK_SCHEMA_VERSION:
            issues.append(f"wrong chunk schema in {chunk_path}: {chunk_id or '<missing>'}")
        for field in ("chunk_id", "doc_id", "citation_key", "source_type", "parser", "source_sha256", "section_title", "section_anchor", "text"):
            if not record.get(field):
                issues.append(f"missing chunk field '{field}' in {chunk_path}: {chunk_id or '<missing>'}")
        if chunk_id in seen:
            issues.append(f"duplicate chunk_id in {chunk_path}: {chunk_id}")
        seen.add(chunk_id)
        contains_equation = bool(record.get("contains_equation"))
        equation_ids = record.get("equation_ids", [])
        if contains_equation and not equation_ids:
            issues.append(f"chunk contains equation but has no equation_ids: {chunk_id}")
        if equation_ids and not contains_equation:
            issues.append(f"chunk has equation_ids but contains_equation=false: {chunk_id}")
        char_start = record.get("char_start")
        char_end = record.get("char_end")
        if not isinstance(char_start, int) or not isinstance(char_end, int) or char_start < 0 or char_end < char_start:
            issues.append(f"invalid char range for chunk: {chunk_id}")
    return issues


def validate_evidence(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    parsed_dir = rag_dir / "reference" / "parsed"
    chunks_dir = rag_dir / "reference" / "chunks"
    if parsed_dir.is_dir():
        for manifest in parsed_dir.glob("*.manifest.json"):
            issues.extend(validate_parsed_manifest(rag_dir, manifest))
    if chunks_dir.is_dir():
        all_ids: set[str] = set()
        for chunk_path in chunks_dir.glob("*.jsonl"):
            issues.extend(validate_chunk_manifest(rag_dir, chunk_path))
            records, _ = _load_chunk_lines(chunk_path)
            for record in records:
                chunk_id = str(record.get("chunk_id", ""))
                if chunk_id in all_ids:
                    issues.append(f"duplicate chunk_id across manifests: {chunk_id}")
                all_ids.add(chunk_id)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DARW parsed evidence and chunk manifests")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    issues = validate_evidence(rag_dir)
    if issues:
        print(f"Evidence issues found: {len(issues)}")
        for issue in issues:
            print(f"- [ ] {issue}")
        return 1
    print("No evidence issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
