# Native Delivery 三任务试点

**日期**：2026-07-25

**变更**：`2028-tooling-native-first`

**状态**：已完成合同级回归；任务绑定的 Runtime Run Artifact 缺失，不能将本记录表述为 Run 级审计证据。

## 结论

- `standard` 的 Task 3 路由为 Native Delivery；`strict` 的 Task 1 与 Task 2 路由为完整 Runtime Run。
- 全量 Python 回归通过：`304 passed, 21 skipped, 111 subtests passed in 46.85s`。
- Runtime Trust Gate 合同回归通过：`13 passed, 6 subtests passed in 6.11s`。
- 本次样本没有证据支持删除或降级 Runtime；Task 1／Task 2 的真实交付未保留绑定本次变更的 Run Artifact，因此只证明升级路由和 Trust Gate 合同仍可用，**不**证明这两个任务已经完成 Run 级审计。

## 口径与限制

1. 「真实任务」指本 Change 中实际实施的 Task 1、Task 2 与 Task 3；路由结论由同一份 `tasks.md` 和当前实现的 `workflow_control.py route` 产生。
2. 机器验证使用本次 worktree 中实际执行的命令及输出；不以估算值补充任务墙钟耗时、Token、成本、人工介入、重试或恢复数据。缺失项统一记为 `unknown`。
3. 本试点不把单元测试伪装成特定变更的 Run Artifact。`scripts/test_runtime_trust.py` 是完整 Runtime Trust Gate 的合同级证据，不是 Task 1／Task 2 的 Run 级交付报告。
4. 当前没有可关联本次三个任务的持久化 `review-report.json`、`verify-report.json` 或 `.agentic-framework/runs/<run-id>/`。因此「最终 Review」仅能记录为任务清单中的状态，不作为新的 Run／Native Delivery Verdict 证据。

## 路由与证据

| 任务 | 实际改动 | 按当前路由器重算的预期路径 | 机器验证 | 最终 Review／交付结论 | 墙钟耗时 | Token／成本 | 人工介入 | 重试／恢复 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Task 1：Native Delivery Verdict 合同与交付门 | Schema、`runtime_schema.py`、`check_delivery.py` 与回归测试 | `route --review-profile strict` → `runtime-run`，原因：`strict-risk` | `python -m pytest scripts/test_runtime_schema.py scripts/test_check_delivery.py -q` → `51 passed, 18 subtests passed in 11.14s` | `tasks.md` 的 Task Review 为 Pending；因无绑定 Run Artifact，交付结论仅为「合同回归通过」，不是 Trust Gate PASS | unknown | unknown | unknown | unknown |
| Task 2：Native-first 路由与可选 Runtime | `workflow_control.py`、代码生成 Skill、执行指南与控制流测试 | `route --review-profile strict --parallel-worktree-write` → `runtime-run`，原因：`strict-risk`、`parallel-worktree-write` | `python -m unittest scripts/test_workflow_control.py` → `Ran 48 tests ... OK` | 未发现本任务的持久化 Review／Run Artifact；交付结论为「控制流回归通过，仍须完整 Runtime 执行留证」 | unknown | unknown | unknown | unknown |
| Task 3：Review／Verify 与 Fast-Path 收敛 | Review／Verify／代码生成 Skill、交付门与回归测试 | `route --review-profile standard` → `native-delivery`，无升级原因 | `python -m pytest scripts/test_check_delivery.py -q` → `40 passed, 9 subtests passed in 11.11s`；`python scripts/lint_skill_graph.py` → `errors=0 warnings=0` | 未发现本任务的持久化 Native Delivery Verdict；交付结论为「无 Run 标准合同回归通过，尚不可替代留存 Verdict」 | unknown | unknown | unknown | unknown |

## 完整 Runtime 证据

高风险样本的路由没有被降级为 Native Delivery。以下命令在本 worktree 实际执行，用于确认完整 Runtime 的 Trust Gate 合同仍通过：

