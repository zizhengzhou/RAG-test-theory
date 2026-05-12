"""Build DARW source-page frontmatter and body skeletons."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml


def _template_body_sections(rag_dir: Path) -> list[str]:
    """Extract body section headings from template.md."""
    template_path = rag_dir / "template.md"
    if not template_path.exists():
        return []
    text = template_path.read_text(encoding="utf-8")
    sections: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### ") and not stripped.startswith("#### "):
            heading = stripped[4:].strip()
            if heading and "frontmatter" not in heading.lower() and heading[0].isdigit():
                parts = heading.split(". ", 1)
                sections.append(parts[1] if len(parts) > 1 else heading)
    return sections


def default_frontmatter(entry: dict[str, str], rag_dir: Path | None = None) -> dict[str, object]:
    today = date.today().isoformat()
    year = entry.get("year", "").strip()
    if not year:
        date_val = entry.get("date", "").strip()
        if date_val:
            year = date_val[:4] if len(date_val) >= 4 else date_val
    title = entry.get("title", "").strip().replace("{", "").replace("}", "")
    arxiv_id = (entry.get("eprint") or "").strip()
    doc_id = f"arxiv:{arxiv_id}" if arxiv_id else entry.get("doi", "").strip()

    return {
        "schema_version": "darw-source-v1",
        "doc_id": doc_id,
        "citation_key": entry.get("ID", "unknown"),
        "identifiers": {
            "arxiv": arxiv_id or None,
            "doi": entry.get("doi", "").strip() or None,
            "inspire": None,
            "zotero_key": entry.get("zotero_key", "").strip() or None,
            "url": None,
        },
        "source": {
            "title": title,
            "authors": [a.strip() for a in entry.get("author", "").replace("{", "").replace("}", "").split(" and ") if a.strip()],
            "year": year,
            "venue": entry.get("journal", "").strip() or None,
            "abstract": "",
            "source_type": "arxiv_source" if arxiv_id else "pdf_pymupdf",
            "primary_evidence": "",
            "original_pdf": f"../../reference/pdfs/{entry.get('ID', 'unknown')}.pdf",
            "original_tex": None,
            "source_sha256": "",
            "parser": "",
            "parser_version": "",
            "parsed_at": "",
        },
        "edges": {
            "research_areas": [],
            "physical_systems": [],
            "techniques": [],
            "properties": [],
            "models": [],
            "observables": [],
            "datasets": [],
            "experiments": [],
        },
        "chunk_manifest": "",
        "quality": {
            "extraction_confidence": "low",
            "needs_human_review": True,
            "math_extraction_quality": "unknown",
            "metadata_conflicts": [],
        },
        "status": {
            "reading_status": "unread",
            "relevance": "unknown",
            "last_checked": today,
        },
    }


def body_skeleton(entry: dict[str, str], rag_dir: Path | None = None) -> str:
    if rag_dir is None:
        rag_dir = Path("RAG")
    sections = _template_body_sections(rag_dir)
    title = entry.get("title", "").strip().replace("{", "").replace("}", "")
    lines = [f"\n# {title}\n"]
    for section in sections:
        slug = section.lower().replace(" ", "-").replace("/", "-")
        lines.append(f"\n## {section}\n")
        lines.append(f"{{#{slug}}}\n")
        lines.append("\n_To be filled._\n")
    return "".join(lines)


def format_frontmatter(fm: dict[str, object]) -> str:
    def _represent_none(self, data):
        return self.represent_scalar("tag:yaml.org,2002:null", "null")

    yaml.add_representer(type(None), _represent_none)
    inner = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{inner}\n---\n"
