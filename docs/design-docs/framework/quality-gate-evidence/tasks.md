# 实施任务清单

> 由 spec.md 生成
> 任务总数: 5
> 核心原则: 跨切面契约先行——先定义 `review-report.json` schema（Task 2），再让消费方（Task 3、4）接入；Task 1 复用已有 `report.json` schema，可与 Task 2 并行

## 依赖关系总览

```
Task 1 (workflow_control.py 加 --verify-report)          Task 2 (review-report.json schema，写入 workflow-code-review/SKILL.md)
        │                                                          │         │
        │                                                          ↓         ↓
        │                                          Task 3 (check_delivery.py 加 --review-report)
        │                                                          │
        │                                          Task 4 (validate_change.py OPSX038/OPSX032 加 Review Report 校验)
        │                                                          │
        └──────────────────────────┬───────────────────────────────┘
                                    ↓
                        Task 5 (文档同步：delegated-execution-guide.md /
                                 opsx-code-generation/SKILL.md /
                                 framework-features-status-and-comparison.md)
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | `quality_passed` 事件加 `--verify-report` 校验 |
| `scripts/test_workflow_control.py` | 修改 | Task 1 | 新增 4 类失败路径测试 |
| `skills/workflow-code-review/SKILL.md` | 修改 | Task 2 | Step 7 新增 `review-report.json` 输出契约 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 3 | 新增 `--review-report` 校验 |
| `scripts/test_check_delivery.py` | 修改 | Task 3 | 新增 4 类失败路径测试 |
| `scripts/validate_change.py` | 修改 | Task 4 | OPSX038/OPSX032 加 Review Report 字段校验 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 4 | 新增失败路径测试 |
| `skills/workflow-code-generation/reference/delegated-execution-guide.md` | 修改 | Task 5 | 同步 Phase 1/2 的调用方式说明 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 5 | 同步 `- Review Report:` 字段要求（如涉及） |
| `docs/framework-features-status-and-comparison.md` | 修改 | Task 5 | 更新「控制内核不会自行验证 Review/Verify 报告」结论 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `workflow_control.py event <id> quality_passed` CLI | 新增必填参数 `--verify-report` | `delegated-execution-guide.md` Phase 1 | Task 1, 5 |
| `check_delivery.py` CLI | 新增必填参数 `--review-report` | Fast-Path 步骤 8、标准流程步骤 6-8 | Task 3, 5 |
| `workflow-code-review` Step 7 输出 | 新增文件产出 `review-report.json` | Task 3、Task 4 消费该文件 | Task 2, 3, 4 |
| `validate_change.py` Delivery 阶段 | `tasks.md` 新增必填字段 `- Review Report:` | `opsx-code-generation` 流程 | Task 4, 5 |

### 构建系统变更

无——纯 Python 脚本与 Markdown 文档改动，无构建配置。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 现有正在跑的 Tooling/Production change 若在本次改动落地前已调用旧 CLI 契约，升级后会因缺字段/缺参数报错 | Task 1, 3, 4 | 假设当前仓库无其他活跃 change 依赖旧契约（本仓库当前工作区状态支持此假设）；若用户环境有其他项目已安装本框架且有活跃 change，需自行升级调用方式 |
| 2 | `review-report.json` 由 LLM（Judge）在 Step 7 手写产出，无独立脚本强制生成，字段名或数值可能被写错 | Task 2, 3, 4 | Task 2 必须在 SKILL.md 里给出与现有 Markdown「总体结论」字段的明确对应关系，降低手写偏差；机器侧只能校验「文件存在且形式合规」，不能校验内容真实性（已在 spec.md 2.5 声明为已知边界） |

## 任务列表

### 任务 1: [x] workflow_control.py 的 quality_passed 加 --verify-report 证据校验
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`（修改）、`scripts/test_workflow_control.py`（修改）
- depends_on: []
- review_profile: strict
- spec 映射：spec 章节 2.2、2.3、2.5
- 说明：`_build_arg_parser` 的 `event_parser` 新增 `--verify-report`（类型 `Path`，默认 `None`）。file IO 与 JSON 解析放在 `main()`/CLI 层（与现有 `_load(tasks_md)` 同层次），解析出的 `dict` 传入一个新的纯函数 `_validate_verify_report(report: dict) -> None`（不做文件 IO，方便单测直接构造 dict 调用），校验 `report.get("verdict") == "PASS"`，不满足则 `raise ValueError`。`apply_event`/`_handle_quality_passed` 在 `event == "quality_passed"` 时必须先调用该校验（可通过新增可选形参传入已解析的 report dict，或在 CLI 层调用 `apply_event` 前先校验——两种实现都可，但必须保证 `apply_event` 单测能不依赖真实文件直接验证校验逻辑）。`--verify-report` 缺失、文件不存在、JSON 解析失败、`verdict != "PASS"` 均需在 CLI 层给出清晰的 `error:` 前缀提示并以退出码 `2` 终止，不写入 `tasks.md`。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py:174-179` — `_handle_quality_passed`，本任务的核心改动点
  - `skills/workflow-code-generation/scripts/workflow_control.py:237-274` — `apply_event`，事件分发与校验入口
  - `skills/workflow-code-generation/scripts/workflow_control.py:557-588` — `_build_arg_parser`，CLI 参数定义
  - `skills/workflow-code-generation/scripts/workflow_control.py:591-644` — `main`，CLI 层文件 IO 与错误处理模式
  - `skills/workflow-verification/scripts/verify.py:776-793` — `.verify/report.json` 的 `verdict` 字段来源，本任务只读取不修改
  - `scripts/test_workflow_control.py` — 现有测试用例结构，新增测试需遵循同一风格
- verification:
  - [x] `python -m py_compile skills/workflow-code-generation/scripts/workflow_control.py`
  - [x] `python -m pytest scripts/test_workflow_control.py -q` 全部通过
  - [x] 新增测试覆盖：缺 `--verify-report`、文件不存在、JSON 非法、`verdict != "PASS"` 四类失败路径均返回非 0 且 `tasks.md` 未被写入
  - [x] 新增测试覆盖：`verdict == "PASS"` 时行为与改动前一致（不影响既有正常路径）
- artifacts:
  - `skills/workflow-code-generation/scripts/workflow_control.py`
  - `scripts/test_workflow_control.py`
- 子任务：
  - [x] 1.1: `_build_arg_parser` 新增 `--verify-report` 参数
  - [x] 1.2: 实现 `_validate_verify_report` 纯函数
  - [x] 1.3: 在 `quality_passed` 分支接入校验，CLI 层完成文件读取与错误提示
  - [x] 1.4: 调用 `workflow-test-generation` 为新增校验路径生成测试（覆盖正常路径 + 4 类失败路径）
  - [x] 1.5: 运行测试，全部通过

### 任务 2: [x] 定义 review-report.json schema 并写入 workflow-code-review/SKILL.md
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-review/SKILL.md`（修改）
- depends_on: []
- review_profile: strict
- spec 映射：spec 章节 2.4
- 说明：在 Step 7「输出最终报告」的现有 Markdown 模板之后，新增一段「机器可读产物」说明：Judge 在输出 Markdown 报告的同一步，额外写入结构化 JSON（路径由调用方通过上下文指定，Tooling/Production 场景建议 `.verify/review-report.json`），字段为 `verdict`（取值须与 Markdown「总体结论」字段一致）、`p0_count`、`p1_count`（分别统计正式问题区 P0/P1 数量，不含 P2/follow-up）、`scope`（`task`/`integration`/`run`，对应现有「审核 Scope」定义）、`review_profile`、`round`（首审 0，复审第 N 轮记 N，对应现有「轮次」字段）。必须明确：该 JSON 与 Markdown 报告的结论必须一致，不是独立判断。
- context_files:
  - `skills/workflow-code-review/SKILL.md:221-268` — Step 7 现有输出模板，本任务在其后补充章节
  - `skills/workflow-code-review/SKILL.md:36-41` — 「审核 Scope」定义，`scope` 字段取值需对齐
  - `skills/workflow-code-review/SKILL.md:203-219` — 「最终裁决」的 PASS/NEEDS_CHANGES 门槛，`verdict` 取值需对齐
  - `docs/design-docs/framework/quality-gate-evidence/spec.md` 2.4 节 — schema 定义来源
