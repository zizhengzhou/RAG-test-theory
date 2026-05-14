---
name: rag-evidence
description: Generate, search, validate, trace, and remove DARW primary evidence. Use for evidence-ingest, evidence-search, evidence-validate, evidence-trace, and evidence-remove.
---

# RAG Evidence Operations

Manage the DARW primary evidence layer: parsed Markdown, evidence manifests, chunk JSONL, and provenance tracing. Primary evidence is the only valid source for physics claims.

## Evidence pipeline

```
BibTeX entry → resolve_source → parse (arxiv2md/pandoc/pymupdf4llm) → chunk → source page update
```

Two evidence routes exist:
- `arxiv_source` — arXiv ID present, uses arxiv2md (HTML→Markdown) with pandoc fallback (LaTeX source)
- `pdf_pymupdf` — PDF only, uses pymupdf4llm (PDF→Markdown); legacy `pdf_mineru` manifests remain readable

## Operations

### evidence-ingest

Ingest one or all entries through the full evidence pipeline:

```bash
# Single entry
python scripts/rag/evidence_ingest.py --rag-dir RAG --key degraaf2018

# All entries
python scripts/rag/evidence_ingest.py --rag-dir RAG --all

# Dry run
python scripts/rag/evidence_ingest.py --rag-dir RAG --key degraaf2018 --dry-run

# With pre-parsed output
python scripts/rag/evidence_ingest.py --rag-dir RAG --key degraaf2018 --arxiv-output path/to/parsed.md
python scripts/rag/evidence_ingest.py --rag-dir RAG --key degraaf2018 --pdf-output path/to/parsed.md
```

After ingest, the source page frontmatter is updated with evidence paths and the chunk manifest reference.

### evidence-search

Search evidence chunks (TF-IDF over chunk texts):

```bash
python scripts/rag/search_evidence.py --rag-dir RAG "superconducting resonators TLS noise"
python scripts/rag/search_evidence.py --rag-dir RAG --top-k 5 "frequency noise spin desorption"
python scripts/rag/search_evidence.py --rag-dir RAG --no-text "CEvNS neutrinos"
```

Results include chunk_id, doc_id, citation_key, source_page path, score, and chunk text snippet.

When answering physics questions using search results, always cite the chunk_id and provide the chunk text as evidence. Do not summarize or invent content not present in the chunk.

### evidence-validate

Validate all evidence artifacts:

```bash
python scripts/rag/validate_evidence.py --rag-dir RAG
```

Checks: schema versions, required fields, chunk_id uniqueness, SHA256 consistency, parsed Markdown existence.

### evidence-trace

Trace a chunk_id back to its source:

```bash
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "arxiv_1705.09158::results::chunk-003-a1b2c3d4e5"
```

Shows: chunk text, source page, parsed Markdown path, chunk manifest path, equation IDs, route.

### evidence-remove

Remove an entry and all its evidence artifacts:

```bash
# Preview
python scripts/rag/remove_evidence.py --rag-dir RAG --key degraaf2018 --dry-run

# Execute
python scripts/rag/remove_evidence.py --rag-dir RAG --key degraaf2018 --yes
```

Removes: parsed Markdown, parsed manifest, chunk JSONL, PDF. Cleans stale evidence references from source page frontmatter. Does not delete the source page itself.

### evidence-vocabulary

Suggest controlled vocabulary and edge candidates from evidence chunks:

```bash
python scripts/rag/suggest_vocabulary.py --rag-dir RAG --key degraaf2018 --dry-run
```

Use this when `RAG/vocabulary.md` is still `terms: []` or source-page edges are empty. Treat output as review candidates, not automatically accepted physics ontology.

### evidence-summary

Draft chunk-backed source page summaries:

```bash
python scripts/rag/summarize_evidence.py --rag-dir RAG --key degraaf2018 --dry-run
python scripts/rag/summarize_evidence.py --rag-dir RAG --key degraaf2018 --yes
```

Only use summary claims that cite existing chunk_ids. Preserve manual edits unless the user explicitly asks to overwrite.

## Protocol

1. For new papers with arXiv ID: `evidence-ingest` triggers the arxiv2md route automatically.
2. For PDF-only papers: ensure the PDF exists at `RAG/reference/pdfs/{key}.pdf` before ingest.
3. After ingest, validate with `evidence-validate`.
4. Before answering claims, search with `evidence-search` and cite chunk_ids.
5. When removing a paper, use `evidence-remove` (not manual file deletion) to keep source pages intact.
