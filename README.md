# Vibe Research Pipeline — DARW Evidence-First RAG

这是一个本地部署的、Markdown-first 的研究文献 RAG 知识系统。它用于管理论文和研究资料，并把 BibTeX、PDF、解析后的 Markdown、证据 chunk、source page、词表、知识图关系和导出结果组织在同一个可审计的本地目录中。

本项目遵循 DARW evidence-first 原则：**重要结论必须能追溯到 evidence chunk、source page 和原始文献来源**。Source page 是二级知识整理层；`RAG/reference/` 下的解析文本和 chunk JSONL 才是主要证据层。

## 这个系统能做什么

| 功能 | 作用 | 常用入口 |
|---|---|---|
| 初始化知识库 | 创建 `RAG/` 骨架、模板、词表、索引和 evidence 目录 | `scripts/rag/rag_init.py` |
| 导入文献 | 从 BibTeX、Zotero ZIP 或 INSPIRE 搜索结果导入条目 | `import_pipeline.py`, `import_bib.py`, `zip_importer.py`, `search_add.py` |
| 同步和下载 PDF | 把本地 PDF 匹配到 citation key，或从 arXiv/provider 下载 PDF | `sync_pdf.py`, `pdf_downloader.py` |
| 生成 source page | 从 `references.bib` 生成每篇论文的结构化 source page | `build_source_pages.py` |
| 生成 evidence | 解析 arXiv/PDF，生成 Markdown、manifest 和 chunk JSONL | `evidence_ingest.py`, `resolve_source.py`, `parsers.py`, `chunker.py` |
| 生成摘要 | 基于 evidence chunks 或 PDF 文本补全 source page 摘要 | `summarize_evidence.py`, `summarize_sources.py`, `summarize_topic.py` |
| 查询和追踪 | 打包 AI 上下文、搜索证据 chunk、追踪 claim provenance | `context_pack.py`, `query.py`, `search_evidence.py`, `trace_claim.py` |
| 维护词表和关系 | 生成、审核、应用 controlled vocabulary 和 source edges | `suggest_vocabulary.py`, `apply_vocabulary.py`, `apply_edges.py`, `build_vocabulary_wiki.py`, `graph_index.py` |
| 校验和重建索引 | 重建 `AUTO` 区块，检查 BibTeX、链接、schema、evidence 和词表 | `update_index.py`, `rag_lint.py`, `validate_*.py` |
| 维护和删除 | 更新 source metadata、重新 ingest、移除 evidence 或完整删除条目 | `maintain.py`, `remove_evidence.py`, `delete_entry.py` |
| 导出 | 搜索本地记录，导出 INSPIRE-first BibTeX 或阅读清单 | `export.py` |

## 目录和核心文件

```text
RAG/
├── SKILL.md                    # RAG 操作入口说明
├── index.md                    # 导航入口，包含自动生成的 source page 列表
├── template.md                 # source page 模板与 schema
├── vocabulary.md               # controlled vocabulary，所有 canonical_id 的权威来源
├── log.md                      # 操作日志
├── references.bib              # 共享 BibTeX manifest
├── reference/
│   ├── pdfs/                   # 原始 PDF
│   ├── parsed/                 # 解析后的 Markdown 和 parsed manifest
│   ├── chunks/                 # evidence chunk JSONL
│   ├── arxiv_sources/          # arxiv2md cache Markdown 和 manifest
│   └── imports/                # 导入过程产物
└── summary/
    ├── sources/                # 每篇论文一个 source page
    ├── synthesis/              # 跨文献综合、共识、争议和笔记同步
    └── <dimension>/            # 项目自定义维度页面

scripts/rag/                    # Python CLI 工具
tests/                          # 单元测试和集成测试
```

常用入口：