- verification:
  - [x] `python skills/workflow-code-generation/scripts/lint_skill_graph.py`（或仓库现有等价命令）无新增错误/警告
  - [x] 人工核对：新增说明的字段名、取值范围与 spec.md 2.4 节完全一致
  - [x] 人工核对：`verdict`/`p0_count`/`p1_count` 与现有 Markdown 报告的「总体结论」「正式问题」区可相互推导，不引入第二套判断标准
- artifacts:
  - `skills/workflow-code-review/SKILL.md`
- 子任务：
  - [x] 2.1: 在 Step 7 后新增「机器可读产物」章节，给出 JSON 示例
  - [x] 2.2: 核对字段与现有 Markdown 报告字段的对应关系，消除歧义表述

### 任务 3: [x] check_delivery.py 加 --review-report 证据校验
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: [Task 2]
- review_profile: strict
- spec 映射：spec 章节 2.2、2.3、2.5
- 说明：新增 `check_review_report(path: Path) -> list[str]` 函数（与现有 `check_tasks`/`check_spec` 同风格，返回错误信息列表），读取 JSON，校验文件存在、可解析、`verdict == "PASS"`、`p0_count == 0`、`p1_count == 0`；不满足则返回对应错误信息。`main()` 新增 `--review-report`（必填，类型 `Path`）参数，纳入现有 `for label, path, checker in (...)` 循环或单独调用，错误信息汇入现有 `errors` 列表，保持退出码语义不变（有 `errors` → 返回 1）。Fast-Path（无 `--tasks`/`--spec`）同样必须传 `--review-report`——不属于现有「仅检查工作区」的豁免范围。
- context_files:
  - `skills/workflow-code-generation/scripts/check_delivery.py` — 全文，新增校验函数与 CLI 参数
  - `scripts/test_check_delivery.py` — 现有测试结构（`CheckDeliveryTest` 各用例），新增用例需遵循同一风格
  - `skills/workflow-code-generation/SKILL.md` — Fast-Path 步骤 8、标准流程步骤 6-8 对 `check_delivery.py` 的调用点（本任务只读，用于确认参数契约，实际文档更新在 Task 5）
