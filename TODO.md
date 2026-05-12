# TODO - DARW RAG 工作流完善路线图

## 0. 当前判断

本项目已经具备 DARW evidence-first RAG 的核心底层能力：文献导入、去重、PDF 同步/下载、arXiv/PDF 解析、chunk 切分、证据检索、chunk 追溯、source page 验证、BibTeX 导出和基础 skill 文档。

但当前还没有完全满足目标中的“一站式工作流”。主要差距不是缺少单个脚本，而是缺少统一编排层：

- 导入应从 BibTeX、Zotero ZIP 或 AI/INSPIRE 搜索开始，自动去重、补 arXiv、维护 Bib、同步 PDF、生成 parsed Markdown、切 chunks、生成/更新词汇表和 wiki 关系。
- 删除应能按 key/DOI/arXiv/title 定位文章，一次删除 Bib、source page、PDF、parsed Markdown、manifest、chunks、wiki 索引和其他 Markdown 引用。
- 查询应同时使用 source/wiki 上下文和 chunks RAG 上下文，并能定位到具体文章、chunk_id 和 BibTeX 条目。
- 导出应优先用 INSPIRE 返回规范 BibTeX，找不到时自动 fallback 到本地 `references.bib`。

当前数据层也还处于早期状态：`RAG/summary/sources/` 有 7 个 source pages，`RAG/reference/pdfs/` 有 7 个 PDF，但只有 1 篇生成了 parsed/chunk evidence，`RAG/vocabulary.md` 仍为 `terms: []`。

## 1. 面向目标工作流的模块评分

评分含义：

- 5 = 已满足目标，可作为稳定工作流使用。
- 4 = 核心能力完整，但仍有边界或编排问题。
- 3 = 单步可用，但不能稳定完成目标流程。
- 2 = 原型或辅助能力，需要明显补齐。
- 1 = 基本未实现。

### 1.1 导入工作流评分

| 需求环节 | 当前实现 | 评分 | 主要缺口 |
|---|---|---:|---|
| BibTeX 导入 | `import_bib.py`, `bib_parser.py`, `dedup.py` | 3.5 | 自写 BibTeX parser 边界有限；输入 Bib 内部重复和 key 冲突处理不足 |
| Zotero ZIP 导入 | `zip_importer.py`, `rdf_parser.py` | 3.5 | citation key 生成过简；未完整保留 Zotero citation key；导入后不自动 evidence 化 |
| AI/INSPIRE 搜索添加 | `search_add.py`, `external_search.py` | 4 | 支持搜索、dry-run、yes、PDF 下载；但不是统一导入 pipeline |
| 自动查询并去重 | `dedup.py`, `metadata_normalizer.py` | 3.5 | 去重结果未统一形成导入计划；重复条目 PDF/metadata merge 策略不足 |
| 尽力补 arXiv number | `resolve_source.py --enrich-inspire` | 2.5 | 未在导入/evidence pipeline 默认使用；查询结果不回写 BibTeX |
| 移动或下载 PDF | `sync_pdf.py`, `pdf_downloader.py`, `search_add.py` | 3.5 | Bib/ZIP 导入后没有统一自动下载缺失 arXiv PDF |
| Bib 维护 | `import_bib.py`, `search_add.py` | 3 | 可追加，但缺少 enrichment 后的 Bib 回写和字段 merge |
| arXiv/PDF 解析 | `parsers.py` | 4 | 后端依赖外部库/网络；失败恢复和记录可加强 |
| chunk 切分 | `chunker.py` | 4 | 稳定 chunk_id 已有；page/equation/section 元数据仍可增强 |
| evidence 编排 | `evidence_ingest.py` | 4 | 单条/全部可跑；导入脚本没有自动调用完整流程 |
| APS PhySH 词汇表 | `physh_mapper.py`, `suggest_vocabulary.py` | 2.5 | 只能建议/规范化；不能审查后自动写 vocabulary 和 source edges |
| wiki 关系建立 | `update_index.py`, `graph_index.py` | 2.5 | 依赖 edges；当前 vocabulary/edges 为空，实际关系图不可用 |
| dry-run 和日志 | 多数脚本已具备 | 3.5 | `build_source_pages.py`, `update_index.py` 等还缺统一 dry-run/yes 语义 |

