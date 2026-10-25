# Proposal: 引入决策依赖追问与领域建模能力

**作者**：Codex（根据用户请求整理）
**日期**：2026-10-25
**变更**：2053-decision-interview-domain-modeling
**状态**：Archived（已实现并完成机器验证与语义 Review，用户最终验收另行确认）

> 第二次文档审核后，用户明确要求「可以实施」，并要求完成本 Change、提交并推送。实施采用 design.md D1～D7 推荐方案，不将实施批准当作验收通过。

---

## 1. 背景

### 1.1 问题描述

- 用户希望分析并引入 Matt Pocock 的 `/grill-me` 与 `/grill-with-docs`。本 Change 保存适配候选，供审核后决定是否实施。
- 需要补充的能力是按决策依赖组织追问，以及在讨论中主动澄清术语、检验概念边界和保存决策理由；不是增加一套平行工程工作流。
- 预期减少无效追问、重复确认与术语歧义，但目前只有静态源码分析，没有本框架效果对照证据，不承诺效率提升。

### 1.2 现状分析

- 上游两个入口分别委托 `grilling`，以及 `grilling` 加 `domain-modeling`；主要行为不在入口文件内，见第 5 节。
- `workflow-requirements-clarification/SKILL.md` 已要求 Agent 自查事实、用户提供需求、逐步更新 Proposal，但规定每轮一个核心问题，并限制未经请求直接给建议（第 59～80、265～285 行）。
- `workflow-system-design/SKILL.md` 按章节讨论，未经请求不给设计方案；需求不完整时停止并转回需求阶段（第 25～53、87～100 行）。
- `workflow-quick-design/SKILL.md` 已允许主动给方案，并要求复用已有上下文、避免重复审批（第 35～47、93～140 行）。本期不改动这条快速路径。
- `project-knowledge/SKILL.md` 已指定唯一知识路由，业务术语位于 `openspec/specs/business/glossary.md`，单次需求、设计与 Delta 位于当前 Change（第 111～138 行）。
- 直接叠加上游会造成提问节奏、推荐答案、写入位置和行动授权冲突。上述行号是本次读取快照，实施前需重新核对。

### 1.3 主要使用场景

- 通用思路推敲：用户要求检验计划或决定，不进入工程流程、不默认写文件。
- 工程需求访谈：先确认问题、目标和约束，不越界决定实现方案。
- 工程设计访谈：基于已确认需求讨论方案与权衡，并澄清领域词汇。
- 术语或事实冲突：展示术语、用户陈述和代码证据的差异，等待裁决，不静默覆盖。

## 2. 目标

- 提供可复用、受阶段边界约束的决策依赖追问方法。
- 提供领域术语澄清与决策理由沉淀方法，复用现有知识治理。
- 将领域模型维护为跨 Change 共享的项目知识，明确 Agent 的读取链及知识更新时机，不让业务理解依赖单次会话或历史 Change。
- 保留可显式调用的两个入口，但不改变原有审批、Review、交付和恢复职责。

### 2.1 非目标

- 不引入上游完整技能套件、工单平台或 setup 流程。
- 不新建 ADR 系统，不在根目录新增 `GLOSSARY.md` 或 `docs/adr/`。
- 不把对话决策树实现为运行时 DAG、状态数据库或新调度器。
- 不修改快速设计路径，不强制每次开发先运行访谈，不自动开始编码、提交或发布。
- 不实现超出已审核方案的能力，不将文档或结构校验通过视为行为验收通过。

## 3. 需求概览

### 3.1 功能性需求

