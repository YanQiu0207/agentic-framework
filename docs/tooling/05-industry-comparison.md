# 业界框架横向对比

> 本文在 `02-tool-landscape.md`（Superpowers 深度对比）和 `04-compound-engineering-comparison.md`（ce-compound 对比）基础上，补充 OpenSpec、Spec Kit、Taskmaster 的对比，形成完整的横向视图。
>
> **复核说明**：2026-06-28 已按官方 README / 文档复核 Superpowers、OpenSpec、Spec Kit、Taskmaster；这些工具迭代很快，本文只保留可由当前公开文档支撑的描述。

---

## 一句话定位

| 框架 | 定位 | 核心解决什么问题 |
|---|---|---|
| **本框架** | 快速构建大型非生产工具的 AI 工程方法论 | 结构与速度的平衡：前重设计门 + 执行段自主并行 |
| **Superpowers** | 编码 agent 的完整开发方法论（通用） | 执行段自主并行 + subagent-driven + worktree 隔离 |
| **OpenSpec** | 轻量 spec / change 工作流层 | 先对齐变更意图，再通过 proposal / specs / design / tasks / apply / verify / archive 管理实现闭环 |
| **Spec Kit** | GitHub 开源的 Spec-Driven Development 工具包 | constitution / specify / plan / tasks / implement 的结构化开发路径，可扩展为团队流程 |
| **Taskmaster** | 面向 AI 开发的任务管理与自动执行工具 | PRD 拆解、依赖图、任务追踪，以及 loop / clusters 自动执行 |
| **compound-engineering-plugin** | 工程经验即时沉淀工具 | 把解决问题的过程知识固化为可复用资产 |

---

## 维度对比

### 工作流完整性

| 维度 | 本框架 | Superpowers | OpenSpec | Spec Kit | Taskmaster |
|---|---|---|---|---|---|
| 需求澄清 | ✅ workflow-requirements-clarification | ✅ brainstorming（设计硬门） | ✅ `/opsx:explore` / `/opsx:propose` | ✅ `/speckit.specify` + `/speckit.clarify` | ⚠️ 主要依赖输入 PRD |
| 系统设计 | ✅ system-design / quick-design | ✅ writing-plans | ✅ `design.md` | ✅ `/speckit.plan` | ❌ 无专门设计阶段 |
| 任务拆解 | ✅ tasks.md（用户批准） | ✅ writing-plans（2-5 分钟小任务） | ✅ `tasks.md` | ✅ `/speckit.tasks` | ✅ 自动拆解（核心功能） |
| 并行执行 | ✅ DAG 分波 + worktree 隔离 + 依赖冲突校验（`lint_task_deps`） | ✅ dispatching-parallel-agents | ⚠️ 支持并行变更管理，但非核心并行 agent 编排 | ⚠️ tasks 可标记并行项，但非核心多 agent 编排 | ✅ `tm clusters start` 支持按依赖簇并行执行 |
| 代码评审 | ✅ 分级多维（3 档 / 5+1 agent） | ✅ task 级两阶段 review + code review 技能 | ⚠️ `/opsx:verify` 偏规格一致性验证，不是代码评审 | ⚠️ `/speckit.analyze` / checklist 偏跨产物一致性与需求质量 | ❌ 无专门 code review 机制 |
| 客观门禁 | ✅ workflow-verification（配置驱动 build/test/lint + 基线对比 + 内置 spec drift 检查） | ✅ TDD + 完成分支前测试验证 | ⚠️ `/opsx:verify` 会报告问题，但文档说明不阻断 archive | ⚠️ checklist / analyze / 项目原则，可接入 CI，但不是内置硬门禁 | ⚠️ 任务含 `testStrategy`，loop preset 可加测试 / lint，但非统一硬门 |
| 知识沉淀 | ✅ ADR + arch-snapshot + spec 归档 | ❌ 无显式 intent / ADR 沉淀 | ✅ specs + changes/archive | ⚠️ constitution + specs / plan / tasks | ⚠️ tasks.json / task files，偏任务状态沉淀 |

### 执行自主性

