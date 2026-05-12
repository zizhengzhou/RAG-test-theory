# RAG Knowledge Base

This directory is the Markdown-first research knowledge layer for the Vibe Research Pipeline.

## Entry points

- [Index](index.md)
- [Vocabulary](vocabulary.md)
- [Source template](template.md)
- [Operation log](log.md)
- [References manifest](references.bib)

## Layout

- `RAG/reference/` — raw materials: PDFs, BibTeX, Zotero exports, arxiv sources, import artifacts.
- `RAG/reference/parsed/` — parsed evidence Markdown and manifest JSON files.
- `RAG/reference/chunks/` — chunk manifest JSONL per document.
- `RAG/summary/sources/` — one structured source page per paper (knowledge index, not primary evidence).
- `RAG/summary/synthesis/` — cross-source synthesis, consensus, disputes, note-derived knowledge.
- `RAG/indexes/` — generated indexes: graph edges, dimension maps.

Use the skills in `.claude/skills/rag*` for operations.
