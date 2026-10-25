# 实施任务清单

> 由 proposal.md、design.md 和 Delta 生成的候选任务。
> 任务总数：3
> 状态：Archived（实现、机器检查及语义 Review 完成；最终交付裁决见机器产物）
> 核心原则：先建立共享方法与入口，再接入现有流程，最后行为评测与知识同步。

- Code Review: PASS

用户在第二次文档审核后明确要求「可以实施」，并要求完成 Change、提交并推送。D1～D7 按本文及 design.md 的推荐方案执行；任务完成与 Review 结果仍以实际证据为准。

## 依赖关系总览

```text
Task 1（共享方法与入口）
    ↓
Task 2（现有流程接入）
    ↓
Task 3（行为验收与知识同步）
```

采用线性依赖，避免规则与调用方并行修改造成契约漂移。

## 变更影响概览

### 文件变更清单

以下为审核后的预期实施面，不是本轮已修改文件。

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/bp-decision-interview/SKILL.md` | 新增 | Task 1 | 获批的共享追问方法 |
| `skills/bp-domain-modeling/SKILL.md` | 新增 | Task 1 | 获批的领域建模与知识路由 |
| 两个新方法技能目录的 `LICENSE` | 新增 | Task 1 | 保留上游 MIT 许可并随技能发行 |
| `commands/grill-me.md` | 新增 | Task 1 | 通用讨论薄入口 |
| `commands/grill-with-docs.md` | 新增 | Task 1 | 工程访谈薄入口 |
| `scripts/install_agentic_framework.py` | 修改 | Task 1 | 显式安装清单加入新技能和命令 |
| `scripts/test_interview_installation.py` | 新增 | Task 1 | 独立安装回归，不改动预存修改的安装测试 |
| `skills/workflow-requirements-clarification/SKILL.md` | 修改 | Task 2 | 决策依赖提问与阶段限制 |
| `skills/workflow-system-design/SKILL.md` | 修改 | Task 2 | 章节覆盖与提问顺序分离 |
| `skills/workflow-system-design/reference/section-guide.md` | 修改 | Task 2 | 消除与新提问顺序冲突的参考指引 |
| `skills/project-knowledge/SKILL.md` | 修改 | Task 2 | 共享领域模型的读取与双轨写入单一规则来源 |
| 当前 Change 的 `validation.md` | 新增 | Task 3 | 结构与行为评测证据 |
| 当前 Change 的 `evidence/` | 新增 | Task 3 | 原样前向试验、阶段回归与有限对照记录 |
| 当前 Change 的知识 Delta | 修改 | Task 3 | 按实际裁决及结果更新 |
| `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md` | 修改 | Task 3 | 归档同步，不提前覆盖 |
| `openspec/specs/backend/engineering/tech/knowledge-management.md` | 修改 | Task 3 | 同步共享模型与读写合同 |

### 受影响接口

新增两个用户命令，改变需求与系统设计的对话组织方式；不修改运行时接口、任务 Schema 或 Review 状态机。共享方法仅由明确访谈请求或现有阶段按需使用，不以普通问答、阅读术语表等近邻请求触发完整访谈。

### 构建系统变更

无编译目标变化。已核实安装器使用显式技能和命令清单，Task 1 将补齐清单并新增独立安装测试；上游许可分别置于两个新技能目录的 `LICENSE`，随技能目录一起发行。技能与命令新文件先暂存到 Git 索引，使既有仅复制受跟踪文件的安装测试覆盖当前候选来源，不提交其他会话的修改。

## 风险与假设

| 编号 | 描述 | 影响任务 | 处理 |
| --- | --- | --- | --- |
| 1 | D1～D7 已获实施批准 | 全部 | 按已审核推荐方案执行，不扩大范围 |
| 2 | 上游资料基准已固定 | Task 1 | README 标注 5beb35b，方法原文哈希与本地清单一致；未冒用旧研究基准或声称远程核验 |
| 3 | 安装器为显式清单 | Task 1 | 本轮已将必要清单与独立安装测试纳入范围 |
| 4 | 静态规则通过不代表对话有效 | Task 3 | 固定输入并保存实际行为轨迹 |
| 5 | 工作区存在其他会话修改 | 全部 | 不覆盖、不清理；只核对本 Change 及授权实施范围 |

## 任务列表

### 任务 1：[x] 建立共享方法与两个薄入口
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/bp-decision-interview/SKILL.md`（新增）、`skills/bp-decision-interview/LICENSE`（新增）、`skills/bp-domain-modeling/SKILL.md`（新增）、`skills/bp-domain-modeling/LICENSE`（新增）、`commands/grill-me.md`（新增）、`commands/grill-with-docs.md`（新增）、`scripts/install_agentic_framework.py`（修改）、`scripts/test_interview_installation.py`（新增）
- depends_on: []
- review_profile: standard
- Task Review: Pending
- 验收标准：下列 verification 全部通过，入口可发现、可加载且无未授权副作用。
    - [x] 技能图校验与隔离安装检查通过，实际轨迹显示两个入口加载相应方法。
