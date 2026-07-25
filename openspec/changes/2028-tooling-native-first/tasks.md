# 实施任务清单

> 由 proposal.md（Quick Draft）生成。
>
> 任务总数：5。
>
> 核心原则：先建立可审计的 Native Delivery 合同与回归测试，再解耦默认入口；完整 Runtime Run 全程保留并回归验证。
>
- Code Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-integration.json
- 构建: N/A：本 Change 不产生独立二进制构建产物；Python 由测试与编译检查验证。
- 测试: PASS（`python -m pytest scripts -q`（324 passed, 21 skipped）、定向回归、路由 Fixture 与归档前验证均退出码 0。）

## 依赖关系总览

```text
Task 1（Native Delivery 证据合同与门禁）
    ├──> Task 2（Tooling 默认入口与可选 Runtime）
    │        └──> Task 3（Review／Verify 与 Fast-Path 收敛）
    └──> Task 4（长期知识、README 与 Skill 合同）

Task 3 ───────────────────────────────┐
Task 4 ───────────────────────────────┼──> Task 5（端到端回归与真实任务试点）
Task 1、Task 2 ───────────────────────┘
```

波次：W1 = {Task 1} → W2 = {Task 2, Task 4} → W3 = {Task 3} → W4 = {Task 5}。

Task 2 与 Task 4 修改不同文件，可并行；Task 3 必须在 Task 2 后执行，因为它消费新的默认路由和交付合同。

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `schemas/runtime/` | 修改或新增 | Task 1 | 定义 Native Delivery Verdict 的机器可读合同；不改变现有 Run Envelope 含义。 |
| `scripts/runtime_schema.py`、相关测试 | 修改 | Task 1 | 注册并校验新合同。 |
| `skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/test_check_delivery.py` | 修改 | Task 1、Task 3 | 增加非 Run 的标准交付门，并保留 Fast-Path 兼容期。 |
| `skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/test_workflow_control.py` | 修改 | Task 2 | 将 Run 初始化和 Run-bound `quality_passed` 与 DAG／恢复控制解耦。 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2、Task 4 | 将默认路径改为 Native Delivery，并列出 Runtime 升级条件。 |
| `skills/workflow-code-review/SKILL.md`、`skills/workflow-verification/SKILL.md` | 修改 | Task 3、Task 4 | 声明无 Run 的标准证据输出与完整 Run 边界。 |
| `README.md`、`openspec/specs/.../trust-model.md`、`openspec/specs/.../workflow-control/overview.md`、`openspec/specs/.../framework-unification.md` | 修改 | Task 4 | 同步稳定合同与双路径边界。 |
| `evaluation/native-delivery-pilot.md` | 新增 | Task 5 | 记录 3 个真实任务的路径对比、证据与结论。 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `check_delivery.py` CLI | 新增 Native Delivery 模式；保留 `--run-dir` 和 Fast-Path 兼容语义 | `workflow-code-generation`、用户脚本 | Task 1、Task 3 |
| `workflow_control.py event quality_passed` | 仅完整 Runtime 路径要求 Run-bound Verify Artifact | Tooling DAG 编排器 | Task 2 |
| `workflow-code-review` 机器可读报告 | 增加无 Run 的标准交付证据口径；Run 级严格报告不变 | `check_delivery.py`、Tooling 调用方 | Task 3 |
| `workflow-code-generation` 路由 | 默认 Native Delivery；按风险与执行需求升级完整 Runtime | Tooling 项目中的代码变更入口 | Task 2、Task 4 |

### 构建系统变更

- 无。全部为 Python、Schema、Skill 与 Markdown 合同变更；使用现有 `pytest`、`unittest`、Lint 与验证脚本。

## 风险与假设

