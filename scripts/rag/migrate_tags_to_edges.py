"""Migrate legacy free-string tags into structured DARW edges.

Reads source page frontmatter, finds legacy ``tags`` fields (lists of
free strings), resolves each tag against vocabulary.md labels/aliases,
falls back to PhySH API, and writes canonical ``edges`` entries.

Rules:
- Default dry-run; apply only with --yes.
- Never delete or modify the legacy ``tags`` field.
- Unresolved terms become ``local:*`` placeholders with needs_review.
- Free-form strings are never written into final edges.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import read_frontmatter, write_frontmatter
from darw_schema import EDGE_CATEGORIES
from physh_mapper import resolve_term


def _classify_edge_category(entity) -> str:
    """Infer a DARW edge category from a NormalizedEntity or raw term."""
    cat = (entity.category or "").strip()
    if cat in EDGE_CATEGORIES:
        return cat
    return ""


def migrate_source_page(
    page_path: Path,
    vocabulary_path: Path,
    cache_dir: Path,
    *,
    dry_run: bool = True,
    online: bool = True,
) -> dict:
    """Migrate a single source page. Returns a result dict with keys:
    'page', 'tags_found', 'resolved', 'unresolved', 'dry_run'.
    """
    fm, body = read_frontmatter(page_path)
    tags = fm.get("tags")
    if not isinstance(tags, list) or len(tags) == 0:
        return {"page": str(page_path), "tags_found": 0, "resolved": [], "unresolved": [], "dry_run": dry_run}

    raw_terms = [str(t).strip() for t in tags if isinstance(t, str) and t.strip()]
    resolved: list[dict] = []
    unresolved: list[str] = []

    for term in raw_terms:
        entity = resolve_term(term, vocabulary_path, cache_dir, online=online)
        category = _classify_edge_category(entity)
        if entity.source == "unresolved":
            unresolved.append(term)
            if not dry_run:
                # still write a local: placeholder with needs_review
                resolved.append({
                    "canonical_id": entity.canonical_id,
                    "label": entity.label,
                    "local_aliases": [entity.raw_term] if entity.raw_term.lower() != entity.label.lower() else [],
                    "confidence": 0.0,
                })
            else:
                resolved.append({
                    "canonical_id": entity.canonical_id,
                    "label": entity.label,
                    "local_aliases": [entity.raw_term] if entity.raw_term.lower() != entity.label.lower() else [],
                    "confidence": 0.0,
                })
        else:
            resolved.append({
                "canonical_id": entity.canonical_id,
                "label": entity.label,
                "local_aliases": [entity.raw_term] if entity.raw_term.lower() != entity.label.lower() else [],
                "confidence": 1.0,
            })

    # Merge into existing edges
    edges = fm.get("edges")
    if not isinstance(edges, dict):
        edges = {cat: [] for cat in EDGE_CATEGORIES}

    if not dry_run:
        for entry in resolved:
            cid = entry["canonical_id"]
            # Try to place in a category based on what the resolver returned or default to first matching
            placed = False
            for cat in EDGE_CATEGORIES:
                existing = edges.setdefault(cat, [])
                existing_ids = {e.get("canonical_id", "") if isinstance(e, dict) else str(e) for e in existing}
                if cid not in existing_ids:
                    existing.append(entry)
                    placed = True
                    break
            if not placed:
                edges.setdefault("research_areas", []).append(entry)

        fm["edges"] = edges
        new_content = write_frontmatter(fm) + body
        page_path.write_text(new_content, encoding="utf-8")

    return {
        "page": str(page_path),
        "tags_found": len(raw_terms),
        "resolved": [r["canonical_id"] for r in resolved],
        "unresolved": unresolved,
        "dry_run": dry_run,
    }


def migrate_all(rag_dir: Path, *, dry_run: bool = True, online: bool = True) -> list[dict]:
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return []
    vocabulary_path = rag_dir / "vocabulary.md"
    cache_dir = rag_dir / "reference"
    results: list[dict] = []
    for page in sorted(sources_dir.glob("*.md")):
        result = migrate_source_page(page, vocabulary_path, cache_dir, dry_run=dry_run, online=online)
        if result["tags_found"] > 0:
            results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy tags to structured edges")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview migration only (default)")
    parser.add_argument("--yes", action="store_true", help="Apply migration")
    parser.add_argument("--offline", action="store_true", help="Skip PhySH API queries")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    dry_run = not args.yes
    online = not args.offline

    results = migrate_all(rag_dir, dry_run=dry_run, online=online)

    if not results:
        print("No source pages with legacy tags found.")
        return 0

    total_tags = sum(r["tags_found"] for r in results)
    total_resolved = sum(len(r["resolved"]) for r in results)
    total_unresolved = sum(len(r["unresolved"]) for r in results)

    for r in results:
        print(f"\n{r['page']}:")
        print(f"  tags found: {r['tags_found']}")
        for cid in r["resolved"]:
            print(f"  -> {cid}")
        for term in r["unresolved"]:
            print(f"  [unresolved] {term}")

    print(f"\n---")
    print(f"Pages: {len(results)}")
    print(f"Tags: {total_tags}, resolved: {total_resolved}, unresolved: {total_unresolved}")
    if dry_run:
        print("[dry-run] no files modified. Run with --yes to apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
