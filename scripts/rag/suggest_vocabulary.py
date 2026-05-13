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
    "used", "use", "with", "this", "report", "reports", "reported", "compare", "compares",
    "compared", "observable", "observables", "article", "articles", "which", "there", "interest",
    "region", "july", "phys", "lett", "picture", "pictures", "omitted", "intentionally",
    "copyright", "published", "received", "accepted", "license", "author", "authors",
    "where", "function", "found", "events", "moreover", "start", "hours", "nature",
    "letters", "publishing", "group", "journal", "review", "caption", "assets", "refer",
    "approx", "displaystyle", "langle", "rangle", "parsed", "pdf", "text", "domain",
    "domains", "obtained", "from", "have", "been", "the", "and", "for", "during",
    "between", "whereas", "however", "while", "respectively", "approximately",
    "expected", "predicted", "included", "described", "observed", "measured",
    "about", "addition", "measure", "shows", "total", "factor", "function",
    "order", "number", "similarly",
}
GENERIC_SINGLE_WORDS = STOPWORDS | {
    "energy", "signal", "physics", "impact", "uncertainty", "counts", "device",
    "nature", "october", "january", "february", "march", "april", "june",
    "august", "september", "november", "december",
}
DOMAIN_TOKENS = {
    "background", "bolometer", "calibration", "cawo4", "cevns", "coherent",
    "conus", "cooper", "cryogenic", "dark", "detector", "detectors", "elastic",
    "electron", "field", "flux", "gamma", "getter", "graphene", "lifetime",
    "liquid", "magnetic", "matter", "microwave", "muon", "muons", "neutrino",
    "neutrinos", "nuclear", "nucleus", "outgassing", "phonon", "purification",
    "reactor", "resonator", "scattering", "shield", "superconducting",
    "threshold", "xenon",
}
GENERIC_EDGE_TOKENS = {
    "a", "an", "the", "each", "every", "other", "another", "this", "that",
    "these", "those", "first", "second", "third", "former", "latter",
    "future", "current", "previous", "next", "technical", "physics",
    "new", "old", "single", "double", "triple", "three",
}
GENERIC_TRAILING_TOKENS = {
    "detector", "detectors", "experiment", "experiments", "measurement",
    "measurements", "signal", "signals", "system", "systems", "setup",
}
SECTION_TITLE_BLACKLIST = {
    "abstract", "introduction", "results", "discussion", "conclusion",
    "references", "acknowledgments", "acknowledgements", "appendix",
    "technical run", "physics run",
}
MIN_TERM_COUNT = 2
MAX_SINGLE_TOKEN_COUNT = 1
TERM_RE = re.compile(r"\b(?:[A-Z][A-Za-z0-9+-]{2,}|[a-z][a-z0-9+-]{3,})(?:[\s/-]+(?:[A-Z][A-Za-z0-9+-]{2,}|[a-z][a-z0-9+-]{3,})){0,4}\b")


def _load_chunks(rag_dir: Path, citation_key: str = "") -> list[dict]:
    chunks_dir = rag_dir / "reference" / "chunks"
    if not chunks_dir.is_dir():
        return []
    records: list[dict] = []
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.lstrip("\ufeff")
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
        variant_parts = variant.split()
        while len(variant_parts) > 1 and variant_parts[0].lower() in GENERIC_EDGE_TOKENS:
            variant_parts = variant_parts[1:]
        while len(variant_parts) > 1 and variant_parts[-1].lower() in (GENERIC_EDGE_TOKENS | GENERIC_TRAILING_TOKENS):
            variant_parts = variant_parts[:-1]
        variant = " ".join(variant_parts).strip()
        if not variant:
            continue
        lower = variant.lower()
        if lower in seen or lower in STOPWORDS:
            continue
        if any(part.lower() in STOPWORDS for part in variant.split()):
            continue
        seen.add(lower)
        result.append(variant)
    return result


