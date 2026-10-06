# Workflow Control Delta — 显式执行路由

## MODIFIED Requirements

### Requirement：路由只由显式模式与硬性要求决定

`select_execution_route` 以 `execution_mode: native|runtime` 为主输入，未指定时默认 `native-delivery`。`strict` 风险、`parallel_worktree_write` 与 `long_task_recovery` 不再触发自动升级：strict 走 Native strict Review，并行/恢复按需使用 Worktree 隔离与恢复规划，均不初始化 Run。

明确 Runtime 需求只有三类：显式 `execution_mode=runtime`、项目硬性审计要求 `audit_required`（编排方从项目约束读取后显式传入，不从风险、复杂度或 Profile 名推断）、跨宿主验证 `cross_host_capability_verification`。命中任一且 VCS 为 Git 时输出 `runtime-run`，`runtime_upgrade_reasons` 只记录实际触发的要求。

#### Scenario：冲突与不支持失败关闭

`execution_mode=native` 与任一明确 Runtime 需求同时出现时，路由以非零退出拒绝（冲突），不得静默放宽项目约束。明确 Runtime 需求在 SVN 或未知 VCS 下同样拒绝（完整 Runtime 仅支持 Git），不再像旧行为那样强制降级为 Native 并仅在 stderr 提示；由用户决定去掉要求改用 Native 或更换环境。

#### Scenario：旧 flags 兼容

`--parallel-worktree-write` 与 `--long-task-recovery` 在一个兼容版本内继续接受，只表示执行需求；CLI 在选择 Native 时输出解释性说明。`--audit-required` 与 `--cross-host-capability-verification` 保留为明确 Runtime 需求输入，不静默忽略。旧返回字段 `path` 与 `runtime_upgrade_reasons` 保留。

### Requirement：路由评测矩阵锁定新优先级

`evaluation/delivery-route-fixtures.json`（schema 2）以真实 selector 执行固定矩阵：三档审查 × 并行/恢复 × 显式模式 × Git/SVN。冲突、SVN Runtime、未知 VCS 与非法模式均以 `expected.error` 断言显式失败；strict/并行/恢复无 Runtime 需求时断言 Native。`delivery_route_fixture_runner.py` 逐条比对并把不一致判 FAIL。

## Verification

`python -m pytest scripts/test_workflow_control.py scripts/test_delivery_route_fixture_runner.py scripts/test_downgrade_equivalence.py -q`；`python scripts/delivery_route_fixture_runner.py` 返回 PASS。
