# DARW 证据优先 RAG —— 实现状态与设计文档

## 0. 当前状态摘要

**版本**：Phase 2-6, 8-9 完成（Phase 7/10/11 推迟）
**测试**：112 项全部通过
**脚本**：scripts/rag/ 下 37 个 Python 模块
**技能**：5 个 Claude Code 技能（rag, rag-evidence, rag-import, rag-init, rag-maintain）

---

# 第一部分：用户工作流程

## 1. 初次使用：初始化知识库

```bash
python scripts/rag/rag_init.py --rag-dir RAG
```

**生成的文件**：

| 文件 | 用途 |
|---|---|
| `RAG/references.bib` | BibTeX 文献清单（空） |
| `RAG/template.md` | 源页面模板（darw-source-v1） |
| `RAG/vocabulary.md` | 受控术语表（初始 terms: []） |
| `RAG/SKILL.md` | 目录结构说明 |
| `RAG/index.md` | 导航索引（含 AUTO 块） |
| `RAG/log.md` | 操作日志 |
| `RAG/summary/sources/` | 源页面目录 |
| `RAG/summary/synthesis/` | 综合页面目录 |
| `RAG/reference/pdfs/` | PDF 存储目录 |
| `RAG/reference/parsed/` | 解析后的 Markdown 证据 |
| `RAG/reference/chunks/` | 证据块 JSONL |
| `RAG/reference/imports/` | 导入存档 |

## 2. 导入文献

有三种方式：

### A. BibTeX 批量导入
```bash
python scripts/rag/import_bib.py --bib references.bib --rag-dir RAG --dry-run
python scripts/rag/import_bib.py --bib references.bib --rag-dir RAG
```
**产出**：去重后写入 `RAG/references.bib`，记录到 `RAG/log.md`

### B. Zotero 压缩包导入
```bash
python scripts/rag/zip_importer.py --zip export.zip --rag-dir RAG --dry-run
python scripts/rag/zip_importer.py --zip export.zip --rag-dir RAG
```
**产出**：解析 RDF → 提取元数据 → 复制 PDF → 追加 BibTeX

### C. INSPIRE 搜索添加
```bash
python scripts/rag/search_add.py search --query "de Graaf surface spin desorption" --limit 5
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:1705.09158" --select 1 --dry-run
python scripts/rag/search_add.py add --rag-dir RAG --query "arxiv:1705.09158" --select 1 --yes
```
**产出**：从 INSPIRE 获取规范 BibTeX → 检查重复 → 创建源页面 → 下载 PDF（如有 arXiv ID）

## 3. 生成证据（核心步骤）

导入文献后，必须运行证据管道生成可检索的 primary evidence：

```bash
# 单篇
python scripts/rag/evidence_ingest.py --rag-dir RAG --key degraafSuppressionLowfrequencyCharge2018

# 全部
python scripts/rag/evidence_ingest.py --rag-dir RAG --all
```

**处理流程**：

```
BibTeX entry
  → resolve_source.py     （判断路线：arxiv_source 或 pdf_pymupdf；pdf_mineru 仅作 legacy alias）
  → parsers.py            （arxiv2md/pandoc/pymupdf4llm → Markdown）
  → chunker.py            （LlamaIndex SentenceSplitter → 句子级块）
  → 更新 source page 的 frontmatter 证据字段
```

**每篇文献生成的文件**：

| 文件 | 路径 | 内容 |
|---|---|---|
| Parsed Markdown | `RAG/reference/parsed/{doc_id}.md` | 解析后的全文 Markdown |
| Parsed manifest | `RAG/reference/parsed/{doc_id}.manifest.json` | 解析元数据（SHA256, parser, route） |
| Chunk JSONL | `RAG/reference/chunks/{doc_id}.jsonl` | 每行一个证据块，含 chunk_id, text, section, equation_ids |

**源页面更新字段**：
`source.primary_evidence`, `source.original_pdf`, `source.source_sha256`, `source.parser`, `source.parser_version`, `source.parsed_at`, `chunk_manifest`, `quality.*`

## 4. 验证证据

```bash
python scripts/rag/validate_evidence.py --rag-dir RAG
```

检查：schema 版本、必需字段、chunk_id 唯一性、SHA256 一致性、parsed Markdown 存在性。

## 5. 搜索证据（查询）

