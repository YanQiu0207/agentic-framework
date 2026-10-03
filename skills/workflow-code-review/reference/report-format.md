# 审查报告格式

生成最终报告前读取。Markdown 标题、轮次和 JSON 字段供遥测与交付脚本解析，保持原格式。

### 7. 输出最终报告

按以下模板输出（整个系统唯一固定格式）。该模板同时是遥测质量账的解析接口（见 [11-session-telemetry.md](../../../docs/tooling/11-session-telemetry.md)），「轮次」字段与复审报告的「（新增）」标记是指标数据源，不得省略：

```markdown
# Code Review 报告

## 审查范围
- **Spec**: [路径 或 N/A]
- **Tasks**: [路径 或 N/A]
- **Feature**: [feature 标识 或 N/A]
- **Task**: [ID/名称 或 N/A]
- **Review Profile**: lightweight / standard / strict
- **轮次**: 首审 / 复审第 N 轮
- **审查文件**: [文件列表]

## 总体结论: PASS / NEEDS_CHANGES

## 裁决明细

> 对每条候选 finding 的最终处置和理由，完整展示审查过程的透明度。

- **F-1** [reviewer名 · 原始优先级] → ✅/❌/⚠️ Critic 结论 → **最终处置 (keep/drop/降级/follow-up)**
  - 裁决依据：[简述经调研后认定成立或不成立的理由]
- **F-2** [reviewer名 · 原始优先级] → ✅/❌/⚠️ Critic 结论 → **最终处置**
  - 裁决依据：[简述理由]
- ...

## 正式问题

### P0（必须修复）

#### P0-1: [问题标题]
- **维度**: [来源维度]
- **位置**: `file:line`
- **问题**: [描述]
- **证据**: [关键证据]
- **建议**: [修复方式]

### P1（应该修复）
...

### P2（建议改进）
...

## Follow-up Notes
- [少量不够进入正式 finding 但值得提醒的事项]
```

#### 机器可读产物

输出 Markdown 报告的**同一步**，Artifact 生成方额外产出一份机器可读 JSON；两者必须来自同一次裁决，`verdict`、P0／P1 数量和 `round` 必须一致。`lightweight` / `standard` 的生成方是 `comprehensive-reviewer`，`strict` 的生成方是独立 Judge；owner / implementer 只能原样持久化，不得手写。产物合同由交付路径决定，不能为了放行伪造 Run 字段：

| 交付路径 | JSON 位置 | 必填裁决字段 | Run Context 与可声明边界 |
| --- | --- | --- | --- |
| Native Delivery | `comprehensive-reviewer` 生成独立 `review-report.json`；编排方原样保存到建议路径 `.agentic-framework/review/review-integration.json`，并显式传给 `check_delivery.py` | 顶层 `verdict`、`p0_count`、`p1_count`、`scope: "integration"`、`review_profile: "standard"`、`round` | 不得提供 `run_id`、Harness、Trust Gate、Manifest 或严格独立 Judge 声明。 |
| 完整 Runtime Run | 独立 Judge 生成 `.agentic-framework/runs/<run-id>/artifacts/review-run.json` | Envelope `payload` 中的裁决字段，`scope: "run"`、`review_profile: "strict"` | 必须提供 `run-context.json`，可按 Runtime 合同声明 Run 绑定证据。 |
| Fast-Path 兼容别名 | `comprehensive-reviewer` 生成独立 `review-report.json`，由编排方原样保存 | 顶层字段，`scope: "integration"`、`review_profile: "lightweight"` | 仅为迁移兼容；不是新的默认执行合同，也不得声明 Runtime 证据。 |

无 Run 的 Native Delivery 标准 Review 使用以下扁平 JSON；`check_delivery.py --native-delivery` 只接受这 6 个字段：

```json
{
    "verdict": "PASS",
    "p0_count": 0,
    "p1_count": 0,
    "scope": "integration",
    "review_profile": "standard",
    "round": 0
}
```

完整 Runtime Run 使用 Envelope，并从 `run-context.json` 复制 `run_id`、`profile`、`harness`、`commit_sha` 和 `config_digest`。缺少 Run Context 时，不得输出 `scope: "run"` 或 `review_profile: "strict"` 的可放行报告：

```json
{
    "schema_version": 1,
    "artifact_type": "review-report",
    "artifact_id": "review-run",
    "run_id": "<run-id>",
    "task_id": null,
    "attempt": null,
    "profile": "tooling",
    "harness": "codex",
    "producer": "workflow-code-review",
    "commit_sha": "<40-hex>",
    "config_digest": "sha256:<64-hex>",
    "created_at": "<RFC3339>",
    "payload": {
        "verdict": "PASS",
        "p0_count": 0,
        "p1_count": 0,
        "scope": "run",
        "review_profile": "strict",
        "round": 0,
        "implementer_actor": "<implementer-agent-id>",
        "judge_actor": "<judge-agent-id>",
        "independence_basis": "process-separated-agent"
    }
}
```

| 字段 | 取值 | 来源 |
| --- | --- | --- |
| `verdict` | `PASS` / `NEEDS_CHANGES` | 与「总体结论」字段完全一致 |
| `p0_count` | 整数 | 「正式问题」区 P0 的数量（不含 P2、不含 Follow-up Notes） |
| `p1_count` | 整数 | 「正式问题」区 P1 的数量（不含 P2、不含 Follow-up Notes） |
| `scope` | `task` / `integration` / `run` | 与「审核 Scope」定义一致 |
| `review_profile` | `lightweight` / `standard` / `strict` | 与调用方传入的档位一致 |
| `round` | 整数 | 与「轮次」字段一致：首审为 0，复审第 N 轮记 N |
