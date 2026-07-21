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
1. 1-add-dark-mode
2. 2-fix-auth-timeout

请问要归档哪个变更？
```

如果当前上下文已有明确的变更目录（如用户在该目录下工作），直接使用，无需询问。

### Step 2：确认归档

展示变更摘要，请用户确认：

```
即将归档：1-add-dark-mode

  文件：proposal.md、design.md、tasks.md、specs/ui/spec.md

归档后目录将移动到：
  openspec/changes/archive/1-2026-06-21-add-dark-mode/

确认归档？（y/n）
```

### Step 3：完成知识同步准备

归档前读取 `openspec/index.md`、当前 Change、实际 Git Diff、测试证据和相关长期 Specs/Issues，完成：

1. 核对 `proposal.md` 的「知识影响」。
2. 将每个 Change-local Delta 映射到 `openspec/specs/` 下的同相对路径，并在 `tasks.md` 的
   「知识同步」表中记录目标、动作和 `Completed` 状态；首版由人工执行语义合并，不依赖自动合并器。
3. 更新被修改知识的相关索引；无索引更新时在同步表中写明理由。
4. 检查知识与代码、Schema、配置、测试或运行证据的冲突。无冲突时记录「无冲突」；有冲突时记录
   知识文件与结论、代码证据、版本、不确定性和处理状态。未解决冲突禁止归档。
5. 已验证故障写入 `openspec/issues/`；跨项目候选只列在交付报告中，未经用户确认不得写公共库。

### Step 4：执行 Archive 门禁

用户确认后，从当前 Skill 目录向上定位 `../../scripts/validate_change.py`，在移动目录前执行：

```bash
python <validator-path> --repo . --change openspec/changes/<ticket>-<change-name> --phase archive --archive-target openspec/changes/archive/<ticket>-YYYY-MM-DD-<change-name>
```

`--archive-target` 必须与下一步 `mv` 使用完全相同的实际目标路径，其中日期为执行当天。

- 退出码为 `0` 才能移动目录。
- 退出码为 `1` 时，按输出提示修正变更文档并重跑；禁止归档。
- 退出码为 `2` 时，停止并报告调用、路径或校验器错误；不得绕过。

### Step 5：执行归档

门禁通过后，移动目录（加当天日期前缀）：

```bash
mkdir -p openspec/changes/archive
mv openspec/changes/<ticket>-<change-name> \
   openspec/changes/archive/<ticket>-$(date +%Y-%m-%d)-<change-name>
```

> 归档状态由**目录位置**表达：在 `openspec/changes/` 下即活跃，移入 `openspec/changes/archive/` 即已归档，不维护单独的状态文件。
> 当前实现始终以代码和运行证据核实；长期 Specs 仅是辅助知识。归档前已由人工完成经过验证的
> Delta 同步，校验器只检查映射、状态、冲突记录和索引更新记录，不执行语义合并。

### Step 6：输出归档报告

```
✅ 归档完成

  变更：1-add-dark-mode
  归档路径：openspec/changes/archive/1-2026-06-21-add-dark-mode/
```

---

## 强制规则

1. **必须用户确认后才执行移动**：不得静默归档
2. **只归档 `openspec/changes/` 下的目录**：不操作其他路径
3. **归档目录名格式**：`<ticket>-YYYY-MM-DD-<change-name>`，工单号来自活跃目录，日期为执行归档当天
4. **知识同步后再归档**：未完成 Delta 映射、索引更新记录或冲突处理时禁止移动目录
5. **保留 Production 门禁**：不得削弱用户确认、逐 Task Review 或最终集成 Review
