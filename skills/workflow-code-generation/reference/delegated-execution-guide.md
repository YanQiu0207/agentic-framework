# 下放 Agent 执行指南

本指南只定义 Tooling Profile 在 `tasks.md` 获批后的执行段。目标是保留 worktree、DAG、失败隔离和机器验证，同时让普通任务优先使用 Native Delivery；完整 Runtime Run 仅在可检查的升级条件命中时启用。

## 路由合同

在业务副作用前，按本次最高 `review_profile` 和执行需求运行：

```bash
python scripts/workflow_control.py <tasks.md> route --review-profile <lightweight|standard|strict>
```

按需追加以下任一参数：`--parallel-worktree-write`、`--long-task-recovery`、`--cross-host-capability-verification`、`--audit-required`。输出如下：

| 输出路径 | 条件 | 必须动作 |
| --- | --- | --- |
| `native-delivery` | `lightweight` 或 `standard`，且未命中升级条件 | 不调用 `init-run`，不创建或伪造 Run Context；使用独立 Verify、最终 Review 与 Native Delivery Verdict。 |
| `runtime-run` | `strict` 风险，或并行 worktree 写入、长任务恢复、跨宿主能力验证、明确审计要求 | 在 dispatch 前调用 `init-run`；保留 Manifest、Journal、Capability Probe、Run-bound Artifact 与 Trust Gate。 |

任务文件数、模型版本或仅存在 `tasks.md` 不构成 Runtime 升级条件。若是否需要并行写入、恢复、跨宿主验证或审计尚不明确，先澄清，不得通过伪造 Run Context 规避判断。

## 核心合同

- Task 级质量门：实现、测试、任务级机器检查。
- 交付级质量门：全部可合并 Task 合并后，全局机器验证，再执行一次首轮 Code Review。
- owner / implementer 禁止在 Task 内调用 `workflow-code-review`。
- `review_profile` 仍是 Task 必填字段，用于最终 Review 与 Runtime 路由；`strict` 必定升级为完整 Runtime Run。
- Review finding 修复后只做定向 re-review，不启动第二次首轮 Review。
- DAG、状态、阻塞和恢复可以独立使用，不自动创建 Runtime Run。

## Phase 0：准备

1. 记录 `base_sha`，有 `verify.config.json` 时采集基线。
2. 运行路由命令；只有输出 `runtime-run` 时，才在后续 Phase 0 初始化 Run。
3. 存在任务依赖、并行写入或中断恢复需求时，运行：

    ```bash
    python scripts/workflow_control.py <tasks.md> waves
    python scripts/workflow_control.py <tasks.md> dispatchable
    ```

4. 每个 Task 使用独立 worktree；同一波只并行无依赖且无文件冲突的 Task。若选择并行 worktree 写入，路由必须传 `--parallel-worktree-write` 并升级 Runtime。
5. 为每个 Task 传入 `id`、`title`、`context_files`、`verification`、`artifacts` 和 `review_profile`。
6. 仅 `runtime-run` 执行：在业务副作用前运行 `init-run`，传入 `.agentic-framework/runs/<run-id>`、Spec、`AGENTS.md`、本 Skill、Harness 声明和 Adapter 命令。失败时禁止 dispatch。

## Phase 1：逐波执行

owner / implementer 的固定职责：

1. 只修改 Task 声明的范围；发现范围或依赖错误时停止并报告。
2. 实现功能并通过 `workflow-test-generation` 补齐测试。
3. 运行 Task 的 `verification` 和 `workflow-verification`；禁止弱化配置绕过失败。
4. 返回摘要、验证命令、报告路径和 Spec Drift 结论，不返回完整 diff。
5. 禁止调用 LLM Reviewer，也不得把「尚未 Review」当作 Task 失败。

主编排方收到结果后：

- 实现、测试和机器检查通过 → 使用 `event <task-id> quality_passed --verify-report <verify-report.json> --write` 写入状态。Native Delivery 只接受独立 JSON 的 `verdict: PASS`，不写 Run Artifact；完整 Runtime Run 还必须传 `--run-dir <run-dir>`，并要求 Verify Artifact 与 Run、Task、Attempt 绑定。
- 失败且两轮内可修复 → 在原 worktree 修复并重验。
- 仍失败、Agent 未返回或出现范围冲突 → 标 `需人工`，保留 worktree。
- 上游未合并 → 下游标 `阻塞`，不得 dispatch。
- Git 合并成功后才写 `merge_success`；冲突标 `需人工`，不得伪装完成。

`quality_passed` 只写 `- 状态：` 字段，不动复选框。**主编排方在把任务写成 `完成` 的同一步，必须按真实完成情况勾选该任务的任务头 `[x]`、验收标准与子任务复选框**——三者是同一个完成信号的三处表达，只改状态字段会留下自相矛盾的记录，并在归档前被 `lint_task_deps.py --state-consistency` 拦住。未达成的验收项不得勾选：改标 `需人工` / `阻塞` 并附原因，未勾选项正是「哪些验收项没达成」的记录。

波间必须串行：当前波的合并和状态持久化结束后，重新运行 `dispatchable` 再开始下一波。

## Phase 2：交付级质量门

所有 Task 到达「完成 / 需人工 / 阻塞」终态后：

1. 对集成结果执行一次全局 `workflow-verification`。`runtime-run` 生成 Run-bound Verify Artifact；Native Delivery 生成独立 Verify 报告。
2. 涉及前端时执行 Taste 和浏览器验证；修复后重跑全局机器验证。
3. 取所有已执行 Task 的最高 `review_profile`，对完整 diff 调用一次 `workflow-code-review`，`mode: initial`。
4. `strict` 必须由未参与实现的独立 Judge 裁决，并保持完整 Runtime Run 的证据要求。
5. keep 的 P0 / P1 触发修复；修复后重跑受影响的机器验证，并以 `mode: re-review` 只复核原 finding 和修复 diff，最多两轮。
6. P2 和 follow-up 不触发修复循环；仍有 P0 / P1 时整体标 `需人工`。
7. Review 通过后：
    - `runtime-run`：由 Judge 写出 Run-bound `review-report.json`，再运行完整 Runtime 的 `check_delivery.py --run-dir ...` 交付门。
    - `native-delivery`：使用标准无 Run Review、独立 Verify 与 `check_delivery.py --native-delivery --native-delivery-verdict <ignored-path>` 生成有界 Verdict；不得声称 Trust Gate PASS、Harness 能力或完整证据图。

最终 Review 不回写每个 Task 的 Review 状态，也不改变已经记录的 DAG 和合并事实。

## 恢复中断

恢复本身是 Runtime 升级条件。先收集已合并 Task ID，再运行：

```bash
python scripts/workflow_control.py <tasks.md> recover --merged <task-id...>
```

执行恢复前，路由命令必须传 `--long-task-recovery` 并初始化完整 Runtime Run。恢复时核对 worktree、Git 合并事实和机器验证记录。若 Run 尚无首轮 Review，全部任务完成后正常执行一次；若已有首轮 Review，只允许继续其定向 re-review，禁止重启首轮。

## 上下文控制

- 主会话只保留状态摘要、验证证据和 finding，不承载完整实现 diff。
- Owner 读取 `context_files` 中的必要文件，不扫描无关目录。
- Agent 之间通过仓库文件和结构化结果传递状态，不复制大段日志。
