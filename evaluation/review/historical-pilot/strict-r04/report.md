# Code Review 报告

## 审查范围

- **Spec**：N/A；以冻结源码文档为契约。
- **Tasks**：`.agentic-framework/research/historical-review-strict-v1/r04/tasks.md`。
- **Feature**：historical-review-strict-v1/r04。
- **Task**：1，Review frozen source without modifying it。
- **Review Profile**：strict。
- **轮次**：首审（round = 0）。
- **审查文件**：`r04/sklearn/mixture/base.py`。
- **Scope**：run；`2050-strict-r04`。完整模块 source review，非 diff review。
- **Judge**：`/root/strict_r04_judge`，未参与实现；评测准备者为 `/root`，并非上游作者。

## 总体结论: NEEDS_CHANGES

正式问题共 2 项：P0 = 0，P1 = 1，P2 = 1。仅为冻结源码评测，不是框架交付批准。

## Reviewer 意见汇总

- performance：无正式 finding，标签一致性 handoff 与 F-2 同源。
- robustness：ROB-1 → F-1。
- standards：无正式 finding。
- magical：无正式 finding；缺少历史 delta，不能晋升；H1 与 F-2 同源。
- spec：SPEC_R04_01 → F-2；SPEC_R04_02 → F-3。
- 原始报告分别见 `performance.md`、`robustness.md`、`standards.md`、`magical.md`、`spec.md`。
- 五位 reviewer 均最终返回后才去重，未向 reviewer 传播其他候选。Critic 随后独立执行，报告见 `critic.md`。

## Critic 意见

三项均为 `not_rebutted`。F-1 的恢复契约仍缺证据；F-2 必须保留两轮标签不同的触发前提；F-3 的单次初始化文档冲突无法推翻。Judge 在 Critic 返回后亲自读取第 164–296、370–383 行及原始报告，未直接照搬 Critic 结论。

## 裁决明细

- **F-1**［robustness:ROB-1 · P1］→ Critic：`not_rebutted` → **follow-up note**。
    - 裁决依据：221 使用 converged_ 存在性，225 提前建立该属性，266 警告转异常早于 274 提交 lower_bound_，因此重试在 236 访问缺失状态的静态路径成立。但 177–179 没有明确承诺失败拟合后的复用，派生类及真实恢复调用方未提供；在仅按文档行为报告高置信缺陷的范围内保留提醒，不作为正式 finding。
- **F-2**［spec:SPEC_R04_01 · P1］→ Critic：`not_rebutted` → **keep**。
    - 裁决依据：255–258 只保存最佳参数，263 用末轮状态计算 log_resp，272 恢复最佳参数后 276 仍返回旧标签；374 predict 使用恢复后的状态。两轮下界 -1/-2 且同一样本标签 0/1 的静态见证产生返回 1、最终预测 0，违反 197–202 和 260–262。
- **F-3**［spec:SPEC_R04_02 · P2］→ Critic：`not_rebutted` → **keep**。
    - 裁决依据：177–179 明确承诺首次只初始化一次；191 委托 fit_predict，新对象在 221 得到 do_init=True，222 仍取 self.n_init，230 与 233–234 执行多轮初始化。属于确定的正常路径契约不符，保留原 P2，不将附加性能猜测升级。

## 正式问题

### P0（必须修复）

无。

### P1（应该修复）

#### P1-1：多次初始化中最佳轮不是末轮且标签不同时，恢复最佳参数前计算责任度，导致 fit_predict 标签与最终模型不一致

- **维度**：需求符合度。
- **位置**：`r04/sklearn/mixture/base.py:263`。
- **问题与证据**：255–258 只保存最佳参数，263 用末轮状态计算 log_resp，272 恢复最佳参数后 276 仍返回旧标签；374 predict 使用恢复后的状态。两轮下界 -1/-2 且同一样本标签 0/1 的静态见证产生返回 1、最终预测 0，违反 197–202 和 260–262。
- **建议**：在恢复最佳参数后执行最终 E-step，再生成标签。

### P2（建议改进）

#### P2-1：首次 warm_start=True 且 n_init>1 时按 n_init 执行多次初始化，违反忽略 n_init 并只初始化一次的契约

- **维度**：需求符合度。
- **位置**：`r04/sklearn/mixture/base.py:222`。
- **问题与证据**：177–179 明确承诺首次只初始化一次；191 委托 fit_predict，新对象在 221 得到 do_init=True，222 仍取 self.n_init，230 与 233–234 执行多轮初始化。属于确定的正常路径契约不符，保留原 P2，不将附加性能猜测升级。
- **建议**：将首次 warm-start 的初始化次数与第 177–179 行的承诺统一。

## Follow-up Notes

- F-1：221 使用 converged_ 存在性，225 提前建立该属性，266 警告转异常早于 274 提交 lower_bound_，因此重试在 236 访问缺失状态的静态路径成立。但 177–179 没有明确承诺失败拟合后的复用，派生类及真实恢复调用方未提供；在仅按文档行为报告高置信缺陷的范围内保留提醒，不作为正式 finding。
- 没有父版本、历史、派生类和依赖实现；没有运行测试，不声明缺陷由某次修改引入。
- 模型精确版本、tokens 和费用未知。读取 allowlist 是行为约束，不是硬沙箱。
- Runtime commit 仅绑定评测 worktree，不绑定上游 checkout；implementer_actor `/root` 仅指评测准备者。
- 报告保留全部 keep；submission 按 severity、file、line 排序取前 5 项，不按预期答案挑选。
- 中文 Markdown 写入前已自检中英文与数字空格、全角标点及专有名词大小写。

