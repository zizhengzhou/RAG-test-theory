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
2. Create one source page per entry using `/RAG/template.md`.
3. Fill bibliographic metadata and provenance. Do not invent paper content during this mechanical ingest step.
4. Assign only approved vocabulary tags. If a tag is unknown, propose a vocabulary diff or use `uncategorized` temporarily.
5. After ingest, if new source pages were created, ask the user which papers should receive AI reading summaries, which should use automatic local summaries, and which should be skipped for now.
6. For automatic summaries, run `python scripts/rag/summarize_sources.py --rag-dir RAG`; for AI summaries, read the corresponding PDF/text and write scholarly summaries into the source pages.
7. Run `update-index` and append `/RAG/log.md`.

### summarize-source

Use this after import/ingest or when the user requests a better source page.

1. Show candidate source pages with citation key, title, PDF availability, and current summary status.
2. Ask the user to select per paper: **AI summary**, **automatic summary**, or **skip**.
3. For AI summary, Claude should read the PDF or extracted text directly and write a scholarly summary: research question, method/design, key findings, limitations, and project relevance.
4. For automatic summary, run `python scripts/rag/summarize_sources.py --rag-dir RAG` and make clear that this is a fast fallback based on PDF text extraction, not a final scholarly reading.
5. Preserve manual edits unless the user explicitly asks to overwrite.
6. Append `/RAG/log.md` and run lint.

### query

1. Read `/RAG/index.md`.
2. Drill into relevant `/RAG/summary/<dimension>/` pages and `/RAG/summary/sources/` pages.
3. Answer with provenance links and distinguish supported claims, contradictions, and gaps.
4. If the synthesis is reusable, offer to save it under `/RAG/summary/synthesis/`.

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

Use local RAG search to identify known project papers, then INSPIRE to verify the canonical record. If INSPIRE has no matching record and the user accepts local fallback, use:

```bash
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --provider inspire --fallback-local
```

Do not edit paper-writing files; a writing skill should consume the returned BibTeX or citation key.

### export-bibtex / export-reading-list

Export subsets after search or tag selection:

```bash
python scripts/rag/export.py export-bibtex --rag-dir RAG --tag primary-goals=cevns --provider inspire --out refs.bib
python scripts/rag/export.py export-reading-list --rag-dir RAG --query "dark matter" --out reading-list.md
```

`export-bibtex` should use INSPIRE by default for canonical keys. `export-reading-list` emits Markdown with RAG source/PDF links and identifiers.
