"""Build structured AI context packs from RAG source pages and evidence chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bib_parser import parse_bibtex_file, render_bibtex
from common import read_frontmatter
from search_evidence import SearchHit, search_chunks


def _rel(path: Path, rag_dir: Path) -> str:
    try:
        return path.resolve().relative_to(rag_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _entry_by_key(rag_dir: Path) -> dict[str, dict[str, str]]:
    return {entry.get("ID", ""): entry for entry in _load_entries(rag_dir)}


def _source_page(rag_dir: Path, key: str) -> dict[str, Any] | None:
    path = rag_dir / "summary" / "sources" / f"{key}.md"
    if not path.exists():
        return None
    fm, body = read_frontmatter(path)
    return {
        "citation_key": key,
        "path": _rel(path, rag_dir),
        "frontmatter": fm,
        "body": body.strip(),
        "metadata_only": "_To be filled._" in body or not body.strip(),
    }


def _edge_pages_for_source(rag_dir: Path, source_page: dict[str, Any]) -> list[dict[str, str]]:
    fm = source_page.get("frontmatter", {})
    edges = fm.get("edges", {}) if isinstance(fm, dict) else {}
    pages: list[dict[str, str]] = []
    if not isinstance(edges, dict):
        return pages
    for category, entries in edges.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            cid = entry.get("canonical_id", "") if isinstance(entry, dict) else str(entry)
            cid = str(cid).strip()
            if not cid:
                continue
            page = rag_dir / "summary" / category / f"{cid.replace(':', '_').replace('/', '_')}.md"
            if page.exists():
                pages.append({"category": category, "canonical_id": cid, "path": _rel(page, rag_dir)})
            else:
                pages.append({"category": category, "canonical_id": cid, "path": ""})
    return pages


def _chunk_to_dict(hit: SearchHit) -> dict[str, Any]:
    return {
        "chunk_id": hit.chunk_id,
        "citation_key": hit.citation_key,
        "doc_id": hit.doc_id,
        "source_page": hit.source_page,
        "parsed_markdown": f"reference/parsed/{hit.doc_id.replace(':', '_').replace('/', '_')}.md",
        "section_anchor": hit.section_anchor,
        "section_title": hit.section_title,
        "score": hit.score,
        "route": hit.route,
        "equation_ids": hit.equation_ids,
        "text": hit.text,
        "snippet": hit.text[:500],
    }


def _load_chunks_for_key(rag_dir: Path, key: str) -> list[dict[str, Any]]:
    chunks_dir = rag_dir / "reference" / "chunks"
    records: list[dict[str, Any]] = []
    if not chunks_dir.is_dir():
        return records
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("citation_key") == key:
                records.append(
                    {
                        "chunk_id": record.get("chunk_id", ""),
                        "citation_key": key,
                        "doc_id": record.get("doc_id", ""),
                        "source_page": f"summary/sources/{key}.md",
                        "parsed_markdown": f"reference/parsed/{str(record.get('doc_id', '')).replace(':', '_').replace('/', '_')}.md",
                        "section_anchor": record.get("section_anchor", ""),
                        "section_title": record.get("section_title", ""),
                        "score": 1.0,
                        "route": record.get("source_type", ""),
                        "equation_ids": record.get("equation_ids", []),
                        "text": record.get("text", ""),
                        "snippet": str(record.get("text", ""))[:500],
                    }
                )
    return records


def build_context_pack(rag_dir: Path, *, query: str = "", key: str = "", top_k: int = 8) -> dict[str, Any]:
    entries = _entry_by_key(rag_dir)
    hits: list[dict[str, Any]] = []
    keys: list[str] = []
    if key:
        keys = [key]
        hits = _load_chunks_for_key(rag_dir, key)[:top_k]
    elif query:
        search_hits = search_chunks(rag_dir, query, top_k=top_k)
        hits = [_chunk_to_dict(hit) for hit in search_hits]
        keys = []
        for hit in search_hits:
            if hit.citation_key and hit.citation_key not in keys:
                keys.append(hit.citation_key)
    else:
        raise ValueError("provide --query or --key")

    source_pages = [page for candidate_key in keys if (page := _source_page(rag_dir, candidate_key))]
    bib_entries = [
        {
            "citation_key": candidate_key,
            "bibtex": render_bibtex(entries[candidate_key]),
            "entry": entries[candidate_key],
        }
        for candidate_key in keys
        if candidate_key in entries
    ]
    graph_edges = [edge for page in source_pages for edge in _edge_pages_for_source(rag_dir, page)]
    gaps: list[str] = []
    if key and not hits:
        gaps.append(f"metadata_only: no evidence chunks for {key}")
    for candidate_key in keys:
        if candidate_key not in entries:
            gaps.append(f"missing BibTeX entry for {candidate_key}")
        if not (rag_dir / "summary" / "sources" / f"{candidate_key}.md").exists():
            gaps.append(f"missing source page for {candidate_key}")
    if query and not hits:
        gaps.append("no evidence chunks matched query")

    return {
        "query": query,
        "key": key,
        "wiki_context": graph_edges,
        "source_pages": source_pages,
        "evidence_chunks": hits,
        "bib_entries": bib_entries,
        "graph_edges": graph_edges,
        "gaps": gaps,
        "provenance": {
            "rag_dir": str(rag_dir),
            "top_k": top_k,
            "mode": "key" if key else "query",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a structured RAG context pack")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", default="")
    parser.add_argument("--key", default="")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    try:
        pack = build_context_pack(rag_dir, query=args.query, key=args.key, top_k=args.top_k)
    except ValueError as exc:
        print(str(exc))
        return 1
    if args.json:
        print(json.dumps(pack, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(pack, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
