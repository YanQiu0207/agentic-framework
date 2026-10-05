# Framework Unification Delta — Profile 与执行路径解耦

## MODIFIED Requirements

### Requirement：Profile 决定治理生命周期，不决定执行证据路径

治理 Profile（Production / Tooling）只选择生命周期与治理门强度（逐任务 Review、批准门、strict 集成下限等），不再隐含完整 Runtime Run 的启用条件：`strict` 风险、并行 Worktree 写入与长任务恢复在两个 Profile 下都默认 Native Delivery，Runtime 只经显式 `execution_mode=runtime`、项目硬性审计要求或跨宿主验证启用。Native strict Review（独立 Judge 与三项独立性声明）在两个 Profile 都是一等公民，不因无 Run 而构成降级。

#### Scenario：Tooling strict 不再要求 Run Context

Tooling 任务声明 `strict` 时走 Native strict Review；旧「strict 必须升级完整 Runtime」的限制移除，档位只决定审查强度与独立性要求。

#### Scenario：Production 证据门不因 Native 放宽

Production 的逐任务 Review、批准门与 strict 集成下限在 Native Delivery 下原样生效；交付证据按 v2 合同（Git clean / scoped / SVN 待提交与确切 revision）区分，不以「减轻流程」解释为降低档位。

#### Scenario：SVN 不再为 Runtime 引入第二套版本管理

纯 SVN 工作副本在两个 Profile 下都走原生串行开发与交付（待提交 / 确切 revision），不为获得 Runtime 证据而创建 Git 镜像或桥接；Runtime 在 SVN 上显式报 unsupported。

## Verification

`python -m pytest scripts/test_profile_contracts.py scripts/test_workflow_control.py scripts/test_check_delivery.py -q`；`python scripts/lint_skill_graph.py` 退出 0。
