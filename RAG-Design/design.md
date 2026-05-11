# 研究知识库（RAG）框架设计方案

## 1. 背景与目标

Vibe Research Pipeline 需要一个面向高能物理研究的知识库层，用来连接论文、PDF、BibTeX、Zotero、项目笔记、讨论共识、失败记录和论文写作。这个知识库需要同时服务理论组、实验组以及理论—实验混合项目，因此不能把目录结构、术语体系或论文总结模板固定成某一种研究范式。

本设计中的“RAG”不是单纯的向量数据库问答系统，而是一个 **LLM 可维护的研究知识库**：

- 原始材料保存在文件系统中，便于人类检查和团队同步；
- AI 生成的结构化总结保存在 Markdown 中，便于跨 session 积累；
- 受控词汇表和 source page 模板由项目初始化时交互生成，避免硬编码；
- 通过 Claude Code skill 定义可重复执行的知识库操作；
- 必要时可接入向量检索或外部 API，但不把它们作为唯一知识来源。

目标是建立一个可读、可维护、可协作、可追溯的研究知识层，而不是只做一次性文献问答。

---

## 2. 设计来源与已有框架比较

### 2.1 传统 RAG 系统

传统 RAG 通常由以下环节组成：

1. 收集文档；
2. 切分 chunk；
3. 生成 embedding；
4. 存入向量数据库；
5. 根据 query 检索相关 chunk；
6. 由 LLM 基于检索结果生成回答。

这种模式适合大规模非结构化文本问答，优点是自动化程度高、检索范围大、对用户透明度要求低。但在研究工作流中存在明显不足：

- 检索结果通常是临时上下文，不自然形成长期可维护知识；
- chunk 缺少研究语义结构，难以表达“方法、假设、适用范围、失败原因、共识”等信息；
- 不适合多人协作编辑和审查；
- 很难追踪一个结论是来自哪篇论文、哪次讨论、哪条笔记；
- 对 BibTeX、Zotero、LaTeX 写作等研究工具链支持不足。

因此，传统向量 RAG 可以作为本框架的可选加速层，但不能作为核心知识组织方式。

### 2.2 Jin Lei 的 LLM Wiki 思路

Jin Lei 的设计更接近“LLM Wiki”：让 AI 维护一组 Markdown 页面，包括论文页、主题页、失败记录、受控词汇表和研究 profile。其核心价值不是向量检索，而是让知识以人类可读、可编辑、可复查的形式积累。

本框架吸收它的几个关键思想：

- 用 Markdown 作为长期知识载体；
- 为每篇 source 建立结构化页面；
- 用受控词汇表减少跨 session 命名漂移；
- 记录失败、争议和阶段性结论，而不只记录成功结果；
- 让 AI 通过文件系统读写来维护知识，而不是只在上下文窗口中回答问题。

但本框架不能照搬 Jin Lei 的结果，因为目标场景不同：

| 维度 | Jin Lei 方案 | 本框架 |
|---|---|---|
| 主要对象 | 计算/建模研究流 | 理论、实验、混合项目 |
| 知识结构 | 更偏个人或小组研究 wiki | 作为 Vibe Research Pipeline 的知识层 |
| 模板/词汇表 | 可由具体项目经验沉淀 | 必须由项目初始化交互生成 |
| 文献工具链 | 可结合文献库 | 明确支持 BibTeX、Zotero、PDF、LaTeX |
| 协作模型 | 偏研究 wiki | 需要适配多仓库、多层同步、团队共享 |

因此，本设计学习的是“LLM 可维护 wiki”的思想，而不是复制固定目录和固定字段。

### 2.3 Vibe Research Pipeline 的约束

当前 pipeline 已经有以下基础设施：

- `CLAUDE.md` 作为薄索引和行为协议；
- 多层同步：个人层、协作者层、团队层；
- TODO 和 session recovery 协议；
- 论文、代码、笔记、决策记录分层存放；
- Claude Code skill 作为可复用操作入口。

因此，RAG 不应设计成一个独立应用，而应作为 pipeline 的知识层：

- `CLAUDE.md` 只引用 RAG 索引，不直接塞入大量知识；
- `/RAG/` 保存项目知识库；
- `.claude/skills/` 定义知识库操作；
- `references.bib` 和 PDF 目录服务团队共享文献管理；
- 论文写作 skill 可调用 RAG 的检索和 BibTeX 输出能力。

