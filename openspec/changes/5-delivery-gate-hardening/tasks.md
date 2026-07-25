# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 5
> 核心原则: 三个独立修复面（信任契约、校验器硬化、标点统一）W1 并行，契约文档与 intent 沉淀以已落地行为为准串行跟随

## 依赖关系总览

```
Task 1 (validate_task_sources 消费侧修复)   Task 2 (校验器硬化)   Task 4 (模板标点)
   │                                            │
   │                                            └──> Task 3 (trust-model 免责扩展 + 契约同步)
   └──────────────────────────────────────────────────────> Task 5 (intent 沉淀 + 知识同步)
```

波次：W1 = {Task 1, Task 2, Task 4} → W2 = {Task 3} → W3 = {Task 5}

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/run_journal.py` | 修改 | Task 1 | 删除冻结快照状态/attempts 比对 |
| `scripts/runtime_trust.py` | 修改 | Task 1 | `_validate_journal` 调用随动（如需要） |
| `scripts/test_runtime_trust.py` | 修改 | Task 1 | 生产保真回归用例 |
| `scripts/validate_change.py` | 修改 | Task 2 | 格式冲突拒绝 + payload 非 dict 定向错误 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 2 | polyglot / 断腿 Envelope / 回落边界用例 |
| `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | 修改 | Task 3, 5 | §6 免责扩展、拒绝行为声明、冻结快照职责边界 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 3 | 双格式契约补拒绝行为 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 3 | :110 / :164 契约补拒绝行为 |
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 修改 | Task 4 | 中文标签全角化 |
| `skills/opsx-code-generation/reference/task_planning_guide.md` | 修改 | Task 4 | 中文标签全角化（与上同步） |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 视检查修改 | Task 5 | 若描述 validate_task_sources 语义则同步 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `validate_task_sources(replay, tasks_text, manifest)` | 行为修正（状态比对改源） | `runtime_trust._validate_journal` | Task 1 |
| `_validate_review_report(path_text, repo, expected_scope)` | 接受面收紧（两种新拒绝） | `_validate_tasks`、`_validate_delivery` | Task 2 |
| tasks.md 文本格式约定 | 中文标签全角化 | `workflow_control.py`、各 tasks.md 作者 | Task 4 |

### 构建系统变更

- 无（纯 Python 标准库脚本，pytest 直跑）。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 删除冻结快照状态比对后，状态一致性保障被削弱 | Task 1 | manifest 腿（`run_journal.py:335-338`）已覆盖状态与 attempts 一致性，其数据源是交付时 task-state artifacts；在测试中断言该腿仍生效 |
| 2 | payload 非 dict 拒绝误伤携带杂键的扁平报告 | Task 2 | 旧扁平契约无 `payload` 键；定向错误消息明确；在 trust-model 与契约文档声明该行为变化 |
| 3 | 全角化模板后既有半角 tasks.md 解析失败 | Task 4 | `lint_task_deps.py` 与 `validate_change.py` 正则均为 `[:：]` 双兼容；跑全量测试验证 |
| 4 | change 4 交付门重跑受 journal 重复事件影响 | 交付阶段 | 已实证 `replay_events` 容忍重复 task-merged（无重复 event_id / idempotency_key）；交付报告披露 |

## 任务列表

