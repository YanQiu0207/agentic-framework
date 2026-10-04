# Runtime Spec Delta — 显式启用与能力边界

## MODIFIED Requirements

### Requirement：Runtime 只经显式选择启用

完整 Runtime Run 不再由 strict 风险、并行 Worktree 写入或长任务恢复自动进入：这些场景默认 Native Delivery（strict 走独立 Native strict Review，并行用 Worktree 隔离，恢复用 tasks/工作区/验证事实）。初始化 Run 的唯一入口是明确的 `execution_mode=runtime`、显式 `audit_required`（项目硬性审计策略，来源由编排方说明）或 `cross_host_capability_verification` 需求。

#### Scenario：策略冲突拒绝

项目策略要求 Runtime 而用户显式选择 Native 时，路由拒绝并要求先变更策略来源；一次模式选择不能覆盖强制策略。

#### Scenario：能力不支持拒绝

显式 Runtime 需求出现在 SVN 工作副本或 VCS 无法确定的环境中时，报告 unsupported 并非零退出；不初始化 Git、不降级为低保证 Native、不静默忽略需求。用户可去掉要求改用 Native 或更换环境。

#### Scenario：已有 Run 保持原路径

存在 Run Context 的任务恢复时保持原模式与既有证据合同（Runtime v1 Schema、Journal、Manifest、Trust Gate 均不变）；不从新版默认值重写历史。Native 中途确需 Runtime 时从新基准建立新 Run 并记录承接关系，不补造此前执行的审计证据。

### Requirement：Native 与 Runtime 的证据合同分离

Native v2 产物（Verify/Review/Verdict 的 `schema_version: 2` 与 `subject_id`）不携带 Runtime 字段（run_id、harness、config_digest、trust_gate 等），递归禁止；Runtime v1 Envelope 与 Run-bound Artifact 沿用既有 Schema 与校验入口。校验器按版本显式分派，旧校验器不误读新报告，新校验器拒绝未知版本。

## Verification

`python -m pytest scripts/test_runtime_schema.py scripts/test_runtime_workflow.py scripts/test_runtime_trust.py scripts/test_workflow_control.py -q`；路由矩阵由 `python scripts/delivery_route_fixture_runner.py` 锁定。
