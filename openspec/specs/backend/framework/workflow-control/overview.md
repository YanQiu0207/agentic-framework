# Tooling 控制流概览

## 职责

Tooling 控制流把 `tasks.md` 作为唯一持久状态，通过确定性脚本计算 DAG 波次、判断可调度任务、校验状态迁移、传播阻塞并生成中断恢复计划。它不维护独立数据库，也不承担 LLM Code Review。

当前行为以 `workflow-code-generation` Skill、控制脚本和测试为准，本文件只提供稳定入口。

## 主链路

```text
proposal.md / tasks.md 获批
    → lint_spec.py / lint_task_deps.py
    → workflow_control.py waves
    → workflow_control.py dispatchable
    → Task 实现、测试和机器验证
    → quality_passed（必须校验 Verify JSON）
    → merge_success / merge_failure
    → 全局 Verification、一次 Run 级 Review
    → check_delivery.py
```

`workflow-code-generation` 要求中等及以上任务使用控制器构建波次，禁止另写手工分波或状态判断（`skills/workflow-code-generation/SKILL.md:98-129`）。

## 状态与恢复

- `waves` 对依赖图做稳定拓扑分波；`dispatchable` 只返回依赖均已完成的未开始任务（`workflow_control.py:123-137`）。
- 状态迁移由事件表约束；失败默认最多修复 2 次，耗尽后进入「需人工」（`workflow_control.py:140-251`）。
- `quality_passed` 只进入待合并阶段，不直接把任务标为完成；只有 `merge_success` 才完成任务（`workflow_control.py:174-183`）。
- `recover` 同时使用 `tasks.md` 状态和调用方提供的已合并事实；两者矛盾时失败关闭（`workflow_control.py:288-347`）。
- 写状态使用锁和原子替换，避免并发写入静默覆盖；锁超时属于可报告错误。锁统一位于仓库根 `.agentic-framework/locks/`，文件名是目标 `tasks.md` 规范化绝对路径的 SHA-256 摘要，不同仓库或 Change 不共享锁名。旧相邻 `.tasks.md.lock` 仅在已存在时兼容加锁读取并提示迁移，不自动删除或覆盖。

## 质量证据边界

- `quality_passed` 必须传入 Verify 报告，且报告 `verdict` 必须为 `PASS`（`workflow_control.py:111-120,531-618`）。
- Task 级不运行 LLM Review；Run 级 Review 由共享 `workflow-code-review` 执行。
- `check_delivery.py` 校验终态 Tasks、已归档 Proposal、Run 级 Review JSON、知识影响结论和 Git 工作区（`check_delivery.py:31-129`）。
- 结构化报告只能证明产物存在且字段满足合同，不能替代语义正确性判断。

## 主要验证证据

- `scripts/test_workflow_control.py`：覆盖稳定分波、同波失败隔离、Verify 证据、状态迁移、阻塞、恢复、锁和原子写入。
- `scripts/test_check_delivery.py`：覆盖终态、归档状态、Git 干净、知识影响和 Review JSON 合同。
- `scripts/test_knowledge_management_e2e.py:109`：覆盖 Tooling 使用统一 Change Artifact 和控制器。
