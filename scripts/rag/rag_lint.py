"""Lint the RAG knowledge base for consistency issues."""

from __future__ import annotations

import argparse
import re
import yaml
from pathlib import Path

from bib_parser import parse_bibtex_file
from common import read_frontmatter

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def load_vocabulary(rag_dir: Path) -> dict[str, set[str]]:
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
    axes: dict[str, set[str]] = {}
    vocab = data.get("vocabulary", data) if isinstance(data, dict) else {}
    for axis, entries in vocab.items():
        if isinstance(entries, dict):
            axes[axis] = set(entries)
    return axes


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


def check_source_fm(rag_dir: Path, vocabulary: dict[str, set[str]]) -> list[str]:
    issues: list[str] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return issues
    for page in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page)
        if fm.get("type") != "source":
            issues.append(f"source page missing type=source: {page.relative_to(rag_dir)}")
        required = ["created", "title"]
        for field in required:
            if field not in fm:
                issues.append(f"missing frontmatter field '{field}' in {page.relative_to(rag_dir)}")
        for key, value in fm.items():
            if isinstance(value, list):
                axis = key if key.endswith("s") else key + "s"
                if axis in vocabulary:
                    valid_tags = vocabulary[axis]
                    for tag in value:
                        tag_clean = tag.strip().strip('"')
                        if tag_clean and tag_clean not in valid_tags:
                            issues.append(f"off-vocab tag '{tag_clean}' in {page.relative_to(rag_dir)} (axis={axis})")
        tag_count = sum(1 for v in fm.values() if isinstance(v, list) and v)
        if tag_count == 0:
            issues.append(f"orphan source (no dimension tags): {page.relative_to(rag_dir)}")
    return issues


def check_pdf_refs(rag_dir: Path) -> list[str]:
    issues: list[str] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return issues
    for page in sources_dir.glob("*.md"):
        fm, _ = read_frontmatter(page)
        pdf_ref = fm.get("pdf", "")
        if pdf_ref:
            pdf_path = (page.parent / pdf_ref).resolve()
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
    parser = argparse.ArgumentParser(description="Lint RAG knowledge base")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    issues: list[str] = []
    vocabulary = load_vocabulary(rag_dir)

    issues.extend(check_bibtex_manifest(rag_dir))
    issues.extend(check_source_fm(rag_dir, vocabulary))
    issues.extend(check_pdf_refs(rag_dir))
    issues.extend(check_dead_links(rag_dir))
    issues.extend(check_auto_blocks(rag_dir))

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
