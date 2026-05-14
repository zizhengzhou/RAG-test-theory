---
name: rag
description: Operate the Vibe Research Pipeline RAG knowledge base. Use for ingest, query, lint, update-index, sync-from-notes, and get-bibtex.
---

# RAG Daily Operations

This skill operates `/RAG/` as a persistent Markdown research knowledge base.

Always read `/RAG/index.md`, `/RAG/template.md`, and `/RAG/vocabulary.md` before changing source pages or dimension pages.

## Operations

### ingest

1. Locate entries in `/RAG/references.bib` without source pages in `/RAG/summary/sources/`.
2. For metadata-only pages, run `python scripts/rag/build_source_pages.py --rag-dir RAG`; for evidence-backed ingest, use `python scripts/rag/evidence_ingest.py --rag-dir RAG --key <key>`.
3. Fill bibliographic metadata and provenance. Do not invent paper content during this mechanical ingest step.
4. Use canonical edge IDs from `/RAG/vocabulary.md`; if terms are missing, run `python scripts/rag/suggest_vocabulary.py --rag-dir RAG --key <key> --dry-run` and review the proposed vocabulary/edge additions.
5. After ingest, if new source pages were created, ask the user which papers should receive AI reading summaries, which should use automatic local summaries, and which should be skipped for now.
6. For automatic summaries, prefer `python scripts/rag/summarize_evidence.py --rag-dir RAG --key <key> --dry-run` when chunks exist; otherwise use `python scripts/rag/summarize_sources.py --rag-dir RAG` as a PDF-text fallback.
7. Run `update-index` and append `/RAG/log.md`.

### summarize-source

Use this after import/ingest or when the user requests a better source page.

1. Show candidate source pages with citation key, title, PDF availability, and current summary status.
2. Ask the user to select per paper: **AI summary**, **automatic summary**, or **skip**.
3. For AI summary, Codex should read the PDF or extracted text directly and write a scholarly summary: research question, method/design, key findings, limitations, and project relevance.
4. For automatic summary, prefer `python scripts/rag/summarize_evidence.py --rag-dir RAG --key <key> --dry-run` when chunks exist; otherwise run `python scripts/rag/summarize_sources.py --rag-dir RAG` as a PDF-text fallback.
5. Preserve manual edits unless the user explicitly asks to overwrite.
6. Append `/RAG/log.md` and run lint.

### query

1. Build a structured context pack first:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --json
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --budget-tokens 2000 --json
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --json
```

The default profile is compact and read-only. It returns short source summaries,
trimmed evidence chunks, section types, provenance links, and gaps. Use the full
profile only for debugging or human review:

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --profile full --json
```

2. If chunk evidence is sparse, use structured local fallback:

```bash
python scripts/rag/query.py --rag-dir RAG --query "title DOI arXiv or key" --json
```

3. Answer with provenance links and distinguish supported claims, contradictions, and gaps.
4. Do not import, delete, re-ingest, or mutate vocabulary from the research-query path.
5. If the synthesis is reusable, offer to save it under `/RAG/summary/synthesis/`.

### update-index

1. Scan source page frontmatter.
2. Rebuild dimension page AUTO blocks between `<!-- AUTO:BEGIN -->` and `<!-- AUTO:END -->`.
3. Preserve manual prose outside AUTO blocks.
4. Update `/RAG/index.md` source listing.

### sync-from-notes

Extract explicit citations, decisions, consensus, open questions, and failed attempts from project notes into `/RAG/summary/synthesis/notes-sync.md` with links to the originating note.

### lint

Run:

```bash
python scripts/rag/rag_lint.py --rag-dir RAG
```

Check duplicate BibTeX keys, missing PDFs, dead links, off-vocabulary tags, orphan source pages, missing dimension pages, and AUTO block integrity.

### get-bibtex

Search first, then export BibTeX. For HEP writing workflows, prefer INSPIRE canonical BibTeX so collaborators share citation keys and formatting:

```bash
python scripts/rag/export.py search --rag-dir RAG --query "paper description" --limit 5
python scripts/rag/export.py get-bibtex --rag-dir RAG --query "arxiv:2603.24450" --provider inspire
```

Use local RAG search to identify known project papers, then INSPIRE to verify the canonical record. `get-bibtex` falls back to local BibTeX by default when INSPIRE has no matching record; use strict mode when fallback is not acceptable:

```bash
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --provider inspire --json
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --strict-provider inspire
```

Do not edit paper-writing files; a writing skill should consume the returned BibTeX or citation key.

### export-bibtex / export-reading-list

Export subsets after search or tag selection:

```bash
python scripts/rag/export.py export-bibtex --rag-dir RAG --tag primary-goals=cevns --provider inspire --out refs.bib
python scripts/rag/export.py export-reading-list --rag-dir RAG --query "dark matter" --out reading-list.md
```

`export-bibtex` should use INSPIRE by default for canonical keys. `export-reading-list` emits Markdown with RAG source/PDF links and identifiers.