### 1.2 删除工作流评分

| 需求环节 | 当前实现 | 评分 | 主要缺口 |
|---|---|---:|---|
| 指定文章定位 | 多数命令按 citation key | 2.5 | 缺少按 title/DOI/arXiv 模糊定位并确认的统一入口 |
| 删除 evidence 文件 | `remove_evidence.py` | 4 | 已删除 parsed/chunk/PDF 并支持 dry-run |
| 删除 Bib/source page/PDF | `maintain.py remove` | 3.5 | 和 `remove_evidence.py` 分散，需要人工组合 |
| 删除所有生成产物 | 无统一命令 | 2.5 | 需要一次性计划和事务式执行 |
| 清理其他 Markdown 引用 | `_find_references` 仅报告部分引用 | 2 | 需要自动 scrub 或生成人工确认 diff |
| dry-run/确认/日志 | 分散实现 | 3.5 | 需要统一删除日志和回滚/审计信息 |

### 1.3 查询工作流评分

| 需求环节 | 当前实现 | 评分 | 主要缺口 |
|---|---|---:|---|
| chunk RAG 查询 | `search_evidence.py` | 3.5 | 当前为 TF-IDF，不是向量或混合检索 |
| 来源追溯 | `trace_claim.py` | 4 | 能追到 chunk/source/parsed/PDF 路径 |
| wiki/source 上下文 | source pages, index, graph | 2.5 | 正文和 edges 仍为空，wiki 上下文薄弱 |
| wiki + chunks 组合上下文 | skill 文档要求 AI 手动组合 | 2 | 缺少统一 `context_pack.py` |
| 向量搜索 | 未实现 | 1.5 | Qdrant/embedding 仍是后续任务 |
| Bib 条目定位 | `references.bib` + citation_key | 3 | 查询结果中未自动返回 Bib block 或 Bib provenance |

### 1.4 导出工作流评分

| 需求环节 | 当前实现 | 评分 | 主要缺口 |
|---|---|---:|---|
| 本地候选检索 | `export.py search` | 4 | 可按 query/key/tag 找本地候选 |
| INSPIRE BibTeX | `export.py get-bibtex --provider inspire` | 4 | 已实现 |
| 本地 fallback | `--fallback-local` | 3.5 | 需要成为默认可解释降级策略 |
| reading list 导出 | `export.py export-reading-list` | 4 | 已实现 |

## 2. P0 - 统一导入编排器

### P0.1 新增 `scripts/rag/import_pipeline.py`

目标：把 BibTeX、Zotero ZIP、AI/INSPIRE 搜索添加整合成一个无副作用可预览、确认后执行的导入流水线。

建议 CLI：

```bash
python scripts/rag/import_pipeline.py --rag-dir RAG --bib path/to/refs.bib --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --zip path/to/zotero.zip --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --query "paper description" --limit 5 --dry-run
python scripts/rag/import_pipeline.py --rag-dir RAG --bib path/to/refs.bib --yes
```

要求：

- 输入支持 `--bib`, `--zip`, `--query`, `--record-id`, `--pdf-dir`。
- 先生成 ImportPlan，不直接写文件。
- plan 必须列出：
  - 候选论文 title/key/DOI/arXiv/year。
  - 是否重复，以及重复匹配依据：DOI、arXiv、normalized title、author-year。
  - BibTeX 将新增、跳过或 merge 的条目。
  - PDF 来源：BibTeX file 字段、ZIP attachment、local pdf-dir、arXiv download、missing。
  - evidence route：`arxiv_source` 或 `pdf_pymupdf`。
  - 将写入的 parsed Markdown、manifest、chunk JSONL、source page、vocabulary、edge index。
