# Tooling 控制流概览

## 职责

Tooling 控制流把 `tasks.md` 作为唯一持久状态，通过确定性脚本计算 DAG 波次、判断可调度任务、校验状态迁移、传播阻塞并生成中断恢复计划。它不维护独立数据库，也不承担 LLM Code Review。

当前行为以 `workflow-code-generation` Skill、控制脚本和测试为准，本文件只提供稳定入口。

## 主链路与路径边界

`workflow-code-generation` 只在可能命中 Runtime 升级条件时调用 `workflow_control.py ... route`；其余情况直接进入 Native Delivery：

```text
proposal.md / tasks.md 获批
    → lint_spec.py / lint_task_deps.py
    → 可能升级时 route；否则直接 Native Delivery
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

`waves`、`dispatchable`、状态迁移、阻塞和恢复不是完整 Runtime 专属能力：只有并行分支、非线性依赖图或中断恢复需要时才调用 `waves` / `dispatchable`。单 Task 或纯串行链直接以 `event start` 启动下一任务，依赖和 Verify 配置选择仍由该命令失败关闭。完整 Runtime 只在 `strict` 风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或明确审计要求命中时初始化 Run；无升级条件时直接 Native Delivery，不调用恒为 Native 的 `route`；控制器禁止为 Native Delivery 伪造 Run Context。

## 状态与恢复

- `waves` 对并行或非线性依赖图做稳定拓扑分波；`dispatchable` 只返回依赖均已完成的未开始任务。单 Task 或纯串行链不调用两者，改由 `event start` 校验前置依赖后直接启动下一任务。
- 对 `tasks.md` 驱动的委派调度，仓库根缺少 `verify.config.json` 时，`dispatchable`、`recover` 和 `event <id> start` 必须失败关闭，直到任务区之前存在用户记录的 `verify_config_decision`。用户先运行 `/verify-config` 实际生成配置后，以 `verify-config-decision --choice initialize --write` 记录「初始化」；或者在配置仍缺失时，以 `verify-config-decision --choice skip --write` 记录「跳过」。配置存在时不要求该记录；「初始化」记录对应的配置后来被删除时，调度再次阻断。
- 状态迁移由事件表约束；失败默认最多修复 2 次，耗尽后进入「需人工」（`workflow_control.py:140-251`）。
- `quality_passed` 只进入待合并阶段，不直接把任务标为完成；只有 `merge_success` 才完成任务（`workflow_control.py:174-183`）。
- `recover` 同时使用 `tasks.md` 状态和调用方提供的已合并事实；两者矛盾时失败关闭（`workflow_control.py:288-347`）。
- 写状态使用锁和原子替换，避免并发写入静默覆盖；锁超时属于可报告错误。锁统一位于仓库根 `.agentic-framework/locks/`，文件名是目标 `tasks.md` 规范化绝对路径的 SHA-256 摘要，不同仓库或 Change 不共享锁名。旧相邻 `.tasks.md.lock` 仅在已存在时兼容加锁读取并提示迁移，不自动删除或覆盖。

## 质量证据边界

- `quality_passed` 始终要求 `verdict: PASS` 的 Verify 报告；Native Delivery 只校验独立 Verify，不写 Run Artifact；完整 Runtime 额外要求 Run-bound Verify Artifact。
- Task 级不运行 LLM Review；全部任务合并后执行一次最终 Review。Native Delivery 消费 `standard` 集成 Review；完整 Runtime 的 Run 级 `strict` Review 由共享 `workflow-code-review` 绑定 Runtime Context。
- `check_delivery.py --native-delivery` 校验终态 Tasks、已归档 Proposal、标准集成 Review、独立 Verify、知识影响和 Git 工作区，并输出有界 Verdict。`check_delivery.py --run-dir` 继续校验完整 Runtime 的 Manifest、Journal、Harness 与 Trust Gate。交付报告只能逐字引用成功命令的原始 stdout；缺少归档、干净 Git 状态或有效 Artifact 时不得声明「交付门 PASS」。
- 结构化报告只能证明产物存在且字段满足合同，不能替代语义正确性判断。

## 主要验证证据

- `scripts/test_workflow_control.py`：覆盖稳定分波、同波失败隔离、Verify 证据、状态迁移、阻塞、恢复、锁和原子写入。
- `scripts/test_check_delivery.py`：覆盖终态、归档状态、Git 干净、知识影响和 Review JSON 合同。
- `scripts/test_knowledge_management_e2e.py:109`：覆盖 Tooling 使用统一 Change Artifact 和控制器。
