Using workflow-code-review
Using bp-coding-best-practices

## standards-reviewer 原始报告

- **Agent ID**：`/root/strict_r03_judge/standards`
- **审查文件**：`r03/src/_pytest/logging.py`（`input.files` 提供的完整源码）
- **审查方式**：静态只读源码审查，非 diff 审查。
- **读取调用数**：3 次文件读取；另有 1 次 `rtk --help`，合计 4 次只读工具调用。
- **候选 finding 数**：0。

### 结论

✅ 本维度无可报告 finding。

已核对所提供的完整源码与 `input.knowledge.conventions` 中的 `standards-reviewer`、`bp-coding-best-practices` 规则。本次只接受正确性缺陷，而工程规范角色要求「无规则不立案」且不得将正确性、健壮性等其他维度的问题改装为工程规则问题。未建立同时满足「明确适用的工程规则违反」和「具体正确性影响」的高置信度证据链。

### 依据与限制

- 规则来源：`input.knowledge.conventions["materials/agents/standards-reviewer.md"]` 的「职责」与「硬性规则」。
- 范围来源：`r03/scope.md` 要求只报告可行动的正确性缺陷，不报告纯风格偏好或推测性要求。
- 已阅读 `r03/tasks.md`、完整冻结源码及所需内嵌 skill。
- 没有将审查宿主的 `AGENTS.md` 当作被审查 pytest 源码的上游规范。
- 未提供上游项目专用工程规范、diff 或历史；不能证明违反未提供的规范，也不声明缺陷由某次改动引入。
- 未执行源码、测试或联网；没有读取其他 reviewer 的候选报告。
- 本结论仅限工程规范维度，不表示其他维度不存在正确性缺陷，也不是集成放行裁决。
