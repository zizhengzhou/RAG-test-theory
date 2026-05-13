"""Apply reviewed vocabulary suggestions to vocabulary.md."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from common import append_log
from darw_schema import EDGE_CATEGORIES
from physh_mapper import load_vocabulary_terms
from suggest_vocabulary import suggest_edges


@dataclass
class VocabularyTermPlan:
    canonical_id: str
    label: str
    namespace: str
    category: str
    aliases: list[str]
    source: str
    needs_review: bool
    confidence: float
    status: str
    auto_apply: bool = False


@dataclass
class VocabularyPlan:
    rag_dir: Path
    key: str = ""
    terms: list[VocabularyTermPlan] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def new_terms(self) -> list[VocabularyTermPlan]:
        return [term for term in self.terms if term.status == "new"]

    @property
    def existing_terms(self) -> list[VocabularyTermPlan]:
        return [term for term in self.terms if term.status == "existing"]

    @property
    def needs_review(self) -> list[VocabularyTermPlan]:
        return [term for term in self.terms if term.needs_review]


def _vocab_path(rag_dir: Path) -> Path:
    return rag_dir / "vocabulary.md"


def _read_vocab_data(rag_dir: Path) -> tuple[str, re.Match[str], dict]:
    path = _vocab_path(rag_dir)
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        raise ValueError("vocabulary.md has no YAML code block")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict):
        raise ValueError("vocabulary.md YAML root is not a mapping")
    terms = data.setdefault("terms", [])
    if not isinstance(terms, list):
        raise ValueError("vocabulary.md 'terms' is not a list")
    return text, match, data


def _namespace(canonical_id: str) -> str:
    return canonical_id.split(":", 1)[0] if ":" in canonical_id else "local"


def build_vocabulary_plan(
    rag_dir: Path,
    *,
    key: str = "",
    limit: int = 20,
    online: bool = False,
    accepted: set[str] | None = None,
    accept_local_all: bool = False,
) -> VocabularyPlan:
    path = _vocab_path(rag_dir)
    if not path.exists():
        return VocabularyPlan(rag_dir=rag_dir, key=key, errors=["vocabulary.md missing"])
    existing = {str(term.get("canonical_id", "")): term for term in load_vocabulary_terms(path)}
    accepted = accepted or set()
    suggestions = suggest_edges(rag_dir, citation_key=key, limit=limit, online=online)
    planned: list[VocabularyTermPlan] = []
    seen: set[str] = set()
    for category, entries in suggestions.items():
        category = category if category in EDGE_CATEGORIES else "research_areas"
        for entry in entries:
            canonical_id = str(entry.get("canonical_id", "")).strip()
            if not canonical_id or canonical_id in seen:
                continue
            seen.add(canonical_id)
            status = "existing" if canonical_id in existing else "new"
            aliases = [str(alias) for alias in entry.get("local_aliases", []) if str(alias).strip()]
            source = "physh" if canonical_id.startswith("physh:") else "script"
            needs_review = bool(entry.get("needs_review", False))
            auto_apply = False
            if status == "new" and canonical_id.startswith("physh:"):
                auto_apply = (not needs_review) or canonical_id in accepted
            elif status == "new" and canonical_id.startswith("local:"):
                auto_apply = accept_local_all or canonical_id in accepted
            planned.append(
                VocabularyTermPlan(
                    canonical_id=canonical_id,
                    label=str(entry.get("label", canonical_id)).strip(),
                    namespace=_namespace(canonical_id),
                    category=category,
                    aliases=aliases,
                    source=source,
                    needs_review=needs_review,
                    confidence=float(entry.get("confidence", 0.0) or 0.0),
                    status=status,
                    auto_apply=auto_apply,
                )
            )
    return VocabularyPlan(rag_dir=rag_dir, key=key, terms=planned)


def _term_to_yaml(term: VocabularyTermPlan) -> dict[str, object]:
    return {
        "canonical_id": term.canonical_id,
        "label": term.label,
        "namespace": term.namespace,
        "category": term.category,
        "aliases": term.aliases,
        "parent": None,
        "related": [],
        "source": term.source,
        "needs_review": term.needs_review,
    }


def apply_vocabulary_plan(plan: VocabularyPlan) -> int:
    text, match, data = _read_vocab_data(plan.rag_dir)
    terms = data["terms"]
    existing_ids = {str(term.get("canonical_id", "")) for term in terms if isinstance(term, dict)}
    added = 0
    for term in plan.new_terms:
        if not term.auto_apply:
            continue
        if term.canonical_id in existing_ids:
            continue
        terms.append(_term_to_yaml(term))
        existing_ids.add(term.canonical_id)
        added += 1
    new_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_block = f"```yaml\n{new_yaml}```"
    _vocab_path(plan.rag_dir).write_text(text[: match.start()] + new_block + text[match.end() :], encoding="utf-8")
    append_log(plan.rag_dir, "apply-vocabulary", f"key={plan.key}", f"added={added} needs_review={len(plan.needs_review)}")
    return added


def plan_as_dict(plan: VocabularyPlan) -> dict[str, object]:
    return {
        "rag_dir": str(plan.rag_dir),
        "key": plan.key,
        "summary": {
            "terms": len(plan.terms),
            "new_terms": len(plan.new_terms),
            "auto_apply": len([term for term in plan.new_terms if term.auto_apply]),
            "existing_terms": len(plan.existing_terms),
            "needs_review": len(plan.needs_review),
            "errors": len(plan.errors),
        },
        "terms": [term.__dict__ for term in plan.terms],
        "errors": plan.errors,
    }


def print_plan(plan: VocabularyPlan, as_json: bool = False) -> None:
    data = plan_as_dict(plan)
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    summary = data["summary"]
    print(
        f"vocabulary plan: terms={summary['terms']} new={summary['new_terms']} "
        f"existing={summary['existing_terms']} needs_review={summary['needs_review']} errors={summary['errors']}"
    )
    for term in plan.terms:
        action = "auto-apply" if term.auto_apply else ("already-present" if term.status == "existing" else "review")
        print(f"- {term.canonical_id}: {term.status} action={action} category={term.category} review={term.needs_review}")
    for error in plan.errors:
        print(f"error: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply suggested vocabulary terms to vocabulary.md")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--accept", action="append", default=[], help="Accept a suggested canonical_id for writing")
    parser.add_argument("--accept-local-all", action="store_true", help="Accept all suggested local:* terms")
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
    plan = build_vocabulary_plan(
        rag_dir,
        key=args.key,
        limit=args.limit,
        online=args.online,
        accepted=set(args.accept),
        accept_local_all=args.accept_local_all,
    )
    print_plan(plan, as_json=args.json)
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    added = apply_vocabulary_plan(plan)
    print(f"added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
