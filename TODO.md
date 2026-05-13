# TODO - DARW Evidence-First RAG

Last updated: 2026-05-13

This file is a stage summary: what has been completed, what is already
verified, and what we should do next.

## Current stage completed

- Import pipeline is in place:
  - `scripts/rag/import_pipeline.py`
  - BibTeX, Zotero ZIP, INSPIRE/search planning and apply flow
  - existing local PDF is preferred over re-download
- Evidence ingest is in place:
  - `scripts/rag/evidence_ingest.py`
  - `arxiv_source` and `pdf_pymupdf` routes
  - parsed markdown, manifests, and chunk JSONL generation
- arXiv failure policy is implemented:
  - `--fallback-pdf-on-arxiv-fail` is explicit
  - default behavior is fail-fast, not silent fallback
- Vocabulary and edge workflow is in place:
  - `suggest_vocabulary.py`
  - `apply_vocabulary.py`
  - `apply_edges.py`
  - `build_vocabulary_wiki.py`
- PhySH safety contract is in place:
  - `physh:*` nodes must come from real PhySH API concepts
  - semantic PhySH suggestions keep the real PhySH id/label
  - semantic PhySH suggestions still require review before saving
  - `validate_vocabulary.py --online-physh` can live-check saved `physh:*`
- Retrieval and maintenance tools are in place:
  - `context_pack.py`
  - `query_hybrid.py`
  - `delete_entry.py`
  - `merge_rag_update.py`
  - `summarize_topic.py`
- Vocabulary suggestion quality has been improved:
  - common PDF/reference noise is filtered
  - ranking now prefers multi-word phrases, acronyms, and domain-signaled terms
  - some generic section-title and container-word noise has been suppressed
- Documentation has been partially cleaned:
  - broken old `TODO.md` has been replaced
  - `README.md` now documents Windows UTF-8/Anaconda usage
  - `README.md` now documents explicit arXiv fallback behavior
  - `README.md` now documents strict `physh:*` provenance expectations

## Current verified state

- Full test suite passes locally.
- `rag_lint.py --rag-dir RAG` passes on the real project data.
- Live vocabulary validation passes for saved `physh:*` terms.
- All current real source pages have evidence artifacts.
- Confirmed vocabulary nodes can already generate wiki pages.
- A real subagent drill for import/evidence/vocabulary/wiki flow has been completed in an isolated temp RAG.

## Main remaining work

### 1. Vocabulary suggestion quality

- Continue reducing broad or fragmentary candidates such as:
  - `reactor`
  - `detector`
  - `coherent elastic`
  - other short prefixes already covered by longer better phrases
- Improve ranking so human review sees the most useful local candidates first.
- Add more regression tests using real noisy examples from the current RAG.

### 2. Real review-driven vocabulary flow

- Re-run an isolated subagent drill after the latest suggestion changes.
- Review suggested `local:*` candidates before saving any more into the main `RAG/vocabulary.md`.
- After review, accept a small controlled set into vocabulary.
- Apply source-page edges from the accepted vocabulary.
- Rebuild vocabulary wiki pages after the accepted terms are written.

### 3. PhySH end-to-end safety

- Add one more end-to-end test for:
  - semantic PhySH suggestion
  - explicit acceptance
  - vocabulary save
  - wiki generation

### 4. Documentation and cleanup

- Add one concrete walkthrough from:
  - local PDF or arXiv id
  - evidence ingest
  - suggestion review
  - accepted vocabulary
  - edge application
  - wiki output
- Check remaining docs and skill files for encoding damage or stale behavior.
- Inspect `RAG/log.md` for repeated or noisy batch-operation records.
- Clean temp drill directories only after explicit user approval:
  - `.tmp_parent_rag_flow/`
  - `.tmp_subagent_rag_flow/`
  - `.tmp_real_drill_subagent/`

## Suggested next order

1. Finish one more round of `suggest_vocabulary.py` filtering and ranking.
2. Run a fresh isolated subagent drill and inspect the candidate list.
3. Review and accept a small set of good `local:*` and reviewed `physh:*` terms.
4. Apply edges and rebuild vocabulary wiki pages.
5. Re-run tests, lint, and live PhySH validation.

## Done for this phase means

- Suggested vocabulary lists are human-reviewable and mostly free of prose junk.
- Every saved `physh:*` term is a real live-valid PhySH concept.
- `local:*` terms are explicit reviewed additions, not accidental extraction artifacts.
- Import and ingest behavior is deterministic around local PDF priority and arXiv fallback.
- The full flow can be demonstrated in an isolated temp RAG without manual YAML editing.