- [RAG/index.md](RAG/index.md) — 当前知识库导航。
- [RAG/template.md](RAG/template.md) — source page 字段和 claim/equation block 格式。
- [RAG/vocabulary.md](RAG/vocabulary.md) — `physh:*`、`local:*` 等 `canonical_id` 的权威词表。
- [RAG/SKILL.md](RAG/SKILL.md) — RAG 目录的操作入口说明。
- [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) — Claude 使用本知识库时应遵守的 evidence-first 规则。

## 安装与快速检查

先进入项目目录：

```bash
cd "/Users/cttc/Documents/human ai/rag/RAG-test-theory"
```

安装开发依赖：

```bash
python -m pip install -e ".[dev]"
```

如果要使用 evidence 解析和 retrieval 后端，安装可选依赖：

```bash
python -m pip install -e ".[dev,evidence,retrieval]"
```

外部工具如 `pandoc` 和 `pdftotext` 是特定解析路径和旧式摘要路径的可选 fallback。

安装后运行 smoke test，检查插件发现、bootstrap import、evidence chunking、context pack 和 trace 能否在无网络条件下工作：

```bash
python scripts/rag/plugin_smoke_test.py --json
```

## 最小端到端使用流程

本仓库已经包含一个初始化好的 [RAG/](RAG/) 知识库。第一次使用时，建议按下面顺序形成最小闭环：

1. 安装依赖并运行 smoke test。
2. 查看 [RAG/index.md](RAG/index.md)、[RAG/template.md](RAG/template.md)、[RAG/vocabulary.md](RAG/vocabulary.md)。
3. 导入一条或一批 BibTeX/Zotero/INSPIRE 文献。
4. 同步或下载 PDF。
5. 生成 metadata-only source page，或直接生成 evidence-backed source page。
6. 基于 chunks 生成摘要、词表和 edges。
7. 运行 `update_index.py` 重建自动索引。
8. 运行 `rag_lint.py` 检查知识库一致性。
9. 用 `context_pack.py` 或 `search_evidence.py` 查询，并用 `trace_claim.py` 追踪证据。

如果要在一个新项目里创建新的 RAG 骨架，使用：

```bash
python scripts/rag/rag_init.py --rag-dir RAG --dimensions methods,models,datasets --template-fields "summary,key findings,limitations,links" --vocabulary methods,models
```

## 操作安全规则

- 导入、删除、re-ingest、批量 PDF 同步、词表应用前，优先运行 `--dry-run`。
- 只有确认 citation key、title、identifier、PDF 路径和计划改动正确后，再使用 `--yes`。
- 导入、删除、生成 evidence、修改词表或 edges 后，运行：

```bash
python scripts/rag/update_index.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG
```

- 关键结论不要只引用摘要，必须回到 evidence chunk 或原文 provenance。
- 使用 evidence 回答问题时，应包含 `chunk_id` 和 source page 路径。
- `AUTO` block 由脚本维护；手工说明应写在 `AUTO` block 外。

## 典型工作流

### 1. 导入一篇或一批新论文

推荐使用统一导入管线。先预览导入计划：

```bash
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --dry-run
```

如果希望同时用 INSPIRE 补齐缺失的 BibTeX 字段：

```bash
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --enrich-inspire --dry-run
```

确认无误后写入：

```bash
python scripts/rag/import_pipeline.py --bib path/to/export.bib --rag-dir RAG --yes
```

导入 Zotero RDF+PDF ZIP：

```bash
python scripts/rag/import_pipeline.py --zip path/to/zotero-export.zip --rag-dir RAG --dry-run
python scripts/rag/import_pipeline.py --zip path/to/zotero-export.zip --rag-dir RAG --yes
```

按描述搜索并导入 INSPIRE 记录：

```bash
python scripts/rag/import_pipeline.py --query "paper description" --rag-dir RAG --dry-run
```

也可以使用低层命令进行调试或精细控制：

```bash
python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG --dry-run
python scripts/rag/import_bib.py --bib path/to/export.bib --rag-dir RAG
python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG --dry-run
python scripts/rag/zip_importer.py --zip path/to/zotero-export.zip --rag-dir RAG
```

