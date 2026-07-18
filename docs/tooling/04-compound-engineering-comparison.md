# compound-engineering-plugin 调研与对比

> 调研背景：本框架「代码是事实来源」的哲学导致每次探索代码都从零开始，架构理解无法跨会话复用。调研 compound-engineering-plugin 是为了了解它如何沉淀可复用资产，并判断有哪些设计值得吸收。
>
> 调研方式：多角度 web 搜索 + 对抗性核验（25 条声明，6 条通过，19 条否决）。以下仅记录通过核验的事实。

## compound-engineering-plugin 核心机制

### 「可复用资产」的定义

带 YAML frontmatter 的结构化 Markdown 文件，存储于 `docs/solutions/[category]/[filename].md`，分两种形式：

| Track | 固定章节 |
|-------|---------|
| Bug track | Symptoms / What Didn't Work / Solution / Why This Works / Prevention |
| Knowledge track | Context / Guidance / Why This Matters / When to Apply / Examples |

定位为「institutional memory」——供未来 AI agent 运行时检索，而非通用 wiki。

### 触发时机

刻意选在**问题刚解决、上下文最新鲜时**。支持两种方式：

- **自动关键词触发**：识别「that worked」「it's fixed」「working now」「problem solved」等短语后自动触发
- **手动命令**：`/ce-compound`

### 防碎片化：Overlap Detection

写入前在 5 个维度评分：

1. problem statement
2. root cause
3. solution approach
4. referenced files
5. prevention rules

4-5 个维度重叠时，更新已有文档而非新建，避免同一问题产生多份漂移文档。

### 已知缺陷（中等置信度）

SkillsBench（arXiv 2602.12670，86 个任务、7308 条轨迹）显示，**纯自动生成的技能库平均比无技能基线低 1.3 个百分点**。

注意：该测试针对「完全自动生成」，而 ce-compound 是「AI 辅助 + 人工确认」的结构化写入，两者方法论不完全等价，负面结论不能直接平移。

### 与「代码是唯一真相」的关系

插件从未做显式哲学声明。它隐含地将 `docs/solutions/` 视为 AI agent 的 institutional memory，属于对「真相来源」边界的扩展，但没有明确反对「代码唯一真相」。相关核验声明全部被否决（0-3 票）。

---

## 与本框架的对比

### ce-compound 更接近 ADR，还是架构快照？

**结论：ce-compound 的 knowledge track 本质上是 ADR 的工程化包装。**

| 维度 | ce-compound knowledge track | 本框架 ADR |
|------|-----------------------------|-----------|
| 背景/问题 | Context | 背景 |
| 决策/方案 | Guidance | 决策 |
| 为什么有效 | Why This Matters | 后果（隐含） |
| 何时适用 | **When to Apply** | ❌ 无 |
| 具体示例 | **Examples** | ❌ 无 |
| 放弃的方案 | ❌（bug track 有 What Didn't Work） | 后果（隐含，不明确） |

ce-compound 的 bug track（What Didn't Work / Why This Works / Prevention）也和 ADR 强相关——本质是「放弃的方案 + 决策理由 + 红线约束」，只是用工程师更自然的语言包装。

两者的根本差异是触发时机：
- ADR：「交付前沉淀检查」时回忆写入（上下文已冷）
- ce-compound：问题刚解决时即时触发（上下文最新鲜）

### 两个框架的定位差异

| | compound-engineering-plugin | 本框架 |
|---|---|---|
| **沉淀内容** | 解决问题的过程知识（how to fix X） | Intent（为什么这样做）+ 现在新增的架构快照 |
| **触发时机** | 问题解决后（事件驱动） | ADR：不可逆决策时即时触发（主触发点）；交付前检查（补网）。架构快照：探索/Q&A 后按需落地 |
| **时效性处理** | Overlap Detection 防碎片化 | `vcs_ref`（git hash / SVN revision）标注过期；`vcs_ref` 与当前版本库一致时自动跳过 |
| **与代码的关系** | 隐含地扩展真相来源边界 | 明确区分「现状以代码为准」vs「intent 必须沉淀」 |

两者解决不同场景，**可以共存，不是替代关系**。

---

## 吸收决策

### 吸收到 ADR

| 吸收点 | 来源 | 改法 |
|--------|------|------|
| 「放弃的方案」独立成节 | bug track 的 What Didn't Work | ADR 模板新增 `## 放弃的方案` 章节 |
| 「适用条件」可选字段 | knowledge track 的 When to Apply | ADR 模板新增 `## 适用条件（可选）` |
| 触发时机即时化 | ce-compound 「上下文最新鲜时触发」原则 | 不再只等交付前；做出不可逆决策时即时询问是否写 ADR |

### 吸收到架构快照（新机制，本次新增）

ce-compound 没有「系统现状快照」这类资产，但它的几个设计模式值得借鉴：

| 借鉴点 | 如何应用到架构快照 |
|--------|-----------------|
| 两种 track 结构 | structure track（模块边界/接口/数据流）+ insights track（设计模式/关键权衡） |
| Overlap Detection | 落地前检查同模块是否已有同 track 文件，有则询问更新/跳过 |
| YAML frontmatter | 加入 `git_commit`、`module`、`generated_at` 字段，支持结构化索引 |
| 「上下文最新鲜时触发」 | 探索/Q&A 结束后主动询问，不等用户手动发起 |

### 不吸收的部分

- Bug track 的固定章节结构（Symptoms / What Didn't Work...）：架构快照不是「问题解决记录」，不需要这个形式
- 「AI agent 自动检索利用」的定位：架构快照主要供**人**快速定向，不需要为 agent 自动发现而设计

---

## 遗留问题（未解答）

1. ce-compound 的「结构化写入 + 人工确认」机制是否能显著优于 SkillsBench 测试的「完全自动生成」基线，目前无受控对照实验数据。
2. Overlap Detection 的 5 维度评分在语义模糊时是否会产生误判（漏更新或误更新），引入「知识债务」？目前没有公开的压力测试数据。
3. 架构快照的 insights track 与 ADR 之间的边界：何时写 insights.md，何时直接升格为 ADR？（待在实践中观察后再明确。）
