# strict 补测试验协议

## 状态与范围

2026-10-25 冻结，尚未完成全部实验。沿用原 r01～r04 的源码和审查请求，旧普通组、standard 组不重写；它们仅作历史对照，不宣称同批随机对照或等计算预算。

- 新计划摘要：`32f48703b0ab18fc190b91bd7233170579a6774f47e61bedc17d2f653cfe492a`。
- 计划目录：`.agentic-framework/evaluation/historical-review-strict-v1/`。
- 输入目录：`.agentic-framework/research/historical-review-strict-v1/<案例>/input.json`。
- 原始结果目录：`.agentic-framework/evaluation/historical-review-strict-raw-v1/<案例>/`。
- 每个案例单独通过现有 `workflow_control.py init-run` 创建真实 Run：`2050-strict-r01` 至 `2050-strict-r04`。
- Run 的 commit 绑定评测工作树，不代表上游完整检出；待审代码另由评测计划冻结。Run 初始化成功不代表交付门通过。

## 执行合同

1. 每案使用全新、无继承对话的独立 Judge。Judge 派发五个角色：performance、robustness、standards、magical-prompt、spec-compliance。并发槽位不足时分批执行，不省略角色。
2. 所有 reviewer 返回后再去重；有候选才派独立 Critic；Judge 独立阅读源码后逐条给出 keep、drop 或 follow-up。
3. 各 reviewer 最多 12 次只读工具调用、最多 5 条候选。Critic 与 Judge 各最多 12 次源码检查调用，编排和持久化调用不计入源码检查预算。
4. 全部候选、反驳、裁决原样保留。完整审核报告保留所有 keep；评测提交最多 5 条，按严重度、文件、行号排序截取，不按目标答案筛选。
5. 冻结实际 workflow、六份角色定义及编码、性能技能；被测者只读白名单导出及自己的 Run Context，不读取私有目标、旧输出、补丁和其他案例。不联网、不执行待审代码。
6. 这是完整模块的源码审查，不是 PR diff。缺少父版本、调用上下文或历史时明确记录限制；特别是契约角色不得编造变更增量证据。
7. 模型继承当前宿主配置；服务端精确版本不可观测。费用和 token 未知时为 null。白名单是提示约束，不是硬隔离。
8. 审查发现上游问题即形成实验结果，不修复上游代码，不把 NEEDS_CHANGES 当作实验失败，也不启动修复复审循环。

## 判定与比较

目标检出按原冻结答案统计，候选阶段与最终阶段分别统计，检查 Critic／Judge 是否误删正确发现。清单外发现单列为有依据、错误或待定，不因未命中目标就算误报。独立 AI 裁定仍需标明非人工验收。

四例各一次不足以证明统计显著、泛化有效或团队知识有效。本轮先补齐严格流程证据，不以角色数代替效果，也不把较高计算量的收益全部归因于技能设计。
