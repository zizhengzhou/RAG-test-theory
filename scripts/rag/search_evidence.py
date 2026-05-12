"""Search DARW evidence chunks with TF-IDF scoring and return ranked provenance."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from darw_schema import chunk_manifest_path


@dataclass
class SearchHit:
    chunk_id: str
    doc_id: str
    citation_key: str
    source_page: str
    section_title: str
    section_anchor: str
    route: str
    text: str
    score: float
    equation_ids: list[str]


def _load_all_chunks(rag_dir: Path) -> list[dict[str, Any]]:
    chunk_dir = rag_dir / "reference" / "chunks"
    if not chunk_dir.is_dir():
        return []
    all_chunks: list[dict[str, Any]] = []
    for path in sorted(chunk_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                all_chunks.append(json.loads(line))
    return all_chunks


def _source_page_path(rag_dir: Path, citation_key: str) -> str:
    sp = rag_dir / "summary" / "sources" / f"{citation_key}.md"
    if sp.exists():
        return f"summary/sources/{citation_key}.md"
    return ""


def search_chunks(rag_dir: Path, query: str, *, top_k: int = 10) -> list[SearchHit]:
    chunks = _load_all_chunks(rag_dir)
    if not chunks:
        return []

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [c.get("text", "") for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    hits: list[SearchHit] = []
    seen_chunk_ids: set[str] = set()
    for idx, score in ranked:
        if score <= 0 or len(hits) >= top_k:
            break
        chunk = chunks[idx]
        chunk_id = chunk.get("chunk_id", "")
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        citation_key = chunk.get("citation_key", "")
        hits.append(
            SearchHit(
                chunk_id=chunk_id,
                doc_id=chunk.get("doc_id", ""),
                citation_key=citation_key,
                source_page=_source_page_path(rag_dir, citation_key),
                section_title=chunk.get("section_title", ""),
                section_anchor=chunk.get("section_anchor", ""),
                route=chunk.get("source_type", ""),
                text=chunk.get("text", ""),
                score=round(float(score), 4),
                equation_ids=chunk.get("equation_ids", []),
            )
        )
    return hits


def format_hits(hits: list[SearchHit], *, show_text: bool = True) -> str:
    if not hits:
        return "No evidence chunks found."

    lines: list[str] = []
    for i, hit in enumerate(hits, 1):
        lines.append(f"--- result {i} (score={hit.score:.4f}) ---")
        lines.append(f"chunk_id: {hit.chunk_id}")
        lines.append(f"doc_id: {hit.doc_id}")
        lines.append(f"citation: {hit.citation_key}")
        lines.append(f"source_page: {hit.source_page or 'none'}")
        lines.append(f"section: {hit.section_anchor} ({hit.section_title})")
        lines.append(f"route: {hit.route}")
        if hit.equation_ids:
            lines.append(f"equations: {', '.join(hit.equation_ids)}")
        if show_text:
            lines.append(f"text: {hit.text[:500]}")
            if len(hit.text) > 500:
                lines.append("  ...")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search DARW evidence chunks")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("query", nargs="*")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--no-text", action="store_true", help="hide chunk text in output")
    args = parser.parse_args()

    query = " ".join(args.query) if args.query else ""
    if not query.strip():
        print("Error: query required")
        return 1

    rag_dir = Path(args.rag_dir).resolve()
    hits = search_chunks(rag_dir, query, top_k=args.top_k)
    print(format_hits(hits, show_text=not args.no_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
