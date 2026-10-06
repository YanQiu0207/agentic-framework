---
name: workflow-code-review
description: 代码审查。用户要求审查变更或开发流程进入 Review 时调用；按风险选择综合审查或五维审查，完成定向复审并输出报告。
---

> 输出一行：`Using workflow-code-review`

# 代码审查

**Reviewer 负责发现问题，编排方负责组织审查。** 综合 Reviewer 完成轻量和标准档结论；严格档由独立 Judge 依据审查证据裁决，Judge 不代替 Reviewer 产出问题。

## 报告职责

| 档位 | 结论与报告生成方 |
| --- | --- |
| `lightweight` / `standard` | `comprehensive-reviewer`，无需另设 Judge |
| `strict` | 未参与实现的独立 Judge，依据 Reviewer 和 Critic 的证据裁决 |

参与实现的调用者须把严格档裁决交给未参与实现的主 Agent 或其他独立 Judge。实现者提交产物并修复保留的问题；编排方和实现者只能原样保存审查方生成的完整 JSON，不得手写、补写或改写结论、P0/P1 数量和轮次。

## Review 档位

| 档位 | 适用 | 调用 reviewer |
| --- | --- | --- |
| `lightweight` | 小需求 / 低风险：局部改动，或不改变接口、契约、控制流与模块交互的跨文件机械重复改动；不碰数据 / 权限 / 并发 / 安全 / 性能关键路径 | `comprehensive-reviewer`（一趟覆盖工程规范、需求符合度、正确性与健壮性） |
| `standard` | 默认档：普通功能、Bug 修复，或涉及多个模块之间的行为、契约、交互变化但风险可控 | `comprehensive-reviewer`（一趟覆盖工程规范、需求符合度、正确性与健壮性） |
| `strict` | 高风险：生产关键路径、安全 / 权限 / 数据迁移 / 并发 / 分布式 / 性能敏感 / 公共 API / 大范围重构 | 全量 5 reviewer；有 finding 时调用 `review-critic` |

调用方可显式传入 `review_profile: lightweight|standard|strict`。未传入时按范围和风险自行判定；无法判断时用 `standard`，命中高风险任一条件时用 `strict`。

## Subagent 清单

| 角色 | subagent_name | 调用方式 |
|------|---------------|----------|
| 综合审查 | `comprehensive-reviewer` | `lightweight` / `standard` 调用；根据档位控制审查深度 |
| 性能审查 | `performance-reviewer` | `strict` 调用 |
| 健壮性审查 | `robustness-reviewer` | `strict` 调用 |
| 工程规范审查 | `standards-reviewer` | `strict` 调用 |
| 契约与信任链审查 | `magical-prompt-reviewer` | `strict` 调用；涉及 prompt / 外部工具 / 权限边界时必须加入 |
| 需求/设计符合度审查 | `spec-compliance-reviewer` | `strict` 调用 |
| 对抗性验证 | `review-critic` | `strict` 有 finding 时调用 |

## 审核 Scope

- `scope: task`：Production 的单个 Task。每个 Task 只能有一次首轮审核。
- `scope: integration`：无 Run 的完整交付 diff。Tooling Native Delivery 默认 `standard`，任务声明 `strict` 时用 `strict`（独立 Judge 与三项独立性声明，不因此要求 Run）；Fast-Path 兼容别名保留 `lightweight`；Production 仍按其生命周期选择 `strict`。
- `scope: run`：Tooling 完整 Runtime Run 的完整 diff，固定使用 `strict`，必须绑定 Run Context；Run 只经显式选择启用（change 2048）。
- `strict` 审查在 Native 与 Runtime 同样要求独立 Judge；无 Run 的 strict 写成 `scope: integration` 的 v2 报告即可，不构成降级。
- 同一 Scope 的修复只能进入 re-review，不能重新启动首轮审核；不同 Task 和最终集成属于不同 Scope。上游范围改变时建立新 Review 主体（新 `subject_id`），原报告保留。

## 复审模式（re-review）

首审后的修复使用复审模式。调用方传入 `rereview: true`、上一轮报告（裁决明细和正式问题）及修复 diff。

1. **确定范围**：检查上一轮保留的问题是否修复，以及修复 diff 是否引入新问题。新 finding 仅限修复 diff，不重新扫描其外的代码。
2. **选择 Reviewer**：只派原问题所属维度的 Reviewer，每维度一个。复审新增 P0/P1 时才调用 `review-critic`。
3. **处理验证类修复**：若修复来自机器或前端验证、没有上一轮保留的问题，则按当前档位选择 Reviewer，只检查修复 diff。
4. **输出增量报告**：使用第 7 步的固定格式。原问题逐条写明“已修复 / 未修复 / 部分修复”及依据；正式问题仅保留未解决项和修复引入的新问题。

