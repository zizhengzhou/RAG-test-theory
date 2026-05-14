"""Build structured AI context packs from RAG source pages and evidence chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bib_parser import parse_bibtex_file, render_bibtex
from common import read_frontmatter
from chunker import classify_section_type
from search_evidence import LOW_QUALITY_SECTION_TYPES, SearchHit, search_chunks


DEFAULT_BUDGET_TOKENS = 2500
DEFAULT_MAX_CHARS_PER_CHUNK = 900


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


def _source_summary(source_page: dict[str, Any]) -> dict[str, Any]:
    fm = source_page.get("frontmatter", {})
    source = fm.get("source", {}) if isinstance(fm, dict) else {}
    identifiers = fm.get("identifiers", {}) if isinstance(fm, dict) else {}
    return {
        "citation_key": source_page.get("citation_key", ""),
        "path": source_page.get("path", ""),
        "title": source.get("title", "") if isinstance(source, dict) else "",
        "year": source.get("year", "") if isinstance(source, dict) else "",
        "source_type": source.get("source_type", "") if isinstance(source, dict) else "",
        "primary_evidence": source.get("primary_evidence", "") if isinstance(source, dict) else "",
        "identifiers": identifiers if isinstance(identifiers, dict) else {},
        "metadata_only": bool(source_page.get("metadata_only")),
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


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars)].rstrip() + "..."


def _chunk_to_dict(hit: SearchHit, *, max_chars: int | None = None) -> dict[str, Any]:
    text = hit.text if max_chars is None else _truncate(hit.text, max_chars)
    return {
        "chunk_id": hit.chunk_id,
        "citation_key": hit.citation_key,
        "doc_id": hit.doc_id,
        "source_page": hit.source_page,
        "parsed_markdown": f"reference/parsed/{hit.doc_id.replace(':', '_').replace('/', '_')}.md",
        "section_anchor": hit.section_anchor,
        "section_title": hit.section_title,
        "section_type": hit.section_type,
        "score": hit.score,
        "raw_score": hit.raw_score,
        "route": hit.route,
        "equation_ids": hit.equation_ids,
        "text": text,
        "snippet": _truncate(hit.text, min(max_chars or 500, 500)),
    }


def _load_chunks_for_key(
    rag_dir: Path,
    key: str,
    *,
    include_low_quality: bool = False,
    max_chars: int | None = None,
) -> list[dict[str, Any]]:
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
                section_type = str(record.get("section_type") or classify_section_type(str(record.get("section_title", "")), str(record.get("text", ""))))
                if not include_low_quality and section_type in LOW_QUALITY_SECTION_TYPES:
                    continue
                text = str(record.get("text", ""))
                records.append(
                    {
                        "chunk_id": record.get("chunk_id", ""),
                        "citation_key": key,
                        "doc_id": record.get("doc_id", ""),
                        "source_page": f"summary/sources/{key}.md",
                        "parsed_markdown": f"reference/parsed/{str(record.get('doc_id', '')).replace(':', '_').replace('/', '_')}.md",
                        "section_anchor": record.get("section_anchor", ""),
                        "section_title": record.get("section_title", ""),
                        "section_type": section_type,
                        "score": 1.0,
                        "raw_score": 1.0,
                        "route": record.get("source_type", ""),
                        "equation_ids": record.get("equation_ids", []),
                        "text": text if max_chars is None else _truncate(text, max_chars),
                        "snippet": _truncate(text, min(max_chars or 500, 500)),
                    }
                )
    return records


def _compact_bib_entry(entry: dict[str, str]) -> dict[str, str]:
    return {
        "citation_key": entry.get("ID", ""),
        "title": entry.get("title", ""),
        "author": entry.get("author", ""),
        "year": entry.get("year") or entry.get("date", ""),
        "doi": entry.get("doi", ""),
        "eprint": entry.get("eprint", ""),
    }


def _fit_budget(pack: dict[str, Any], budget_tokens: int) -> tuple[dict[str, Any], list[str]]:
    budget_chars = max(budget_tokens * 4, 800)
    encoded = json.dumps(pack, ensure_ascii=False)
    if len(encoded) <= budget_chars:
        return pack, []

    gaps: list[str] = [f"context_budget_exceeded: compact pack trimmed to about {budget_tokens} tokens"]
    evidence = list(pack.get("evidence_chunks", []))
    while evidence and len(json.dumps({**pack, "evidence_chunks": evidence}, ensure_ascii=False)) > budget_chars:
        evidence.pop()
    if not evidence and pack.get("evidence_chunks"):
        first = dict(pack["evidence_chunks"][0])
        allowance = max(200, budget_chars - 1000)
        first["text"] = _truncate(str(first.get("text", "")), allowance)
        first["snippet"] = _truncate(str(first.get("snippet", "")), min(allowance, 500))
        evidence = [first]
    pack["evidence_chunks"] = evidence
    return pack, gaps


def build_context_pack(
    rag_dir: Path,
    *,
    query: str = "",
    key: str = "",
    top_k: int = 8,
    profile: str = "compact",
    budget_tokens: int = DEFAULT_BUDGET_TOKENS,
    max_chars_per_chunk: int = DEFAULT_MAX_CHARS_PER_CHUNK,
    include_low_quality: bool = False,
) -> dict[str, Any]:
    entries = _entry_by_key(rag_dir)
    hits: list[dict[str, Any]] = []
    keys: list[str] = []
    if profile not in {"compact", "full"}:
        raise ValueError("profile must be compact or full")
    if key:
        keys = [key]
        hits = _load_chunks_for_key(
            rag_dir,
            key,
            include_low_quality=include_low_quality,
            max_chars=max_chars_per_chunk if profile == "compact" else None,
        )[:top_k]
    elif query:
        search_hits = search_chunks(rag_dir, query, top_k=top_k, include_low_quality=include_low_quality)
        hits = [
            _chunk_to_dict(hit, max_chars=max_chars_per_chunk if profile == "compact" else None)
            for hit in search_hits
        ]
        keys = []
        for hit in search_hits:
            if hit.citation_key and hit.citation_key not in keys:
                keys.append(hit.citation_key)
    else:
        raise ValueError("provide --query or --key")

    source_pages = [page for candidate_key in keys if (page := _source_page(rag_dir, candidate_key))]
    if profile == "full":
        packed_source_pages = source_pages
        bib_entries = [
            {
                "citation_key": candidate_key,
                "bibtex": render_bibtex(entries[candidate_key]),
                "entry": entries[candidate_key],
            }
            for candidate_key in keys
            if candidate_key in entries
        ]
    else:
        packed_source_pages = [_source_summary(page) for page in source_pages]
        bib_entries = [_compact_bib_entry(entries[candidate_key]) for candidate_key in keys if candidate_key in entries]
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

    pack = {
        "query": query,
        "key": key,
        "wiki_context": graph_edges,
        "source_pages": packed_source_pages,
        "evidence_chunks": hits,
        "bib_entries": bib_entries,
        "graph_edges": graph_edges,
        "gaps": gaps,
        "provenance": {
            "rag_dir": str(rag_dir),
            "top_k": top_k,
            "mode": "key" if key else "query",
            "profile": profile,
            "budget_tokens": budget_tokens if profile == "compact" else None,
            "include_low_quality": include_low_quality,
        },
    }
    if profile == "compact":
        pack, budget_gaps = _fit_budget(pack, budget_tokens)
        pack["gaps"] = gaps + budget_gaps
    return pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a structured RAG context pack")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", default="")
    parser.add_argument("--key", default="")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--profile", choices=["compact", "full"], default="compact")
    parser.add_argument("--budget-tokens", type=int, default=DEFAULT_BUDGET_TOKENS)
    parser.add_argument("--max-chars-per-chunk", type=int, default=DEFAULT_MAX_CHARS_PER_CHUNK)
    parser.add_argument("--include-low-quality", action="store_true", help="include references and metadata sections")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    try:
        pack = build_context_pack(
            rag_dir,
            query=args.query,
            key=args.key,
            top_k=args.top_k,
            profile=args.profile,
            budget_tokens=args.budget_tokens,
            max_chars_per_chunk=args.max_chars_per_chunk,
            include_low_quality=args.include_low_quality,
        )
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
