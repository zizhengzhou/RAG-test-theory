"""Sync knowledge from project notes into RAG synthesis pages."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from datetime import date

from common import append_log

MARKER_RE = re.compile(r"^(?:- |\* |\d+\. )?(Decision|Consensus|Open question|Failed|Dispute|Finding|Method):\s*(.+)", re.IGNORECASE)
CITE_RE = re.compile(r"\[@(?P<key>[\w:-]+)\]")


def _bucket(category: str) -> str:
    value = category.strip().lower()
    if value == "decision":
        return "decisions"
    if value == "method":
        return "methods"
    if value == "failed":
        return "failures"
    if value in {"open question", "dispute"}:
        return "open_questions"
    return "claims"


def _item_id(note: str, line: int, text: str) -> str:
    digest = hashlib.sha1(f"{note}:{line}:{text}".encode("utf-8", "replace")).hexdigest()[:10]
    return f"note:{digest}"


def extract_from_note(note_path: Path, base_dir: Path) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    import os
    rel = Path(os.path.relpath(str(note_path.resolve()), str(base_dir.resolve())))
    heading = ""
    for line_no, raw_line in enumerate(note_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        match = MARKER_RE.search(line)
        if match:
            cate = match.group(1).strip().lower()
            body = match.group(2).strip()
            cites = [m.group("key") for m in CITE_RE.finditer(line)]
            note = rel.as_posix()
            items.append(
                {
                    "id": _item_id(note, line_no, body),
                    "category": cate,
                    "bucket": _bucket(cate),
                    "text": body,
                    "citations": cites,
                    "note": note,
                    "heading": heading,
                    "line": line_no,
                }
            )
    return items


def _render_items(items: list[dict[str, object]]) -> str:
    lines = [
        "---",
        "type: synthesis",
        f"created: {date.today().isoformat()}",
        'source: "notes-sync"',
        "---",
        "",
        "# Notes Sync",
        "",
        "Auto-extracted from project notes.",
        "",
    ]
    labels = {
        "claims": "Claims",
        "methods": "Methods",
        "failures": "Failures",
        "decisions": "Decisions",
        "open_questions": "Open Questions",
    }
    for bucket, label in labels.items():
        bucket_items = [item for item in items if item.get("bucket") == bucket]
        if not bucket_items:
            continue
        lines.append(f"## {label}")
        for item in bucket_items:
            cites = ", ".join(f"[@{c}]" for c in item["citations"]) if item["citations"] else ""
            heading = f" > {item['heading']}" if item.get("heading") else ""
            lines.append(
                f"- <!-- {item['id']} --> **{str(item['category']).capitalize()}**: {item['text']} {cites} "
                f"_(from `{item['note']}`:{item['line']}{heading})_"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def sync_notes(rag_dir: Path, notes_dir: Path) -> tuple[Path, int]:
    synthesis_dir = rag_dir / "summary" / "synthesis"
    synthesis_dir.mkdir(parents=True, exist_ok=True)
    all_items: list[dict[str, object]] = []
    for note_path in notes_dir.rglob("*.md"):
        all_items.extend(extract_from_note(note_path, rag_dir))
    out_path = synthesis_dir / "notes-sync.md"
    existing_ids: set[str] = set()
    if out_path.exists():
        existing_ids = set(re.findall(r"<!--\s*(note:[a-f0-9]+)\s*-->", out_path.read_text(encoding="utf-8")))
    unique: dict[str, dict[str, object]] = {}
    for item in all_items:
        unique[str(item["id"])] = item
    out_path.write_text(_render_items(list(unique.values())), encoding="utf-8")
    new_count = len(set(unique) - existing_ids)
    return out_path, new_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync project notes into RAG synthesis")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--notes-dir", required=True, help="Directory containing notes")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    notes_dir = Path(args.notes_dir).resolve()
    if not notes_dir.exists():
        print(f"notes-dir not found: {notes_dir}")
        return 1

    out_path, new_count = sync_notes(rag_dir, notes_dir)
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    item_count = text.count("<!-- note:")
    if item_count == 0:
        print("no items extracted")
        return 0

    append_log(rag_dir, "sync-from-notes", f"notes_dir={notes_dir}", f"items={item_count} new={new_count}")
    print(f"sync-from-notes: {item_count} items new={new_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