```bash
python scripts/rag/search_evidence.py --rag-dir RAG "superconducting resonators TLS noise"
python scripts/rag/search_evidence.py --rag-dir RAG --top-k 5 --no-text "frequency noise spin desorption"
```

**返回**：按 TF-IDF 余弦相似度排序的 SearchHit 列表，包含 chunk_id, doc_id, citation_key, source_page, score, chunk text。

## 6. 追溯证据

```bash
python scripts/rag/trace_claim.py --rag-dir RAG --chunk-id "arxiv_1705.09158::results::chunk-003-a1b2c3d4e5"
```

**输出**：chunk text → source page path → parsed Markdown path → chunk manifest path → equation IDs → route → arXiv ID

## 7. 综合检查

```bash
# 标准模式
python scripts/rag/rag_lint.py --rag-dir RAG

# 严格模式（空边=错误）
python scripts/rag/rag_lint.py --rag-dir RAG --strict
```

检查范围：BibTeX 去重、死链、PDF 引用、AUTO 块匹配、schema 版本、词汇表、源页面结构、证据完整性。

## 8. 删除条目

```bash
# 预览
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --dry-run

# 执行
python scripts/rag/remove_evidence.py --rag-dir RAG --key citationKey --yes
```

**删除**：parsed Markdown、parsed manifest、chunk JSONL、PDF。**保留**：源页面（清除证据链接字段）。

## 9. 维护操作

### 同步 PDF
```bash
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir /path/to/pdfs --dry-run
python scripts/rag/sync_pdf.py --rag-dir RAG --pdf-dir /path/to/pdfs
```

### 更新源页面字段
```bash
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set year=2025 --dry-run
python scripts/rag/maintain.py update-source --rag-dir RAG --key citationKey --set year=2025 --yes
```

### 检查过时证据
```bash
python scripts/rag/check_staleness.py --rag-dir RAG
python scripts/rag/check_staleness.py --rag-dir RAG --key citationKey
```

### 重建索引导航
```bash
python scripts/rag/update_index.py --rag-dir RAG
```

## 10. 完整工作流总结

```
初始化     → 导入文献   → 生成证据   → 验证证据   → 搜索/查询
rag_init     import_bib   evidence_     validate_    search_
             zip_importer ingest       evidence     evidence
             search_add                            trace_claim
             sync_pdf                              

导入后可选步骤：
  → 填充术语表（vocabulary.md）
  → 术语标准化（edge_normalizer / physh_mapper）
  → 建立图谱索引（graph_index）

维护阶段：
  → lint 检查 → check_staleness → 必要时 re-ingest 或 remove
```

---

# 第二部分：模块设计说明

## 平台与环境

- **操作系统**：Windows 11 Pro for Workstations
- **Python**：3.13.5（Anaconda）
- **关键依赖**：arxiv2markdown, pymupdf4llm, LlamaIndex, scikit-learn, PyYAML, pybtex
- **外部 API**：INSPIRE HEP（文献搜索）、PhySH（术语标准化）
- **集成**：Claude Code 技能系统（.claude/skills/）

## 模块评分体系

每个模块按以下维度评分（1-5）：

| 维度 | 说明 |
|---|---|
| **正确性** | 功能是否正确，边界条件处理 |
| **可测试性** | 是否有测试覆盖，测试是否充分 |
| **集成度** | 是否被 pipeline/技能/其他模块引用 |
| **文档化** | 代码注释、docstring、CLI help |
| **可维护性** | 代码结构清晰度、单一职责 |

---

## 核心管道模块

### resolve_source.py
解析 BibTeX 条目确定证据路线（arxiv_source / pdf_pymupdf；pdf_mineru 仅作为 legacy alias）。
- **正确性**：4 — arXiv eprint、DataCite DOI、PDF 存在性均覆盖
- **可测试性**：4 — 4 项测试，覆盖主要路线
- **集成度**：5 — 被 evidence_ingest、parsers 引用
- **文档化**：3 — 核心函数有 docstring
- **可维护性**：4 — 纯函数式，输入明确
- **改进方向**：INSPIRE 富化可加缓存层

