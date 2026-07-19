# 003：Task/Run 质量门改用结构化证据文件校验

**状态**：Accepted

## 背景

Tooling 的 `workflow_control.py`（`quality_passed` 事件）与 Production 的 `validate_change.py`（OPSX038/OPSX032）当前都只信任自由文本自述放行质量门：前者接受任意 `--reason` 字符串即可让状态迁移进入 merge，后者只检查 `tasks.md` 里 `Task Review: PASS` / `Code Review: PASS` 一行文本。两者都无法察觉 Review 或 Verify 被跳过、遗漏或谎报——这是同一类信任链漏洞，出现在两个不同 Profile 的两个不同工具里。

## 决策

1. Tooling Task 级 `quality_passed` 新增必填 `--verify-report <path>`，读取并校验 `.agentic-framework/verify/report.json` 的 `verdict == "PASS"`。
2. Tooling Run 级 `check_delivery.py` 新增必填 `--review-report <path>`，读取并校验新引入的 `.agentic-framework/verify/review-report.json` 的 `verdict == "PASS"` 且 `p0_count == p1_count == 0`；该文件由 `workflow-code-review` Step 7 在现有 Markdown 报告之外额外产出。
3. Production `validate_change.py` 的 OPSX038（Task 级）与 OPSX032（集成级）同样要求 `tasks.md` 声明 `- Review Report: <path>` 字段，并校验对应文件满足同一契约。
4. 两个 Profile 统一到同一套证据文件字段：`verdict` / `p0_count` / `p1_count` / `scope` / `review_profile` / `round`。

## 放弃的方案

### review-report 直接挂在 Task 级 `quality_passed`

放弃原因：Tooling 故意把 Code Review 推迟到 Run 级才跑一次，以收敛「修复→review→新问题」循环的成本（见 `docs/tooling/adr/003-review-fix-loop-convergence.md`）。Task 级 `quality_passed` 触发时，Review 架构上还没有发生，强行要求证据文件会直接违反这条既有决策。因此 Review 证据门放在 Run 级 `check_delivery.py`，Verify 证据门才放在 Task 级 `quality_passed`。

### 一并修复 `validate_change.py` 的构建/测试执行记录自由文本校验（`_execution_record`，OPSX033/034）

放弃原因：与本次问题同类（同样是自由文本自述），但超出本次讨论范围。为避免范围蔓延导致改动难以评审，留作独立后续项，不在本次实现。

## 后果

- 新增必填参数/字段是破坏性变更：升级后若有仍在进行中的 Tooling/Production change 使用旧调用方式，会在下一次调用时因缺字段/缺参数报错，需要同步升级调用方式或补齐证据文件。
- 仍然无法验证 Review/Verify 结论的语义正确性——只能保证「有真实产物文件佐证」，不能保证该产物内容判断无误；Reviewer/Judge 主观误判不在本决策覆盖范围内。
- 两个 Profile 的质量门证据契约从此保持一致，后续新增质量门机制应优先复用同一套字段，而不是各自发明新的自述格式。

## 适用条件

适用于本仓库 Tooling（`workflow-code-generation`）与 Production（`opsx-code-generation` / `validate_change.py`）两条主执行链路的质量门。若未来引入新的质量门机制或第三个 Profile，需重新评估是否纳入同一套证据契约，而不是默认复用。

## 参考

- [项目知识库与跨项目公共知识库统一方案](../knowledge-management.md)
- [Feature Spec：质量门证据校验](../../../../../../docs/design-docs/framework/quality-gate-evidence/spec.md)
