"""Build vocabulary-backed wiki pages from source-page edges."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from common import append_log, read_frontmatter, write_frontmatter
from darw_schema import EDGE_CATEGORIES
from physh_mapper import load_vocabulary_terms
from update_index import AUTO_BEGIN, AUTO_END


@dataclass
class VocabularyNode:
    canonical_id: str
    label: str
    namespace: str
    category: str
    aliases: list[str] = field(default_factory=list)
    source_pages: list[str] = field(default_factory=list)


@dataclass
class VocabularyWikiPlan:
    rag_dir: Path
    nodes: list[VocabularyNode] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.nodes)


def _safe_page_name(canonical_id: str) -> str:
    return canonical_id.replace(":", "_").replace("/", "_")


def _vocabulary_terms(rag_dir: Path) -> dict[str, dict]:
    terms = load_vocabulary_terms(rag_dir / "vocabulary.md")
    return {
        str(term.get("canonical_id", "")): term
        for term in terms
        if str(term.get("canonical_id", "")).strip()
    }


def _namespace(canonical_id: str) -> str:
    return canonical_id.split(":", 1)[0] if ":" in canonical_id else "local"


def build_vocabulary_wiki_plan(rag_dir: Path, *, strict_physh: bool = False) -> VocabularyWikiPlan:
    vocabulary_terms = _vocabulary_terms(rag_dir)
    if not vocabulary_terms:
        return VocabularyWikiPlan(rag_dir=rag_dir, errors=["no canonical terms in vocabulary.md"])
    nodes: dict[str, VocabularyNode] = {}
    skipped: list[dict[str, str]] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return VocabularyWikiPlan(rag_dir=rag_dir, errors=["summary/sources missing"])
    for source_page in sorted(sources_dir.glob("*.md")):
        fm, _ = read_frontmatter(source_page)
        rel = source_page.relative_to(rag_dir).as_posix()
        edges = fm.get("edges", {})
        if not isinstance(edges, dict):
            continue
        for category, entries in edges.items():
            if category not in EDGE_CATEGORIES or not isinstance(entries, list):
                continue
            for entry in entries:
                cid = entry.get("canonical_id", "") if isinstance(entry, dict) else str(entry)
                cid = str(cid).strip()
                if not cid:
                    continue
                namespace = _namespace(cid)
                if strict_physh and namespace != "physh":
                    skipped.append({"canonical_id": cid, "source_page": rel, "reason": "strict-physh filter"})
                    continue
                term = vocabulary_terms.get(cid)
                if not term:
                    skipped.append({"canonical_id": cid, "source_page": rel, "reason": "missing from vocabulary"})
                    continue
                node = nodes.setdefault(
                    cid,
                    VocabularyNode(
                        canonical_id=cid,
                        label=str(term.get("label", cid)),
                        namespace=namespace,
                        category=str(term.get("category", category)),
                        aliases=[str(alias) for alias in term.get("aliases", []) or []],
                    ),
                )
                if rel not in node.source_pages:
                    node.source_pages.append(rel)
    return VocabularyWikiPlan(rag_dir=rag_dir, nodes=sorted(nodes.values(), key=lambda node: node.canonical_id), skipped=skipped)


def _render_node(node: VocabularyNode) -> str:
    fm = {
        "type": "vocabulary-node",
        "canonical_id": node.canonical_id,
        "label": node.label,
        "namespace": node.namespace,
        "category": node.category,
        "aliases": node.aliases,
    }
    lines = [
        write_frontmatter(fm).rstrip(),
        "",
        f"# {node.label}",
        "",
        f"`{node.canonical_id}`",
        "",
        AUTO_BEGIN,
        f"## Source pages ({len(node.source_pages)})",
    ]
    for page in sorted(node.source_pages):
        key = Path(page).stem
        lines.append(f"- [[../sources/{key}]]")
    lines.extend([AUTO_END, ""])
    return "\n".join(lines)


def apply_vocabulary_wiki_plan(plan: VocabularyWikiPlan) -> int:
    written = 0
    for node in plan.nodes:
        out_dir = plan.rag_dir / "summary" / node.category
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{_safe_page_name(node.canonical_id)}.md"
        path.write_text(_render_node(node), encoding="utf-8")
        written += 1
    append_log(plan.rag_dir, "build-vocabulary-wiki", "", f"written={written} skipped={len(plan.skipped)}")
    return written


def plan_as_dict(plan: VocabularyWikiPlan) -> dict[str, object]:
    return {
        "rag_dir": str(plan.rag_dir),
        "summary": {"nodes": len(plan.nodes), "skipped": len(plan.skipped), "errors": len(plan.errors)},
        "nodes": [node.__dict__ for node in plan.nodes],
        "skipped": plan.skipped,
        "errors": plan.errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build vocabulary-backed wiki pages from source edges")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--strict-physh", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.yes:
        print("choose only one of --dry-run or --yes")
        return 1
    plan = build_vocabulary_wiki_plan(Path(args.rag_dir).resolve(), strict_physh=args.strict_physh)
    data = plan_as_dict(plan)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"vocabulary wiki plan: nodes={len(plan.nodes)} skipped={len(plan.skipped)} errors={len(plan.errors)}")
        for node in plan.nodes:
            print(f"- {node.canonical_id}: {node.label} [{node.namespace}] ({len(node.source_pages)} source pages)")
        for skipped in plan.skipped:
            print(f"skipped: {skipped['canonical_id']} {skipped['reason']} in {skipped['source_page']}")
    if plan.errors:
        return 1
    if args.dry_run or not args.yes:
        print("[dry-run] no files written")
        return 0
    written = apply_vocabulary_wiki_plan(plan)
    print(f"written={written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
