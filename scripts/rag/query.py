"""Query the RAG knowledge base with Markdown-first search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bib_parser import parse_bibtex_file
from common import read_frontmatter
from metadata_normalizer import normalize_arxiv, normalize_doi, normalize_entry, normalize_title


def search_in_dir(directory: Path, query: str) -> list[tuple[Path, list[str]]]:
    results: list[tuple[Path, list[str]]] = []
    for md in directory.rglob("*.md"):
        lines = md.read_text(encoding="utf-8").splitlines()
        matches = [line for line in lines if query.lower() in line.lower()]
        if matches:
            results.append((md, matches[:5]))
    return results


def structured_search(rag_dir: Path, query: str, *, limit: int = 10) -> list[dict[str, object]]:
    manifest = rag_dir / "references.bib"
    entries = parse_bibtex_file(manifest) if manifest.exists() else []
    q_norm = normalize_title(query)
    q_doi = normalize_doi(query)
    q_arxiv = normalize_arxiv(query)
    results: list[dict[str, object]] = []
    for entry in entries:
        normalized = normalize_entry(entry)
        key = str(normalized["key"])
        title = str(normalized["title"])
        title_norm = str(normalized["title_norm"])
        doi = str(normalized["doi"])
        arxiv = str(normalized["arxiv"])
        source_path = rag_dir / "summary" / "sources" / f"{key}.md"
        source_text = ""
        fm: dict[str, object] = {}
        if source_path.exists():
            fm, body = read_frontmatter(source_path)
            source_text = normalize_title(body)
        score = 0
        matched: list[str] = []
        if query.lower() == key.lower():
            score += 100
            matched.append("citation_key")
        if q_doi and doi and q_doi == doi:
            score += 95
            matched.append("doi")
        if q_arxiv and arxiv and q_arxiv == arxiv:
            score += 95
            matched.append("arxiv")
        if q_norm and title_norm and q_norm == title_norm:
            score += 90
            matched.append("title")
        elif q_norm and title_norm and q_norm in title_norm:
            score += 50
            matched.append("title-substring")
        if q_norm and source_text and q_norm in source_text:
            score += 25
            matched.append("source_body")
        if score <= 0:
            continue
        results.append(
            {
                "citation_key": key,
                "title": title,
                "doi": doi,
                "arxiv": arxiv,
                "score": score,
                "matched_fields": sorted(set(matched)),
                "source_page": f"summary/sources/{key}.md" if source_path.exists() else "",
                "frontmatter": fm,
            }
        )
    results.sort(key=lambda item: (-int(item["score"]), str(item["citation_key"]).lower()))
    return results[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the RAG knowledge base")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", required=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    query = args.query.strip()
    if not query:
        print("empty query")
        return 1

    if args.json:
        print(json.dumps({"query": query, "results": structured_search(rag_dir, query, limit=args.limit)}, indent=2, ensure_ascii=False))
        return 0

    print(f"# query: {query}\n")
    areas = [
        ("summary/sources", "Source pages"),
        ("summary/synthesis", "Synthesis"),
    ]
    for rel, label in areas:
        path = rag_dir / rel
        if path.exists():
            results = search_in_dir(path, query)
            if results:
                print(f"## {label}")
                for filepath, matches in results:
                    print(f"  - [{filepath.stem}]({rel}/{filepath.name})")
                    for line in matches:
                        print(f"    > {line.strip()}")
                print()

    # Also search dimension directories
    summary_dir = rag_dir / "summary"
    if summary_dir.exists():
        for child in summary_dir.iterdir():
            if child.is_dir() and child.name not in {"sources", "synthesis"}:
                results = search_in_dir(child, query)
                if results:
                    print(f"## {child.name}")
                    for filepath, matches in results:
                        print(f"  - [{filepath.stem}](summary/{child.name}/{filepath.name})")
                        for line in matches:
                            print(f"    > {line.strip()}")
                    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
