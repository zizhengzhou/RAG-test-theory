"""Hybrid query scaffold over graph filters and evidence chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from context_pack import build_context_pack
from search_evidence import search_chunks


def query_hybrid(rag_dir: Path, query: str, *, top_k: int = 8) -> dict[str, Any]:
    hits = search_chunks(rag_dir, query, top_k=top_k)
    candidates = [
        {
            "chunk_id": hit.chunk_id,
            "citation_key": hit.citation_key,
            "doc_id": hit.doc_id,
            "score": hit.score,
            "source_page": hit.source_page,
            "section_anchor": hit.section_anchor,
        }
        for hit in hits
    ]
    pack = build_context_pack(rag_dir, query=query, top_k=top_k)
    gaps = list(pack.get("gaps", []))
    if not candidates:
        gaps.append("fallback TF-IDF found no evidence chunks")
    return {
        "query": query,
        "graph_filter": {"matched_edges": pack.get("graph_edges", [])},
        "answer_candidates": candidates,
        "evidence": pack.get("evidence_chunks", []),
        "gaps": gaps,
        "retrieval": {"mode": "tfidf-fallback", "top_k": top_k},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid RAG query scaffold")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = query_hybrid(Path(args.rag_dir).resolve(), args.query, top_k=args.top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