- 默认 dry-run；写入必须 `--yes`。
- 成功执行后必须写 `RAG/log.md`。
- 对每篇新文章自动调用或等价执行：
  - import/dedup。
  - INSPIRE/arXiv enrichment。
  - PDF sync/download。
  - BibTeX manifest update。
  - evidence ingest。
  - evidence validate。
  - vocabulary/edge suggestion。
  - update index。
  - lint。

验收：

- BibTeX 导入 3 篇，其中 1 篇重复时，dry-run 能清楚报告 2 new / 1 duplicate，且不写任何文件。
- 对只有 DOI 的条目，如果 INSPIRE 找到 arXiv ID，plan 显示将回写 BibTeX `eprint`。
- 对有 arXiv ID 但无 PDF 的条目，plan 显示将下载 `RAG/reference/pdfs/{key}.pdf`。
- `--yes` 后生成 source page、parsed manifest、chunk JSONL，并更新 log。

### P0.2 增强 enrichment 和 Bib 回写

相关文件：

- `scripts/rag/resolve_source.py`
- `scripts/rag/search_add.py`
- `scripts/rag/import_bib.py`
- 新增或复用 `scripts/rag/bib_update.py`

要求：

- 将 `resolve_entry(..., enrich_inspire=True)` 纳入导入 pipeline。
- 如果发现 arXiv ID、INSPIRE ID、canonical DOI，能回写到 `references.bib`。
- 回写前必须保留原字段并输出 diff/plan。
- 对冲突情况标记 `needs_review`，不得静默覆盖。

验收：

- DOI-only 条目可通过 INSPIRE 补 `eprint`。
- 多候选时不自动选择，要求用户确认。
- 回写 BibTeX 后 parser 能重新读出一致字段。

### P0.3 强化导入去重

相关文件：

- `scripts/rag/dedup.py`
- `scripts/rag/import_bib.py`
- `scripts/rag/zip_importer.py`

要求：

- 对输入文件内部也做去重。
- 检测 citation key 冲突：同 key 但不同 DOI/arXiv/title 必须报错或生成新 key。
- Zotero ZIP 优先使用 RDF 中的 citation key；没有时再生成。
- 重复条目可 merge PDF/file/arXiv/DOI metadata，而不是简单跳过所有信息。

验收：

- 同一个 BibTeX 文件内重复 DOI 只导入一次。
- 同 key 不同论文不会覆盖。
- 重复文献但 ZIP 中有 PDF 时，PDF 能复制到已有 key 对应路径。

## 3. P1 - 词汇表、edges 和 wiki 关系闭环

### P1.1 新增 `scripts/rag/apply_vocabulary.py`

目标：把 `suggest_vocabulary.py` 的候选结果变成可审查、可写入的 `vocabulary.md` 更新。

建议 CLI：

```bash
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/apply_vocabulary.py --rag-dir RAG --key citationKey --yes
```

要求：

- 从 evidence chunks 和 source metadata 抽取候选词。
- 调用 `physh_mapper.py` / `edge_normalizer.py`。
- 输出 VocabularyPlan：
  - new terms。
  - existing matched terms。
  - unresolved local terms。
  - needs_review terms。
- dry-run 输出将写入的 YAML diff。
- `--yes` 后写入 `RAG/vocabulary.md`。
- 不自动合并冲突词。

验收：

- 空 `terms: []` 可以安全追加本地或 PhySH term。
- 重复运行不会重复追加相同 canonical_id。
- alias 不会作为 final canonical_id 写入 edges。

### P1.2 新增 `scripts/rag/apply_edges.py`

目标：把规范化后的 canonical_id 写回对应 source page 的 `edges` 字段。

要求：

- 输入可来自 `suggest_vocabulary.py` / `apply_vocabulary.py` 的候选结果。
- 每条 edge 包含：
  - `canonical_id`
  - `label`
  - `confidence`
  - `evidence`
  - `needs_review`