- 文档映射：proposal.md §2～3；design.md §4.1～4.3、§5～6、§9
- 说明：审核批准后实现方法与入口；区分建议、记录和执行授权，保留停止条件；固定上游来源并保留适用许可。没有必要不创建辅助脚本或额外文件。
- context_files:
    - `skills/bp-skill-authoring/SKILL.md` — 技能编写约定。
    - `skills/project-knowledge/SKILL.md` — 下游知识写入唯一规则。
    - `commands/requirements-clarification.md` — 上游命令入口形式。
    - `scripts/install_agentic_framework.py` — 下游发行和宿主适配，实施前核实。
    - `scripts/lint_skill_graph.py` — 引用存在、frontmatter 与连通性检查。
    - `openspec/changes/2053-decision-interview-domain-modeling/design.md` — 候选职责与待批决策。
- verification:
    - [x] `python scripts/lint_skill_graph.py` 无本任务新增错误；记录原有问题与新问题的区别。
    - [x] `python -m pytest scripts/test_install_agentic_framework.py -q`，报告结果和失败归因。
    - [x] 隔离安装后实际发现并加载两个入口与方法，检查通用模式无写入、工程模式先检查阶段与授权。
- artifacts:
    - `skills/bp-decision-interview/SKILL.md`
    - `skills/bp-domain-modeling/SKILL.md`
    - `commands/grill-me.md`
    - `commands/grill-with-docs.md`
    - `skills/bp-decision-interview/LICENSE`
    - `skills/bp-domain-modeling/LICENSE`
    - `scripts/install_agentic_framework.py`
    - `scripts/test_interview_installation.py`
- 子任务：
    - [x] 确认审核裁决、上游版本、许可及必要发行面。
    - [x] 编写单一来源方法和薄入口，按 md-zh 与指令维护原则自检。
    - [x] 运行结构与隔离安装检查，保留输出供 Task 3 汇总。

