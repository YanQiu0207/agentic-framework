# Main 整合任务

### 任务 1：[x] 整合远程合同与本地能力
- 状态：完成
- depends_on: []
- review_profile: strict
- context_files: [proposal.md]
- verification: pytest scripts 与独立严格审核
- artifacts: workflow_control.py、合同测试、活跃知识和执行指南

### 任务 2：[x] 修复边界问题与补齐跨平台验证
- 状态：完成
- depends_on: [Task 1]
- review_profile: strict
- context_files: [proposal.md]
- verification: 嵌套目录负向回归、Linux 全量测试、信任链及需求符合度定向复审
- artifacts: 嵌套目录防护、跨平台测试 fixture、验证与审核报告

交付动作：备份并恢复用户本地改动、快进 main、正常推送及核对远程 SHA；执行状态由会话和 Git 记录单独报告。

## 知识同步

| 增量 | 目标 | 动作 | 状态 | 证据 |
| --- | --- | --- | --- | --- |
| proposal.md | openspec/specs/backend/engineering/tech/framework-unification.md | 同步 Native v2、显式 Runtime 与能力包边界 | Completed | 当前路由实现、合同测试与定向复审 |
| Runtime 路由合同 | openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md | 同步启用条件与证据声明边界 | Completed | 当前 SKILL、Runtime 路由与定向复审 |
| Review 合同 | openspec/specs/backend/framework/quality-gates/overview.md | 同步 strict 独立 Judge 与 v2 内容绑定 | Completed | native_delivery.py、报告示例及合同测试 |

索引：已在 `openspec/index.md` 增加本 Change 入口；上述长期文档原导航入口保留。

## 知识冲突

状态：Resolved。本地旧知识要求 strict、并行或恢复自动升级 Runtime，并禁止 Fast-Path；远程 `23d3473` 的路由实现及当前 Native v2 门禁允许独立 Judge 的 Native strict，Runtime 仅显式启用。按用户选择以远程行为为基线，已同步活跃知识；历史归档不改写。实现与本次活跃知识核对后无冲突。

## 实际 Diff 核对

已核对远程 `23d3473` 至整合提交的实际 Diff：保留评测框架、Runtime 修复和能力包门禁，不将用户 main 工作区未提交内容纳入提交。
