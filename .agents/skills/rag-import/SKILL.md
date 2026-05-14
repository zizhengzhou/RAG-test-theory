---
name: rag-import
description: Import external references into the Vibe Research Pipeline RAG knowledge base. Use for import-bib, import-zip, and search-and-add.
---

# RAG Import

External import operations compose parser, normalizer, deduplication, PDF sync, evidence-ingest, summary-mode selection, and lint.

After every successful import that creates or updates source pages, do **not** silently leave placeholder summaries. Present the imported papers to the user and ask which papers should receive AI reading summaries and which should use the automatic local summary fallback.

Summary-mode choices:

- **AI summary**: Codex reads the PDF/text and writes a scholarly source page summary with methods, findings, limitations, and relevance to the project. Use for important papers, review papers, and papers likely to affect synthesis.
- **Automatic summary**: prefer `python scripts/rag/summarize_evidence.py --rag-dir RAG --key <key> --dry-run` when chunks exist; otherwise run `python scripts/rag/summarize_sources.py --rag-dir RAG` as a PDF-text fallback.
- **Skip for now**: leave source page metadata only, but report that it remains unsummarized.

The assistant should ask using a paper list grouped by title/citation key, allowing the user to choose per paper or choose a bulk default. Then perform the chosen summary steps and run lint.

## import-bib

Prefer the unified import pipeline for normal imports:

```bash
python scripts/rag/import_pipeline.py --rag-dir RAG --bib path/to/file.bib --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --bib path/to/file.bib --enrich-inspire --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --bib path/to/file.bib --yes
```

Use the lower-level commands below only for debugging a specific stage.

1. Parse the input BibTeX file.
2. Normalize DOI, arXiv ID, title, authors, and citation key.
3. Deduplicate against `/RAG/references.bib` by DOI, arXiv, normalized title, then author/year.
4. Append new entries to `/RAG/references.bib` unless `--dry-run` is set.
5. Append `/RAG/log.md`.
6. Run `sync-pdf` if the BibTeX `file` field or a local PDF directory is available.
7. Run `evidence-ingest` to create source pages and generate evidence artifacts (parsed Markdown, chunk manifests).
8. Run `evidence-validate` to verify the generated evidence.
9. Ask the user to choose AI summary / automatic summary / skip for the newly imported papers.
10. Apply the selected summary mode and run lint.

CLI:

```bash
python scripts/rag/import_bib.py --bib path/to/file.bib --rag-dir RAG --dry-run
python scripts/rag/import_bib.py --bib path/to/file.bib --rag-dir RAG
```

## import-zip

Prefer:

```bash
python scripts/rag/import_pipeline.py --rag-dir RAG --zip path/to/zotero.zip --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --zip path/to/zotero.zip --yes
```

For Zotero RDF exports:

1. Unzip to a temporary directory.
2. Find `exported-items.rdf` or the first `.rdf` file.
3. Parse metadata and attachment relationships.
4. Copy only valid PDF attachments into `/RAG/reference/pdfs/`.
5. Skip HTML snapshots and non-PDF attachments.
6. Run `evidence-ingest` to create source pages and generate evidence artifacts.
7. Run `evidence-validate` to verify the generated evidence.
8. Ask the user to choose AI summary / automatic summary / skip for the imported papers.
9. Apply the selected summary mode and run lint.

CLI:

```bash
python scripts/rag/zip_importer.py --zip path/to/zotero.zip --rag-dir RAG --dry-run
```

## search-and-add

Prefer:

```bash
python scripts/rag/import_pipeline.py --rag-dir RAG --query "paper description" --limit 5 --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --record-id INSPIRE_ID --yes
```

Search is AI-orchestrated but script-executed:

1. Use Codex to refine the user's natural-language description into one or more search queries.
2. Run deterministic provider search and show candidates with title, year, authors, arXiv/DOI, INSPIRE id, duplicate status if known, and PDF availability.
3. Ask the user to choose a candidate when results are ambiguous.
4. Run dry-run add and show every planned write.
5. Only after explicit confirmation, run with `--yes`.
6. Run lint and ask AI summary / automatic summary / skip for the new source page.

Commands:

```bash
python scripts/rag/search_add.py search --query "paper description" --limit 5
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --dry-run
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --yes
```

`search_add.py` uses `scripts/rag/external_search.py` for INSPIRE search/canonical BibTeX and `scripts/rag/pdf_downloader.py` for arXiv PDF download when an arXiv id is available. Never add records or download PDFs silently.