---

## 3. 本框架的核心设计

### 3.1 设计原则

1. **结构化 Markdown 优先**：长期知识以 Markdown 保存，而不是只存在于 embedding 或聊天上下文中。
2. **原始材料与总结分离**：PDF、Zotero 导出、BibTeX 属于 reference；AI 总结、共识和索引属于 summary。
3. **模板和词汇表动态生成**：不同项目可定义不同 source page 模板和维度体系。
4. **操作协议化**：常用动作通过 skill 描述成可重复执行的协议。
5. **基础操作可组合**：高级操作应尽量由导入、去重、同步、摘要、查询、维护等基础操作组合而成。
6. **可追溯**：每条综合结论应能追踪到 source page、笔记或讨论记录。
7. **可协作**：文件结构应适合 Git/OneDrive/Overleaf 等已有同步机制。

### 3.2 目录结构

```text
/RAG/
├── SKILL.md                  # 日常知识库操作说明
├── vocabulary.md             # 项目受控词汇表，初始化时生成
├── template.md               # source page 模板，初始化时生成
├── index.md                  # 知识库导航中心
├── log.md                    # 知识库操作日志
├── references.bib            # 团队共享文献 manifest
├── summary/                  # 结构化知识
│   ├── sources/              # 每篇文献一页
│   ├── [维度1]/              # 由初始化生成，如 methods、systems、observables
│   ├── [维度2]/
│   ├── [维度3]/
│   └── synthesis/            # 跨文献综合、共识、争议、失败记录
└── reference/                # 原始材料
    ├── pdfs/                 # PDF 文件
    └── imports/              # 可选：外部导入源的归档或临时说明

.claude/skills/
├── rag-init/
│   └── SKILL.md              # 项目初始化
├── rag/
│   └── SKILL.md              # 日常操作：ingest/query/lint/update-index/sync-from-notes
├── rag-import/
│   └── SKILL.md              # 外部导入：import-bib/import-zip/search-and-add
└── rag-maintain/
    └── SKILL.md              # 维护：remove/update-source/re-ingest/sync-pdf
```

### 3.3 关键文件职责

| 文件或目录 | 职责 |
|---|---|
| `/RAG/reference/` | 保存原始材料，包括 PDF、导入源、外部 metadata。 |
| `/RAG/summary/` | 保存 AI 与人共同维护的结构化知识。 |
| `/RAG/summary/sources/` | 每篇论文或资料对应一个 source page。 |
| `/RAG/summary/synthesis/` | 保存跨文献共识、争议、失败记录、主题综述。 |
| `/RAG/template.md` | 定义 source page 应包含哪些字段，由项目初始化生成。 |
| `/RAG/vocabulary.md` | 定义项目受控词汇表，减少命名漂移。 |
| `/RAG/index.md` | 知识库入口，指向重要主题、维度页、synthesis 和 source pages。 |
| `/RAG/references.bib` | 团队共享文献 manifest，类似依赖清单，不等同于单篇论文的最终 `.bib`。 |
| `/RAG/log.md` | 记录导入、删除、重索引、修正等知识库操作。 |

### 3.4 BibTeX 的双重角色

BibTeX 在本框架中有两种不同用途：

1. **知识库 manifest**：`/RAG/references.bib` 记录团队知识库包含哪些文献，类似 `requirements.txt`。
2. **论文写作引用**：具体论文项目中的 `.bib` 只收录写作中实际引用的条目，可由 RAG 检索后导出或由 INSPIRE-HEP 实时获取。

因此，RAG 应提供 `get-bibtex` 能力，但不直接承担 LaTeX 文档编辑职责。插入 `\cite{}` 应由论文写作 skill 完成。

---

## 4. 框架能力模型

研究知识库不能只用 CRUD 描述。除增删改查外，还需要归一化、分类、综合、校验和追溯。

