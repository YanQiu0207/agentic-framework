# opsx-* 工作流 × 标准 OpenSpec

> 对照对象：本仓库 `skills/opsx-*` 技能族 与 官方 OpenSpec（见 [01-openspec-core.md](01-openspec-core.md)）。
> **定性**：以下差异**不是缺陷，而是约束下的有意取舍**——业务要求「使用 OpenSpec，但不要中央真相库」，且载体限定为纯 Claude Code Skill（无 Node CLI）。本文记录取舍内容与代价，便于后人理解「为什么这么裁」。

## 1. opsx-* 是什么

本仓库有两套设计工作流：默认的 `workflow-*`，以及本文的 `opsx-*`。`opsx-*` 是在纯 Skill 环境里对 OpenSpec 的复刻，服务一个明确约束：

> **对外符合「使用 OpenSpec」（沿用其 `changes/` 目录、proposal/design/tasks、delta 词汇），但刻意不引入中央真相库。**

## 2. 对比总览

| 维度 | 标准 OpenSpec | 本仓库 `opsx-*` | 性质 |
| --- | --- | --- | --- |
| 载体 | Node CLI + 各工具 slash command | 纯 Claude Code Skill（Markdown） | 环境约束 |
| 中央真相库 `specs/` | ✅ `openspec/specs/<cap>/`（source of truth） | ❌ 只有 `changes/` 与 `changes/archive/` | **有意取舍** |
| archive 合并 | ✅ delta merge 进 `specs/` | ❌ 只移动目录（无合并目标） | 取舍的必然结果 |
| 校验 | ✅ `validate --strict` | ❌ 无 CLI、无机器校验 | 载体约束 |
| spec 格式 | `### Requirement:` + `#### Scenario:`（GWT） | 自由 bullet（功能要求/行为约束/验收标准） | 载体约束 |
| 变更元数据 | 可选 `.openspec.yaml`（change metadata） | ❌ 已删除，状态靠目录位置表达 | **本次精简** |
| 架构/ADR 沉淀 | 不属于 OpenSpec（OpenSpec 不管这层） | ❌ 已删除，opsx 不承担知识沉淀 | **本次精简** |
| 流程哲学 | fluid，无刚性门禁 | 刚性顺序门禁（继承 `workflow-*` 风格） | 实现差异 |
| 评审 | 无 | 复用 `workflow-code-review` 多 agent 评审 | **增益** |

## 3. 三个核心取舍（约束使然，非疏漏）

**① 无中央真相库 `openspec/specs/`** —— 业务明确不要。`opsx-project-knowledge` 的目录树只有 `changes/` 与 `changes/archive/`，capability spec 只活在每个变更内部（`opsx-requirements-clarification` 产出 `changes/<name>/specs/<cap>/spec.md`）。系统现状以代码为准。

**② archive 不合并** —— ①的必然结果。`opsx-archive` 只把整目录移到 `changes/archive/YYYY-MM-DD-<name>/`，没有合并步骤——因为根本没有可合并进去的中央库。

**③ 无 CLI / validate，spec 用自由格式** —— 纯 Skill 载体（无 Node CLI）的必然。spec 结构对不对靠 AI 自觉；`spec_capability_template.md` 把「状态（ADDED/MODIFIED/REMOVED）」放文件头，正文是自由 bullet，没有 `Requirement`/`Scenario`/Given-When-Then，也没有 SHALL/MUST 强制。

## 4. 本次精简（2026-06-21）

在上述取舍基础上，进一步删掉两样冗余：

- **删 `.openspec.yaml`**（含模板文件）：既然没有中央库、archive 不合并，`Draft/In Review/Approved` 这套 status 元数据没有任何驱动价值。改为：
  - **活跃 / 已归档** 由**目录位置**表达（`changes/` vs `changes/archive/`）；
  - **Quick Draft** 由 `proposal.md` 头部「状态」字段标注（`quick-proposal-template.md` 自带，`opsx-code-generation` 路由读它）。
- **删「更新 architecture / ADR」**：`opsx-*` 聚焦 OpenSpec 的 changes 流，不承担常青架构文档与 ADR 的知识沉淀（那是 `workflow-*` + `project-knowledge` 那套的职责）。相应删掉了 `opsx-project-knowledge` 的 architecture/adr 章节、`opsx-archive` 的文档同步检查、`opsx-code-generation`/`opsx-quick-design` 的文档同步任务。

## 5. 已知代价（诚实记录）

- **delta 语义弱化**：`ADDED/MODIFIED/REMOVED` 本是「相对某个 base spec 的增量」，但没有中央库 = 没有 base、归档也不合并。因此 opsx 的 delta 实质是「每个变更孤立的需求文档 + 一个状态标签」，不构成对某个真相库的真增量。**这是「不要中央真相库」的直接代价，已接受。**
- 没有 `validate` 兜底：spec 是否写全、capability 是否一致，靠人工/AI 自觉。

## 6. 与 workflow-* 的关系

两套工作流**都不维护中央真相库**，变更产物都是一次性的：

- `workflow-*`：诚实地用单一 `spec.md`（10 章设计文档）。
- `opsx-*`：套用 OpenSpec 的 `changes/` 目录形态与 delta 词汇——选它的理由是**对外符合「使用 OpenSpec」**。

> 一句话：`opsx-*` = OpenSpec 的目录骨架 + 词汇，在「不要中央真相库 + 纯 Skill」约束下的精简实例化。它不追求 OpenSpec 的 `specs/` 闭环，只借其变更管理的形态。

## 来源

- 标准 OpenSpec：见 [01-openspec-core.md](01-openspec-core.md)（官方 main 分支已核实）。
- opsx-* 证据：`skills/opsx-project-knowledge/SKILL.md`（目录结构、归档）、`skills/opsx-archive/SKILL.md`（只移动不合并）、`skills/opsx-requirements-clarification/`（产出 + `reference/spec_capability_template.md` 自由格式）、`skills/opsx-system-design/SKILL.md`（刚性顺序门禁）、`skills/opsx-code-generation/SKILL.md`（复用 `workflow-code-review`）。
