"""Apply vocabulary-backed edge suggestions to source pages."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from common import append_log, read_frontmatter, write_frontmatter
from darw_schema import EDGE_CATEGORIES
from physh_mapper import load_vocabulary_terms
from suggest_vocabulary import suggest_edges


@dataclass
class EdgePlanItem:
    category: str
    canonical_id: str
    label: str
    confidence: float
    evidence: str
    needs_review: bool
    status: str
    message: str = ""


@dataclass
class EdgePlan:
    rag_dir: Path
    key: str
    source_path: Path
    items: list[EdgePlanItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def new_items(self) -> list[EdgePlanItem]:
        return [item for item in self.items if item.status == "new"]


def _source_path(rag_dir: Path, key: str) -> Path:
    return rag_dir / "summary" / "sources" / f"{key}.md"


def _vocab_ids(rag_dir: Path) -> set[str]:
    return {str(term.get("canonical_id", "")) for term in load_vocabulary_terms(rag_dir / "vocabulary.md")}


def build_edge_plan(rag_dir: Path, *, key: str, limit: int = 20, online: bool = False) -> EdgePlan:
    source_path = _source_path(rag_dir, key)
    if not key:
        return EdgePlan(rag_dir=rag_dir, key=key, source_path=source_path, errors=["provide --key"])
    if not source_path.exists():
        return EdgePlan(rag_dir=rag_dir, key=key, source_path=source_path, errors=[f"source page missing: {source_path}"])
    vocab_ids = _vocab_ids(rag_dir)
    if not vocab_ids:
        return EdgePlan(rag_dir=rag_dir, key=key, source_path=source_path, errors=["vocabulary has no canonical terms"])
    fm, _ = read_frontmatter(source_path)
    existing: set[str] = set()
    edges = fm.get("edges", {})
    if isinstance(edges, dict):
        for entries in edges.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    cid = str(entry.get("canonical_id", ""))
                else:
                    cid = str(entry)
                if cid:
                    existing.add(cid)

    suggestions = suggest_edges(rag_dir, citation_key=key, limit=limit, online=online)
    items: list[EdgePlanItem] = []
    for category, entries in suggestions.items():
        category = category if category in EDGE_CATEGORIES else "research_areas"
        for entry in entries:
            canonical_id = str(entry.get("canonical_id", "")).strip()
            if not canonical_id:
                continue
            if canonical_id not in vocab_ids:
                status = "unresolved"
                message = "not in vocabulary.md"
            else:
                status = "existing" if canonical_id in existing else "new"
                message = ""
            items.append(
                EdgePlanItem(
                    category=category,
                    canonical_id=canonical_id,
                    label=str(entry.get("label", canonical_id)),
                    confidence=float(entry.get("confidence", 0.0) or 0.0),
                    evidence=f"suggest_vocabulary:{key}",
                    needs_review=bool(entry.get("needs_review", False)) or status == "unresolved",
                    status=status,
                    message=message,
                )
            )
    return EdgePlan(rag_dir=rag_dir, key=key, source_path=source_path, items=items)


def _edge_entry(item: EdgePlanItem) -> dict[str, object]:
    return {
        "canonical_id": item.canonical_id,
        "label": item.label,
        "confidence": item.confidence,
        "evidence": item.evidence,
        "needs_review": item.needs_review,
    }


def apply_edge_plan(plan: EdgePlan) -> int:
    fm, body = read_frontmatter(plan.source_path)
    edges = fm.setdefault("edges", {})
    if not isinstance(edges, dict):
        edges = {}
        fm["edges"] = edges
    added = 0
    for category in EDGE_CATEGORIES:
        edges.setdefault(category, [])
    for item in plan.new_items:
        entries = edges.setdefault(item.category, [])
        if not isinstance(entries, list):
            entries = []
            edges[item.category] = entries
        existing = {
            str(entry.get("canonical_id", "")) if isinstance(entry, dict) else str(entry)
            for entry in entries
        }
        if item.canonical_id in existing:
            continue
        entries.append(_edge_entry(item))
        added += 1
    plan.source_path.write_text(write_frontmatter(fm) + body, encoding="utf-8")
    append_log(plan.rag_dir, "apply-edges", f"key={plan.key}", f"added={added}")
    return added


def plan_as_dict(plan: EdgePlan) -> dict[str, object]:
    return {
        "rag_dir": str(plan.rag_dir),
        "key": plan.key,
        "source_path": str(plan.source_path),
        "summary": {
            "items": len(plan.items),
            "new_items": len(plan.new_items),
            "errors": len(plan.errors),
        },
        "items": [item.__dict__ for item in plan.items],
        "errors": plan.errors,
    }


def print_plan(plan: EdgePlan, as_json: bool = False) -> None:
    data = plan_as_dict(plan)
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    summary = data["summary"]
    print(f"edge plan: items={summary['items']} new={summary['new_items']} errors={summary['errors']}")
    for item in plan.items:
        print(f"- {item.category}: {item.canonical_id} {item.status} confidence={item.confidence}")
    for error in plan.errors:
        print(f"error: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply source-page edge suggestions")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.dry_run and args.yes:
        print("choose only one of --dry-run or --yes")
        return 1
    rag_dir = Path(args.rag_dir).resolve()
    plan = build_edge_plan(rag_dir, key=args.key, limit=args.limit, online=args.online)
    print_plan(plan, as_json=args.json)
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    added = apply_edge_plan(plan)
    print(f"added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
