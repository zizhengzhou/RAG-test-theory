"""Evidence-first ingest: resolve, register parsed evidence, chunk, and link source pages."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from bib_parser import parse_bibtex_file
from chunker import write_chunks
from common import append_log, read_frontmatter, write_frontmatter
from darw_schema import chunk_manifest_path, parsed_manifest_path
from source_page_builder import body_skeleton, default_frontmatter
from parsers import EvidenceResolutionError, parse_evidence
from resolve_source import ResolvedSource, resolve_entry


def _source_path(rag_dir: Path, key: str) -> Path:
    return rag_dir / "summary" / "sources" / f"{key}.md"


def _rel(path: Path, rag_dir: Path) -> str:
    try:
        return path.resolve().relative_to(rag_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = rag_dir / "references.bib"
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _set_evidence_frontmatter(fm: dict[str, object], resolved: ResolvedSource, rag_dir: Path) -> dict[str, object]:
    parsed_path = parsed_manifest_path(rag_dir, resolved.doc_id)
    import json
    manifest = json.loads(parsed_path.read_text(encoding="utf-8"))
    chunk_path = chunk_manifest_path(rag_dir, resolved.doc_id)

    fm["doc_id"] = resolved.doc_id
    fm["citation_key"] = resolved.citation_key
    identifiers = fm.setdefault("identifiers", {})
    if isinstance(identifiers, dict):
        identifiers["arxiv"] = resolved.arxiv_id or None
        identifiers["doi"] = resolved.doi or None
    source = fm.setdefault("source", {})
    if isinstance(source, dict):
        source["source_type"] = resolved.route
        source["primary_evidence"] = manifest.get("parsed_markdown", "")
        source["original_pdf"] = manifest.get("original_pdf", "")
        source["original_tex"] = manifest.get("original_tex")
        source["source_sha256"] = manifest.get("source_sha256", "")
        source["parser"] = manifest.get("parser", "")
        source["parser_version"] = manifest.get("parser_version", "")
        source["parsed_at"] = manifest.get("created_at", "")
    fm["chunk_manifest"] = _rel(chunk_path, rag_dir)
    quality = fm.setdefault("quality", {})
    if isinstance(quality, dict):
        quality["needs_human_review"] = bool(resolved.needs_review)
        quality["metadata_conflicts"] = resolved.metadata_conflicts
    return fm


def ingest_entry(
    entry: dict[str, str],
    rag_dir: Path,
    *,
    pdf_output: Path | None = None,
    arxiv_output: Path | None = None,
    dry_run: bool = False,
) -> bool:
    resolved = resolve_entry(entry, rag_dir)
    if not resolved.route:
        print(f"unresolved: {resolved.citation_key} ({'; '.join(resolved.metadata_conflicts)})")
        return False

    print(f"evidence plan: {resolved.citation_key} route={resolved.route} doc_id={resolved.doc_id}")
    evidence = parse_evidence(
        resolved,
        rag_dir,
        pdf_output=pdf_output,
        arxiv_output=arxiv_output,
        dry_run=dry_run,
    )
    manifest_path = parsed_manifest_path(rag_dir, resolved.doc_id)
    if dry_run:
        chunk_path = chunk_manifest_path(rag_dir, resolved.doc_id)
        print(f"would write chunk manifest: {chunk_path}")
        print(f"would update source page: {_source_path(rag_dir, resolved.citation_key)}")
        return True

    chunk_path = write_chunks(rag_dir, manifest_path)
    source_path = _source_path(rag_dir, resolved.citation_key)
    if source_path.exists():
        fm, body = read_frontmatter(source_path)
    else:
        fm = default_frontmatter(entry, rag_dir)
        body = body_skeleton(entry, rag_dir)
    fm = _set_evidence_frontmatter(fm, resolved, rag_dir)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(write_frontmatter(fm) + body, encoding="utf-8")
    append_log(
        rag_dir,
        "evidence-ingest",
        f"key={resolved.citation_key}",
        f"parsed={asdict(evidence)['parsed_markdown']} chunks={_rel(chunk_path, rag_dir)}",
    )
    print(f"updated evidence: {resolved.citation_key}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DARW parsed evidence and chunk manifests")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--pdf-output", default="")
    parser.add_argument("--mineru-output", default="", help="Deprecated alias for --pdf-output")
    parser.add_argument("--arxiv-output", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    entries = _load_entries(rag_dir)
    if args.key:
        entries = [entry for entry in entries if entry.get("ID") == args.key]
    elif not args.all:
        print("provide --key or --all")
        return 1
    if not entries:
        print("no matching entries")
        return 1

    ok = 0
    for entry in entries:
        try:
            if ingest_entry(
                entry,
                rag_dir,
                pdf_output=Path(args.pdf_output or args.mineru_output).resolve() if (args.pdf_output or args.mineru_output) else None,
                arxiv_output=Path(args.arxiv_output).resolve() if args.arxiv_output else None,
                dry_run=args.dry_run,
            ):
                ok += 1
        except EvidenceResolutionError as exc:
            print(f"{entry.get('ID', 'unknown')}: {exc}")
    if args.dry_run:
        print("[dry-run] no files written")
    print(f"evidence_ingest: processed={ok} requested={len(entries)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
