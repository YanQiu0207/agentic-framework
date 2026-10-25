# Agentic Engineering Framework 项目知识索引

本目录是当前项目的知识入口。知识仅用于辅助理解；当前实现必须以代码、Schema、配置、测试和运行证据核实，冲突必须显式报告。

## 项目概述

Agentic Engineering Framework 以一个 Shared Core 支撑两个独立生命周期：Production 与 Tooling 共用统一的 `workflow-*` 入口与状态机，差异由治理守卫承载。Commands 是用户入口，Skills 保存执行策略，Agents 负责语义审查，确定性脚本负责安装、状态、门禁、校验和 Telemetry。

## 导航

- [长期 Specs](specs/)
- [机器可验证的 Agent 运行协议](specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md)
- [已验证 Issues](issues/)
- [历史 Changes](changes/archive/)

## 近期变更

- [2054：变更调研结论落盘与实现参考传递](changes/2054-research-note-persistence/proposal.md)（调研落盘 `research.md`、任务级「实现参考」字段与编码入口通读接线；进行中）

- [2054：深模块、测试接点与只读架构改善](changes/archive/2054-2026-10-25-deep-module-architecture/proposal.md)（方法、设计／测试接线与存量调查入口；完整测试及安装生命周期已复验）

- [2052：以远程 main 为基线整合评测与 Runtime 修复](changes/archive/2052-2026-10-25-main-integration/proposal.md)（Native v2 与显式 Runtime、嵌套目录边界、跨平台验证及证据限制）

- [2048：简化默认执行流程，收窄 Runtime 使用范围](changes/archive/2026-10-05-native-first-runtime-simplification/proposal.md) · [设计与实施阶段](changes/archive/2026-10-05-native-first-runtime-simplification/design.md)（已实施并归档：默认 Native、显式 Runtime、纯 SVN 串行交付与 v2 证据链）

## 任务路由

- 深模块、测试接点与只读存量架构改善：[`architecture-improvement`](specs/backend/engineering/tech/architecture-improvement.md)

- 双 Profile、Shared Core 和整体架构：[`framework-unification.md`](specs/backend/engineering/tech/framework-unification.md)
- Tooling DAG、状态与恢复：[`workflow-control`](specs/backend/framework/workflow-control/overview.md)
- Production 阶段门、Review 与 Verification：[`quality-gates`](specs/backend/framework/quality-gates/overview.md)
- 项目知识、迁移和公共知识边界：[`knowledge-management`](specs/backend/framework/knowledge-management/overview.md)
- 安装、Manifest 与 Registry：[`install-agentic-framework`](specs/backend/framework/install-agentic-framework/overview.md)
- 会话指标与质量收敛分析：[`session-telemetry`](specs/backend/framework/session-telemetry/overview.md)
- Run Envelope、证据链、恢复与 Trust Model：[`machine-verifiable-agent-runtime`](specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md)

## 读取规则

- 先按任务类型定位相关条目，不默认扫描整个目录。
- 当前框架合同优先读取 `specs/backend/engineering/tech/`。
- 查询具体实现入口时读取 `specs/backend/framework/` 下的对应模块，再回到其 `source_paths` 核实。
- 历史 Change 只保存当时证据，不代表当前状态。

## 外部参考

- 同类框架对比、近两个月模型与平台动态、项目证据缺口及候选路线（2026-10-25 快照）：[`external-reference-agentic-landscape-2026-10.md`](specs/backend/engineering/tech/external-reference-agentic-landscape-2026-10.md)
- 多 Agent 协作样例（AWS sample-codex-agent-team）协议设计逐文件解读、维度级对比与补强点候选：[`external-reference-sample-codex-agent-team.md`](specs/backend/engineering/tech/external-reference-sample-codex-agent-team.md)
- HarnessX Agent Harness Foundry 的组合模型、轨迹驱动演化、模型共演化、证据边界及适配候选：[`external-reference-harnessx.md`](specs/backend/engineering/tech/external-reference-harnessx.md)
- Alibaba skill-up 的 Skill 评测、with/without 基线、对话式演进、与 HarnessX 的分层对比及试点候选：[`external-reference-skill-up.md`](specs/backend/engineering/tech/external-reference-skill-up.md)
- Matt Pocock Skills 的工程理念、使用方式、访谈来源与框架适配候选：[`external-reference-mattpocock-skills.md`](specs/backend/engineering/tech/external-reference-mattpocock-skills.md)

- Comet 流程编排状态机（rpamis/comet）的双工作流、源码核验机制、三层扩展模型、与本框架 27 skills 的迁移对照及共存策略：[`external-reference-comet.md`](specs/backend/engineering/tech/external-reference-comet.md)

- Agent 实验评测与 Review 首例（含四个经典 Bug 的普通组、standard 与 strict 实评）：[agent-evaluation](specs/backend/engineering/tech/agent-evaluation.md)
- Review 效果评测方法：[SWR-Bench 与 SWE-PRBench](specs/backend/engineering/tech/external-reference-review-evaluation-methods.md)
