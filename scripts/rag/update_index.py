"""Rebuild auto-generated index blocks on dimension pages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from datetime import date

import yaml

from common import read_frontmatter, append_log

AUTO_BEGIN = "<!-- AUTO:BEGIN -->"
AUTO_END = "<!-- AUTO:END -->"


def load_dimension_axes(rag_dir: Path) -> set[str]:
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
    vocab = data.get("vocabulary", data) if isinstance(data, dict) else {}
    if not isinstance(vocab, dict):
        return set()
    return {axis for axis, entries in vocab.items() if isinstance(entries, dict)}


def collect_dimension_tags(rag_dir: Path) -> dict[str, dict[str, list[str]]]:
    tag_map: dict[str, dict[str, list[str]]] = {}
    allowed_axes = load_dimension_axes(rag_dir)
    if not allowed_axes:
        return tag_map
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return tag_map
    for page_path in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page_path)
        for axis in allowed_axes:
            value = fm.get(axis, [])
            if not isinstance(value, list):
                continue
            for tag in value:
                tag = tag.strip().strip('"')
                if not tag:
                    continue
                tag_map.setdefault(axis, {})
                tag_map[axis].setdefault(tag, [])
                tag_map[axis][tag].append(page_path.stem)
    return tag_map


def ensure_dimension_page(rag_dir: Path, axis: str, tag: str) -> Path:
    dim_dir = rag_dir / "summary" / axis
    dim_dir.mkdir(parents=True, exist_ok=True)
    page = dim_dir / f"{tag}.md"
    if not page.exists():
        today = date.today().isoformat()
        page.write_text(
            f"---\ntype: {axis[:-1]}\nslug: {tag}\ncreated: {today}\nlast_updated: {today}\nlast_indexed: {today}\n---\n\n"
            f"# {tag}\n\n_Manual prose here._\n\n{AUTO_BEGIN}\n## Papers using this tag (0)\n\n{AUTO_END}\n",
            encoding="utf-8",
        )
    return page


def rebuild_auto_block(page_path: Path, axis: str, tag: str, source_keys: list[str]) -> bool:
    text = page_path.read_text(encoding="utf-8")
    begin_idx = text.find(AUTO_BEGIN)
    end_idx = text.find(AUTO_END)
    if begin_idx == -1 or end_idx == -1:
        return False
    before = text[:begin_idx + len(AUTO_BEGIN)]
    after = text[end_idx:]

    lines = [
        f"\n## Papers using this tag ({len(source_keys)})",
    ]
    for key in source_keys:
        lines.append(f"- [[../sources/{key}]]")
    lines.append("")
    new_block = "\n".join(lines)
    new_text = before + new_block + after
    page_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update AUTO index blocks on dimension pages")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    tag_map = collect_dimension_tags(rag_dir)
    updated = 0
    for axis, tags in tag_map.items():
        for tag, source_keys in tags.items():
            page = ensure_dimension_page(rag_dir, axis, tag)
            if rebuild_auto_block(page, axis, tag, source_keys):
                updated += 1

    append_log(rag_dir, "update-index", "", f"updated={updated} pages")
    print(f"update-index: updated {updated} dimension pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
