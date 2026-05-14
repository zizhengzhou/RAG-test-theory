# RAG-test-theory — DARW evidence-first RAG

## RAG knowledge base at `/RAG/`

This project contains a DARW (evidence-first) RAG knowledge base for physics research. When answering questions that may be addressed by the literature in this knowledge base:

1. **Search evidence first**: `python scripts/rag/search_evidence.py --rag-dir RAG "query terms"`
2. **Cite chunk IDs** when using evidence: always include the `chunk_id` and source page path
3. **Trace for context**: `python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id <id>` to get full provenance
4. **Do not invent claims** — if no evidence chunk exists for a conclusion, say so

## Evidence pipeline

```
BibTeX → resolve → parse (arxiv2md/pymupdf4llm/pandoc) → chunk (LlamaIndex) → validate → searchable
```

Two evidence routes:
- `arxiv_source` — papers with arXiv ID (HTML→Markdown, TeX→pandoc fallback)
- `pdf_pymupdf` — PDF-only papers (uses pymupdf4llm; legacy `pdf_mineru` is accepted as a compatibility alias)

## Key conventions

- **Primary evidence** = parsed Markdown + chunk JSONL under `RAG/reference/`
- **Secondary knowledge** = source pages under `RAG/summary/sources/`
- **Vocabulary** = controlled terms in `RAG/vocabulary.md` (empty `terms: []` until populated)
- **Edges** = structured `canonical_id` references in source page frontmatter
- **Claims** = `chunk_id`-backed statements in source page body claim blocks

## Primary scripts (use via skills or directly)

| Category | Script | Purpose |
|---|---|---|
| **Init** | `rag_init.py` | Initialize DARW directory skeleton and template files |
| **Import** | `import_bib.py` | Import BibTeX files with dedup |
| | `zip_importer.py` | Import Zotero RDF+PDF zip exports |
| | `search_add.py` | INSPIRE search + add to knowledge base |
| | `sync_pdf.py` | Sync local PDFs into RAG |
| | `pdf_downloader.py` | Download arXiv PDFs |
| **Evidence** | `evidence_ingest.py` | Full pipeline: resolve → parse → chunk → update source page |
| | `parsers.py` | Parse papers (arxiv2md, pandoc, pymupdf4llm) |
| | `chunker.py` | Sentence-level chunking via LlamaIndex |
| | `resolve_source.py` | Resolve BibTeX entry to evidence route |
| **Query** | `search_evidence.py` | TF-IDF search over evidence chunks |
| | `query.py` | Quick substring search over all Markdown files |
| | `trace_claim.py` | Trace chunk_id back to source/provenance |
| **Validate** | `rag_lint.py` | Comprehensive lint (BibTeX, links, schema, evidence, vocab, source pages) |
| | `validate_evidence.py` | Validate parsed manifests and chunk JSONL |
| | `validate_vocabulary.py` | Validate vocabulary.md term structure |
| | `validate_source_pages.py` | Validate source page schema, edges, claims |
| **Maintain** | `maintain.py` | Remove, update-source, re-ingest entries |
| | `remove_evidence.py` | Remove evidence artifacts + scrub source page links |
| | `check_staleness.py` | Detect SHA256 drift, parser version changes |
| **Enrich** | `physh_mapper.py` | Normalize terms via PhySH API + vocabulary |
| | `edge_normalizer.py` | Batch-normalize raw terms to edge entries |
| | `migrate_tags_to_edges.py` | Migrate legacy free-string tags to edges |
| | `graph_index.py` | Build graph index from source page edges |
| | `update_index.py` | Rebuild auto-generated index blocks |
| | `summarize_sources.py` | Legacy: fill source page placeholders via pdftotext |
| **Export** | `export.py` | Search, BibTeX export, reading list export |

## Skills

- `/rag-evidence` — generate, search, validate, trace, remove evidence
- `/rag-import` — import BibTeX, Zotero ZIP, search-and-add
- `/rag-init` — initialize RAG knowledge base
- `/rag` — daily operations (ingest, query, lint, update-index, export)
- `/rag-maintain` — remove, update-source, re-ingest, sync-pdf

## Running tests

```bash
python -m pytest tests/ -v
```

193 tests covering: evidence pipeline (resolve, parse, chunk, ingest), search, remove, validate (evidence, vocabulary, source pages), lint, import (BibTeX, ZIP), export, external search, maintain, PDF handling, workflow integration, bootstrap, plugin smoke tests, and compact research context packs.
