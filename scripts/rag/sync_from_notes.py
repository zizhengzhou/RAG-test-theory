"""Sync knowledge from project notes into RAG synthesis pages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from datetime import date

from common import append_log

MARKER_RE = re.compile(r"^(?:- |\* |\d+\. )?(Decision|Consensus|Open question|Failed|Dispute|Finding):\s*(.+)", re.IGNORECASE)
CITE_RE = re.compile(r"\[@(?P<key>[\w:-]+)\]")


def extract_from_note(note_path: Path, base_dir: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    import os
    rel = Path(os.path.relpath(str(note_path.resolve()), str(base_dir.resolve())))
    for raw_line in note_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        match = MARKER_RE.search(line)
        if match:
            cate = match.group(1).strip().lower()
            body = match.group(2).strip()
            cites = [m.group("key") for m in CITE_RE.finditer(line)]
            items.append({"category": cate, "text": body, "citations": cites, "note": rel.as_posix()})
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync project notes into RAG synthesis")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--notes-dir", required=True, help="Directory containing notes")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    notes_dir = Path(args.notes_dir).resolve()
    synthesis_dir = rag_dir / "summary" / "synthesis"
    synthesis_dir.mkdir(parents=True, exist_ok=True)

    if not notes_dir.exists():
        print(f"notes-dir not found: {notes_dir}")
        return 1

    all_items: list[dict[str, object]] = []
    for note_path in notes_dir.rglob("*.md"):
        items = extract_from_note(note_path, rag_dir)
        all_items.extend(items)

    if not all_items:
        print("no items extracted")
        return 0

    out_path = synthesis_dir / "notes-sync.md"
    lines = [
        "---",
        f"type: synthesis",
        f"created: {date.today().isoformat()}",
        'source: "notes-sync"',
        "---",
        "",
        "# Notes Sync",
        "",
        "Auto-extracted from project notes.",
        "",
    ]
    for item in all_items:
        category = str(item["category"]).capitalize()
        text = item["text"]
        cites = ", ".join(f"[@{c}]" for c in item["citations"]) if item["citations"] else ""
        note = item["note"]
        lines.append(f"- **{category}**: {text} {cites} _(from `{note}`)_")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_log(rag_dir, "sync-from-notes", f"notes_dir={notes_dir}", f"items={len(all_items)}")
    print(f"sync-from-notes: {len(all_items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
