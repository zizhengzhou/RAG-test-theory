"""Create deterministic DARW evidence chunks from parsed Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from darw_schema import CHUNK_SCHEMA_VERSION, chunk_manifest_path, safe_doc_id

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
EQUATION_RE = re.compile(r"\$\$(.*?)\$\$", re.DOTALL)


@dataclass(frozen=True)
class ChunkRecord:
    schema_version: str
    chunk_id: str
    doc_id: str
    citation_key: str
    source_type: str
    parser: str
    source_sha256: str
    section_title: str
    section_anchor: str
    chunk_index: int
    text: str
    contains_equation: bool
    equation_ids: list[str]
    page_start: int | None
    page_end: int | None
    char_start: int
    char_end: int
    edges: dict[str, list[str]]
    created_at: str


def stable_anchor(title: str) -> str:
    clean = title.strip().lower()
    clean = re.sub(r"[^\w\s-]", "", clean, flags=re.UNICODE)
    clean = re.sub(r"\s+", "-", clean).strip("-")
    return f"#{clean or 'section'}"


def _sections(text: str) -> list[tuple[str, str, int, int]]:
    """Split text into heading-aware sections via regex (preserves heading text for anchors)."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("Document", "#document", 0, len(text))]
    sections: list[tuple[str, str, int, int]] = []
    if matches[0].start() > 0 and text[: matches[0].start()].strip():
        sections.append(("Document", "#document", 0, matches[0].start()))
    for idx, match in enumerate(matches):
        title = match.group(2).strip().strip("#").strip()
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((title, stable_anchor(title), start, end))
    return sections


def _split_section(section_text: str, absolute_start: int, max_chars: int) -> list[tuple[str, int, int]]:
    """Split an oversized section into sentence-sized chunks via LlamaIndex."""
    if len(section_text) <= max_chars:
        return [(section_text.strip(), absolute_start, absolute_start + len(section_text))] if section_text.strip() else []

    from llama_index.core.node_parser import SentenceSplitter
    from llama_index.core.schema import Document

    doc = Document(text=section_text)
    splitter = SentenceSplitter(chunk_size=max_chars, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents([doc])

    chunks: list[tuple[str, int, int]] = []
    for node in nodes:
        if node.text.strip():
            s = absolute_start + (node.start_char_idx or 0)
            e = absolute_start + (node.end_char_idx or len(section_text))
            chunks.append((node.text.strip(), s, e))
    return chunks


def _equation_ids(text: str, section_anchor: str, chunk_index: int) -> list[str]:
    ids: list[str] = []
    safe_section = section_anchor.lstrip("#") or "section"
    for idx, _ in enumerate(EQUATION_RE.finditer(text), start=1):
        ids.append(f"eq-{safe_section}-{chunk_index:03d}-{idx:02d}")
    return ids


def _chunk_id(doc_id: str, section_anchor: str, chunk_index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{safe_doc_id(doc_id)}::{section_anchor.lstrip('#') or 'section'}::chunk-{chunk_index:03d}-{digest}"


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_chunks(manifest: dict[str, Any], parsed_text: str, *, max_chars: int = 1800) -> list[ChunkRecord]:
    doc_id = str(manifest.get("doc_id", ""))
    records: list[ChunkRecord] = []
    index = 0
    for title, anchor, start, end in _sections(parsed_text):
        section_text = parsed_text[start:end]
        for chunk_text, char_start, char_end in _split_section(section_text, start, max_chars):
            index += 1
            eq_ids = _equation_ids(chunk_text, anchor, index)
            records.append(
                ChunkRecord(
                    schema_version=CHUNK_SCHEMA_VERSION,
                    chunk_id=_chunk_id(doc_id, anchor, index, chunk_text),
                    doc_id=doc_id,
                    citation_key=str(manifest.get("citation_key", "")),
                    source_type=str(manifest.get("route", "")),
                    parser=str(manifest.get("parser", "")),
                    source_sha256=str(manifest.get("source_sha256", "")),
                    section_title=title,
                    section_anchor=anchor,
                    chunk_index=index,
                    text=chunk_text,
                    contains_equation=bool(eq_ids),
                    equation_ids=eq_ids,
                    page_start=None,
                    page_end=None,
                    char_start=char_start,
                    char_end=char_end,
                    edges={
                        "research_areas": [],
                        "physical_systems": [],
                        "techniques": [],
                        "properties": [],
                        "models": [],
                        "observables": [],
                        "datasets": [],
                        "experiments": [],
                    },
                    created_at=date.today().isoformat(),
                )
            )
    return records


def write_chunks(rag_dir: Path, manifest_path: Path, *, max_chars: int = 1800, dry_run: bool = False) -> Path:
    manifest = load_manifest(manifest_path)
    parsed_path = Path(str(manifest.get("parsed_markdown", "")))
    if not parsed_path.is_absolute():
        parsed_path = rag_dir / parsed_path
    parsed_text = parsed_path.read_text(encoding="utf-8")
    records = build_chunks(manifest, parsed_text, max_chars=max_chars)
    out_path = chunk_manifest_path(rag_dir, str(manifest.get("doc_id", "")))
    if dry_run:
        print(f"would write chunk manifest: {out_path} ({len(records)} chunks)")
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunk DARW parsed evidence Markdown")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--max-chars", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    out_path = write_chunks(rag_dir, Path(args.manifest).resolve(), max_chars=args.max_chars, dry_run=args.dry_run)
    print(f"chunk_manifest={out_path}")
    if args.dry_run:
        print("[dry-run] no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
