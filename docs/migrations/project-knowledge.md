# 项目知识库迁移指南

## 结论

首版迁移工具只生成逐文件映射、引用清单和待人工分类项，不复制、移动、覆盖、删除或标记任何旧文件。现有仓库的真实迁移必须基于计划单独审核，并获得用户明确授权。

## 识别范围

工具识别以下旧目录：

| 旧目录 | 建议目标 | 说明 |
| --- | --- | --- |
| `docs/design-docs/` | `openspec/changes/archive/` | 按原目录聚合为 Legacy Change，复制前确认归档名称 |
| `docs/adr/` | `openspec/specs/backend/engineering/tech/adr/` 候选 | ADR 必须按实际作用域复核，不能机械归类 |
| `docs/incidents/` | `openspec/issues/incidents/` | 保留 Incident 分类，避免与原 Issue 重名 |
| `docs/issues/` | `openspec/issues/` | 保留原相对路径 |
| `docs/arch-snapshots/` | 待人工分类 | 必须先确认端、业务域和模块，工具不得猜测 |

迁移计划会为每个旧文件保留原路径，并列出仓库内指向它的 Markdown 引用。无法安全推导唯一目标的文件标记为 `classification-required`，而不是写入临时公共目录。

## 生成计划

在目标项目根目录外运行框架脚本：

```powershell
python scripts/migrate_project_knowledge.py `
    --repo E:/path/to/project `
    --output E:/path/to/project-knowledge-plan.json
```

省略 `--output` 时，JSON 计划写入标准输出。脚本没有 `--apply` 或 `--fix` 参数；唯一可能的写入是用户明确指定的计划输出文件。

计划中的安全字段必须保持为：

```json
{
    "writes_source": false,
    "copies_files": false,
    "deletes_files": false,
    "overwrites_files": false,
    "apply_supported": false
}
```

## 人工审核清单

1. 逐项确认 `proposed_target` 是否符合正文的实际作用域。
2. 处理所有 `classification-required` 和 `review-required` 条目。
3. 检查目标文件不存在，禁止覆盖已有 `openspec/` 内容。
4. 根据 `references` 更新引用方案，保留旧来源路径和历史关系。
5. 确认所有 Workflow 已停止写入 `docs/design-docs/`。
6. 为计划和目标目录建立可验证备份，并取得用户明确授权。
7. 迁移时只复制到空目标，不移动或删除旧目录。
8. 核对复制结果后，在每个实际迁移的旧目录创建或更新 `README.md`，统一标记 `Superseded` 状态、停止写入规则和新目录入口；未经授权不得添加标记。
9. 重新运行测试、链接检查和迁移计划，确认没有漏项。

## 目录级 `Superseded` 标记

旧文件必须保留正文、原历史状态和来源引用。获得授权并完成复制核对后，在每个实际迁移的旧目录 `README.md` 中增加：

```markdown
> 状态：Superseded
> 当前入口：`openspec/...`
> 说明：本目录正文保留为历史来源，不再作为当前工作流写入位置。
```

目录级标记是统一策略，不要求逐文件改写原状态。`README.md` 必须给出与该旧目录对应的新入口；目标仍需人工分类时，指向迁移计划并明确禁止继续写入。

不得仅因旧文件未跟踪、疑似重复或已有新版本就删除它。若计划内容与真实项目结构不一致，应修改计划或人工分类，不得用残片覆盖性重写原文件。

## 验收

- 迁移计划覆盖所有旧 Change、ADR、Incident、Issue 和架构快照文件。
- 每个文件都具有来源路径、建议目标或待分类状态，以及引用清单。
- 运行计划前后，目标仓库除用户指定的外部 JSON 输出外没有变化。
- 所有 Workflow 的新写入路径均为 `openspec/changes/`，不再出现 `docs/design-docs/`。
- 实际迁移仅在用户授权后执行，且旧目录未被删除、覆盖或移动。
- 每个实际迁移的旧目录都有目录级 `README.md`，记录 `Superseded`、停止写入规则和当前入口。
