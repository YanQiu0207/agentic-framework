# r04 工程规则专项审查

Using bp-coding-best-practices

## 结论

未发现同时满足「明确工程规则依据」和 scope 中 actionable correctness 要求的本维度问题。

```json
{"findings": []}
```

候选数量：0。无候选需要填写 id、title、file、line、severity 或触发链。

## 审查依据与覆盖

- 角色依据：`input.json` 的 `knowledge.conventions` 中 `materials/agents/standards-reviewer.md`，要求「无规则不立案」，且不报告其他维度的正确性、健壮性和性能问题。
- 技能依据：同一输入嵌入的 `materials/skills/bp-coding-best-practices/SKILL.md`。已检查命名、函数设计、控制流、资源安全、注释与可观测性规则；不将纯风格建议提升为缺陷。
- 范围依据：同目录 `scope.md` 要求审查完整源码中的可操作正确性缺陷，排除纯风格及无证据要求；`tasks.md` 指定冻结源码审查、不修改源码。
- 源码覆盖：完整阅读 `r04/sklearn/mixture/base.py:1–536`，包括输入校验、参数初始化、拟合、预测、采样、概率估计和 verbose 输出。
- 规则对照证据：`r04/sklearn/mixture/base.py:32–60` 和 `92–116` 的失败检查直接抛出异常；`143–155`、`340`、`422–441`、`503–507` 复用已有聚类、概率计算和随机采样实现；`505–508` 使用上下文管理器限制数值错误设置的作用域。未从这些路径证成应报告的工程规则违规。

## 隔离与限制

- 只读调用共 4 次：全局 AGENTS/RTK；本案例 tasks、scope 和输入；抽取嵌入角色、技能及完整带行号源码；核对嵌入材料名称。第二次输出被截断，第三次已完整读取本维度必需材料及源码。
- 仅读取获准文件，未读取其他案例、历史、其他 reviewer 产物或真实源码路径；未联网、未执行目标源码、未启动子代理。
- 技能引用的 `reference/readability.md` 和 `reference/safety.md` 未嵌入输入，受读取边界约束未另行读取，不将其未知内容作为规则证据。
- 没有 diff 或父版本，仅作完整模块 source review，不声称问题属于 introduced、widened 或其他变更归因。
- 本结论仅表示本维度未证成候选，不代表整个模块不存在其他维度的问题，也不构成集成批准。
- 写入前已自检中文 Markdown 的中英文空格、中文与数字空格、全角中文标点和专有名词大小写。
