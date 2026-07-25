# 实施任务清单

> 由 proposal.md 生成
> 任务总数：3
> 核心原则：三处独立诊断精确化，无接口变更，无依赖顺序，可全并行

## 依赖关系总览

Task 1（runtime_trust 接入 schema 校验）  ← 无依赖，可并行
Task 2（validate_change Envelope 顶层白名单）  ← 无依赖，可并行
Task 3（run_journal 守卫收窄）  ← 无依赖，可并行

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|---|---|---|---|
| `scripts/runtime_trust.py` | 修改 | Task 1 | `_validate_strict_review` 接入 `validate_document` |
| `scripts/test_runtime_trust.py` | 修改 | Task 1 | 新增杂键/缺键回归 |
| `scripts/validate_change.py` | 修改 | Task 2 | Envelope 分支顶层键白名单 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 2 | 新增杂键回归 |
| `scripts/run_journal.py` | 修改 | Task 3 | :316 守卫收窄 |
| `scripts/tests/test_run_journal.py` | 修改 | Task 3 | 新增 manifest 腿冲突不被吞回归 |

### 受影响接口

无接口签名变更；三处均为函数内部逻辑硬化。

### 构建系统变更

无。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|---|---|---|
| 1 | `RuntimeSchemaError` 不在 `validate_run:308` 的 except 四元组中 | Task 1 | 必须在 `_validate_strict_review` 内部捕获并转换为 issue，不能依赖上层兜底 |
| 2 | 白名单硬编码值与 schema 演进可能漂移 | Task 2 | 用注释标注来源 `run-envelope.schema.json:6-20`，不引入运行时依赖 |

## 任务列表

### 任务 1：[x] Trust Gate 接入 review-report schema 校验（诊断证伪，已撤销）
- 状态：完成（结论：不改代码）
- 文件：无（改动已撤销）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 1（问题 1，已证伪）
- 说明：原计划在 `_validate_strict_review`（:59-90）筛选 review 候选前调用 `runtime_schema.validate_document`。执行中实测（`git stash` 还原基线后用大写变体键 `Verdict`、缺失 `review_profile` 两个场景重跑 `validate_run`）发现 `validate_run:295` 调用的 `run_manifest.validate_manifest` 早已在其内部 `_read_artifact`（`run_manifest.py:90-98`）对每个 artifact 做了 `runtime_schema.validate_document` 校验，杂键/缺键在 manifest 校验阶段即被拦截为 `manifest:invalid_artifact_schema:<file>:<detail>`，根本不会带着坏数据流入 `_validate_strict_review`。P2-1a 描述的缺陷不存在，改动是死代码。已用 `git checkout -- scripts/runtime_trust.py scripts/test_runtime_trust.py` 撤销，全量测试确认无回归（337 passed）。
- context_files:
  - `scripts/run_manifest.py:90-98` — 实际生效的校验点 `_read_artifact`，证伪证据
  - `scripts/run_manifest.py:306-311` — `validate_manifest` 入口，先于 `_validate_strict_review` 执行
- verification:
  - [x] `python -m pytest scripts -q` 全量无回归（337 passed, 21 skipped）
- artifacts:
  - 无（撤销的代码不作为产物）
- 子任务：
  - [x] 1.1: 用 `git stash` 还原基线，实测大写变体键 `Verdict` 场景 → 确认 `REJECTED`，manifest 阶段已拦截
  - [x] 1.2: 实测缺失 `review_profile` 字段场景 → 确认 `REJECTED`，manifest 阶段已拦截
  - [x] 1.3: `git checkout -- scripts/runtime_trust.py scripts/test_runtime_trust.py` 撤销改动
  - [x] 1.4: `python -m pytest scripts -q` 确认撤销后无回归