| # | 描述 | 影响任务 | 假设／处理 |
| --- | --- | --- | --- |
| 1 | 无 Run 的报告若复用 Run Envelope，可能错误暗示存在 Manifest 或 Harness 证明 | Task 1、Task 3 | Native Delivery 使用独立或明确无 Run 语义的合同；不得伪造 `run_id`。 |
| 2 | 从 `quality_passed` 移除 Run 绑定可能削弱完整 Runtime 的失败关闭 | Task 2 | 保持完整 Runtime 子路径原样；仅无 Run 路径不调用 Run 记录逻辑，并补双路径回归。 |
| 3 | Fast-Path 与 Native Delivery 并存期间出现分支漂移 | Task 3、Task 4 | Fast-Path 仅保留兼容别名；文档和测试明确其退役目标。 |
| 4 | 3 个真实任务样本不足以证明通用收益 | Task 5 | 仅作为是否扩大试点的决策证据，不据此删除 Runtime 组件。 |
| 5 | `strict`、并行 worktree、恢复和审计的升级条件被漏判 | Task 2、Task 5 | 将条件写为可检查的路由表，并用触发／不触发案例验证。 |

## 任务列表

### 任务 1: [x] Native Delivery Verdict 合同、交付门与回归测试

- 状态: 完成
- 文件: `schemas/runtime/`（修改或新增）、`scripts/runtime_schema.py`（修改）、`scripts/test_runtime_schema.py`（修改）、`skills/workflow-code-generation/scripts/check_delivery.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: 无
- review_profile: standard
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-task-1.json
- 文档映射: proposal.md 1.目标 1、1.验收标准 1 和 4、2.1 整体方案、2.2 Native Delivery Verdict、2.3 Native Delivery 行
- 说明: 先定义无 Run 的 Native Delivery Verdict 及其机器校验方式。该结论只能绑定机器验证、最终 Review、知识影响和提交／工作区状态；明确拒绝将其表述为 Trust Gate PASS、Harness 能力、完整证据图或严格独立 Judge。扩展 `check_delivery.py` 以支持标准 Native Delivery，且保留现有 `--run-dir` 完整 Runtime 与 Fast-Path 兼容分支。不得修改 `runtime_trust.validate_run` 的语义。
- context_files:
  - `schemas/runtime/run-envelope.schema.json` — 现有 Run 绑定字段与不可复用边界。
  - `schemas/runtime/review-report.schema.json` — 最终 Review 裁决字段来源。
  - `scripts/runtime_schema.py`、`scripts/test_runtime_schema.py` — Schema 注册和回归模式。
  - `skills/workflow-code-generation/scripts/check_delivery.py` — 直接修改目标，当前 Run／Fast-Path 分支。
  - `scripts/test_check_delivery.py` — 直接修改目标，当前交付门夹具和断言。
  - `scripts/runtime_trust.py:validate_run` — 下游完整 Runtime 边界，只读核对。
- verification:
  - [x] `python -m pytest scripts/test_runtime_schema.py scripts/test_check_delivery.py -q` 退出码 0。
  - [x] 新增 Native Delivery 正例只输出有界裁决；伪造 Run／Trust 声明、失败 Verify、P0／P1 非零 Review、缺知识影响或脏工作区均被拒绝。
  - [x] 现有 Fast-Path 与 `--run-dir` 完整 Runtime 用例全部通过。
  - [x] `python -m py_compile scripts/runtime_schema.py skills/workflow-code-generation/scripts/check_delivery.py` 退出码 0。
- artifacts:
  - Native Delivery Verdict Schema 或等价的版本化机器合同。
  - `check_delivery.py` 的 Native Delivery 分支和回归测试。
  - Schema 与交付门测试报告。
- 验收标准:
  - [x] 无 Run 的 `standard` Review 和 PASS Verify 可生成 Native Delivery Verdict。
  - [x] Verdict 明确列出不可证明声明，且不调用 `runtime_trust.validate_run`。
  - [x] 完整 Runtime Run 的 Trust Gate 与 Fast-Path 的既有有界裁决不回归。
- 子任务:
  - [x] 1.1: 比较现有 Run Envelope、Review Report 与 Fast-Path 输出，选择不伪造 Run 事实的 Native Delivery 数据合同。
  - [x] 1.2: 实现 Schema／解析与 `check_delivery.py` Native Delivery 分支。
  - [x] 1.3: 为正例、越权声明、失败验证、Review finding、知识影响和 Git 状态补回归测试。
  - [x] 1.4: 运行 Task 1 的测试与 Python 编译检查。

### 任务 2: [x] 将 Tooling 默认入口与可选 Runtime 解耦

- 状态: 完成
- 文件: `skills/workflow-code-generation/SKILL.md`（修改）、`skills/workflow-code-generation/scripts/workflow_control.py`（修改）、`scripts/test_workflow_control.py`（修改）、必要的 `skills/workflow-code-generation/reference/` 文档（修改）
- depends_on: Task 1
- review_profile: standard
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-task-2.json
- 文档映射: proposal.md 1.目标 1、2、3 和 5、1.验收标准 2 和 4、2.2 原生执行路径／可选 DAG 控制／完整 Runtime Run、2.3 升级条件、2.4 迁移顺序 2 和 3
- 说明: 将 `workflow-code-generation` 的普通低／中风险默认执行路径改为 Native Delivery；完整 Runtime 只在 `strict` 风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或审计要求命中时初始化。保留 `workflow_control.py` 的 DAG、状态、阻塞和恢复功能；将 `init-run`、Run-bound Verify Artifact 校验及 `record_quality_passed` 限定为完整 Runtime 子路径。不得给无 Run 的任务伪造 Run Context。
- context_files:
  - `skills/workflow-code-generation/SKILL.md` — 直接修改的路由、Phase 0 和交付合同。
  - `skills/workflow-code-generation/scripts/workflow_control.py` — 直接修改的 `init-run`、`quality_passed`、波次和恢复逻辑。
  - `scripts/test_workflow_control.py` — 直接修改目标，控制流与 Runtime fixture。
  - `skills/workflow-code-generation/reference/delegated-execution-guide.md` — 调用方，当前 DAG／worktree 执行说明。
  - `skills/workflow-code-generation/scripts/check_delivery.py` — Task 1 产出的下游 Native Delivery 门。
  - `skills/workflow-verification/scripts/verify.py` — 无 `--run-dir` 可独立验证的既有能力，只读核对。
- verification:
  - [x] `python -m unittest scripts/test_workflow_control.py` 退出码 0。
  - [x] `python skills/workflow-code-generation/scripts/lint_task_deps.py <fixture-tasks.md>` 对 Native Delivery 与完整 Runtime 的任务图均退出码 0。
  - [x] 触发测试覆盖：普通单 Agent 任务不调用 `init-run`；命中每个升级条件的任务调用完整 Runtime；无 Run 的 `quality_passed` 不写 Run Artifact。
  - [x] 现有完整 Runtime 的 `init-run`、Run-bound Verify 和恢复失败关闭用例全部通过。
- artifacts:
  - Native-first 路由表与升级条件。
  - 解耦后的 `workflow_control.py` 接口和双路径回归测试。
  - 更新后的 delegated execution 说明。
- 验收标准:
  - [x] 普通 Tooling 任务可使用 Native Delivery 而不创建 `.agentic-framework/runs/<run-id>/`。
  - [x] DAG／恢复仍可在确有任务依赖或中断恢复时独立使用。
  - [x] 任一完整 Runtime 升级条件命中时，仍执行现有严格 Run 初始化和失败关闭。
- 子任务:
  - [x] 2.1: 将现有路由条件整理为可检查的 Native／Runtime 升级表，并补触发案例。
  - [x] 2.2: 把 `workflow_control.py` 的 Run 专用动作与 DAG／恢复动作拆开，保持现有 CLI 兼容或提供明确迁移提示。
  - [x] 2.3: 更新执行指南，禁止为 Native Delivery 伪造 Run Context。
  - [x] 2.4: 运行控制流和依赖 Lint 回归。

### 任务 3: [x] 对齐 Review、Verify 与 Fast-Path 兼容期

- 状态: 完成
- 文件: `skills/workflow-code-review/SKILL.md`（修改）、`skills/workflow-verification/SKILL.md`（修改）、`skills/workflow-code-generation/SKILL.md`（修改）、`skills/workflow-code-generation/scripts/check_delivery.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: Task 1、Task 2
- review_profile: standard
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-task-3.json
- 文档映射: proposal.md 1.目标 4、2.1 整体方案、2.3 三类交付接口、2.4 迁移顺序 1 和 4、2.5 关键权衡 1 和 4
- 说明: 定义无 Run 标准 Review 与独立 Verify 的产物位置、`scope`、`review_profile` 和可放行条件；Run 级 `strict` Review 仍必须绑定 Run Context。将现有「主会话直接修改」Fast-Path 收敛为 Native Delivery 的兼容别名，避免低／中风险任务按执行主体分叉。该任务只在 Task 1 的机器合同和 Task 2 的入口路由稳定后更新文案和兼容处理。
- context_files:
  - `skills/workflow-code-review/SKILL.md` — 直接修改的机器可读 Review 合同。
  - `skills/workflow-verification/SKILL.md`、`skills/workflow-verification/scripts/verify.py` — 独立 Verify 与 Run-bound Verify 边界。
  - `skills/workflow-code-generation/SKILL.md` — Fast-Path、Native Delivery 和完整 Runtime 的调用方。
  - `skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/test_check_delivery.py` — Task 1 的实现与兼容测试。
  - `openspec/changes/4-review-report-dual-format/proposal.md` — 已存在的无 Run 报告双格式边界，防止口径冲突。
