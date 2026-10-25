# Proposal: 知识合同补全——共享条目退役语义与定位链缺口

**作者**：Claude（default-agent-admin）
**日期**：2026-10-26
**变更**：knowledge-retirement-contracts
**状态**：Draft

---

## 1. 背景

### 1.1 问题描述

- 知识合同按「建立、新增、更新、删除、读取」五个动作审计后，「删除/退役」无操作 SOP：Change 路径有 Delta `REMOVED` 动词，但走「既有知识澄清」直写路径（`project-knowledge` §7.1）更新的 glossary/rules/flows/overview 条目、`custom/` 三件套和 `issues/` 条目没有作废手段，只能改写或沉默保留。
- 定位链缺口：`business/index.md` 在结构树与 §3.4 读取路由中被要求存在，但无职责定义；glossary 分节名（业务上下文）与 `<domain>/` 目录名的映射无约定，不一致时 §3.4 定位断链；「小项目允许根索引直接链接条目」未指明哪级索引。
- `research.md` 已是 Change 标准中间产物（`knowledge-management.md` §5.5、需求澄清/系统设计技能均接线），但 `project-knowledge` §2 的 Change 目录树未列入，两处合同漂移。

### 1.2 现状分析

- 仓库已有四种状态机制各管一段：ADR Status 枚举含 `deprecated`/`superseded by`（`bp-domain-modeling/reference/adr-format.md`）、公共库证据等级含 `deprecated`（`knowledge-management.md` §11.1）、`meta.yaml` 有 `status` 字段、Change Delta 有 `REMOVED`。本次不发明新机制，把这些语义收拢为直写路径的退役操作规则。
- `skills/project-knowledge/SKILL.md` 是操作合同权威（`knowledge-management.md` §19 显式回指），补丁落点在此及写入方 `bp-domain-modeling`。
- 缺口现状已于 2026-10-26 通读核对并沉淀至 `openspec/specs/backend/framework/knowledge-management/overview.md` 合同速查节（commit `8668968`）。

### 1.3 主要使用场景

- Agent 或用户要作废一条已确认的术语、规则或流程（如业务放弃部分退款）时，有确定的标记写法与索引同步义务。
- 新增业务域或术语分节时，映射登记位置明确，读取路由不断链。
- Change 目录树与实际产物一致，编码阶段通读清单有合同依据。

## 2. 目标

- 直写路径的共享条目具备统一的退役标记法与同步义务，与既有四种状态机制衔接。
- `business/index.md` 获得职责定义；glossary 分节与 `<domain>/` 目录的映射有登记位置与维护时机。
- `project-knowledge` §2 目录树、`knowledge-management.md` §4 树与 §5.2 职责三处对 `research.md`、`business/index.md` 一致。

### 2.1 非目标

- 不新增机器校验器、门禁参数或安装器改动。
- 不重排 `project-knowledge/SKILL.md` 既有章节号（外部引用锚定 §3.4/§5/§7.1/§9）。
- 不制定 domain 粒度与嵌套标准（既有兜底规则「判断不了不猜目录」已工作）。
- 不改公共库结构与晋升流程；不动 `workflow-code-review/SKILL.md` 的既有未提交改动（非本 Change 产物）。

## 3. 需求概览

### 3.1 功能性需求

- `project-knowledge/SKILL.md` 新增共享条目退役小节：Change 路径沿用 Delta `REMOVED`；直写路径不物理删除，加状态标记（glossary 行内标注、rules/flows/overview/`issues/` 状态行、`custom/` 沿用人工确认 + 状态标注，decisions 沿用 adr-format Status 枚举）；同轮更新索引与引用方；自动流程禁止物理删除，物理删除仅限用户明确授权。
- `project-knowledge/SKILL.md` §3.4 补 `business/index.md` 职责与 `specs/index.md` 澄清。
- `project-knowledge/SKILL.md` §2 Change 目录树补 `research.md`。
- `bp-domain-modeling/SKILL.md` 补 rules.md 不变量判据；`reference/glossary-format.md` 补分节-目录映射登记规则。
- `knowledge-management.md` §4 树补 `research.md` 行、§5.2 补 `index.md` 职责行、§9.1 指针更新（经 Delta，归档合并）。
- `openspec/specs/backend/framework/knowledge-management/overview.md` 合同速查节与 `docs/framework-features-status-and-comparison.md` §4.6 同步状态。

### 3.2 非功能性需求

- 兼容：不改变既有读取路由与写入位置的语义，只做增量；既有 `--knowledge-impact` 机器参数不变。
- 可维护：退役规则只写一处（`project-knowledge/SKILL.md`），其他位置引用。

### 3.3 验收标准

- `lint_skill_graph.py`、技能 `quick_validate.py`、`git diff --check` 通过。
- `lint_spec.py`（proposal/design 两 phase）与 `lint_task_deps.py`（tasks.md）通过。
- 定向 pytest 通过：`test_skill_slimming_contracts.py`、`test_profile_contracts.py`（若断言合同文本则同步更新断言）。
- `research.md` 在两棵目录树均出现；`business/index.md` 职责在 SKILL.md §3.4 与 knowledge-management.md §5.2 均可查。
- 全量 `verify.py` 通过；独立最终 Review 无未解决 P0/P1。
- 新增中文段落通过 md-zh 自检（中英文空格、全角标点、专有名词大小写）。

## 4. 知识影响

- Delta：`specs/backend/engineering/tech/knowledge-management.md` → `openspec/specs/backend/engineering/tech/knowledge-management.md`（MODIFIED：§4 树、§5.2 职责、§9.1 指针）。
- Delta：`specs/backend/engineering/tech/external-reference-mattpocock-skills.md` → `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`（MODIFIED：§9.1 指针补 §7.3，review P2-3 连带同步）。
- 直接维护（2057/2058 先例：行为合同直接维护在技能与状态文档）：`skills/project-knowledge/SKILL.md`、`skills/bp-domain-modeling/SKILL.md`、`skills/bp-domain-modeling/reference/glossary-format.md`、`openspec/specs/backend/framework/knowledge-management/overview.md`、`docs/framework-features-status-and-comparison.md` §4.6。
- 无跨项目候选：全部为本框架内部合同事实，不满足公共库晋升的泛化前提。

## 5. 参考资料

- `skills/project-knowledge/SKILL.md`（操作合同权威，§2/§3.4/§5/§6.2/§7.1/§7.2）
- `openspec/specs/backend/engineering/tech/knowledge-management.md`（方案记录，§4/§5.2/§5.5/§9.1）
- `skills/bp-domain-modeling/reference/adr-format.md`（Status 枚举来源）
- `skills/bp-domain-modeling/reference/glossary-format.md`（分节规则现状）
- `openspec/changes/2054-research-note-persistence/`（Delta 格式先例）
