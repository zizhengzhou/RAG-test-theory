"""Generate RAG source pages from references manifest entries."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from bib_parser import parse_bibtex_file
from common import append_log, write_frontmatter


def _template_frontmatter_defaults(rag_dir: Path) -> dict[str, object]:
    template_path = rag_dir / "template.md"
    if not template_path.exists():
        return {}
    text = template_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    start = text.find("---")
    end = text.find("---", start + 3)
    if start == -1 or end == -1:
        return {}
    defaults: dict[str, object] = {}
    for raw_line in text[start + 3:end].splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"type", "created", "last_updated", "title", "authors", "year", "venue", "doi", "arxiv", "pdf"}:
            continue
        if value.startswith("[") and value.endswith("]"):
            defaults[key] = ["uncategorized"]
        else:
            defaults[key] = ""
    return defaults


def default_frontmatter(entry: dict[str, str], rag_dir: Path | None = None) -> dict[str, object]:
    today = date.today().isoformat()
    year = entry.get("year", "").strip()
    if not year:
        date_val = entry.get("date", "").strip()
        if date_val:
            year = date_val[:4] if len(date_val) >= 4 else date_val
    title = entry.get("title", "").strip().replace("{", "").replace("}", "")
    fm = {
        "type": "source",
        "created": today,
        "last_updated": today,
        "title": title,
        "authors": [a.strip() for a in entry.get("author", "").replace("{", "").replace("}", "").split(" and ") if a.strip()],
        "year": year,
        "doi": entry.get("doi", "").strip(),
        "arxiv": (entry.get("eprint") or "").strip(),
        "pdf": f"../../reference/pdfs/{entry.get('ID', 'unknown')}.pdf",
    }
    if rag_dir is not None:
        fm.update(_template_frontmatter_defaults(rag_dir))
    return fm


def body_skeleton(entry: dict[str, str], rag_dir: Path | None = None) -> str:
    if rag_dir is None:
        rag_dir = Path("RAG")
    template_path = rag_dir / "template.md"
    if template_path.exists():
        text = template_path.read_text(encoding="utf-8")
        sections = [line for line in text.splitlines() if line.startswith("## ") and " " in line]
        parts = [f"\n\n## Summary\n\n_No summary yet._"]
        for section in sections[1:]:
            parts.append(f"\n\n{section.rstrip()}\n\n_To be filled._")
        return "".join(parts)
    return "\n\n## Summary\n\n_No summary yet._\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest bibliographic entries into source pages")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    manifest = rag_dir / "references.bib"
    sources_dir = rag_dir / "summary" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        print(f"No {manifest}")
        return 1

    entries = parse_bibtex_file(manifest)
    created = 0
    skipped = 0
    for entry in entries:
        key = entry.get("ID", "unknown")
        page_path = sources_dir / f"{key}.md"
        if page_path.exists():
            skipped += 1
            continue
        fm = default_frontmatter(entry, rag_dir)
        body = body_skeleton(entry, rag_dir)
        content = write_frontmatter(fm) + f"\n# {fm['title']}\n" + body + "\n"
        page_path.write_text(content, encoding="utf-8")
        created += 1

    append_log(rag_dir, "ingest", f"manifest={manifest}", f"created={created} skipped={skipped}")
    print(f"created={created} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
