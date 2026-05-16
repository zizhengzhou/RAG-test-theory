"""Rebuild auto-generated index blocks on edge-category pages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from datetime import date

import yaml

from common import read_frontmatter, append_log

AUTO_BEGIN = "<!-- AUTO:BEGIN -->"
AUTO_END = "<!-- AUTO:END -->"
SOURCE_AUTO_BEGIN = "<!-- AUTO:SOURCES:BEGIN -->"
SOURCE_AUTO_END = "<!-- AUTO:SOURCES:END -->"


def load_vocabulary_categories(rag_dir: Path) -> set[str]:
    """Return the set of edge categories defined in vocabulary.md."""
    vocab_file = rag_dir / "vocabulary.md"
    if not vocab_file.exists():
        return set()
    text = vocab_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return set()
    try:
        data = yaml.safe_load(match.group(1))
    except Exception:
        return set()
    if isinstance(data, dict):
        terms = data.get("terms", [])
        if isinstance(terms, list):
            return {t["category"] for t in terms if isinstance(t, dict) and "category" in t}
    return set()


def collect_edge_tags(rag_dir: Path) -> dict[str, dict[str, list[str]]]:
    """Collect canonical_id values from source page ``edges`` frontmatter, grouped by category."""
    tag_map: dict[str, dict[str, list[str]]] = {}
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return tag_map
    for page_path in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page_path)
        edges = fm.get("edges")
        if not isinstance(edges, dict):
            continue
        for category, entries in edges.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    cid = entry.get("canonical_id", "")
                elif isinstance(entry, str):
                    cid = entry
                else:
                    continue
                cid = str(cid).strip()
                if not cid:
                    continue
                tag_map.setdefault(category, {})
                tag_map[category].setdefault(cid, [])
                tag_map[category][cid].append(page_path.stem)
    return tag_map


def ensure_category_page(rag_dir: Path, category: str, tag: str) -> Path:
    cat_dir = rag_dir / "summary" / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    page = cat_dir / f"{tag.replace(':', '_').replace('/', '_')}.md"
    if not page.exists():
        today = date.today().isoformat()
        page.write_text(
            f"---\ntype: edge-index\ncategory: {category}\ncanonical_id: {tag}\ncreated: {today}\nlast_indexed: {today}\n---\n\n"
            f"# {tag}\n\n_Manual prose here._\n\n{AUTO_BEGIN}\n## Source pages (0)\n\n{AUTO_END}\n",
            encoding="utf-8",
        )
    return page


def rebuild_auto_block(page_path: Path, category: str, tag: str, source_keys: list[str]) -> bool:
    text = page_path.read_text(encoding="utf-8")
    begin_idx = text.find(AUTO_BEGIN)
    end_idx = text.find(AUTO_END)
    if begin_idx == -1 or end_idx == -1:
        return False
    before = text[:begin_idx + len(AUTO_BEGIN)]
    after = text[end_idx:]

    lines = [
        f"\n## Source pages ({len(source_keys)})",
    ]
    for key in sorted(source_keys):
        lines.append(f"- [[../sources/{key}]]")
    lines.append("")
    new_block = "\n".join(lines)
    new_text = before + new_block + after
    page_path.write_text(new_text, encoding="utf-8")
    return True


def rebuild_source_index(rag_dir: Path) -> bool:
    index_path = rag_dir / "index.md"
    sources_dir = rag_dir / "summary" / "sources"
    if not index_path.exists() or not sources_dir.is_dir():
        return False
    text = index_path.read_text(encoding="utf-8")
    begin_idx = text.find(SOURCE_AUTO_BEGIN)
    end_idx = text.find(SOURCE_AUTO_END)
    if begin_idx == -1 or end_idx == -1:
        return False
    source_pages = sorted(sources_dir.glob("*.md"))
    if source_pages:
        lines = [""]
        for page in source_pages:
            lines.append(f"- [{page.stem}](summary/sources/{page.name})")
        lines.append("")
    else:
        lines = ["", "No source pages indexed yet.", ""]
    new_block = "\n".join(lines)
    new_text = text[: begin_idx + len(SOURCE_AUTO_BEGIN)] + new_block + text[end_idx:]
    index_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update AUTO index blocks on edge-category pages")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    tag_map = collect_edge_tags(rag_dir)
    if not tag_map:
        print("update-index: no edge tags found in source pages")
        return 0

    updated = 0
    for category, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_category_page(rag_dir, category, tag)
            if rebuild_auto_block(page, category, tag, source_keys):
                updated += 1

    source_index_updated = rebuild_source_index(rag_dir)
    append_log(rag_dir, "update-index", "", f"updated={updated} pages source_index={source_index_updated}")
    suffix = " and source index" if source_index_updated else ""
    print(f"update-index: updated {updated} edge-category pages{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
