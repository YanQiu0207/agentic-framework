# 下放 Agent 执行指南

本指南只定义 Tooling Profile 在 `tasks.md` 获批后的执行段。目标是保留 worktree、DAG、失败隔离和机器验证，同时保证每次 Run 只启动一次首轮 LLM Code Review。

## 核心合同

- Task 级质量门：实现、测试、任务级机器检查。
- Run 级质量门：全部可合并 Task 合并后，全局机器验证，再执行一次首轮 Code Review。
- owner / implementer 禁止在 Task 内调用 `workflow-code-review`。
- `review_profile` 仍是 Task 必填字段，但只用于计算 Run 级 Review 的最高风险档位。
- Review finding 修复后只做定向 re-review，不启动第二次首轮 Review。

## Phase 0：准备

1. 记录 `base_sha`，有 `verify.config.json` 时采集基线。
2. 运行：

   ```bash
   python scripts/workflow_control.py <tasks.md> waves
   python scripts/workflow_control.py <tasks.md> dispatchable
   ```

3. 每个 Task 使用独立 worktree；同一波只并行无依赖且无文件冲突的 Task。
4. 为每个 Task 传入 `id`、`title`、`context_files`、`verification`、`artifacts` 和 `review_profile`。

## Phase 1：逐波执行

owner / implementer 的固定职责：

1. 只修改 Task 声明的范围；发现范围或依赖错误时停止并报告。
2. 实现功能并通过 `workflow-test-generation` 补齐测试。
3. 运行 Task 的 `verification` 和 `workflow-verification`；禁止弱化配置绕过失败。
4. 返回摘要、验证命令、报告路径和 Spec Drift 结论，不返回完整 diff。
5. 禁止调用 LLM Reviewer，也不得把「尚未 Review」当作 Task 失败。

主编排方收到结果后：

- 实现、测试和机器检查通过 → 使用 `event <task-id> quality_passed --verify-report <verify-report.json> --write` 写入状态；控制器仅在报告的 `verdict` 为 `PASS` 时允许进入合并阶段。
- 失败且两轮内可修复 → 在原 worktree 修复并重验。
- 仍失败、Agent 未返回或出现范围冲突 → 标 `需人工`，保留 worktree。
- 上游未合并 → 下游标 `阻塞`，不得 dispatch。
- Git 合并成功后才写 `merge_success`；冲突标 `需人工`，不得伪装完成。

波间必须串行：当前波的合并和状态持久化结束后，重新运行 `dispatchable` 再开始下一波。

## Phase 2：Run 级质量门

所有 Task 到达「完成 / 需人工 / 阻塞」终态后：

1. 对集成结果执行一次全局 `workflow-verification`。
2. 涉及前端时执行 Taste 和浏览器验证；修复后重跑全局机器验证。
3. 取所有已执行 Task 的最高 `review_profile`，对完整 diff 调用一次 `workflow-code-review`，`mode: initial`。
4. `strict` 必须由未参与实现的独立 Judge 裁决。
5. keep 的 P0 / P1 触发修复；修复后重跑受影响的机器验证，并以 `mode: re-review` 只复核原 finding 和修复 diff，最多两轮。
6. P2 和 follow-up 不触发修复循环；仍有 P0 / P1 时整体标 `需人工`。
7. Review 通过后，由 Judge 同步写出 `review-report.json`，再运行 `check_delivery.py --tasks <tasks.md> --spec <spec.md> --review-report <review-report.json>`；只有退出码为 `0` 才允许交付。

最终 Review 是 Run 级门禁，不回写每个 Task 的 Review 状态，也不改变已经记录的 DAG 和合并事实。

## 恢复中断

先收集已合并 Task ID，再运行：

```bash
python scripts/workflow_control.py <tasks.md> recover --merged <task-id...>
```

恢复时核对 worktree、Git 合并事实和机器验证记录。若 Run 尚无首轮 Review，全部任务完成后正常执行一次；若已有首轮 Review，只允许继续其定向 re-review，禁止重启首轮。

## 上下文控制

- 主会话只保留状态摘要、验证证据和 finding，不承载完整实现 diff。
- Owner 读取 `context_files` 中的必要文件，不扫描无关目录。
- Agent 之间通过仓库文件和结构化结果传递状态，不复制大段日志。
