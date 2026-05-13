"""Create evidence-grounded topic summary drafts from context packs."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from common import append_log
from context_pack import build_context_pack


def build_topic_summary(rag_dir: Path, query: str, *, top_k: int = 8) -> dict[str, Any]:
    pack = build_context_pack(rag_dir, query=query, top_k=top_k)
    chunks = pack.get("evidence_chunks", [])
    references = pack.get("bib_entries", [])
    consensus = [
        {
            "statement": str(chunk.get("snippet", "")).strip(),
            "chunk_id": chunk.get("chunk_id", ""),
            "source_page": chunk.get("source_page", ""),
        }
        for chunk in chunks[:5]
        if str(chunk.get("snippet", "")).strip()
    ]
    return {
        "query": query,
        "generated_at": date.today().isoformat(),
        "consensus": consensus,
        "disagreement": [],
        "open_problems": pack.get("gaps", []),
        "key_references": [
            {
                "citation_key": item.get("citation_key", ""),
                "title": item.get("entry", {}).get("title", ""),
            }
            for item in references
        ],
        "provenance": pack.get("provenance", {}),
    }


def render_summary(summary: dict[str, Any]) -> str:
    lines = [f"# Topic Summary: {summary['query']}", ""]
    lines.append("## Consensus")
    for item in summary["consensus"]:
        lines.append(f"- {item['statement']} [{item['chunk_id']}]({item['source_page']})")
    if not summary["consensus"]:
        lines.append("- No chunk-backed consensus found.")
    lines.append("")
    lines.append("## Disagreement")
    lines.append("- None identified by the deterministic summarizer.")
    lines.append("")
    lines.append("## Open Problems")
    for gap in summary["open_problems"] or ["No gaps recorded."]:
        lines.append(f"- {gap}")
    lines.append("")
    lines.append("## Key References")
    for ref in summary["key_references"]:
        lines.append(f"- {ref['citation_key']}: {ref['title']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a topic from source pages and evidence chunks")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--out", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    summary = build_topic_summary(rag_dir, args.query, top_k=args.top_k)
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(render_summary(summary))
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    out = Path(args.out).resolve() if args.out else rag_dir / "summary" / "synthesis" / f"{args.query.lower().replace(' ', '-')[:60]}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_summary(summary), encoding="utf-8")
    append_log(rag_dir, "summarize-topic", f"query={args.query}", f"out={out}")
    print(f"wrote: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