### 任务 1: [ ] validate_task_sources 消费侧修复与生产保真回归
- 状态: 未开始
- 文件: `scripts/run_journal.py`（修改）, `scripts/runtime_trust.py`（修改，如调用需随动）, `scripts/test_runtime_trust.py`（修改）
- depends_on: []
- review_profile: strict
- 文档映射: proposal.md 问题 1 / 目标 1 / 2.1 整体方案 / 2.5 权衡 1
- 说明: 修复 Trust Gate 生产路径必挂缺陷。`validate_task_sources` 删除用冻结快照 `- 状态:` / `attempts` 与 journal 重放态的比对（`run_journal.py:326-334`），保留任务存在性三方一致性（missing_task_event / missing_manifest_task / missing_task_plan_task）与 manifest 腿状态/attempts 比对（335-338 行）。`runtime_trust._validate_journal` 的 tasks_text 读取与调用随动（若仅用于存在性检查则保留读取）。测试：在 `test_runtime_trust.py` 增加生产保真用例——input-task-plan 快照内容为「- 状态: 未开始」（模拟 init 冻结）+ journal 含 task-merged + 合法 manifest，`validate_run` 必须 PASS；保留既有「状态：完成」快照用例不回归；断言 manifest 腿仍拦截「manifest 任务状态与 journal 不一致」。
- context_files:
  - `scripts/run_journal.py:validate_task_sources` — 直接修改目标（:297-340）
  - `scripts/run_journal.py:replay_events` — journal 重放语义（:183-221）
  - `scripts/runtime_trust.py:_validate_journal` — 调用方（:215-279）
  - `scripts/run_manifest.py:generate_manifest` — manifest payload.tasks 来源（:381-407）
  - `scripts/test_runtime_trust.py` — fixture 构造（:100-180），生产保真盲区所在
- verification:
  - [ ] 新增生产保真用例（冻结「未开始」快照 + 完成 journal）PASS
  - [ ] `python -m pytest scripts/test_runtime_trust.py scripts/test_runtime_workflow.py scripts/test_run_manifest.py scripts/test_workflow_control.py -q` 全部通过
  - [ ] `python -m pytest scripts -q` 全量回归通过
- artifacts:
  - `scripts/run_journal.py`（修改）
  - `scripts/runtime_trust.py`（如修改）
  - `scripts/test_runtime_trust.py`（修改）
- 子任务:
  - [ ] 1.1: 删除冻结快照状态/attempts 比对，保留存在性与 manifest 腿
  - [ ] 1.2: `_validate_journal` 调用随动与注释/docstring 同步
  - [ ] 1.3: 新增生产保真回归用例（改前必挂、改后必过）
  - [ ] 1.4: 调用 `workflow-test-generation` 核对覆盖，运行全量测试通过

