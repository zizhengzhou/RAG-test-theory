"""Generate evidence-grounded draft summaries for DARW source pages."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from common import append_log, read_frontmatter, write_frontmatter

PLACEHOLDER_MARKERS = ("_To be filled._", "_No summary yet._", "Needs manual/AI review")


def _load_chunks_for_key(rag_dir: Path, key: str, limit: int) -> list[dict]:
    chunks_dir = rag_dir / "reference" / "chunks"
    if not chunks_dir.is_dir():
        return []
    chunks: list[dict] = []
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("citation_key") == key:
                chunks.append(record)
    return chunks[:limit]


def _sentence(text: str, max_len: int = 260) -> str:
    text = " ".join(text.split())
    for sep in (". ", "; ", "。"):
        if sep in text:
            candidate = text.split(sep, 1)[0].strip() + sep.strip()
            if 30 <= len(candidate) <= max_len:
                return candidate
    return text[:max_len].rstrip()


def draft_summary_from_chunks(chunks: list[dict]) -> dict[str, str]:
    if not chunks:
        return {}
    by_section: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        by_section[str(chunk.get("section_title") or "Document")].append(chunk)

    first = chunks[0]
    one_line = _sentence(str(first.get("text", "")))
    evidence_refs = ", ".join(str(c.get("chunk_id", "")) for c in chunks[:3] if c.get("chunk_id"))

    key_results: list[str] = []
    for chunk in chunks[:5]:
        text = _sentence(str(chunk.get("text", "")), 220)
        if text:
            key_results.append(f"- {text} [`{chunk.get('chunk_id', '')}`]")

    trace_rows = ["| claim_id | evidence chunk_id | section | equation_ids | notes |", "|---|---|---|---|---|"]
    for idx, chunk in enumerate(chunks[:8], start=1):
        eqs = ", ".join(chunk.get("equation_ids", []) or [])
        trace_rows.append(
            f"| draft-{idx:03d} | `{chunk.get('chunk_id', '')}` | {chunk.get('section_anchor', '')} | {eqs} | draft evidence candidate |"
        )

    return {
        "one-line contribution": f"Draft from evidence chunks: {one_line} Evidence: {evidence_refs}.",
        "key results": "\n".join(key_results) if key_results else "_To be filled._",
        "trace index": "\n".join(trace_rows),
    }


def _replace_or_append_sections(body: str, replacements: dict[str, str]) -> str:
    if not replacements:
        return body
    lines = body.splitlines()
    out: list[str] = []
    idx = 0
    replaced: set[str] = set()
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("## "):
            title = line[3:].strip()
            key = title.lower()
            out.append(line)
            idx += 1
            section_lines: list[str] = []
            while idx < len(lines) and not lines[idx].startswith("## "):
                section_lines.append(lines[idx])
                idx += 1
            current = "\n".join(section_lines).strip()
            if key in replacements and (not current or any(marker in current for marker in PLACEHOLDER_MARKERS)):
                out.append("")
                out.append(replacements[key])
                replaced.add(key)
            else:
                out.extend(section_lines)
            continue
        out.append(line)
        idx += 1
    for key, value in replacements.items():
        if key not in replaced:
            out.extend(["", f"## {key.title()}", "", value])
    return "\n".join(out).rstrip() + "\n"


def summarize_source_page(rag_dir: Path, key: str, *, limit: int = 8, dry_run: bool = True) -> bool:
    page = rag_dir / "summary" / "sources" / f"{key}.md"
    if not page.exists():
        print(f"source page missing: {page}")
        return False
    chunks = _load_chunks_for_key(rag_dir, key, limit)
    if not chunks:
        print(f"no chunks for {key}; run evidence_ingest first")
        return False
    fm, body = read_frontmatter(page)
    replacements = draft_summary_from_chunks(chunks)
    new_body = _replace_or_append_sections(body, replacements)
    if dry_run:
        print(f"# draft summary for {key}")
        for section, text in replacements.items():
            print(f"\n## {section}\n{text}")
        print("\n[dry-run] no files written")
        return True
    page.write_text(write_frontmatter(fm) + new_body, encoding="utf-8")
    append_log(rag_dir, "summarize-evidence", f"key={key}", f"chunks={len(chunks)}")
    print(f"updated: summary/sources/{key}.md")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft source-page summaries from evidence chunks")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--key", required=True)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--yes", action="store_true", help="Apply generated draft to source page")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    ok = summarize_source_page(rag_dir, args.key, limit=args.limit, dry_run=not args.yes)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