### parsers.py
双引擎解析：arxiv2markdown（HTML→MD）+ pandoc（LaTeX 回退）+ pymupdf4llm（PDF→MD）。
- **正确性**：4 — 三引擎覆盖 arxiv_source 和 pdf_pymupdf 路线；pdf_mineru 旧值仍可读
- **可测试性**：3 — 测试覆盖路由和注册模式，后端实际调用需网络/二进制
- **集成度**：4 — 被 evidence_ingest、validate_evidence 引用
- **文档化**：3
- **可维护性**：3 — 三个后端耦合在同一模块
- **已知风险**：三个解析后端仍耦合在同一模块；旧 `pdf_mineru` 值仅保留为兼容 alias
- **改进方向**：将 arxiv2md、pandoc、pymupdf4llm 后端拆分为独立 adapter；继续扩大 arxiv2md cache 覆盖

### chunker.py
基于 LlamaIndex SentenceSplitter 的句子级分块，regex 提取 section heading。
- **正确性**：3 — 句子级切分正确，但 heading 检测用 regex 而 LlamaIndex 的 MarkdownNodeParser header_path 有已知缺陷
- **可测试性**：3 — 3 项测试（稳定性、anchor、字符范围）
- **集成度**：4 — 被 evidence_ingest 引用
- **文档化**：3
- **可维护性**：3 — 混合方案（regex sections + LlamaIndex splitter）
- **改进方向**：LlamaIndex 升级后切换到纯 MarkdownNodeParser

### evidence_ingest.py
证据管道编排器：resolve → parse → chunk → 更新源页面。
- **正确性**：4 — 正确处理 dry-run、保留现有 body、增量更新 frontmatter
- **可测试性**：4 — 3 项测试
- **集成度**：5 — 主要入口点，被 rag-evidence 技能引用
- **文档化**：3
- **可维护性**：4 — 清晰的流程编排

---

## 查询与追溯模块

### search_evidence.py
TF-IDF + 余弦相似度搜索证据块。
- **正确性**：4 — 排序正确，区分度好
- **可测试性**：5 — 6 项测试（相关性、排序、空结果、字段完整性、格式化）
- **集成度**：4 — 被 CLAUDE.md 引用为核心查询工具
- **文档化**：4 — SearchHit dataclass 清晰
- **可维护性**：4
- **改进方向**：可升级为 BM25 或密集向量搜索

### trace_claim.py
从 chunk_id 反向追溯到源页面、parsed Markdown、方程 ID。
- **正确性**：4 — 所有字段正确追溯
- **可测试性**：3 — 2 项测试
- **集成度**：3 — 被 rag-evidence 技能引用
- **文档化**：3
- **可维护性**：4 — 单一职责

### query.py
全库 Markdown 子串搜索（grep 风格）。
- **正确性**：3 — 简单匹配，无语义理解
- **可测试性**：2 — 仅通过集成测试（子进程）
- **集成度**：2 — 独立 CLI，未被任何技能或模块引用
- **文档化**：2
- **可维护性**：3
- **改进方向**：与 search_evidence.py 合并为统一查询入口

---

## 验证模块

### rag_lint.py
综合检查：BibTeX、源页面 schema、PDF 引用、死链、AUTO 块、词汇表、源页面、证据。
- **正确性**：4 — 所有检查项正确
- **可测试性**：4 — 8 项测试，覆盖主要检查类别
- **集成度**：5 — 被 rag 和 rag-init 技能引用
- **文档化**：3
- **可维护性**：3 — 集成了 3 个 validator，但主函数较长

### validate_evidence.py
检查 parsed manifest 和 chunk JSONL 的 schema 合规性。
- **正确性**：4
- **可测试性**：3 — 2 项测试
- **集成度**：4 — 被 rag_lint 引用
- **文档化**：3

### validate_vocabulary.py
检查词汇表 schema、术语必需字段、重复 ID、别名泄漏。
- **正确性**：4
- **可测试性**：5 — 9 项测试
- **集成度**：3 — 被 rag_lint 引用
- **文档化**：4

### validate_source_pages.py
检查源页面结构、边类型、claim 证据引用。
- **正确性**：4
- **可测试性**：5 — 15 项测试
- **集成度**：3 — 被 rag_lint 引用
- **文档化**：4

---

## 维护模块

### remove_evidence.py
删除证据产物 + 清理源页面链接。
- **正确性**：4 — 修复了 YAML 缩进键清理
- **可测试性**：5 — 5 项测试
- **集成度**：3 — 被 rag-maintain 和 rag-evidence 技能引用
- **文档化**：4

