# Proposal: 简化默认执行流程，收窄 Runtime 使用范围

**作者**：Codex（依据用户讨论整理）
**日期**：2026-10-03
**变更**：2048-native-first-runtime-simplification
**状态**：Archived

## 1. 背景

### 1.1 问题描述

框架需要帮助 Agent 完成开发、验证和交付。完整 Runtime 额外提供输入快照、事件日志、产物关联、宿主探测和 Trust Gate，但当前将严格审查、并行 Worktree 和长任务恢复都作为自动升级条件，日常开发因此承担了较重的协议成本。

此前讨论 SVN 支持时，方案一度扩展到双向 Git/SVN 同步和 Runtime Schema 重构。用户确认应先评估 Runtime 的必要性，优先简化默认流程。本次设计取代尚未落盘的“扩展 SVN Runtime”方向。

### 1.2 现状分析

核对基准：Git `00355a9`。以下为当前实现，尚未被本方案改变：

- `skills/workflow-code-generation/scripts/workflow_control.py` 的 `select_execution_route` 将 strict、并行 Worktree 写入、长任务恢复、跨宿主验证、审计要求中的任一项映射为 Runtime。SVN 在 CLI 层被强制降级。
- DAG、任务状态、阻塞传播和恢复规划已经可独立使用；`scripts/runtime_workflow.py` 再增加 Run 初始化、输入快照和交付证据组织。
- `skills/workflow-code-generation/scripts/check_delivery.py` 的 Native 路径在 Tooling 下接受 standard integration Review，Production 已接受 strict 六字段报告，Fast-Path 兼容别名接受 lightweight；现有报告不能证明独立 Judge 或内容绑定。普通工作区检查直接调用 Git，Scoped Delivery 才有 SVN 分支。
- `schemas/runtime/run-envelope.schema.json` 要求 Git `commit_sha`，Runtime 不支持纯 SVN。
- `skills/project-init/SKILL.md` 已提供“Git + SVN”，会初始化本地 Git，但没有持续双向同步实现。这不等于成熟桥接支持。
- project-init 也已提供“纯 SVN”，不创建 Git，初始化产物逐路径 `svn add` 后保持未提交。本方案调整现有模式的推荐与探测，并补齐后续验证/交付闭环，不重建纯 SVN 初始化。
- 文档存在需显式处理的差异：下放执行指南仍写“strict 必定升级”、最终复审“最多两轮”，主 Review Skill 已为十轮；project-init 仍提 OPSX，而当前入口已统一为 workflow-*。本方案记录这些差异，实施时统一，当前不把历史描述当作实现事实。

### 1.3 主要使用场景

1. Git 或 SVN 单人、单 Agent 的日常修复与功能开发。
2. 已有明确任务依赖，需要分波、隔离失败或恢复中断的 Git 开发。
3. 高风险修改需要独立严格审查，但没有完整执行审计要求。
4. 明确需要 Run 证据链、事件回放或跨宿主能力审计的高级任务。

## 2. 目标

- 所有常规任务默认 Native Delivery；复杂度、风险、并行和中断不自动要求 Runtime。
- 将审查强度、执行辅助能力和 Runtime 证据要求分开决定。
- 保留机器验证、审查独立性、批准边界、失败隔离、知识影响检查与真实完成声明。
- 为纯 SVN 提供可用的原生串行开发与交付流程，不引入 Git。
- 完整 Runtime 保留为显式选择的高级路径，已有 Run 继续按原合同完成。

### 2.1 非目标

- 不实现 SVN Runtime、Git/SVN 双向同步或自动 git-svn 初始化。
- 不删除 Runtime 实现和历史证据，不把已有 Run 降级成 Native。
- 不建设调度服务、事件数据库、远程 Agent 平台或新的通用插件体系。
- 不取消 Production 治理门，不把“减轻流程”解释为降低审查档位。
- 不在本次方案阶段修改执行代码、Schema、项目安装配置或正式规则。

## 3. 需求概览

### 3.1 功能性需求

- R1：默认只执行需求/任务、实现/测试、Verify、Review、交付检查；请求即计划的轻量任务继续免 proposal/tasks。
- R2：Native 接受符合档位要求的 lightweight、standard 或 strict Review；strict 保留五维审查与独立 Judge。
- R3：DAG、Git Worktree、任务委派和状态恢复按实际需要启用；单个串行任务允许主 Agent 直接完成。
- R4：完整 Runtime 仅由明确选择或明确的项目审计策略启用；指定但不支持时报告原因，不能静默降级。
- R5：SVN 原生路径区分“本地已验证待提交”和“已提交指定 revision 并验证”；svn commit 需要明确授权。
- R6：更新、合并或手工编辑改变已验证内容后，原通过结果不能直接用于新内容。
- R7：初始化识别现有 VCS，SVN 默认保留原生模式；旧混合仓库显式确认后端，不自动改造或删除。
- R8：已有 Git Native、Production 和 Runtime 证据有明确兼容策略，升级不改写历史产物。

### 3.2 非功能性需求

- 默认路径不调用 init-run、Harness 探测或 Trust Gate，不生成 Manifest、Journal、Envelope。
- 新增规则优先在已有验证与交付入口实现；不再建设一套平行状态系统。
- VCS 查询错误与发现代码违规分别报告；工具缺失、网络失败和未知状态不能当作通过。
- 所有本地改动和既有未跟踪文件可追踪、可保留；不为获得干净状态自动清理用户内容。

### 3.3 验收标准

- A1：Git 的 standard、strict、并行 Worktree、普通中断恢复，在未显式要求 Runtime 时均选 Native。
- A2：strict Native 缺独立 Judge、P0/P1 未清零或报告与当前内容不匹配时不能通过；Production 不接受 lightweight。
- A3：无 Runtime 的串行任务不要求子 Agent、波次计算或宿主探测；具有任务文件时仍遵守批准和依赖约束。
- A4：纯 SVN 完成更新、改动、Verify、Review 后，可输出待提交状态；未经授权无服务器写入。
- A5：SVN 提交后以确切 revision 检查项目内容；更新冲突、提交结果不明或版本验证失败时不会输出已交付。
- A6：已有 Runtime v1 继续校验；显式 Runtime 在 SVN 上返回能力不支持，既不初始化 Git，也不降级为低保证结果。
- A7：新 Native 正常路径不依赖 Runtime 模块执行副作用；现有 Schema、报告和评测升级有对应兼容测试。
- A8：文档中的路由、十轮复审、当前 workflow-* 入口与代码一致；主 Skill 不重复承载高级 Runtime 细节。

## 4. 知识影响

实施通过后更新以下长期知识，Draft 阶段不提前改写当前事实：

- `openspec/specs/backend/framework/workflow-control/overview.md`：可选执行能力、默认路由与恢复。
- `openspec/specs/backend/framework/quality-gates/overview.md`：Native strict、SVN 待提交与正式交付。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：Profile 与执行路径解耦。
- `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` 和 `trust-model.md`：显式启用条件及可声明边界。
- `openspec/specs/backend/framework/install-agentic-framework/overview.md`：项目初始化与 VCS 选择。

## 5. 参考资料

当前事实来自上述实现及 `scripts/test_workflow_control.py`、`scripts/test_check_delivery.py`、`scripts/test_profile_contracts.py`、`scripts/test_runtime_workflow.py`、`scripts/test_workspace_residue.py`。详细设计、实施阶段与外部资料见同目录 `design.md`。