- verification:
  - [x] `python -m pytest scripts/test_check_delivery.py -q` 退出码 0。
  - [x] `python scripts/lint_skill_graph.py` 退出码 0。
  - [x] `grep -n "Native Delivery\|Fast-Path\|Run Context" skills/workflow-code-generation/SKILL.md skills/workflow-code-review/SKILL.md skills/workflow-verification/SKILL.md` 命中三路径边界，且人工核对与 Task 1、Task 2 实现一致。
- artifacts:
  - 三个 Skill 的双路径合同。
  - Fast-Path 兼容说明与交付门回归测试。
- 验收标准:
  - [x] Native Delivery 不要求 Run Context，且只能输出其有界结论。
  - [x] `scope: run` 与 `strict` Review 继续要求完整 Runtime 证据。
  - [x] Fast-Path 不再是「主会话直接修改」的独立默认执行合同。
- 子任务:
  - [x] 3.1: 更新 Review 与 Verify 的无 Run／Run-bound 产物契约。
  - [x] 3.2: 将 Fast-Path 文案和调用改为 Native Delivery 兼容别名。
  - [x] 3.3: 补充兼容、拒绝越权声明与全文引用图检查。

### 任务 4: [x] 同步长期知识、README 与 Profile 路由

- 状态: 完成
- 文件: `README.md`（修改）、`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（修改）、`openspec/specs/backend/framework/workflow-control/overview.md`（修改）、`openspec/specs/backend/engineering/tech/framework-unification.md`（修改）
- depends_on: Task 1
- review_profile: standard
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-task-4.json
- 文档映射: proposal.md 1.问题、1.目标 1 至 5、2.1 整体方案、2.2 核心组件、2.3 升级条件、2.4 迁移顺序、3.知识影响、4.运维
- 说明: 在稳定知识中明确 Tooling 的 Native-first 默认路径、完整 Runtime Run 的 opt-in 条件、DAG／恢复的独立价值，以及两种结论的可证明边界。README 仅描述已实现行为；若 Task 2 和 Task 3 尚未完成，正文必须标注 Change 状态或等待实施后写入，不能把提案当成当前事实。
- context_files:
  - `README.md:86-128` — Tooling Profile 与当前工作流说明。
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` — 直接修改的 Runtime 接入矩阵和声明边界。
  - `openspec/specs/backend/framework/workflow-control/overview.md` — 直接修改的 DAG、状态与恢复说明。
  - `openspec/specs/backend/engineering/tech/framework-unification.md` — Tooling／Production 路由的长期事实来源。
  - `openspec/changes/2028-tooling-native-first/proposal.md` — 本 Change 的已确认设计来源。
  - `skills/workflow-code-generation/SKILL.md` — Task 2 和 Task 3 的实现事实来源。
