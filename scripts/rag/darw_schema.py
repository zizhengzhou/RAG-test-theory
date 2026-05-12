"""Shared DARW schema constants and path helpers."""

from __future__ import annotations

import re
from pathlib import Path

SOURCE_SCHEMA_VERSION = "darw-source-v1"
VOCABULARY_SCHEMA_VERSION = "darw-vocabulary-v1"
PARSED_EVIDENCE_SCHEMA_VERSION = "darw-parsed-evidence-v1"
CHUNK_SCHEMA_VERSION = "darw-chunk-v1"

ARXIV_SOURCE = "arxiv_source"
PDF_PYMUPDF = "pdf_pymupdf"
PDF_MINERU = "pdf_mineru"
PDF_ROUTE_ALIASES = {PDF_MINERU: PDF_PYMUPDF}
ALLOWED_ROUTES = (ARXIV_SOURCE, PDF_PYMUPDF, PDF_MINERU)
CANONICAL_ROUTES = (ARXIV_SOURCE, PDF_PYMUPDF)


def canonical_route(route: str) -> str:
    return PDF_ROUTE_ALIASES.get(route, route)

EDGE_CATEGORIES = (
    "research_areas",
    "physical_systems",
    "techniques",
    "properties",
    "models",
    "observables",
    "datasets",
    "experiments",
)

_SAFE_CHARS_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def safe_doc_id(doc_id: str) -> str:
    clean = doc_id.strip().replace(":", "_").replace("/", "_")
    clean = _SAFE_CHARS_RE.sub("_", clean).strip("_")
    return clean or "unknown"


def is_allowed_route(route: str) -> bool:
    return route in ALLOWED_ROUTES


def edge_categories() -> list[str]:
    return list(EDGE_CATEGORIES)


def parsed_markdown_path(rag_dir: Path, doc_id: str) -> Path:
    return rag_dir / "reference" / "parsed" / f"{safe_doc_id(doc_id)}.md"


def parsed_manifest_path(rag_dir: Path, doc_id: str) -> Path:
    return rag_dir / "reference" / "parsed" / f"{safe_doc_id(doc_id)}.manifest.json"


def chunk_manifest_path(rag_dir: Path, doc_id: str) -> Path:
    return rag_dir / "reference" / "chunks" / f"{safe_doc_id(doc_id)}.jsonl"
