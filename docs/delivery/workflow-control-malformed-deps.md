# 交付说明：调度器拒绝不合规依赖

## 背景

`tasks.md` 中 `depends_on` 写成 `[Task 1]` 等不合规格式时，`lint_task_deps.py` 会报 ERROR，但 `workflow_control.py` 的 `waves`、`dispatchable`、`event start` 和 `recover` 会把依赖解析为空集合，静默当作无依赖，导致下游任务与上游并行派发。

## 提交文件清单

| 路径 | 状态 | 用途 |
| --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | `_validate_dependencies` 遇到依赖格式错误时抛出 `ValueError`，覆盖全部调度入口 |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 修改 | `dep_format_error` 对「字段存在但值为空」报错，lint 与调度器同口径（无依赖须显式写 `[]`） |
| `scripts/test_workflow_control.py` | 修改 | 新增复现测试：`[Task 1]` 依赖在 `build_waves`、`dispatchable_tasks`、`apply_event` 下均失败关闭；空值依赖在 `build_waves` 下失败关闭 |
| `scripts/test_lint_task_deps.py` | 修改 | 新增测试：空值依赖产生 `dep_error` |
| `openspec/changes/2047-freshness-doc-resync/tasks.md` | 修改 | 修正 `depends_on: [1]`，补齐缺失的 `artifacts` 与 `context_files` |
| `docs/delivery/workflow-control-malformed-deps.md` | 新增 | 本交付说明 |

不应提交：工作区中与本次无关的预存 Markdown 改动（`skills/workflow-code-generation/` 与 `skills/workflow-system-design/` 下的文档调整），不纳入本次提交。

## QA 测试点

- 正常：`depends_on: []`、`Task 1`、`Task 1, Task 3` 的分波结果不变。
- 异常：`depends_on: [Task 1]`、`[1]` 等不合规写法，以及 `depends_on:` 留空，`lint_task_deps.py`、`waves`、`dispatchable`、`event <id> start`、`recover` 均以非零退出并给出同一错误信息。
- 回归：缺少 `depends_on`、循环依赖、依赖不存在任务的既有报错保持不变。

## 审核顺序

1. `workflow_control.py` 的 `_validate_dependencies`：新增两行，复用 `lint_task_deps.parse_tasks` 已产出的 `dep_error`，错误文案与 lint 一致。检查重点：所有调度入口是否都经过此函数。
2. `lint_task_deps.py` 的 `dep_format_error`：空值依赖改为报错。检查重点：现存活跃与归档 `tasks.md` 均无空值写法，不产生新违规。
3. `scripts/test_workflow_control.py`、`scripts/test_lint_task_deps.py`：复现测试，修复前失败（`ValueError not raised`、`unexpectedly None`），修复后通过。
4. `2047-freshness-doc-resync/tasks.md`：仅补格式，不改任务状态与内容。
