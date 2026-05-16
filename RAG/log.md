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

## 2026-05-13T06:42:03Z | evidence-ingest

- input: key=ackermann2025
- result: parsed=reference/parsed/arxiv_2501.05206.md chunks=reference/chunks/arxiv_2501.05206.jsonl

## 2026-05-13T06:43:13Z | evidence-ingest

- input: key=panReviewBackgroundStudy2024
- result: parsed=reference/parsed/10.1393_ncc_i2024-24369-3.md chunks=reference/chunks/10.1393_ncc_i2024-24369-3.jsonl

## 2026-05-13T06:43:13Z | evidence-ingest

- input: key=kinastImprovingQualityCaWO42022
- result: parsed=reference/parsed/10.1007_s10909-022-02743-7.md chunks=reference/chunks/10.1007_s10909-022-02743-7.jsonl

## 2026-05-13T06:43:18Z | evidence-ingest

- input: key=dayBroadbandSuperconductingDetector2003
- result: parsed=reference/parsed/10.1038_nature02037.md chunks=reference/chunks/10.1038_nature02037.jsonl

## 2026-05-13T06:43:54Z | evidence-ingest

- input: key=degraafSuppressionLowfrequencyCharge2018
- result: parsed=reference/parsed/arxiv_1705.09158.md chunks=reference/chunks/arxiv_1705.09158.jsonl

## 2026-05-13T06:47:41Z | evidence-ingest

- input: key=yu2026
- result: parsed=reference/parsed/arxiv_2604.12572.md chunks=reference/chunks/arxiv_2604.12572.jsonl

## 2026-05-13T07:17:28Z | apply-vocabulary

- input: key=ackermann2025
- result: added=2 needs_review=18

## 2026-05-13T07:17:45Z | build-vocabulary-wiki

- input:
- result: written=0 skipped=0

## 2026-05-13T07:19:18Z | apply-edges

- input: key=ackermann2025
- result: added=2

## 2026-05-13T07:21:53Z | build-vocabulary-wiki

- input:
- result: written=2 skipped=0

## 2026-05-13T07:29:03Z | apply-vocabulary

- input: key=abeleProspectNUCLEUSExperiment2026
- result: added=1 needs_review=19

## 2026-05-13T07:29:33Z | apply-vocabulary

- input: key=dayBroadbandSuperconductingDetector2003
- result: added=2 needs_review=17

## 2026-05-13T07:30:00Z | apply-vocabulary

- input: key=degraafSuppressionLowfrequencyCharge2018
- result: added=1 needs_review=19

## 2026-05-13T07:30:37Z | apply-vocabulary

- input: key=kinastImprovingQualityCaWO42022
- result: added=1 needs_review=18

## 2026-05-13T07:31:03Z | apply-vocabulary

- input: key=panReviewBackgroundStudy2024
- result: added=1 needs_review=18

## 2026-05-13T07:31:34Z | apply-vocabulary

- input: key=yu2026
- result: added=0 needs_review=20

## 2026-05-13T07:32:02Z | apply-edges

- input: key=abeleProspectNUCLEUSExperiment2026
- result: added=1

## 2026-05-13T07:32:03Z | apply-edges

- input: key=dayBroadbandSuperconductingDetector2003
- result: added=2

## 2026-05-13T07:32:04Z | apply-edges

- input: key=degraafSuppressionLowfrequencyCharge2018
- result: added=1

## 2026-05-13T07:32:05Z | apply-edges

- input: key=kinastImprovingQualityCaWO42022
- result: added=1

## 2026-05-13T07:32:06Z | apply-edges

- input: key=panReviewBackgroundStudy2024
- result: added=2

## 2026-05-13T07:32:08Z | apply-edges

- input: key=yu2026
- result: added=0

## 2026-05-13T07:32:44Z | build-vocabulary-wiki

- input: 
- result: written=8 skipped=0

## 2026-05-13T07:37:26Z | build-vocabulary-wiki

- input:
- result: written=7 skipped=0

## 2026-05-16T03:32:03Z | update-index

- input:
- result: updated=19 pages source_index=True

