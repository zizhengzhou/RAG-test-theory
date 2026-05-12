"""Initialize a DARW RAG knowledge base."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from common import append_log, ensure_rag_dirs

TEMPLATE_CONTENT = """# DARW Source Page Template

Schema version: `darw-source-v1`

A source page is the **paper knowledge page + graph node + claim index + evidence anchor map**.
It references primary evidence chunks — it is not itself primary evidence.

---

## Frontmatter

```yaml
---
schema_version: "darw-source-v1"

doc_id: ""                           # canonical doc identifier (e.g. arxiv:2603.xxxxx, doi:10.xxxx/yyyy)
citation_key: ""                     # BibTeX citation key

identifiers:
  arxiv: null
  doi: null
  inspire: null
  zotero_key: null
  url: null

source:
  title: ""
  authors: []
  year: null
  venue: null
  abstract: ""
  source_type: "arxiv_source"       # arxiv_source | pdf_pymupdf
  primary_evidence: ""
  original_pdf: ""
  original_tex: null
  source_sha256: ""
  parser: ""                        # arxiv2md | pymupdf4llm
  parser_version: ""
  parsed_at: ""

edges:
  research_areas: []
  physical_systems: []
  techniques: []
  properties: []
  models: []
  observables: []
  datasets: []
  experiments: []

chunk_manifest: ""

quality:
  extraction_confidence: "high"     # high | medium | low
  needs_human_review: true
  math_extraction_quality: "unknown"
  metadata_conflicts: []

status:
  reading_status: "unread"          # unread | skimmed | read | verified
  relevance: "unknown"              # core | useful | peripheral | irrelevant
  last_checked: ""
---
```

### Edge entry shape

```yaml
- canonical_id: "physh:research-area:cevns"   # or local:xxx
  label: "Coherent elastic neutrino-nucleus scattering"
  local_aliases: ["CEvNS"]
  confidence: 0.9
```

Only `canonical_id` is required. All `canonical_id` values must be resolvable in `RAG/vocabulary.md`.

---

## Body sections

### 1. One-line contribution

### 2. Research context

### 3. Physical system / model

### 4. Methods and assumptions

### 5. Key results

Every important result must use a claim block referencing evidence chunks.

```claim
claim_id: claim-001
statement: ""
evidence:
  - chunk_id: ""
    section_anchor: ""
    equation_ids: []
confidence: "high"
```

### 6. Important equations

```equation
equation_id: eq-001
chunk_id: ""
latex: ""
meaning: ""
used_for: ""
```

### 7. Limitations and caveats

### 8. Relation to current project

### 9. Conflicts / agreements with other sources

### 10. Trace index

| claim_id | evidence chunk_id | section | equation_ids | notes |
|---|---|---|---|---|
| | | | | |
"""

VOCABULARY_CONTENT = """# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

This file is the **script-readable ontology cache**.
It is the authority for all `canonical_id` values used in `edges` fields.
Do not hardcode physics terms in scripts.

---

## Namespaces

| Namespace | Meaning |
|---|---|
| `physh:` | Term from APS PhySH controlled vocabulary |
| `local:` | Project-local controlled term |
| `alias:` | Non-canonical alias — never written as a final `canonical_id` |

---

## Categories

| Category | Description |
|---|---|
| `research_areas` | Sub-field or research program |
| `physical_systems` | Detector, material, or physical system |
| `techniques` | Experimental or computational methods |
| `properties` | Physical observables or quantities |
| `models` | Theoretical models or frameworks |
| `observables` | Measured quantities |
| `datasets` | Named datasets or data releases |
| `experiments` | Named experiments or facilities |

---

## Terms

```yaml
terms: []
```

---

## Rules

1. `edges` may only contain `canonical_id` values from this file.
2. Unknown terms enter `local:` with `needs_review: true`.
3. Aliases are for matching only — never written as final edge values.
4. APS PhySH API may be used for lookup; this cache is the authoritative fallback.
5. Conflicting terms must not be auto-merged.
6. `uncategorized` is temporary — propose a diff before committing new terms.

---

## Adding a new term

```yaml
- canonical_id: "local:new-term-key"
  label: "Human-readable label"
  namespace: "local"
  category: "research_areas"
  aliases: []
  parent: null
  related: []
  source: "llm"                   # physh | llm | user | script
  needs_review: true
```
"""

INDEX_CONTENT = """# RAG Index

## Navigation

- [Vocabulary](vocabulary.md)
- [Source template](template.md)
- [References manifest](references.bib)
- [Operation log](log.md)

## Knowledge areas

- [Sources](summary/sources/)
- [Synthesis](summary/synthesis/)

## Source pages

<!-- AUTO:SOURCES:BEGIN -->
No source pages indexed yet.
<!-- AUTO:SOURCES:END -->
"""

SKILL_CONTENT = """# RAG Knowledge Base

This directory is the Markdown-first research knowledge layer for the Vibe Research Pipeline.

## Entry points

- [Index](index.md)
- [Vocabulary](vocabulary.md)
- [Source template](template.md)
- [Operation log](log.md)
- [References manifest](references.bib)

## Layout

- `RAG/reference/` — raw materials: PDFs, BibTeX, Zotero exports, arxiv sources, import artifacts.
- `RAG/reference/parsed/` — parsed evidence Markdown and manifest JSON files.
- `RAG/reference/chunks/` — chunk manifest JSONL per document.
- `RAG/summary/sources/` — one structured source page per paper (knowledge index, not primary evidence).
- `RAG/summary/synthesis/` — cross-source synthesis, consensus, disputes, note-derived knowledge.
- `RAG/indexes/` — generated indexes: graph edges, dimension maps.

Use the skills in `.claude/skills/rag*` for operations.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize DARW RAG knowledge base")
    parser.add_argument("--rag-dir", default="RAG")
    args = parser.parse_args()

    rag_dir = Path(args.rag_dir).resolve()
    ensure_rag_dirs(rag_dir, ())

    # Create subdirectories
    (rag_dir / "indexes").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "parsed").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "chunks").mkdir(parents=True, exist_ok=True)
    (rag_dir / "reference" / "arxiv_sources").mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()

    # Core schema files — always write canonical embedded content
    (rag_dir / "template.md").write_text(TEMPLATE_CONTENT, encoding="utf-8")
    (rag_dir / "vocabulary.md").write_text(VOCABULARY_CONTENT, encoding="utf-8")

    # Navigation and metadata
    (rag_dir / "index.md").write_text(INDEX_CONTENT, encoding="utf-8")
    (rag_dir / "SKILL.md").write_text(SKILL_CONTENT, encoding="utf-8")

    # Append-only files — preserve if already existing
    if not (rag_dir / "log.md").exists():
        (rag_dir / "log.md").write_text("# RAG Operation Log\n\n", encoding="utf-8")
    if not (rag_dir / "references.bib").exists():
        (rag_dir / "references.bib").write_text("% RAG shared references manifest\n", encoding="utf-8")

    append_log(rag_dir, "rag-init", f"initialized={today}", "ok")
    print(f"RAG initialized at {rag_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
