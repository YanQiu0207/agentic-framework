# 评测框架恢复验证任务

## 恢复依据

原实施范围见 `review-first-amendment.md`，原任务见 `tasks.md`。代码已实现，两项旧测试已修复，F-1 参考组问题已修复，原 Run 的 `verify-1-3.json` 实际通过。

原 Run `2050-review-eval` 的质量事件以 attempt 3 落盘后，Journal 重放要求 attempt 1，导致 `attempt_mismatch:1:expected=1`。原 Journal、Verify 和首审裁决全部保留，不修改或重标。新 Run 只重新验证当前源码与定向复核已有 finding，不声称补齐旧 Run 的历史。

## 任务列表

### 任务 1：[x] 重新验证与完成 F-1 定向复审
- 状态：完成
- attempts：0
- control_stage：completed
- depends_on: []
- review_profile: strict
- 文件：`scripts/agent_eval.py`、`scripts/test_agent_eval.py`、`scripts/test_knowledge_management_e2e.py`、`scripts/test_workflow_control.py`、`evaluation/review/`、`openspec/specs/backend/engineering/tech/agent-evaluation.md`
- 文档映射：review-first-amendment.md、verification-notes.md、原首审 review-run.md。
- verification:
  - [x] 原配置全量 Verify 与 Spec Drift 通过。
  - [x] 独立 Judge 对 F-1 修复与修复 diff 定向复审通过。
  - [x] 真实案例试点结果与知识索引同步，准确区分观察值和未验证限制。
- artifacts:
  - `.agentic-framework/runs/2050-review-eval-recovery/artifacts/verify-1-1.json`
  - `.agentic-framework/runs/2050-review-eval-recovery/artifacts/review-run.json`

## 知识同步

Completed：目标为 `openspec/specs/backend/engineering/tech/agent-evaluation.md`。旧 Run 失败与恢复证据必须保留，新的真实实验报告不得冒充模型性能统计定论。
