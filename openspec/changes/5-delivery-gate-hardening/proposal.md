# Proposal: 修复 Run 交付门信任契约缺陷与审查硬化（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：delivery-gate-hardening
**状态**：Quick Draft

---

## 1. 问题与目标

### 问题

Change 4 的交付门执行暴露出框架自身的四处缺陷（均有实证）：

1. **Trust Gate 生产路径必挂（P0 级框架 bug）**：`run_journal.py:326-334` 的 `validate_task_sources` 用 init-run 时冻结的 tasks.md 快照的 `- 状态:`（必然为「未开始」）与 journal 重放的任务终态（「完成」）做相等校验，任何按文档流程走的真实 Run 都必然冲突。证据：`runtime_trust.py:230-232` 读取冻结快照；change 2 与 change 4 的快照均为「未开始」；全仓无代码刷新该快照；`test_runtime_trust.py:123` 的 fixture 手写「状态：完成」快照，与生产路径不一致，所以测试绿而生产挂；change 2 的已交付 Run 在当前代码下也过不了 `validate_run`（`invalid_run_evidence`），说明该路径从未被真实 Run 走通过。
2. **Polyglot 双面报告静默放行**（change 4 strict review F-5，critic 成立）：顶层 `verdict: NEEDS_CHANGES` + dict `payload` 内 PASS 的文件，`validate_change.py` 新版放行、旧版拒绝；放行时无任何格式标注。
3. **断腿 Envelope 无定向报错且无测试锁定**（F-1/F-2，critic 成立）：`payload` 键存在但非 dict 时落入扁平分支，报 6 条「扁平格式…None」却不指向真正缺陷；该回落路径无测试。
4. **信任模型免责句挂错表示形态**（F-6，critic 成立）：`trust-model.md` §6 免责声明只附加于扁平 JSON，未覆盖「无 Run Context 的 Envelope」——该类产物展示的 `run_id` / `commit_sha` 未经任何组件验证。

另有一项框架级不一致（critic F-3 驳回时提示的治理议题）：`task_planning_guide.md` 模板中文标签用半角冒号，而 `workflow_control.py:410` 机器写入全角，导致每个生成的 tasks.md 内部标点不一致。

### 目标

1. 修复 `validate_task_sources` 消费侧缺陷：冻结快照只承担计划完整性（task_ids 一致性），任务状态 / attempts 一致性改由 manifest `payload.tasks` 腿（由交付时 task-state artifacts 构建）承担；补生产保真回归测试（冻结「未开始」快照 + 完成 journal 必须 PASS）。
2. `validate_change.py` 硬化：Envelope 模式下顶层携带裁决字段判格式冲突拒绝；`payload` 键存在但非 dict 追加定向错误并拒绝；测试锁定全部边界。
3. `trust-model.md` §6 免责句扩展为任一格式，并补 unbound Envelope 绑定字段未验证的声明；契约文档同步第 2 项的行为变化。
4. 两份 `task_planning_guide.md` 中文标签标点统一为全角，消除模板与控制平面的不一致源。

### 非目标

- 不改 Run Context 的 Git-only 现状（SVN 适配另立议题）。
- 不改 `check_delivery.py` 的重试幂等性（finalize 失败后需手工清理可再生 artifact，已在 change 4 交付报告中记录，另行评估）。
- 不回改已归档的 change 4 tasks.md 排版。
- 不变更扁平格式与 Envelope 的双轨定位本身。

### 验收标准

- 生产保真回归：`validate_run` 对「冻结『未开始』快照 + 完成 journal + 合法 manifest」的 Run 判定 PASS；`python -m pytest scripts -q` 全量通过。
- polyglot 文件（顶层与 payload 同时携带裁决字段）被 delivery / archive 门禁拒绝且报错含「格式冲突」；`payload` 非 dict 时被拒绝且报错指向 payload 类型；无 `payload` 键的纯扁平报告放行不回归。
- `trust-model.md` §6 免责声明覆盖任一格式，含 unbound Envelope 绑定字段未验证的声明。
- 两份 `task_planning_guide.md` 中文标签全角化，`lint_task_deps.py` 对既有 tasks.md（半角）与新格式（全角）均解析正常。
- Change 4 的交付门在修复合入后重跑通过。