### 任务 2: [ ] validate_change.py 格式冲突与断腿 Envelope 硬化
- 状态: 未开始
- 文件: `scripts/validate_change.py`（修改）, `scripts/tests/test_validate_change.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md 问题 2,3 / 目标 2 / 2.5 权衡 2
- 说明: 在 `_validate_review_report` 追加两条失败关闭规则：① Envelope 模式（`payload` 为 dict）下，顶层同时携带 6 个裁决字段（`verdict` / `p0_count` / `p1_count` / `scope` / `review_profile` / `round`）任一时，追加「顶层与 payload 同时携带裁决字段，格式冲突」错误（polyglot 拒绝）；② `payload` 键存在但值非 dict 时，追加「payload 必须为 JSON 对象」定向错误（不再静默回落扁平放行），随后仍按扁平分支照常评估其余字段（保持累积式报错）。报错消息沿用「Review Report（…格式）的…」句式。测试：polyglot（顶层 NEEDS_CHANGES + payload PASS + artifact_type）task 级与 integration 级均拒绝且消息含「格式冲突」；payload 为 null / list / str 拒绝且消息指向 payload 类型；payload 非 dict + 顶层字段齐全同样拒绝（行为变化锁定）；无 payload 键纯扁平放行不回归。
- context_files:
  - `scripts/validate_change.py:_validate_review_report` — 直接修改目标（change 4 已合并的双格式版本，:142-225）
  - `scripts/tests/test_validate_change.py:envelope_report / break_envelope_report` — change 4 新增的测试辅助
  - change 4 strict review 报告 F-5/F-1/F-2 裁决与 critic 证据 — 行为依据
- verification:
  - [ ] polyglot 两级拒绝（OPSX038 / OPSX032 + 「格式冲突」消息）
  - [ ] payload 非 dict 拒绝且消息指向 payload 类型
  - [ ] `python -m pytest scripts/tests/test_validate_change.py -q` 与 `python -m pytest scripts -q` 全部通过
- artifacts:
  - `scripts/validate_change.py`（修改）
  - `scripts/tests/test_validate_change.py`（修改）
- 子任务:
  - [ ] 2.1: Envelope 分支顶层裁决字段冲突检查
  - [ ] 2.2: payload 非 dict 定向错误分支
  - [ ] 2.3: 新增两级正反用例并锁定行为变化
  - [ ] 2.4: 调用 `workflow-test-generation` 核对覆盖，运行全量测试通过

### 任务 3: [ ] trust-model 免责扩展与契约文档同步
- 状态: 未开始
- 文件: `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（修改）, `openspec/specs/backend/framework/quality-gates/overview.md`（修改）, `skills/opsx-code-generation/SKILL.md`（修改）
- depends_on: [Task 2]
- review_profile: lightweight
- 文档映射: proposal.md 问题 4 / 目标 3 / 2.5 权衡 2
- 说明: ① `trust-model.md` §6 新增段的免责句主语从「旧式扁平 JSON」扩为「无 Run Context 时放行的报告（任一格式）」，并补一句：无 Run Context 的 Envelope 中 `run_id` / `commit_sha` / `config_digest` 未经任何组件验证，不构成 Run 绑定声明（F-6）。② 三处文档同步 Task 2 的行为变化：双格式契约补「顶层与 payload 同时携带裁决字段判格式冲突拒绝」「payload 键存在但非对象时拒绝」（`overview.md:51` 双格式句、`opsx-code-generation/SKILL.md:110` 与 `:164`、`trust-model.md` §6 新增段）。措辞与 Task 2 落地实现逐字核对。
- context_files:
  - `scripts/validate_change.py:_validate_review_report` — 行为来源（Task 2 产出）
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` — §6 修改目标
  - `openspec/specs/backend/framework/quality-gates/overview.md:51` — 双格式句
  - `skills/opsx-code-generation/SKILL.md:110` / `:164` — 契约段
- verification:
  - [ ] 三处文档含免责扩展与两条拒绝行为声明，与实现一致（人工核对）
  - [ ] 按 md-zh 规范自检排版
- artifacts:
  - `trust-model.md`（修改）
  - `overview.md`（修改）
  - `skills/opsx-code-generation/SKILL.md`（修改）
- 子任务:
  - [ ] 3.1: §6 免责句扩展为任一格式 + unbound Envelope 声明
  - [ ] 3.2: 三处文档补两条拒绝行为
  - [ ] 3.3: md-zh 排版自检

### 任务 4: [ ] task_planning_guide 模板标点统一
- 状态: 未开始
- 文件: `skills/workflow-code-generation/reference/task_planning_guide.md`（修改）, `skills/opsx-code-generation/reference/task_planning_guide.md`（修改）
- depends_on: []
- review_profile: lightweight
- 文档映射: proposal.md 问题（不一致段）/ 目标 4 / 2.5 权衡 3
- 说明: 两份模板中的中文标签半角冒号统一为全角：`### 任务 N：`、`- 状态：`、`- 文件：`、`- 说明：`、`- 文档映射：`、`- 子任务：`、`- 验收标准：`、`- 依赖：` 等；英文 key（`depends_on:` / `review_profile:` / `context_files:` / `verification:` / `artifacts:`）保持半角；代码 span、正则示例（`[:：]`）、命令行内容不动。两份文件改动保持一致。消除与 `workflow_control.py:410`（全角写入 `- 状态：`）的不一致源。
- context_files:
  - `skills/workflow-code-generation/reference/task_planning_guide.md` — 直接修改目标
  - `skills/opsx-code-generation/reference/task_planning_guide.md` — 直接修改目标
  - `skills/workflow-code-generation/scripts/workflow_control.py:410` — 全角写入点（只读参照）
  - `skills/workflow-code-generation/scripts/lint_task_deps.py` — 解析正则 `[:：]` 双兼容（只读参照）
