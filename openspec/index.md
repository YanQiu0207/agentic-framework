# Agentic Engineering Framework 项目知识索引

本目录是当前项目的知识入口。知识仅用于辅助理解；当前实现必须以代码、Schema、配置、测试和运行证据核实，冲突必须显式报告。

## 项目概述

Agentic Engineering Framework 以一个 Shared Core 支撑两个独立生命周期：Production 使用 `opsx-*` 和阶段校验器，Tooling 使用 `workflow-*`、DAG、Worktree 和失败恢复。Commands 是用户入口，Skills 保存执行策略，Agents 负责语义审查，确定性脚本负责安装、状态、门禁、校验和 Telemetry。

## 导航

- [长期 Specs](specs/)
- [活跃 Change：建立机器可验证的 Agent 运行协议](changes/machine-verifiable-agent-runtime/)
- [已验证 Issues](issues/)
- [历史 Changes](changes/archive/)

## 任务路由

- 双 Profile、Shared Core 和整体架构：[`framework-unification.md`](specs/backend/engineering/tech/framework-unification.md)
- Tooling DAG、状态与恢复：[`workflow-control`](specs/backend/framework/workflow-control/overview.md)
- Production 阶段门、Review 与 Verification：[`quality-gates`](specs/backend/framework/quality-gates/overview.md)
- 项目知识、迁移和公共知识边界：[`knowledge-management`](specs/backend/framework/knowledge-management/overview.md)
- 安装、Manifest 与 Registry：[`install-agentic-framework`](specs/backend/framework/install-agentic-framework/overview.md)
- 会话指标与质量收敛分析：[`session-telemetry`](specs/backend/framework/session-telemetry/overview.md)

## 读取规则

- 先按任务类型定位相关条目，不默认扫描整个目录。
- 当前框架合同优先读取 `specs/backend/engineering/tech/`。
- 查询具体实现入口时读取 `specs/backend/framework/` 下的对应模块，再回到其 `source_paths` 核实。
- 历史 Change 只保存当时证据，不代表当前状态。
