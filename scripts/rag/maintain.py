"""Maintain RAG source pages, metadata, and local artifacts."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

from bib_parser import parse_bibtex_file, render_bibtex
from common import append_log, read_frontmatter, write_frontmatter
from ingest import default_frontmatter, body_skeleton
from pdf_validator import is_pdf
from update_index import collect_dimension_tags, ensure_dimension_page, rebuild_auto_block


CORE_FIELDS = {"type", "created", "last_updated", "title", "authors", "year", "venue", "doi", "arxiv", "pdf"}


def _manifest_path(rag_dir: Path) -> Path:
    return rag_dir / "references.bib"


def _sources_dir(rag_dir: Path) -> Path:
    return rag_dir / "summary" / "sources"


def _source_path(rag_dir: Path, key: str) -> Path:
    return _sources_dir(rag_dir) / f"{key}.md"


def _pdf_path(rag_dir: Path, key: str) -> Path:
    return rag_dir / "reference" / "pdfs" / f"{key}.pdf"


def _load_entries(rag_dir: Path) -> list[dict[str, str]]:
    manifest = _manifest_path(rag_dir)
    if not manifest.exists():
        return []
    return parse_bibtex_file(manifest)


def _find_entry(entries: list[dict[str, str]], key: str) -> dict[str, str] | None:
    for entry in entries:
        if entry.get("ID") == key:
            return entry
    return None


def _write_manifest(rag_dir: Path, entries: list[dict[str, str]]) -> None:
    text = ""
    for entry in entries:
        text += render_bibtex(entry) + "\n\n"
    _manifest_path(rag_dir).write_text(text, encoding="utf-8")


def _relative(path: Path, rag_dir: Path) -> str:
    try:
        return path.resolve().relative_to(rag_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _find_references(rag_dir: Path, key: str) -> tuple[list[Path], list[Path]]:
    dimension_refs: list[Path] = []
    synthesis_refs: list[Path] = []
    needles = [key, f"../sources/{key}", f"sources/{key}", f"{key}.md"]
    for page in rag_dir.rglob("*.md"):
        if page == _source_path(rag_dir, key):
            continue
        text = page.read_text(encoding="utf-8")
        if not any(needle in text for needle in needles):
            continue
        try:
            rel = page.relative_to(rag_dir)
        except ValueError:
            rel = page
        if len(rel.parts) >= 2 and rel.parts[0] == "summary" and rel.parts[1] == "synthesis":
            synthesis_refs.append(page)
        else:
            dimension_refs.append(page)
    return dimension_refs, synthesis_refs


def _refresh_indexes(rag_dir: Path) -> int:
    tag_map = collect_dimension_tags(rag_dir)
    updated = 0
    for axis, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_dimension_page(rag_dir, axis, tag)
            if rebuild_auto_block(page, axis, tag, source_keys):
                updated += 1
    return updated


def _require_yes(args: argparse.Namespace) -> bool:
    if args.dry_run:
        return True
    if args.yes:
        return True
    print("Refusing to modify files without --yes. Run with --dry-run first, then add --yes after reviewing the plan.")
    return False


def remove_source(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    key = args.key
    entries = _load_entries(rag_dir)
    entry = _find_entry(entries, key)
    source = _source_path(rag_dir, key)
    pdf = _pdf_path(rag_dir, key)
    dimension_refs, synthesis_refs = _find_references(rag_dir, key)

    print(f"remove plan for {key}:")
    print(f"- BibTeX entry: {'yes' if entry else 'not found'}")
    print(f"- source page: {_relative(source, rag_dir) if source.exists() else 'not found'}")
    print(f"- PDF: {_relative(pdf, rag_dir) if pdf.exists() else 'not found'}")
    if dimension_refs:
        print("- dimension/index references:")
        for page in dimension_refs:
            print(f"  - {_relative(page, rag_dir)}")
    else:
        print("- dimension/index references: none")
    if synthesis_refs:
        print("- synthesis pages for manual review:")
        for page in synthesis_refs:
            print(f"  - {_relative(page, rag_dir)}")
    else:
        print("- synthesis pages for manual review: none")

    if args.dry_run:
        print("[dry-run] no files written")
        return 0
    if not _require_yes(args):
        return 2

    changed: list[str] = []
    if entry:
        _write_manifest(rag_dir, [e for e in entries if e.get("ID") != key])
        changed.append("manifest")
    if source.exists():
        source.unlink()
        changed.append("source")
    if pdf.exists():
        pdf.unlink()
        changed.append("pdf")
    updated = _refresh_indexes(rag_dir)
    append_log(rag_dir, "remove", f"key={key}", f"changed={','.join(changed) or 'none'} updated_indexes={updated} synthesis_review={len(synthesis_refs)}")
    print(f"removed {key}: changed={','.join(changed) or 'none'} updated_indexes={updated}")
    if synthesis_refs:
        print("synthesis pages were not deleted; review them manually")
    return 0


def _parse_value(raw: str, existing: object | None) -> object:
    if isinstance(existing, list):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if raw.startswith("[") and raw.endswith("]"):
        return [item.strip().strip('"\'') for item in raw[1:-1].split(",") if item.strip()]
    return raw


def _write_source_page(path: Path, fm: dict[str, object], body: str) -> None:
    text = write_frontmatter(fm) + body
    path.write_text(text, encoding="utf-8")


def update_source(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    source = _source_path(rag_dir, args.key)
    if not source.exists():
        print(f"source page not found: {_relative(source, rag_dir)}")
        return 1
    if not args.set_values:
        print("no --set field=value values provided")
        return 1
    fm, body = read_frontmatter(source)
    updates: dict[str, object] = {}
    for assignment in args.set_values:
        if "=" not in assignment:
            print(f"invalid --set value, expected field=value: {assignment}")
            return 1
        field, raw_value = assignment.split("=", 1)
        field = field.strip()
        if field not in fm and not args.allow_new_field:
            print(f"field does not exist in source frontmatter: {field}")
            return 1
        updates[field] = _parse_value(raw_value.strip(), fm.get(field))

    print(f"update-source plan for {args.key}:")
    for field, value in updates.items():
        print(f"- {field}: {fm.get(field, '<missing>')} -> {value}")
    if args.dry_run:
        print("[dry-run] no files written")
        return 0
    if not _require_yes(args):
        return 2

    fm.update(updates)
    fm["last_updated"] = date.today().isoformat()
    _write_source_page(source, fm, body)
    updated = _refresh_indexes(rag_dir)
    append_log(rag_dir, "update-source", f"key={args.key}", f"fields={','.join(updates)} updated_indexes={updated}")
    print(f"updated source {args.key}: fields={','.join(updates)} updated_indexes={updated}")
    return 0


def _copy_replacement_pdf(pdf_path: Path, rag_dir: Path, key: str, dry_run: bool) -> bool:
    if not pdf_path.exists() or not is_pdf(pdf_path):
        raise ValueError(f"replacement PDF is missing or invalid: {pdf_path}")
    dest = _pdf_path(rag_dir, key)
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, dest)
    return True


def re_ingest(args: argparse.Namespace) -> int:
    rag_dir = Path(args.rag_dir).resolve()
    entries = _load_entries(rag_dir)
    entry = _find_entry(entries, args.key)
    if not entry:
        print(f"BibTeX entry not found: {args.key}")
        return 1
    source = _source_path(rag_dir, args.key)
    existing_fm: dict[str, object] = {}
    existing_body = ""
    if source.exists():
        existing_fm, existing_body = read_frontmatter(source)

    defaults = default_frontmatter(entry, rag_dir)
    merged = dict(defaults)
    merged.update(existing_fm)
    changed_fields = [field for field in defaults if field not in existing_fm]
    merged["last_updated"] = date.today().isoformat()
    body = existing_body if existing_body.strip() else f"# {merged.get('title', source.stem)}" + body_skeleton(entry, rag_dir) + "\n"

    print(f"re-ingest plan for {args.key}:")
    print(f"- source page: {_relative(source, rag_dir)}")
    print(f"- missing frontmatter fields to add: {', '.join(changed_fields) if changed_fields else 'none'}")
    if args.replace_pdf:
        print(f"- replace PDF: {args.replace_pdf} -> {_relative(_pdf_path(rag_dir, args.key), rag_dir)}")
        try:
            _copy_replacement_pdf(Path(args.replace_pdf).resolve(), rag_dir, args.key, dry_run=True)
        except ValueError as exc:
            print(str(exc))
            return 1
    if args.overwrite_generated:
        print("- overwrite-generated requested, but narrative section rewriting is not implemented in this conservative slice")
    if args.dry_run:
        print("[dry-run] no files written")
        return 0
    if not _require_yes(args):
        return 2

    if args.replace_pdf:
        _copy_replacement_pdf(Path(args.replace_pdf).resolve(), rag_dir, args.key, dry_run=False)
    source.parent.mkdir(parents=True, exist_ok=True)
    _write_source_page(source, merged, body)
    updated = _refresh_indexes(rag_dir)
    append_log(rag_dir, "re-ingest", f"key={args.key}", f"added_fields={','.join(changed_fields) or 'none'} replace_pdf={bool(args.replace_pdf)} updated_indexes={updated}")
    print(f"re-ingested {args.key}: added_fields={','.join(changed_fields) or 'none'} updated_indexes={updated}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain RAG source pages and artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    remove_parser = subparsers.add_parser("remove", help="Remove a source from manifest, source pages, and local PDFs")
    remove_parser.add_argument("--rag-dir", default="RAG")
    remove_parser.add_argument("--key", required=True)
    remove_parser.add_argument("--dry-run", action="store_true")
    remove_parser.add_argument("--yes", action="store_true")
    remove_parser.set_defaults(func=remove_source)

    update_parser = subparsers.add_parser("update-source", help="Update source frontmatter fields")
    update_parser.add_argument("--rag-dir", default="RAG")
    update_parser.add_argument("--key", required=True)
    update_parser.add_argument("--set", dest="set_values", action="append", default=[])
    update_parser.add_argument("--allow-new-field", action="store_true")
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--yes", action="store_true")
    update_parser.set_defaults(func=update_source)

    reingest_parser = subparsers.add_parser("re-ingest", help="Refresh source metadata defaults and optionally replace PDF")
    reingest_parser.add_argument("--rag-dir", default="RAG")
    reingest_parser.add_argument("--key", required=True)
    reingest_parser.add_argument("--replace-pdf", default="")
    reingest_parser.add_argument("--overwrite-generated", action="store_true")
    reingest_parser.add_argument("--dry-run", action="store_true")
    reingest_parser.add_argument("--yes", action="store_true")
    reingest_parser.set_defaults(func=re_ingest)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
