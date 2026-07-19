# Harness Capability Matrix 与 Adapter 合同

本目录只声明统一能力词汇和未验证默认值，不凭静态文档断言 Codex 或 Claude Code 当前版本具备某项能力。`capabilities/codex.json` 与 `capabilities/claude-code.json` 使用完全相同的能力集合和三态：`supported`、`degraded`、`unsupported`。

静态声明中的 `unsupported` 表示「启动前尚无可执行证据」，不是产品能力结论。运行时必须由具体 Harness Adapter 执行探测；探测结果覆盖静态默认值，并在报告中保留证据来源。

## Adapter JSON 合同

Runner 通过标准输入发送单个 JSON 对象：

```json
{
    "contract_version": 1,
    "operation": "probe",
    "payload": {}
}
```

第一版支持两种操作：

- `probe`：返回完整能力集合、三态和非空证据说明。
- `evaluate`：执行 Tier 1 行为用例，返回 Transcript 和确定性信号。

Adapter 只负责宿主调用、Transcript 和工具结果转换；Workflow 只消费统一接口，不包含 Codex 或 Claude Code 产品分支。

## 启动门

```text
python scripts/harness_runtime.py --declaration harness/capabilities/codex.json --adapter <adapter> --required subagents --optional transcript_access --run-id <run-id> --output <probe-report.json>
```

- 必需能力只有 `supported` 才放行；`degraded` 和 `unsupported` 都失败关闭。
- 可选能力为 `degraded` 或 `unsupported` 时继续执行，但生成 `capability-degraded` 证据记录。
- Adapter 未返回完整词汇、合法状态或证据时，探测整体失败，不回退到静态猜测。
- 进入最终 Trust Gate 的探测报告必须使用 `--run-id` 绑定本次 Run；旧的无 Run 绑定报告可单独查看，但不能作为最终放行证据。