首审记第 0 轮，复审轮次在上一轮基础上加 1；没有上一轮报告的验证类修复从第 1 轮起。新问题沿用 `F-{seq}` 续号，标题加“（新增）”，如 `#### P1-2（新增）: ...`。

### 复审结束条件

- 仅总体结论为 `NEEDS_CHANGES`（存在 keep 的 P0 / P1）触发「修复 → 复审」循环；**P2 与 follow-up note 不触发循环**，原样记入报告交用户决定。
- 修复-复审最多 10 轮；第 10 轮复审仍 `NEEDS_CHANGES` → 调用方标「需人工」终止，禁止继续循环。

## 工作流

### 1. 解析 review 范围

根据用户输入确定审查文件、diff 来源和 `review_profile`。若范围不清，先澄清再继续。

> 调用方传入 `rereview: true` → 按上方「复审模式」执行（收窄核验范围与派发），不走全量首轮流程；Step 4-7 的去重、裁决与报告规则仍适用于复审产物。

- 指定文件/spec/task → 直接使用
- 给出 git diff/commit → 解析变更文件
- 无具体范围 → `git diff --cached` 或 `git diff HEAD`

### 2. 构建共享上下文

- 在 `openspec/changes/` 下搜索相关 `proposal.md`、`design.md`、Delta 和 `tasks.md`
- 确定审查文件、上下文文件（caller/callee/接口定义）
- 根据文件类型和目录确定适用 skill；若改动涉及架构边界 / 模块划分或组件接口 / 数据模型设计，相应将 `bp-architecture-design` / `bp-component-design` 加入 `{skill_list}`
- 提炼与本次 review 相关的 spec/task 摘要

### 3. 并行分派 reviewer

按 `review_profile` **并行**调用对应 reviewer subagent。**必须等待本档位所有 reviewer subagent 返回后才能进入 Step 4**——禁止主 agent 自己产出 finding。

**跳过 / 追加列表**：调用方可在请求中通过 `skip_reviewers: [name1, name2]` 跳过某些 reviewer，或通过 `extra_reviewers: [name1]` 给当前档位追加 reviewer。未指定时按 `review_profile` 调用。

派发前读取 [Reviewer 提示模板](reference/reviewer-prompts.md#reviewer-提示模板)，提供范围、上下文、严重度定义和报告要求。

### 4. 汇总审查意见

收齐本档位所有结果后，合并同根因、同位置或同调用链的问题，保留最高严重度，并分配全局编号 `F-{seq}`。

全部 Reviewer 均无正式问题时，直接进入第 7 步输出 PASS 报告。否则按 [Reviewer 意见汇总模板](reference/reviewer-prompts.md#reviewer-意见汇总) 立即向用户展示实际调用的各维度意见。

### 5. 对抗性验证

`strict` 首审有 finding 时调用 `review-critic`；复审仅在新增 P0/P1 时调用。`lightweight` / `standard` 首审不调用 Critic；若 Judge 判断问题达到严格档风险，升级为 `strict` 后重审。

调用前读取 [Critic 提示与结果模板](reference/reviewer-prompts.md#critic-提示与结果)。等待结果后立即展示成立、驳回或降级意见，再进入裁决。

### 6. 最终裁决

`lightweight` / `standard` 由 `comprehensive-reviewer` 确认审查结论并生成最终报告；`strict` 的独立 Judge 必须亲自调研后裁决，不能简单采信 reviewer 或 critic 的结论。严格档对每条 issue：

1. **独立调研**：阅读相关代码上下文（调用方、被调用方、数据流）、spec 设计意图、相关注释和 git history，形成自己对该问题的理解
2. **交叉验证**：将 reviewer 提出的证据、critic 的反证与自己调研的结果三方对比
3. **基于证据裁决**：
   - **keep**：问题成立，按 P0/P1/P2 分类进入报告正式问题区
   - **drop**：经调研确认 critic 反证成立或证据不足，丢弃
   - **follow-up note**：不够正式 finding 但值得提醒，进入报告 Follow-up Notes 区（不分级）

裁决理由须引用具体代码位置、规格条目或上下文事实，说明问题为何成立或不成立。

通过门槛：
- 存在 keep 的 P0/P1 → `NEEDS_CHANGES`
- 无 keep 的 P0/P1 → `PASS`
- P2 不阻塞通过

### 7. 输出最终报告

生成报告前读取 [审查报告格式](reference/report-format.md)，按同一次裁决同时产出 Markdown 和 JSON。保留标题、轮次、「（新增）」标记及机器字段，并核对两份报告的结论、P0/P1 数量和轮次一致。

- `lightweight` / `standard`：由 `comprehensive-reviewer` 生成最终报告。
- `strict`：由未参与实现的独立 Judge 生成最终报告。
- 编排方与实现者只能原样保存完整 JSON。

报告格式包含 Native Delivery、Fast-Path 和完整 Runtime Run 的示例及字段来源；按本次路径选择，Run 报告必须绑定实际 Run Context。
