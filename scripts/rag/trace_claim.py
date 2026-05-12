"""Trace DARW chunk IDs back to raw parsed evidence."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import read_frontmatter


@dataclass(frozen=True)
class TraceResult:
    chunk_id: str
    doc_id: str
    citation_key: str
    source_page: str
    chunk_manifest: str
    parsed_markdown: str
    section_anchor: str
    equation_ids: list[str]
    route: str
    original_pdf: str
    original_tex: str | None
    text: str


def _resolve_rag_path(rag_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else rag_dir / path


def _rel(path: Path, rag_dir: Path) -> str:
    try:
        return path.resolve().relative_to(rag_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    return records


def _find_source_page(rag_dir: Path, citation_key: str, chunk_manifest: Path) -> Path | None:
    direct = rag_dir / "summary" / "sources" / f"{citation_key}.md"
    if direct.exists():
        return direct
    target_rel = _rel(chunk_manifest, rag_dir)
    for page in (rag_dir / "summary" / "sources").glob("*.md"):
        fm, _ = read_frontmatter(page)
        if fm.get("chunk_manifest") == target_rel:
            return page
    return None


def trace_chunk(rag_dir: Path, chunk_id: str) -> TraceResult | None:
    chunks_dir = rag_dir / "reference" / "chunks"
    if not chunks_dir.is_dir():
        return None
    for chunk_path in chunks_dir.glob("*.jsonl"):
        for record in _load_jsonl(chunk_path):
            if record.get("chunk_id") != chunk_id:
                continue
            doc_id = str(record.get("doc_id", ""))
            citation_key = str(record.get("citation_key", ""))
            manifest_path = rag_dir / "reference" / "parsed" / f"{chunk_path.stem}.manifest.json"
            manifest: dict[str, Any] = {}
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source_page = _find_source_page(rag_dir, citation_key, chunk_path)
            parsed_markdown = str(manifest.get("parsed_markdown", ""))
            return TraceResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                citation_key=citation_key,
                source_page=_rel(source_page, rag_dir) if source_page else "",
                chunk_manifest=_rel(chunk_path, rag_dir),
                parsed_markdown=parsed_markdown,
                section_anchor=str(record.get("section_anchor", "")),
                equation_ids=[str(v) for v in record.get("equation_ids", [])],
                route=str(record.get("source_type", "")),
                original_pdf=str(manifest.get("original_pdf", "")),
                original_tex=manifest.get("original_tex"),
                text=str(record.get("text", "")),
            )
    return None


def format_trace(trace: TraceResult) -> str:
    lines = [
        f"chunk_id: {trace.chunk_id}",
        f"doc_id: {trace.doc_id}",
        f"citation_key: {trace.citation_key}",
        f"source_page: {trace.source_page or '<none>'}",
        f"chunk_manifest: {trace.chunk_manifest}",
        f"parsed_markdown: {trace.parsed_markdown}",
        f"section_anchor: {trace.section_anchor}",
        f"equation_ids: {', '.join(trace.equation_ids) if trace.equation_ids else '<none>'}",
        f"route: {trace.route}",
        f"original_pdf: {trace.original_pdf or '<none>'}",
        f"original_tex: {trace.original_tex or '<none>'}",
        "",
        "--- chunk text ---",
        trace.text,
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace DARW evidence chunks")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--chunk-id", required=True)
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    trace = trace_chunk(rag_dir, args.chunk_id)
    if trace is None:
        print(f"chunk not found: {args.chunk_id}")
        return 1
    print(format_trace(trace))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
