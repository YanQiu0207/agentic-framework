# 质量门概览

## 职责划分

框架把确定性质量门、机器 Verification 与语义 Code Review 分开：

| 层 | 入口 | 职责 |
| --- | --- | --- |
| Production 阶段门 | `scripts/validate_change.py` | 只读校验 Plan、Delivery、Archive 的 Artifact 与证据合同 |
| Tooling Task 门 | `workflow_control.py quality_passed` | 要求 Task 机器验证报告为 `PASS` |
| Tooling Run 交付门 | `check_delivery.py` | 校验归档、终态、Review JSON、知识影响和 Git 状态 |
| 机器 Verification | `workflow-verification/scripts/verify.py` | 执行项目配置、比较基线、检查 Spec Drift 并生成 JSON 报告 |
| 语义 Review | `workflow-code-review` 与 `agents/` | 按风险分档审查 Diff，由 Judge 输出 Markdown 与结构化 JSON |

这些层相互提供证据，但不能互相替代。

## Production 阶段门

`validate_change.py` 支持 `plan`、`delivery` 和 `archive` 三个阶段（`scripts/validate_change.py:17-57,1375-1479`）：

- Plan 检查 Change 类型、Proposal、Tasks、依赖、文档映射和 Task Review 合同。
- Delivery 检查任务完成、执行记录、Task 级 Review 证据和风险触发批准证据。
- Archive 检查集成 Review、知识同步、Delta 映射、冲突记录、索引影响和归档目标。
- 目录边界、命名、重解析点和代码派生知识元数据均采用失败关闭。

校验器只读取 Change 和证据，不维护第二套执行状态。对应回归测试位于 `scripts/tests/test_validate_change.py`。

风险触发批准由 Change `2029-risk-triggered-task-approval` 定义：Completed Task 声明 `Escalation` 时，必须具有条件集合一致的 `Approval: granted`；`pending`、缺失、重复、条件非法或不一致均失败关闭。头部声明 `批准模式：per-task` 时，全部 Completed Task 都必须获批；默认 `risk-triggered` 模式的未升级 Task 不要求 Approval。

## Verification

`verify.py` 总是计算 Spec Drift；代码发生变化时，必须存在相关规格类更新或显式的无需更新理由（`verify.py:144-246`）。配置驱动检查支持退出码、输出匹配和数量基线，并对以下配置漂移失败关闭：

- 已有检查被删除或修改。
- `baseline_aware` 检查缺少基线条目或指纹。
- 基线存在孤儿检查。

退出码语义为：`0` 表示 PASS，`1` 表示新增违规，`2` 表示工具或配置错误（`verify.py:750-895`）。长期知识来源晚于 `source_ref` 时只输出 `WARN`，不改变总判定。

本仓库的 `verify.config.json` 运行全量 Pytest、测试数量不下降检查和 Skill 图 Lint。

Verification 基线、机器报告和 Run 级 Review JSON 统一位于仓库根 `.agentic-framework/verify/`，不纳入 Git。旧 `.verify/` 只作为迁移期读取来源；检测到旧产物时提示迁移，新版本不再写入、删除或覆盖旧产物。

## Code Review

共享 Review 入口按风险选择：

- `lightweight`、`standard`：调用 `comprehensive-reviewer`。
- `strict`：调用 5 个专项 Reviewer；存在 Finding 时再调用 `review-critic`。
- Strict 最终 Judge 必须与实现主体独立。
- 修复后只定向 Re-review，最多 2 轮；不得启动第二次全量首审。

Review 同时输出 Markdown 和 Run 级 JSON。机器门校验 `verdict`、P0/P1 数量、`scope`、`review_profile` 和轮次，但 Reviewer 的语义判断仍需独立 Judge 负责（`skills/workflow-code-review/SKILL.md:14-59,270-300`）。OPSX 阶段门（`validate_change.py`）接受双格式 Review 报告：Envelope（裁决字段在 `payload` 内）或旧式扁平 JSON（裁决字段在顶层），按同一套字段校验，Envelope 额外要求顶层 `artifact_type` 为 `review-report`，顶层字段仅限 Run Envelope schema 定义的 13 个键（与 `payload` 同时携带裁决字段、`payload` 非 JSON 对象、或顶层携带该白名单外的未知字段，均拒绝）；Tooling Run 级报告仍必须是绑定 Run Context 的 Envelope（见 trust-model.md §6）。

## 信任边界

- JSON 证据防止只靠自由文本宣称 PASS，但不能证明判断本身正确。
- Verification 只运行配置中的命令，不推断未声明的生产环境行为。
- 长期 Specs 只辅助理解；活跃 Change、代码、测试和运行报告用于当前裁决。
- Production 与 Tooling 共享证据字段，不共享生命周期状态机。