- 写入前验证 canonical_id 已存在于 `vocabulary.md`。
- 支持 dry-run 和 yes。
- 保留人工已有 edges，不覆盖。

验收：

- 对一篇已 chunk 的文章，可以从 chunks 生成 vocabulary terms，再写入 source page edges。
- `rag_lint.py --strict` 不再因该文章 empty edges 失败。
- `update_index.py` 能基于 edges 创建 wiki 分类页。

### P1.3 修正 lint/validator 细节

相关文件：

- `scripts/rag/rag_lint.py`
- `scripts/rag/validate_source_pages.py`
- `scripts/rag/common.py`

要求：

- 将 `_resolve_rag_path` 统一移动到 `common.py`。
- `rag_lint.py` 的 category 合法性应基于 `darw_schema.EDGE_CATEGORIES`，不应基于当前 vocabulary 里出现过哪些 category。
- `validate_source_pages.py` 非 strict 模式下 warning 不应导致 CLI exit 1，或者明确区分 warnings/errors。

验收：

- 词表只含 `techniques` 时，标准空 category 不会被误报 unknown。
- 非 strict validator 可报告 warning 但返回 0。
- strict 模式空 edges 返回 1。

## 4. P2 - 统一删除编排器

### P2.1 新增 `scripts/rag/delete_entry.py`

目标：实现用户指定某篇文章后，一次性定位并删除该文章所有相关产物。

建议 CLI：

```bash
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --doi 10.xxxx/yyyy --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --arxiv 2603.24450 --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --title "paper title" --dry-run
python scripts/rag/delete_entry.py --rag-dir RAG --key citationKey --yes
```

要求：

- 支持按 key、DOI、arXiv、title 定位。
- 模糊 title 命中多篇时必须要求确认。
- dry-run 输出 DeletePlan：
  - BibTeX entry。
  - source page。
  - PDF。
  - parsed Markdown。
  - parsed manifest。
  - chunk JSONL。
  - arXiv cache。
  - graph/index pages affected。
  - other Markdown references。
- `--yes` 后执行：
  - 删除 BibTeX entry。
  - 删除 source page。
  - 删除 PDF。
  - 删除 parsed/chunk evidence。
  - 删除或重建 wiki auto index。
  - 删除其他 Markdown 中的明确引用，或输出需要人工确认的引用。
  - 写 log。

验收：

- 删除已 evidence 化文章后，不存在 orphan parsed/chunk/PDF。
- `references.bib` 中不再有该 key。
- `RAG/summary/sources/{key}.md` 不存在。
- `rag_lint.py --rag-dir RAG` 不因残留引用失败。
- dry-run 前后文件内容完全一致。

### P2.2 增强 Markdown 引用清理

相关文件：

- `scripts/rag/maintain.py`
- 新增 `scripts/rag/reference_scrubber.py`

要求：

- 扫描所有 `RAG/**/*.md`。
- 识别：
  - `[[../sources/key]]`
  - `(summary/sources/key.md)`
  - `[@citationKey]`
  - chunk_id。
  - source page path。
- 对 AUTO block 内引用可自动删除。
- 对人工 prose 中引用默认只报告，除非 `--apply-manual`。

验收：

- 删除 source 后，自动索引页不再引用该 source。
- synthesis 手写段落中的引用不会静默删除，而是进入 review list。

## 5. P3 - 查询上下文打包

### P3.1 新增 `scripts/rag/context_pack.py`

目标：把用户问题转成 AI 可直接使用的上下文包，同时包含 wiki/source 上下文和 chunks RAG 上下文。

建议 CLI：

```bash
python scripts/rag/context_pack.py --rag-dir RAG --query "question" --top-k 8 --json
python scripts/rag/context_pack.py --rag-dir RAG --key citationKey --json
```

要求：