| 能力类别 | 说明 | 示例操作 |
|---|---|---|
| Import / Ingest | 引入外部材料或把原始材料转成知识页 | import-bib、import-zip、ingest PDF |
| Normalize / Deduplicate | 统一 metadata、citation key、DOI/arXiv、去重 | 自动去重、规范 BibTeX |
| Summarize / Index | 生成 source page，并写入维度索引 | 增量摘要、update-index |
| Query / Retrieve | 根据描述、方法、结论、对象查找内容 | 根据内容描述查找文献 |
| Synthesize | 跨 source 总结共识、争议、失败 | 讨论时找共识、从笔记抽取决策 |
| Maintain / Update | 删除、修正、重新索引、同步 PDF | remove、update-source、re-ingest、sync-pdf |
| Integrate | 与外部工具链连接 | Zotero、BibTeX、LaTeX、CLAUDE.md、项目笔记 |
| Validate / Lint | 检查一致性和可维护性 | 死链检查、重复 key 检查、PDF 缺失检查 |
| Trace / Provenance | 追踪结论来源 | 从 synthesis 追踪到 source page 和笔记 |
| Export | 输出某个主题的材料集 | reading list、主题 BibTeX、写作引用候选 |

这个能力模型说明：用户提出的 12 个操作不是孤立功能，而是上述能力的具体实例。

---

## 5. 当前可实现操作分析

### 5.1 12 个操作的能力映射

| 操作 | 能力类别 | 可实现性 | 依赖模块 | 说明 |
|---|---|---|---|---|
| 从 Zotero BibTeX 导入 | Import + Deduplicate | 可以 | bib parser、dedup、sync-pdf、ingest | 解析 `.bib`，去重后加入 manifest，并触发 PDF 同步和摘要。 |
| 从 Zotero PDF 压缩包导入 | Import + Normalize | 可以 | zip importer、RDF parser、dedup、ingest | 实际 Zotero 导出常见为 RDF + files 目录，需要解析 metadata 与附件关系。 |
| 自动去重 | Normalize / Deduplicate | 可以 | dedup module | 按 DOI、arXiv、标题规范化、作者年份等规则判断重复。 |
| 删除不相关参考文献 | Maintain | 可以 | locator、cascade delete、lint | 删除 BibTeX、PDF、source page，并清理索引和交叉链接。 |
| 根据描述搜索并添加 | Import + External Search | 可以 | INSPIRE/arXiv search、pdf downloader、ingest | 先返回候选，用户确认后添加。 |
| 增量摘要新参考文献 | Summarize / Index | 可以 | references.bib、PDF reader、template、index updater | 对 manifest 中未生成 source page 的文献执行 ingest。 |
| 从项目笔记管理 KB | Synthesize + Integrate | 可以 | note reader、extraction prompt、ingest/update-index | 从笔记抽取引用、方法讨论、共识和失败记录。 |
| 根据内容描述查找文献 | Query / Retrieve | 可以 | index、维度页、source pages | 先查结构化索引，再必要时扩展到外部搜索。 |
| 写文章时自动插入引用 | Integrate + Export | 可以，但应拆分 | get-bibtex、paper-writing skill | RAG 提供 BibTeX，论文写作 skill 负责修改 LaTeX。 |
| 讨论时找到相关内容和共识 | Query + Synthesize | 可以 | CLAUDE.md 引用、index、synthesis | 通过 RAG 索引查找先前讨论、共识和相关文献。 |
| 修正错误的总结 | Maintain / Update | 可以 | source locator、PDF reader、template、index updater | 重新读取原文，更新 source page 和相关索引。 |
| 重新索引参考文献 | Maintain / Update | 可以 | pdf replacement、re-ingest、lint | 替换 PDF 或 metadata 后重新生成 source page。 |

结论：这 12 个操作都能在该框架下实现，而且不需要改变总体目录结构。它们的差异主要在于属于基础操作还是组合操作。

### 5.2 基础操作与组合操作

建议把操作分成两层：

**基础操作**：

- `ingest`：从单篇 PDF 或 BibTeX entry 生成 source page；
- `query`：从 index、维度页和 source pages 中检索信息；
- `lint`：检查链接、BibTeX、PDF、source page、index 的一致性；
- `update-index`：根据 source page 更新维度页和 index；
- `sync-from-notes`：从项目笔记抽取结构化知识。

**组合操作**：

- `import-bib` = parse bib + dedup + sync-pdf + ingest；
- `import-zip` = unzip + parse metadata + copy PDF + dedup + ingest；
- `search-and-add` = external search + user confirmation + download + ingest；
- `remove` = locate + confirm + cascade delete + lint；
- `update-source` = locate + reread + rewrite source page + update-index；
- `re-ingest` = replace PDF/metadata + ingest + lint；
- `get-bibtex` = query + metadata lookup + BibTeX export。

这样可以避免 skill 文件变成一组互相重复的长流程。

