"""Register or run evidence parsers and write DARW parsed manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from darw_schema import (
    ARXIV_SOURCE,
    PARSED_EVIDENCE_SCHEMA_VERSION,
    PDF_MINERU,
    PDF_PYMUPDF,
    parsed_manifest_path,
    parsed_markdown_path,
)
from resolve_source import ResolvedSource, resolve_key
from temp_paths import local_temp_dir


class EvidenceResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedEvidence:
    schema_version: str
    doc_id: str
    citation_key: str
    route: str
    arxiv_id: str
    doi: str
    parser: str
    parser_version: str
    source_sha256: str
    parsed_markdown: str
    original_pdf: str
    original_tex: str | None
    created_at: str


_ARXIV_RETRY_DELAY = 5.0
_ARXIV_MAX_RETRIES = 3
_ARXIV_CACHE_VERSION = "arxiv2md-cache-v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path, rag_dir: Path) -> str:
    try:
        return path.resolve().relative_to(rag_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _build_frontmatter(paper, arxiv_id: str) -> str:
    return f"""---
arxiv_id: "{arxiv_id}"
title: "{paper.title}"
published: "{paper.published.strftime('%Y-%m-%d') if paper.published else ''}"
authors: {', '.join(str(a.name) for a in paper.authors)}
---