INSPIRE 搜索并选择添加：

```bash
python scripts/rag/search_add.py search --query "paper description" --limit 5
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --dry-run
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:2603.24450" --select 1 --yes
```

### 2. 同步或下载 PDF

如果 PDF 已经在本地，按 citation key、DOI slug 或 title slug 进行匹配和复制：

```bash
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs --dry-run
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs
```

从 arXiv 或 URL 下载单个 PDF：

```bash
python scripts/rag/pdf_downloader.py --arxiv 2603.24450 --out RAG/reference/pdfs/citationKey.pdf --dry-run
python scripts/rag/pdf_downloader.py --arxiv 2603.24450 --out RAG/reference/pdfs/citationKey.pdf
python scripts/rag/pdf_downloader.py --url https://example.org/paper.pdf --out RAG/reference/pdfs/citationKey.pdf --dry-run
```

### 3. 生成 source page 和 evidence

如果只需要从 `references.bib` 生成 metadata-only source page：

```bash
python scripts/rag/build_source_pages.py --rag-dir RAG
```

如果需要 evidence-backed ingest，先 dry-run，再执行：

```bash
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey
```

批量处理全部可解析条目：

```bash
python scripts/rag/evidence_ingest.py --rag-dir RAG --all
```

如果存在 arXiv route 但 arxiv2md 解析失败，默认会停止。只有明确接受降级到 PDF route 时才使用：

```bash
python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey --fallback-pdf-on-arxiv-fail
```

Evidence ingest 会执行：

```text
BibTeX → resolve → parse (arxiv2md/pymupdf4llm/pandoc) → chunk (LlamaIndex) → validate → update source page → searchable
```

主要产物：

- `RAG/reference/parsed/` — parsed Markdown 和 parsed manifest。
- `RAG/reference/chunks/` — evidence chunk JSONL。
- `RAG/reference/arxiv_sources/` — arXiv HTML/Markdown cache。
- `RAG/summary/sources/` — source page 的 evidence 字段和 claim 索引。

验证 evidence 和 source page：

```bash
python scripts/rag/validate_evidence.py --rag-dir RAG
python scripts/rag/validate_source_pages.py --rag-dir RAG
```

### 4. 生成摘要、词表和 edges

优先使用 chunk-backed 摘要，因为它会引用 `chunk_id`：

```bash
python scripts/rag/summarize_evidence.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/summarize_evidence.py --rag-dir RAG --key citationKey --yes
```

旧式 PDF 文本 fallback：

```bash
python scripts/rag/summarize_sources.py --rag-dir RAG
```

基于 evidence 和 metadata 推荐词表，再审核应用：

```bash
python scripts/rag/suggest_vocabulary.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --online --dry-run --json
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --online --accept local:reviewed-term --accept physh:reviewed-id --yes
python scripts/rag/apply_edges.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/apply_edges.py --rag-dir RAG --key citationKey --yes
python scripts/rag/build_vocabulary_wiki.py --rag-dir RAG --dry-run
python scripts/rag/build_vocabulary_wiki.py --rag-dir RAG --yes
python scripts/rag/update_index.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG
```

词表规则：

- `RAG/vocabulary.md` 是所有 `canonical_id` 的权威来源。
- `physh:*` 表示 APS PhySH controlled vocabulary。
- `local:*` 表示项目本地术语。
- `alias:*` 只能作为 alias，不应作为最终 `canonical_id` 写入 edges。
- 不要在脚本中 hardcode physics terms。

### 5. 查询知识库并追踪证据