- 调用 `search_evidence.py` 或内部 API 获取 top chunks。
- 读取相关 source pages。
- 读取相关 edge/wiki pages。
- 读取 BibTeX entry。
- 输出结构化 JSON：
  - `query`
  - `wiki_context`
  - `source_pages`
  - `evidence_chunks`
  - `bib_entries`
  - `graph_edges`
  - `gaps`
  - `provenance`
- 每个 evidence chunk 必须包含：
  - chunk_id
  - citation_key
  - doc_id
  - source_page
  - parsed_markdown
  - section_anchor
  - score
  - text snippet。
- 如果没有 chunks，但有 source page，应明确标记 `metadata_only`。

验收：

- 对已 evidence 化文章的问题，返回 chunk + source page + BibTeX。
- 对未 evidence 化文章的问题，返回 source page/BibTeX 并报告缺少 chunks。
- AI 回答可以只依赖 context pack，不需要手动散查文件。

### P3.2 增强 `query.py` 或新增 `query_structured.py`

要求：

- 支持按 citation key、doc_id、title、DOI、arXiv、edge、tag 搜索。
- 支持 `--json`。
- 输出 matched_fields、score、source_page、bib_key。
- 作为无 Qdrant 时的 fallback。

验收：

- 给定 title keyword 能找到 source page。
- 给定 citation key 能精确命中。
- 输出可被 `context_pack.py` 调用。

## 6. P4 - 导出 BibTeX 完善

### P4.1 增强 `scripts/rag/export.py`

要求：

- `get-bibtex` 默认优先 INSPIRE。
- INSPIRE 找不到时，默认 fallback 到本地，并在输出中标注来源。
- 支持 `--strict-provider`：严格模式下 INSPIRE 找不到则失败。
- 输出可选 JSON metadata：
  - provider_used
  - fallback_used
  - citation_key
  - doi
  - arxiv
  - source_page。

验收：

- INSPIRE 有结果时返回 INSPIRE BibTeX。
- INSPIRE 无结果但本地有条目时返回本地 BibTeX，并提示 fallback。
- `--strict-provider inspire` 时无结果返回非 0。

## 7. P5 - 向量库和混合检索

这部分低于 P0-P4。只有当导入、删除、context pack 和 vocabulary/edges 闭环稳定后再做。

### P5.1 新增 `scripts/rag/embedding_router.py`

要求：

- 优先 `Alibaba-NLP/gte-Qwen2-1.5B-instruct`。
- fallback `BAAI/bge-m3`。
- 缺少 ML stack 时不影响普通脚本。
- 提供 `get_embedding(text)` 和 `get_embeddings(texts)`。
- 记录模型、维度、设备、耗时。

### P5.2 新增 `scripts/rag/qdrant_store.py`

要求：

- collection: `darw_evidence_chunks`。
- upsert `darw-chunk-v1` JSONL。
- 支持 doc_id、citation_key、edges filter。
- 支持 chunk_id 精确读取。
- 支持 doc_id 删除。
- 支持 dry-run。

### P5.3 新增 `scripts/rag/query_hybrid.py`

流程：

1. 解析问题中的实体和约束。
2. 用 `physh_mapper.py` / `edge_normalizer.py` 规范化。
3. 用 graph/wiki edges 过滤候选 doc。
4. 用 Qdrant 或 fallback 检索 chunks。
5. 输出 answer candidates、evidence、gaps。

要求：

- 必须输出 chunk_id。
- 必须报告 graph filter 命中的 edges。
- 证据不足时输出 gaps，不强答。

## 8. P6 - synthesis 和协作维护

### P6.1 新增 `scripts/rag/summarize_topic.py`

要求：

- 基于 source pages + evidence chunks。
- 输出 consensus、disagreement、open problems、key references。
- 每条结论必须有 source path 或 chunk_id。
- 支持 dry-run。
- 可写入 `RAG/summary/synthesis/`。

### P6.2 增强 `sync_from_notes.py`

要求：