```text
python -m pytest scripts/test_runtime_trust.py -q
13 passed, 6 subtests passed in 6.11s
```

该测试覆盖完整 Run 通过、伪造或自审 `strict` Review 拒绝、Artifact 替换／串 Run 拒绝、能力漂移、用户覆盖与失败 Verify 等失败关闭边界。详细威胁用例定义见 [`runtime-threat-cases.md`](runtime-threat-cases.md)。

## 全量回归

```text
python -m pytest scripts -q
304 passed, 21 skipped, 111 subtests passed in 46.85s

python scripts/lint_skill_graph.py
skills=33 commands=20 agents=8 | errors=0 warnings=0
```

## 公开基准自动试点

为避免把后补的历史 Artifact 当作真实证据，本轮额外执行了 3 个公开 SWE-bench Verified 实例。三个预测均由隔离克隆中的 Agent 生成未提交 diff；未使用 gold patch。评测由 `scripts/swebench_runner.py` 通过 `--allow-container-execution --execution-host wsl-docker` 调用官方评测器，输出保存在本地忽略目录 `.agentic-framework/evaluation/`。

| 实例 | Agent 聚焦测试 | 官方评测结果 |
| --- | --- | --- |
| `sympy__sympy-20590` | `sympy/core/tests/test_symbol.py`：13 passed | resolved |
| `sympy__sympy-16886` | `sympy/crypto/tests/test_crypto.py`：44 passed | resolved |
| `sympy__sympy-19637` | `sympy/core/tests/test_sympify.py -k kernS`：1 passed | resolved |

官方汇总报告 `codex-agent.native-first-public-pilot.json` 的选中实例结果为：`completed=3`、`resolved=3`、`unresolved=0`、`errors=0`。Runner 同时写入 prediction 的 SHA-256 和官方报告路径；后续版本在进程退出码为 0 时仍会解析该报告，若任一选中实例没有 completed 和 resolved，或出现 error／incomplete，则失败关闭。

这 3 个公开实例衡量的是 Agent 真实代码修复结果，不是本框架的 Runtime Trust Gate 证据；路由 Fixture 继续负责验证 Native／Runtime 的选择和失败关闭边界。

## 决策

**继续有限扩大 Native Delivery 试点，但保留 Runtime。**

依据是：标准档 Task 3 已由路由器选择 Native Delivery，且相关交付门与 Skill 图回归通过；严格档与并行 worktree 写入仍明确升级到 Runtime Run。由于本批 Task 1／Task 2 缺少与变更绑定的 Run Artifact，尚不能比较两条路径的端到端耗时、Token、成本、重试或恢复收益，也不能据此删除任何 Runtime 代码。

## 下一轮自动化试点

下一轮不要求人工手工挑选或补写历史 Artifact，而是由两类可重复执行的评测共同产生新证据：

1. 先运行本地路由 Fixture：`python scripts/delivery_route_fixture_runner.py`。它默认零网络、零 Docker，覆盖 `lightweight`／`standard` 的 Native Delivery 路由，以及 `strict`、并行 worktree 写入、长任务恢复、跨宿主能力验证和审计要求的完整 Runtime 升级路由。
2. 再使用 [`evaluation/swebench/README.md`](swebench/README.md) 规定的 Runner 选择经过审核的 SWE-bench Verified 小样本。未传 `--allow-container-execution` 时只生成计划；只有显式允许后才调用官方评测器和容器。
3. 每个实际执行样本都以新文件名保存 Runner 输出、Native Delivery Verdict 或 Runtime Run Artifact、Review Report、Verify Report 与会话引用。`--output` 会拒绝覆盖既有证据。
4. 观察期结束后，再汇总返工、墙钟耗时、Token／成本、人工介入和重试／恢复字段；不可得字段仍记为 `unknown`。

路由 Fixture 验证的是本框架的选择与失败关闭边界；SWE-bench Verified 验证真实代码修复结果。二者均不可替代完整 Runtime Trust Gate，也不能单独作为删除 Runtime 的依据。