| 框架 | 执行节奏 | 人工干预点 |
|---|---|---|
| 本框架 | tasks 批准后自主连跑 | 需求→设计→tasks 批准；收尾汇报 |
| Superpowers | brainstorm 批准后自主连跑 | 设计批准；完成后 code review |
| OpenSpec | 有 `/opsx:apply` 执行 tasks，但强调轻量、可迭代 | propose 前可 explore；apply 后可 verify / archive |
| Spec Kit | 按 constitution → specify → plan → tasks → implement 推进 | 关键产物建议人工审阅，也可按 lean path 快速跑 |
| Taskmaster | `tm loop` 可顺序自动执行，`tm clusters start` 可并行执行 | 任务 / 依赖 / 执行计划可审阅；强制审批不属于核心机制 |

### 质量基建深度

| 框架 | review 机制 | 验证机制 | 对抗性验证 |
|---|---|---|---|
| 本框架 | 3 档位 × 5 维度 reviewer + critic judge | ✅ workflow-verification（配置驱动 + 基线对比 + spec drift） | ✅ review-critic 专项驳斥 |
| Superpowers | task 级两阶段 review + code review 技能 | ✅ TDD + 完成分支前测试验证 | ❌ 无独立 critic judge |
| OpenSpec | ⚠️ 规格一致性验证 | ⚠️ `/opsx:verify` 非硬阻断 | ❌ 无独立 critic judge |
| Spec Kit | ⚠️ analyze / checklist / constitution | ⚠️ 可扩展接入 CI，核心不是统一硬门禁 | ❌ 无独立 critic judge |
| Taskmaster | ❌ 无专门 review | ⚠️ testStrategy + loop preset | ❌ 无独立 critic judge |

---

## 各框架的核心优势与短板

### Superpowers

**强在**：执行形态最完整——并行 dispatch、worktree 隔离、subagent-driven、TDD 强制。这是本框架执行段的直接原型。

**弱在**：
- 无本框架这种分级多维 review + critic judge，质量审查深度仍弱于本框架
- 无本框架这种系统 intent / ADR 沉淀机制（每次探索成本难以沉淀为长期架构记忆）
- 无 Fast-Path（所有改动都走完整流程）

**适用场景**：通用 AI 辅助开发，对质量深度要求中等、更看重执行速度的场景。

---

### OpenSpec

**强在**：
- 专注 spec-driven development，核心产物轻量、可读
- `/opsx:explore` / `/opsx:propose` / `/opsx:apply` / `/opsx:verify` / `/opsx:archive` 串成完整变更闭环
- 对「承重决策」做最小化但足够结构化的文档

**弱在**：
- 执行与验证存在，但质量门不是硬阻断，文档明确 `/opsx:verify` 只报告问题、不阻断 archive
- 并行执行不是核心卖点，更多是「按 change 管理并行工作」而不是多 agent DAG 编排
- 仍以 `openspec/specs/` 保存当前规格，和本框架「代码是事实来源、文档沉淀 intent」的哲学不同

**与本框架的关系**：OpenSpec 解决的是「如何用轻量变更工件让人和 AI 先对齐再实现」；本框架解决的是「在更重的质量基建下，如何把设计转成可验证、可并行、可沉淀的实现」。可以组合：借鉴 OpenSpec 的 change / archive 思路，但执行与质量门仍由本框架负责。

**不采用原因**（更新后）：OpenSpec 当前更完整，但仍以 `openspec/specs/` 作为当前行为真相。本框架刻意避免维护会和代码争真相的中央现状规范库，只沉淀需求、决策 intent、架构快照和变更记录；因此更适合吸收其轻量 change / archive 做法，而不是整体迁移。

---

### Spec Kit（GitHub）

**强在**：
- GitHub 官方开源项目背书，并支持 30+ AI coding agent 集成
- constitution → specify → plan → tasks → implement 路径清晰
- 支持 clarify / analyze / checklist 等辅助质量步骤，也支持 extensions / presets / bundles 扩展团队流程

**弱在**：
- 相比 OpenSpec 更重，文档和模板体系更多，轻量个人任务会显得有仪式感
- `/speckit.implement` 可执行 tasks，`tasks.md` 也可标记并行项，但官方核心文档没有把多 agent 并行编排作为主要卖点
- 无本框架这种分级多维 code review + critic judge
- 知识沉淀主要靠 constitution、spec / plan / tasks 等产物，无本框架这种 ADR / intent 专项沉淀机制

