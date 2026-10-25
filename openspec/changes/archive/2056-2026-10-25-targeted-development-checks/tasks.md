# 实施任务清单

> 任务总数：1。纯执行指引调整；老板已批准完成本 Change 及正式交付。

## 依赖关系总览

Task 1（四份指引修改与交付核验），无前置依赖。

## 变更影响概览

四份指引见 design.md 第 1 节；另更新本 Change 的 proposal.md、design.md 和 tasks.md。不修改代码、配置、测试或报告 Schema；无构建系统变更。

## 风险与假设

定向检查不得正式放行；正式质量门执行完整 Verify。主工作区已有 `.codex/hooks.json` 无关改动，合并时保留且不得纳入本次提交。

## 任务列表

### 任务 1：[x] 区分开发反馈与正式验证
- 状态：完成
- 文件：`skills/workflow-verification/SKILL.md`、`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-generation/reference/delegated-execution-guide.md`、`skills/workflow-code-generation/reference/delivery-guide.md`
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 第 2、3 节；design.md 第 1 至 4 节
- 说明：实施四文件方案，保留完整验证及内容主体合同。
- context_files:
  - `skills/workflow-verification/SKILL.md`
  - `skills/workflow-code-generation/SKILL.md`
  - `skills/workflow-code-generation/reference/delegated-execution-guide.md`
  - `skills/workflow-code-generation/reference/delivery-guide.md`
- verification:
  - [x] `git diff --check` 返回 0。
  - [x] `python scripts/lint_skill_graph.py` 返回 0。
  - [x] Diff 仅包含四份指引与本 Change 文档，无禁改文件。
- artifacts:
  - 四份执行指引和本 Change 文档。
- 子任务：
  - [x] 分类主定义与三处流程接线。
  - [x] 核对正式验证红线和修改范围。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal.md 全文、design.md 第 1 至 4 节 | Task 1 | 执行指引与检查 |

## 知识同步

无长期知识影响：不改变机器门禁合同；执行策略唯一来源仍为四份指引，不创建长期 Spec Delta 或公共知识。

## 知识冲突

- 结论：无冲突。现行质量门报告合同保持不变。

## 实际 Diff 核对

- `git diff --check` 与 Skill 图检查均通过；实际范围为四份指引和本 Change 文档。
- 正式完整 Verify 与 standard 集成首审均已通过，证据置于 `.agentic-framework/`，归档后交付前另行核验主体有效性，不将以上静态结果视为正式放行。
