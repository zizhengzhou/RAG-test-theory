---
name: rag-maintain
description: Maintain the Vibe Research Pipeline RAG knowledge base. Use for remove, update-source, re-ingest, and sync-pdf.
---

# RAG Maintain

Maintenance operations must preserve traceability and avoid destructive changes without confirmation.

## sync-pdf

Local PDF matching only:

```bash
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs --dry-run
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs
```

`sync_pdf.py` copies PDFs from BibTeX `file` fields or a local PDF directory into `RAG/reference/pdfs/`. It does not download from network providers.

For provider-backed downloads, use:

```bash
python scripts/rag/pdf_downloader.py --arxiv 2603.24450 --out RAG/reference/pdfs/paper.pdf --dry-run
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --dry-run
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --yes
```

`search_add.py` composes INSPIRE search, canonical BibTeX fetch, optional arXiv PDF download, source-page creation, and index refresh. Never download or add records silently.

## remove

Always run dry-run first and show the user every planned change:

```bash
python scripts/rag/maintain.py remove --rag-dir RAG --key citationKey --dry-run
```

After explicit user confirmation, run:

```bash
python scripts/rag/maintain.py remove --rag-dir RAG --key citationKey --yes
python scripts/rag/rag_lint.py --rag-dir RAG
```

The command removes the BibTeX entry, local source page, and matching local PDF, then rebuilds generated dimension indexes. It reports synthesis pages for manual review but does not delete them.

**For entries with generated evidence, use `evidence-remove` instead** (see `rag-evidence` skill):

```bash
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --yes
```

This also cleans parsed Markdown, manifests, chunk JSONL, and scrubs stale evidence links from source pages.

Never remove user files directly without confirmation.

## update-source

Use this for targeted frontmatter corrections while preserving narrative prose:

```bash
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set year=2025 --set primary-goals=cevns,new-physics --dry-run
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set year=2025 --yes
python scripts/rag/rag_lint.py --rag-dir RAG
```

Only existing frontmatter fields can be updated unless `--allow-new-field` is explicitly provided. Vocabulary validation is handled by lint.

## re-ingest

Use this to refresh source metadata defaults from `references.bib` or replace a local PDF while preserving existing source-page prose:

```bash
python scripts/rag/maintain.py re-ingest --rag-dir RAG --key citationKey --dry-run
python scripts/rag/maintain.py re-ingest --rag-dir RAG --key citationKey --replace-pdf path/to/paper.pdf --yes
python scripts/rag/rag_lint.py --rag-dir RAG
```

## staleness

Check whether parsed evidence or chunks are stale against source hashes and parser versions:

```bash
python scripts/rag/check_staleness.py --rag-dir RAG
python scripts/rag/check_staleness.py --rag-dir RAG --key citationKey
```

Use staleness results to decide whether to re-run `evidence_ingest.py` or remove/regenerate evidence artifacts.

## edges and graph maintenance

Normalize raw terms and migrate legacy tags into DARW edges:

```bash
python scripts/rag/edge_normalizer.py --rag-dir RAG --term "raw term" --dry-run
python scripts/rag/migrate_tags_to_edges.py --rag-dir RAG --dry-run
```

Build a graph index from source-page edges:

```bash
python scripts/rag/graph_index.py --rag-dir RAG --out RAG/indexes/graph_edges.yaml
```

These operations should remain dry-run first unless the user explicitly approves writes.