"""


def _run_arxiv2md_html(arxiv_id: str, paper) -> str:
    """Primary route: convert arXiv HTML to Markdown via arxiv2markdown."""
    import asyncio
    from arxiv2md.ingestion import ingest_paper

    print(f"  arxiv-source: converting via arxiv2md (HTML)...", flush=True)
    ingest_result, _ingest_meta = asyncio.run(
        ingest_paper(
            arxiv_id=arxiv_id,
            version=None,
            html_url="",
            remove_refs=True,
            remove_toc=False,
            section_filter_mode="all",
            sections=[],
            include_frontmatter=False,
        )
    )
    content_md = ingest_result.content
    if not content_md or not content_md.strip():
        raise EvidenceResolutionError(f"arxiv2md produced empty content for {arxiv_id}")
    content_md = _build_frontmatter(paper, arxiv_id) + content_md
    print(f"  arxiv-source: arxiv2md parsed {len(content_md)} chars", flush=True)
    return content_md


def _run_pandoc_fallback(arxiv_id: str, paper) -> str:
    """Fallback route: download LaTeX source and convert with pandoc."""
    import subprocess
    import tarfile

    with local_temp_dir("rag_arxiv_source_") as dpath:
        print(f"  arxiv-source: downloading source tarball...", flush=True)
        fpath_source = paper.download_source(dirpath=str(dpath), download_domain="arxiv.org")
        time.sleep(1.0)
        extract_dir = dpath / "source"
        extract_dir.mkdir(exist_ok=True)
        with tarfile.open(fpath_source, mode="r:gz") as tar:
            tar.extractall(extract_dir)
        tex_files = sorted(extract_dir.rglob("*.tex"))
        if not tex_files:
            raise EvidenceResolutionError(f"No .tex file found in source for {arxiv_id}")
        main_tex = tex_files[0]
        print(f"  arxiv-source: converting {main_tex.name} with pandoc...", flush=True)
        result = subprocess.run(
            ["pandoc", "-f", "latex", "-t", "markdown", "--wrap=none", str(main_tex)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0 or not result.stdout.strip():
            stderr_snippet = result.stderr[:300] if result.stderr else ""
            raise EvidenceResolutionError(f"pandoc failed for {arxiv_id}: {stderr_snippet}")
        content_md = _build_frontmatter(paper, arxiv_id) + result.stdout
        print(f"  arxiv-source: pandoc parsed {len(content_md)} chars", flush=True)
        return content_md


def _run_arxiv2md(arxiv_id: str, verbose: bool = False) -> str:
    import arxiv

    retries = 0
    last_error: Exception | None = None
    while retries < _ARXIV_MAX_RETRIES:
        try:
            print(f"  arxiv-source: fetching metadata for arXiv:{arxiv_id}...", flush=True)
            client = arxiv.Client(delay_seconds=10.0, num_retries=5)
            results = list(client.results(arxiv.Search(id_list=[arxiv_id])))
            if not results:
                raise EvidenceResolutionError(f"No arXiv results for {arxiv_id}")
            paper = results[0]
            time.sleep(1.0)

            # Primary: arxiv2md HTML→Markdown (best quality)
            try:
                return _run_arxiv2md_html(arxiv_id, paper)
            except Exception as html_err:
                print(f"  arxiv-source: arxiv2md failed ({str(html_err)[:120]}), falling back to pandoc...", flush=True)
                return _run_pandoc_fallback(arxiv_id, paper)

        except Exception as exc:
            last_error = exc
            retries += 1
            err_msg = str(exc)[:200]
            if "429" in err_msg or "Too Many Requests" in err_msg:
                wait = _ARXIV_RETRY_DELAY * (retries + 1)
                print(f"  arxiv-source: rate-limited (HTTP 429), retry {retries}/{_ARXIV_MAX_RETRIES} in {wait}s...", flush=True)
                time.sleep(wait)
            elif retries < _ARXIV_MAX_RETRIES:
                wait = _ARXIV_RETRY_DELAY
                print(f"  arxiv-source: error, retry {retries}/{_ARXIV_MAX_RETRIES}: {err_msg}", flush=True)
                time.sleep(wait)
            else:
                raise EvidenceResolutionError(f"arxiv source failed for {arxiv_id} after {_ARXIV_MAX_RETRIES} retries: {last_error}") from last_error


def _arxiv_cache_paths(rag_dir: Path, arxiv_id: str) -> tuple[Path, Path]:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", arxiv_id).strip("_") or "unknown"
    cache_dir = rag_dir / "reference" / "arxiv_sources"
    return cache_dir / f"{safe}.md", cache_dir / f"{safe}.manifest.json"


def _load_arxiv_cache(rag_dir: Path, arxiv_id: str, parser_version: str) -> str | None:
    cache_md, cache_manifest = _arxiv_cache_paths(rag_dir, arxiv_id)
    if not cache_md.exists() or not cache_manifest.exists():
        return None
    try:
        manifest = json.loads(cache_manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if manifest.get("cache_version") != _ARXIV_CACHE_VERSION:
        return None
    if manifest.get("arxiv_id") != arxiv_id:
        return None
    if str(manifest.get("parser_version", "")) != parser_version:
        return None
    expected = str(manifest.get("content_sha256", ""))
    content = cache_md.read_text(encoding="utf-8")
    if expected and hashlib.sha256(content.encode("utf-8")).hexdigest() != expected:
        return None
    print(f"  arxiv-source: using cached arxiv2md Markdown for {arxiv_id}", flush=True)
    return content


def _save_arxiv_cache(rag_dir: Path, arxiv_id: str, parser_version: str, content_md: str, *, dry_run: bool = False) -> None:
    cache_md, cache_manifest = _arxiv_cache_paths(rag_dir, arxiv_id)
    if dry_run:
        print(f"would write arxiv2md cache: {cache_md}")
        return
    cache_md.parent.mkdir(parents=True, exist_ok=True)
    cache_md.write_text(content_md, encoding="utf-8")
    manifest = {
        "cache_version": _ARXIV_CACHE_VERSION,
        "arxiv_id": arxiv_id,
        "parser": "arxiv2md",
        "parser_version": parser_version,
        "content_sha256": hashlib.sha256(content_md.encode("utf-8")).hexdigest(),
        "cached_markdown": _rel(cache_md, rag_dir),
        "created_at": date.today().isoformat(),
    }
    cache_manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run_pdf_to_md(pdf_path: Path, resolved: ResolvedSource) -> str:
    """Convert a PDF to Markdown via pymupdf4llm."""
    import pymupdf4llm

    print(f"  pdf-source: converting {pdf_path.name} via pymupdf4llm...", flush=True)
    content_md = pymupdf4llm.to_markdown(str(pdf_path))
    if not content_md or not content_md.strip():
        raise EvidenceResolutionError(f"pymupdf4llm produced empty content for {pdf_path.name}")

    title = resolved.title or ""
    frontmatter = f"""---
doc_id: "{resolved.doc_id}"
citation_key: "{resolved.citation_key}"
title: "{title}"
doi: "{resolved.doi}"
---

