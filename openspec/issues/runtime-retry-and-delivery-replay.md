# Runtime 重试记账与交付重跑失败

**状态**：已观察并定位，未修复。

**日期**：2026-10-25。

## 观察证据

在 `codex/comet-review-eval` 的评测框架实现中，全量 Verify 与独立严格复审通过，但 Runtime 记账与交付重跑存在以下问题。没有修改相关生产源码或绕过检查。

### 重试计数与 Journal 不一致

旧 Run `.agentic-framework/runs/2050-review-eval/` 的任务经历两次真实失败：旧测试失败、严格首审 F-1 失败。控制器补记 failure 后，任务 attempts 为 2；引用真实通过的 `verify-1-3.json` 时，质量事件已追加，但 checkpoint 重放报：

```text
run_journal.JournalError: attempt_mismatch:1:expected=1
```

只读核验发现该 Journal 只有 run-started 和 attempt 3 的 task-quality-passed。控制器 start/failure 未写相应 Journal 事件，而 `scripts/runtime_workflow.py:335` 的质量记录会写；`scripts/run_journal.py:145` 的 append_event 在追加前重放旧前缀，追加后的完整事件校验失败发生在后续 checkpoint。

原始 Journal 与报告均保留，未裁剪或改写。恢复验证另建 Run，真实重跑 attempt 1 并完成独立定向复审，不声称修复旧历史。

### 交付检查失败后不能直接重跑

恢复 Run `.agentic-framework/runs/2050-review-eval-recovery/` 的交付检查先报告任务文档缺少 context_files。补齐真实上下文声明并提交后再次运行同一命令，得到：

```text
ERROR  Runtime 证据链：artifact_already_exists:task-1-state
```

`scripts/runtime_workflow.py:407` 使用固定 task-state ID，`:102` 拒绝已有 Artifact。当前现象表明失败的交付检查已留下中间产物，后续重跑被不可覆盖检查阻止。没有移动或重写该证据以强行放行；最终交付门仍未通过。

## 当前影响与后续验收

- 评测实现的专项测试、全量 Verify 和独立代码复审已有通过证据；不能将其替代 Runtime 交付门通过。
- 真实历史 Bug 的 8 份观察和独立 AI 初评不依赖该交付门，已保存在 `evaluation/review/historical-pilot/`，但不能据此宣布框架完整交付。
- 后续修复应分别覆盖「failure/start 与 Journal 的合法事件一致性」「追加失败不污染可重放前缀」「交付校验失败后重复执行的幂等性」，保留严格绑定与不可覆盖语义，不简单删除已有 Artifact 或弱化门禁。
- 本次仅得到用户对两项旧测试的修复授权，未把上述生产控制器修改混入评测功能。