### 任务 2：[x] 接入需求、系统设计与共享领域知识合同
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-requirements-clarification/SKILL.md`（修改）、`skills/workflow-system-design/SKILL.md`（修改）、`skills/workflow-system-design/reference/section-guide.md`（修改）、`skills/project-knowledge/SKILL.md`（修改）
- depends_on: Task 1
- review_profile: standard
- Task Review: Pending
- 验收标准：下列 verification 全部通过，阶段边界与原有审批不被绕过。
    - [x] 缺失需求、已有答案、上游决定变更三个场景分别满足不越界、不重问、重算依赖。
- 文档映射：proposal.md §1、§3；design.md §4.3～4.5
- 说明：只修改审核通过的对话契约。消除同文件中相反的单问题和顺序硬限制，保留需求与设计分界、已有审批、Proposal 与 Design 产物规则，不修改快速设计。
  共享模型读取、既有澄清及时写入、未来变化 Delta 及索引维护规则统一写入 project-knowledge；需求与设计引用该规则。实现、测试与 Review 沿其现有知识路由复用，不改动快速设计的步骤与审批。
- context_files:
    - `skills/workflow-requirements-clarification/SKILL.md` — 直接修改需求对话约束。
    - `skills/workflow-system-design/SKILL.md` — 直接修改设计对话约束。
    - `skills/project-knowledge/SKILL.md` — 直接修改共享领域模型读取与双轨写入合同。
    - `skills/bp-decision-interview/SKILL.md` — Task 1 的方法来源。
    - `skills/bp-domain-modeling/SKILL.md` — Task 1 的记录规则。
    - `commands/requirements-clarification.md` — 上游需求入口。
    - `commands/system-design.md` — 上游设计入口。
    - `skills/workflow-code-generation/SKILL.md` — 下游交付边界，不在本任务修改。
- verification:
    - [x] `python scripts/lint_skill_graph.py` 无本任务新增错误。
    - [x] `python -m pytest scripts/test_lint_skill_graph.py -q`，报告结果。
    - [x] 用缺失需求、已有完整答案、改变上游决定三个场景检查真实对话，分别验证不越界、不重问、重算依赖。
    - [x] 对照 design.md §4.3.1 逐条核对，未批准的安全、审批、验证要求无弱化。
    - [x] 检查读取链涵盖领域讨论前的术语与模型加载；无 Change 的既有知识澄清不被强制转为功能开发，未来变更不提前写入长期知识。
- artifacts:
    - `skills/workflow-requirements-clarification/SKILL.md`
    - `skills/workflow-system-design/SKILL.md`
    - `skills/project-knowledge/SKILL.md`
    - `skills/workflow-system-design/reference/section-guide.md`
- 子任务：
    - [x] 定向修改路由和冲突规则，不重写无关章节。
    - [x] 检查命令调用与下游交接，保持原有阶段批准。
    - [x] 在 project-knowledge 维护 design.md §4.2.6 的唯一读写规则，并接线需求与设计调用方。
    - [x] 运行结构及代表性行为回归，保存证据。

### 任务 3：[x] 完成行为验收、统一 Review 与知识同步
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`openspec/changes/2053-decision-interview-domain-modeling/validation.md`（新增）、`openspec/changes/2053-decision-interview-domain-modeling/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`（修改）、`openspec/changes/2053-decision-interview-domain-modeling/specs/backend/engineering/tech/knowledge-management.md`（修改）、`openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`（修改）、`openspec/specs/backend/engineering/tech/knowledge-management.md`（修改）
- depends_on: Task 2
- review_profile: standard
- Task Review: Pending
- 验收标准：下列 verification 全部通过，行为矩阵逐项判定并完成统一 Review。
    - [x] design.md §7 每个场景都有实际结果，禁止副作用场景的文件快照与工具轨迹无越权操作。
- 文档映射：proposal.md §3.3～5；design.md §7～8；知识 Delta 全文
- 说明：执行 design.md §7 的行为矩阵与有限对照；统一 Review 完成后按现有归档流程同步知识。不得用结构校验代替效果证据，不因本任务存在自动提交或发布。
- context_files:
    - `openspec/changes/2053-decision-interview-domain-modeling/proposal.md` — 验收条件。
    - `openspec/changes/2053-decision-interview-domain-modeling/design.md` — 行为矩阵。
    - `skills/workflow-code-review/SKILL.md` — 下游统一最终 Review。
    - `skills/project-knowledge/SKILL.md` — 下游归档同步规则。
    - `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md` — 长期同步目标，保留既有研究上下文。
    - `openspec/specs/backend/engineering/tech/knowledge-management.md` — 共享模型与生命周期长期合同目标。
- verification:
    - [x] `python scripts/lint_skill_graph.py`，记录结构结果。
    - [x] `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2053-decision-interview-domain-modeling/tasks.md --governance-profile tooling`。
    - [x] `python scripts/validate_change.py --repo . --change openspec/changes/2053-decision-interview-domain-modeling --phase plan --governance-profile tooling`。
    - [x] `python -m pytest scripts/test_lint_skill_graph.py scripts/test_install_agentic_framework.py -q`，保存实际结果。
    - [x] design.md §7 每个场景均有预期、轨迹与实际结论；禁止副作用用例检查文件快照和工具调用。
    - [x] 未达到验收标准则明确失败，不晋升知识为已验证结论、不宣称交付完成。
    - [x] 在隔离项目由会话 A 写入获授权的既有定义，会话 B 只接收新需求与根索引，检查实际读取与理解；再验证未来规则仅在 Delta、不污染主本。
    - [x] 同名概念、共享条目与两个 Change Delta 冲突、只有含义确认而无写入授权三类场景均按 design.md §7 判定。
- artifacts:
    - `openspec/changes/2053-decision-interview-domain-modeling/validation.md`
    - `openspec/changes/2053-decision-interview-domain-modeling/evidence/`
    - `openspec/changes/2053-decision-interview-domain-modeling/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`
    - `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`
    - `openspec/changes/2053-decision-interview-domain-modeling/specs/backend/engineering/tech/knowledge-management.md`
    - `openspec/specs/backend/engineering/tech/knowledge-management.md`
- 子任务：
    - [x] 运行行为矩阵并比较原流程与候选流程，记录模型、宿主及权限边界。
    - [x] 汇总结构检查、实际加载证据与行为结果，进入统一最终 Review。
    - [x] 按最终裁决更新 Delta；归档时同步长期研究，不提前回写。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal.md §1～2 | Task 1, Task 2 | 能力定位及范围 |
| proposal.md §3.1～3.2 | Task 1, Task 2 | 方法与阶段集成 |
| proposal.md §3.3 | Task 3 | AC1～AC10 验收 |
| spec.md（旧校验器映射标签，实际需求规格为 proposal.md §3，无此文件） | Task 3 | 仅兼容校验器要求的标签，不创建旧规格文件 |
| proposal.md §4～5 | Task 3 | 知识影响与来源核对 |
| design.md §4.1～4.2 | Task 1, Task 2 | 入口、方法、共享模型及授权 |
| design.md §4.3～4.5 | Task 1, Task 2 | 冲突裁决，须先审核 |
| design.md §5～6、§9 | Task 1 | 备选、上游版本与许可 |
| design.md §7～8 | Task 3 | 评测、证据与交付边界 |
| specs/backend/engineering/tech/external-reference-mattpocock-skills.md 全文 | Task 3 | 按实际结果同步 |
| specs/backend/engineering/tech/knowledge-management.md 全文 | Task 2, Task 3 | 共享模型操作合同及长期同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/engineering/tech/external-reference-mattpocock-skills.md` | `openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md` | MODIFIED | 完成 | 定向内容及历史状态限定已更新，既有入口不变 |
| `specs/backend/engineering/tech/knowledge-management.md` | `openspec/specs/backend/engineering/tech/knowledge-management.md` | MODIFIED | 完成 | 共享模型与双轨知识合同已更新，既有入口不变 |

## 知识冲突

- Resolved：阶段技能与上游的提问、建议及落盘冲突按获批 design.md §4.3.1 实施，阶段与授权边界保留；实际行为见 validation.md。
- Resolved：最初研究 d81f3a1 与本次资料 5beb35b 分别记录，不混淆版本；本地方法原文哈希核对通过。
- Resolved：project-knowledge §7.1 新增既有澄清分支，并在 §9 消除强制创建功能 Change 的相反规则；未来变化仍走 Delta，不扩大人工知识与公共知识权限。

## 实际 Diff 核对

- 核对状态：PASS。实现、有限行为回归、定向 round 1、真实安装与编码补验及原配置全量 Verify 均已通过。归档后的内容绑定及交付门另以真实机器产物核对，不将本记录当作交付 Verdict。
- 既有工作区修改不属于本 Change，不覆盖、不清理、不纳入本次成果。
- 实际机器检查、原样行为轨迹、首审及复审结论、干净基准对照和限制均记录于 validation.md；复选框仅在对应实测完成后勾选，Tooling 采用统一集成 Review，不回写各 Task 的独立 Review 结果。