**适用场景**：生产系统的团队协作开发，需要与 GitHub 生态深度集成的场景。

**与本框架的关系**：Spec Kit 更像通用、可扩展的 SDD 工具包；本框架是面向「大型非生产工具」的本地方法论，重点放在快速前重设计、执行段并行、自主验证和 intent 沉淀。

---

### Taskmaster

**强在**：
- PRD→带依赖关系任务清单，自动拆解、复杂度分析和依赖追踪是核心价值
- `tm loop` 支持顺序自动执行，`tm clusters start` 支持按依赖簇并行执行（当前文档强调 Claude Code + tmux / iTerm2 体验）

**弱在**：
- 无本框架这种统一的强制质量门（分级 review / verify / spec drift / ADR）
- 无需求澄清、系统设计阶段
- 知识沉淀偏任务状态与执行上下文，不覆盖系统 intent / ADR
- 任务拆解质量依赖输入 PRD 的质量

**与本框架的关系**：Taskmaster 已不只是 tasks 生成器，它在依赖图、顺序 loop、并行 clusters 上与本框架执行段有重叠；但本框架仍强在前置设计门、分级质量门、spec drift 和 intent 沉淀。若只想加强任务编排，Taskmaster 值得作为候选；若要端到端方法论，本框架覆盖面更完整。

---

### compound-engineering-plugin（详见 doc 04）

**强在**：解决问题时即时沉淀（上下文最新鲜），Overlap Detection 防碎片化。

**弱在**：沉淀对象是「解决问题的过程知识」，不是「系统架构理解」或「决策 intent」——定位不同。

**已吸收的点**：ADR 即时触发原则、「放弃的方案」独立成节、「适用条件」字段。

---

## 综合定位图

```
                    执行自主性
                    高 ↑
                    │
         Superpowers │ 本框架
         Taskmaster  │ (执行强 + 质量深
         (执行强,    │  + 知识沉淀)
          质量中)
                    │
────────────────────┼──────────────────── 质量深度
低                  │                   高
                    │
     轻量任务清单   │   Spec Kit / OpenSpec
                    │   (规格化强,
                    │    门禁深度中等)
                    │
                    ↓ 低
```

**结论**：旧版结论「OpenSpec / Spec Kit / Taskmaster 无执行能力」已过时。当前真正差异不再是「谁能执行」，而是「执行后有没有足够深的质量与 intent 闭环」。本框架仍适合放在右上角：它把并行执行、分级多维 review、`workflow-verification` 客观门禁、spec drift 检查和 ADR / arch-snapshot 沉淀放在同一条链路里。代价是复杂度最高，不适合轻量场景。

> 一份对自身短板的独立批判（含已补 / 待做项）见 [07-critical-review.md](07-critical-review.md)。

---

## 来源盲区（诚实标注）

- 已复核官方公开文档，但未实际安装跑通 OpenSpec / Spec Kit / Taskmaster 的最新版本
- Spec Kit 是否在具体团队流程中接入 CI / PR / issue，需要看用户安装的 extensions / presets / bundles，不能从核心 README 直接推出
- Taskmaster 的 `clusters start` 当前文档更偏 Claude Code + tmux / iTerm2 场景，其他环境体验需实测
- 以上对比基于 2026-06-28 公开信息，框架迭代较快，建议定期复核

## 本次复核来源

- [Superpowers README](https://github.com/obra/superpowers)：basic workflow、subagent-driven development、TDD、code review 与 finishing branch。
- [OpenSpec README](https://github.com/Fission-AI/OpenSpec) / [OpenSpec commands](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)：OPSX workflow、`/opsx:apply`、`/opsx:verify`、archive。
- [Spec Kit README](https://github.com/github/spec-kit)：`/speckit.constitution`、`/speckit.specify`、`/speckit.plan`、`/speckit.tasks`、`/speckit.implement`、`/speckit.analyze`、`/speckit.checklist`。
- [Taskmaster README](https://github.com/eyaltoledano/claude-task-master) / [Taskmaster docs](https://tryhamster.com/docs/taskmaster)：task structure、dependencies、`tm loop`、`tm clusters start`。