- verification:
  - [x] Markdown 相对链接检查无失效链接，且 `git diff --check` 退出码 0。
  - [x] 按 `md-zh` 检查新增或修改的中文 Markdown。
  - [x] 人工核对 README／长期 Spec 不将未实施的 Native Delivery 表述为当前事实。
- artifacts:
  - 更新后的 README、Trust Model、Workflow Control Overview 和 Framework Unification 条目。
  - 变更状态与长期知识一致性核对记录。
- 验收标准:
  - [x] 当前实现与计划状态在文档中可区分。
  - [x] Native Delivery、完整 Runtime Run 和 Fast-Path 兼容期的边界在至少一个长期入口中可定位。
  - [x] 未复制项目私有运行数据到跨项目公共知识库。
- 子任务:
  - [x] 4.1: 更新 Runtime Trust Model 与 Workflow Control Overview 的职责边界。
  - [x] 4.2: 在实施完成后更新 README 和 Framework Unification 的当前行为。
  - [x] 4.3: 完成 Markdown 与事实一致性检查。

### 任务 5: [x] 端到端回归与 3 个真实任务试点

- 状态: 完成
- 文件: `evaluation/native-delivery-pilot.md`（新建）、相关测试报告与交付 Artifact（按任务生成）
- depends_on: Task 1、Task 2、Task 3、Task 4
- review_profile: standard
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2028-tooling-native-first/review-task-5.json
- 归档调整: 用户要求以公开测试集替代手工代表性试点；本任务采用 3 个 SWE-bench Verified 实例和 8 个本地路由 Fixture。早期 Task 1 至 Task 3 未保留绑定的 Runtime Artifact，未反向补造；详见 `evaluation/native-delivery-pilot.md`。
- 文档映射: proposal.md 1.目标 5、1.验收标准 3 和 4、2.4 迁移顺序 5、2.5 关键权衡 2 和 3、4.运维
- 说明: 在完整 Runtime 与 Native Delivery 均可用后，选择 3 个不同代表性 Tooling 任务：局部低风险变更、普通多文件变更、触发升级条件的高风险或并行／恢复变更。记录每个任务的路径、验证与 Review 结果、人工介入、墙钟耗时、Token／成本（不可得则 `unknown`）、重试和恢复需求。高风险样本必须走完整 Runtime，不能为了对比强行降级。
- context_files:
  - `evaluation/runtime-threat-cases.md` — 当前 Runtime 风险用例和不可降低的边界。
  - `docs/tooling/11-session-telemetry.md`、`scripts/analyze_session_metrics.py` — 可用的成本和收敛数据来源。
  - Task 1 至 Task 4 的实现与测试报告 — 本次试点的前置事实。
  - `skills/workflow-code-generation/SKILL.md` — 最终路径路由与升级条件。
  - `openspec/changes/2028-tooling-native-first/proposal.md` — 试点指标与停止条件。