- R1：按决策依赖组织轮次；独立且前提已明确的问题可分组，有依赖的问题后置；已确认答案直接复用。
- R2：可自行核实的事实由 Agent 调查；用户决定目标与取舍。证据不足时明确不确定性，不将猜测写成事实。
- R3：通用访谈默认只讨论；工程访谈遵循当前需求或设计阶段，不以新入口绕过已有前置检查和批准。
- R4：主动检验术语歧义、概念边界与代码一致性；术语表只放上下文特有定义，不混入实现方案。
- R5：记录有价值的决策理由，采用上游 ADR 三条件作为重点提示，而不是遗漏其他必要设计记录的理由；复用 design.md，不新增 ADR 目录。
- R6：写入前明确授权范围。已确认、仅澄清既有含义且无待解决事实冲突的知识，可在明确授权后及时更新项目共享模型；未来业务变化先进入当前 Change 的 Delta，交付归档再同步。无法分类时先留候选，不提前覆盖共享模型。
- R7：允许用户暂停、结束或延期问题；结束时区分已确认、待调查、延期与非目标。只要关键阻塞仍在，就不能宣称可实施。
- R8：领域模型包含术语、概念职责与关系、业务规则与不变量、跨模块流程，分别复用 `business/glossary.md` 和 `business/<domain>/` 下的 `overview.md`、`rules.md`、`flows.md`，不只保存词汇。
- R9：Agent 在解释领域需求或决定设计前，经 `openspec/index.md` 定向读取相关共享模型，再读取当前 Change 的已批准变化；后续实现、测试与 Review 在涉及领域语义时沿同一路由读取，不要求每个 Change 再次解释已有术语。
- R10：新建或更新共享条目时维护可达索引，记录确认来源与适用范围；只有模型确实不存在时才补充询问，不默认全库加载，也不自动推断业务定义。多个 Change 对同一概念提出不同变化时显式报告，不静默合并。

### 3.2 非功能性需求

- 共用规则只维护一个来源，两个命令保持薄入口，避免复制完整访谈流程。
- 不强制某个宿主专有的 Skill 工具或子 Agent；加载方式与可选委派服从宿主能力及项目授权。
- 中文文档遵循 md-zh；适配时保留上游适用的 MIT 版权与许可声明。
- 文本引用和图结构校验不代表技能实际加载；行为验收必须检查实际执行轨迹。

### 3.3 验收标准

- AC1：两个入口与共享方法可被框架发现，引用无悬空；适用与不适用场景明确。
- AC2：依赖追问场景中，不提前询问前提未定的问题；上游决定变更后重新检查受影响决定。
- AC3：事实自查、未知事实披露与事实冲突场景均有可复核证据。
- AC4：需求阶段不产出未经批准的设计；已有审批被复用，不重复访谈或自动进入实现。
- AC5：只讨论、暂停、拒绝写入场景均无越权文件写入、代码修改或外部操作；局部确认不扩大为整轮批准。
- AC6：术语与决策按唯一位置记录；既有知识澄清与未来业务变更使用不同写入时机，无新增平行知识目录、无自动公共知识晋升。
- AC7：结构校验和行为评测分别报告；无运行证据时只报告静态结论，不宣称效果提高。
- AC8：最终统一 Review 仍由现有流程负责，候选任务全部完成不代表自动批准提交或发布。
- AC9：独立新会话处理 Change B 时，能仅从项目索引找到 Change A 已沉淀的相关概念和规则，无须依赖 A 的会话或扫描历史 Change；实际读取轨迹可核查。
- AC10：同一术语在不同业务上下文含义不同、未来规则尚未交付、两个 Change 同时修改同一概念三类场景均不会污染共享主本；用户仅确认含义不被视为允许写入。

## 4. 知识影响

- 预期修改长期研究文档 `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`：补充本次源码分析、审核裁决和评测结果，明确候选与已实施的区别。
- 对应 Delta 已置于本 Change 的 `specs/backend/engineering/tech/external-reference-mattpocock-skills.md`，当前为 Pending，不回写长期文档。
- 另以 `specs/backend/engineering/tech/knowledge-management.md` 保存知识合同变更候选：领域模型跨 Change 共享、强制定向读取、双轨写入与索引维护。实施时同步修改 `skills/project-knowledge/SKILL.md`，知识路由规则仍以该技能为操作单一来源。
- 本 Change 本身不产生业务术语，不创建占位业务术语表。新技能的执行合同以实施后的技能及测试为准，不把研究文档当机器合同。

## 5. 参考资料

- 框架现状：`skills/workflow-requirements-clarification/SKILL.md`、`skills/workflow-system-design/SKILL.md`、`skills/workflow-quick-design/SKILL.md`、`skills/project-knowledge/SKILL.md`。
- 框架入口与结构校验：`commands/requirements-clarification.md`、`scripts/lint_skill_graph.py`、`scripts/install_agentic_framework.py`。
- 上游本地原文：`.learn-by-gpt/mattpocock-skills/source/skills/productivity/grilling/SKILL.md`、`source/skills/engineering/domain-modeling/SKILL.md`（后一路径同属该本地资料根）。
- 译文入口：`.learn-by-gpt/mattpocock-skills/zh-CN/README.md` 及对应两个入口的 SKILL.md。
- 既有研究：`openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`。其 2026-10-03 版本基准不自动代表本次本地源码版本；实施时单独确认来源版本。
