"""Search DARW evidence chunks with TF-IDF scoring and return ranked provenance."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chunker import classify_section_type


LOW_QUALITY_SECTION_TYPES = {"references", "metadata"}
SECTION_TYPE_WEIGHTS = {
    "abstract": 1.25,
    "results": 1.25,
    "conclusion": 1.2,
    "discussion": 1.15,
    "methods": 1.05,
    "introduction": 1.0,
    "body": 1.0,
    "appendix": 0.8,
    "metadata": 0.2,
    "references": 0.05,
}
TOKEN_RE = re.compile(r"[\w.+-]+", re.UNICODE)


@dataclass
class SearchHit:
    chunk_id: str
    doc_id: str
    citation_key: str
    source_page: str
    section_title: str
    section_anchor: str
    section_type: str
    route: str
    text: str
    score: float
    raw_score: float
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


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token.strip("._-")) >= 2]


def _bm25_scores(texts: list[str], query: str) -> list[float]:
    tokenized_docs = [_tokenize(text) for text in texts]
    query_terms = _tokenize(query)
    if not tokenized_docs or not query_terms:
        return [0.0 for _ in texts]

    doc_freq: Counter[str] = Counter()
    doc_counters: list[Counter[str]] = []
    for tokens in tokenized_docs:
        counter = Counter(tokens)
        doc_counters.append(counter)
        doc_freq.update(counter.keys())

    n_docs = len(tokenized_docs)
    avgdl = sum(len(tokens) for tokens in tokenized_docs) / max(n_docs, 1)
    k1 = 1.5
    b = 0.75
    scores: list[float] = []
    for tokens, counter in zip(tokenized_docs, doc_counters):
        doc_len = max(len(tokens), 1)
        score = 0.0
        for term in query_terms:
            freq = counter.get(term, 0)
            if not freq:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1 - b + b * doc_len / max(avgdl, 1))
            score += idf * (freq * (k1 + 1)) / denom
        scores.append(score)
    return scores


def _normalize_scores(scores: list[float]) -> list[float]:
    max_score = max(scores, default=0.0)
    if max_score <= 0:
        return [0.0 for _ in scores]
    return [score / max_score for score in scores]


def _section_type(chunk: dict[str, Any]) -> str:
    existing = str(chunk.get("section_type", "")).strip()
    if existing:
        return existing
    return classify_section_type(str(chunk.get("section_title", "")), str(chunk.get("text", "")))


def _section_weight(section_type: str) -> float:
    return SECTION_TYPE_WEIGHTS.get(section_type, 1.0)


def search_chunks(
    rag_dir: Path,
    query: str,
    *,
    top_k: int = 10,
    include_low_quality: bool = False,
    min_score: float = 0.05,
) -> list[SearchHit]:
    chunks = _load_all_chunks(rag_dir)
    if not chunks:
        return []

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [c.get("text", "") for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(texts)
    query_vec = vectorizer.transform([query])
    tfidf_scores = cosine_similarity(query_vec, tfidf_matrix).flatten().tolist()
    bm25_scores = _normalize_scores(_bm25_scores(texts, query))
    combined_scores: list[tuple[int, float, float]] = []
    query_lower = query.lower().strip()
    for idx, chunk in enumerate(chunks):
        section_type = _section_type(chunk)
        raw_score = (0.55 * float(tfidf_scores[idx])) + (0.45 * bm25_scores[idx])
        if query_lower and query_lower in str(chunk.get("text", "")).lower():
            raw_score += 0.05
        weighted_score = raw_score * _section_weight(section_type)
        combined_scores.append((idx, raw_score, weighted_score))

    ranked = sorted(combined_scores, key=lambda x: x[2], reverse=True)
    hits: list[SearchHit] = []
    seen_chunk_ids: set[str] = set()
    for idx, raw_score, score in ranked:
        if score <= 0 or len(hits) >= top_k:
            break
        chunk = chunks[idx]
        section_type = _section_type(chunk)
        if not include_low_quality and section_type in LOW_QUALITY_SECTION_TYPES:
            continue
        if not include_low_quality and score < min_score:
            continue
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
                section_type=section_type,
                route=chunk.get("source_type", ""),
                text=chunk.get("text", ""),
                score=round(float(score), 4),
                raw_score=round(float(raw_score), 4),
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
        lines.append(f"section_type: {hit.section_type}")
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
    parser.add_argument("--include-low-quality", action="store_true", help="include references and metadata sections")
    parser.add_argument("--min-score", type=float, default=0.05)
    args = parser.parse_args()

    query = " ".join(args.query) if args.query else ""
    if not query.strip():
        print("Error: query required")
        return 1

    rag_dir = Path(args.rag_dir).resolve()
    hits = search_chunks(
        rag_dir,
        query,
        top_k=args.top_k,
        include_low_quality=args.include_low_quality,
        min_score=args.min_score,
    )
    print(format_hits(hits, show_text=not args.no_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
