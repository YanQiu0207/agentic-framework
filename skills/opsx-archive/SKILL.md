---
name: opsx-archive
description: OpenSpec 变更归档。将活跃 Change 整目录移动到带日期前缀的 archive 目录。由 /opsx-archive 命令触发。
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

### Step 3：执行 Archive 门禁

用户确认后，从当前 Skill 目录向上定位 `../../scripts/validate_change.py`，在移动目录前执行：

```bash
python <validator-path> --repo . --change openspec/changes/<change-name> --phase archive --archive-target openspec/changes/archive/YYYY-MM-DD-<change-name>
```

`--archive-target` 必须与下一步 `mv` 使用完全相同的实际目标路径，其中日期为执行当天。

- 退出码为 `0` 才能移动目录。
- 退出码为 `1` 时，按输出提示修正变更文档并重跑；禁止归档。
- 退出码为 `2` 时，停止并报告调用、路径或校验器错误；不得绕过。

### Step 4：执行归档

门禁通过后，移动目录（加当天日期前缀）：

```bash
mkdir -p openspec/changes/archive
mv openspec/changes/<change-name> \
   openspec/changes/archive/$(date +%Y-%m-%d)-<change-name>
```

> 归档状态由**目录位置**表达：在 `openspec/changes/` 下即活跃，移入 `openspec/changes/archive/` 即已归档，不维护单独的状态文件。
> 归档只移动目录，**不把增量规范合并到任何中央库**——本工作流不维护中央真相库（见 `opsx-project-knowledge`）。

### Step 5：输出归档报告

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
4. **禁止中央规范库**：不创建、合并或更新 `openspec/specs/`
