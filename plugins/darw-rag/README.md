# DARW RAG Plugin

Repo-local Codex plugin for the DARW evidence-first RAG workflow.

## Install / Discover

Clone this repository and install or enable the `plugins/darw-rag` plugin in
Codex. The plugin contributes the `darw-rag` skill, which points the agent at
the repository scripts under `scripts/rag/`.

## Start From A BibTeX Or Zotero ZIP

Run the smoke test first to verify the plugin, bootstrap path, evidence ingest,
compact search, and trace workflow:

```bash
python scripts/rag/plugin_smoke_test.py --json
```

Run a dry-run plan first:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --dry-run --json
python scripts/rag/bootstrap_rag.py --rag-dir RAG --zip path/to/zotero-export.zip --dry-run --json
```

Apply after review:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --yes --json
python scripts/rag/bootstrap_rag.py --rag-dir RAG --zip path/to/zotero-export.zip --yes --json
```

Use metadata-only import when evidence parsing should be deferred:

```bash
python scripts/rag/bootstrap_rag.py --rag-dir RAG --bib path/to/refs.bib --ingest none --yes --json
```

## Search

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --budget-tokens 2000 --json
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "chunk_id"
```

Default search is compact and filters reference-list / publisher-metadata chunks.
