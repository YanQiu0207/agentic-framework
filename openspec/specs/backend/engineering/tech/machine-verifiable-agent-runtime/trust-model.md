# 最小 Trust Model

- **状态**：Active
- **适用范围**：Production 与 Tooling 共用的机器运行证据协议
- **当前验证入口**：`scripts/runtime_trust.py`

## 1. 结论

第一版 Trust Model 只证明「受版本约束的证据存在，且 Schema、路径、摘要、Run 绑定、事件历史、Harness 探测和流程独立性声明相互一致」。它不证明 Reviewer 或 Judge 的语义结论必然正确，也不抵御已完全控制主机的攻击者。

## 2. 参与者与信任边界

| 参与者 | 可执行职责 | 不直接信任的自述 | 机器约束 |
| --- | --- | --- | --- |
| 用户 | 批准、拒绝、重试、取消或覆盖机器门 | 聊天中的口头覆盖 | 必须写入带非空理由的 `user-*` 事件 |
| 主 Agent | 编排 Run、收集 Artifact、触发最终门 | 「任务已完成」「Review 已通过」 | 必须提交 Manifest、Journal、Checkpoint 和质量 Artifact |
| 实现 Agent | 实现、测试、机器验证和修复 | 自己对质量和完成度的判断 | Strict 最终裁决不得由同一 actor 完成 |
| Reviewer | 发现候选 Finding | Finding 一定成立 | 输出结构化 Review Artifact，由独立 Judge 裁决 |
| Judge | 裁决 Finding 和 Run 结论 | 语义裁决必然正确 | Strict Run 报告声明实现者、Judge 和流程分离依据 |
| 确定性脚本 | 校验字段、摘要、路径、绑定、命令结果和状态迁移 | 未执行检查所覆盖的行为 | 只按版本化合同失败关闭 |
| Harness Adapter | 探测宿主能力、转换调用和工具结果 | 静态能力声明等于当前事实 | 每个 Run 使用可执行探测，必需能力缺失时停止 |
| 文件系统与 Git | 保存 Artifact、提交和合并事实 | 在恶意主机上仍可信 | 属于第一版可信计算基座 |

## 3. 可信计算基座

第一版信任以下基座未被完全攻破：

- 运行确定性脚本的 Python 解释器与操作系统进程边界；
- Run 目录所在文件系统、Git 对象库和工作区读取结果；
- 被执行的 Harness Adapter 与 `verify.config.json` 中命令；
- 当前仓库内受 Git 管理的 Schema、脚本和活跃 Change。

任一基座被完全控制时，攻击者可同时替换 Artifact、摘要、脚本与输出；本模型不声称能发现该类攻击。

## 4. 强制约束

### 4.1 证据而非 Agent 自述

最终 Trust Gate 先执行 Manifest 全量校验，确认关键 Artifact 存在、位于 Run 目录内、摘要匹配且未串 Run。自由文本、聊天记录和 Agent 自述不能替代 Artifact。

### 4.2 Strict Judge 独立性

Run 级 Review 必须满足：

- `scope: run`、`review_profile: strict`；
- `verdict: PASS` 且 `p0_count`、`p1_count` 均为 `0`；
- `implementer_actor` 与 `judge_actor` 均非空且不同；
- `independence_basis: process-separated-agent`。

这是可审计的流程分离声明，不是强身份隔离。实现者若能完全控制主机，仍可能伪造 actor 字段。

### 4.3 Harness 能力漂移

静态 Capability Matrix 只提供统一词汇，不作为运行事实。最终门只接受：

- `evidence_source: runtime-adapter-probe`；
- `run_id` 和 `harness` 与 Manifest 一致；
- 必需能力当前探测结果均为 `supported`；
- 可选能力降级已形成可观察证据。

### 4.4 事件、恢复和用户覆盖

恢复只使用 `events.jsonl`、最后 Checkpoint、Manifest、`tasks.md` 与 Git 事实。事件序号必须连续，外部副作用必须使用幂等键。所有 `user-*` 事件必须由 `user` actor 提供非空理由；覆盖不会删除原失败证据。

## 5. 威胁与残余风险

威胁用例及测试映射见 `evaluation/runtime-threat-cases.md`。这些控制可以发现伪造但缺少独立性声明的报告、被替换 Artifact、串 Run、重复副作用、运行时能力漂移和静默覆盖。

以下结论不可由第一版证明：

- Reviewer 或 Judge 的语义判断正确；
- actor 字段对应强认证的不同自然人或安全主体；
- 已完全控制主机的攻击者没有伪造文件、进程、Git 或命令输出；
- 未在 `verify.config.json`、行为用例或 Harness 探测中声明的行为正确。

### Fast-Path 交付的有界裁决

局部低风险改动可走 Fast-Path 交付门（无 `--run-dir`）：校验 lightweight Review、机器验证报告、工作区干净与知识影响结论后输出 `fast-path-pass`。该裁决**不是** Run 级 Trust Gate PASS，仅证明上述四项本地检查通过；它显式不声明 `strict-independent-review`、`run-manifest-evidence-graph` 与 `harness-capability-probe`。任何要求独立审查或完整证据链的交付必须走 `--run-dir` 的 strict 路径，不得用 `fast-path-pass` 替代。

## 6. Skill 接入矩阵

当前仓库中，完整 Runtime 不是所有 Skill 的统一前置条件，而是由 `workflow-code-generation` 作为主编排入口强制接入：

