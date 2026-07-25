# Proposal: OPSX 校验器双格式对齐 Review 报告协议（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：review-report-dual-format
**状态**：Archived

---

## 1. 问题与目标

### 问题

`workflow-code-review` 已升级为 Envelope 协议：Judge 的机器可读报告必须符合 `schemas/runtime/review-report.schema.json`，`verdict`、`p0_count`、`p1_count`、`scope`、`review_profile`、`round` 等裁决字段收进 `payload`（`skills/workflow-code-review/SKILL.md:270-300`）。但 OPSX 阶段门 `scripts/validate_change.py:142-209` 的 `_validate_review_report` 仍只读顶层字段，形成双向断层：

- Judge 按新协议写出的 Envelope 被门禁误杀（报「verdict 必须为 PASS，当前为 None」）；
- 旧式扁平 JSON 仍被放行，与「缺少 Run Context 时不得输出可放行的旧式顶层 PASS JSON」的新规口径不一致。

同框架的 `check_delivery.py:79-110` 已完成同步（按 `run_dir` 有无选择 payload 提取），`validate_change.py` 是迁移漏网者。

### 目标

- `_validate_review_report` 支持双格式解析：Envelope 与旧式扁平报告共用同一套裁决字段校验。
- 补充 Envelope 正反用例回归测试，现有扁平用例无回归。
- 契约文档与项目知识同步，显式声明 OPSX 双轨边界。

### 非目标

- 不给 OPSX 引入 Run Context、Manifest、Trust Gate（B/C 档另立 Change 评估）。
- 不修改 `schemas/runtime/*.json`（`commit_sha` 的 Git-only 约束属 SVN 适配议题，另行处理）。
- 不修改 `scripts/runtime_workflow.py`、`check_delivery.py`。
- 不废弃旧式扁平格式（去留由 B/C 档决策）。

### 验收标准

- Envelope 与扁平两种 PASS 报告均通过 delivery 与 archive 门禁（退出码 0）。
- Envelope 反例（NEEDS_CHANGES、p0_count 大于 0、p1_count 大于 0、scope 错误、review_profile 非法、round 负数、artifact_type 缺失或错误）分别被 OPSX038（task 级）或 OPSX032（integration 级）拦截。
- `python -m pytest scripts -q` 全量测试通过，无回归。

## 2. 设计方案

### 2.1 整体方案

在 `_validate_review_report` 内做内容探测：JSON 顶层为对象且 `payload` 为对象时按 Envelope 解析（裁决字段取自 `payload`），否则按旧式扁平解析（裁决字段取自顶层）。两种格式共用现有字段校验逻辑与报错口径，报错消息标注本次按哪种格式解析。对 Envelope 额外校验唯一顶层字段 `artifact_type == "review-report"`，防止把 verify、event 等其他 Artifact 误当 Review 报告。

### 2.2 核心组件

- 格式探测与字段提取：`_validate_review_report` 内部重构，先解析 JSON，再按 `payload` 是否为 dict 选择裁决字段来源。
- 共用校验：verdict 必须为 PASS、p0_count 与 p1_count 必须为整数 0、scope 必须匹配预期、review_profile 必须合法、round 必须为非负整数（现有判定逻辑不变，仅字段来源参数化）。
- Envelope 顶层校验：`artifact_type` 必须为 `"review-report"`；`run_id`、`commit_sha`、`config_digest` 等 Run 绑定字段不校验。

### 2.5 关键权衡

1. **按内容探测而非按 artifact_type 探测**：旧扁平契约固定 6 个字段、无 `payload` 键，探测零歧义；若按 `artifact_type` 探测，缺失该字段的 Envelope 会被误判为扁平报告并报出误导性错误。代价：旧扁平报告若意外含 `payload` 键会被判为 Envelope——旧契约无此键，概率极低，且报错会标注解析格式引导修正。
2. **Envelope 顶层字段从宽**：严格校验 `run_id` 或 `commit_sha` 会把断层 3（Git-only pattern）拖进本 Change，且纯 OPSX 流程没有 Run Context 可提供这些值，强制校验等于变相强迫 OPSX 建 Run，违背双轨定位。Run 绑定一致性本属 `runtime_trust` 职责，不在 OPSX 阶段门重复。
3. **扁平格式无限期保留**：本 Change 的定位是止血对齐，不是协议迁移；废弃扁平格式需要 Production 项目侧迁移窗口，留给 B/C 档统一决策。

## 3. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，机器门段落补充双格式报告契约。
- `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`：MODIFIED，§6 接入矩阵补充 OPSX 双轨适用范围（无 Run Context 时扁平报告由 `validate_change.py` 与人审放行；该豁免不适用于 `scope: run`）。

## 4. 参考资料

- 误杀点：`scripts/validate_change.py:142-209`
- 新协议：`skills/workflow-code-review/SKILL.md:270-300`、`schemas/runtime/review-report.schema.json`
- 已同步参照：`skills/workflow-code-generation/scripts/check_delivery.py:79-110`