### check_staleness.py
检查 SHA256 漂移、parser 版本变化。
- **正确性**：3 — 依赖外部 parser 版本函数
- **可测试性**：1 — 无测试
- **集成度**：1 — 独立 CLI，未被引用
- **文档化**：2
- **改进方向**：集成到 rag_lint 作为 staleness check 子模块

### maintain.py
更新源页面、re-ingest、remove 条目。
- **正确性**：4
- **可测试性**：4 — 5 项测试
- **集成度**：4 — 被 rag-maintain 技能引用
- **文档化**：3

---

## 导入模块

### import_bib.py
BibTeX 导入 + 去重。
- **正确性**：4
- **可测试性**：2 — 仅集成测试
- **集成度**：4 — 被 rag-import 技能引用
- **文档化**：3

### zip_importer.py
Zotero RDF+PDF 压缩包导入。
- **正确性**：4
- **可测试性**：3 — 6 项测试（含 dry-run 集成测试）
- **集成度**：3 — 被 rag-import 技能引用
- **文档化**：3
- **已知风险**：中文文件名编码（已通过 Python 侧文件发现解决）

### search_add.py
INSPIRE 搜索 + 交互式添加。
- **正确性**：4
- **可测试性**：4 — 4 项测试
- **集成度**：4 — 被 rag-import 和 rag-maintain 技能引用
- **文档化**：4

---

## 术语与图谱模块

### physh_mapper.py
APS PhySH API 术语标准化 + 本地词汇表回退。
- **正确性**：3 — API 调用有节流和缓存，网络无连接时回退到本地
- **可测试性**：1 — 无测试（依赖外部 API）
- **集成度**：2 — 被 edge_normalizer、migrate_tags_to_edges 引用
- **文档化**：4 — 详细 docstring
- **可维护性**：3 — 约 400 行，API 逻辑与缓存层耦合
- **改进方向**：mock PhySH API 增加单元测试

### edge_normalizer.py
批量标准化原始术语为 DARW edge 条目。
- **正确性**：3
- **可测试性**：1 — 无测试
- **集成度**：1 — 独立 CLI
- **改进方向**：集成到 evidence_ingest 流程，自动填充边

### migrate_tags_to_edges.py
遗留自由文本 tags → 结构化 edges。
- **正确性**：3 — dry-run 安全，按设计不删除原 tags
- **可测试性**：1 — 无测试
- **集成度**：1 — 一次性迁移工具
- **改进方向**：当所有源页面迁移完成后可移除

### graph_index.py
从源页面 edges 构建 YAML 图谱索引。
- **正确性**：3
- **可测试性**：1 — 无测试
- **集成度**：1 — 独立 CLI
- **改进方向**：集成到 update_index 流程，支持 NetworkX 图查询

---

## 共享模块

### darw_schema.py
DARW schema 常量（版本、route、edge 类别）和路径辅助函数。
- **正确性**：5 — 单一真相来源
- **可测试性**：2 — 隐式测试通过其他模块
- **集成度**：5 — 被 7+ 模块引用
- **文档化**：4
- **已知风险**：保留 `PDF_MINERU` 仅为读取旧 manifest/source page 的 compatibility alias
- **改进方向**：在确认旧数据迁移完成后移除 alias

### common.py
共享辅助函数（read_frontmatter, write_frontmatter, ensure_rag_dirs, append_log）。
- **正确性**：4 — YAML 回退解析器有边界情况
- **可测试性**：2 — 隐式测试（15+ 模块导入）
- **集成度**：5 — 被 9+ 模块引用
- **文档化**：3

### metadata_normalizer.py
DOI、arXiv ID、标题标准化。
- **正确性**：4
- **可测试性**：3 — 被 test_dedup 测试
- **集成度**：5 — 被 6+ 模块引用
- **文档化**：3

### bib_parser.py
BibTeX 解析/渲染。
- **正确性**：4
- **可测试性**：5 — 5 项测试
- **集成度**：5 — 被 9+ 模块引用

---

# 第三部分：完成度评估

## 当前可实现的操作