- 支持增量更新，重复运行不重复追加。
- 按 claims、methods、failures、decisions 分类。
- 记录 note path、heading、line 或 anchor。
- 增加单元测试。

### P6.3 新增 `scripts/rag/merge_rag_update.py`

要求：

- 合并协作者 source pages。
- 检测 vocabulary 冲突。
- 检测 duplicate citation keys。
- 检测同一 doc_id 不同 summaries。
- 输出人工审查清单。

## 9. Skill 文档更新任务

相关文件：

- `.claude/skills/rag-import/SKILL.md`
- `.claude/skills/rag-evidence/SKILL.md`
- `.claude/skills/rag-maintain/SKILL.md`
- `.claude/skills/rag/SKILL.md`

要求：

- `rag-import` 优先调用 `import_pipeline.py`，而不是手动串多个命令。
- `rag-maintain` 删除操作优先调用 `delete_entry.py`。
- `rag` 查询操作优先调用 `context_pack.py`。
- `rag` 导出操作说明 INSPIRE-first + local fallback。
- 所有写操作必须 dry-run first，除非用户明确要求直接执行。

验收：

- 用户说“导入这篇文章”时，skill 指向统一导入 pipeline。
- 用户说“删除这篇文章”时，skill 指向统一删除 pipeline。
- 用户问研究问题时，skill 先生成 context pack，再回答。

## 10. 测试任务清单

### P0/P1 导入和词汇

- `test_import_pipeline_bib_dry_run.py`
- `test_import_pipeline_zip_dry_run.py`
- `test_import_pipeline_search_add.py`
- `test_import_pipeline_enrich_arxiv.py`
- `test_import_pipeline_no_side_effects.py`
- `test_bib_update_merge.py`
- `test_apply_vocabulary.py`
- `test_apply_edges.py`

### P2 删除

- `test_delete_entry_by_key.py`
- `test_delete_entry_by_doi.py`
- `test_delete_entry_by_arxiv.py`
- `test_delete_entry_title_ambiguous.py`
- `test_delete_entry_scrubs_auto_indexes.py`
- `test_delete_entry_dry_run_no_side_effects.py`
- `test_reference_scrubber.py`

### P3 查询上下文

- `test_context_pack_with_chunks.py`
- `test_context_pack_metadata_only.py`
- `test_context_pack_bib_entry.py`
- `test_query_structured_output.py`

### P4 导出

- `test_export_inspire_first.py`
- `test_export_local_fallback.py`
- `test_export_strict_provider.py`

### P5/P6 后续

- `test_embedding_router_fallback.py`
- `test_qdrant_store.py`
- `test_query_hybrid.py`
- `test_summarize_topic.py`
- `test_sync_from_notes_incremental.py`
- `test_merge_rag_update.py`

## 11. 下一版 Definition of Done

DARW RAG 下一版视为完成，当且仅当：

- `import_pipeline.py` 能从 BibTeX、ZIP、INSPIRE/search 三种入口完成 dry-run 计划和 `--yes` 执行。
- 导入时能自动去重、尽力补 arXiv、同步/下载 PDF、维护 BibTeX。
- 导入后能生成 parsed Markdown、manifest、chunk JSONL，并更新 source page。
- 能从 chunks 生成候选 vocabulary，写入 `vocabulary.md`，并把 canonical edges 写回 source page。
- `update_index.py` 能基于 edges 建立 wiki 关系页。
- `delete_entry.py` 能一次删除指定文献的 Bib/source/PDF/parsed/chunk/index 引用。
- 删除 dry-run 前后文件完全一致。
- `context_pack.py` 能同时返回 wiki/source 上下文、chunks RAG 上下文和 BibTeX provenance。
- 查询回答需要具体来源时，能定位到 citation key、source page、chunk_id 和 BibTeX entry。
- `export.py` 能 INSPIRE-first，找不到时自动 local fallback 并标注来源。
- 所有写操作都有 dry-run 和真正执行模式，并写入 `RAG/log.md`。
