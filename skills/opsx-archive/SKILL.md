---
name: opsx-archive
description: OpenSpec 变更归档。将 openspec/changes/<change-name>/ 整目录移动到 openspec/changes/archive/YYYY-MM-DD-<change-name>/。由 /opsx-archive 命令触发。
---

> 输出一行：`Using opsx-archive`

# OpenSpec 变更归档

## 触发条件

- 用户执行 `/opsx-archive`
- 当前变更的代码已合入主干，或用户明确确认变更已完成

---

## 工作流程

### Step 1：确认变更目录

在 `openspec/changes/` 下列出所有活跃变更（排除 `archive/` 子目录），让用户选择要归档的变更：

```
当前活跃变更：
1. add-dark-mode
2. fix-auth-timeout

请问要归档哪个变更？
```

如果当前上下文已有明确的变更目录（如用户在该目录下工作），直接使用，无需询问。

### Step 2：确认归档

展示变更摘要，请用户确认：

```
即将归档：add-dark-mode

  文件：proposal.md、design.md、tasks.md、specs/ui/spec.md

归档后目录将移动到：
  openspec/changes/archive/2026-06-21-add-dark-mode/

确认归档？（y/n）
```

### Step 3：执行归档

用户确认后，移动目录（加当天日期前缀）：

```bash
mkdir -p openspec/changes/archive
mv openspec/changes/<change-name> \
   openspec/changes/archive/$(date +%Y-%m-%d)-<change-name>
```

> 归档状态由**目录位置**表达：在 `openspec/changes/` 下即活跃，移入 `openspec/changes/archive/` 即已归档，不维护单独的状态文件。
> 归档只移动目录，**不把增量规范合并到任何中央库**——本工作流不维护中央真相库（见 `opsx-project-knowledge`）。

### Step 4：输出归档报告

```
✅ 归档完成

  变更：add-dark-mode
  归档路径：openspec/changes/archive/2026-06-21-add-dark-mode/
```

---

## 强制规则

1. **必须用户确认后才执行移动**：不得静默归档
2. **只归档 `openspec/changes/` 下的目录**：不操作其他路径
3. **归档目录名格式**：`YYYY-MM-DD-<change-name>`，日期为执行归档当天
