# Vibe Research Pipeline — DARW Evidence-First RAG

Markdown-first, AI-maintained, researcher-readable research knowledge base with chunk-level provenance. Source pages are secondary knowledge; parsed Markdown and chunk JSONL under `RAG/reference/` are the primary evidence layer.

## Quick start

### 1. Initialize a project-specific RAG

```bash
python scripts/rag/rag_init.py --rag-dir RAG --dimensions methods,models,datasets --template-fields "summary,key findings,limitations,links" --vocabulary methods,models
```

This generates `RAG/template.md`, `RAG/vocabulary.md`, `RAG/index.md`, dimension directories under `RAG/summary/<dimension>/`, and the full reference skeleton. Dimensions and vocabulary remain project-specific; reusable scripts must not hardcode physics terms.

### 2. Import references

```bash
python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG --dry-run
python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG

python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG --dry-run
python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG
```

BibTeX import parses, normalizes, deduplicates, and appends entries to `RAG/references.bib`. Zotero ZIP import discovers RDF metadata and valid PDF attachments, including non-ASCII filenames on Windows.

### 3. Sync PDFs

```bash
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs --dry-run
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs
```

Matches local PDF files by citation key, DOI slug, or title slug and copies valid PDFs into `RAG/reference/pdfs/`.

### 4. Generate source pages or evidence

For metadata-only source pages:

```bash
python scripts/rag/build_source_pages.py --rag-dir RAG
```

For evidence-backed ingest:

```bash
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey
python scripts/rag/evidence_ingest.py --rag-dir RAG --all
```

`build_source_pages.py` creates source-page skeletons from `references.bib`. `evidence_ingest.py` runs the DARW pipeline: resolve → parse → chunk → update source-page evidence fields.

### 5. Summarize source pages

Prefer chunk-backed drafts when evidence chunks exist:

```bash
python scripts/rag/summarize_evidence.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/summarize_evidence.py --rag-dir RAG --key citationKey --yes
```

Fallback for legacy PDF-text placeholders:

```bash
python scripts/rag/summarize_sources.py --rag-dir RAG
```

Chunk-backed summaries cite `chunk_id` values. PDF-text fallback is useful for quick placeholders but is not a substitute for evidence-grounded claims.

### 6. Suggest vocabulary and edges

```bash
python scripts/rag/suggest_vocabulary.py --rag-dir RAG --key citationKey --dry-run
```

This reads evidence chunks and source metadata, proposes candidate controlled terms, and normalizes them through local vocabulary and PhySH mapping where configured. `RAG/vocabulary.md` may start as `terms: []`; that is a valid empty skeleton until terms are reviewed and added.

### 7. Search and trace evidence

```bash
python scripts/rag/search_evidence.py --rag-dir RAG "superconducting resonators TLS noise"
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "doc::section::chunk-001-abcdef1234"
```

Use `search_evidence.py` for chunk-level retrieval and `trace_claim.py` to print raw chunk text plus source page, parsed Markdown, manifest, route, section, and equation provenance.

### 8. Update navigation and lint

```bash
python scripts/rag/update_index.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG --strict
```

Lint covers BibTeX, links, PDF references, AUTO blocks, vocabulary schema, source-page schema, evidence manifests, and chunk JSONL. Strict mode treats metadata-only source pages as failures.

## Evidence routes

- `arxiv_source` — arXiv papers, parsed through arxiv2md HTML-to-Markdown with pandoc fallback and cached Markdown under `RAG/reference/arxiv_sources/`.
- `pdf_pymupdf` — PDF-only papers, parsed through `pymupdf4llm`.
- `pdf_mineru` — accepted only as a legacy compatibility alias for existing manifests or old CLI usage.

## Run tests

```bash
python -m pytest tests/ -v
```

The suite covers import, evidence resolution/parsing/chunking, validators, search, trace, maintenance, export, source-page building, and workflow integration.

## Directory layout

```text
RAG/
├── SKILL.md                    # Operation entry point
├── index.md                    # Navigation hub
├── template.md                 # Source page template (darw-source-v1)
├── vocabulary.md               # Controlled vocabulary (darw-vocabulary-v1)
├── log.md                      # Operation log
├── references.bib              # Shared references manifest
├── reference/
│   ├── pdfs/                   # Raw PDFs
│   ├── parsed/                 # Parsed Markdown + parsed manifests
│   ├── chunks/                 # Evidence chunk JSONL
│   ├── arxiv_sources/          # arxiv2md cache Markdown + cache manifests
│   └── imports/                # Import artifacts
└── summary/
    ├── sources/                # One secondary source page per paper
    ├── synthesis/              # Cross-source synthesis
    └── <dimension>/            # Project-specific dimension pages

.claude/skills/
├── rag-init/SKILL.md           # Initialization protocol
├── rag/SKILL.md                # Daily operations protocol
├── rag-import/SKILL.md         # Import operations protocol
├── rag-evidence/SKILL.md       # Evidence generation/search/trace protocol
└── rag-maintain/SKILL.md       # Maintenance operations protocol

scripts/rag/                    # Python CLI tools
tests/                          # Unit and integration tests
```

## Operation status

| Operation | Status | CLI | Notes |
|---|---|---|---|
| rag-init | Implemented | `rag_init.py` | Generates template, vocabulary, dimensions, evidence dirs |
| import-bib | Implemented | `import_bib.py` | Parse + normalize + dedup + append |
| import-zip | Implemented | `zip_importer.py` | Zotero RDF + PDF attachments |
| sync-pdf | Implemented | `sync_pdf.py` | Local PDF matching |
| build source pages | Implemented | `build_source_pages.py` | Metadata-only source-page skeletons |
| evidence ingest | Implemented | `evidence_ingest.py` | Resolve → parse → chunk → source-page evidence links |
| resolve source | Implemented | `resolve_source.py` | Chooses `arxiv_source` or `pdf_pymupdf` |
| parse evidence | Implemented | `parsers.py` | arxiv2md/pandoc/pymupdf4llm + arxiv2md cache |
| chunk evidence | Implemented | `chunker.py` | Deterministic chunk JSONL |
| summarize evidence | Implemented | `summarize_evidence.py` | Chunk-backed source summary drafts |
| suggest vocabulary | Implemented | `suggest_vocabulary.py` | Evidence-driven term/edge suggestions |
| search evidence | Implemented | `search_evidence.py` | TF-IDF over evidence chunks |
| trace claim | Implemented | `trace_claim.py` | Chunk provenance and raw text |
| lint | Implemented | `rag_lint.py` | Comprehensive validation, with `--strict` |
| validate evidence | Implemented | `validate_evidence.py` | Parsed/chunk manifest validation |
| validate vocabulary | Implemented | `validate_vocabulary.py` | Vocabulary schema and alias checks |
| validate source pages | Implemented | `validate_source_pages.py` | Source schema, edges, claims, evidence links |
| update-index | Implemented | `update_index.py` | AUTO block regeneration |
| maintain | Implemented | `maintain.py` | Source-page update/remove/re-ingest patterns |
| remove evidence | Implemented | `remove_evidence.py` | Removes evidence artifacts and scrubs source evidence fields |
| check staleness | Implemented | `check_staleness.py` | SHA/parser staleness detection |
| graph index | Implemented | `graph_index.py` | Source-page edge graph index |
| export | Implemented | `export.py` | Search, BibTeX export, reading lists |

`ingest.py` is legacy. Current workflows use `build_source_pages.py` for metadata stubs and `evidence_ingest.py` for evidence-backed ingest.
