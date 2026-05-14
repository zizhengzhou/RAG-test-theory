---
name: darw-rag
description: Bootstrap and operate a DARW evidence-first research RAG from BibTeX or Zotero ZIP inputs. Use for first-run setup, importing references, evidence-backed search, and read-only context packs.
---

# DARW RAG Plugin

This plugin turns a cloned repository into a usable evidence-first research RAG.

## First-run bootstrap

Use this when the user provides a BibTeX file, Zotero RDF+PDF ZIP, or local PDF
folder and wants to start using the RAG immediately.

To verify a fresh clone before importing user data, run:

```bash
python scripts/rag/plugin_smoke_test.py --json
```

Always dry-run first:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --dry-run --json
python scripts/rag/bootstrap_rag.py --rag-dir RAG --zip path/to/zotero-export.zip --dry-run --json
```

After the user confirms the plan:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --yes --json
python scripts/rag/bootstrap_rag.py --rag-dir RAG --zip path/to/zotero-export.zip --yes --json
```

The bootstrap command initializes missing RAG files, imports references, creates
source pages, attempts evidence ingest for new entries, and runs lint.

For metadata-only import without evidence parsing:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --ingest none --yes --json
```

## Research-agent search

For normal research answers, use compact read-only context packs:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --budget-tokens 2000 --json
```

If the answer depends on a specific citation key:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --budget-tokens 2000 --json
```

When quoting or verifying a claim, trace the chunk:

```bash
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "chunk_id"
```

Every scientific claim must cite `chunk_id` and source page path. If no chunk
supports the claim, report a gap instead of inventing content.

## Operations boundary

Research workflows should stay read-only: `context_pack.py`, `search_evidence.py`,
`trace_claim.py`, and `export.py get-bibtex`.

State-changing workflows belong to RAG operations: bootstrap, import, re-ingest,
delete, vocabulary, edges, and lint. Keep state-changing commands dry-run first
unless the user explicitly approves writes.
