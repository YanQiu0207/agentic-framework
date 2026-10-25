# Runtime 重放修复任务

### 任务 1：[ ] 修复与验证 Runtime 证据重放
- 状态：进行中
- attempts：0
- control_stage：running
- depends_on: []
- review_profile: strict
- 文件：`scripts/run_journal.py`、`scripts/runtime_workflow.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、相关测试。
- context_files:
  - `spec.md`
  - `scripts/runtime_schema.py`
  - `scripts/run_manifest.py`
  - `scripts/runtime_trust.py`
- verification:
  - [ ] 全量 Verify 与回归测试通过。
  - [ ] 独立 strict 审核通过。
  - [ ] 实际交付与同参数重跑通过。
- artifacts:
  - `.agentic-framework/runs/2051-runtime-replay-fix/artifacts/verify-run.json`
  - `.agentic-framework/runs/2051-runtime-replay-fix/artifacts/review-run.json`

## 知识同步

修复结论同步至 `openspec/issues/runtime-retry-and-delivery-replay.md`，旧失败证据保留。

## 知识冲突

Issue 中的「未修复」是本次修复前的状态；最终通过验证后追加新结论，不能改写历史 Run 的错误。
