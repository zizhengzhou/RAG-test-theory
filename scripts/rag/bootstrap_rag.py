"""Bootstrap a DARW RAG project from a BibTeX file, Zotero ZIP, or provider query."""

from __future__ import annotations

import argparse
import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from bib_parser import parse_bibtex_file
from common import append_log, ensure_rag_dirs
from evidence_ingest import ingest_entry
from import_pipeline import apply_plan, build_plan, plan_as_dict
from rag_init import INDEX_CONTENT, SKILL_CONTENT, TEMPLATE_CONTENT, VOCABULARY_CONTENT
from rag_lint import (
    check_auto_blocks,
    check_bibtex_manifest,
    check_dead_links,
    check_pdf_refs,
    check_source_fm,
    load_vocabulary_canonical_ids,
)
from validate_evidence import validate_evidence
from validate_source_pages import validate_source_pages
from validate_vocabulary import validate_vocabulary


def _write_if_missing(path: Path, text: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def initialize_if_needed(rag_dir: Path, *, dry_run: bool = True) -> dict[str, Any]:
    planned = [
        "template.md",
        "vocabulary.md",
        "index.md",
        "SKILL.md",
        "log.md",
        "references.bib",
        "summary/sources/",
        "summary/synthesis/",
        "reference/pdfs/",
        "reference/parsed/",
        "reference/chunks/",
        "reference/arxiv_sources/",
        "reference/imports/",
        "indexes/",
    ]
    if dry_run:
        return {"dry_run": True, "planned": planned, "created": []}

    ensure_rag_dirs(rag_dir, ())
    (rag_dir / "indexes").mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for rel, text in (
        ("template.md", TEMPLATE_CONTENT),
        ("vocabulary.md", VOCABULARY_CONTENT),
        ("index.md", INDEX_CONTENT),
        ("SKILL.md", SKILL_CONTENT),
        ("log.md", "# RAG Operation Log\n\n"),
        ("references.bib", "% RAG shared references manifest\n"),
    ):
        if _write_if_missing(rag_dir / rel, text):
            created.append(rel)
    append_log(rag_dir, "bootstrap-init", f"rag_dir={rag_dir}", f"created={len(created)}")
    return {"dry_run": False, "planned": planned, "created": created}


def lint_issues(rag_dir: Path, *, strict: bool = False) -> list[str]:
    issues: list[str] = []
    vocab_ids = load_vocabulary_canonical_ids(rag_dir)
    issues.extend(check_bibtex_manifest(rag_dir))
    issues.extend(check_source_fm(rag_dir, vocab_ids, strict=strict))
    issues.extend(check_pdf_refs(rag_dir))
    issues.extend(check_dead_links(rag_dir))
    issues.extend(check_auto_blocks(rag_dir))
    issues.extend(validate_vocabulary(rag_dir))
    issues.extend([issue for issue in validate_source_pages(rag_dir, strict=strict) if strict or not issue.startswith("[warning]")])
    issues.extend(validate_evidence(rag_dir))
    return issues


def _import_args(args: argparse.Namespace) -> Namespace:
    return Namespace(
        rag_dir=args.rag_dir,
        bib=args.bib,
        zip=args.zip,
        query=args.query,
        record_id=args.record_id,
        pdf_dir=args.pdf_dir,
        limit=args.limit,
        select=args.select,
        enrich_inspire=args.enrich_inspire,
    )


def _entries_for_ingest(rag_dir: Path, plan, mode: str) -> list[dict[str, str]]:
    if mode == "none":
        return []
    if mode == "new":
        return [candidate.entry for candidate in plan.new_entries]
    manifest = rag_dir / "references.bib"
    return parse_bibtex_file(manifest) if manifest.exists() else []


def bootstrap(args: argparse.Namespace) -> dict[str, Any]:
    rag_dir = Path(args.rag_dir).resolve()
    init_result = initialize_if_needed(rag_dir, dry_run=args.dry_run or not args.yes)
    import_plan = build_plan(_import_args(args)) if any([args.bib, args.zip, args.query, args.record_id]) else None
    plan_data = plan_as_dict(import_plan) if import_plan else {"summary": {"candidates": 0, "new_entries": 0, "duplicates": 0, "errors": 0}, "items": [], "errors": []}

    if args.dry_run or not args.yes:
        return {
            "dry_run": True,
            "init": init_result,
            "import_plan": plan_data,
            "evidence": {"mode": args.ingest, "processed": 0, "failed": []},
            "lint": {"skipped": True, "issues": []},
        }

    if import_plan and import_plan.errors:
        return {
            "dry_run": False,
            "init": init_result,
            "import_plan": plan_data,
            "applied": {},
            "evidence": {"mode": args.ingest, "processed": 0, "failed": []},
            "lint": {"skipped": True, "issues": []},
            "errors": import_plan.errors,
        }

    applied = apply_plan(import_plan) if import_plan else {}
    evidence_entries = _entries_for_ingest(rag_dir, import_plan, args.ingest) if import_plan else []
    evidence_failed: list[str] = []
    evidence_processed = 0
    for entry in evidence_entries:
        key = entry.get("ID", "unknown")
        try:
            ok = ingest_entry(
                entry,
                rag_dir,
                fallback_pdf_on_arxiv_fail=args.fallback_pdf_on_arxiv_fail,
                dry_run=False,
            )
        except Exception as exc:
            ok = False
            evidence_failed.append(f"{key}: {exc}")
        if ok:
            evidence_processed += 1
        elif not any(item.startswith(f"{key}:") for item in evidence_failed):
            evidence_failed.append(f"{key}: evidence ingest did not produce chunks")

    issues = lint_issues(rag_dir, strict=args.strict_lint)
    errors: list[str] = []
    if args.strict_evidence and evidence_failed:
        errors.extend(evidence_failed)
    if issues:
        errors.extend(issues)
    return {
        "dry_run": False,
        "init": init_result,
        "import_plan": plan_data,
        "applied": applied,
        "evidence": {
            "mode": args.ingest,
            "requested": len(evidence_entries),
            "processed": evidence_processed,
            "failed": evidence_failed,
        },
        "lint": {"skipped": False, "issues": issues},
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap a DARW RAG from BibTeX, Zotero ZIP, or provider search")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--bib", default="")
    parser.add_argument("--zip", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--record-id", default="")
    parser.add_argument("--pdf-dir", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--select", type=int, default=1)
    parser.add_argument("--enrich-inspire", action="store_true")
    parser.add_argument("--ingest", choices=["new", "all", "none"], default="new")
    parser.add_argument("--fallback-pdf-on-arxiv-fail", action="store_true")
    parser.add_argument("--strict-evidence", action="store_true")
    parser.add_argument("--strict-lint", action="store_true")
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
    if not any([args.bib, args.zip, args.query, args.record_id]):
        print("provide --bib, --zip, --query, or --record-id")
        return 1

    result = bootstrap(args)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        summary = result["import_plan"]["summary"]
        print(
            "bootstrap: "
            f"dry_run={result['dry_run']} candidates={summary['candidates']} "
            f"new={summary['new_entries']} duplicates={summary['duplicates']}"
        )
        evidence = result["evidence"]
        print(f"evidence: mode={evidence['mode']} processed={evidence['processed']} failed={len(evidence.get('failed', []))}")
        lint = result["lint"]
        print(f"lint: skipped={lint['skipped']} issues={len(lint['issues'])}")
        for error in result.get("errors", []):
            print(f"error: {error}")
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
