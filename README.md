# Vibe Research Pipeline — DARW Evidence-First RAG

Markdown-first, AI-maintained, researcher-readable research knowledge base with chunk-level provenance. Source pages are secondary knowledge; parsed Markdown and chunk JSONL under `RAG/reference/` are the primary evidence layer.

## Windows note

If your Windows terminal shows encoding noise, prefer running scripts through
the Anaconda Python with UTF-8 enabled:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONIOENCODING = "utf-8"
& "C:\ProgramData\anaconda3\python.exe" -X utf8 scripts\rag\rag_lint.py --rag-dir RAG
```

## Quick start

### 1. Initialize a project-specific RAG

```bash
python scripts/rag/rag_init.py --rag-dir RAG --dimensions methods,models,datasets --template-fields "summary,key findings,limitations,links" --vocabulary methods,models
```

This generates `RAG/template.md`, `RAG/vocabulary.md`, `RAG/index.md`, dimension directories under `RAG/summary/<dimension>/`, and the full reference skeleton. Dimensions and vocabulary remain project-specific; reusable scripts must not hardcode physics terms.

### 2. Import references

```bash
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --dry-run
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --yes
python scripts/rag/import_pipeline.py --zip path/to/zotero-export.zip --rag-dir RAG --dry-run
python scripts/rag/import_pipeline.py --query "paper description" --rag-dir RAG --dry-run
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --enrich-inspire --dry-run

python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG --dry-run
python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG

python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG --dry-run
python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG
```

Use `import_pipeline.py` for new imports: it builds an import plan first, reports duplicate match basis, PDF/source-page/evidence actions, and only writes when `--yes` is passed. Add `--enrich-inspire` when you want the plan to query INSPIRE and safely fill missing BibTeX fields such as `eprint` or `inspire`. The older focused commands remain available for low-level debugging. BibTeX import parses, normalizes, deduplicates, and appends entries to `RAG/references.bib`. Zotero ZIP import discovers RDF metadata and valid PDF attachments, including non-ASCII filenames on Windows.

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
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey --fallback-pdf-on-arxiv-fail
```

`build_source_pages.py` creates source-page skeletons from `references.bib`. `evidence_ingest.py` runs the DARW pipeline: resolve → parse → chunk → update source-page evidence fields.

If a local PDF is already available, it is preferred over re-downloading from arXiv. If an arXiv route exists but arxiv2md parsing fails, the default behavior is to stop with an error. Use `--fallback-pdf-on-arxiv-fail` only when you explicitly want to degrade to the PDF route.

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
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --online --dry-run
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --online --accept local:project-specific-term --yes
python scripts/rag/apply_edges.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/build_vocabulary_wiki.py --rag-dir RAG --dry-run
python scripts/rag/build_vocabulary_wiki.py --rag-dir RAG --strict-physh --dry-run
```

This reads evidence chunks and source metadata, proposes candidate controlled terms, and normalizes them through local vocabulary and PhySH mapping where configured. `RAG/vocabulary.md` may start as `terms: []`; that is a valid empty skeleton until terms are reviewed and added.

Keyword selection is review-based, not manual YAML editing. Existing vocabulary terms are reused automatically. Exact-label `physh:*` terms resolved from APS PhySH are safe to apply automatically. Semantic PhySH candidates keep the PhySH `canonical_id` and PhySH label, but require explicit `--accept <canonical_id>` review before saving. New `local:*` terms are treated as project-specific review candidates and are only saved when explicitly accepted with `--accept <canonical_id>` or `--accept-local-all`.

Any saved `physh:*` node must be a real concept returned by the PhySH API. Do not synthesize `physh:*` IDs or labels from extracted article text.

Use `build_vocabulary_wiki.py` to generate wiki pages from confirmed `vocabulary.md` nodes. `physh:*` and `local:*` nodes are treated equally once saved in the vocabulary; namespace is retained as provenance. Use `--strict-physh` only when you want a PhySH-only projection. Candidate terms not present in `vocabulary.md` are skipped/reported and are not emitted as wiki nodes.

### 7. Search and trace evidence

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "superconducting resonators TLS noise" --top-k 8 --json
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --json
python scripts/rag/query.py --rag-dir RAG --query "citationKey or DOI or title" --json
python scripts/rag/search_evidence.py --rag-dir RAG "superconducting resonators TLS noise"
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "doc::section::chunk-001-abcdef1234"
```

