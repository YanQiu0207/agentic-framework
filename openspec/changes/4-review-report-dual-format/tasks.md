# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 3
> 核心原则: 先落地代码与测试（Task 1），契约文档（Task 2）与信任边界知识沉淀（Task 3）以已落地行为为准、并行跟随

## 依赖关系总览

```
Task 1 (validate_change.py 双格式 + 测试)
   ├──> Task 2 (SKILL.md 双轨契约对齐)
   └──> Task 3 (intent 沉淀：信任边界知识)
```

波次：W1 = {Task 1} → W2 = {Task 2, Task 3}

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/validate_change.py` | 修改 | Task 1 | `_validate_review_report` 双格式解析 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 1 | Envelope 正反用例 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 2 | :110、:164 报告契约段补双格式说明 |
| `skills/workflow-code-review/SKILL.md` | 修改 | Task 2 | 机器可读产物段豁免句改写 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 3 | 机器门段落补双格式契约 |
| `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | 修改 | Task 3 | §6 接入矩阵补 OPSX 双轨适用范围 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `_validate_review_report(path_text, repo, expected_scope)` | 内部逻辑变更，签名不变 | `_validate_tasks`、`_validate_delivery`（同文件） | Task 1 |
| Review Report JSON 契约 | 接受面扩大（扁平 + Envelope 双格式） | `opsx-code-generation` / `workflow-code-review` 的 Judge、下游 OPSX 项目 | Task 1, 2 |

### 构建系统变更

- 无（纯 Python 标准库脚本，pytest 直跑）。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 旧扁平报告意外含 `payload` 键会被判为 Envelope | Task 1 | 旧契约固定 6 个字段无 `payload` 键；报错消息标注解析格式，引导修正 |
| 2 | Envelope 顶层字段从宽会削弱门禁 | Task 1, 3 | OPSX 无 Run 可绑定，Run 绑定属 `runtime_trust` 职责；在 trust-model.md §6 显式声明双轨边界 |
| 3 | 探测规则与 `check_delivery.py` 的选取方式不同 | Task 1, 2 | `check_delivery.py` 按 `run_dir` 有无选解析路径，本方案按内容探测（OPSX 校验器无 run_dir 可用）；规则写入 SKILL.md 保持两处语义一致 |

## 任务列表

### 任务 1: [ ] validate_change.py 双格式解析与回归测试
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `scripts/validate_change.py`（修改）, `scripts/tests/test_validate_change.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md 验收标准 / 2.1 整体方案 / 2.2 核心组件 / 2.5 关键权衡 1,2
- 说明: 重构 `_validate_review_report`：JSON 顶层为 dict 且 `payload` 为 dict 时按 Envelope 解析（裁决字段取自 `payload`），否则按旧式扁平解析；两种格式共用现有 verdict / p0_count / p1_count / scope / review_profile / round 校验逻辑，报错消息标注解析格式；Envelope 额外校验顶层 `artifact_type == "review-report"`，不校验 `run_id` / `commit_sha` / `config_digest`。测试沿用 `write_report` 覆写 `valid-standard` fixture 的既有模式：新增 Envelope 正例（task 级过 delivery、integration 级过 archive）与反例（NEEDS_CHANGES、p0_count 大于 0、p1_count 大于 0、scope 错误、review_profile 非法、round 负数、artifact_type 缺失或错误），现有扁平用例不改动、不回归。
- context_files:
  - `scripts/validate_change.py:_validate_review_report` — 直接修改目标
  - `scripts/validate_change.py:_validate_tasks` / `_validate_delivery` — 调用方，`expected_scope`（task / integration）来源
  - `skills/workflow-code-generation/scripts/check_delivery.py:79-110` — 已同步的 payload 提取参照实现
  - `schemas/runtime/review-report.schema.json` — Envelope 契约（只读，不修改）
  - `scripts/tests/test_validate_change.py:write_report` 与两个 evidence 测试 — 现有测试模式基准
- verification:
  - [ ] `python -m pytest scripts/tests/test_validate_change.py -q` 全部通过（含新增 Envelope 用例）
  - [ ] `python -m pytest scripts -q` 全量回归通过
  - [ ] `python -m py_compile scripts/validate_change.py` 退出码 0
- artifacts:
  - `scripts/validate_change.py`（修改）
  - `scripts/tests/test_validate_change.py`（修改）
- 子任务:
  - [ ] 1.1: 重构 `_validate_review_report`：格式探测、字段来源参数化、`artifact_type` 校验、报错标注格式
  - [ ] 1.2: 新增 Envelope 正例（task 级过 delivery、integration 级过 archive）
  - [ ] 1.3: 新增 Envelope 反例（7 类）并断言 OPSX038 / OPSX032
  - [ ] 1.4: 调用 `workflow-test-generation` 核对覆盖完整性，运行全量测试通过

### 任务 2: [ ] SKILL.md 双轨契约对齐
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/opsx-code-generation/SKILL.md`（修改）, `skills/workflow-code-review/SKILL.md`（修改）
- depends_on: [Task 1]
- review_profile: lightweight
- 文档映射: proposal.md 2.1 整体方案 / 3. 知识影响（契约口径）
- 说明: `skills/opsx-code-generation/SKILL.md:110` 与 `:164` 的报告契约段补充：Judge 报告可为符合 `schemas/runtime/review-report.schema.json` 的 Envelope（裁决字段在 `payload` 内）或旧式扁平 JSON；有 Run Context 时必须写 Envelope。`skills/workflow-code-review/SKILL.md:272` 机器可读产物段的豁免句改写：`scope: run` 报告必须是 Envelope 且绑定 Run Context；无 Run Context 的纯 OPSX Production 流程（`scope: task` / `integration`）允许旧式扁平 JSON，由 `validate_change.py` 与人审放行，该豁免不适用于 `scope: run`。措辞与 Task 1 落地的探测规则保持一致。
- context_files:
  - `skills/opsx-code-generation/SKILL.md` — 直接修改目标（:110、:164 契约段）
  - `skills/workflow-code-review/SKILL.md` — 直接修改目标（机器可读产物段）
  - `scripts/validate_change.py:_validate_review_report` — 文档描述的行为来源（Task 1 产出）
