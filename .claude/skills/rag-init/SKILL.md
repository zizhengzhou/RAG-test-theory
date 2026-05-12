---
name: rag-init
description: Initialize a project-specific Vibe Research Pipeline RAG knowledge base. Use when creating /RAG/, generating template.md, vocabulary.md, or project-specific dimensions.
---

# RAG Init

Initialize `/RAG/` as a Markdown-first research knowledge base.

## Protocol

1. Ask the user for:
   - project type and research scope;
   - desired dimension axes, such as methods/models/datasets/systematics, without assuming defaults;
   - source page fields;
   - initial controlled vocabulary entries and aliases.
2. Create or update:
   - `/RAG/template.md`;
   - `/RAG/vocabulary.md`;
   - `/RAG/index.md`;
   - `/RAG/log.md`;
   - `/RAG/summary/sources/`;
   - `/RAG/summary/synthesis/`;
   - `/RAG/summary/<dimension>/` for each approved dimension;
   - `/RAG/reference/pdfs/`, `/RAG/reference/parsed/`, `/RAG/reference/chunks/`, `/RAG/reference/arxiv_sources/`, and `/RAG/reference/imports/`.
3. Preserve `CLAUDE.md` as a thin index if it exists; do not move detailed knowledge there.
4. Do not hardcode a scientific field. Template and vocabulary are generated from the project answers.

## CLI helper

Use:

```bash
python scripts/rag/rag_init.py --rag-dir RAG --dimensions methods,models --template-fields "summary,key findings,limitations,links" --vocabulary "methods,models"
```

After initialization, run:

```bash
python scripts/rag/rag_lint.py --rag-dir RAG
```
