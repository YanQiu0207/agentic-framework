# 真实任务基准

本目录记录用于比较 `fast-path`、`standard` 与 `strict` 路径的真实开发任务。它不替代测试、Verify 或 Code Review；其作用是把交付结果、返工和 Telemetry 成本放到同一份可比较数据中。

## 记录流程

1. 开始实现前，创建 `evaluation/real-task-cases/<task-id>/case.json`，固定任务标题、风险级别、路由和验收标准。
2. 完成交付后，在同目录写入 `outcome.json`，填写验收结果、Review 的 P0/P1 与轮次，并关联本次 Codex 或 Claude 会话。
3. 七天后更新 `follow_up.status`：`no-rework` 表示未返工，`reworked` 表示已确认返工；尚未到观察期使用 `pending`。
4. 每次更新 Telemetry 后生成汇总报告，再按路由比较结果。

## `case.json`

```json
{
    "schema_version": 1,
    "task_id": "2027-example",
    "title": "示例：修复 JSON 输出目录创建",
    "route": "fast-path",
    "risk_level": "low",
    "acceptance_criteria": [
        "首次运行无需预建目录",
        "相关 Python 测试通过"
    ]
}
```

`route` 只允许 `fast-path`、`standard` 或 `strict`；`risk_level` 只允许 `low`、`medium` 或 `high`。验收标准必须在开始时固定，禁止在得知结果后修改。

## `outcome.json`

```json
{
    "schema_version": 1,
    "task_id": "2027-example",
    "final_verdict": "accepted",
    "first_acceptance": true,
    "review": {
        "p0_count": 0,
        "p1_count": 0,
        "rounds": 1
    },
    "follow_up": {
        "window_days": 7,
        "status": "pending"
    },
    "session_refs": [
        {
            "source": "codex",
            "session": "<session-id>"
        }
    ]
}
```

`final_verdict` 只允许 `accepted`、`rejected` 或 `manual`。一个会话只能关联一个任务，避免重复累计 Token 和耗时。

## 命令

先持续采集会话指标：

```bash
python scripts/analyze_session_metrics.py \
    --codex-dir "$HOME/.codex/sessions" \
    --cwd "$PWD" \
    --profile tooling \
    --history .agentic-framework/metrics/session-history.jsonl \
    --json .agentic-framework/metrics/latest-report.json
```

验证一个完成记录：

```bash
python scripts/benchmark_runner.py validate \
    --case-dir evaluation/real-task-cases/2027-example
```

生成路由对比报告：

```bash
python scripts/benchmark_runner.py report \
    --cases-root evaluation/real-task-cases \
    --history .agentic-framework/metrics/session-history.jsonl \
    --output .agentic-framework/metrics/real-task-benchmark.json
```

报告会按路由统计首次验收率、最终验收率、Review P0/P1、Review 轮次、七天返工率、活跃耗时和四类 Token。观察期未结束的记录不计入返工率分母。
