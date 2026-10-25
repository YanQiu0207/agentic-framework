# Design: 知识合同补全——共享条目退役语义与定位链缺口

**作者**: Claude（default-agent-admin）
**日期**: 2026-10-26
**状态**: Draft

> **编号说明**：design.md 保留历史局部编号 4～9，可与 proposal.md 的编号重叠，不重新编号。跨文件引用必须带文件名，例如「design.md §4.1」。

---

## 4. 设计方案

### 4.1 方案概览

全部改动为文档与合同文本，无代码。四条裁决：

1. **落点主从**：操作规则一律写进 `skills/project-knowledge/SKILL.md`（操作合同权威），`knowledge-management.md` 是方案记录，只经 Delta 同步树/职责/指针三处，不在其内另写平行操作规则（避免双事实源）。
2. **不发明机制**：退役语义收拢既有四种状态机制（adr-format Status 枚举、公共库证据等级 `deprecated`、`meta.yaml` status、Delta `REMOVED`），为直写路径统一标记法。
3. **保护既有引用**：`project-knowledge/SKILL.md` 不重排章节号——外部合同以「§3.4/§5/§6.2/§7.1/§7.2/§9」锚定引用（`knowledge-management.md` §7.1/§9.1、`openspec/specs/backend/framework/knowledge-management/overview.md` 速查节）。新规则作为 §7.3 插入，§8-§10 编号不变。
4. **行为合同直接维护**：技能文件与状态文档的改动不经 Delta（2057/2058 先例），仅 `knowledge-management.md` 长期方案文档走 Delta。

### 4.2 组件设计

#### 4.2.1 核心类或模块设计

不适用（无代码组件）。改动单元是六个 Markdown 文件，见 §4.3。

#### 4.2.2 接口设计

文本合同的「接口」是被外部引用的章节锚点与措辞：

- `project-knowledge/SKILL.md` §2 目录树新增 `research.md` 行，措辞与 `knowledge-management.md` §5.5 一致：「调研中间产物，追加式，随 Change 归档」。
- §3.4 新增 `business/index.md` 职责句与「小项目根索引 = `specs/index.md`」澄清；该职责句与 Delta 写入 `knowledge-management.md` §5.2 的行措辞一致（同一规则一个来源、两处登记时逐字对齐）。
- 新 §7.3 标题定为「共享条目的退役与删除」，供 Delta §9.1 指针与 overview.md 速查节引用。

#### 4.2.3 数据模型

不适用。无 Schema、无机器字段变更；`--knowledge-impact` 机器参数不变。

#### 4.2.4 并发模型

不适用。单 worktree 串行实施；无并发写同一文件的第二执行方（`workflow-code-review/SKILL.md` 的未提交改动属 main 工作区，不在本 worktree）。

#### 4.2.5 错误处理

- 实施前重读目标文件现文（2054 风险表先例）：与 design 描述冲突时按知识合同报告，更新本 design 后再动手。
- lint/pytest 失败时回对应任务修复复跑，不放宽校验。

### 4.3 核心逻辑实现

| 文件 | 操作 | 落点 |
| --- | --- | --- |
| `skills/project-knowledge/SKILL.md` | 修改 | §2 树加 `research.md` 行；§3.4 补职责与澄清；新增 §7.3 |
| `skills/bp-domain-modeling/SKILL.md` | 修改 | 「记录边界」加 rules.md 判据一句 |
| `skills/bp-domain-modeling/reference/glossary-format.md` | 修改 | 「结构规则」加分节-目录映射登记一条 |
| `openspec/changes/2059-.../specs/backend/engineering/tech/knowledge-management.md` | 新建 | MODIFIED Delta 三处（§4 树、§5.2 职责、§9.1 指针「§5、§7.1」→「§5、§7.1、§7.3」） |
| `openspec/specs/backend/framework/knowledge-management/overview.md` | 修改 | 速查节三处缺口标「已由 change 2059 补全」+ §7.3 摘要；`source_ref` 归档时更新为实施后 HEAD |
| `docs/framework-features-status-and-comparison.md` | 修改 | §4.6 知识管理 bullet 补退役语义一条 |

**退役标记法（§7.3 的内容裁决，Task 1 照此措辞）**

原则：状态标记替代物理删除，正文保留为历史证据（与「已验证故障是证据」的既有定位一致）。