## 2. 设计方案

### 2.1 整体方案

Bug 修复走消费侧（用户已拍板）：`validate_task_sources` 删除冻结快照的 `状态` / `attempts` 比对（326-334 行），保留任务存在性三方一致性检查；状态 / attempts 一致性由既有 manifest 腿（335-338 行，`manifest_task["state"]` / `["attempt"]` vs journal 重放）承担——manifest `payload.tasks` 由 task-state artifacts 构建（`run_manifest.py:395-407`），task-state artifacts 由 `check_delivery --tasks` 的交付时当前 tasks.md 生成，因此该比对等价于「journal vs 交付时当前 tasks.md」，且全程在 Run 目录内、经 manifest digest 绑定，不引入外部文件读取。

校验器硬化在同一函数内追加两条失败关闭规则，均先报错再照常评估，保持累积式报错风格。

### 2.2 核心组件

- `run_journal.validate_task_sources`：删除冻结快照状态比对；`runtime_trust._validate_journal` 调用点与参数随动；测试补生产保真用例。
- `validate_change._validate_review_report`：Envelope 分支增加顶层裁决字段冲突检查；新增 `payload` 键存在但非 dict 的定向错误分支。
- 契约与信任文档：`trust-model.md` §6（免责扩展 + 冻结快照职责边界）、`quality-gates/overview.md:51` 与 `opsx-code-generation/SKILL.md:110` / `:164`（同步冲突拒绝与 payload 非对象拒绝行为）。
- 两份 `task_planning_guide.md`：中文标签（`### 任务 N：`、`- 状态：`、`- 文件：`、`- 说明：`、`- 文档映射：`、`- 子任务：` 等）半角冒号改全角；英文 key（`depends_on:` / `review_profile:` 等）与代码 span、正则示例不动。

### 2.5 关键权衡

1. **状态比对改走 manifest 腿而非读当前 tasks.md 文件**：`validate_run` 只接收 run_dir，读外部可变文件会削弱 Run 目录 containment；manifest `payload.tasks` 本身就是交付时 tasks.md 的 Run 内绑定代表（经 task-state artifacts 传递），信息等价且证据更强。代价：比对链多一层间接，需在 trust-model.md 写清传递关系。
2. **payload 非 dict 直接拒绝而非回落扁平**：断腿 Envelope 回落扁平会把「写坏的 Envelope」静默当扁平处理，诊断方向错误；存在 `payload` 键即表明生产者意图是 Envelope，拒绝并给出定向错误更安全。代价：扁平报告若意外携带 `payload: null` 类杂键将被拒——旧扁平契约无此键，概率极低，且报错消息明确。
3. **标点修模板而非修控制平面**：md-zh 要求中文用全角标点，`workflow_control.py:410` 已是全角，统一方向为模板向控制平面对齐；既有半角 tasks.md 由 lint 正则 `[:：]` 双兼容继续解析，不回改。

## 3. 知识影响

- `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`：MODIFIED，§6 免责扩展 + 冻结快照职责边界（§4.4 或 §6）。
- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，双格式契约补冲突拒绝与 payload 非对象拒绝。
- `openspec/specs/backend/framework/workflow-control/`：检查 journal / 状态一致性描述是否涉及 `validate_task_sources` 语义，涉及则同步。

## 4. 参考资料

- bug 现场：`scripts/run_journal.py:297-340`、`scripts/runtime_trust.py:215-279`、`scripts/run_manifest.py:381-407`
- change 4 strict review 报告（F-1/F-2/F-5/F-6 裁决明细与 critic 证据）
- 不一致源：`skills/workflow-code-generation/scripts/workflow_control.py:410`、`skills/*/reference/task_planning_guide.md`
