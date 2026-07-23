# Proposal: 真实任务质量基准（Quick Draft）

**作者**：主会话
**日期**：2026-07-23
**变更**：2027-real-task-quality-benchmark
**状态**：Archived

## 1. 问题与目标

现有 Telemetry 能提取会话成本和 Review 轨迹，但首次 JSON 写入要求预建目录，且无法关联真实任务的验收和返工结果。

目标是自动创建 JSON 输出目录、提供 Bash 持续采集命令，并用真实任务结果按路由比较质量、返工和成本。

非目标是不把 Codex Adapter 伪装成能自动执行真实任务的评测器，也不以少量历史会话证明流程优劣。

## 2. 设计方案

保留转录后处理作为成本数据源；人工在开始和交付后填写结构化案例与结果；汇总器通过稳定的 `source`、`session` 键关联两类数据。七天观察期结束后，任务才能进入返工率分母。

## 3. 验收标准

- `--json` 指向不存在的父目录时成功写入。
- 文档提供 Bash 采集与报告命令。
- 基准工具拒绝无效路由、重复会话和缺失账本引用，并按路由汇总验收、返工、Review 和成本。

## 4. 知识影响

- 长期目标：`openspec/specs/backend/framework/session-telemetry/overview.md`。