| 位置 | 直写路径作废写法 | 索引义务 |
| --- | --- | --- |
| `glossary.md` 条目 | 行尾追加 `_已废弃（YYYY-MM-DD，原因或替代条目）_`，不删行 | 同轮检查 `business/index.md` 与引用方 |
| `rules.md` / `flows.md` / `overview.md` 条目 | 条目前加状态行：`**状态**：已废弃（YYYY-MM-DD，原因；替代：<路径或「无」>）` | 同上 |
| `issues/<issue>.md` | 头部状态行标注已失效/已被修复版本取代，正文不动 | 同步 `issues/index.md` |
| `custom/` | 沿用 §6.2 人工确认门 + 状态标注；`decisions.md` 条目用 adr-format Status 枚举（`deprecated`/`superseded by <编号>`） | 同上 |

- Change 路径：删除走 Delta `REMOVED`（既有），无新规则，仅引用。
- 硬边界：自动流程禁止物理删除任何知识文件；物理删除仅限用户明确授权，授权不外推。
- 衔接：§4 冲突报告的「下一步」处置出口扩展出「标记废弃」；§6.2「更新内容、适用范围或状态」落为上表操作。

**定位链补全（§3.4 与写入方的内容裁决）**

1. `business/index.md` 职责：登记业务域清单——每个 `<domain>/` 目录一行（名称 + 一句范围 + 指向 `overview.md`），及 glossary 分节名与 domain 目录名的映射；新增、改名或退役 domain 时同轮更新。小项目不建空层级：`specs/index.md` 直接链接 glossary 与各条目，映射写在对应条目旁。
2. glossary 分节-目录映射：分节名与 `<domain>/` 目录名不必同词（如「订购上下文」↔ `ordering/`），映射必须登记在 `business/index.md`（小项目在 `specs/index.md`）；未登记视为定位断链，创建分节时同轮登记。
3. rules.md 判据：只收可证伪的不变量——给定具体场景能客观判定成立或违反；倾向性描述归 `overview.md`、实现约定归 `custom/`。一句为限，不给格式模板（保持反模板哲学）。

### 4.4 方案优劣分析

- 优点：不新增机制与机器门禁，改动面小且全部落在既有权威文件；章节号稳定，外部引用零破坏。
- 代价：退役标记靠模型自觉执行，无机器校验（与 2054 风险表第 3 条同一立场：执行率低再立 change 加校验）；`business/index.md` 登记义务同样无 lint。

## 5. 备选方案

- **备选 A（否决）**：在 `knowledge-management.md` 直接改写并同步 SKILL.md——违反「操作合同权威在 SKILL.md」的既有主从，制造双事实源。
- **备选 B（否决）**：为退役立机器门禁（如 lint 检查废弃标记格式）——首版无真实执行数据，属过度设计；契约已声明「积累真实问题数据后再校准」。
- **备选 C（否决）**：重排 SKILL.md 章节把退役并入 §7.2——破坏外部 §x.x 锚定引用，收益为零。

## 6. 业界调研

不适用。本 Change 是内部合同补全，无外部方案引入；机制来源（ADR Status、证据等级）已在既有文件内。

## 7. 测试计划

1. 定向静态校验：`python skills/workflow-code-generation/scripts/lint_spec.py`（proposal `--phase code`、design `--phase design-code`）、`python skills/workflow-code-generation/scripts/lint_task_deps.py <tasks.md> --governance-profile tooling`、`python scripts/lint_skill_graph.py`、三个技能文件过 `quick_validate.py`。
2. 定向 pytest：`scripts/test_skill_slimming_contracts.py`、`scripts/test_profile_contracts.py`（断言合同文本时同步更新断言并记录）。
3. 结构核验：`git diff --check`；逐文件 diff 无越界；`grep` 验证 `research.md`、`business/index.md`、`### 7.3`、§8-§10 标题在位；`grep -rn "SKILL.md:" openspec/specs/` 抽查无行号锚定被破坏。
4. 全量：`workflow-verification` 的 `verify.py`（含 pytest 门槛与 Spec Drift）。
5. 独立 Review：standard 档综合 Review，无未解决 P0/P1 方可交付。
6. md-zh 自检：全部新增中文段落（中英文空格、全角标点、专有名词大小写）。

## 8. 可观测性与运维

不适用（无代码、无运行时行为）。运维影响仅一句：归档时按既有 §7.2 门禁合并 Delta，`overview.md` 的 `source_ref` 随归档更新。

## 9. 参考资料（design）

- `skills/bp-domain-modeling/reference/adr-format.md` — Status 枚举（`deprecated`/`superseded by`）来源。
- `openspec/changes/2054-research-note-persistence/` — Delta 格式与「文本类 Change 敏捷实施」先例。
- `openspec/changes/2057-task-agent-isolation/`、`openspec/changes/2058-self-refinement-retro/` — 行为合同直接维护在技能文档的先例。
