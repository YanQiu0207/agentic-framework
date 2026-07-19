# 机器可验证的 Agent 运行协议设计

## 1. 设计判断

框架下一阶段不需要继续增加 Workflow、Reviewer 或说明文档数量，优先补齐「统一机器协议、证据链和行为回归」三项底座。它们解决的是现有能力之间无法可靠组合的问题，而不是增加新的流程层级。

## 2. 当前基线与缺口

| 能力 | 已有事实 | 本 Change 只补的缺口 |
| --- | --- | --- |
| 控制流 | `workflow_control.py` 维护 Task 状态迁移、失败隔离和恢复动作 | 缺少跨 Artifact 的 Run/Task/Attempt 标识与可重放事件历史 |
| Verification | `verify.py` 输出结构化 JSON、执行基线对比和 Spec Drift 检查 | 报告未绑定统一 Run、Task、Commit、配置摘要和生产者 |
| Review | Review JSON 已统一 `verdict`、P0/P1、`scope`、档位和轮次 | 只能校验局部字段，不能校验与被审 Diff、Run 和其他证据的一致性 |
| 评测 | 4 个核心路由 Skill 已有触发、误触发和边界用例 | 缺少自动 Runner、结果基线、恢复/冲突/跳过证据等行为用例 |
| Telemetry | 能解析 Claude Code/Codex Transcript 并输出任务归因 | 依赖宿主 Transcript 和 Markdown 标记，不是框架自己的运行事实账本 |
| Harness | Skills 采用 Agent-Agnostic 设计 | 缺少宿主能力声明、Adapter 合同和统一降级语义 |
| 信任边界 | 独立 Judge、结构化证据和失败关闭规则已分散存在 | 缺少统一威胁、信任假设、人工覆盖和不可证明边界 |

证据来源：

- `openspec/specs/backend/framework/workflow-control/overview.md`
- `openspec/specs/backend/framework/quality-gates/overview.md`
- `openspec/specs/backend/framework/session-telemetry/overview.md`
- `openspec/specs/backend/engineering/tech/adr/003-quality-gate-evidence.md`
- `docs/tooling/08-evaluation-strategy.md`
- `docs/tooling/13-agentic-workflow-engine-references.md`

## 3. P0 设计

### 3.1 Run Envelope 与分类型 Schema

所有机器产物共享最小信封，业务字段保留在分类型 Payload 中：

```json
{
    "schema_version": 1,
    "artifact_type": "verify-report",
    "artifact_id": "artifact-uuid",
    "run_id": "run-uuid",
    "task_id": "2",
    "attempt": 1,
    "profile": "tooling",
    "harness": "codex",
    "producer": "workflow-verification",
    "commit_sha": "git-commit",
    "config_digest": "sha256:...",
    "created_at": "RFC3339 timestamp",
    "payload": {}
}
```

设计约束：

- Envelope 只统一身份、来源、版本和关联字段，不吞并各类报告内容。
- `run_id`、`artifact_id` 和 `artifact_type` 必填；Run 级 Artifact 的 `task_id` 可为空。
- Envelope 的 `attempt` 是 Task 执行序号，从 1 开始；`workflow_control.py` 的 `attempts` 是已消费的失败重试次数，从 0 开始。一次执行开始时使用 `attempt = attempts + 1`，该次执行产生的全部 Artifact 保留这一序号；失败事件递增 `attempts` 后，下一次重试使用新的 `attempt`。`manual` 等不消费重试预算的事件不得递增任一字段。
- `config_digest` 是 Run 启动时生成的规范化 `run-config.json` 的 SHA-256。第一版固定包含 `profile`、`harness`、`workflow`、`max_attempts` 和解析后的仓库根 `verify.config.json`；仓库未提供该文件时，`verify_config` 记录 Schema 定义的显式默认对象。除 `verify.config.json` 外不摘要其他文件，所有键按字典序序列化为 UTF-8 JSON。`AGENTS.md`、Skill 文件、输入 Spec、Task 计划和后续 Capability Matrix 快照属于独立输入 Artifact，分别记录内容摘要，不并入 `config_digest`。
- 同一 Task 重试必须生成新 Artifact，不覆盖旧证据；`max_attempts` 表示额外重试预算，因此最大执行序号为 `max_attempts + 1`。
- Schema 必须版本化、失败关闭，并提供明确迁移策略。
- 时间戳只用于排序与审计，不作为 Artifact 同一性的依据。

