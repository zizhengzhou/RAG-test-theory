# RAG Operation Log

## 2026-05-11T17:25:34Z | rag-init

- input: dimensions=['experiment-groups', 'detector-materials', 'primary-goals', 'background-sources', 'project-relevance'] vocab=['experiment-groups', 'detector-materials', 'primary-goals', 'background-sources', 'project-relevance']
- result: ok

## 2026-05-11T17:31:50Z | import-bib

- input: source=./tests/resources/fortest-some-references.bib dry_run=False
- result: new=5 skipped=0

## 2026-05-11T17:31:50Z | import-zip

- input: source=./tests/resources/fortest-zotero-导出的条目.zip dry_run=False
- result: entries=3 new_bib=2 pdfs=3 skipped_html=1

## 2026-05-11T17:32:43Z | ingest

- input: manifest=./RAG/references.bib
- result: created=7 skipped=0

## 2026-05-11T17:32:44Z | summarize-sources

- input: sources_dir=./RAG/summary/sources
- result: updated=7 skipped=0

## 2026-05-11T17:32:44Z | update-index

- input: 
- result: updated=5 pages

## 2026-05-11T17:33:39Z | sync-pdf

- input: dry_run=False
- result: copied=4 missing=0

## 2026-05-11T17:33:40Z | summarize-sources

- input: sources_dir=./RAG/summary/sources
- result: updated=7 skipped=0

