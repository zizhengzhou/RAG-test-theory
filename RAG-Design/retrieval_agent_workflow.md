# Retrieval Agent Workflow

This document defines the default boundary between the research agent and the
DARW RAG operations layer.

## Goals

- Keep research-agent context small by default.
- Expose only read-only retrieval tools to research workflows.
- Keep import, deletion, re-ingest, vocabulary review, and index maintenance in
  an operations workflow with explicit confirmation.
- Prefer chunk-level evidence with stable `chunk_id` provenance.

## Agent Boundary

### Research agent

The research agent may call only read-only commands:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "..." --top-k 8 --budget-tokens 2000 --json
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --budget-tokens 2000 --json
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "..."
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --provider inspire --json
```

It should not call import, delete, re-ingest, vocabulary, or index-maintenance
commands. If evidence is missing, it reports a gap instead of mutating the RAG.

### RAG operations agent

The operations workflow owns state-changing commands:

```bash
python scripts/rag/import_pipeline.py --rag-dir RAG --bib refs.bib --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --bib refs.bib --yes
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/apply_edges.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/rag_lint.py --rag-dir RAG
```

State-changing commands should remain dry-run first unless the user explicitly
approved the write.

## Retrieval Pipeline

The default retrieval path is:

1. Load evidence chunks.
2. Classify each chunk by `section_type`.
3. Score with TF-IDF and BM25.
4. Apply section-aware weighting.
5. Exclude references and metadata sections by default.
6. Return a compact context pack with provenance and gaps.

`--include-low-quality` can be used for audit/debug queries when references or
publisher metadata are intentionally needed.

## Context Profiles

### Compact profile

Default for research workflows. It returns:

- chunk IDs and source-page paths;
- short source summaries;
- compact BibTeX metadata, not full BibTeX blocks;
- trimmed evidence text;
- section type and retrieval scores;
- gap reports.

Use `--budget-tokens` to cap the approximate context size.

### Full profile

Use only for debugging or human review:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "..." --profile full --json
```

It includes full source-page frontmatter/body and full BibTeX entries.

## Done Criteria

- Research answers cite `chunk_id` and source page paths.
- Retrieval defaults do not return reference-list or publisher metadata chunks.
- Compact context remains small enough to pass between agents.
- RAG mutations are handled outside the research-agent path.
