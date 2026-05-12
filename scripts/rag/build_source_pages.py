"""Create metadata-only DARW source-page stubs from references.bib."""

from __future__ import annotations

import argparse
from pathlib import Path

from bib_parser import parse_bibtex_file
from common import append_log
from source_page_builder import body_skeleton, default_frontmatter, format_frontmatter


def build_source_pages(rag_dir: Path) -> tuple[int, int]:
    manifest = rag_dir / "references.bib"
    sources_dir = rag_dir / "summary" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        raise FileNotFoundError(f"No {manifest}")

    created = 0
    skipped = 0
    for entry in parse_bibtex_file(manifest):
        key = entry.get("ID", "unknown")
        page_path = sources_dir / f"{key}.md"
        if page_path.exists():
            skipped += 1
            continue
        page_path.write_text(
            format_frontmatter(default_frontmatter(entry, rag_dir)) + body_skeleton(entry, rag_dir),
            encoding="utf-8",
        )
        created += 1
    append_log(rag_dir, "build-source-pages", f"manifest={manifest}", f"created={created} skipped={skipped}")
    return created, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Build metadata-only DARW source pages from references.bib")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    try:
        created, skipped = build_source_pages(rag_dir)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    print(f"created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
