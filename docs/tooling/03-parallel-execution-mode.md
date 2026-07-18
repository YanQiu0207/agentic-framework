# 执行段设计规格 — 下放 agent 与并行执行

> 本规格描述 `workflow-code-generation` **执行段（步骤 5：下放 agent 执行）** 的设计——把「逐 task 停等串行执行」换成「设计与 tasks.md 批准后的批量自主实现」。它是 `code-generation` 这一个 skill 的一部分（中等及以上改动走此执行段），前期（需求 / 设计 / 任务拆解 / 批准）和收尾（汇总 + intent 沉淀）不变。

## 1. 定位与边界

- **管**：tasks.md 批准之后，到全部 task 实现完成、质量门通过、汇总交付之前。
- **不管**：需求澄清、系统设计、任务拆解、用户对设计/tasks 的批准——这些是人把关的前期，保持不变。
- **本质**：把 Superpowers 的执行形态（subagent-driven + 并行 + worktree + 自主连跑）嫁接到 `workflow-*`，质量门用 `workflow-*` 自己的（多维 `code-review`）。

## 2. 前置条件（人把关的最后一道闸）

进入本模式前必须全部满足，否则退回标准流程：

1. `spec.md`（或 Quick Draft）已存在且已批准。
2. `tasks.md` 已拆解完成，每个 task 带 `depends_on`、`review_profile`、`context_files`、`verification`、`artifacts`。
3. 用户已批准 `tasks.md`。
4. 编码规范已确定（按技术栈）。

## 3. 何时进入本执行段

`workflow-code-generation` 步骤 1 复杂度路由判定为**中等及以上**（不满足 Fast-Path 的「请求即计划」判据）、且 tasks.md 经用户批准后，即进入本执行段。波内并行度由 `depends_on` 决定：多 task 无依赖 → 并行分波；单 task / 串行依赖 → 逐波单 agent。

## 4. 核心流程

> **编排模型（先判定 CLI）**：`code-review` 按 task 风险选择轻量 / 标准 / 严格 reviewer 集，「子 agent 能否再派子 agent」（嵌套 dispatch）决定 review/verify 跑在哪层。Claude Code 自 v2.1.172（2026-06-10）起**支持**子 agent 嵌套（深度上限 5 层，已实测确认）。据此二选一：**模式 A（支持嵌套，默认）**——每 task 派 owner 子 agent；`lightweight` / `standard` 由 owner 自闭环，`strict` 的 review 和裁决上提给主 agent 或独立 Judge Agent；**模式 B（不支持嵌套的 CLI）**——implementer 只实现，主 agent 上提 review/verify。实现见 `workflow-code-generation` skill 步骤 5。

### Phase 0：准备

1. 完整读 `spec.md` + `tasks.md`。
2. 加载编码规范（`bp-coding-best-practices` + `bp-performance-optimization` + 按文件类型 `std-*`）。
3. 记录 `base_sha=$(git rev-parse HEAD)`，后续 `workflow-verification` 显式传 `--diff-base <base_sha>`。
4. 由 `depends_on` 构建任务 **DAG**，**分波（wave）**：同波内任务互不依赖、可并行；后波依赖前波产物。无依赖信息时保守串行或回问用户。

### Phase 1：逐波并行执行

对每个 wave：

1. **并行 dispatch**：wave 内每个 task 派一个子 agent（模式 A 为 owner、模式 B 为 implementer），各自在**隔离 git worktree**（基于当前分支 HEAD）工作，受并发上限约束（超出排队）。
   - subagent 输入：task 描述 + `context_files` + `verification` + `artifacts` + spec/tasks 摘要 + 编码规范 + worktree 路径。
   - subagent 动作：模式 A（owner）完成实现 → 写 + 跑测试（`workflow-test-generation`，与实现同批）→ 机器验证；`lightweight` / `standard` 自跑 review，`strict` 等待独立 Judge 裁决后修复 keep finding。模式 B（implementer）实现 + 写 / 跑测试。（可选 TDD：先写失败测试）
