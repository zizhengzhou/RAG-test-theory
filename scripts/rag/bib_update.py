"""Plan and apply safe BibTeX metadata updates."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bib_parser import parse_bibtex_file, render_bibtex
from common import append_log
from external_search import SearchResult, search_inspire, search_inspire_by_identifier
from metadata_normalizer import normalize_arxiv, normalize_doi, normalize_entry


@dataclass
class BibFieldChange:
    field: str
    old: str
    new: str
    reason: str


@dataclass
class BibEntryUpdate:
    key: str
    title: str
    provider: str = "inspire"
    provider_record_id: str = ""
    changes: list[BibFieldChange] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    needs_review: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.changes)


@dataclass
class BibUpdatePlan:
    rag_dir: Path
    entries: list[BibEntryUpdate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> list[BibEntryUpdate]:
        return [entry for entry in self.entries if entry.changed and not entry.needs_review]

    @property
    def needs_review(self) -> list[BibEntryUpdate]:
        return [entry for entry in self.entries if entry.needs_review]


def _candidate_query(entry: dict[str, str]) -> tuple[str, list[SearchResult]]:
    normalized = normalize_entry(entry)
    doi = str(normalized["doi"])
    arxiv = str(normalized["arxiv"])
    title = str(normalized["title"])
    if doi or arxiv:
        return "identifier", search_inspire_by_identifier(doi=doi, arxiv=arxiv, size=3)
    if title:
        return "title", search_inspire(title, size=3)
    return "", []


def _matching_candidates(entry: dict[str, str], results: list[SearchResult]) -> list[SearchResult]:
    normalized = normalize_entry(entry)
    doi = str(normalized["doi"])
    arxiv = str(normalized["arxiv"])
    if doi:
        return [result for result in results if normalize_doi(result.doi) == doi]
    if arxiv:
        return [result for result in results if normalize_arxiv(result.arxiv) == arxiv]
    return results


def _add_missing_or_conflict(
    update: BibEntryUpdate,
    entry: dict[str, str],
    field: str,
    new_value: str,
    reason: str,
    *,
    normalizer=lambda value: value.strip(),
) -> None:
    new_value = new_value.strip()
    if not new_value:
        return
    old_value = entry.get(field, "").strip()
    if not old_value:
        update.changes.append(BibFieldChange(field=field, old="", new=new_value, reason=reason))
        return
    if normalizer(old_value) != normalizer(new_value):
        update.needs_review = True
        update.conflicts.append(f"{field} conflict: existing={old_value} provider={new_value}")


def plan_entry_update(entry: dict[str, str], *, provider: str = "inspire") -> BibEntryUpdate:
    if provider != "inspire":
        raise ValueError(f"unsupported provider: {provider}")
    normalized = normalize_entry(entry)
    update = BibEntryUpdate(
        key=str(normalized["key"] or entry.get("ID", "")),
        title=str(normalized["title"] or entry.get("title", "")),
        provider=provider,
    )
    _, results = _candidate_query(entry)
    candidates = _matching_candidates(entry, results)
    if not candidates:
        return update
    if len(candidates) > 1:
        update.needs_review = True
        update.conflicts.append("multiple INSPIRE candidates")
        return update

    result = candidates[0]
    update.provider_record_id = result.record_id
    _add_missing_or_conflict(
        update,
        entry,
        "eprint",
        normalize_arxiv(result.arxiv),
        f"INSPIRE:{result.record_id}",
        normalizer=normalize_arxiv,
    )
    _add_missing_or_conflict(
        update,
        entry,
        "doi",
        normalize_doi(result.doi),
        f"INSPIRE:{result.record_id}",
        normalizer=normalize_doi,
    )
    _add_missing_or_conflict(update, entry, "inspire", result.control_number or result.record_id, f"INSPIRE:{result.record_id}")
    return update


def build_update_plan(rag_dir: Path, *, key: str = "", all_entries: bool = False) -> BibUpdatePlan:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return BibUpdatePlan(rag_dir=rag_dir, errors=[f"No {manifest}"])
    entries = parse_bibtex_file(manifest)
    if key:
        entries = [entry for entry in entries if entry.get("ID") == key]
    elif not all_entries:
        return BibUpdatePlan(rag_dir=rag_dir, errors=["provide --key or --all"])
    if not entries:
        return BibUpdatePlan(rag_dir=rag_dir, errors=["no matching entries"])
    return BibUpdatePlan(rag_dir=rag_dir, entries=[plan_entry_update(entry) for entry in entries])


def apply_update_plan(plan: BibUpdatePlan) -> int:
    manifest = plan.rag_dir / "references.bib"
    entries = parse_bibtex_file(manifest)
    by_key = {entry.key: entry for entry in plan.changed}
    updated = 0
    rendered: list[str] = []
    for entry in entries:
        update = by_key.get(entry.get("ID", ""))
        if update:
            for change in update.changes:
                entry[change.field] = change.new
            updated += 1
        rendered.append(render_bibtex(entry))
    manifest.write_text("\n\n".join(rendered).strip() + "\n", encoding="utf-8")
    append_log(plan.rag_dir, "bib-update", f"entries={len(plan.entries)}", f"updated={updated} needs_review={len(plan.needs_review)}")
    return updated


def plan_as_dict(plan: BibUpdatePlan) -> dict[str, object]:
    return {
        "rag_dir": str(plan.rag_dir),
        "summary": {
            "entries": len(plan.entries),
            "changed": len(plan.changed),
            "needs_review": len(plan.needs_review),
            "errors": len(plan.errors),
        },
        "entries": [asdict(entry) for entry in plan.entries],
        "errors": plan.errors,
    }


def print_plan(plan: BibUpdatePlan, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(plan_as_dict(plan), indent=2, ensure_ascii=False))
        return
    summary = plan_as_dict(plan)["summary"]
    print(
        f"bib update plan: entries={summary['entries']} changed={summary['changed']} "
        f"needs_review={summary['needs_review']} errors={summary['errors']}"
    )
    for entry in plan.entries:
        status = "needs-review" if entry.needs_review else ("update" if entry.changed else "unchanged")
        print(f"- {entry.key}: {status}")
        for change in entry.changes:
            print(f"  {change.field}: {change.old or '<missing>'} -> {change.new} ({change.reason})")
        for conflict in entry.conflicts:
            print(f"  conflict: {conflict}")
    for error in plan.errors:
        print(f"error: {error}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan and apply safe BibTeX metadata updates")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="")
    parser.add_argument("--all", action="store_true")
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
    plan = build_update_plan(rag_dir, key=args.key, all_entries=args.all)
    print_plan(plan, as_json=args.json)
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    updated = apply_update_plan(plan)
    print(f"updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
