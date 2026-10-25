# Code Review 报告

## 审查范围
- **Spec**：N/A。使用 scope.md、源码注释和模块接口作为行为基线。
- **Tasks**：`.agentic-framework/research/historical-review-strict-v1/r02/tasks.md`
- **Feature**：历史源码评测 r02。
- **Task**：任务 1。
- **Review Profile**：strict。
- **轮次**：首审（round = 0）。
- **审查文件**：`r02/django/db/models/sql/compiler.py`；`r02/django/db/models/sql/query.py` 为 supplied 调用链上下文。
- **方式**：完整模块 source review，不是 diff；无父版本或历史。未执行源码、测试或联网。

## 总体结论: NEEDS_CHANGES

P0：0；P1：2。仅代表限定源码审查结论，不是框架交付批准。

## Reviewer 意见汇总
- performance：无正式候选；原始报告 `performance.json`。
- robustness：2 条 P1；原始报告 `robustness.json`。
- standards：无正式候选；原始报告 `standards.json`。
- magical：无正式候选；原始报告 `magical.json`。缺少历史，未伪造 delta，7 项源代码义务保留原始网格。
- spec：1 条 P1，与 robustness 的空操作数问题合并；原始报告 `spec.json`。
- 收齐全部最终返回后才去重；3 条原始候选合并为 2 条。没有候选互传。

## Critic 对抗性验证
- F-1：`not_rebutted`。按运算符处理空集的保护存在，但发生在提前过滤之后。
- F-2：`not_rebutted`。所供 `Query.explain()` 直接消费生成器，没有空结果保护。
- 完整反驳尝试见 `critic.json`。Critic 未作最终裁决。

## 裁决明细
- **F-1**［robustness、spec · P1］→ Critic `not_rebutted` → **keep**。
  - Judge 亲读 `compiler.py:410–463、481–484` 和 `query.py:264–282、1716–1720`。第 414 行统一删除空操作数，令后续第 446–451 行无法执行必要空集处理。只剩一个 part 时，第 459 行生成 A 的 SQL，既不是 A 与空集的交集，也不是空集减 A。
- **F-2**［robustness · P1］→ Critic `not_rebutted` → **keep**。
  - Judge 亲读 `query.py:292–336、532–538` 和 `compiler.py:452–453、576–580、1062–1150`。clone 保留组合状态，explain 直接消费生成器。全空组合在添加 EXPLAIN 前抛出 EmptyResultSet；execute_sql 返回空迭代器，result[0] 必然越界。
- 没有 drop 或 follow-up 处置的正式候选；所有原始候选均可追溯到上述两项。

## 正式问题

### P0（必须修复）
无。

### P1（应该修复）

#### P1-1: 交集含空项或差集首项为空时，无条件删除空操作数使本应为空的结果返回其他查询的数据
- **维度**：健壮性、需求符合度。
- **位置**：`r02/django/db/models/sql/compiler.py:414`。
- **问题**：A 返回非空结果，E 为 set_empty() 查询时，intersection(A,E) 或 difference(E,A) 被编译成只查询 A。
- **证据**：第 412–415 行删除 E，第 435、445 行只生成 A 的 part，第 459 行单项拼接直接返回 A。第 446–451 行的注释和保护明确区别 UNION 与 DIFFERENCE 的空项语义。
- **前提**：支持对应运算的后端、相同投影、无排序分页；外层组合状态保留该操作数序列。未提供 QuerySet 层，不声称所有公共 API 均可触发。
- **建议**：保留操作数顺序，让已有的按运算符区分的空集处理生效，或提供语义等价的按类型处理。

#### P1-2: 解释静态空查询时，execute_sql 返回空迭代器但 explain_query 直接索引首项，导致 IndexError
- **维度**：健壮性。
- **位置**：`r02/django/db/models/sql/compiler.py:1146`。
- **问题**：解释静态空查询时，正常内部空集状态变为未处理的 IndexError。
- **证据**：全空组合在第 452–453 行抛 EmptyResultSet，第 1082 行返回 iter([])，第 1143 行得到空列表，第 1146 行无保护索引。query.py 第 532–538 行提供实际直接调用方。
- **建议**：显式处理解释结果为空的路径，避免未经检查索引首项。

### P2（建议改进）
无。

## Follow-up Notes
- 没有上游 spec、历史、外部 QuerySet 构造实现或数据库验证，不能确定缺陷引入时间或完整产品影响范围。
- magical 的未晋升义务留在原始报告；Judge 不将这些观察自行提升为新 finding。
- 本轮不修复上游代码、不复审；所有静态见证均非执行复现。
- Runtime commit 绑定评测 worktree，不是上游 checkout；implementer_actor `/root` 仅为评测准备者，不是上游作者。
- Judge 为 `/root/strict_r02_judge`，未参与实现。五位 reviewer 与 Critic 均为真实独立子 Agent，详见 `decisions.json` 和 `validation.json`。
- allowlist 为流程限制，不是硬沙箱；模型精确版本、tokens 和费用未知。

## Runtime 绑定
- run_id：2050-strict-r02。
- scope：run；profile：tooling；review_profile：strict；round：0。
- commit_sha：4eb6f91718dee2cb6ae905472f125363e1ad0955。
- P0：0；P1：2；verdict：NEEDS_CHANGES。
