"""Map raw physics terms to PhySH / local vocabulary canonical IDs.

Queries the public APS PhySH REST API (https://physh.org) to resolve
concepts, falling back to the local vocabulary cache in RAG/vocabulary.md.

Usage::

    python scripts/rag/physh_mapper.py --term "coherent neutrino scattering"
    python scripts/rag/physh_mapper.py --terms-file terms.txt --dry-run

As a library::

    from physh_mapper import resolve_term, NormalizedEntity
    entity = resolve_term("CEvNS", vocabulary_path)
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

PHYSH_BASE = "https://physh.org"
PHYSH_CACHE_FILE = "physh_cache.json"
_PHYSH_LAST_CALL = 0.0
_PHYSH_MIN_INTERVAL = 0.35  # seconds between API calls


def _throttle() -> None:
    """Ensure minimum interval between PhySH API calls."""
    global _PHYSH_LAST_CALL
    elapsed = time.monotonic() - _PHYSH_LAST_CALL
    if elapsed < _PHYSH_MIN_INTERVAL:
        time.sleep(_PHYSH_MIN_INTERVAL - elapsed)
    _PHYSH_LAST_CALL = time.monotonic()


# ── API helpers ──────────────────────────────────────────────────────────────


def _physh_get(path: str, timeout: int = 15) -> list[dict[str, Any]] | dict[str, Any] | None:
    """GET ``path`` from the PhySH API.  Returns parsed JSON or None on failure."""
    url = f"{PHYSH_BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    _throttle()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"[physh] API request failed: {url}  ({exc})", flush=True)
        return None


def query_concept(concept_id: str) -> dict[str, Any] | None:
    """Get a single concept by UUID."""
    data = _physh_get(f"/concepts/{concept_id}?include=related,facets,disciplines")
    if isinstance(data, dict):
        return data
    return None


def search_concepts(query: str) -> list[dict[str, Any]]:
    """Search PhySH concepts by label text."""
    import urllib.parse
    data = _physh_get(f"/concepts?q={urllib.parse.quote(query)}")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("data", data.get("results", []))
    return []


# ── Cache helpers ────────────────────────────────────────────────────────────


def _load_physh_cache(cache_dir: Path) -> dict[str, dict[str, Any]]:
    cache_path = cache_dir / PHYSH_CACHE_FILE
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_physh_cache(cache_dir: Path, cache: dict[str, dict[str, Any]]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / PHYSH_CACHE_FILE).write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _cache_concept(cache: dict[str, dict[str, Any]], concept: dict[str, Any]) -> None:
    cid = concept.get("id") or concept.get("uuid") or concept.get("concept_id", "")
    if cid:
        cache[str(cid)] = concept
        label = (concept.get("label") or "").strip().lower()
        if label:
            cache.setdefault("__by_label__", {})[label] = str(cid)


# ── Vocabulary helpers ───────────────────────────────────────────────────────


def load_vocabulary_terms(vocabulary_path: Path) -> list[dict[str, Any]]:
    """Parse ``vocabulary.md`` and return the terms list."""
    if not vocabulary_path.exists():
        return []
    import re
    text = vocabulary_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return []
    import yaml
    try:
        data = yaml.safe_load(match.group(1))
    except Exception:
        return []
    terms = data.get("terms", []) if isinstance(data, dict) else []
    return [t for t in terms if isinstance(t, dict)]


def _lookup_local(term: str, terms: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Try to match *term* against local vocabulary aliases and labels."""
    t = term.strip().lower()
    for entry in terms:
        label = (entry.get("label") or "").strip().lower()
        if t == label:
            return entry
        aliases = entry.get("aliases") or []
        for alias in aliases:
            if t == alias.strip().lower():
                return entry
    return None


# ── Core resolver ────────────────────────────────────────────────────────────


@dataclass
class NormalizedEntity:
    raw_term: str
    canonical_id: str
    label: str
    namespace: str            # "physh" | "local"
    category: str
    source: str               # "physh_api" | "local_cache" | "alias_match" | "unresolved"
    needs_review: bool = False
    physh_uuid: str | None = None
    matched_alias: str | None = None


