# 完善框架项目知识

**作者**：Codex
**日期**：2026-07-19
**状态**：Archived

## 1. 背景

当前 `openspec/` 已包含双 Profile、统一知识管理、安装器模块、架构决策和历史 Change，但对框架核心执行链的长期知识覆盖不均，部分已有条目尚未进入索引。新 Agent 仍需要跨 README、Skills、Agents、脚本和测试反复搜索，才能定位 Tooling 编排、Production 生命周期、质量门、知识管理与 Telemetry 的事实入口。

## 2. 目标

- 从源码、配置和测试建立框架核心链路的当前证据图。
- 修复长期 Specs、ADR 和历史 Change 的索引缺口。
- 为缺少模块知识的稳定核心链路增加最小 `overview.md` 与来源元数据。
- 增加框架架构总览，使 Agent 能从 `openspec/index.md` 渐进定位实现证据。

### 2.1 非目标

- 不修改框架代码、运行合同或工作流行为。
- 不逐个为所有 Skill、Command 或 Agent 建立独立知识文件。
- 不复制 README、历史 Change 或源码注释的正文。
- 不把未验证推断写入长期 Specs。

## 3. 验收标准

- 所有新增事实都有 `source_ref`、`source_paths`、源码位置或测试证据。
- `openspec/index.md` 能路由到架构总览、长期 Specs、Issues 和历史 Changes。
- 长期 Specs 与历史 Change 的索引覆盖现有目标条目。
- 模块知识覆盖安装分发、Tooling 编排、Production 质量门、Review 与 Verification、知识管理和 Telemetry。
- Markdown、Skill 图和全量测试通过。

## 4. 知识影响

- 命中：补充项目架构与模块级长期知识，修复索引遗漏。
- 不修改公共知识库，不产生跨项目知识晋升候选。