### 任务 2：[x] OPSX 阶段门 Envelope 顶层键白名单
- 状态：完成
- 文件：`scripts/validate_change.py`（修改）, `scripts/tests/test_validate_change.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 2.1/2.2 第 2 条
- 说明：在 `_validate_review_report`（:142-254）Envelope 分支（`isinstance(payload, dict)` 为真时，:189-209）新增顶层键白名单检查。模块级定义 `_ENVELOPE_TOP_KEYS = frozenset({"schema_version","artifact_type","artifact_id","run_id","task_id","attempt","profile","harness","producer","commit_sha","config_digest","created_at","payload"})`（注释标注来源 `run-envelope.schema.json:6-20`，与其 `additionalProperties:false` 对齐）。Envelope 分支内计算 `extras = set(data) - _ENVELOPE_TOP_KEYS`，非空时追加 `f"{label}的顶层携带未知字段：{sorted(extras)}。"`（不 import runtime_schema，保持 OPSX 阶段门轻量，纯本地常量对比）。
- context_files:
  - `scripts/validate_change.py:142-254` — 直接修改目标 `_validate_review_report`
  - `schemas/runtime/run-envelope.schema.json:6-20` — 白名单取值依据（required 字段列表）
  - `scripts/tests/test_validate_change.py:798-848` — `envelope_report`/`break_envelope_report` 辅助方法，新增测试沿用其构造模式
  - `scripts/tests/test_validate_change.py:1105-1299` — 既有 Envelope/polyglot/断腿测试，确认不回归
- verification:
  - [x] `python -m pytest scripts/tests/test_validate_change.py -q` 全部通过（47 passed, 1 skipped, 68 subtests）
  - [x] `python -m pytest scripts -q` 全量无回归（336 passed, 21 skipped, 129 subtests）
- artifacts:
  - `scripts/validate_change.py`
  - `scripts/tests/test_validate_change.py`
- 子任务：
  - [x] 2.1: 定义 `_ENVELOPE_TOP_KEYS` 常量并在 Envelope 分支接入白名单检查
  - [x] 2.2: 新增测试 `test_envelope_top_level_uppercase_variant_key_is_rejected`：Envelope 顶层含 `Verdict`（大写变体）→ 报错含「未知字段」且拒绝
  - [x] 2.3: 新增测试 `test_envelope_top_level_unknown_stray_key_is_rejected`：Envelope 顶层含未知杂键（如 `extra_field`）→ 报错含「未知字段」且拒绝
  - [x] 2.4: 运行 `python -m pytest scripts/tests/test_validate_change.py -q`，确认既有合法 Envelope（`envelope_report` 构造）与扁平格式测试不回归

### 任务 3：[x] Journal 守卫收窄，不吞 manifest 腿冲突
- 状态：完成
- 文件：`scripts/run_journal.py`（修改）, `scripts/tests/test_run_journal.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 2.1/2.2 第 3 条
- 说明：`validate_task_sources`（:289-327）的守卫行 :316 由 `if state is None or manifest_task is None or task is None: continue` 收窄为 `if state is None or manifest_task is None: continue`。收窄后，当 `task is None`（plan 缺该任务）但 `state` 与 `manifest_task` 均存在且状态/attempt 不一致时，:322-325 的比较会继续执行，`conflicts` 同时包含 :314 追加的 `missing_task_plan_task:<id>` 与该比较追加的 `event_manifest_task_conflict:<id>`。不改变任何单一冲突的判定条件，只改变「多腿同时缺失/冲突时是否都报出来」。
- context_files:
  - `scripts/run_journal.py:289-327` — 直接修改目标 `validate_task_sources`
  - `scripts/run_journal.py:256-286` — 调用方 `recovery_plan`，确认异常传播路径不变
  - `scripts/runtime_trust.py` — 另一调用方（`_validate_journal`），确认签名和调用点不受影响
  - `scripts/tests/test_run_journal.py:59-100` — `manifest()`/`tasks()` fixture 构造函数，新增测试基于其扩展
  - `scripts/tests/test_run_journal.py:237-270` — 既有 `test_recovery_rejects_tasks_missing_from_any_state_source`，确认收窄后不回归
- verification:
  - [x] `python -m pytest scripts/tests/test_run_journal.py -q` 全部通过（13 passed, 8 subtests）
  - [x] `python -m pytest scripts -q` 全量无回归（撤销 Task 1 后合并复测：337 passed, 21 skipped）
- artifacts:
  - `scripts/run_journal.py`
  - `scripts/tests/test_run_journal.py`
- 子任务：
  - [x] 3.1: 收窄 :316 守卫行，删去 `or task is None`
  - [x] 3.2: 新增测试 `test_recovery_reports_event_manifest_conflict_even_when_plan_leg_missing`：plan 缺任务（`task is None`）但 event 与 manifest 都存在且状态不一致 → `JournalError` 同时含 `missing_task_plan_task:2` 与 `event_manifest_task_conflict:2`（修复前手工复现确认后者被吞）
  - [x] 3.3: 运行 `python -m pytest scripts/tests/test_run_journal.py -q`，确认既有 `test_recovery_rejects_tasks_missing_from_any_state_source` 等用例不回归

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|---|---|---|
| 2.1/2.2 第 1 条（P2-1a） | Task 1 | Trust Gate 接入 schema 校验 |
| 2.1/2.2 第 2 条（P2-1b） | Task 2 | OPSX 顶层键白名单 |
| 2.1/2.2 第 3 条（P2-2） | Task 3 | Journal 守卫收窄 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
|---|---|---|---|---|
| `specs/backend/framework/quality-gates/overview.md` | 同路径 | MODIFIED | Done | 不涉及导航条目变更，无需更新 knowledge/README.md |

`trust-model.md` 的知识影响随 P2-1a 一并撤销：`_validate_strict_review` 未改动，无需在 §4.1 补充新校验行为描述。

## 知识冲突

- 结论：无冲突。`quality-gates/overview.md` 的改动是对既有 Envelope 双格式描述的精确化补充（新增「顶层字段仅限白名单」一句），未与其他长期 Spec 或活跃 Change 产生矛盾陈述。

## 实际 Diff 核对

- 核对状态：Done。
- 核对命令：`git diff --stat` 确认改动范围限于 `scripts/run_journal.py`（+1/-1）、`scripts/tests/test_run_journal.py`（新增 1 测试）、`scripts/validate_change.py`（+常量+白名单检查）、`scripts/tests/test_validate_change.py`（新增 2 测试）、`openspec/specs/backend/framework/quality-gates/overview.md`（1 句精确化）；`runtime_trust.py`/`test_runtime_trust.py` 已 `git checkout --` 撤销回基线，无残留改动。
- 测试证据：`python -m pytest scripts -q` → 337 passed, 21 skipped, 129 subtests passed，无回归。
- 结论：PASS。Task 1 因诊断证伪不产出代码变更，Task 2/3 按计划交付且测试全绿。
