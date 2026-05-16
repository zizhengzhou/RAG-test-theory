# TODO - DARW Evidence-First RAG

Last updated: 2026-05-14

This file tracks the current completion state and the next verification or future-work items.

## Current stage completed

- Import pipeline is in place:
  - `scripts/rag/import_pipeline.py`
  - BibTeX, Zotero ZIP, INSPIRE/search planning and apply flow
  - existing local PDF is preferred over re-download
- Evidence ingest is in place:
  - `scripts/rag/evidence_ingest.py`
  - `arxiv_source` and `pdf_pymupdf` routes
  - parsed Markdown, manifests, and chunk JSONL generation
- arXiv failure policy is implemented:
  - `--fallback-pdf-on-arxiv-fail` is explicit
  - default behavior is fail-fast, not silent fallback
- Vocabulary suggestion quality has been improved:
  - broad standalone tokens such as `reactor` and `detector` are suppressed
  - fragmentary candidates such as `coherent elastic` are filtered when better longer phrases exist
  - acronyms and existing vocabulary-backed aliases are preserved
  - regression tests cover noisy evidence examples
- Review-driven vocabulary and edge workflow is implemented:
  - `local:*` terms require explicit acceptance before saving
  - semantic `physh:*` candidates require explicit acceptance before saving
  - exact safe PhySH matches can auto-apply when resolved safely
  - accepted vocabulary can drive edge application and wiki generation without manual YAML edits
- PhySH safety coverage is in place:
  - saved `physh:*` nodes must come from real PhySH concepts
  - semantic PhySH suggestions keep the real PhySH id/label
  - offline tests cover semantic suggestion → explicit acceptance → vocabulary save → edge/wiki flow
  - `validate_vocabulary.py --online-physh` can live-check saved `physh:*` terms
- Retrieval, validation, and maintenance tools are in place:
  - `context_pack.py`
  - `query_hybrid.py`
  - `delete_entry.py`
  - `merge_rag_update.py`
  - `summarize_topic.py`
  - validators and `rag_lint.py`
- Real project RAG artifacts have been updated through the reviewed flow:
  - a controlled set of `local:*` terms has been accepted into `RAG/vocabulary.md`
  - source-page edges have been applied only for canonical IDs present in the vocabulary
  - vocabulary wiki pages have been generated
  - `RAG/index.md` source-page AUTO block now reflects current source pages
- Documentation has been synchronized:
  - installation/test setup is documented through `pyproject.toml` and editable install commands
  - brittle fixed test-count claims were removed
  - the reviewed vocabulary workflow is documented
  - current evidence/vocabulary status is distinguished from deferred retrieval work

## Current verification status

- Focused vocabulary, PhySH, edge, wiki, and source-index tests have been added or expanded.
- Full local test suite passes: `199 passed`.
- Plugin smoke test passes and returns `success: true`.
- Real RAG offline validation passes:
  - `validate_vocabulary.py --rag-dir RAG`
  - `validate_source_pages.py --rag-dir RAG`
  - `validate_evidence.py --rag-dir RAG`
  - `rag_lint.py --rag-dir RAG`

## Optional verification

Network-dependent live PhySH validation can still be run when internet access is desired:

```bash
python scripts/rag/validate_vocabulary.py --rag-dir RAG --online-physh
```

## Deferred future work

- LLM-assisted source summaries and synthesis pages.
- Production vector retrieval and Qdrant integration beyond the current scaffolding.
- Full graph-aware hybrid retrieval beyond the current fallback/scaffold behavior.
- Larger vocabulary curation passes as more papers are imported.

## Done for this phase means

- Suggested vocabulary lists are human-reviewable and mostly free of prose junk.
- Every saved `physh:*` term is a real live-valid PhySH concept when checked online.
- `local:*` terms are explicit reviewed additions, not accidental extraction artifacts.
- Import and ingest behavior is deterministic around local PDF priority and arXiv fallback.
- The reviewed vocabulary → edge → wiki flow works without manual YAML editing.
- Tests, smoke test, validators, and lint pass on the final checked-out state.