def _term_tokens(term: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]+", term)]


def _has_domain_signal(term: str) -> bool:
    tokens = _term_tokens(term)
    return any(token in DOMAIN_TOKENS for token in tokens)


def _looks_like_acronym(term: str) -> bool:
    compact = re.sub(r"[^A-Za-z0-9]", "", term)
    return 2 <= len(compact) <= 12 and compact.upper() == compact and any(ch.isalpha() for ch in compact)


def _quality_score(term: str, count: int) -> float:
    tokens = _term_tokens(term)
    token_count = len(tokens)
    score = float(count)
    if token_count >= 2:
        score += 8.0 + min(token_count, 4)
    if _has_domain_signal(term):
        score += 10.0
    if _looks_like_acronym(term):
        score += 5.0
    if token_count == 1:
        score -= 4.0
    return score


def _keep_section_title(title: str) -> bool:
    normalized = re.sub(r"\s+", " ", title.strip()).lower()
    if not normalized or normalized in SECTION_TITLE_BLACKLIST:
        return False
    tokens = _term_tokens(normalized)
    if not tokens:
        return False
    if normalized.endswith(" run"):
        return False
    return _has_domain_signal(normalized) or _looks_like_acronym(normalized)


def _is_fragment_of_longer(term: str, selected_terms: list[str]) -> bool:
    term_tokens = _term_tokens(term)
    if len(term_tokens) < 2:
        return False
    joined = " ".join(term_tokens)
    for selected in selected_terms:
        selected_tokens = _term_tokens(selected)
        if len(selected_tokens) <= len(term_tokens):
            continue
        haystack = " ".join(selected_tokens)
        if joined in haystack:
            return True
    return False


def _is_useful_candidate(term: str, count: int) -> bool:
    lower = term.lower()
    parts = lower.split()
    if lower in STOPWORDS or any(part in STOPWORDS for part in parts):
        return False
    if re.search(r"\b(?:hep|astro|nucl|cond-mat|quant-ph)-[a-z]{2}\b", lower):
        return False
    if len(parts) == 1 and count <= MAX_SINGLE_TOKEN_COUNT:
        return False
    if len(parts) == 1:
        if lower in GENERIC_SINGLE_WORDS:
            return False
        if not (_has_domain_signal(term) or _looks_like_acronym(term)):
            return False
    if count < MIN_TERM_COUNT and len(parts) < 2:
        return False
    if len(term) < 5:
        return False
    if not (_has_domain_signal(term) or len(parts) >= 2 or _looks_like_acronym(term)):
        return False
    return True


def extract_candidate_terms(rag_dir: Path, *, citation_key: str = "", limit: int = 40) -> list[dict]:
    texts: list[str] = []
    for chunk in _load_chunks(rag_dir, citation_key):
        # Keep fields separate so the regex cannot join a section title and the
        # first words of the body into one artificial term.
        section_title = str(chunk.get("section_title", ""))
        if _keep_section_title(section_title):
            texts.append(section_title)
        texts.append(str(chunk.get("text", "")))
    texts.append(_metadata_text(rag_dir, citation_key))
    counter: Counter[str] = Counter()
    for text in texts:
        for match in TERM_RE.finditer(text):
            term = re.sub(r"\s+", " ", match.group(0)).strip(" -/")
            if len(term) < 4:
                continue
            for variant in _candidate_variants(term):
                counter[variant] += 1
    terms: list[dict] = []
    ranked = sorted(counter.items(), key=lambda item: (_quality_score(item[0], item[1]), item[1], len(item[0])), reverse=True)
    selected_terms: list[str] = []
    for term, count in ranked:
        if not _is_useful_candidate(term, count):
            continue
        if _is_fragment_of_longer(term, selected_terms):
            continue
        terms.append({"term": term, "count": count})
        selected_terms.append(term)
        if len(terms) >= limit:
            break
    return terms


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