2. **每产物过质量门**（在各自 worktree 内；模式 A 按 review 档位分流，模式 B 由主 agent 跑）：
   - `workflow-code-review`（按风险分级：小需求轻量审，普通任务标准审，高风险任务严格审）。
   - `workflow-verification`（有配置跑 build / test / lint；无配置也跑内置 spec drift）——与 review 并列，机器能验的不靠 LLM 背书。
   - 未过 → 有限轮次自修复 → 仍不过 → 标记该 task **「需人工」**，**不阻塞同波其他 task**。
3. **合并**：wave 内通过的 task，其 worktree 依次合并回主分支；冲突 → 标记该 task「需人工」。
4. **不停等用户**，进入下一波。

### Phase 2：收尾（全部 wave 完成后）

1. **一次性**汇总报告：每个 task 的实现 / review 结果、哪些「需人工」、哪些冲突。
2. 交付前 **intent 沉淀检查**（按 `project-knowledge`）。
3. 交付，等用户验收。

## 5. 关键设计点

| 设计点 | 说明 |
| --- | --- |
| **CLI 嵌套能力决定编排** | 支持子 agent 嵌套（如 Claude Code）→ 模式 A：owner 执行，`strict` 独立裁决；不支持 → 模式 B：主 agent 上提质量门 |
| **依赖分波保正确性** | 有依赖的 task 不并行；无 `depends_on` 则保守串行或询问 |
| **worktree 隔离保并行安全** | 并行写文件不冲突；review/verify 通过后才合并回主分支 |
| **失败隔离** | 单 task 失败/不过/冲突 → 标记「需人工」，不阻塞其他、不停整个流程 |
| **tasks.md 进度真相源** | 状态实时写回（进行中 / 完成 / 需人工 + 原因 + 失败输出）；中断后读 tasks.md + `git worktree list` 残留续跑 |
| **质量不打折** | 必过匹配风险的 review；小需求不强制全量 reviewer，高风险才全量 |
| **严格档独立裁决** | `strict` 的 implementer、reviewer、Judge 分离；owner 只修复 keep finding，不参与最终裁决 |
| **自主但可观测** | 全程不停等，但每个 subagent 的 review/verify 结果留痕，末尾汇总透明 |
| **并发上限** | 受机器/工具并发能力约束，超出排队 |
| **安全边界** | worktree 基于主分支，合并前主分支不受影响 |

## 6. 强制规则

1. 前置门（设计 + `tasks.md` 批准）未过，**禁止**进入并行执行。
2. 每个并行产物**必须**过匹配风险的 `code-review`，不得整体跳过 review。
3. 失败 task **必须**标记「需人工」，不得静默丢弃或假装通过。
4. 合并回主分支前，每个 worktree **必须** review 通过。
5. 收尾**必须**做 intent 沉淀检查。
6. 测试与实现**同批交付**，不允许先实现后补。

## 7. 反模式

| ❌ | ✅ |
| --- | --- |
| 不构依赖图就全并行 | 按 `depends_on` 分波，依赖串行、独立并行 |
| 并行产物不过 review/verify 直接合并 | 每产物过质量门，通过才合并 |
| 单 task 失败就停整个流程 | 失败隔离、标记需人工、继续其余 |
| 逐 task 停等用户 | 全程自主，末尾一次性汇总 |

## 8. 与 `workflow-code-generation` 的关系

本规格即 `workflow-code-generation` 步骤 5「下放 agent 执行」的详细设计。`code-generation` 是统一入口 + 复杂度路由：符合「请求即计划」的**轻量改动**由主会话直改（Fast-Path），**中等及以上**走本执行段（下放 agent，单 task 单 agent / 多 task 并行分波）。两者是**同一个 skill**，共享质量基建（review / intent 沉淀）；Fast-Path 免 spec / tasks，标准流程须经过完整前置设计门。