- verification:
  - [ ] 两份文件中文标签全角、英文 key 半角（grep 核对）
  - [ ] `python -m pytest scripts -q` 全量通过（含 lint / profile contract 测试）
  - [ ] `python scripts/lint_skill_graph.py` 退出码 0
- artifacts:
  - 两份 `task_planning_guide.md`（修改）
- 子任务:
  - [ ] 4.1: workflow-code-generation 版模板全角化
  - [ ] 4.2: opsx-code-generation 版模板全角化并互核一致
  - [ ] 4.3: 全量测试与 lint 验证

### 任务 5: [ ] intent 沉淀与知识同步
- 状态: 未开始
- 文件: `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（修改）, `openspec/specs/backend/framework/workflow-control/overview.md`（视检查修改）
- depends_on: [Task 1, Task 2, Task 3]
- review_profile: lightweight
- 文档映射: proposal.md 3. 知识影响
- 说明: 命中「架构决策」信号：冻结快照职责边界是信任契约语义修正。在 `trust-model.md`（§4.4 或 §6，择语义最贴合处）补一段：input-task-plan 冻结快照的职责是冻结计划（task_ids 与计划结构），任务终态一致性以交付时 tasks.md 为准，经 task-state artifacts 与 manifest `payload.tasks` 传递后由 `validate_task_sources` 比对。检查 `openspec/specs/backend/framework/workflow-control/overview.md` 是否描述 journal / 状态一致性语义，涉及则同步；不涉及写明无需更新理由。
- context_files:
  - `scripts/run_journal.py:validate_task_sources` — 修复后行为（Task 1 产出）
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` — 修改目标
  - `openspec/specs/backend/framework/workflow-control/overview.md` — 检查目标
- verification:
  - [ ] trust-model.md 含冻结快照职责边界段，与 Task 1 实现一致（人工核对）
  - [ ] workflow-control overview 检查结论落盘（同步或写明无需更新理由）
  - [ ] 按 md-zh 规范自检排版
- artifacts:
  - `trust-model.md`（修改）
  - `workflow-control/overview.md`（视检查修改）
- 子任务:
  - [ ] 5.1: 冻结快照职责边界写入 trust-model.md
  - [ ] 5.2: workflow-control overview 检查与同步
  - [ ] 5.3: md-zh 排版自检

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal 1.问题 1 | Task 1 | bug 根因修复 |
| proposal 1.问题 2,3 | Task 2 | 校验器硬化 |
| proposal 1.问题 4 | Task 3 | 免责形态修正 |
| proposal 1.不一致段 | Task 4 | 标点统一 |
| proposal 1.验收标准 | Task 1, 2, 3, 4 | 各条对应验证 |
| proposal 2.1 / 2.2 | Task 1, 2, 3, 4 | 方案落地 |
| proposal 2.5 关键权衡 | Task 1, 2, 3, 5 | 改源理由、拒绝行为声明、模板方向、职责边界沉淀 |
| proposal 3.知识影响 | Task 3, 5 | 长期知识同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | MODIFIED | Pending | 无需更新：条目级修改，不影响索引 |
| （Quick，无 Delta） | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Pending | 无需更新：条目级修改，不影响索引 |
| （Quick，无 Delta） | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Pending | 视 Task 5 检查结论确定 |

> 本 Change 为 Quick Draft，未创建 `specs/` Delta。长期知识修改由 Task 3 / Task 5 直接落盘，归档阶段由 `project-knowledge` 核对。

## 知识冲突

- 结论：待核对。归档前写「无冲突」，或记录双方证据并标记 `Resolved`。

## 实际 Diff 核对

- 核对状态：Pending。归档前记录实际 Diff、Change 和测试证据的核对命令与 PASS 结论。