Use `context_pack.py` when preparing an AI answer: it bundles source pages, evidence chunks, BibTeX entries, graph edges, gaps, and provenance. Use `query.py --json` for structured local fallback by citation key, title, DOI, or arXiv. Use `search_evidence.py` for raw chunk-level retrieval and `trace_claim.py` to print raw chunk text plus source page, parsed Markdown, manifest, route, section, and equation provenance.

### 8. Update navigation and lint

```bash
python scripts/rag/update_index.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG --strict
python scripts/rag/validate_vocabulary.py --rag-dir RAG --online-physh
```

Lint covers BibTeX, links, PDF references, AUTO blocks, vocabulary schema, source-page schema, evidence manifests, and chunk JSONL. Strict mode treats metadata-only source pages as failures.

### 9. Delete entries

```bash
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --doi 10.xxxx/yyyy --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --arxiv 2603.24450 --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --yes
```

`delete_entry.py` plans removal of the BibTeX entry, source page, PDF, parsed Markdown, parsed manifest, chunk JSONL, arXiv cache artifacts, and Markdown references before writing. Title matches that hit multiple entries are reported as ambiguous.

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
| import pipeline | Implemented | `import_pipeline.py` | Unified BibTeX, Zotero ZIP, and INSPIRE/search plan/apply flow |
| BibTeX update | Implemented | `bib_update.py` | Safe INSPIRE-backed missing-field update plan and apply |
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
| apply vocabulary | Implemented | `apply_vocabulary.py` | Plan/apply vocabulary.md term additions |
| apply edges | Implemented | `apply_edges.py` | Plan/apply source-page edge updates |
| context pack | Implemented | `context_pack.py` | Structured source/chunk/BibTeX context for AI answers |
| search evidence | Implemented | `search_evidence.py` | TF-IDF over evidence chunks |
| embedding router | Implemented | `embedding_router.py` | Optional embedding backend with hash fallback |
| qdrant store | Implemented | `qdrant_store.py` | Dry-run/upsert scaffold for evidence chunks |
| hybrid query | Implemented | `query_hybrid.py` | Graph-aware scaffold with TF-IDF fallback |
| trace claim | Implemented | `trace_claim.py` | Chunk provenance and raw text |
| summarize topic | Implemented | `summarize_topic.py` | Deterministic chunk-grounded topic summary drafts |
| merge RAG update | Implemented | `merge_rag_update.py` | Duplicate key/doc-id/vocabulary review report |
| lint | Implemented | `rag_lint.py` | Comprehensive validation, with `--strict` |
| validate evidence | Implemented | `validate_evidence.py` | Parsed/chunk manifest validation |
| validate vocabulary | Implemented | `validate_vocabulary.py` | Vocabulary schema, alias checks, optional live PhySH concept validation |
| validate source pages | Implemented | `validate_source_pages.py` | Source schema, edges, claims, evidence links |
| update-index | Implemented | `update_index.py` | AUTO block regeneration |
| maintain | Implemented | `maintain.py` | Source-page update/remove/re-ingest patterns |
| remove evidence | Implemented | `remove_evidence.py` | Removes evidence artifacts and scrubs source evidence fields |
| check staleness | Implemented | `check_staleness.py` | SHA/parser staleness detection |
| graph index | Implemented | `graph_index.py` | Source-page edge graph index |
| vocabulary wiki | Implemented | `build_vocabulary_wiki.py` | Wiki pages for confirmed `physh:*` and `local:*` vocabulary nodes |
| export | Implemented | `export.py` | Search, INSPIRE-first BibTeX export with local fallback, reading lists |
| delete entry | Implemented | `delete_entry.py` | Unified dry-run deletion for Bib/source/PDF/evidence artifacts |

`ingest.py` is legacy. Current workflows use `build_source_pages.py` for metadata stubs and `evidence_ingest.py` for evidence-backed ingest.
