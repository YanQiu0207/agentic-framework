# 跨项目公共知识库迁移契约

## 结论

本迁移只调整跨项目公共知识库的作用域与元数据合同。框架仓库提供只读校验器和迁移步骤，不直接修改 `E:/work/shared-knowledge-base`。公共库的每次修复仍需在其自身仓库中审查、提交和验证。

## 目标状态

公共库只保存经过批准、泛化和脱敏的跨项目知识，以及公共库自身的治理记录：

```text
shared-knowledge-base/
├── index.md
├── domains/
├── issues/
├── sources/
├── changes/
└── archives/
```

- `projects/` 可以暂时保留，但不得出现在根索引或其他日常索引中，也不得新增项目入口。
- `changes/` 只记录公共库自身的索引、分类、元数据和检索治理，不保存项目知识候选。
- `domains/` 和 `issues/` 中除 `index.md` 外的公共条目必须包含完整元数据。
- 公共索引不得链接 `projects/`、公共库外路径或任何项目私有正文。

## 公共条目元数据

每个公共条目至少包含：

```yaml
---
status: provisional
source: <可复核来源>
source_version: <来源版本或获取日期>
applies_to: <适用范围>
excludes: <不适用范围>
---
```

`status` 允许值如下：

- `provisional`：只有一个真实案例，边界已经写明。
- `verified`：有官方依据和真实验证，或多个独立案例一致。
- `uncertain`：证据冲突或无法复核。
- `deprecated`：已经被新证据取代。

不得为了通过校验而虚构来源、版本或适用边界。不确定时使用 `uncertain`，并在正文说明缺少的证据。

## 只读校验

在框架仓库执行：

```powershell
python scripts/validate_shared_knowledge.py --root E:/work/shared-knowledge-base
```

退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 所有确定性结构检查通过 |
| `1` | 发现合同违规 |
| `2` | 参数错误或目标不是可用的公共知识库 |

校验器不提供 `--fix`，也不写入目标仓库。它能检查：

- 根索引是否仍把 `projects/` 作为日常入口。
- 公共索引是否链接 `projects/` 或越出公共库。
- 公共 `changes/` 是否含有确定性的项目候选标记。
- 公共条目是否具有非空的 `status`、`source`、`source_version`、`applies_to` 和 `excludes`。
- `status` 是否属于合同允许值。

校验器不能证明正文已经充分泛化或脱敏，也不能识别所有项目内部术语。晋升前仍必须取得用户明确确认，并由公共库变更的人工 Review 复核；脚本不能替代用户确认或人工判断。

## 现有 9 条元数据债务的修复步骤

当前公共库已有 9 个条目缺少既有必填元数据。修复时在公共库自己的分支中逐条执行：

1. 读取条目全文及其主题索引，不批量填入同一组占位值。
2. 从正文引用、官方资料或原始实验记录中确定 `source`。
3. 将版本号、发布日期、Commit 或本次复核日期写入 `source_version`。
4. 根据正文结论写明 `applies_to` 和 `excludes`，不得用「所有项目」代替边界分析。
5. 根据证据强度选择 `status`；证据不足时使用 `uncertain` 或 `provisional`。
6. 删除项目名、内部路径、内部接口、业务数据和不可公开的环境信息。
7. 运行公共库原有的 `scripts/lint_kb.py`，再运行本框架的只读校验器。
8. 检查 `git diff`，确认只修改目标条目及必要索引后，在公共库中单独提交。

本任务不实际修改这 9 个条目，避免跨仓库未审变更，也不声称债务已经清零。

## `projects/` 与 `changes/` 的迁移

### `projects/`

1. 从根索引和所有主题索引删除 `projects/` 日常入口。
2. 在 `projects/README.md` 标记 `Superseded`，说明停止新增，但先不删除已有内容。
3. 检查其他索引和条目是否仍指向 `projects/`。
4. 对已有文件逐项确认来源与用途；未获得用户授权前不得永久删除。

### `changes/`

允许记录：

- 公共分类和索引调整。
- 公共元数据合同变更。
- 检索失败和公共库验收记录。
- 公共条目的合并、拆分、替代和退役计划。

禁止记录：

- 未获用户确认的项目知识候选。
- `scope: project` 的正文。
- 指向项目私有正文的证据链接。
- 等待泛化或脱敏的项目原始材料。

项目候选只能留在来源项目的 `openspec/changes/` 或交付报告中。用户确认晋升后，直接以完成泛化和脱敏的公共条目进入公共库 Review。

## 验收清单

- [ ] 根索引和所有公共索引不再链接 `projects/`。
- [ ] 公共索引不存在越出公共库的本地链接。
- [ ] `changes/` 只包含公共库自身治理记录。
- [ ] 9 个既有条目已经逐条补齐真实元数据。
- [ ] `python scripts/lint_kb.py` 在公共库中通过。
- [ ] `python scripts/validate_shared_knowledge.py --root E:/work/shared-knowledge-base` 返回 `0`。
- [ ] 公共库 Diff 已由用户或独立 Reviewer 审核，并在公共库中单独提交。
