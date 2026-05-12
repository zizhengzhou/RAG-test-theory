"""Extract candidate vocabulary terms from evidence chunks and source metadata."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from common import read_frontmatter
from darw_schema import EDGE_CATEGORIES
from edge_normalizer import normalize_terms

STOPWORDS = {
    "abstract", "introduction", "method", "methods", "result", "results", "discussion",
    "conclusion", "figure", "table", "using", "based", "shown", "paper", "study", "analysis",
    "measurement", "measurements", "data", "model", "models", "effect", "effects", "system",
    "systems", "sample", "samples", "experiment", "experiments", "background", "source",
}
TERM_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9+-]{2,}|[a-z][a-z0-9+-]{3,})(?:[\s/-]+(?:[A-Z][A-Za-z0-9+-]{2,}|[a-z][a-z0-9+-]{3,})){0,3}\b")


def _load_chunks(rag_dir: Path, citation_key: str = "") -> list[dict]:
    chunks_dir = rag_dir / "reference" / "chunks"
    if not chunks_dir.is_dir():
        return []
    records: list[dict] = []
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if citation_key and rec.get("citation_key") != citation_key:
                continue
            records.append(rec)
    return records


def _metadata_text(rag_dir: Path, citation_key: str = "") -> str:
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return ""
    parts: list[str] = []
    pages = [sources_dir / f"{citation_key}.md"] if citation_key else sorted(sources_dir.glob("*.md"))
    for page in pages:
        if not page.exists():
            continue
        fm, _ = read_frontmatter(page)
        source = fm.get("source")
        if not isinstance(source, dict):
            continue
        parts.append(str(source.get("title", "")))
        parts.append(str(source.get("abstract", "")))
    return "\n".join(parts)


def _candidate_variants(term: str) -> list[str]:
    parts = term.split()
    variants = [term]
    if len(parts) > 1:
        for start in range(len(parts)):
            for end in range(len(parts), start + 1, -1):
                phrase = " ".join(parts[start:end])
                if phrase != term and len(phrase) >= 4:
                    variants.append(phrase)
    seen: set[str] = set()
    result: list[str] = []
    for variant in variants:
        lower = variant.lower()
        if lower in seen or lower in STOPWORDS:
            continue
        if any(part.lower() in STOPWORDS for part in variant.split()):
            continue
        seen.add(lower)
        result.append(variant)
    return result


def extract_candidate_terms(rag_dir: Path, *, citation_key: str = "", limit: int = 40) -> list[dict]:
    texts = [str(chunk.get("section_title", "")) + "\n" + str(chunk.get("text", "")) for chunk in _load_chunks(rag_dir, citation_key)]
    texts.append(_metadata_text(rag_dir, citation_key))
    counter: Counter[str] = Counter()
    for text in texts:
        for match in TERM_RE.finditer(text):
            term = re.sub(r"\s+", " ", match.group(0)).strip(" -/")
            if len(term) < 4:
                continue
            for variant in _candidate_variants(term):
                counter[variant] += 1
    return [{"term": term, "count": count} for term, count in counter.most_common(limit)]


def suggest_edges(rag_dir: Path, *, citation_key: str = "", limit: int = 20, online: bool = False) -> dict[str, list[dict]]:
    candidates = extract_candidate_terms(rag_dir, citation_key=citation_key, limit=limit)
    normalized = normalize_terms([c["term"] for c in candidates], rag_dir, online=online) if candidates else []
    counts = {c["term"].lower(): c["count"] for c in candidates}
    grouped: dict[str, list[dict]] = {cat: [] for cat in EDGE_CATEGORIES}
    seen: set[str] = set()
    for item in normalized:
        cid = item["canonical_id"]
        if cid in seen:
            continue
        seen.add(cid)
        category = item.get("_category", "research_areas")
        entry = {
            "canonical_id": cid,
            "label": item["label"],
            "local_aliases": item["local_aliases"],
            "confidence": item["confidence"],
            "count": counts.get(str(item["_entity"].raw_term).lower(), 1),
            "needs_review": bool(item["_entity"].needs_review),
        }
        grouped.setdefault(category if category in EDGE_CATEGORIES else "research_areas", []).append(entry)
    return {cat: values for cat, values in grouped.items() if values}


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest vocabulary/edge candidates from evidence chunks")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="", help="Limit to one citation key")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--online", action="store_true", help="Allow PhySH API lookup")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    suggestions = suggest_edges(rag_dir, citation_key=args.key, limit=args.limit, online=args.online)
    if args.json:
        print(json.dumps(suggestions, indent=2, ensure_ascii=False))
        return 0
    if not suggestions:
        print("No candidate terms found. Generate evidence chunks first or lower filtering expectations.")
        return 0
    for category, entries in suggestions.items():
        print(f"## {category}")
        for entry in entries:
            print(f"- {entry['canonical_id']} | {entry['label']} | confidence={entry['confidence']} count={entry['count']}")
    print("\n[dry-run] suggestions only; review before writing vocabulary.md or source edges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
