"""Validate DARW vocabulary.md structure and term consistency."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

from darw_schema import EDGE_CATEGORIES, VOCABULARY_SCHEMA_VERSION
from common import read_frontmatter


REQUIRED_TERM_FIELDS = (
    "canonical_id", "label", "namespace", "category",
    "aliases", "source", "needs_review",
)


def _extract_vocab_terms(rag_dir: Path) -> tuple[dict | None, list[str]]:
    """Parse the YAML block from vocabulary.md. Returns (data, issues)."""
    vocab_file = rag_dir / "vocabulary.md"
    if not vocab_file.exists():
        return None, ["vocabulary.md missing"]
    text = vocab_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    issues: list[str] = []

    if f"`{VOCABULARY_SCHEMA_VERSION}`" not in text:
        issues.append(f"vocabulary.md missing schema version declaration: `{VOCABULARY_SCHEMA_VERSION}`")

    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return None, issues + ["vocabulary.md has no YAML code block"]
    try:
        data = yaml.safe_load(match.group(1))
    except Exception as exc:
        return None, issues + [f"vocabulary.md YAML parse error: {exc}"]
    if not isinstance(data, dict):
        return None, issues + ["vocabulary.md YAML root is not a mapping"]
    return data, issues


def _collect_source_page_edge_ids(rag_dir: Path) -> set[str]:
    """Return the set of all canonical_id values used in source page edges."""
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return set()
    ids: set[str] = set()
    for page in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page)
        edges = fm.get("edges")
        if not isinstance(edges, dict):
            continue
        for entries in edges.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                cid = entry.get("canonical_id", "") if isinstance(entry, dict) else str(entry)
                cid = str(cid).strip()
                if cid:
                    ids.add(cid)
    return ids


def _validate_physh_terms_online(terms: list[dict]) -> list[str]:
    issues: list[str] = []
    from physh_mapper import query_concept

    for i, term in enumerate(terms):
        if not isinstance(term, dict):
            continue
        cid = str(term.get("canonical_id", "")).strip()
        namespace = str(term.get("namespace", "")).strip()
        if not cid.startswith("physh:") and namespace != "physh":
            continue
        if not cid.startswith("physh:"):
            issues.append(f"term[{i}] namespace is physh but canonical_id is not physh:*: {cid}")
            continue
        concept_id = cid.split(":", 1)[1]
        concept = query_concept(concept_id)
        if not concept:
            issues.append(f"PhySH concept not found for {cid}")
            continue
        label = str(term.get("label", "")).strip()
        physh_label = str(concept.get("label", "")).strip()
        if not physh_label:
            issues.append(f"PhySH concept has no label for {cid}")
        elif label != physh_label:
            issues.append(f"PhySH label mismatch for {cid}: vocabulary='{label}' physh='{physh_label}'")
    return issues


def validate_vocabulary(rag_dir: Path, *, online_physh: bool = False) -> list[str]:
    issues: list[str] = []
    data, parse_issues = _extract_vocab_terms(rag_dir)
    issues.extend(parse_issues)
    if data is None:
        return issues

    terms = data.get("terms")
    if not isinstance(terms, list):
        return issues + ["vocabulary.md 'terms' is not a list"]

    if len(terms) == 0:
        return issues  # empty skeleton is valid

    seen_ids: set[str] = set()
    for i, term in enumerate(terms):
        if not isinstance(term, dict):
            issues.append(f"term[{i}] is not a mapping")
            continue
        for field in REQUIRED_TERM_FIELDS:
            if field not in term:
                issues.append(f"term[{i}] missing required field '{field}'")
        category = str(term.get("category", ""))
        if category and category not in EDGE_CATEGORIES:
            issues.append(f"term[{i}] has unknown category '{category}'")
        cid = str(term.get("canonical_id", ""))
        namespace = str(term.get("namespace", ""))
        if namespace == "alias:":
            issues.append(f"term[{i}] has namespace 'alias:' but is listed as a canonical term")
        if cid.startswith("physh:") and namespace != "physh":
            issues.append(f"term[{i}] canonical_id is physh:* but namespace is '{namespace}'")
        if namespace == "physh" and not cid.startswith("physh:"):
            issues.append(f"term[{i}] namespace is physh but canonical_id is not physh:*")
        if cid:
            if cid in seen_ids:
                issues.append(f"duplicate canonical_id in vocabulary: {cid}")
            seen_ids.add(cid)

    # Aliases appearing as canonical IDs in source page edges
    all_aliases: set[str] = set()
    for term in terms:
        if not isinstance(term, dict):
            continue
        for alias in term.get("aliases", []) or []:
            if isinstance(alias, str) and alias.strip():
                all_aliases.add(alias.strip())

    edge_ids = _collect_source_page_edge_ids(rag_dir)
    alias_in_edges = all_aliases & edge_ids
    for cid in sorted(alias_in_edges):
        issues.append(f"alias '{cid}' used as final canonical_id in source page edges")

    if online_physh:
        issues.extend(_validate_physh_terms_online(terms))

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DARW vocabulary.md")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--online-physh", action="store_true", help="Verify physh:* terms against the live PhySH API")
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    issues = validate_vocabulary(rag_dir, online_physh=args.online_physh)
    if issues:
        print(f"Vocabulary issues found: {len(issues)}")
        for issue in issues:
            print(f"- [ ] {issue}")
        return 1
    print("No vocabulary issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
