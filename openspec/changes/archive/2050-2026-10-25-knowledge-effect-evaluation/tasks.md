# 团队知识效果评测实施任务

## 依赖关系总览

Task 1：独立评测闭环、合成案例与测试；一个内聚切片，无并行写入。

## 变更影响概览

- 新增 `scripts/agent_eval.py`、`scripts/test_agent_eval.py` 和必要的同名前缀辅助模块。
- 新增 `evaluation/review/` 的 JSON 配置、公开样例、私有预期问题及 README。
- 新增长期知识 `openspec/specs/backend/engineering/tech/agent-evaluation.md`，更新两级知识索引。
- 不改现有适配器、历史基准、验证配置、模型调用、安装器与治理门禁。

## 风险与假设

- 实际宿主和费用预算尚未确认，首版采用公开请求与导入产物模式，不声明已自动运行 Agent。
- 用户确认 Review 优先修订；不实现 Docker 或运行生成代码，保留 strict 最终审核。
- 模拟执行只证明框架合同，不构成真实知识增益证据。

## 任务列表

### 任务 1：[x] 构建通用评测与 Review 首例
- 状态：完成（恢复 Run verify-run PASS、独立review round1 PASS，实际任务完成；不声明原 Journal 修复）
- attempts：2
- control_stage：completed
- 文件：`scripts/agent_eval.py`、`scripts/test_agent_eval.py`、`evaluation/review/`、`openspec/specs/backend/engineering/tech/agent-evaluation.md`、`openspec/index.md`、`openspec/specs/index.md`
- depends_on: []
- review_profile: strict
- 文档映射：review-first-amendment.md 全部章节（优先于原 proposal）
- context_files:
  - `scripts/evaluation_runner.py`
  - `scripts/benchmark_runner.py`
  - `scripts/harness_runtime.py`
  - `scripts/swebench_runner.py`
- verification:
  - [x] `python -m pytest scripts/test_agent_eval.py -q` 通过。
  - [x] 配置驱动全量 Verify 与 Spec Drift 检查通过。
  - [x] 独立审核检查隐藏答案隔离、路径边界、执行许可与配对指标。
- artifacts:
  - `scripts/agent_eval.py`
  - `scripts/test_agent_eval.py`
  - `evaluation/review/README.md`
  - `openspec/specs/backend/engineering/tech/agent-evaluation.md`
- 子任务：
  - [x] 1.1 实验契约、公开请求和不可覆盖快照。
  - [x] 1.2 人工裁定、Review 评分与配对报告。
  - [x] 1.3 合成代码案例、失败路径与编码测试。
  - [x] 1.4 知识同步、全量验证与审核。

## 文档覆盖映射

| 文档 | 任务 |
| --- | --- |
| proposal.md §1～4 | Task 1 |

## 知识同步

目标为 `openspec/specs/backend/engineering/tech/agent-evaluation.md`，状态 Completed；两级索引已更新，历史案例证据见 evaluation/review/historical-pilot/。

## 知识冲突

既有 Comet 研究中「本框架无机器验收」表述过于绝对；本次不修改旧文档，只在新增知识区分原有合同评测与新实验执行层。

## 实际 Diff 核对

新增实验脚本、专项测试、合成样例与真实历史试点证据；两项既有测试仅补 Profile 参数；更新长期知识和索引。未改适配器、旧评测、配置或生产门禁。最终证据由 recovery Run 提供，详见 verification-notes.md。

## 状态纠正

2026-10-25：用户授权修复旧测试后，误用 manual_resolved 产生完成状态；该命令语义不是恢复执行。实际测试与审核未完成，已纠正为进行中，保留 Journal 原事件，不把它作为交付证据。授权范围补充 scripts/test_knowledge_management_e2e.py 与 scripts/test_workflow_control.py 的两处 Profile 声明。
