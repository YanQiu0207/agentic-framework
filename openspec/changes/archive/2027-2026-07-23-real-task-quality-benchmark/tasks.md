# 实施任务清单

> 任务总数：3
> 核心原则：固定数据合同，再接入汇总和文档，最后统一验证。

## 依赖关系总览

```text
Task 1 → Task 2 → Task 3
```

### 任务 1：[x] 修复 Telemetry JSON 首次写入

- 状态: 完成
- depends_on: []
- review_profile: lightweight
- context_files: `scripts/analyze_session_metrics.py`、`scripts/test_analyze_session_metrics.py`
- verification: `python -m pytest scripts/test_analyze_session_metrics.py -q`
- artifacts: 自动创建父目录的 JSON 输出和回归测试

### 任务 2：[x] 实现真实任务基准与 Bash 文档

- 状态: 完成
- depends_on: [Task 1]
- review_profile: standard
- context_files: `scripts/benchmark_runner.py`、`scripts/analyze_session_metrics.py`、`evaluation/real-task-cases/README.md`
- verification: `python -m pytest scripts/test_benchmark_runner.py -q`
- artifacts: 案例与结果合同、路由对比报告 CLI、Bash 采集命令

### 任务 3：[x] 全量验证、Review 与归档

- 状态: 完成
- depends_on: [Task 2]
- review_profile: standard
- context_files: 本 Change 和全部实现文件
- verification: `python -m pytest scripts -q`、`git diff --check`
- artifacts: Verify 报告和 OCR re-review 结论
