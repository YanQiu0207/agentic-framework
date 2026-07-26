# Proposal: 缺少 Verify 配置时阻断任务调度（Quick Draft）

**作者**：Codex
**日期**：2026-07-26
**变更**：enforce-verify-config-dispatch-gate
**状态**：Archived

---

## 1. 问题与目标

### 问题

`workflow_control.py` 当前只依据任务状态和依赖关系决定是否可调度；`event start` 也能直接启动任务。`workflow-code-generation` 已要求缺少 `verify.config.json` 时等待用户选择初始化或跳过，但该规则未由控制流内核强制执行，委派执行可绕过用户知情确认。

### 目标

- 在 `tasks.md` 驱动的任务调度中，缺少仓库根 `verify.config.json` 且没有用户选择记录时，拒绝 dispatch。
- 同时保护 `dispatchable`、`recover` 中的可 dispatch 计划和 `event start`，避免通过不同命令绕过门禁。
- 提供唯一的控制流命令写入用户「初始化」或「跳过」记录。
- 「初始化」记录只在配置文件已经存在时允许写入；「跳过」仅在配置文件缺失时允许写入。

### 非目标

- 不把 `verify.config.json` 变为所有项目的强制文件。
- 不修改 `workflow-verification` 的无配置内置门禁能力。
- 不在代码任务中创建或修改 `verify.config.json`。

### 验收标准

- 缺少配置且没有记录时，`dispatchable`、`recover` 和 `event start` 均以非零状态失败，且不改写 `tasks.md`。
- 用户记录「跳过」后，无配置仓库可继续调度；用户记录「初始化」后，只有配置实际存在时可继续调度。
- 现有配置仓库的调度行为保持不变。
- `scripts/test_workflow_control.py` 和项目 Verify 通过。

## 2. 设计方案

### 2.1 整体方案

把选择记录持久化在 `tasks.md` 的任务区之前，使用固定字段 `verify_config_decision`。控制器在真正会产出或执行 dispatch 动作的 CLI 分支中检查仓库根配置与该字段，不满足条件即失败关闭。

### 2.2 核心组件

- `workflow_control.py`：解析与原子写入选择记录，校验记录与配置文件的一致性，并在调度入口前执行门禁。
- `scripts/test_workflow_control.py`：覆盖未决策阻断、两种有效记录和直接启动不可绕过。

### 2.3 主要接口或 API

新增 `verify-config-decision --choice initialize|skip --write` 子命令。它将选择写为 `初始化` 或 `跳过`，并在写入前校验相应前置条件。

### 2.4 关键权衡

- 选择存入 `tasks.md`，而非独立运行时文件：记录与被调度的任务计划一同归档，恢复时不依赖易丢失的本地状态。
- 只在委派调度入口执行硬阻断：保留无配置项目运行内置 Verify 的能力，不把可选配置误作全局必需条件。
- 「初始化」要求配置实际存在：避免仅记录意图就放行缺少自定义机器验证的任务。

## 3. 知识影响

- 修改 `openspec/specs/backend/framework/workflow-control/overview.md`，记录 Verify 决策门禁与命令合同。

## 4. 运维

- 阻断报错必须指出可运行的决策命令，便于操作者恢复。
