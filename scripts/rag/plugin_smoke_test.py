"""End-to-end smoke test for the repo-local DARW RAG plugin workflow."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from bootstrap_rag import bootstrap
from context_pack import build_context_pack
from evidence_ingest import ingest_entry
from trace_claim import trace_chunk
from bib_parser import parse_bibtex_file


def _write_demo_inputs(base: Path) -> tuple[Path, Path]:
    pdf = base / "demo-paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")
    bib = base / "demo.bib"
    bib.write_text(
        "@article{demo2026,\n"
        "  title = {Demonstration of Low Threshold Detector Background Rejection},\n"
        "  author = {Researcher, Ada},\n"
        "  year = {2026},\n"
        "  doi = {10.1000/demo-rag},\n"
        f"  file = {{{pdf.as_posix()}}}\n"
        "}\n",
        encoding="utf-8",
    )
    return bib, pdf


def _write_parsed_markdown(base: Path) -> Path:
    parsed = base / "demo-parsed.md"
    parsed.write_text(
        "# Abstract\n\n"
        "The demo detector study describes low threshold detector background rejection "
        "using pulse-shape discrimination and shielding.\n\n"
        "# Results\n\n"
        "Background rejection improves the signal search sensitivity in the low-energy "
        "region while preserving detector efficiency.\n\n"
        "# References\n\n"
        "[1] A reference list entry that should not dominate retrieval.\n"
        "[2] Another reference list entry.\n"
        "[3] A third reference list entry.\n",
        encoding="utf-8",
    )
    return parsed


def _bootstrap_args(rag_dir: Path, bib: Path, *, yes: bool) -> Namespace:
    return Namespace(
        rag_dir=str(rag_dir),
        bib=str(bib),
        zip="",
        query="",
        record_id="",
        pdf_dir="",
        limit=5,
        select=1,
        enrich_inspire=False,
        ingest="none",
        fallback_pdf_on_arxiv_fail=False,
        strict_evidence=False,
        strict_lint=False,
        dry_run=not yes,
        yes=yes,
    )


def run_smoke_test(workdir: Path, *, keep: bool = False) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    plugin_manifest = repo_root / "plugins" / "darw-rag" / ".codex-plugin" / "plugin.json"
    marketplace = repo_root / ".agents" / "plugins" / "marketplace.json"
    report: dict[str, Any] = {
        "plugin_manifest_exists": plugin_manifest.exists(),
        "marketplace_exists": marketplace.exists(),
        "workdir": str(workdir),
        "steps": {},
    }
    if plugin_manifest.exists():
        report["plugin_manifest"] = json.loads(plugin_manifest.read_text(encoding="utf-8"))
    if marketplace.exists():
        report["marketplace"] = json.loads(marketplace.read_text(encoding="utf-8"))

    bib, _pdf = _write_demo_inputs(workdir)
    parsed = _write_parsed_markdown(workdir)
    rag_dir = workdir / "RAG"

    operation_logs: dict[str, str] = {}
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        dry_run = bootstrap(_bootstrap_args(rag_dir, bib, yes=False))
    operation_logs["bootstrap_dry_run"] = buffer.getvalue()

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        applied = bootstrap(_bootstrap_args(rag_dir, bib, yes=True))
    operation_logs["bootstrap_apply"] = buffer.getvalue()

    entries = parse_bibtex_file(rag_dir / "references.bib")
    if not entries:
        raise RuntimeError("bootstrap did not import any BibTeX entries")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        ingested = ingest_entry(entries[0], rag_dir, pdf_output=parsed)
    operation_logs["evidence_ingest"] = buffer.getvalue()

    context = build_context_pack(
        rag_dir,
        query="low threshold detector background rejection",
        top_k=3,
        budget_tokens=1200,
    )
    chunks = context.get("evidence_chunks", [])
    trace = trace_chunk(rag_dir, chunks[0]["chunk_id"]) if chunks else None

    report["steps"] = {
        "bootstrap_dry_run": {
            "dry_run": dry_run["dry_run"],
            "candidates": dry_run["import_plan"]["summary"]["candidates"],
            "new_entries": dry_run["import_plan"]["summary"]["new_entries"],
        },
        "bootstrap_apply": {
            "dry_run": applied["dry_run"],
            "appended": applied.get("applied", {}).get("appended", 0),
            "lint_issues": len(applied.get("lint", {}).get("issues", [])),
        },
        "evidence_ingest": {
            "ok": bool(ingested),
            "chunk_files": len(list((rag_dir / "reference" / "chunks").glob("*.jsonl"))),
        },
        "research_context": {
            "profile": context.get("provenance", {}).get("profile"),
            "chunks": len(chunks),
            "first_chunk_id": chunks[0]["chunk_id"] if chunks else "",
            "first_source_page": chunks[0]["source_page"] if chunks else "",
            "first_section_type": chunks[0].get("section_type", "") if chunks else "",
            "has_trace": trace is not None,
            "context_chars": len(json.dumps(context, ensure_ascii=False)),
        },
    }
    report["success"] = all(
        [
            report["plugin_manifest_exists"],
            report["marketplace_exists"],
            report["steps"]["bootstrap_dry_run"]["dry_run"],
            report["steps"]["bootstrap_apply"]["appended"] == 1,
            report["steps"]["evidence_ingest"]["ok"],
            report["steps"]["research_context"]["chunks"] > 0,
            report["steps"]["research_context"]["has_trace"],
        ]
    )
    if keep:
        report["kept_workdir"] = str(workdir)
    report["operation_logs"] = operation_logs
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a DARW RAG plugin smoke test")
    parser.add_argument("--workdir", default="", help="Optional scratch directory. Defaults to .tmp_plugin_smoke/<run-id>.")
    parser.add_argument("--keep", action="store_true", help="Keep the scratch directory after the test.")
    parser.add_argument("--json", action="store_true")
    return parser


def _new_scratch_dir(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        candidate = parent / f"run-{uuid.uuid4().hex[:12]}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"could not create a unique smoke-test workdir under {parent}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    cleanup_after = False
    if args.workdir:
        workdir = Path(args.workdir).resolve()
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        workdir = _new_scratch_dir(Path.cwd() / ".tmp_plugin_smoke")
        cleanup_after = not args.keep
    try:
        report = run_smoke_test(workdir, keep=args.keep or bool(args.workdir))
    finally:
        if cleanup_after:
            shutil.rmtree(workdir, ignore_errors=True)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"plugin smoke test: success={report['success']}")
        for name, data in report["steps"].items():
            print(f"- {name}: {data}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