| 操作 | 状态 | 说明 |
|---|---|---|
| 初始化知识库 | ✅ | rag_init.py |
| BibTeX 导入 + 去重 | ✅ | import_bib.py，支持 DOI/arXiv/标题去重 |
| Zotero 压缩包导入 | ✅ | zip_importer.py，含中文文件名处理 |
| INSPIRE 搜索添加 | ✅ | search_add.py，含 arXiv PDF 下载 |
| arXiv 论文解析（HTML→MD） | ✅ | arxiv2markdown 集成，pandoc LaTeX 回退 |
| PDF 论文解析（PDF→MD） | ✅ | pymupdf4llm 集成 |
| 证据分块（句子级） | ✅ | LlamaIndex SentenceSplitter |
| 源页面生成 | ✅ | evidence_ingest.py + build_source_pages.py；ingest.py 为 legacy |
| 证据搜索（TF-IDF） | ✅ | search_evidence.py |
| 证据追溯 | ✅ | trace_claim.py |
| 证据删除 + 链接清理 | ✅ | remove_evidence.py |
| 综合 lint | ✅ | rag_lint.py（含 --strict） |
| 证据验证 | ✅ | validate_evidence.py |
| 词汇表验证 | ✅ | validate_vocabulary.py |
| 源页面验证 | ✅ | validate_source_pages.py |
| 过时检查 | ✅ | check_staleness.py |
| 术语标准化 | ✅ | physh_mapper.py, edge_normalizer.py |
| 图谱索引构建 | ✅ | graph_index.py |
| 索引导航重建 | ✅ | update_index.py |
| BibTeX 导出 | ✅ | export.py |
| PDF 同步/下载 | ✅ | sync_pdf.py, pdf_downloader.py |
| 条目维护 | ✅ | maintain.py |

## 当前不能做的操作（推迟到后续 Phase）

| 操作 | Phase | 阻塞原因 |
|---|---|---|
| LLM 撰写源页面摘要 | Phase 7 | 需要证据块数据足够丰富后再引入 |
| Qdrant 向量存储 | Phase 10 | 需要 strict lint 至少对一篇论文通过 |
| 语义向量搜索 | Phase 10 | 同上 |
| 混合查询（图谱+向量+关键词） | Phase 11 | 需要 Phase 8 + 10 先完成 |
| NetworkX 图推理 | Phase 8+ | graph_index 目前仅做 YAML 导出 |
| 跨源综合 | Phase 7+ | 需要 claim 生成和边填充 |

## 潜在风险

1. **PDF route 命名兼容期**：canonical route 已改为 `pdf_pymupdf`，旧 `pdf_mineru` 仅作为 schema/validator/CLI compatibility alias 保留。风险是旧数据迁移前仍会在少量兼容层看到 legacy 名称。

2. **词汇表为空**：`vocabulary.md` 的 `terms: []` 意味着所有 source page 的 edges 均为空。edge-based 查询和图谱导航完全不可用，直到手动填充术语。

3. **Windows 编码**：已增加 `cli_encoding.py` 并在 `common.py` 中配置 UTF-8 stdio；仍需关注不导入 `common.py` 的独立脚本输出。

4. **外部 API 依赖**：INSPIRE 和 PhySH API 不可用时，search_add 和 physh_mapper 功能降级。

5. **LlamaIndex heading 缺陷**：MarkdownNodeParser 对顶级标题返回 `header_path: /`，导致 section 标题检测依赖 regex 回退。

6. **证据覆盖率低**：当前 7 篇源页面中仅 2 篇有完整的证据产物（parsed MD + chunks），其余仅为元数据存根。

7. **技能引用覆盖仍需巡检**：核心 evidence/search/trace/validate/maintain 脚本已有技能入口；新增的 vocabulary suggestion、evidence summary、graph/edge 工具需要定期与技能文档同步。

8. **端到端集成测试仍可加强**：`test_rag_workflow.py` 已迁移到 metadata stub builder，但 evidence pipeline 的真实后端调用仍依赖网络/外部库，主要通过注册模式与单元测试覆盖。

## 未来改进路线图

**短期（Phase 7）**：
- vocabulary.md 术语表已可通过 `suggest_vocabulary.py` 从 evidence chunks 生成候选；仍需人工审核后写入
- LLM/AI 辅助源页面摘要可通过 `summarize_evidence.py` 生成 chunk-backed draft；必须保留 chunk_id 引用

**中期（Phase 8+ enhanced, Phase 10）**：
- graph_index.py 集成 NetworkX 图查询
- Qdrant 向量存储 + 语义搜索
- check_staleness 集成到 rag_lint

**长期（Phase 11+）**：
- 混合查询（图谱过滤 → 向量搜索 → 证据块返回）
- 跨源综合报告生成
- legacy PDF route alias 移除（确认旧数据完成迁移后）
- 三个解析后端拆分为独立 adapter 模块