- verification:
  - [x] `python -m py_compile skills/workflow-code-generation/scripts/check_delivery.py`
  - [x] `python -m pytest scripts/test_check_delivery.py -q` 全部通过
  - [x] 新增测试覆盖：缺 `--review-report`、文件不存在、JSON 非法、`verdict != "PASS"`、`p0_count>0`、`p1_count>0` 六类失败路径均返回非 0
  - [x] 新增测试覆盖：`verdict=="PASS"` 且 P0/P1 均为 0 时，行为与改动前一致
- artifacts:
  - `skills/workflow-code-generation/scripts/check_delivery.py`
  - `scripts/test_check_delivery.py`
- 子任务：
  - [x] 3.1: 实现 `check_review_report` 函数
  - [x] 3.2: `main()` 接入 `--review-report` 参数与校验
  - [x] 3.3: 调用 `workflow-test-generation` 生成测试（正常路径 + 六类失败路径）
  - [x] 3.4: 运行测试，全部通过

### 任务 4: [x] validate_change.py 的 OPSX038/OPSX032 加 Review Report 字段校验
- 状态：完成
- 文件：`scripts/validate_change.py`（修改）、`scripts/tests/test_validate_change.py`（修改）
- depends_on: [Task 2]
- review_profile: strict
- spec 映射：spec 章节 2.2、2.3、2.5
- 说明：新增正则 `TASK_REVIEW_REPORT_RE`（匹配 `- Review Report: <path>`，风格对齐现有 `TASK_REVIEW_STATUS_RE`）。在 `_validate_tasks` 的 Task 级校验中（现有 OPSX038 判断附近，`validate_change.py:1057-1081`），`require_completed=True` 且 `Task Review` 为 `PASS` 时，额外要求存在合法 `Review Report` 字段且指向文件存在、可解析、`verdict=="PASS"`、`p0_count==0`、`p1_count==0`，不满足复用 `OPSX038` rule_id 追加 finding（沿用现有 `_finding` 辅助函数）。同理在 `_validate_delivery` 的 change 级 `Code Review` 校验中（`validate_change.py:1182-1204`，现有 `OPSX032`），`expected_review=="PASS"` 时额外要求变更头部存在 `- Review Report: <path>` 字段并做同样校验。两处校验逻辑应提炼为共用的 `_validate_review_report(path_text, repo) -> list[str]` 辅助函数，避免重复。
- context_files:
  - `scripts/validate_change.py:27-35` — 现有正则定义区，新增正则加在此处
  - `scripts/validate_change.py:1041-1081` — `_validate_tasks` 内 OPSX037/038 校验逻辑
  - `scripts/validate_change.py:1182-1204` — `_validate_delivery` 内 OPSX032 校验逻辑
  - `scripts/validate_change.py:124-134` — `_finding` 辅助函数，新增 finding 复用此签名
  - `scripts/tests/test_validate_change.py` — 现有测试结构，新增用例需遵循同一风格
