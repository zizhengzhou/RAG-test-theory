"""Query the RAG knowledge base with Markdown-first search."""

from __future__ import annotations

import argparse
from pathlib import Path


def search_in_dir(directory: Path, query: str) -> list[tuple[Path, list[str]]]:
    results: list[tuple[Path, list[str]]] = []
    for md in directory.rglob("*.md"):
        lines = md.read_text(encoding="utf-8").splitlines()
        matches = [line for line in lines if query.lower() in line.lower()]
        if matches:
            results.append((md, matches[:5]))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the RAG knowledge base")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", required=True)
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    query = args.query.strip()
    if not query:
        print("empty query")
        return 1

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
