"""Lint the DARW RAG knowledge base for consistency issues."""

from __future__ import annotations

import argparse
import re
import yaml
from pathlib import Path

from bib_parser import parse_bibtex_file
from common import read_frontmatter

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def load_vocabulary_canonical_ids(rag_dir: Path) -> dict[str, set[str]]:
    """Return {{category: {canonical_id, ...}}} from vocabulary.md terms."""
    vocab_file = rag_dir / "vocabulary.md"
    if not vocab_file.exists():
        return {}
    text = vocab_file.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n")
    match = re.search(r"```ya?ml\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except Exception:
        return {}
    terms = data.get("terms", []) if isinstance(data, dict) else []
    if not isinstance(terms, list):
        return {}
    cats: dict[str, set[str]] = {}
    for term in terms:
        if not isinstance(term, dict):
            continue
        cat = term.get("category", "")
        cid = term.get("canonical_id", "")
        if cat and cid:
            cats.setdefault(cat, set()).add(cid)
    return cats


def check_dead_links(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    for md in rag_dir.rglob("*.md"):
        for match in LINK_RE.finditer(md.read_text(encoding="utf-8")):
            target_raw = match.group(1)
            if target_raw.startswith("http"):
                continue
            target = (md.parent / target_raw.split("#")[0]).resolve()
            if not target.exists():
                issues.append(f"dead link in {md.relative_to(rag_dir)}: {target_raw}")
    return issues


def check_bibtex_manifest(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    manifest_path = rag_dir / "references.bib"
    if not manifest_path.exists():
        return ["references.bib missing"]
    entries = parse_bibtex_file(manifest_path)
    keys: set[str] = set()
    for entry in entries:
        key = entry.get("ID", "")
        if key in keys:
            issues.append(f"duplicate BibTeX key: {key}")
        keys.add(key)
    return issues


def check_source_fm(rag_dir: Path, vocab_ids: dict[str, set[str]], *, strict: bool = False) -> list[str]:
    issues: list[str] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return issues
    for page in sources_dir.glob("*.md"):
        fm, body = read_frontmatter(page)
        rel = str(page.relative_to(rag_dir))

        if fm.get("schema_version") != "darw-source-v1":
            issues.append(f"missing or wrong schema_version in {rel}")

        for field in ("doc_id", "citation_key"):
            if not fm.get(field):
                issues.append(f"missing frontmatter field '{field}' in {rel}")

        edges = fm.get("edges")
        if not isinstance(edges, dict):
            issues.append(f"missing edges block in {rel}")
            continue

        valid_categories = set(vocab_ids.keys())
        for category, entries in edges.items():
            if valid_categories and category not in valid_categories:
                issues.append(f"unknown edge category '{category}' in {rel}")
                continue
            if not isinstance(entries, list):
                continue
            valid_ids = vocab_ids.get(category, set())
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
                if valid_ids and cid not in valid_ids:
                    issues.append(f"off-vocab canonical_id '{cid}' in {rel} (category={category})")

        tag_count = sum(
            len(v) for v in edges.values() if isinstance(v, list)
        )
        if tag_count == 0 and strict:
            issues.append(f"source page has no edges: {rel}")

    return issues


def _resolve_rag_path(rag_dir: Path, page: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    rag_root_path = (rag_dir / candidate).resolve()
    if rag_root_path.exists() or value.startswith(("reference/", "summary/", "indexes/")):
        return rag_root_path
    return (page.parent / candidate).resolve()


def check_pdf_refs(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return issues
    for page in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page)
        pdf_ref = fm.get("pdf", "")
        if not pdf_ref:
            source = fm.get("source")
            if isinstance(source, dict):
                pdf_ref = source.get("original_pdf", "")
        if pdf_ref:
            pdf_path = _resolve_rag_path(rag_dir, page, str(pdf_ref))
            if not pdf_path.exists():
                issues.append(f"missing PDF for {page.relative_to(rag_dir)}: {pdf_ref}")
    return issues


def check_auto_blocks(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    for md in rag_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        begin_count = text.count("<!-- AUTO:BEGIN -->")
        end_count = text.count("<!-- AUTO:END -->")
        if begin_count != end_count:
            issues.append(f"AUTO block mismatch in {md.relative_to(rag_dir)} (BEGIN={begin_count}, END={end_count})")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint DARW RAG knowledge base")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as errors (empty edges, metadata-only pages)")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    issues: list[str] = []
    vocab_ids = load_vocabulary_canonical_ids(rag_dir)

    # Core lint checks
    issues.extend(check_bibtex_manifest(rag_dir))
    issues.extend(check_source_fm(rag_dir, vocab_ids, strict=args.strict))
    issues.extend(check_pdf_refs(rag_dir))
    issues.extend(check_dead_links(rag_dir))
    issues.extend(check_auto_blocks(rag_dir))

    # Phase 5 validators
    from validate_evidence import validate_evidence
    from validate_source_pages import validate_source_pages
    from validate_vocabulary import validate_vocabulary

    vocab_issues = validate_vocabulary(rag_dir)
    source_issues = [issue for issue in validate_source_pages(rag_dir, strict=args.strict) if args.strict or not issue.startswith("[warning]")]
    evidence_issues = validate_evidence(rag_dir)

    issues.extend(vocab_issues)
    issues.extend(source_issues)
    issues.extend(evidence_issues)

    print(f"# RAG Lint Report\n")
    print(f"Linted: {rag_dir}\n")
    if issues:
        print(f"Issues found: {len(issues)}\n")
        for issue in issues:
            print(f"- [ ] {issue}")
    else:
        print("No issues found.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
