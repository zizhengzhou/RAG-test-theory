"""Build and query a DARW graph index from source page edges.

The graph maps canonical edge IDs to the source pages that cite them,
enabling candidate filtering and cross-source navigation.

Rules:
- Graph is for candidate filtering and navigation only.
- Graph does not answer physics questions.
- Graph never replaces chunk evidence.
- Empty-edge source pages produce no graph entries.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from common import read_frontmatter
from darw_schema import EDGE_CATEGORIES


def build_graph(rag_dir: Path) -> dict:
    """Build a graph index from all source page edges.

    Returns a dict with:
      - 'nodes': {source_page_path: {title, citation_key, doc_id}}
      - 'edges': {category: {canonical_id: [source_page_path, ...]}}
    """
    sources_dir = rag_dir / "summary" / "sources"
    nodes: dict[str, dict] = {}
    edges: dict[str, dict[str, list[str]]] = {cat: {} for cat in EDGE_CATEGORIES}

    if not sources_dir.is_dir():
        return {"nodes": nodes, "edges": edges}

    for page in sorted(sources_dir.glob("*.md")):
        fm, _ = read_frontmatter(page)
        rel = page.relative_to(rag_dir).as_posix()
        title = ""
        source = fm.get("source")
        if isinstance(source, dict):
            title = str(source.get("title", ""))
        nodes[rel] = {
            "title": title,
            "citation_key": str(fm.get("citation_key", "")),
            "doc_id": str(fm.get("doc_id", "")),
        }

        edge_map = fm.get("edges")
        if not isinstance(edge_map, dict):
            continue
        for category, entries in edge_map.items():
            if category not in edges:
                continue
            if not isinstance(entries, list):
                continue
            for entry in entries:
                cid = entry.get("canonical_id", "") if isinstance(entry, dict) else str(entry)
                cid = str(cid).strip()
                if not cid:
                    continue
                edges[category].setdefault(cid, []).append(rel)

    return {"nodes": nodes, "edges": {k: v for k, v in edges.items() if v}}


def query_graph(graph: dict, canonical_id: str, top_k: int = 10) -> list[str]:
    """Return source page paths that reference a given canonical_id across all categories."""
    pages: set[str] = set()
    for cat_edges in graph.get("edges", {}).values():
        if canonical_id in cat_edges:
            for p in cat_edges[canonical_id]:
                pages.add(p)
    return sorted(pages)[:top_k]


def write_graph(rag_dir: Path, graph: dict) -> Path:
    """Persist the graph to RAG/indexes/graph_edges.yaml."""
    indexes_dir = rag_dir / "indexes"
    indexes_dir.mkdir(parents=True, exist_ok=True)
    output = indexes_dir / "graph_edges.yaml"
    output.write_text(yaml.dump(graph, allow_unicode=True, default_flow_style=False, sort_keys=True),
                      encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and query DARW graph index")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--query", default="", help="Query by canonical_id")
    parser.add_argument("--write", action="store_true", help="Write graph to RAG/indexes/graph_edges.yaml")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    graph = build_graph(rag_dir)

    node_count = len(graph["nodes"])
    edge_count = sum(len(cat) for cat in graph["edges"].values())

    print(f"# DARW Graph Index\n")
    print(f"Nodes (source pages): {node_count}")
    print(f"Edge categories with entries: {len(graph['edges'])}")
    print(f"Canonical term nodes: {edge_count}")
    print()

    if node_count == 0 and edge_count == 0:
        print("Graph is empty — no source pages with edges found.")
        return 0

    if args.query:
        pages = query_graph(graph, args.query)
        if pages:
            print(f"Pages referencing '{args.query}':")
            for p in pages:
                node = graph["nodes"].get(p, {})
                title = node.get("title", "")
                print(f"  {p}  ({title})")
        else:
            print(f"No pages reference '{args.query}'")
        return 0

    if args.write:
        output = write_graph(rag_dir, graph)
        print(f"Graph written to {output.relative_to(rag_dir).as_posix()}")
    else:
        for category, terms in sorted(graph["edges"].items()):
            if not terms:
                continue
            print(f"## {category} ({len(terms)} terms)")
            for cid, pages in sorted(terms.items()):
                print(f"  {cid}: {len(pages)} page(s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
