# 002：统一项目知识库与 Change Artifact 结构

**状态**：Accepted

## 背景

Production 使用 `openspec/changes/`，Tooling 使用 `docs/design-docs/`，两个 Profile 的项目产物结构不同。当前 Production 不维护项目长期 Specs，归档只移动 Change；当前 Tooling 则通过 ADR、架构快照、Feature Spec 和 Issues 分散沉淀项目知识。这使 `project-init`、`project-knowledge`、Workflow、验证器和迁移规则长期存在两套契约。

两篇参考实践分别证明了「总览 → 业务域 → 服务 → 自动与人工知识」和「长期 Specs + 单次 Changes + Delta 归档」的可行方向，但它们也明确承认自动治理、跨项目迁移和效果评估仍在演进。

## 决策

- Production 和 Tooling 统一使用项目根 `openspec/`。
- 项目长期辅助知识放入 `openspec/specs/`，单次变更放入 `openspec/changes/`，已验证故障放入 `openspec/issues/`。
- 长期 Specs 按 `business/`、`frontend/`、`backend/` 和 `common/` 组织；端内知识再按业务域与模块或服务分层，并分离自动生成内容与 `custom/` 人工内容。
- Change-local `specs/` 使用长期 Specs 的镜像相对路径和 Delta 语义，归档前只把已验证且值得长期保留的内容合并回长期 Specs。
- 项目知识与跨项目公共知识严格分域，未确认候选不得进入公共仓库。
- 知识仅用于辅助理解；当前实现以代码、Schema、配置、测试和运行证据核实。冲突必须显式报告。
- 两个 Profile 只统一 Artifact 和知识生命周期，不统一审批、Review、DAG、Worktree 和恢复策略。
- `project-init` 支持项目内存储或外部私有目录加链接，但项目逻辑入口始终为 `<project>/openspec/`。

## 放弃的方案

### 继续维护两套项目目录

该方案改动最小，但会继续扩大 Profile 切换、Workflow 接线、验证器和知识沉淀规则的重复成本，因此不采用。

### 只把现有 Tooling 目录搬入 `openspec/`

该方案只是把 `knowledge/`、`adr/` 和 `arch-snapshots/` 换位置，没有形成参考资料中的长期 Specs、Change Delta 和归档复利闭环，因此不采用。

### 只保留 Change，不维护长期 Specs

该方案能避免知识与代码争夺事实源，但项目的业务规则、人工上下文和跨任务经验只能散落在 Archive，下一次任务难以定向消费，因此不采用。

### 自动把所有 Change 内容合并进长期 Specs

该方案会把临时实现细节和中间草案带入长期知识，造成知识膨胀和错误复用，因此不采用。

### 把项目知识集中到跨项目公共目录

该方案会让其他项目检索到当前项目专属知识，破坏作用域隔离，因此不采用。外置项目知识也必须位于项目私有位置。

## 后果

- 需要修改两个 Profile 的 Workflow、模板、验证器和安装归属，不是小范围文档调整。
- 原「禁止 `openspec/specs/`」和「Archive 只移动目录」合同已由统一知识管理合同替代。
- Tooling 现有 `docs/design-docs/`、`docs/adr/`、`docs/arch-snapshots/` 和 `docs/issues/` 需要安全迁移，旧内容不能直接删除。
- 归档增加知识影响检查和 Delta 合并成本，但可以减少跨任务重复理解。
- 长期知识可能与代码漂移，因此必须保留来源版本、按需复核和冲突报告机制。
- 外置链接提高物理存储灵活性，但必须明确版本管理、备份和恢复方式。

## 适用条件

- 项目接受 Markdown、Git 和分层索引作为首版知识载体。
- 项目把知识视为辅助上下文，而不是当前实现事实源。
- Production 和 Tooling 愿意共享 Artifact 协议，同时保留各自执行策略。
- 跨项目公共知识的写入继续由用户显式确认。

## 相关文档

- [项目知识库与跨项目公共知识库统一方案](../knowledge-management.md)
- [历史实施任务清单](../../../../../changes/archive/2026-07-19-unified-knowledge-management/tasks.md)（历史归档链接，保留原路径）
