# RAG Operation Log

## 2026-05-12T06:37:27Z | rag-init

- input: initialized=2026-05-12
- result: ok

## 2026-05-12T06:40:14Z | import-bib

- input: source=./tests/resources/fortest-some-references.bib dry_run=False
- result: new=5 skipped=0

## 2026-05-12T06:44:47Z | sync-pdf

- input: dry_run=False
- result: copied=5 missing=0

## 2026-05-12T06:44:59Z | ingest

- input: manifest=./RAG/references.bib
- result: created=5 skipped=0

## 2026-05-12T07:25:15Z | import-zip

- input: source=fortest-zotero-导出的条目.zip
- result: new=2 skipped=1 pdfs=2

## 2026-05-12T07:26:14Z | import-zip

- input: source=fortest-zotero-导出的条目.zip
- result: new=0 skipped=3 pdfs=0

## 2026-05-12T07:26:54Z | ingest

- input: manifest=./RAG/references.bib
- result: created=2 skipped=5

## 2026-05-12T07:27:35Z | ingest

- input: manifest=./RAG/references.bib
- result: created=1 skipped=6

## 2026-05-12T08:49:34Z | evidence-ingest

- input: key=abeleProspectNUCLEUSExperiment2026
- result: parsed=reference/parsed/arxiv_2603.24450.md chunks=reference/chunks/arxiv_2603.24450.jsonl

## 2026-05-12T09:31:08Z | evidence-ingest

- input: key=ackermann2025
- result: parsed=reference/parsed/arxiv_2501.05206.md chunks=reference/chunks/arxiv_2501.05206.jsonl

## 2026-05-12T09:34:30Z | evidence-ingest

- input: key=abeleProspectNUCLEUSExperiment2026
- result: parsed=reference/parsed/arxiv_2603.24450.md chunks=reference/chunks/arxiv_2603.24450.jsonl

