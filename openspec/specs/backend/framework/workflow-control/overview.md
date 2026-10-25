# Tooling 控制流概览

## 职责

Tooling 控制流把 `tasks.md` 作为唯一持久状态，通过确定性脚本计算 DAG 波次、判断可调度任务、校验状态迁移、传播阻塞并生成中断恢复计划。它不维护独立数据库，也不承担 LLM Code Review。

当前行为以 `workflow-code-generation` Skill、控制脚本和测试为准，本文件只提供稳定入口。

## 主链路与路径边界

`workflow-code-generation` 默认直接进入 Native Delivery；只有存在显式 Runtime 需求（`--execution-mode runtime`、项目硬性审计要求或跨宿主验证）时才调用 `workflow_control.py ... route`：

```text
proposal.md / tasks.md 获批
    → lint_spec.py / lint_task_deps.py
    → 默认直接 Native Delivery；显式 Runtime 需求时 route
        ├── Native Delivery
        │   → 仅并行分支、非线性依赖或恢复时 waves / dispatchable
        │   → 单 Task / 纯串行链直接 event start
        │   → Task 实现、测试、独立 Verify、quality_passed
        │   → merge_success / merge_failure
        │   → 集成 Review → check_delivery.py --native-delivery
        └── 完整 Runtime Run
            → init-run → waves / dispatchable
            → Task 实现、测试、Run-bound Verify、quality_passed
            → merge_success / merge_failure
            → Run 级 Review → check_delivery.py --run-dir → Trust Gate
```

`waves`、`dispatchable`、状态迁移、阻塞和恢复不是完整 Runtime 专属能力：只有并行分支、非线性依赖图或中断恢复需要时才调用 `waves` / `dispatchable`。单 Task 或纯串行链直接以 `event start` 启动下一任务，依赖和 Verify 配置选择仍由该命令失败关闭。

路由只由显式模式与硬性要求决定（change 2048）：`select_execution_route` 以 `execution_mode: native|runtime` 为主输入，未指定时默认 `native-delivery`；`strict` 风险、并行 Worktree 写入与长任务恢复不再自动升级——strict 走 Native strict Review（独立 Judge），并行/恢复按需使用隔离与恢复规划，均不初始化 Run。明确 Runtime 需求只有三类：显式 `--execution-mode runtime`、项目硬性审计要求 `--audit-required`（编排方从项目约束读取后显式传入，不从风险、复杂度或 Profile 名推断）、跨宿主验证 `--cross-host-capability-verification`；命中且 VCS 为 Git 时输出 `runtime-run`，`runtime_upgrade_reasons` 只记录实际触发的要求。硬性要求与 `execution_mode=native` 冲突、或 Runtime 在 SVN／未知 VCS 下不受支持时，路由以非零退出拒绝（不再像旧行为那样把 SVN 强制降级为 Native 并仅在 stderr 提示）；`--parallel-worktree-write` 与 `--long-task-recovery` 在一个兼容版本内仍接受，只表示执行需求。VCS 探测经公共接口 `scripts/vcs.py`（`inspect_workspace`）：Git 与 SVN 并存且未显式传 `--vcs-backend git|svn` 时 route/recover 拒绝隐式选择，不再 Git 优先；`recover` 只读核对 tasks、工作区与验证事实，SVN 工作副本按串行写入恢复，更新/提交只由明确的工作流步骤执行。控制器禁止为 Native Delivery 伪造 Run Context。

## 状态与恢复

- `waves` 对并行或非线性依赖图做稳定拓扑分波；`dispatchable` 只返回依赖均已完成的未开始任务。单 Task 或纯串行链不调用两者，改由 `event start` 校验前置依赖后直接启动下一任务。
- `workflow-code-generation` 的步骤 1 路由成功后，无论 `tasks.md` 是否预存，都必须先检查仓库根 `verify.config.json`；缺失时立即暂停，要求用户明确选择「初始化」或「跳过」，不得等到任务确认或 dispatch 才首次询问。对 `tasks.md` 驱动的委派调度，`dispatchable`、`recover` 和 `event <id> start` 继续失败关闭，直到任务区之前存在该用户选择的 `verify_config_decision`。用户先运行 `/verify-config` 实际生成配置后，以 `verify-config-decision --choice initialize --write` 记录「初始化」；或者在配置仍缺失时，以 `verify-config-decision --choice skip --write` 记录「跳过」。配置存在时不要求该记录；「初始化」记录对应的配置后来被删除时，调度再次阻断。
- 状态迁移由事件表约束；失败默认最多修复 2 次，耗尽后进入「需人工」（`workflow_control.py:140-251`）。
- `quality_passed` 只进入待合并阶段，不直接把任务标为完成；只有 `merge_success` 才完成任务（`workflow_control.py:174-183`）。
- `recover` 同时使用 `tasks.md` 状态和调用方提供的已合并事实；两者矛盾时失败关闭（`workflow_control.py:288-347`）。
- 写状态使用锁和原子替换，避免并发写入静默覆盖；锁超时属于可报告错误。锁统一位于仓库根 `.agentic-framework/locks/`，文件名是目标 `tasks.md` 规范化绝对路径的 SHA-256 摘要，不同仓库或 Change 不共享锁名。旧相邻 `.tasks.md.lock` 仅在已存在时兼容加锁读取并提示迁移，不自动删除或覆盖。

## 升级与批准（change 2039）