- verification:
  - [ ] `grep -n "Envelope" skills/opsx-code-generation/SKILL.md skills/workflow-code-review/SKILL.md` 有命中，且语义与 Task 1 实现一致（人工核对）
  - [ ] `python scripts/lint_skill_graph.py` 退出码 0
- artifacts:
  - `skills/opsx-code-generation/SKILL.md`（修改）
  - `skills/workflow-code-review/SKILL.md`（修改）
- 子任务:
  - [ ] 2.1: opsx-code-generation 两处契约段补双格式说明
  - [ ] 2.2: workflow-code-review 豁免句改写并标注 OPSX 双轨适用范围
  - [ ] 2.3: 按 md-zh 规范自检两处中文排版

### 任务 3: [ ] intent 沉淀：信任边界知识同步
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（修改）, `openspec/specs/backend/framework/quality-gates/overview.md`（修改）
- depends_on: [Task 1]
- review_profile: lightweight
- 文档映射: proposal.md 3. 知识影响
- 说明: 命中「新增信任边界约束」信号：OPSX 双轨是信任模型边界决策（放弃「OPSX 全量 Run Context」方案、确立「无 Run 时扁平报告可放行」约束）。`trust-model.md` §6 接入矩阵补注：OPSX Production 阶段门接受双格式报告，扁平报告的放行依据是 `validate_change.py` 确定性校验与人审，该豁免不适用于 `scope: run`；`quality-gates/overview.md` 机器门相关段落补双格式报告契约说明。
- context_files:
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` — 直接修改目标（§6 接入矩阵）
  - `openspec/specs/backend/framework/quality-gates/overview.md` — 直接修改目标（Production 阶段门 / Code Review 段）
  - `scripts/validate_change.py:_validate_review_report` — 行为来源（Task 1 产出）
- verification:
  - [ ] 两处文档含双轨 / 双格式说明且与 Task 1 实现一致（人工核对）
  - [ ] 按 md-zh 规范自检排版
- artifacts:
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（修改）
  - `openspec/specs/backend/framework/quality-gates/overview.md`（修改）
- 子任务:
  - [ ] 3.1: trust-model.md §6 补 OPSX 双轨适用范围
  - [ ] 3.2: quality-gates/overview.md 补双格式报告契约
  - [ ] 3.3: 按 md-zh 规范自检排版

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal 1.问题 | Task 1 | 断层根因在格式探测与字段来源重构中消除 |
| proposal 1.验收标准 | Task 1 | 正反用例即验收标准的机器化 |
| proposal 2.1 / 2.2 方案 | Task 1, 2 | 实现落地 + 契约文档对齐 |
| proposal 2.5 关键权衡 | Task 1, 3 | 探测规则、从宽理由、双轨边界沉淀 |
| proposal 3.知识影响 | Task 3 | 两处长期知识同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引 |
| （Quick，无 Delta） | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引 |

> 本 Change 为 Quick Draft，未创建 `specs/` Delta。两处长期知识修改由 Task 3 直接落盘，归档阶段由 `project-knowledge` 核对。

## 知识冲突

- 结论：无冲突。Task 3 新增段与 §6 既有矩阵、`quality-gates/overview.md` 既有职责表经两轮交叉核对（owner 自查 + Run 级 review F-1/F-2 修复与复审确认），语义一致。

## 实际 Diff 核对

- 核对状态：PASS。核对命令：`git diff 18f46f1..HEAD --stat`（改动文件与本清单一致：代码 2、测试同文件、SKILL.md 2、知识文档 2、Change 文档 2）；`python -m pytest scripts -q`（290 passed，含新增 Envelope 用例）；Run 级 `verify.py` 总判定 PASS（`verify-run.json`）；Run 级 review 复审第 1 轮 PASS（`review-run.json`）。
