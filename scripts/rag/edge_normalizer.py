"""Normalize raw extracted terms into canonical edge entities via physh_mapper.

Accepts a list of free-text terms (from source page analysis, LLM output,
or manual curation) and returns normalized DARW edge entries suitable for
writing into source page ``edges`` blocks.

Does NOT hardcode physics terms — all normalization flows through
vocabulary.md and the PhySH API.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from darw_schema import EDGE_CATEGORIES
from physh_mapper import resolve_term, NormalizedEntity


def _guess_category(label: str, entity_category: str) -> str:
    """Return a valid DARW edge category, preferring the entity's own category."""
    if entity_category in EDGE_CATEGORIES:
        return entity_category
    lower = label.lower()
    heuristics = {
        "research_areas": [],
        "physical_systems": ["detector", "crystal", "resonator", "wafer", "film", "sensor"],
        "techniques": ["spectroscopy", "microscopy", "lithography", "deposition", "measurement",
                       "fabrication", "analysis", "imaging", "noise", "calibration"],
        "properties": ["conductivity", "temperature", "density", "frequency", "resistance",
                       "noise", "loss", "efficiency", "resolution", "threshold"],
        "models": ["model", "theory", "framework", "simulation", "dft", "monte carlo"],
        "observables": ["cross section", "rate", "spectrum", "signal", "background"],
        "datasets": ["dataset", "catalog", "survey", "database"],
        "experiments": ["experiment", "facility", "telescope", "collider", "observatory"],
    }
    for cat, keywords in heuristics.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return "research_areas"


def normalize_term(term: str, rag_dir: Path, *, online: bool = True) -> dict:
    """Normalize a single raw term to a DARW edge entry dict.

    Returns a dict with canonical_id, label, local_aliases, confidence,
    and the NormalizedEntity for inspection.
    """
    vocab_path = rag_dir / "vocabulary.md"
    cache_dir = rag_dir / "reference"
    entity = resolve_term(term, vocab_path, cache_dir, online=online)

    category = _guess_category(entity.label, entity.category)
    if entity.source == "unresolved":
        confidence = 0.0
    elif entity.source == "local_cache":
        confidence = 0.9
    elif entity.source == "physh_api" and entity.match_score:
        confidence = entity.match_score
    else:
        confidence = 1.0

    entry = {
        "canonical_id": entity.canonical_id,
        "label": entity.label,
        "local_aliases": [entity.raw_term] if entity.raw_term.lower() != entity.label.lower() else [],
        "confidence": confidence,
    }
    entry["_entity"] = entity
    entry["_category"] = category
    return entry


def normalize_terms(terms: list[str], rag_dir: Path, *, online: bool = True) -> list[dict]:
    """Batch-normalize a list of raw terms. Returns edge-ready dicts."""
    return [normalize_term(t, rag_dir, online=online) for t in terms]


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize raw terms to canonical edge entries")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--term", action="append", default=None, help="Term to normalize (repeatable)")
    parser.add_argument("--terms-file", default="", help="File with one term per line")
    parser.add_argument("--offline", action="store_true", help="Skip PhySH API queries")
    parser.add_argument("--json", action="store_true", help="Output JSON for machine consumption")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    online = not args.offline

    terms: list[str] = []
    if args.term:
        terms = args.term
    elif args.terms_file:
        raw = Path(args.terms_file).read_text(encoding="utf-8")
        terms = [line.strip() for line in raw.splitlines() if line.strip()]
    else:
        print("provide --term or --terms-file")
        return 1

    results = normalize_terms(terms, rag_dir, online=online)

    if args.json:
        import json
        output = []
        for r in results:
            output.append({
                "canonical_id": r["canonical_id"],
                "label": r["label"],
                "local_aliases": r["local_aliases"],
                "confidence": r["confidence"],
                "category": r["_category"],
                "source": r["_entity"].source,
                "needs_review": r["_entity"].needs_review,
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for r in results:
            entity = r["_entity"]
            print(f"\n{r['canonical_id']}")
            print(f"  label:      {r['label']}")
            print(f"  category:   {r['_category']}")
            print(f"  confidence: {r['confidence']}")
            print(f"  source:     {entity.source}")
            print(f"  needs_review: {entity.needs_review}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