| Skill | Runtime 要求 | 具体位置与作用 |
| --- | --- | --- |
| `workflow-code-generation` | 完整 Run 路径强制使用；低风险 Fast-Path 可不创建 Run | `SKILL.md:121` 要求 Phase 0 先执行 `workflow_control.py ... init-run`，冻结输入、探测 Harness、创建 Journal；`SKILL.md:128` 要求整体 Verify 传入 `--run-dir`；`SKILL.md:134` 以 `check_delivery.py --run-dir` 执行 Manifest、Journal、Harness 与 Trust Gate 校验。 |
| `workflow-code-review` | Run 级 Review 需要 Runtime Context | `SKILL.md:272` 要求调用方提供 `run-context.json`，并将 `run_id`、`profile`、`harness`、`commit_sha` 和 `config_digest` 写入 Review Envelope；缺少 Context 时不得生成可放行的旧式顶层 `PASS` JSON（该禁令适用于 Run 级；`scope: task` / `integration` 的 OPSX 豁免见本节下文）。 |
| `workflow-verification` | 支持接入 Runtime，但不是所有独立 Verify 场景都强制创建完整 Run | `scripts/verify.py` 支持 `--run-dir`、`--task-id` 和 `--attempt`，用于生成绑定到 Run/Task/Attempt 的 Verify Artifact；是否必须传入由上层 `workflow-code-generation` 的流程决定。 |

因此，当前最准确的调用链是：

```text
workflow-code-generation
    → workflow_control.py init-run
    → workflow-verification（Run 级 Verify）
    → workflow-code-review（Run 级 Review）
    → check_delivery.py
    → runtime_trust.validate_run（Trust Gate）
```

`workflow-code-review` 和 `workflow-verification` 是 Runtime 证据链的参与者，但当前没有证据表明它们各自的独立入口都必须无条件执行完整 Runtime。Fast-Path 是明确的例外：它只输出有界的 `fast-path-pass`，不能表述为完整 Trust Gate PASS。

OPSX Production 阶段门是另一类例外。`scripts/validate_change.py` 的 `delivery` 与 `archive` 阶段接受双格式 Review 报告：符合 `schemas/runtime/review-report.schema.json` 的 Envelope（裁决字段取自 `payload`，且顶层 `artifact_type` 必须为 `review-report`），或裁决字段取自顶层的旧式扁平 JSON；两种格式共用同一套 `verdict`、`p0_count`、`p1_count`、`scope`、`review_profile` 与 `round` 校验。无 Run Context 时，旧式扁平 JSON 的放行依据是 `validate_change.py` 的确定性校验与人审，不构成 Trust Gate PASS，也不声明 Run 绑定、Manifest 证据链或 Harness 能力探测。该豁免不适用于 `scope: run`：Run 级 Review 必须是 Envelope，并满足 4.2 节的 Strict 独立性要求。

### Claude Code、Runtime 与 Adapter 的关系

三者不是同一层的组件：

| 组件 | 所在层 | 主要职责 | 不负责的事情 |
| --- | --- | --- | --- |
| Claude Code | Agent Harness 与主编排会话 | 读取任务、派发 Task、调用工具、修改代码、运行测试并收集结果 | 不直接替代 Runtime 的 Manifest、Journal 和 Trust Gate 校验 |
| Runtime | 工作流控制与信任协议层 | 创建 Run Context，冻结输入，记录 Artifact 和事件，执行能力门、质量门与最终 Trust Gate | 不负责理解业务语义，也不证明 Reviewer 或 Judge 的结论必然正确 |
| Adapter | Runtime 与 Harness 之间的协议边界 | 以子进程 JSON 合同向 Runtime 报告当前 Harness 能力，并在协议需要时转换工具结果 | 当前实现不负责派发任务；任务由 Claude Code 主会话通过 Task 工具执行 |

当前调用关系为：

```text
Claude Code 主会话
    ├── 通过 Task 工具执行和编排任务
    └── 由 Runtime 启动 claude_code_adapter.py 进行能力探测

Runtime
    ├── 读取 Adapter 返回的 Capability Matrix
    ├── 创建并校验 Run Context、Manifest、Journal 和 Artifact
    └── 执行最终 Trust Gate
```

因此，Adapter 不是「另一个 Claude Code」，也不是当前任务的执行引擎；它是一个可执行的协议桥，使 Runtime 能够把 Claude Code 的宿主能力转换成可校验、可记录的运行证据。当前实现的事实来源是 `scripts/claude_code_adapter.py`、`scripts/harness_runtime.py` 和 `scripts/runtime_workflow.py`。

## 7. 迁移说明

1. 旧 Review Artifact 仍可按 Schema 解析，但缺少 `scope: run` 或 actor 独立性声明时不能通过最终 Trust Gate。
2. 新的 Strict Run Review 同步填写 `implementer_actor`、`judge_actor` 和 `independence_basis`。旧 Artifact 不原地改写。
3. Harness 探测命令增加 `--run-id <run-id>`。无 Run 绑定的旧探测报告只作诊断信息，不能用于最终放行。
4. 每次 Run 把实际探测报告作为 `input_type: capability-matrix` 的快照登记到 Manifest，不能只引用仓库静态声明。
5. 归档前由主编排执行 Run 级独立 Strict Review；通过后把本候选同步到长期目标路径并更新相关索引，再归档 Change。

## 8. 当前收口状态

- Task 级实现与端到端威胁测试：由 Task 7 完成并提供机器验证证据。
- Run 级独立 Strict Review：等待主编排在 Tasks 2～7 合并后执行。
- 长期知识同步、Proposal 状态变更与 Change 归档：等待 Run 级 Review 通过后执行。
- 归档记录与最终交付门：本 Task 不生成，避免用实现者自审替代独立裁决。