"""
    content_md = frontmatter + content_md
    print(f"  pdf-source: pymupdf4llm parsed {len(content_md)} chars", flush=True)
    return content_md


def _get_arxiv2md_version() -> str:
    try:
        import arxiv2md
        return getattr(arxiv2md, "__version__", "")
    except Exception:
        return ""


def _get_pymupdf4llm_version() -> str:
    try:
        import pymupdf4llm
        return getattr(pymupdf4llm, "__version__", "")
    except Exception:
        return ""


def register_parsed_markdown(
    resolved: ResolvedSource,
    rag_dir: Path,
    parsed_input: Path,
    *,
    parser_name: str,
    parser_version: str = "",
    dry_run: bool = False,
) -> ParsedEvidence:
    if not resolved.route:
        raise EvidenceResolutionError(f"unresolved evidence route for {resolved.citation_key}")
    if resolved.route not in (ARXIV_SOURCE, PDF_PYMUPDF, PDF_MINERU):
        raise EvidenceResolutionError(f"unsupported evidence route: {resolved.route}")
    if not parsed_input.exists():
        raise EvidenceResolutionError(f"parsed Markdown not found: {parsed_input}")

    source_path = Path(resolved.pdf_path) if resolved.pdf_path else parsed_input
    if source_path.exists():
        source_hash = sha256_file(source_path)
    else:
        source_hash = sha256_file(parsed_input)

    out_md = parsed_markdown_path(rag_dir, resolved.doc_id)
    out_manifest = parsed_manifest_path(rag_dir, resolved.doc_id)
    evidence = _build_evidence(resolved, rag_dir, out_md, parser_name, parser_version, source_hash)

    if dry_run:
        print(f"would write parsed Markdown: {out_md}")
        print(f"would write parsed manifest: {out_manifest}")
        return evidence

    out_md.parent.mkdir(parents=True, exist_ok=True)
    if parsed_input.resolve() != out_md.resolve():
        shutil.copy2(parsed_input, out_md)
    out_manifest.write_text(json.dumps(asdict(evidence), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return evidence


def _build_evidence(
    resolved: ResolvedSource,
    rag_dir: Path,
    out_md: Path,
    parser_name: str,
    parser_version: str,
    source_hash: str,
) -> ParsedEvidence:
    return ParsedEvidence(
        schema_version=PARSED_EVIDENCE_SCHEMA_VERSION,
        doc_id=resolved.doc_id,
        citation_key=resolved.citation_key,
        route=resolved.route,
        arxiv_id=resolved.arxiv_id,
        doi=resolved.doi,
        parser=parser_name,
        parser_version=parser_version,
        source_sha256=source_hash,
        parsed_markdown=_rel(out_md, rag_dir),
        original_pdf=_rel(Path(resolved.pdf_path), rag_dir) if resolved.pdf_path else "",
        original_tex=None,
        created_at=date.today().isoformat(),
    )


def _save_parsed_content(
    resolved: ResolvedSource,
    rag_dir: Path,
    content_md: str,
    parser_name: str,
    parser_version: str,
    source_hash: str,
    dry_run: bool,
) -> ParsedEvidence:
    out_md = parsed_markdown_path(rag_dir, resolved.doc_id)
    out_manifest = parsed_manifest_path(rag_dir, resolved.doc_id)
    evidence = _build_evidence(resolved, rag_dir, out_md, parser_name, parser_version, source_hash)

    if dry_run:
        print(f"would write parsed Markdown ({len(content_md)} chars): {out_md}")
        print(f"would write parsed manifest: {out_manifest}")
        return evidence

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(content_md, encoding="utf-8")
    out_manifest.write_text(json.dumps(asdict(evidence), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return evidence


def parse_evidence(
    resolved: ResolvedSource,
    rag_dir: Path,
    *,
    pdf_output: Path | None = None,
    arxiv_output: Path | None = None,
    fallback_pdf_on_arxiv_fail: bool = False,
    dry_run: bool = False,
) -> ParsedEvidence:
    if resolved.route == ARXIV_SOURCE:
        parser_version = _get_arxiv2md_version()
        if arxiv_output is not None:
            return register_parsed_markdown(
                resolved, rag_dir, arxiv_output,
                parser_name="arxiv2md", parser_version=parser_version, dry_run=dry_run,
            )

        cached = _load_arxiv_cache(rag_dir, resolved.arxiv_id, parser_version)
        if cached is not None:
            content_md = cached
        else:
            try:
                content_md = _run_arxiv2md(resolved.arxiv_id)
            except EvidenceResolutionError:
                if not fallback_pdf_on_arxiv_fail:
                    raise
                pdf_path = rag_dir / resolved.pdf_path if resolved.pdf_path else None
                if pdf_path is None or not pdf_path.exists():
                    raise
                print(f"  arxiv-source: falling back to local PDF for {resolved.citation_key}", flush=True)
                fallback = ResolvedSource(
                    doc_id=resolved.doc_id,
                    citation_key=resolved.citation_key,
                    arxiv_id=resolved.arxiv_id,
                    doi=resolved.doi,
                    title=resolved.title,
                    pdf_path=resolved.pdf_path,
                    route=PDF_PYMUPDF,
                    needs_review=resolved.needs_review,
                    metadata_conflicts=resolved.metadata_conflicts + ["arxiv_source_failed; used local PDF fallback"],
                )
                parser_version = _get_pymupdf4llm_version()
                content_md = _run_pdf_to_md(pdf_path, fallback)
                source_hash = sha256_file(pdf_path)
                return _save_parsed_content(fallback, rag_dir, content_md, "pymupdf4llm", parser_version, source_hash, dry_run)
            _save_arxiv_cache(rag_dir, resolved.arxiv_id, parser_version, content_md, dry_run=dry_run)
        source_hash = hashlib.sha256(content_md.encode("utf-8")).hexdigest()
        if resolved.pdf_path:
            pdf_path = rag_dir / resolved.pdf_path
            if pdf_path.exists():
                source_hash = sha256_file(pdf_path)
        return _save_parsed_content(resolved, rag_dir, content_md, "arxiv2md", parser_version, source_hash, dry_run)

    if resolved.route in (PDF_PYMUPDF, PDF_MINERU):
        parser_version = _get_pymupdf4llm_version()
        if pdf_output is not None:
            return register_parsed_markdown(
                resolved, rag_dir, pdf_output,
                parser_name="pymupdf4llm", parser_version=parser_version, dry_run=dry_run,
            )

        pdf_path = rag_dir / resolved.pdf_path if resolved.pdf_path else None
        if pdf_path is None or not pdf_path.exists():
            raise EvidenceResolutionError(f"PDF not found for {resolved.citation_key}, provide --pdf-output to register parsed Markdown")
        content_md = _run_pdf_to_md(pdf_path, resolved)
        source_hash = sha256_file(pdf_path)
        return _save_parsed_content(resolved, rag_dir, content_md, "pymupdf4llm", parser_version, source_hash, dry_run)
    raise EvidenceResolutionError(f"unresolved evidence route for {resolved.citation_key}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Register or run evidence parsing into DARW")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", required=True)
    parser.add_argument("--pdf-output", default="")
    parser.add_argument("--mineru-output", default="", help="Deprecated alias for --pdf-output")
    parser.add_argument("--arxiv-output", default="")
    parser.add_argument("--parser-version", default="")
    parser.add_argument(
        "--fallback-pdf-on-arxiv-fail",
        action="store_true",
        help="If arXiv parsing fails and a local PDF exists, explicitly allow PDF fallback",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    resolved = resolve_key(rag_dir, args.key)
    if resolved is None:
        print(f"BibTeX entry not found: {args.key}")
        return 1
    try:
        evidence = parse_evidence(
            resolved,
            rag_dir,
            pdf_output=Path(args.pdf_output or args.mineru_output).resolve() if (args.pdf_output or args.mineru_output) else None,
            arxiv_output=Path(args.arxiv_output).resolve() if args.arxiv_output else None,
            fallback_pdf_on_arxiv_fail=args.fallback_pdf_on_arxiv_fail,
            dry_run=args.dry_run,
        )
    except EvidenceResolutionError as exc:
        print(str(exc))
        return 1
    print(json.dumps(asdict(evidence), indent=2, ensure_ascii=False))
    if args.dry_run:
        print("[dry-run] no files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