def resolve_term(
    raw_term: str,
    vocabulary_path: Path,
    cache_dir: Path | None = None,
    *,
    online: bool = True,
) -> NormalizedEntity:
    """Resolve a single raw term to a NormalizedEntity.

    1. Check local vocabulary aliases / labels first.
    2. If not found and *online* is True, query the PhySH API.
    3. If still unresolved, create a ``local:`` placeholder with ``needs_review``.

    *cache_dir* is used to persist PhySH API results across runs.
    """
    raw = raw_term.strip()
    terms = load_vocabulary_terms(vocabulary_path)
    cache: dict[str, dict[str, Any]] = {}
    if cache_dir is not None:
        cache = _load_physh_cache(cache_dir)

    # 1. Local vocabulary (fast path)
    local = _lookup_local(raw, terms)
    if local is not None:
        return NormalizedEntity(
            raw_term=raw,
            canonical_id=str(local.get("canonical_id", "")),
            label=str(local.get("label", raw)),
            namespace=str(local.get("namespace", "local")),
            category=str(local.get("category", "")),
            source="local_cache",
            needs_review=bool(local.get("needs_review", False)),
        )

    # 2. PhySH API search
    if online:
        key = raw.strip().lower()

        # Check cache first
        by_label: dict[str, str] = cache.get("__by_label__", {})
        physh_id = by_label.get(key)
        concept = None

        if physh_id:
            concept = cache.get(physh_id)

        if concept is None:
            # Search PhySH API directly
            results = search_concepts(raw)
            for result in results:
                _cache_concept(cache, result)
                result_label = (result.get("label") or "").strip().lower()
                if result_label == key:
                    concept = result
                    physh_id = concept.get("id") or concept.get("uuid", "")
                    break
                # exact match not found yet, store best candidate
                if concept is None:
                    concept = result
                    physh_id = concept.get("id") or concept.get("uuid", "")

            # If still no exact match, try individual word tokens
            if concept is None or (concept.get("label") or "").strip().lower() != key:
                tokens = key.split()
                if len(tokens) > 1:
                    for token in tokens:
                        if len(token) < 3:
                            continue
                        token_results = search_concepts(token)
                        for result in token_results:
                            _cache_concept(cache, result)
                            result_label = (result.get("label") or "").strip().lower()
                            if result_label == key:
                                concept = result
                                physh_id = concept.get("id") or concept.get("uuid", "")
                                break
                        if concept is not None and (concept.get("label") or "").strip().lower() == key:
                            break

            if cache_dir is not None:
                _save_physh_cache(cache_dir, cache)

        if physh_id and concept:
            # Fetch full concept details (search results may lack facets)
            full = query_concept(physh_id)
            if full:
                concept = full
                _cache_concept(cache, full)

            if cache_dir is not None:
                _save_physh_cache(cache_dir, cache)

            concept = dict(concept)
            facets = concept.get("facets") or []
            facet_name = facets[0].get("label", "") if isinstance(facets, list) and facets else ""
            return NormalizedEntity(
                raw_term=raw,
                canonical_id=f"physh:{physh_id}",
                label=str(concept.get("label", raw)),
                namespace="physh",
                category=_map_physh_facet_to_category(facet_name),
                source="physh_api",
                needs_review=False,
                physh_uuid=physh_id,
            )

    # 3. Unresolved → local placeholder
    slug = raw.lower().replace(" ", "-").replace("/", "-")
    return NormalizedEntity(
        raw_term=raw,
        canonical_id=f"local:{slug}",
        label=raw,
        namespace="local",
        category="",
        source="unresolved",
        needs_review=True,
    )


def _map_physh_facet_to_category(facet_name: str) -> str:
    """Map a PhySH facet name to a DARW edge category."""
    mapping: dict[str, str] = {
        "Research Areas": "research_areas",
        "Physical Systems": "physical_systems",
        "Techniques": "techniques",
        "Properties": "properties",
        "Models": "models",
        "Observables": "observables",
    }
    return mapping.get(facet_name, "")


def _append_term_to_vocabulary(vocabulary_path: Path, entity: NormalizedEntity) -> bool:
    """Add a resolved PhySH term to vocabulary.md if not already present.

    Returns True if a new term was written.
    """
    import re
    terms = load_vocabulary_terms(vocabulary_path)
    existing_ids = {t.get("canonical_id", "") for t in terms}
    if entity.canonical_id in existing_ids:
        return False

    # check by label too
    for t in terms:
        if (t.get("label") or "").strip().lower() == entity.label.strip().lower():
            return False

    new_term = {
        "canonical_id": entity.canonical_id,
        "label": entity.label,
        "namespace": entity.namespace,
        "category": entity.category,
        "aliases": [entity.raw_term] if entity.raw_term.lower() != entity.label.lower() else [],
        "parent": None,
        "related": [],
        "source": "physh",
        "needs_review": False,
    }
    if entity.physh_uuid:
        new_term["physh_uuid"] = entity.physh_uuid

    text = vocabulary_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return False

    import yaml
    try:
        data = yaml.safe_load(match.group(1))
    except Exception:
        return False

    if not isinstance(data, dict):
        return False
    term_list = data.get("terms", [])
    if not isinstance(term_list, list):
        return False

    term_list.append(new_term)
    data["terms"] = term_list

    new_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_block = f"```yaml\n{new_yaml}```"
    new_text = text[:match.start()] + new_block + text[match.end():]
    vocabulary_path.write_text(new_text, encoding="utf-8")
    return True


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="PhySH / local vocabulary entity mapper")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--term", action="append", default=None, help="Term to resolve (repeatable)")
    parser.add_argument("--terms-file", default="", help="File with one term per line")
    parser.add_argument("--offline", action="store_true", default=False, help="Skip PhySH API queries")
    parser.add_argument("--dry-run", action="store_true", help="Do not modify vocabulary.md")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    vocabulary_path = rag_dir / "vocabulary.md"
    cache_dir = rag_dir / "reference"

    if not vocabulary_path.exists():
        print("vocabulary.md not found; run rag-init first")
        return 1

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

    print(f"# PhySH Mapper {'(dry-run)' if args.dry_run else ''}\n")
    written = 0
    for term in terms:
        entity = resolve_term(term, vocabulary_path, cache_dir, online=online)
        print(f"  {entity.raw_term}")
        print(f"    -> {entity.canonical_id}")
        print(f"       namespace: {entity.namespace}")
        print(f"       source:    {entity.source}")
        print(f"       category:  {entity.category or '<unknown>'}")
        print(f"       review:    {entity.needs_review}")
        if entity.matched_alias:
            print(f"       alias:     {entity.matched_alias}")
        # Write PhySH-discovered terms back to vocabulary
        if entity.source == "physh_api" and not args.dry_run:
            if _append_term_to_vocabulary(vocabulary_path, entity):
                print(f"       -> added to vocabulary.md")
                written += 1
        print()

    if written:
        print(f"Added {written} new term(s) to vocabulary.md")
    elif not args.dry_run:
        print("No new terms to add to vocabulary.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