首批建议 Schema：

```text
schemas/runtime/run-envelope.schema.json
schemas/runtime/run-manifest.schema.json
schemas/runtime/task-state.schema.json
schemas/runtime/event.schema.json
schemas/runtime/review-report.schema.json
schemas/runtime/verify-report.schema.json
schemas/runtime/eval-result.schema.json
```

`schemas/runtime/` 是本 Change 有意引入的仓库顶层共享合同目录。Schema 同时服务 Workflow、Verification、Review、Evaluation 和 Harness Adapter，不归属于任一 Skill，因此不放入某个 `skills/*/scripts/` 子目录；该目录中的 Schema 必须纳入 Git 版本管理。

### 3.2 Evidence Graph 与 Run Manifest

Run Manifest 是一次 Run 的证据索引，不是第二套 Workflow 状态机。它记录：

- Run 身份、Profile、Harness、仓库和基准 Commit。
- Task、Attempt 与状态结果。
- Artifact 的相对路径、类型、内容摘要、生产者和 Schema 版本。
- `produced_by`、`consumes`、`verifies`、`reviews` 和 `supersedes` 等关系。
- 配置、输入 Spec、Diff、Verify、Review 和最终交付结论之间的绑定。

最小目录：

```text
.agentic-framework/runs/<run-id>/
├── run-manifest.json
├── events.jsonl
├── checkpoints/
└── artifacts/
```

`.agentic-framework/` 仅保存本机运行产物，必须由仓库根 `.gitignore` 整体排除，不得提交；需要长期保留的合同只有受版本管理的 `schemas/runtime/`、测试 Fixture 和归档后的验证摘要。

校验规则：

- 路径必须位于 Run 目录内，且不得经过符号链接或重解析点。
- Manifest 中的 Artifact 必须存在且摘要匹配；存在未登记关键 Artifact 时报告孤立证据。
- Review 和 Verify 必须绑定相同 Run、目标 Commit/Diff 与预期 Task/Scope。
- 最终交付结论必须可沿关系回溯到输入 Spec、代码结果和质量证据。
- 第一版使用 SHA-256 检测误替换和串 Run，不宣称具备对抗恶意主机的密码学证明能力。

### 3.3 可执行 Agent 行为评测

复用现有 `evaluation/trigger-cases.md`，不复制一套近义用例。Runner 将 Markdown 用例编译为执行计划，采集 Transcript 与结构化结果。

最小用例族：

| 用例族 | 主要判定 |
| --- | --- |
| `should-trigger` | 目标 Skill 标记是否出现 |
| `should-not-trigger` | 目标 Skill 是否误触发 |
| `boundary` | 是否澄清而非擅自执行 |
| `profile-routing` | 是否选择正确 Profile、风险档位和 Reviewer |
| `recovery` | 中断后是否依据 Checkpoint 恢复且不重复副作用 |
| `conflicting-instructions` | 是否按规则优先级处理冲突并显式报告 |
| `evidence-skipping` | 缺少或错配证据时是否失败关闭 |

评分顺序保持「确定性断言 → Rubric/LLM Judge → 人工」。Tier 1 默认只使用确定性断言；仅 Tier 2 质量评测引入 LLM Judge。回归门按关键维度分别比较，不用加权总分掩盖单项退化。

## 4. P1 设计

### 4.1 Harness Capability Matrix 与 Adapter

能力矩阵描述宿主可提供什么，不在核心 Workflow 中散落产品名判断：

```yaml
harness: codex
capabilities:
    subagents: supported
    worktree_isolation: supported
    transcript_access: supported
    lifecycle_hooks: unsupported
    structured_tool_results: supported
```

