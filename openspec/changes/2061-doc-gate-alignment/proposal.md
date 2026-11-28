# Proposal: 文档模板与校验脚本对齐（Quick Draft）

**作者**：YanQi
**日期**：2026-11-28
**变更**：2061-doc-gate-alignment
**状态**：Quick Draft

---

## 1. 问题与目标

### 问题

框架要求的各类 Markdown 与校验脚本存在五处不一致，照指令写会被脚本拦截，或脚本形同虚设：

1. 需求澄清指令规定无长期知识影响时「不创建占位 Delta」（`skills/workflow-requirements-clarification/SKILL.md:159`），而 `validate_change.py` 的 OPSX018 要求 Standard 至少有一个 Delta，OPSX043 又禁止「有 Delta 且声明无影响」，两者无法同时满足；OPSX029 还要求映射表出现 `spec.md`，新 Change 已禁止写入 `spec.md`。
2. `lint_spec.py` 未接入任何流程步骤，而 `docs/tooling/08-evaluation-strategy.md:52` 声称已挂在系统设计前置条件与代码生成步骤 2。
3. 启用 Verify 而项目无 `verify.config.json` 时，`native_subject.py` 把配置缺失记为覆盖限制，Verify 总判定 ERROR；多处指令却声明无配置可只跑内置检查。
4. `task_planning_guide.md` 的模板未覆盖 Production 计划门与交付门要求的字段，按模板生成的 `tasks.md` 无法通过 Production 校验。
5. 公共知识库的 `status` 合法值只存在于 `validate_shared_knowledge.py`，规则文档未写；全局规则要求的 `superseded` 与 `superseded_by` 不被脚本接受。

### 目标

- 指令、模板与脚本对上述五处给出同一口径，照指令写能通过脚本。
- `lint_spec.py` 在文档写完的时点被调用。

### 非目标

- 不修改公共知识库中已有条目的 `status` 值，只列出清单交用户决定。
- 不处理本轮审计中的其他中低优先级项（Review JSON 结论词、交付门 `--subject-base`、`## 4.x` 章节覆盖等）。
- 不把 `lint_spec.py` 接入 `check_delivery.py` 或 `workflow_control.py` 机器门禁。

### 验收标准

- Standard Change 在 proposal 声明「无长期知识影响：<理由>」且无 Delta 时，`validate_change --phase plan` 不报 OPSX018 与 OPSX029 的 spec 缺失；声明有影响而无 Delta 时仍报 OPSX018。
- 无 `verify.config.json` 时 `native_subject.capture_subject` 返回 `complete=True`（无其他限制时），补上配置后 `subject_id` 改变。
- `validate_shared_knowledge.py` 接受 `superseded`，且 `superseded` 缺少 `superseded_by` 时报错；长期 Spec、公共库写入规则和晋升参考写明五个合法值。
- 按 `task_planning_guide.md` 的 Production 追加字段生成的样例通过 `validate_change --phase plan --governance-profile production` 的 Tasks 相关规则。
- `workflow-system-design`（前置条件、设计完成前）与 `workflow-code-generation` 步骤 2 写明 `lint_spec.py` 调用与失败处理；08 文档描述与实际一致。
- 全量测试通过，`lint_skill_graph.py` 0 错。

## 2. 设计方案

### 2.1 整体方案

按「改与现行模型不符的一侧」逐项对齐：规则过时的改脚本（OPSX018／029、`verify_config_missing`、公共库状态值），指令缺失的补指令（Production 字段、`lint_spec` 接线、状态值说明）。

### 2.2 核心组件

- `scripts/validate_change.py`：Standard 路径读取 proposal「知识影响」，声明无影响时豁免 OPSX018；OPSX029 只在存在 Delta 时要求映射 Delta。
- `scripts/native_subject.py`：删除 `verify_config_missing` 限制；主体已记录 `config_sha256: null`，配置变化仍改变 `subject_id`。
- `scripts/validate_shared_knowledge.py`：允许值增加 `superseded`，并校验 `superseded_by` 非空。
- `skills/workflow-code-generation/reference/task_planning_guide.md`：新增「Production 追加字段」小节。
- `skills/workflow-system-design/SKILL.md`、`skills/workflow-code-generation/SKILL.md`：接入 `lint_spec.py`。

### 2.5 关键权衡

- **不建占位 Delta 而非放宽 OPSX043**：OPSX018 早于统一知识模型（`95cb742` 与 `677a4fd` 同日先后提交），Delta 现指长期知识变更，占位 Delta 会在归档时被合并或需特判；放弃「要求占位 Delta」。
- **`superseded` 与 `deprecated` 并存**：`superseded` 表示被指定条目取代，必须填 `superseded_by`；`deprecated` 表示失效且无替代。放弃「全局规则改用 deprecated」，因为会丢失替代指向。
- **`lint_spec` 只接指令层**：放在文档写完的时点修正成本最低；放弃交付门（太晚）和 `workflow_control start` 机器门禁（会卡住进行中的 Change，Tooling 轨无先例）。
- **配置缺失不算覆盖不完整**：无配置是指令允许的合法状态，主体对配置的绑定由 `config_sha256` 承担；放弃「改指令要求必须先有配置」，因为会推翻多处低侵入默认。

## 3. 知识影响

- `openspec/specs/backend/engineering/tech/knowledge-management.md` §11 证据等级：增加 `superseded` 及 `superseded_by` 要求（Delta：`specs/backend/engineering/tech/knowledge-management.md`）。