### 5.3 还可自然支持的操作

除了当前 12 个操作，本框架还自然支持：

| 操作 | 用途 |
|---|---|
| `lint` | 检查死链、重复 BibTeX key、缺失 PDF、source page frontmatter 不完整。 |
| `export-reading-list` | 导出某个主题、方法或项目阶段的阅读清单。 |
| `export-bibtex` | 导出某个主题或论文草稿需要的 BibTeX 子集。 |
| `trace-claim` | 追踪某个结论来自哪些 source pages 或笔记。 |
| `merge-rag-update` | 合并协作者更新的 source pages、vocabulary 和 synthesis。 |
| `check-staleness` | 检查 arXiv 版本、PDF、source page 是否过期。 |
| `summarize-topic` | 基于多个 source pages 生成主题综述。 |

这些操作说明该框架不只是“查文献”，而是一个研究知识维护系统。

---

## 6. 关键输入格式与数据流设计

### 6.1 Zotero RDF + files 目录

Zotero 的导出不一定是单个 `.bib` 或 `.ris` 文件。实际导出的压缩包可能包含一个 RDF 元数据文件和一个 `files/` 附件目录。设计上应把它视为一种正式输入格式。

典型结构：

```text
zotero-export/
├── exported-items.rdf
└── files/
    ├── <attachment-id>/
    │   └── paper.pdf
    └── <attachment-id>/
        └── snapshot.html
```

RDF 中需要解析的关键信息：

| 字段 | 用途 |
|---|---|
| `dc:title` | 标题 |
| `bib:authors` | 作者列表 |
| `dcterms:abstract` | 摘要 |
| `dc:date` | 发表日期 |
| `dc:description` / `dc:identifier` | arXiv ID、DOI 或其他标识 |
| `z:citationKey` | Zotero citation key |
| `z:Attachment` | 附件 metadata |
| `z:path` | 附件文件路径 |
| `link:link` | 文献条目与附件的关联 |

导入逻辑：

1. 解压后优先查找 RDF；
2. 解析论文 metadata；
3. 解析 attachment；
4. 用 RDF link 关系匹配论文与附件；
5. 只把 PDF 类型附件复制到 `/RAG/reference/pdfs/`；
6. HTML snapshot 等非 PDF 附件不进入 PDF 库；
7. 生成或补全 BibTeX entry；
8. 执行去重；
9. 触发 ingest。

### 6.2 其他导入格式

导入格式优先级建议为：

1. RDF + files：保留 Zotero metadata 和附件关系；
2. BibTeX：适合文献 manifest；
3. RIS：作为兼容格式；
4. PDF-only：只能从文件名、PDF metadata、arXiv/DOI 检索中推断信息。

### 6.3 去重策略

去重应在所有导入入口中复用同一套规则：

| 优先级 | 规则 | 说明 |
|---|---|---|
| 1 | DOI 完全匹配 | 最可靠。 |
| 2 | arXiv ID 完全匹配 | 对预印本文献可靠。 |
| 3 | 标题规范化后相同 | 忽略大小写、标点和多余空格。 |
| 4 | 作者列表 + 年份高度一致 | 作为辅助判断。 |
| 5 | 标题相似度超过阈值 | 只作为兜底，需在报告中说明。 |

每次导入都应报告新增、跳过和可能冲突的条目数量。

---

## 7. 具体实现方案

### 7.1 文件系统骨架

P0 阶段只需要创建框架骨架：

- `/RAG/SKILL.md`
- `/RAG/index.md`
- `/RAG/log.md`
- `/RAG/references.bib`
- `/RAG/template.md`
- `/RAG/vocabulary.md`
- `/RAG/summary/sources/`
- `/RAG/summary/synthesis/`
- `/RAG/reference/pdfs/`

维度目录不应硬编码，应由初始化过程根据项目类型生成。例如理论项目可能生成 `methods/`、`models/`、`approximations/`；实验项目可能生成 `detectors/`、`datasets/`、`systematics/`。

### 7.2 Skill 层

| Skill | 职责 |
|---|---|
| `rag-init` | 初始化 `/RAG/`，询问用户项目类型、source page 模板、受控词汇表维度。 |
| `rag` | 日常操作：`ingest`、`query`、`lint`、`update-index`、`sync-from-notes`。 |
| `rag-import` | 外部导入：`import-bib`、`import-zip`、`search-and-add`。 |
| `rag-maintain` | 维护：`remove`、`update-source`、`re-ingest`、`sync-pdf`。 |