- verification:
  - [x] `python -m py_compile scripts/validate_change.py`
  - [x] `python -m pytest scripts/tests/test_validate_change.py -q` 全部通过
  - [x] 新增测试覆盖：Task 级与 change 级各自的「缺字段」「文件不存在」「JSON 非法」「verdict 不是 PASS」「P0/P1>0」五类失败路径均产出对应 finding
  - [x] 新增测试覆盖：字段合法且文件满足条件时，不产出新增 finding（不破坏现有通过路径）
- artifacts:
  - `scripts/validate_change.py`
  - `scripts/tests/test_validate_change.py`
- 子任务：
  - [x] 4.1: 新增 `TASK_REVIEW_REPORT_RE` 正则与 `_validate_review_report` 共用校验函数
  - [x] 4.2: 接入 `_validate_tasks`（Task 级，OPSX038）
  - [x] 4.3: 接入 `_validate_delivery`（change 级，OPSX032）
  - [x] 4.4: 调用 `workflow-test-generation` 生成测试（两处校验点 × 五类失败路径 + 正常路径）
  - [x] 4.5: 运行测试，全部通过

### 任务 5: [x] 同步调用方文档与现状描述
- 状态：完成
- 文件：`skills/workflow-code-generation/SKILL.md`（修改）、`skills/workflow-code-generation/reference/delegated-execution-guide.md`（修改）、`skills/opsx-code-generation/SKILL.md`（修改）、`docs/framework-features-status-and-comparison.md`（修改）、`docs/tooling/08-evaluation-strategy.md`（修改）
- depends_on: [Task 1, Task 3, Task 4]
- review_profile: lightweight
- spec 映射：spec 章节 2.5
- 说明：`delegated-execution-guide.md` Phase 1/2 补充说明 `quality_passed`/`check_delivery.py` 现在必须携带 `--verify-report`/`--review-report`；`opsx-code-generation/SKILL.md` 补充 `tasks.md` 需要声明 `- Review Report: <path>` 字段（若该 SKILL.md 当前未描述具体字段格式，视实际内容判断是否需要改动，不强行添加不存在的章节）；`framework-features-status-and-comparison.md` 第 4.1/4.3 节更新「控制内核不会自行验证 Review/Verify 报告」相关表述，改为反映证据门已接入的现状，并注明其边界（仍无法验证语义正确性）。本任务不修改任何代码文件。
- context_files:
  - `skills/workflow-code-generation/reference/delegated-execution-guide.md:38,46-57` — 现有 `quality_passed`/Run 级 Review 描述
  - `skills/opsx-code-generation/SKILL.md` — Production 流程描述，确认是否已有类似字段格式章节
  - `docs/framework-features-status-and-comparison.md` 第 4.1、4.3 节 — 现状描述需更新处
  - Task 1、2、3、4 产出的最终 CLI 参数与字段名——文档必须与实现完全一致
- verification:
  - [x] `python skills/workflow-code-generation/scripts/lint_skill_graph.py` 无新增错误/警告
  - [x] 人工核对：三份文档中出现的参数名/字段名与 Task 1/2/3/4 的最终实现逐一核对一致
- artifacts:
  - `skills/workflow-code-generation/reference/delegated-execution-guide.md`
  - `skills/opsx-code-generation/SKILL.md`（如有改动）
  - `docs/framework-features-status-and-comparison.md`
- 子任务：
  - [x] 5.1: 更新 `delegated-execution-guide.md`
  - [x] 5.2: 检查并更新 `opsx-code-generation/SKILL.md`（如需要）
  - [x] 5.3: 更新 `framework-features-status-and-comparison.md`

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
|-----------|------|------|
| 1（问题与目标） | Task 1, 2, 3, 4 | 四处改动共同覆盖验收标准 |
| 2.2（核心组件） | Task 1, 2, 3, 4 | 每个组件对应一个任务 |
| 2.3（接口） | Task 1, 3, 4 | CLI 参数与 tasks.md 字段落地 |
| 2.4（数据模型） | Task 2 | schema 定义 |
| 2.5（关键权衡） | Task 1, 3, 4, 5 | 权衡说明需体现在实现约束与文档同步中 |
