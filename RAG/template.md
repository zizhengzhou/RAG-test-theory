# DARW Source Page Template

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
