# 实施任务清单

> 由 `spec.md` 生成  
> 任务总数：2  
> 核心原则：先固定契约，再扩展解析器并用真实会话验收。

## 依赖关系总览

```text
Task 1（固定报告契约）
  ↓
Task 2（解析、测试与账本验证）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-review/SKILL.md` | 修改 | Task 1 | 补充归因字段 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 1 | 固定交付归因格式 |
| `scripts/analyze_session_metrics.py` | 修改 | Task 2 | 解析任务归因 |
| `scripts/test_analyze_session_metrics.py` | 修改 | Task 2 | 增加回归测试 |
| `docs/11-session-telemetry.md` | 修改 | Task 2 | 更新契约和演进状态 |
| `metrics/session-history.jsonl` | 修改 | Task 2 | 更新真实会话账本 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| Code Review 报告模板 | 增加字段 | 遥测与人工阅读 | Task 1 |
| 统一交付证据格式 | 增加固定区块 | 遥测解析器 | Task 1、Task 2 |
| `analyze_session()` 返回值 | 增加字段 | JSON 输出与账本 | Task 2 |

### 构建系统变更

- 无。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | 旧会话没有任务归因区块 | Task 2 | 返回空列表，不推测 |
| 2 | 同一任务可能多次输出交付归因 | Task 2 | 按 feature/task 保留最后一份 |

## 任务列表

### 任务 1：[x] 固定任务归因报告契约

- 状态：完成
- 文件：`skills/workflow-code-review/SKILL.md`（修改）、`skills/workflow-code-generation/SKILL.md`（修改）
- depends_on：[]
- review_profile：standard
- spec 映射：2.1、2.2、2.3
- 说明：补齐 review 定位字段，并定义机器可解析的交付归因区块。
- context_files：
    - `skills/workflow-code-review/SKILL.md` — review 固定模板
    - `skills/workflow-code-generation/SKILL.md` — 交付证据格式
    - `docs/11-session-telemetry.md` — 格式即接口约束
- verification：
    - [x] `python scripts/lint_skill_graph.py` 返回 0
    - [x] 固定模板包含 spec 规定的 6 个归因字段
- artifacts：
    - `skills/workflow-code-review/SKILL.md`
    - `skills/workflow-code-generation/SKILL.md`
- 子任务：
    - [x] 1.1：扩展 review 报告审查范围字段
    - [x] 1.2：增加固定任务归因交付区块

### 任务 2：[x] 扩展解析器并完成真实账本验证

- 状态：完成
- 文件：`scripts/analyze_session_metrics.py`（修改）、`scripts/test_analyze_session_metrics.py`（修改）、`docs/11-session-telemetry.md`（修改）、`metrics/session-history.jsonl`（修改）
- depends_on：[Task 1]
- review_profile：standard
- spec 映射：1、2.1、2.2、2.3
- 说明：解析固定归因区块，覆盖兼容和去重测试，执行真实 review 后更新账本。
- context_files：
    - `scripts/analyze_session_metrics.py:extract_reviews()` — 现有固定报告解析方式
    - `scripts/analyze_session_metrics.py:analyze_session()` — 会话结果组装
    - `scripts/test_analyze_session_metrics.py` — 回归测试入口
    - `metrics/session-history.jsonl` — 下游账本
- verification：
    - [x] `python -m unittest scripts/test_analyze_session_metrics.py` 返回 0
    - [x] `python scripts/lint_skill_graph.py` 返回 0
    - [x] 对真实会话运行 `--history` 后，新 review 轨迹不出现「?」
- artifacts：
    - `scripts/analyze_session_metrics.py`
    - `scripts/test_analyze_session_metrics.py`
    - `docs/11-session-telemetry.md`
    - `metrics/session-history.jsonl`
- 子任务：
    - [x] 2.1：实现归因区块解析与去重
    - [x] 2.2：补充正常、旧格式和重复记录测试
    - [x] 2.3：运行真实 review 和账本更新

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
| --- | --- | --- |
| 1 | Task 2 | 验收解析、兼容和真实账本 |
| 2.1 | Task 1、Task 2 | 固定报告并消费契约 |
| 2.2 | Task 1、Task 2 | 定义并实现归因模型 |
| 2.3 | Task 1、Task 2 | 落实不推测和职责边界 |
