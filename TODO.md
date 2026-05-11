# TODO

## RAG design coverage review — 2026-05-12

Current implementation status against `RAG-Design/design.md`:

- Overall design coverage: about **72/100**.
- Implementation quality: about **74/100**.
- If scoped only to the foundational literature knowledge-base toolchain, current maturity is closer to **82/100**.
- The framework is now a usable base system, not just a prototype.

### Implemented well

- RAG initialization scaffold: `scripts/rag/rag_init.py`, `.claude/skills/rag-init/SKILL.md`.
- BibTeX parsing and rendering: `scripts/rag/bib_parser.py`.
- Metadata normalization and deduplication: `scripts/rag/metadata_normalizer.py`, `scripts/rag/dedup.py`.
- BibTeX import with dry-run and dedup: `scripts/rag/import_bib.py`.
- Zotero RDF/ZIP import: `scripts/rag/rdf_parser.py`, `scripts/rag/zip_importer.py`.
- Template-driven source-page ingest: `scripts/rag/ingest.py`.
- Vocabulary-driven index update: `scripts/rag/update_index.py`.
- Lint checks: `scripts/rag/rag_lint.py`.
- Maintenance operations: `scripts/rag/maintain.py` for remove, update-source, and re-ingest.
- INSPIRE search/export/get-bibtex: `scripts/rag/external_search.py`, `scripts/rag/export.py`.
- Reading-list and BibTeX subset export: `scripts/rag/export.py`.
- Provider PDF download: `scripts/rag/pdf_downloader.py`.
- Search-and-add: `scripts/rag/search_add.py`.
- Skill split is aligned with the design: `rag-init`, `rag`, `rag-import`, `rag-maintain`.

### Implemented but weak

- `scripts/rag/query.py`: currently simple substring search; design expects richer retrieval with provenance and gap/contradiction handling.
- `scripts/rag/sync_from_notes.py`: initial extraction exists, but no tests, no dedup/incremental update, and only one coarse `notes-sync.md` output.
- `scripts/rag/summarize_sources.py`: useful as automatic fallback, but not a substitute for scholarly AI reading summaries.
- `scripts/rag/sync_pdf.py`: local PDF copy works, but dry-run still creates `reference/pdfs/` and appends `log.md`; this breaks the stricter dry-run standard established elsewhere.
- Provenance is partial: links exist, but there is no dedicated `trace-claim` workflow.
- End-to-end orchestration exists mostly as skill protocol; full scripted E2E coverage is still limited.

### Missing or mostly uncovered

- RIS parser.
- `trace-claim`.
- `check-staleness` for arXiv/PDF/source freshness.
- `merge-rag-update` for collaborator updates.
- Dedicated `summarize-topic` workflow.
- Optional vector/semantic retrieval layer.
- Paper-writing skill integration beyond providing `get-bibtex`.
- Rich conflict/consensus synthesis workflow.

### Core operation scores

| Design operation | Status | Coverage | Quality |
|---|---|---:|---:|
| Zotero BibTeX import | implemented | 4 | 4 |
| Zotero RDF/PDF ZIP import | implemented | 4 | 4 |
| Deduplication | implemented | 4 | 4 |
| Remove irrelevant reference | implemented | 4 | 4 |
| Search-and-add by description | implemented | 4 | 4 |
| Incremental summary for new references | partial | 3 | 2 |
| Manage KB from project notes | initial | 2 | 2 |
| Find literature by content description | initial | 2 | 2 |
| Auto-insert writing references | RAG-side partial | 2 | 3 |
| Find relevant content/consensus during discussion | partial via Claude protocol | 2 | 2 |
| Correct wrong summaries | metadata/frontmatter implemented, content correction manual | 3 | 3 |
| Re-index references | implemented | 4 | 4 |

### Phase scores

| Phase | Design goal | Current score |
|---|---|---:|
| P0 | initialization, manual ingest, query, lint | 4/5 |
| P1 | BibTeX, dedup, PDF, import-bib/sync-pdf | 4/5 |
| P2 | remove, update-source, re-ingest, cleanup | 4/5 |
| P3 | Zotero RDF, INSPIRE/arXiv, search-and-add, notes, synthesis | 3/5 |
| P4 | get-bibtex, reading list, collaboration, staleness, writing integration | 2.5/5 |

### Highest-priority next work

1. Fix `scripts/rag/sync_pdf.py` dry-run side effects.
2. Enhance `scripts/rag/query.py` with structured search, scoring, tag/key support, and provenance-oriented output.
3. Add tests and incremental behavior for `scripts/rag/sync_from_notes.py`.
4. Implement a minimal `trace-claim` workflow.
5. Implement a minimal `check-staleness` workflow.

Recommended next slice: **sync_pdf dry-run fix + query enhancement + sync_from_notes tests** before adding more large features.

## Jinlei wiki comparison target

Compare this framework against `jinlei-wiki/`, especially:

- `jinlei-wiki/literature-wiki/README.md`
- `jinlei-wiki/literature-wiki/SKILL.md`
- `jinlei-wiki/research-profile/README.md`
- `jinlei-wiki/research-profile/SKILL.md`

Key question: how much of Jinlei's literature-wiki is a subset of this RAG framework, and how does completion quality compare?
