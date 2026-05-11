"""Fill RAG source pages with local, metadata/PDF-backed summaries.

This script does not call external APIs. It extracts text from PDFs with
``pdftotext`` when available and uses title/abstract/first-page snippets to
replace placeholder sections in existing source pages.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

from common import append_log, read_frontmatter, write_frontmatter

PLACEHOLDER_RE = re.compile(r"_(?:No summary yet\.|To be filled\.)_|PDF text was not available|No clear abstract heading was extracted|Needs manual/AI review", re.IGNORECASE)
SECTION_RE = re.compile(r"(?ms)^## (?P<name>.+?)\n\n(?P<body>.*?)(?=\n## |\Z)")
SPACE_RE = re.compile(r"\s+")
ABSTRACT_RE = re.compile(r"(?is)\babstract\b\s*(?P<abstract>.*?)(?:\n\s*(?:1\.?\s+)?(?:introduction|keywords|index terms)\b|\n\s*I\.\s+INTRODUCTION\b)")


def _normalize_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def _pdf_to_text(pdf_path: Path, max_pages: int = 3) -> str:
    if not pdf_path.exists():
        return ""
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", str(max_pages), "-layout", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _extract_abstract(text: str) -> str:
    cleaned = re.sub(r"(?m)^\s*\d+\s*$", "", text)
    match = ABSTRACT_RE.search(cleaned)
    if match:
        abstract = _normalize_text(match.group("abstract"))
        abstract = abstract.replace("Abstract—", "").replace("Abstract-", "").strip(" :-")
        return abstract[:1200]
    # Some journal PDFs do not expose an Abstract heading in extracted text; use
    # the first prose paragraph after title/author metadata instead of raw page text.
    for paragraph in re.split(r"\n\s*\n", cleaned):
        para = _normalize_text(paragraph)
        if len(para) < 180:
            continue
        lower = para.lower()
        if any(skip in lower for skip in ("article", "https://doi.org", "received:", "accepted:", "published online", "check for updates")):
            continue
        return para[:1200]
    return ""


def _metadata_summary(fm: dict[str, object], pdf_text: str) -> str:
    title = str(fm.get("title", "")).strip()
    year = str(fm.get("year", "")).strip()
    authors = fm.get("authors", [])
    author_text = ""
    if isinstance(authors, list) and authors:
        shown = ", ".join(str(a) for a in authors[:3])
        suffix = " et al." if len(authors) > 3 else ""
        author_text = f" by {shown}{suffix}"
    abstract = _extract_abstract(pdf_text)
    if abstract:
        return f"{title} ({year}){author_text}. Extracted abstract: {abstract}"
    if pdf_text:
        snippet = _normalize_text(pdf_text)[:900]
        return f"{title} ({year}){author_text}. No clear abstract heading was extracted; first-page text begins: {snippet}"
    return f"{title} ({year}){author_text}. PDF text was not available; this source page currently contains bibliographic metadata only."


def _key_findings(fm: dict[str, object], pdf_text: str) -> str:
    abstract = _extract_abstract(pdf_text)
    if abstract:
        sentences = re.split(r"(?<=[.!?])\s+", abstract)
        bullets = [s.strip() for s in sentences if len(s.strip()) > 40][:3]
        if bullets:
            return "\n".join(f"- {b}" for b in bullets)
    title = str(fm.get("title", "")).strip()
    return f"- Needs manual/AI review of the PDF for detailed findings. Current indexed topic: {title}."


def _links(fm: dict[str, object]) -> str:
    lines: list[str] = []
    doi = str(fm.get("doi", "")).strip()
    arxiv = str(fm.get("arxiv", "")).strip()
    pdf = str(fm.get("pdf", "")).strip()
    if doi:
        lines.append(f"- DOI: {doi}")
    if arxiv:
        lines.append(f"- arXiv: {arxiv}")
    if pdf:
        lines.append(f"- PDF: {pdf}")
    return "\n".join(lines) if lines else "- No external identifiers recorded."



def _replace_sections(body: str, replacements: dict[str, str]) -> str:
    cleaned = body
    while cleaned.startswith("\n"):
        cleaned = cleaned[1:]
    lines = cleaned.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    section_body = "\n".join(lines)

    def repl(match: re.Match[str]) -> str:
        name = match.group("name").strip()
        key = name.lower()
        current = match.group("body").strip()
        if key in replacements and (not current or PLACEHOLDER_RE.search(current) or (key == "limitations" and "Not yet assessed" in current)):
            return f"## {name}\n\n{replacements[key].strip()}"
        return match.group(0).rstrip()

    return SECTION_RE.sub(repl, section_body).rstrip() + "\n"


def summarize_page(page_path: Path) -> bool:
    fm, body = read_frontmatter(page_path)
    if not fm:
        return False
    pdf_ref = str(fm.get("pdf", "")).strip()
    pdf_path = (page_path.parent / pdf_ref).resolve() if pdf_ref else Path()
    pdf_text = _pdf_to_text(pdf_path) if pdf_ref else ""
    replacements = {
        "summary": _metadata_summary(fm, pdf_text),
        "key findings": _key_findings(fm, pdf_text),
        "limitations": "- Not yet assessed. This section should be refined after a focused reading of the full paper.",
        "links": _links(fm),
    }
    new_body = _replace_sections(body, replacements)
    if new_body == body:
        return False
    fm["last_updated"] = date.today().isoformat()
    page_path.write_text(write_frontmatter(fm) + f"\n# {fm.get('title', page_path.stem)}\n" + new_body, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize RAG source pages from local PDFs")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--force", action="store_true", help="Reserved for future use; current mode only replaces placeholders")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        print(f"No sources directory: {sources_dir}")
        return 1

    updated = 0
    skipped = 0
    for page_path in sorted(sources_dir.glob("*.md")):
        if summarize_page(page_path):
            updated += 1
            print(f"updated: {page_path.relative_to(rag_dir).as_posix()}")
        else:
            skipped += 1
    append_log(rag_dir, "summarize-sources", f"sources_dir={sources_dir}", f"updated={updated} skipped={skipped}")
    print(f"updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
