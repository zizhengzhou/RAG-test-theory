"""Search external providers and add selected papers to RAG."""

from __future__ import annotations

import argparse
from pathlib import Path

from bib_parser import parse_bibtex, parse_bibtex_file, render_bibtex
from common import append_log
from dedup import entry_dedup_key
from external_search import SearchResult, fetch_inspire_bibtex, search_inspire
from source_page_builder import default_frontmatter, body_skeleton
from pdf_downloader import download_arxiv_pdf
from update_index import collect_edge_tags, ensure_category_page, rebuild_auto_block


def _manifest_path(rag_dir: Path) -> Path:
    return rag_dir / "references.bib"


def _existing_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = _manifest_path(rag_dir)
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _refresh_indexes(rag_dir: Path) -> int:
    tag_map = collect_edge_tags(rag_dir)
    updated = 0
    for category, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_category_page(rag_dir, category, tag)
            if rebuild_auto_block(page, category, tag, source_keys):
                updated += 1
    return updated


def _select_result(args: argparse.Namespace) -> SearchResult | None:
    if args.record_id:
        results = search_inspire(f"recid:{args.record_id}", size=1)
        return results[0] if results else None
    results = search_inspire(args.query, size=max(args.select, args.limit))
    if not results:
        return None
    index = args.select - 1
    if index < 0 or index >= len(results):
        raise ValueError(f"--select {args.select} is outside search result range 1..{len(results)}")
    return results[index]


def _print_result(result: SearchResult, index: int) -> None:
    authors = ", ".join(result.authors[:3])
    suffix = " et al." if len(result.authors) > 3 else ""
    print(f"[{index}] INSPIRE:{result.record_id} {result.title} ({result.year})")
    if authors:
        print(f"    authors: {authors}{suffix}")
    if result.arxiv:
        print(f"    arxiv: {result.arxiv}")
    if result.doi:
        print(f"    doi: {result.doi}")
    if result.pdf_url:
        print(f"    pdf: {result.pdf_url}")


def command_search(args: argparse.Namespace) -> int:
    if not args.query:
        print("provide --query")
        return 1
    results = search_inspire(args.query, size=args.limit)
    if not results:
        print("no INSPIRE candidates found")
        return 1
    for i, result in enumerate(results, 1):
        _print_result(result, i)
    return 0


def _require_yes(args: argparse.Namespace) -> bool:
    if args.dry_run or args.yes:
        return True
    print("Refusing to write without --yes. Run --dry-run first and confirm the selected candidate.")
    return False


def _write_source_if_missing(rag_dir: Path, entry: dict[str, str]) -> bool:
    sources_dir = rag_dir / "summary" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    key = entry.get("ID", "unknown")
    page_path = sources_dir / f"{key}.md"
    if page_path.exists():
        return False
    fm = default_frontmatter(entry, rag_dir)
    body = body_skeleton(entry, rag_dir)
    page_path.write_text(render_source(fm, body), encoding="utf-8")
    return True


def render_source(fm: dict[str, object], body: str) -> str:
    from common import write_frontmatter

    return write_frontmatter(fm) + f"# {fm.get('title', 'Untitled')}\n" + body + "\n"


def command_add(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    try:
        result = _select_result(args)
    except ValueError as exc:
        print(str(exc))
        return 1
    if not result:
        print("no INSPIRE candidate selected")
        return 1

    bibtex = fetch_inspire_bibtex(result.record_id)
    entries = parse_bibtex(bibtex)
    if not entries:
        print("INSPIRE BibTeX could not be parsed")
        return 1
    entry = entries[0]
    key = entry.get("ID", result.record_id)
    existing = _existing_entries(rag_dir)
    existing_keys = {entry_dedup_key(item): item for item in existing}
    dedup_key = entry_dedup_key(entry)
    duplicate = existing_keys.get(dedup_key)
    effective_key = duplicate.get("ID", key) if duplicate else key
    pdf_path = rag_dir / "reference" / "pdfs" / f"{effective_key}.pdf"
    source_path = rag_dir / "summary" / "sources" / f"{effective_key}.md"

    print(f"search-and-add plan for INSPIRE:{result.record_id}")
    print(f"- title: {result.title}")
    print(f"- BibTeX key: {key}")
    print(f"- duplicate: {duplicate.get('ID') if duplicate else 'no'}")
    print(f"- manifest append: {'no' if duplicate else 'yes'}")
    print(f"- PDF: {result.pdf_url or 'not available'} -> {pdf_path}")
    print(f"- source page: {source_path}")
    if args.dry_run:
        print("[dry-run] no files written")
        return 0
    if not _require_yes(args):
        return 2

    manifest = _manifest_path(rag_dir)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if not manifest.exists():
        manifest.write_text("", encoding="utf-8")
    if not duplicate:
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write(bibtex.strip())
            handle.write("\n\n")
    if result.arxiv and not pdf_path.exists():
        download_arxiv_pdf(result.arxiv, pdf_path, dry_run=False)
    if duplicate:
        entry = duplicate
    created_source = _write_source_if_missing(rag_dir, entry)
    updated = _refresh_indexes(rag_dir)
    append_log(
        rag_dir,
        "search-and-add",
        f"provider=inspire record_id={result.record_id}",
        f"key={effective_key} duplicate={bool(duplicate)} source_created={created_source} updated_indexes={updated}",
    )
    print(f"added: {effective_key} duplicate={bool(duplicate)} source_created={created_source} updated_indexes={updated}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search providers and add selected records to RAG")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=5)
    search_parser.set_defaults(func=command_search)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--rag-dir", default="RAG")
    add_parser.add_argument("--query", default="")
    add_parser.add_argument("--record-id", default="")
    add_parser.add_argument("--select", type=int, default=1)
    add_parser.add_argument("--limit", type=int, default=5)
    add_parser.add_argument("--dry-run", action="store_true")
    add_parser.add_argument("--yes", action="store_true")
    add_parser.set_defaults(func=command_add)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "add" and not args.query and not args.record_id:
        print("provide --query or --record-id")
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