- verification:
  - [x] `python -m pytest scripts -q` 退出码 0。
  - [x] `python scripts/lint_skill_graph.py` 退出码 0。
  - [x] 3 个公开 SWE-bench Verified 试点均附 Agent 聚焦测试和官方评测结论；`completed=3`、`resolved=3`、`errors=0`。
  - [x] 原始 Task 1 至 Task 3 缺少绑定的 Runtime Artifact 已如实记录；公开试点与本地路由 Fixture 的证据范围已在 `evaluation/native-delivery-pilot.md` 分离说明。
  - [x] `evaluation/native-delivery-pilot.md` 包含路径、结果、人工介入、耗时、Token／成本、重试和恢复字段；未知值明确写 `unknown`。
- artifacts:
  - 全量回归记录。
  - 3 个真实任务的交付证据与 `evaluation/native-delivery-pilot.md`。
  - 是否继续扩大 Native Delivery 默认范围的决策记录。
- 验收标准:
  - [x] 两条路径的现有自动化回归全部通过。
  - [x] 归档前 Task 级和 integration 级独立 Review 的 P0／P1 均为 0；发现的 Verify 合同和文档漂移 P1 已修复并定向复审。
  - [x] 试点结论只决定后续扩大、调整或停止，不据此直接删除 Runtime 代码。
