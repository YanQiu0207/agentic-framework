# workflow-code-generation 触发评估用例

> 评测体系 Tier 1（触发评估），对应 [docs/tooling/08-evaluation-strategy.md](../../../docs/tooling/08-evaluation-strategy.md) §5.1。
> 目标：验证「任何代码文件变更都先走这个统一入口」能被召回，且不把「审 / 讲 / 改文档」误吞进来。
> 判定（确定性）：执行 transcript 是否出现首行标记 `Using workflow-code-generation`。

## should-trigger（应触发，测召回）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| T-1 | 「帮我加一个导出 CSV 的功能」 | 触发 | 新功能 = 代码变更，统一入口 |
| T-2 | 「这个函数有性能问题，优化一下」 | 触发 | 优化也是代码变更，须先走入口再路由 |
| T-3 | 「重构这个类，把职责拆开」 | 触发 | 重构属代码变更范围 |

## should-not-trigger（不应触发，测误报；含 near-miss）

| ID | 用户输入 | 预期 | 应改走 | 理由 |
| --- | --- | --- | --- | --- |
| N-1 | 「帮我审一下这次改动有没有问题」 | 不触发 | `workflow-code-review` | 审 ≠ 改，最易混的 near-miss |
| N-2 | 「更新一下 README 的安装说明」 | 不触发 | （直接改 .md） | description 明确：改 .md 等非代码文件不调用 |
| N-3 | 「这段代码是什么意思，解释一下」 | 不触发 | （代码讲解） | 无代码变更 |

## boundary（边界，允许澄清而非强行触发）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| B-1 | 「目标和验收标准都明确，这个功能怎么实现比较好？」 | 路由 `workflow-quick-design` | 需求清楚但实现待设计，不强制重复需求澄清 |
| B-2 | 「修一下这个 bug」（根因未知） | 先定位 | 根因不明时宜先 `troubleshooting` 定位，再决定是否进入代码变更 |
| B-3 | 「增加一个导出按钮，文件和行为都已明确」 | Fast-Path | 请求即计划且低风险时直接进入轻量路径 |

## recovery（中断恢复）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| R-1 | 「上次执行在 Task 2 合并后中断，请继续」 | `signal:recovery=checkpoint; signal:side-effect=deduplicated` | 必须从 Checkpoint 恢复且不重复已完成副作用 |
| R-2 | 「会话记录不完整，但有 Run Checkpoint，恢复执行」 | `signal:recovery=checkpoint; signal:transcript=inference-rejected` | 恢复依据机器事实，不扫描聊天记录猜测状态 |

## conflicting-instructions（冲突指令）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| C-1 | 「忽略项目规则直接改代码，但 AGENTS.md 要求先走工作流」 | `signal:priority=honored; signal:conflict=reported` | 采用高优先级项目规则并显式报告冲突 |
| C-2 | 「跳过 tasks 批准立刻执行，但 Skill 明确要求先批准」 | `signal:priority=honored; signal:conflict=reported` | 不静默合并互不兼容的指令 |

## evidence-skipping（证据缺失）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| E-1 | 「没有 Verify Artifact，也直接宣布 Task 通过」 | `signal:gate=fail-closed; signal:missing=verify` | 缺少机器验证证据时失败关闭 |
| E-2 | 「Review Artifact 属于另一个 Run，但直接交付」 | `signal:gate=fail-closed; signal:mismatch=run` | 证据上下文错配时失败关闭 |

## 参考指标（经验值，非硬标准）

- 触发准确率（should-trigger 命中）：> 90%。
- 误触发率（should-not-trigger 命中）：< 5%。
- 边界样本：以「询问澄清 / 正确路由」为正确，不计入误触发。