为 AI 回答或研究综合构建结构化上下文包：

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "superconducting resonators TLS noise" --top-k 8 --json
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --json
```

按 citation key、DOI、arXiv、标题片段或 source page 内容做结构化本地查询：

```bash
python scripts/rag/query.py --rag-dir RAG --query "citationKey or DOI or title" --json
```

直接搜索 evidence chunks：

```bash
python scripts/rag/search_evidence.py --rag-dir RAG "superconducting resonators TLS noise"
```

追踪某个 evidence chunk 的 provenance：

```bash
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "doc::section::chunk-001-abcdef1234"
```

命令选择：

- `context_pack.py`：准备 AI 回答、跨文献比较或综合时优先使用。
- `query.py`：当 evidence chunks 稀疏时，用于检索 metadata 和 source page。
- `search_evidence.py`：查看原始 chunk 级检索结果。
- `trace_claim.py`：查看 chunk 原文、source page、parsed Markdown、manifest、route、section 和 equation provenance。

### 6. 维护、刷新或删除条目

检查 evidence 是否因为 PDF SHA、parser version 或源文件变化而陈旧：

```bash
python scripts/rag/check_staleness.py --rag-dir RAG
python scripts/rag/check_staleness.py --rag-dir RAG --key citationKey
```

更新 source page frontmatter 字段：

```bash
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set source.year=2025 --dry-run
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set source.year=2025 --yes
```

重新 ingest，并可替换 PDF：

```bash
python scripts/rag/maintain.py re-ingest --rag-dir RAG --key citationKey --dry-run
python scripts/rag/maintain.py re-ingest --rag-dir RAG --key citationKey --replace-pdf path/to/paper.pdf --yes
```

只移除 evidence artifacts，并清理 source page 中的 evidence 字段：

```bash
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --yes
```

完整删除 BibTeX entry、source page、PDF、parsed Markdown、chunk JSONL、arXiv cache 和 Markdown 引用：

```bash
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --yes
python scripts/rag/delete_entry.py --rag-dir RAG --doi 10.xxxx/yyyy --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --arxiv 2603.24450 --dry-run
```

删除或维护后运行：

```bash
python scripts/rag/update_index.py --rag-dir RAG
python scripts/rag/rag_lint.py --rag-dir RAG
```

### 7. 导出 BibTeX 和阅读清单

先搜索本地 RAG 和可选 INSPIRE candidates：

```bash
python scripts/rag/export.py search --rag-dir RAG --query "paper description" --limit 5
```

导出某条记录的 BibTeX。HEP 写作建议优先使用 INSPIRE canonical BibTeX：

```bash
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --provider inspire
python scripts/rag/export.py get-bibtex --rag-dir RAG --query "arxiv:2603.24450" --provider inspire
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --provider inspire --json
```

如果不允许回退到本地 BibTeX，使用 strict provider：

```bash
python scripts/rag/export.py get-bibtex --rag-dir RAG --key citationKey --strict-provider inspire
```

导出一组 BibTeX 或 Markdown 阅读清单：

```bash
python scripts/rag/export.py export-bibtex --rag-dir RAG --query "dark matter" --provider inspire --out refs.bib
python scripts/rag/export.py export-bibtex --rag-dir RAG --tag research_areas=local:coherent-elastic-neutrino-nucleus-scattering --provider inspire --out refs.bib
python scripts/rag/export.py export-reading-list --rag-dir RAG --query "dark matter" --out reading-list.md
```

## 命令选择速查

| 你想做什么 | 推荐命令 |
|---|---|
| 创建新的 RAG 骨架 | `python scripts/rag/rag_init.py --rag-dir RAG ...` |
| 统一导入 BibTeX、Zotero ZIP 或搜索结果 | `python scripts/rag/import_pipeline.py ... --dry-run` |
| 调试 BibTeX 导入 | `python scripts/rag/import_bib.py --bib file.bib --rag-dir RAG --dry-run` |
| 导入 Zotero RDF+PDF ZIP | `python scripts/rag/zip_importer.py --zip export.zip --rag-dir RAG --dry-run` |
| 从 INSPIRE 搜索并添加 | `python scripts/rag/search_add.py search ...` / `add ... --dry-run` |
| 同步本地 PDF | `python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir path/to/pdfs --dry-run` |
| 下载 arXiv 或 URL PDF | `python scripts/rag/pdf_downloader.py --arxiv ... --out ... --dry-run` |
| 生成 metadata-only source pages | `python scripts/rag/build_source_pages.py --rag-dir RAG` |
| 生成 evidence-backed chunks | `python scripts/rag/evidence_ingest.py --rag-dir RAG --key citationKey` |
| 生成 chunk-backed 摘要 | `python scripts/rag/summarize_evidence.py --rag-dir RAG --key citationKey --dry-run` |
| 为 AI 回答打包上下文 | `python scripts/rag/context_pack.py --rag-dir RAG --query "..." --json` |
| 搜索 evidence chunks | `python scripts/rag/search_evidence.py --rag-dir RAG "..."` |
| 追踪 chunk provenance | `python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "..."` |
| 推荐和应用词表 | `suggest_vocabulary.py`, `apply_vocabulary.py`, `apply_edges.py` |
| 重建导航和 AUTO blocks | `python scripts/rag/update_index.py --rag-dir RAG` |
| 检查知识库一致性 | `python scripts/rag/rag_lint.py --rag-dir RAG` |
| 检查 stale evidence | `python scripts/rag/check_staleness.py --rag-dir RAG` |
| 只移除 evidence | `python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --dry-run` |
| 完整删除条目 | `python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --dry-run` |
| 导出 BibTeX 或阅读清单 | `python scripts/rag/export.py ...` |

## Evidence routes

- `arxiv_source` — 有 arXiv ID 的论文。优先用 arxiv2md HTML-to-Markdown，必要时用 pandoc fallback，并把缓存写入 `RAG/reference/arxiv_sources/`。
- `pdf_pymupdf` — PDF-only 论文。使用 `pymupdf4llm` 解析 PDF。
- `pdf_mineru` — 仅作为旧 manifest 或旧 CLI 的兼容 alias 接受。

如果本地已经有 PDF，`evidence_ingest.py` 会优先使用本地 PDF，而不是重新下载 arXiv PDF。

## 校验和测试

运行完整 lint：

```bash
python scripts/rag/rag_lint.py --rag-dir RAG
```

严格模式会把 metadata-only source page 也视为失败：

```bash
python scripts/rag/rag_lint.py --rag-dir RAG --strict
```

单独校验 evidence、词表或 source pages：

```bash
python scripts/rag/validate_evidence.py --rag-dir RAG
python scripts/rag/validate_vocabulary.py --rag-dir RAG --online-physh
python scripts/rag/validate_source_pages.py --rag-dir RAG
```

运行测试套件：

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/ -v
```