- 子任务:
  - [x] 5.1: 选择并记录 3 个代表性真实任务及其预期路由。
  - [x] 5.2: 自动执行 3 个公开 SWE-bench Verified 实例，保存 prediction、官方评测报告和可获得的测试字段。
  - [x] 5.3: 汇总公开试点与本地路由 Fixture，形成继续有限扩大 Native Delivery 的建议并运行全量回归。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal.md 1.问题 | Task 2、Task 4 | 解除默认 Runtime 绑定，并同步当前与计划状态。 |
| proposal.md 1.目标 | Task 1 至 Task 5 | 合同、入口、控制流、分支收敛和试点分别覆盖五项目标。 |
| proposal.md 1.验收标准 | Task 1、Task 2、Task 5 | 合同边界、迁移责任、真实试点和双路径回归。 |
| proposal.md 2.1 整体方案 | Task 1、Task 2、Task 3 | Native Delivery 与完整 Runtime 双路径。 |
| proposal.md 2.2 核心组件 | Task 1、Task 2 | Verdict、可选 DAG 与完整 Runtime 边界。 |
| proposal.md 2.3 交付接口与升级条件 | Task 1、Task 2、Task 3 | 三类交付路径与触发条件。 |
| proposal.md 2.4 迁移顺序 | Task 1 至 Task 5 | 按合同、入口、控制、收敛和数据退役顺序实施。 |
| proposal.md 2.5 关键权衡 | Task 1、Task 2、Task 5 | 验证保留、双路径、试点限制与分支收敛。 |
| proposal.md 3.知识影响 | Task 4 | 长期 Specs、README 与 Skill 合同同步。 |
| proposal.md 4.运维 | Task 4、Task 5 | 不新增服务、运行产物边界和指标记录。 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `machine-verifiable-agent-runtime` | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引。 |
| `workflow-control-overview` | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引。 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引。 |

> 本 Change 为 Quick Draft，未创建 `specs/` Delta。Task 4 在实现事实已确认后更新长期知识；归档阶段由 `project-knowledge` 核对。

## 知识冲突

- 状态: Resolved。Task 2 的路由与控制流测试、Task 3 的无 Run 交付合同和 Task 4 的长期文档已将默认路径更新为 Native Delivery、将完整 Runtime 约束为升级路径；完整 Runtime 的 Trust Gate 合同回归仍通过。

## 实际 Diff 核对

- 核对状态：Task 1 至 Task 5 已完成。原始 Task 1 至 Task 3 的 Runtime Artifact 缺口未补造；用户指定的公开 SWE-bench Verified 试点及本地路由 Fixture 已替代为 Task 5 的可复现评测证据，且不作为 Runtime Trust Gate 证据。
- 已执行：`python -m pytest scripts -q`、`python scripts/lint_skill_graph.py`、`python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2028-tooling-native-first/tasks.md`、`python scripts/delivery_route_fixture_runner.py --fixtures evaluation/delivery-route-fixtures.json` 和 `python scripts/validate_change.py --repo . --change openspec/changes/2028-tooling-native-first --phase plan --json`；归档前均记录为 PASS。
- 审查结论：Task 1 至 Task 5 均已完成独立 task-scope standard Review；integration Review 为 PASS。归档后交付门仍须消费新的 Verify Report 和 Native Delivery Verdict。
