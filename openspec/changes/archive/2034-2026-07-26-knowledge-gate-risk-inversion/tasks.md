# 实施任务清单

> 由 Quick Draft proposal.md 生成。
> 任务总数：3。
> 核心原则：先统一门禁行为与测试，再同步文档，最后执行全量验证。

## 依赖关系总览

Task 1（统一门禁与测试）
    ↓
Task 2（同步调用示例与长期 Specs）
    ↓
Task 3（全量验证与归档准备）

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 1 | 统一知识影响检查与路径名输出。 |
| `scripts/test_check_delivery.py` | 修改 | Task 1 | 四条路径的成功与失败回归。 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2 | Runtime Run 与 Scoped Delivery 示例同步参数。 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 2 | 记录统一知识影响门。 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 2 | 更新 Tooling 强制规则与 Verification 对照。 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `check_delivery.main()` | 交付参数校验收紧 | `workflow-code-generation/SKILL.md` 中的交付命令 | Task 1、Task 2 |

### 构建系统变更

- 无：纯 Python 标准库脚本仓库，使用 Pytest 与 Skill 图 Lint 验证。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | 原 Proposal 将 Scoped Delivery 视为遗漏路径，与代码不一致。 | Task 1 | 以代码为当前事实；保留 Scoped Delivery 回归测试与独立输出。 |
| 2 | Runtime Run 的既有调用可能缺少新参数。 | Task 1、Task 2 | 直接失败关闭；同步 Skill 示例。 |

## 任务列表

### 任务 1：[x] 统一知识影响门并补四路径回归

- 状态：完成
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：`proposal.md` §1、§2.1、§2.2、§2.3
- 说明：删除仅覆盖部分路径的条件变量，让 Runtime Run 与既有三条路径统一执行知识影响检查；按实际路径输出名称；补齐成功、缺参、空理由与非法值测试。
- context_files:
    - `skills/workflow-code-generation/scripts/check_delivery.py` — 参数解析、知识影响检查与交付输出。
    - `scripts/test_check_delivery.py` — 交付门测试夹具与路径行为回归。
    - `skills/workflow-code-generation/scripts/runtime_schema.py` — Native Delivery Verdict 对知识影响字段的消费方。
- verification:
    - [x] `python -m pytest scripts/test_check_delivery.py -q` 退出码为 0。
    - [x] 四条路径成功输出各自路径名和知识影响结论。
    - [x] 缺参、`none` 空理由与非法值均返回非 0。
- artifacts:
    - `skills/workflow-code-generation/scripts/check_delivery.py`
    - `scripts/test_check_delivery.py`
- 子任务:
    - [x] 1.1：统一四条路径的知识影响检查入口。
    - [x] 1.2：补 Runtime Run 与 Scoped Delivery 的回归夹具和断言。
    - [x] 1.3：运行定向 Pytest。

### 任务 2：[x] 同步 Tooling 调用示例与长期 Specs

- 状态：完成
- 文件：`skills/workflow-code-generation/SKILL.md`（修改）、`openspec/specs/backend/framework/quality-gates/overview.md`（修改）、`openspec/specs/backend/engineering/tech/framework-unification.md`（修改）
- depends_on: [Task 1]
- review_profile: standard
- 文档映射：`proposal.md` §1、§2.2、§3、§4
- 说明：以 Task 1 的最终参数合同更新 Runtime Run 与 Scoped Delivery 调用示例，并说明知识影响检查不再按路径豁免。
- context_files:
    - `skills/workflow-code-generation/SKILL.md` — Tooling 交付命令的权威调用示例。
    - `openspec/specs/backend/framework/quality-gates/overview.md` — Tooling Run 交付门长期说明。
    - `openspec/specs/backend/engineering/tech/framework-unification.md` — Tooling 强制规则与 Verification 对照。
    - `skills/workflow-code-generation/scripts/check_delivery.py` — 实现后的参数合同。
- verification:
    - [x] `python scripts/markdown_links.py openspec` 退出码为 0。
    - [x] `python scripts/lint_skill_graph.py` 退出码为 0。
    - [x] Runtime Run 与 Scoped Delivery 示例均包含 `--knowledge-impact`，且 `none` 示例如实包含理由。
- artifacts:
    - `skills/workflow-code-generation/SKILL.md`
    - `openspec/specs/backend/framework/quality-gates/overview.md`
    - `openspec/specs/backend/engineering/tech/framework-unification.md`
- 子任务:
    - [x] 2.1：更新交付命令示例。
    - [x] 2.2：更新长期 Specs。
    - [x] 2.3：运行 Markdown 链接与 Skill 图检查。

### 任务 3：[x] 执行全量验证并准备归档

- 状态：完成
- 文件：`.agentic-framework/verify/`（本地产物，不入库）、`openspec/changes/2034-knowledge-gate-risk-inversion/`（归档前状态更新）
- depends_on: [Task 1, Task 2]
- review_profile: standard
- 文档映射：`proposal.md` §1 验收标准、§3
- 说明：对完整变更运行配置驱动 Verification 和全量测试，记录知识同步、冲突核对与实际 Diff；归档只在全部门禁和统一 Review 完成后执行。
- context_files:
    - `verify.config.json` — 配置驱动 Verification 合同。
    - `skills/workflow-verification/SKILL.md` — 基线与报告生成方式。
    - `skills/workflow-code-generation/scripts/check_delivery.py` — Native Delivery 交付门。
- verification:
    - [x] `python -m pytest scripts -q` 退出码为 0。
    - [x] `python scripts/lint_skill_graph.py` 退出码为 0。
    - [x] 按 `workflow-verification` 生成 PASS 报告，且 `spec_drift` 为 PASS。
- artifacts:
    - `.agentic-framework/verify/report.json`
    - `openspec/changes/2034-knowledge-gate-risk-inversion/tasks.md`
    - `openspec/changes/archive/2034-2026-07-26-knowledge-gate-risk-inversion/`
- 子任务:
    - [x] 3.1：运行全量测试和配置驱动 Verification。
    - [x] 3.2：完成一次统一集成 Review。
    - [x] 3.3：归档 Change、提交本地 Git 并执行交付门。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §1 问题与目标 | Task 1、Task 2 | 统一检查、同步参数合同。 |
| `proposal.md` §1 验收标准 | Task 1、Task 3 | 定向回归与全量验证。 |
| `proposal.md` §2 设计方案 | Task 1、Task 2 | 实现与文档同步。 |
| `proposal.md` §3 知识影响 | Task 2、Task 3 | 长期 Specs 与归档核对。 |
| `proposal.md` §4 运维 | Task 2 | 无新增运维面，记录失败关闭行为。 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `quality-gates-overview` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Completed | 无需更新 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Completed | 无需更新 |

## 知识冲突

- 结论：Resolved。原 Proposal 将 Scoped Delivery 视为知识影响检查的遗漏路径；当前代码要求 Scoped Delivery 同时传入 `--native-delivery`，因此已有覆盖。Task 1 以代码为当前事实修正行为描述，并保留回归测试。

## 实际 Diff 核对

- 核对状态：Completed。实现修改 `check_delivery.py`、`test_check_delivery.py` 与 `test_runtime_workflow.py`；文档同步 `SKILL.md` 和两份长期 Specs。已运行 `python -m pytest scripts -q`（389 passed、21 skipped、135 subtests passed）、`python scripts/lint_skill_graph.py`（errors=0）、`python scripts/markdown_links.py openspec`（退出码 0）、配置驱动 Verification（PASS，`spec_drift` 为 PASS）和 standard 集成 Review（PASS，P0/P1=0）。