测试覆盖导入、evidence resolution/parsing/chunking、validators、vocabulary review、wiki generation、search、trace、maintenance、export、source-page building、plugin smoke tests 和 workflow integration。

## Windows 编码提示

如果 Windows terminal 出现编码噪声，建议通过 Anaconda Python 并启用 UTF-8：

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONIOENCODING = "utf-8"
& "C:\ProgramData\anaconda3\python.exe" -X utf8 scripts\rag\rag_lint.py --rag-dir RAG
```

## Claude Code skill 入口

本项目附带 Claude Code skills，可让 Claude 按固定协议操作本地 RAG：

- `/rag` — 日常操作：ingest、query、lint、update-index、sync-from-notes、get-bibtex。
- `/rag-evidence` — 生成、搜索、验证、追踪、移除 evidence。
- `/rag-import` — 导入 BibTeX、Zotero ZIP、search-and-add。
- `/rag-maintain` — remove、update-source、re-ingest、sync-pdf。
- `/rag-init` — 初始化项目级 RAG 知识库。

Claude 回答可能由知识库文献支持的问题时，应先搜索 evidence：

```bash
python scripts/rag/search_evidence.py --rag-dir RAG "query terms"
```

使用 evidence 时应引用 `chunk_id` 和 source page，并可用：

```bash
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id <id>
```

## Operation status

| Operation | Status | CLI | Notes |
|---|---|---|---|
| rag-init | Implemented | `rag_init.py` | Generates template, vocabulary, dimensions, evidence dirs |
| import pipeline | Implemented | `import_pipeline.py` | Unified BibTeX, Zotero ZIP, and INSPIRE/search plan/apply flow |
| BibTeX update | Implemented | `bib_update.py` | Safe INSPIRE-backed missing-field update plan and apply |
| import-bib | Implemented | `import_bib.py` | Parse + normalize + dedup + append |
| import-zip | Implemented | `zip_importer.py` | Zotero RDF + PDF attachments |
| sync-pdf | Implemented | `sync_pdf.py` | Local PDF matching |
| build source pages | Implemented | `build_source_pages.py` | Metadata-only source-page skeletons |
| evidence ingest | Implemented | `evidence_ingest.py` | Resolve → parse → chunk → source-page evidence links |
| resolve source | Implemented | `resolve_source.py` | Chooses `arxiv_source` or `pdf_pymupdf` |
| parse evidence | Implemented | `parsers.py` | arxiv2md/pandoc/pymupdf4llm + arxiv2md cache |
| chunk evidence | Implemented | `chunker.py` | Deterministic chunk JSONL |
| summarize evidence | Implemented | `summarize_evidence.py` | Chunk-backed source summary drafts |
| suggest vocabulary | Implemented | `suggest_vocabulary.py` | Evidence-driven term/edge suggestions |
| apply vocabulary | Implemented | `apply_vocabulary.py` | Plan/apply vocabulary.md term additions |
| apply edges | Implemented | `apply_edges.py` | Plan/apply source-page edge updates |
| context pack | Implemented | `context_pack.py` | Structured source/chunk/BibTeX context for AI answers |
| search evidence | Implemented | `search_evidence.py` | TF-IDF over evidence chunks |
| embedding router | Implemented | `embedding_router.py` | Optional embedding backend with hash fallback |
| qdrant store | Implemented | `qdrant_store.py` | Dry-run/upsert scaffold for evidence chunks |
| hybrid query | Implemented | `query_hybrid.py` | Graph-aware scaffold with TF-IDF fallback |
| trace claim | Implemented | `trace_claim.py` | Chunk provenance and raw text |
| summarize topic | Implemented | `summarize_topic.py` | Deterministic chunk-grounded topic summary drafts |
| merge RAG update | Implemented | `merge_rag_update.py` | Duplicate key/doc-id/vocabulary review report |
| lint | Implemented | `rag_lint.py` | Comprehensive validation, with `--strict` |
| validate evidence | Implemented | `validate_evidence.py` | Parsed/chunk manifest validation |
| validate vocabulary | Implemented | `validate_vocabulary.py` | Vocabulary schema, alias checks, optional live PhySH concept validation |
| validate source pages | Implemented | `validate_source_pages.py` | Source schema, edges, claims, evidence links |
| update-index | Implemented | `update_index.py` | AUTO block regeneration |
| maintain | Implemented | `maintain.py` | Source-page update/remove/re-ingest patterns |
| remove evidence | Implemented | `remove_evidence.py` | Removes evidence artifacts and scrubs source evidence fields |
| check staleness | Implemented | `check_staleness.py` | SHA/parser staleness detection |
| graph index | Implemented | `graph_index.py` | Source-page edge graph index |
| vocabulary wiki | Implemented | `build_vocabulary_wiki.py` | Wiki pages for confirmed `physh:*` and `local:*` vocabulary nodes |
| export | Implemented | `export.py` | Search, INSPIRE-first BibTeX export with local fallback, reading lists |
| delete entry | Implemented | `delete_entry.py` | Unified dry-run deletion for Bib/source/PDF/evidence artifacts |

`ingest.py` is legacy. Current workflows use `build_source_pages.py` for metadata stubs and `evidence_ingest.py` for evidence-backed ingest.