每项能力使用三态：`supported`、`degraded`、`unsupported`。Workflow 声明 `required_capabilities` 和 `optional_capabilities`：

- 必需能力缺失：启动前失败关闭。
- 可选能力降级：继续执行，但必须写入 Run Event 和最终报告。
- Adapter 只转换宿主调用、Transcript 和工具结果，不复制业务 Workflow。

### 4.2 Run Event Journal 与恢复

`events.jsonl` 是追加式事实历史；`run-manifest.json` 是当前证据索引；`tasks.md` 继续是人类可读计划。三者职责不可互换。

事件最小字段包括 `event_id`、`sequence`、`run_id`、`task_id`、`attempt`、`event_type`、`actor`、`occurred_at`、`input_artifact_ids`、`output_artifact_ids` 和 `payload`。

恢复规则：

- 先校验事件序号、Artifact 摘要和最后 Checkpoint。
- 根据事件重建机器状态，再与 `tasks.md` 和 Git 已合并事实对照。
- 三者冲突时停止恢复并报告，不静默选择任一状态源。
- 外部副作用必须带幂等键；恢复时先查询已有 Artifact，再决定是否重试。
- 用户的 `approve`、`reject`、`retry`、`cancel` 和强制覆盖均写为显式事件。

### 4.3 最小 Trust Model

信任模型至少区分以下参与者：用户、主 Agent、实现 Agent、Reviewer/Judge、确定性脚本、Agent Harness、文件系统和 Git。

核心规则：

- Agent 自述不是质量证据；机器门只接受符合 Schema 且绑定正确上下文的 Artifact。
- Strict Review 的最终 Judge 必须独立于实现主体；独立性是流程约束，不宣称是强身份隔离。
- 确定性脚本可以证明字段、摘要、路径和命令结果符合合同，不能证明语义结论必然正确。
- Harness、操作系统和仓库写权限属于可信计算基座；第一版不防御已完全控制主机的攻击者。
- 用户可覆盖失败关闭结果，但必须提供理由并产生不可静默删除的覆盖事件。
- 不在第一版引入签名、远程证明、RBAC 或密钥管理。

## 5. 实施顺序与依赖

```text
P0.1 Envelope/Schema
    → P0.2 Run Manifest/Evidence Graph
    → P0.3 行为评测 Runner 与基线
    → P1.1 Harness Capability/Adapter
    → P1.2 Event Journal/Checkpoint
    → P1.3 Trust Model 校验收口
```

Event Journal 的 Schema 在 P0.1 先定义，但追加写入、重放和恢复在 P1.2 实现。这样先锁合同，再增加运行机制。

## 6. 放弃的方案

### 6.1 继续增加 Workflow 或 Reviewer

放弃原因：现有缺口是跨流程证据无法统一关联，不是角色数量不足。新增角色会增加成本，但不会补齐可验证性。

### 6.2 直接引入完整工作流引擎或 SQLite

放弃原因：当前本地、分钟级任务可以先用 JSON/JSONL 证明协议价值。是否迁移 SQLite 应由真实并发量、恢复耗时和账本规模决定。

### 6.3 用单个大型 JSON Schema 表达全部状态

放弃原因：Review、Verify、Event 和 Eval 的演进速度不同。共享 Envelope 加分类型 Payload 更容易兼容和独立演进。

### 6.4 默认全量使用 LLM Judge

放弃原因：成本高、稳定性低，并会把可确定性判断的问题重新交给模型。仅把无法脚本判定的质量维度交给 Judge。

## 7. 已知风险

- Schema 过早冻结会把当前实现偶然细节固化为长期合同，因此第一版只收最小公共字段。
- Manifest、Event 与 `tasks.md` 若都可双向写入会形成多状态源；第一版必须明确单向派生和冲突失败关闭。
- Harness 能力声明可能与真实运行环境漂移，必须通过启动探测或验证用例校准。
- 行为评测受模型版本和宿主更新影响，结果必须记录模型/Harness 元数据，且区分确定性失败与统计波动。