- 任务声明 `- Escalation: <条件>` 后，`event escalate` 把任务从 `进行中` 暂停为「待批准」：持久化写回规范态 `需人工`（原因前缀 `待批准 <条件>`）加 `control_stage: awaiting_approval`。「待批准」只是执行期内部态，读侧规范值恒为五个，`parse_state` 不接受 `待批准`。
- 恢复转移是 `event approval_granted`：要求任务块内 `- Approval: granted (<条件>)` 且条件集合与 `Escalation` 一致；缺失、`pending`、条件非法、条件不一致、声明缩进或列表错位，全部失败关闭（与 OPSX053 方向对齐）。恢复后回到 `进行中`。
- `merge_success` 前的批准门：命中升级条件的任务必须已有 granted 证据；头部声明 `> 批准模式: per-task` 时每个任务都需要（缺省 `risk-triggered` 只看声明了条件的任务）。未声明任何升级条件的执行路径不经过批准门（零触发等价）。
- 升级条件与批准模式词表逐项抄录 Production（`validate_change.py:102-113`），两侧集合相等有测试断言。
- 传播行为：待批准（`需人工`＋`awaiting_approval`）与失败需人工一样阻塞下游、不被 `dispatchable` 派发；`recover` 对其输出 `await_approval` 动作（与 `manual` 区分）。
- 词表事件只加新分支：`escalate`／`approval_granted` 两个新事件与两个新转移，既有事件与转移未改。

## 治理守卫与转移的关系（change 2043）

- 守卫只增前置条件，不新增、不删除、不重定向转移（门为叠加）：`_VALID_TRANSITIONS` 与 change 2043 交付前基线逐字节相同，是结构性约束而非约定。
- 挂载点统一为 `guard_errors`：`start` 前挂 Plan 总门（production 下调 `validate_change` plan 阶段，整体守卫不拆散），`merge_success` 前挂逐任务 Review 守卫（按 `review_profile` 逐任务触发，禁止统一收尾）；2039 的批准门在前，2043 的守卫在后。
- 降级等价：`profile=tooling` 时守卫全部返回空，状态机行为与纯 Tooling 逐字节相同（事件序列基线比对＋change 2042 比对器「通过」）。
- Profile 取得：start／merge_success 事件经 `--governance-profile` 或 manifest 解析；无法取得失败关闭——不能确认当前不是 production 就不放行。

## 写路径统一（change 2044）

- `update_task_state` 是任务状态字段（`- 状态:`）与任务头完成标记（`[x]`／`[ ]`）的**唯一写者**：状态机写回时同步两者，消除 Skill 流程或人手改 `tasks.md` 状态的做法——状态变更必须经状态机命令。
- 写回经 `_atomic_write`（带锁、`os.replace` 原子替换），时机与原因随 `TaskDecision` 落盘；任务状态仍只在 `tasks.md`，不另建副本或第二事实源。
- 审计痕迹由版本控制历史承载（Git 提交历史、SVN 修订日志），不引入独立转移日志——后者会与 `tasks.md` 形成双事实源。
- `validate_change.py` 全程只读：写层合并后它仍是只读裁决器，只核对不写回；可审计性（判定可复现、不依赖自身写入）未下降。
- 写锁（`_try_lock`／`_unlock`）、attempts、`plan_recovery` 在单一执行链上行为不变，由既有用例与 change 2043 的事件序列基线共同回归。

## 质量证据边界

- `quality_passed` 始终要求 `verdict: PASS` 的 Verify 报告；Native Delivery 只接受独立 v2 报告（顶层 `schema_version: 2` 与 `subject_id`），旧 v1 不能作为新完成证据；完整 Runtime 额外要求 Run-bound Verify Artifact。
- Task 级不运行 LLM Review；全部任务合并后执行一次最终 Review。Native Delivery 按任务实际档位出 v2 集成 Review（任务声明 `strict` 时要求独立 Judge 与三项独立性声明）；完整 Runtime 的 Run 级 `strict` Review 由共享 `workflow-code-review` 绑定 Runtime Context。
- `check_delivery.py --native-delivery` 校验终态 Tasks、已归档 Proposal、档位匹配的集成 Review、独立 v2 Verify、知识影响与工作区状态，重算当前内容主体并核对 Review/Verify/当前三方一致后输出有界 Verdict。Git 工作区要求干净（`native-delivery-pass`）；Scoped Delivery 输出 `git-scoped-delivery-pass`（冻结范围与残留摘要入证据）；纯 SVN 的预期本地改动不适用 Git clean——无提交授权输出 `svn-pending-commit`（本地已验证待提交，不是正式交付 PASS），有确切 revision 且隔离核验通过输出 `svn-revision-verified`。`check_delivery.py --run-dir` 继续校验完整 Runtime 的 Manifest、Journal、Harness 与 Trust Gate。交付报告只能逐字引用成功命令的原始 stdout；缺少归档、有效 Artifact 或工作区证据时不得声明「交付门 PASS」。
- `merge_success` 只表示任务结果纳入本地集成内容，不等于 SVN 远程提交；正式交付由交付门按确切 revision 核验。
- 结构化报告只能证明产物存在且字段满足合同，不能替代语义正确性判断。

## 主要验证证据

- `scripts/test_workflow_control.py`：覆盖稳定分波、同波失败隔离、Verify 证据、状态迁移、阻塞、恢复、锁和原子写入。
- `scripts/test_check_delivery.py`：覆盖终态、归档状态、Git 干净、知识影响和 Review JSON 合同。
- `scripts/test_knowledge_management_e2e.py:109`：覆盖 Tooling 使用统一 Change Artifact 和控制器。