Skill 文件应写操作协议，而不是写死具体项目词汇。真正的项目词汇来自 `/RAG/vocabulary.md`，source page 格式来自 `/RAG/template.md`。

### 7.3 Script 层

建议脚本按能力拆分，而不是按用户话术拆分：

| 模块 | 用途 |
|---|---|
| `rdf_parser.py` | 解析 Zotero RDF，输出规范化 metadata 和附件映射。 |
| `bib_parser.py` | 解析 BibTeX，输出规范化 entry。 |
| `ris_parser.py` | 解析 RIS，作为兼容输入。 |
| `metadata_normalizer.py` | 统一 DOI、arXiv ID、标题、作者、citation key。 |
| `dedup.py` | 复用去重逻辑。 |
| `pdf_downloader.py` | 从 arXiv/INSPIRE 等来源下载 PDF，并验证 PDF。 |
| `external_search.py` | 封装 INSPIRE-HEP 和 arXiv 搜索。 |
| `rag_lint.py` | 检查知识库一致性。 |

如果 P0 阶段只做框架和 skill，可以暂不实现所有脚本，但文档中应明确它们的职责边界。

### 7.4 CLAUDE.md 集成

项目 `CLAUDE.md` 应保持薄索引，只引用 RAG 入口：

```markdown
## 知识库
@/RAG/index.md

### 快速操作
- 归档论文：读 /RAG/SKILL.md 的 Ingest 操作
- 查询文献：读 /RAG/SKILL.md 的 Query 操作
- 导入 Zotero：读 .claude/skills/rag-import/SKILL.md
- 维护知识库：读 .claude/skills/rag-maintain/SKILL.md
```

不要把大量文献总结、物理结论或模板细节直接写入 `CLAUDE.md`。

### 7.5 与论文写作集成

自动插入引用应拆成两层：

1. RAG 提供 `get-bibtex`：根据描述找到候选文献并返回 BibTeX entry 或 citation key。
2. 论文写作 skill：检查论文项目的 `.bib`，必要时追加 BibTeX，并在 LaTeX/Typst 中插入引用。

这样可以保持 RAG 的职责清晰：RAG 管“知识和引用信息”，写作 skill 管“修改论文文件”。

---

## 8. 实施路线

### P0：核心骨架

目标：让知识库可以被初始化、手动 ingest、查询和 lint。

- 创建 `/RAG/` 目录结构；
- 创建 `rag-init` 和基础 `rag` skill；
- 生成 `template.md` 和 `vocabulary.md` 的初始化协议；
- 支持手动添加 source page；
- 支持 `index.md` 导航和基础 lint。

### P1：BibTeX 与 PDF 同步

目标：让 `references.bib` 成为可用的团队文献 manifest。

- 实现 BibTeX 解析；
- 实现 DOI/arXiv/title 去重；
- 复用或改造 PDF 下载脚本；
- 支持 `import-bib` 和 `sync-pdf`。

### P2：维护能力

目标：让知识库可以长期维护，而不是只增不改。

- 实现 remove；
- 实现 update-source；
- 实现 re-ingest；
- 实现 cascade cleanup 和 lint。

### P3：高级导入与笔记同步

目标：连接 Zotero、外部搜索和项目笔记。

- 实现 Zotero RDF + files 导入；
- 实现 INSPIRE/arXiv 搜索并添加；
- 实现 sync-from-notes；
- 支持 synthesis 页面生成。

### P4：写作与团队协作优化

目标：让 RAG 与论文写作和协作流程闭环。

- 实现 `get-bibtex`；
- 与 LaTeX/Typst 写作 skill 对接；
- 支持 reading list / BibTeX 子集导出；
- 支持团队协作合并和 staleness check。

---

## 9. 测试与验收策略

测试章节应验证框架能力和不变量，而不是记录某个具体样例压缩包中有哪些论文。

### 9.1 单元测试

| 测试对象 | 验证内容 |
|---|---|
| RDF parser | 能从 Zotero RDF 中抽取 title、authors、date、abstract、arXiv/DOI、citation key 和 attachment path。 |
| BibTeX parser | 能解析 entry key、author、title、year、doi、eprint。 |
| RIS parser | 能解析基础 metadata，并转换成统一格式。 |
| metadata normalizer | 能规范 DOI、arXiv ID、标题和作者列表。 |
| dedup | 能按 DOI、arXiv ID、标题规范化结果识别重复。 |
| PDF validator | 能识别有效 PDF，拒绝非 PDF 或损坏文件。 |

