"""Validate DARW source pages — schema, edges, claims, and evidence linkage."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

from common import read_frontmatter
from darw_schema import (
    ARXIV_SOURCE,
    EDGE_CATEGORIES,
    PDF_MINERU,
    PDF_PYMUPDF,
    SOURCE_SCHEMA_VERSION,
)
from validate_vocabulary import _extract_vocab_terms


REQUIRED_BLOCKS = ("identifiers", "source", "edges", "quality", "status")

CLAIM_RE = re.compile(r"```claim\n(.*?)\n```", re.DOTALL)


def _load_chunk_id_set(rag_dir: Path) -> set[str]:
    """Collect all chunk_ids from all chunk manifests."""
    chunks_dir = rag_dir / "reference" / "chunks"
    if not chunks_dir.is_dir():
        return set()
    ids: set[str] = set()
    for chunk_path in chunks_dir.glob("*.jsonl"):
        for line in chunk_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                cid = record.get("chunk_id", "")
                if cid:
                    ids.add(str(cid))
            except Exception:
                continue
    return ids


def _parse_claim_blocks(body: str) -> list[dict]:
    """Parse ```claim YAML blocks from the Markdown body."""
    claims: list[dict] = []
    for match in CLAIM_RE.finditer(body):
        try:
            data = yaml.safe_load(match.group(1))
            if isinstance(data, dict):
                claims.append(data)
        except Exception:
            continue
    return claims


def _resolve_rag_path(rag_dir: Path, page: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    rag_root_path = (rag_dir / candidate).resolve()
    if rag_root_path.exists() or value.startswith(("reference/", "summary/", "indexes/")):
        return rag_root_path
    return (page.parent / candidate).resolve()


def validate_source_pages(rag_dir: Path, strict: bool = False) -> list[str]:
    issues: list[str] = []
    sources_dir = rag_dir / "summary" / "sources"
    if not sources_dir.is_dir():
        return issues

    vocab_data, _ = _extract_vocab_terms(rag_dir)
    vocab_terms = vocab_data.get("terms", []) if isinstance(vocab_data, dict) else []
    valid_cids: set[str] = set()
    for term in vocab_terms:
        if isinstance(term, dict):
            cid = str(term.get("canonical_id", ""))
            if cid:
                valid_cids.add(cid)

    all_chunk_ids = _load_chunk_id_set(rag_dir)

    for page in sorted(sources_dir.glob("*.md")):
        fm, body = read_frontmatter(page)
        rel = str(page.relative_to(rag_dir))

        # schema version
        if fm.get("schema_version") != SOURCE_SCHEMA_VERSION:
            issues.append(f"missing/wrong schema_version in {rel}")

        # required blocks
        for block in REQUIRED_BLOCKS:
            if not isinstance(fm.get(block), dict):
                issues.append(f"missing required block '{block}' in {rel}")

        # source_type validity
        source = fm.get("source")
        st = ""
        if isinstance(source, dict):
            st = str(source.get("source_type", ""))
        if st and st not in (ARXIV_SOURCE, PDF_PYMUPDF, PDF_MINERU):
            issues.append(f"invalid source_type '{st}' in {rel}")

        # doc_id / arxiv consistency
        doc_id = str(fm.get("doc_id", ""))
        identifiers = fm.get("identifiers")
        if isinstance(identifiers, dict):
            arxiv_id = str(identifiers.get("arxiv", "") or "")
            if arxiv_id and doc_id and f"arxiv:{arxiv_id}" != doc_id:
                issues.append(f"doc_id '{doc_id}' inconsistent with identifiers.arxiv '{arxiv_id}' in {rel}")

        # edges validation
        edges = fm.get("edges")
        if isinstance(edges, dict):
            if not edges or all(not v for v in edges.values()):
                severity = "warning" if not strict else "error"
                issues.append(f"[{severity}] source page has no edges: {rel}")
            for category, entries in edges.items():
                if category not in EDGE_CATEGORIES:
                    issues.append(f"unknown edge category '{category}' in {rel}")
                    continue
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    cid = entry.get("canonical_id", "") if isinstance(entry, dict) else str(entry)
                    cid = str(cid).strip()
                    if not cid:
                        continue
                    if valid_cids and cid not in valid_cids:
                        issues.append(f"off-vocab canonical_id '{cid}' in {rel} edges.{category}")

        # primary evidence link consistency
        if isinstance(source, dict):
            primary_ev = str(source.get("primary_evidence", ""))
            if primary_ev:
                ev_path = _resolve_rag_path(rag_dir, page, primary_ev)
                if not ev_path.exists():
                    issues.append(f"primary_evidence target missing in {rel}: {primary_ev}")
            chunk_manifest = str(fm.get("chunk_manifest", ""))
            if chunk_manifest:
                cm_path = _resolve_rag_path(rag_dir, page, chunk_manifest)
                if not cm_path.exists():
                    issues.append(f"chunk_manifest target missing in {rel}: {chunk_manifest}")

        # claim blocks
        claims = _parse_claim_blocks(body)
        for claim in claims:
            claim_id = str(claim.get("claim_id", "<missing>"))
            evidence_list = claim.get("evidence")
            if not isinstance(evidence_list, list) or len(evidence_list) == 0:
                issues.append(f"claim {claim_id} has no evidence entries in {rel}")
                continue
            for ev in evidence_list:
                if not isinstance(ev, dict):
                    continue
                chunk_id = str(ev.get("chunk_id", ""))
                if not chunk_id:
                    issues.append(f"claim {claim_id} has evidence entry without chunk_id in {rel}")
                    continue
                if all_chunk_ids and chunk_id not in all_chunk_ids:
                    issues.append(f"claim {claim_id} references missing chunk_id '{chunk_id}' in {rel}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DARW source pages")
    parser.add_argument("--rag-dir", default="RAG")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()
    rag_dir = Path(args.rag_dir).resolve()
    issues = validate_source_pages(rag_dir, strict=args.strict)
    if issues:
        print(f"Source page issues found: {len(issues)}")
        for issue in issues:
            print(f"- [ ] {issue}")
        return 1
    print("No source page issues found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
