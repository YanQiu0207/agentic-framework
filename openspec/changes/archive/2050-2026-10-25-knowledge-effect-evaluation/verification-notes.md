# 首版验证记录

**阶段说明**：下方「当前结果」「待完成」是首次验证阶段记录，现已由本页末尾恢复验证结果更新，不代表仍等待旧测试授权。

## 当前结果

- 专项：`python -m pytest scripts/test_agent_eval.py -q`，43 passed、1 skipped。跳过项为真实符号链接创建权限不足，模拟 Windows reparse point 拒绝路径已覆盖。
- 全量：原配置 `python -m pytest scripts -q`，643 passed、22 skipped、2 failed；测试数量检查、Skill Graph 检查及 Spec Drift 通过。
- Run 证据：`.agentic-framework/runs/2050-review-eval/artifacts/verify-1-1.json`，总体 FAIL，不得作为通过证据。
- CLI 冒烟：真实执行示例 `plan`、CONTROL `export`、`report` 成功；报告包含 8 个 missing 单元、4 个未完成配对，未知费用为 null。未伪造真实模型结果。

## 基准复现

在独立工作区 `C:/Users/YanQi/.codex/worktrees/7abd/aef-baseline-2050` 检出基准提交 `7441ecc96a2f6b71f3df6b7ba0e73530ce6a6c11`，下列两项原测试同样失败：

```text
scripts/test_knowledge_management_e2e.py::KnowledgeManagementE2ETest::test_tooling_standard_uses_unified_artifact_and_controller
scripts/test_workflow_control.py::WorkflowControlTest::test_skip_decision_allows_dispatch_without_verify_config
```

共同错误为「无法取得治理 Profile：缺少 .agentic-framework/manifest.json 且未传 --governance-profile」。复现命令为 `python -m pytest <上述两个节点> -q --tb=short`，退出码 1，2 failed。此证据表明当前环境下基准已经失败，不代表可以放宽本次门禁。

## 待完成

已询问用户是否允许修复两项既有测试的 Profile 声明。未获确认前不扩大实现范围，不修改旧测试或配置。全量 Verify 通过前不进入最终统一严格审核；不归档、不提交、不宣布交付通过。

旧的知识效果 Run 与 proposal 保留作方向变更记录；当前有效范围为 `review-first-amendment.md`。原始 E: 工作区未改动。没有调用模型、执行待审代码、启动容器或发送项目知识到外部服务。

## 恢复验证与实际试点结果

- 用户授权后仅补充两处测试调用的 `--governance-profile tooling`，原生产门禁、断言和配置不变。两个目标测试通过，全量 Verify 随后通过。
- 严格首审 5 个维度与 Critic、独立 Judge 确认 F-1：JSON 对象键顺序可反转参考组。已改用摘要保护的有序 cells，并增加保留原摘要、重排分组后非零差值不变的回归测试。
- 报告改称外部提供的裁定，身份未验证，不能把 AI 初评称为人工复核；没有新增自动 Judge 或更改评分逻辑。
- 专项 43 passed、1 skipped；恢复 Run 的任务 Verify 与全局 Verify 均 PASS，独立定向复审第 1 轮 PASS，P0/P1 均为 0。P2 的测试函数类型注解建议保留。
- 有效证据目录为 `.agentic-framework/runs/2050-review-eval-recovery/artifacts/`，包含 `verify-1-1.json`、`verify-run.json`、`review-run.json` 和对应 Markdown 审核报告。
- 已执行 8 次真实 Agent Review，4 个成熟仓库历史案例，每组各命中 3/4 个官方目标。原始观察、冻结来源与独立 AI 初评已保存至 `evaluation/review/historical-pilot/`；AI 初评不是人工复核，上游回归测试未在本地执行。

## 原 Run 记账失败与未修复问题

原 Run 保留：控制器 start/failure 未记录到 Journal，质量事件 attempt 3 先落盘，随后重放报 `attempt_mismatch:1:expected=1`。已有事件不能通过正常追加恢复；未裁剪、插入或重写原 Journal。源头见 `scripts/runtime_workflow.py` 与 `scripts/run_journal.py`，完整结论是控制器与 Journal 的重试记账／追加后校验缺口，尚未在本次修改。

使用独立 `recovery/tasks.md`、新 Run Context、真实重跑 attempt 1 和真实定向复审恢复验证。原实施任务根据新证据闭环，不表示旧 Run 历史完整或旧缺陷已修复。后续应单独修复重试事件一致性和追加原子性；本次不扩大到生产门禁源码。