### 9.2 集成测试

| 场景 | 验收标准 |
|---|---|
| import-bib | 新文献进入 `references.bib`，重复文献被跳过，报告包含跳过原因。 |
| import-zotero-rdf | RDF metadata 被解析，PDF attachment 被复制，非 PDF attachment 被跳过。 |
| sync-pdf | 缺失 PDF 被下载或报告失败，已有 PDF 不重复下载。 |
| ingest | 为未处理文献生成 source page，并更新 index/维度页。 |
| remove | 删除文献后，BibTeX、PDF、source page、维度页和 index 中的引用一致清理。 |
| update-source | 修正 source page 后，相关维度页和 synthesis 不产生死链。 |
| re-ingest | 替换 PDF 或 metadata 后可重新生成 source page，并保留必要 provenance。 |
| sync-from-notes | 能从笔记中抽取引用、方法讨论、共识和失败记录。 |
| get-bibtex | 能根据描述返回候选 BibTeX entry，不直接修改论文文件。 |
| lint | 能发现死链、缺失 PDF、重复 BibTeX key、source page frontmatter 缺失等问题。 |

### 9.3 端到端测试

完整工作流应覆盖：

1. 初始化 RAG；
2. 导入一批文献；
3. 去重；
4. 同步 PDF；
5. 生成 source pages；
6. 查询某个方法或主题；
7. 从笔记同步一条共识或失败记录；
8. 导出某个引用的 BibTeX；
9. 修正或重索引一篇 source；
10. 删除一篇不相关文献；
11. 运行 lint，确认知识库状态一致。

### 9.4 质量验收标准

| 标准 | 要求 |
|---|---|
| 可读性 | source page、synthesis、index 都应能被人类直接阅读。 |
| 可追溯性 | synthesis 中的重要结论能追踪到 source page 或笔记来源。 |
| 一致性 | index 不含死链，BibTeX 不含重复 key，source page frontmatter 完整。 |
| 可维护性 | 模板和词汇表可由项目初始化生成，不依赖固定学科目录。 |
| 可组合性 | 高级操作应由基础操作组合，避免重复实现。 |
| 工具链兼容 | 能与 Zotero、BibTeX、PDF、CLAUDE.md、论文写作流程连接。 |

---

## 10. 设计取舍与风险

### 10.1 优点

- 比传统向量 RAG 更透明，知识可读可审查；
- 比普通文件夹更结构化，AI 可以稳定维护；
- 比固定 wiki 模板更灵活，适配理论、实验和混合项目；
- 与 Vibe Research Pipeline 的 session recovery、CLAUDE.md 和多层同步机制兼容；
- 支持从文献管理到论文写作的端到端链路。

### 10.2 缺点

- 初始设计比简单向量库复杂；
- 需要维护模板、词汇表和索引一致性；
- source page 质量依赖 LLM 摘要质量和用户审查；
- 如果没有 lint，长期维护可能出现死链、重复条目和命名漂移；
- 大规模全文语义检索可能仍需要额外向量库辅助。

### 10.3 适用边界

本框架适合：

- 长期研究项目；
- 多人协作文献和知识维护；
- 需要记录共识、失败和争议的研究过程；
- 需要连接 BibTeX/Zotero/PDF/论文写作的项目。

不适合只做一次性问答、临时 PDF 总结，或完全不需要人工审查的自动知识库。

---

## 11. 总结

本方案把 RAG 设计为 Vibe Research Pipeline 的研究知识层。它吸收传统 RAG 的检索思想和 Jin Lei LLM Wiki 的可维护 Markdown 思路，但不照搬固定目录和模板。核心是：原始材料与结构化总结分离，模板和词汇表由项目初始化生成，知识库操作通过 skill 协议化，高级功能由基础操作组合实现。

在这个框架下，当前讨论的 12 个操作都可以实现；同时，框架还自然支持 lint、trace、export、merge、staleness check 等更符合长期研究维护需求的操作。后续实现应从 P0 骨架开始，再逐步接入 BibTeX/PDF、维护操作、Zotero RDF、项目笔记和论文写作工具链。
