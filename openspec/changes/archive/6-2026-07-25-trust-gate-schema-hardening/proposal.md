# Proposal：Trust Gate 与 Journal 校验精确化（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：trust-gate-schema-hardening
**状态**：Archived

---

## 1. 问题与目标

### 问题

Change 5 终审留下两条 P2（均 critic 补证、keep 交用户），核心是「校验器只做字段访问、未接入 schema，导致诊断粗糙或杂键不可见」：

1. ~~**Trust Gate 把 schema 缺陷碾平成笼统失败**（P2-1a）~~——**执行中核实为误判，已撤销**。最初诊断认为 `runtime_trust._validate_strict_review` 直接下标访问、缺键会被 `validate_run` 的 except 吞成笼统失败、杂键完全不可见。实测（`git stash` 还原到基线后用大写变体键 `Verdict`、缺失 `review_profile` 字段两个场景重跑 `validate_run`）发现：`validate_run:295` 先调用 `run_manifest.validate_manifest`，其内部 `_read_artifact`（`run_manifest.py:90-98`）已对每个 artifact（含 review-report）调用 `runtime_schema.validate_document`，杂键/缺键在 manifest 校验阶段即被拦截，转成精确的 `manifest:invalid_artifact_schema:<file>:<detail>` issue（如 `unexpected field Verdict`、`required field is missing`），根本不会带着坏数据流入 `_validate_strict_review`。P2-1a 描述的缺陷不存在，`_validate_strict_review` 内重复调用 `validate_document` 是死代码（该函数只在通过上游校验的合法 documents 上运行）。本轮撤销该改动，不再处理。
2. **OPSX 阶段门对 Envelope 顶层杂键不可见**（P2-1b）：`validate_change._validate_review_report` 的 Envelope 分支只校验 `artifact_type` 与「顶层不重复携带裁决字段」，顶层出现 `Verdict` 或未知键时不报错，与 `run-envelope.schema.json:125` 的 `additionalProperties:false` 不一致。
3. **Journal 守卫吞掉 manifest 腿冲突诊断**（P2-2）：`run_journal.validate_task_sources:316` 守卫 `if state is None or manifest_task is None or task is None: continue` 含 `task is None`，与上一行注释「Compare state/attempts against the manifest leg only」矛盾——plan 腿缺失时会跳过 manifest 腿比较，吞掉 `event_manifest_task_conflict`。

### 目标

1. ~~`_validate_strict_review` 接入 schema 校验~~——已撤销，见上。
2. `_validate_review_report` 的 Envelope 分支维护顶层键白名单（与 envelope schema 的 13 个键对齐），顶层杂键追加精确错误；不引入 runtime_schema 耦合，OPSX 阶段门保持轻量。
3. `validate_task_sources:316` 守卫收窄为 `state is None or manifest_task is None`，让 manifest 腿冲突诊断与注释意图一致。

### 非目标

- 不改 Run Context 的 Git-only 现状（SVN 适配另立议题）。
- 不重新评估 `check_delivery.py`（已被 native-first 重构迁移到 `skills/workflow-code-generation/scripts/`，原 follow-up 行号失效，另立评估）。
- 不对 OPSX 扁平格式引入 schema（扁平报告无对应 schema，维持字段校验）。
- 不变更各门的拒绝边界（两处均为补精确诊断，方向是收紧，不放宽任何安全门）。
- 不处理 P2-1a：执行中核实为误判，见上，本轮不改动 `runtime_trust.py`。

### 验收标准

- `_validate_review_report` 对 Envelope 顶层含 `Verdict` 或未知键的报告追加错误且拒绝；扁平格式与合法 Envelope 不回归。
- `validate_task_sources` 在 plan 缺 task 但 event 与 manifest 都在且状态冲突时，conflicts 同时含 `missing_task_plan_task:<id>` 与 `event_manifest_task_conflict:<id>`；现有 journal 回归全绿。
- `python -m pytest scripts -q` 全量通过。

## 2. 设计方案

### 2.1 整体方案

两处独立硬化，均为「在既有校验链中补一道白名单或守卫收窄」，不改函数签名与模块边界：

- **P2-1b**：Envelope 分支定义本地常量 `_ENVELOPE_TOP_KEYS`（13 个，取自 `run-envelope.schema.json:6-20`），`extras = set(data) - _ENVELOPE_TOP_KEYS` 非空时追加错误。纯本地常量，不 import runtime_schema。
- **P2-2**：守卫行删去 `or task is None`，与上一行注释对齐。

### 2.2 关键权衡

1. **P2-1b 用本地白名单而非接入 `validate_document`**：保持 OPSX 阶段门轻量、不引入 runtime_schema 耦合；代价：白名单与 schema 存在重复，schema 演进时需同步（用注释标明来源 `run-envelope.schema.json:6-20`）。
2. **P2-2 收窄后 task is None 仍报 `missing_task_plan_task`**：plan 缺失本就报错，收窄只是让「同时存在的 manifest 腿冲突」不再被吞；不改变任何门的通过或拒绝边界。

## 3. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，Envelope 顶层键白名单行为同步到双格式契约段。

## 4. 参考资料

- 现场证据：`scripts/validate_change.py:142-254`；`scripts/run_journal.py:297-327`
- 已证伪证据（P2-1a）：`scripts/run_manifest.py:90-98`（`_read_artifact` 内置 schema 校验）、`scripts/run_manifest.py:295`（`validate_manifest` 在 `_validate_strict_review` 之前调用）
- schema 与工具：`schemas/runtime/run-envelope.schema.json`、`scripts/runtime_schema.py:237-259`
- change 5 终审报告（P2-1 与 P2-2 裁决明细）
