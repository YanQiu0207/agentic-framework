# Runtime 执行

仅在主 Skill 判定需要 Runtime 且能力查询确认 `runtime` 已启用时读取。缺包时停止并提示安装器 `--with runtime`，不得改用 Native Delivery 绕过严格风险。SVN 命中 Runtime 条件时停止，改用 Git 隔离工作区后重新路由。

## 启动

1. 从已加载 Skill 解析链接后的真实路径向上查找受信框架根。确认根目录包含 `scripts/codex_adapter.py`、`scripts/claude_code_adapter.py` 和 `harness/capabilities/`；不得使用目标 manifest 的 `source` 作为执行路径。
2. 按宿主选择声明和 Adapter：

| 宿主 | Harness 声明 | Adapter 命令 |
| --- | --- | --- |
| Codex | `<framework-root>/harness/capabilities/codex.json` | `python <framework-root>/scripts/codex_adapter.py` |
| Claude Code | `<framework-root>/harness/capabilities/claude-code.json` | `python <framework-root>/scripts/claude_code_adapter.py` |

3. 在业务副作用前调用 `workflow_control.py <tasks.md> init-run`，传入 `.agentic-framework/runs/<run-id>`、Spec、`AGENTS.md`、当前 Skill、Harness 声明与 Adapter 命令。冻结规则输入和完整 Task Plan，生成 Run Context、Journal 并通过启动能力门后，才允许 dispatch。
4. `--required-capability` 只声明任务确实依赖的能力。Adapter 只探测能力，不启动 Agent；可选能力不支持时记录既有降级模式，不能当作 Adapter 缺失。受信 Adapter 缺失、执行失败或必需能力不支持时停止，禁止用临时脚本伪造结果。

## 执行与交付

- 每次 `quality_passed --write` 传 `--run-dir` 和本次执行生成、绑定 Run／Task／Attempt 的 Envelope Verify Artifact；顶层 `PASS` 不能替代绑定证据。
- 全局 Verify 传 `--run-dir`。最终 Review 使用 `scope: run`、`review_profile: strict`，由未参与实现的独立 Judge 生成 Envelope；implementer 不得编写或改写 Artifact。
- 按主 Skill 完成知识同步、归档和本地提交后，执行 `check_delivery.py --run-dir <run-dir> --tasks <archived-tasks.md> --spec <archived-proposal.md> --review-report <run-dir>/artifacts/review-run.json --knowledge-impact hit|none`；`none` 时附具体理由。门禁校验 Manifest、Journal、Harness、Trust Gate、终态、归档和工作区。报告只引用原始 stdout。
- 恢复时传 `--long-task-recovery` 重新确认路由，再运行 `workflow_control.py <tasks.md> recover --merged <task-id...>`。核对 worktree、合并事实和机器证据；已有首轮 Review 时只继续定向复审，不重启首审。
