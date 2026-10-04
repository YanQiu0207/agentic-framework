# workflow-verification 触发评估用例

> 评测体系 Tier 1（触发评估），对应 [docs/tooling/08-evaluation-strategy.md](../../../docs/tooling/08-evaluation-strategy.md) §5.1。
> 目标：验证「机器验证门」在该跑客观门禁时被召回，且不与「LLM 审查 / 写测试 / 改代码」混淆。
> 判定（确定性）：执行 transcript 是否出现首行标记 `Using workflow-verification`。

## should-trigger（应触发，测召回）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| T-1 | 「跑一下机器验证门 / 验证一下」 | 触发 | 用户直接要求跑客观验证 |
| T-2 | 「这次改动到底算不算真做完了，客观判一下」 | 触发 | 「是否真做完」正是本门的职责（机器绿灯而非口头背书） |
| T-3 | 「合入前帮我过一遍 build / test 门禁」 | 触发 | merge 前与 review 并列的硬门 |

## should-not-trigger（不应触发，测误报；含 near-miss）

| ID | 用户输入 | 预期 | 应改走 | 理由 |
| --- | --- | --- | --- | --- |
| N-1 | 「帮我审一下代码质量和设计」 | 不触发 | `workflow-code-review` | LLM 多维审查，不是机器门 |
| N-2 | 「给这个模块补单元测试」 | 不触发 | `workflow-test-generation` | 写测试 ≠ 跑验证门 |
| N-3 | 「帮我修掉这个编译错误」 | 不触发 | `workflow-code-generation` | 改代码，不是验证 |

## boundary（边界，允许澄清而非强行触发）

| ID | 用户输入 | 预期 | 理由 |
| --- | --- | --- | --- |
| B-1 | 「跑一下测试」 | 先澄清 | 可能只想临时跑 pytest，未必要过整个 merge 门——确认是单跑测试还是过门禁 |
| B-2 | 「检查一下代码有没有问题」 | 先澄清 | 「问题」歧义：机器可验问题（本门）还是设计 / 逻辑问题（review），需厘清 |

## 参考指标（经验值，非硬标准）

- 触发准确率（should-trigger 命中）：> 90%。
- 误触发率（should-not-trigger 命中）：< 5%。
- 边界样本：以「询问澄清」为正确，不计入误触发。

## behavior（行为用例，change 2048；逐条演练 v2 主体绑定）

| ID | 场景 | 预期行为 | 理由 |
| --- | --- | --- | --- |
| S-1 | standalone Verify 正常完成 | 顶层 `schema_version: 2` + `subject_id`，检查前后主体一致 | v2 合同 |
| S-2 | 检查运行期间输入被编辑 | 追加 native-subject error 结果，verdict=ERROR，不能 PASS | 改动中结果无效 |
| S-3 | 非 VCS 目录或无法绑定主体 | 退出码 2，不写报告 | 失败关闭，不产出无主体报告 |
| S-4 | Verify 配置缺失的仓库 | 主体覆盖不完整 → ERROR，提示先完成配置选择 | 覆盖不完整不发完整 PASS |
| S-5 | 交付门消费 Verify | 门以 `--subject-base` 重算当前内容，三方（Review/Verify/当前）一致才放行 | 交付前编辑会被拒 |
| S-6 | Runtime 路径（--run-dir） | 仍产出 v1 Envelope Run-bound Artifact，行为不变 | Runtime v1 合同保留 |
