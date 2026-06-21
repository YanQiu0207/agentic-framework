# 框架对比：OpenSpec × workflow-*

> 对照对象：官方 OpenSpec 机制（见 [01-openspec-core.md](01-openspec-core.md)）与本框架 `workflow-*` 工作流的当前实现。
> OpenSpec 侧附来源 URL；`workflow-*` 侧以 `file:line` 标注，可直接跳转核对。
> 每条「缺失」候选都经过对抗性核验（尽力证伪），判定列为 ✅ 成立 / ⚠️ 方向成立但有降级。

## 1. 定位差异

| 维度 | OpenSpec | `workflow-*` |
| --- | --- | --- |
| 重心 | 规范层（spec as living source of truth） | 执行层（澄清 → 设计 → 编码 → 评审 → 验证） |
| 核心产物 | `specs/` 持续演进的系统真相 + `changes/` 增量 | 单功能一份 `spec.md`（10 章设计文档）+ `tasks.md` |
| 组织方式 | 按 capability（系统能做什么） | 按 `<module>/<feature>`（变更产物） |
| 归档 | delta 合并回 `specs/`（内容沉淀） | 翻状态字段为 `Archived`，文件原地不动（`skills/project-knowledge/SKILL.md:48`） |
| 工具化 | `validate`/`list`/`show`/`view` CLI | 仅 `verify.py` 代码门禁，不碰 spec 结构 |
| 哲学 | fluid，可随时改任意 artifact，无门禁 | 刚性顺序门禁（强制 4.1 → 4.2 → 4.3、逐 task 停等批准） |

结论：缺的不是某个步骤，而是 OpenSpec 的**「知识积累闭环」整层**。

## 2. 核心缺失：常青规范库 + delta + 归档合并

这是**一件事的三个面**——OpenSpec 把 `specs/`（真相）与 `changes/`（增量）二分，并在归档时缝合；`workflow-*` 这条链路完全没有。

| 维度 | OpenSpec | `workflow-*` 现状 | 判定 |
| --- | --- | --- | --- |
| **delta 语义** | 变更用 `## ADDED / MODIFIED / REMOVED Requirements` 表达增量（concepts.md），校验器强校验该结构（validator.ts） | 每个 feature 写一份**全新自包含** `spec.md`，3.1/3.2 为自由 bullet，零 delta（`skills/workflow-requirements-clarification/reference/spec_template.md:22`） | ✅ 成立（**高**） |
| **归档即合并** | archive 自动把 delta 并回 `specs/`（cli.md "Merges delta specs into openspec/specs/"） | 归档只改状态字段、文件原地不动不合并（`skills/project-knowledge/SKILL.md:48`） | ⚠️ 方向成立 |
| **中央真相库** | `specs/` 按 capability 组织、独立于 changes、可机器读取「某能力当前长什么样」（concepts.md / openspec.dev） | 过期 spec 散落在 `docs/design-docs/<module>/<feature>/`，按变更而非能力组织 | ⚠️ 方向成立 |

> **诚实降级（对抗核验结论）**：`workflow-*` 并非「零沉淀」。`project-knowledge` 规定，当某 spec 转 `Approved` 且涉及架构变更时，**必须人工**同步更新常青文档 `docs/architecture/overview.md`（`skills/project-knowledge/SKILL.md:60`），这是一个更弱的「现状真相」载体。但它是**散文式、按子系统而非 capability 组织、纯手工、与设计流脱钩**（明确「不由设计工作流自动创建」，`skills/project-knowledge/SKILL.md:111`），既无 Requirement/Scenario 结构，也无 delta 自动合并与 CLI 校验。
>
> 所以差距的准确表述是：缺的是「**结构化 + 自动合并 + 工具化 + 与工作流强绑定**」，而非「有无现状文档」。这也正是 `architecture/` 容易和代码/分散的功能 spec 漂移的根因。

## 3. 支撑层缺失

| 缺失项 | OpenSpec | `workflow-*` 现状 | 判定 |
| --- | --- | --- | --- |
| **可校验的需求格式** | 每条 Requirement 至少一个 `#### Scenario:`（Given/When/Then），由 validate 分级强制 | 需求是 `3.1/3.2` 自由 bullet（模板原文「用 bullet points 列出」，`spec_template.md:24`），无场景结构、无任何结构校验 | ✅ 成立 |
| **spec 工具链** | `validate --strict` / `list` / `show` / `status` / `view`，对规范做确定性校验与浏览 | 唯一脚本 `verify.py` 是**代码质量门禁**（exit_code / forbid_pattern / count，`skills/workflow-verification/SKILL.md:32`），不解析 spec 结构 | ⚠️ 方向成立 |
| **多工具指令分发** | `init` / `update` CLI 为 25+ 工具生成 slash command + 托管 `AGENTS.md` | 靠 README 手工 `cp -R agents skills commands ~/.claude/`（`README.md:24`），无再生成机制、无统一 hand-off | ⚠️ 方向成立 |

## 4. 哲学差异（是取舍，不是缺陷）

OpenSpec 明确主张「update any artifact anytime, no rigid phase gates」；`workflow-*` 恰好相反——`system-design` 强制严格顺序约束（`skills/workflow-system-design/SKILL.md:214`），`code-generation` 逐 task 停下等用户批准。

**这很可能正是中意 `workflow-*` 的原因**，别当缺点改掉。两者是对「灵活 vs 严谨」的不同下注，不存在谁对谁错。

## 5. 关键事实纠正（对抗核验中推翻的误记）

为避免后续以讹传讹，记录三处被核实推翻的常见说法：

1. **OpenSpec 没有 `diff` 命令**：`docs/cli.md` 两次完整命令列举均无 `diff`，README/官网亦无。
2. **项目级文件是 `config.yaml` 不是 `project.md`**：所抓五个官方来源均无 `project.md`；项目配置由可选的 `config.yaml` 承载，change 级另有可选 `.openspec.yaml`。
3. **场景是 Given/When/Then 且校验分级**：不是纯 WHEN/THEN 二段式；且「强制至少一个场景」非一刀切——delta 中 ADDED/MODIFIED 缺场景是硬 ERROR，主 spec 缺场景仅 WARNING（`--strict` 下才失败）；validator 仅以 `####` 标题存在性判定「有无场景」。

来源：[docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)、[validator.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/validation/validator.ts)、[docs/concepts.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md)。

## 6. workflow-* 反而更强的点

差异是非对称的——OpenSpec 的赌注全押在规范层，以下这些 OpenSpec 几乎没有：

- **设计深度**：10 章重型 `spec.md` + 苏格拉底式逐节 `system-design`（OpenSpec 的 spec 是轻量需求清单）。
- **多 Agent 对抗式 code review**：5 reviewer + critic + Judge（`skills/workflow-code-review/SKILL.md:12`）；OpenSpec 无评审编排。
- **客观验证门禁**：`verify.py` 基线对比、只追新增违规（`skills/workflow-verification/SKILL.md:32`）。
- **编码规范体系**：`std-*` / `bp-*` 按需加载。

> 一句话：`workflow-*` 强在「把一次变更做对做扎实」，OpenSpec 强在「让规范长期保鲜可查」。两者其实互补，补齐方向见 [03-roadmap.md](03-roadmap.md)。

## 7. 再认识：第 2 节的「缺失」对 workflow-* 是缺陷吗？

第 2、3 节的**事实**成立（OpenSpec 确有中央规范库/delta/归档合并，`workflow-*` 确无）。但「这是不是 `workflow-*` 该补的洞」需要分层判断——经讨论，结论有重要修正：

- **`workflow-*` 信奉「代码 = 现状的唯一真相」**：它的设计工作流每次变更都强制 AI 重新分析代码提取现状（「信息可以从 codebase 获取，AI 必须自己调研」，`skills/workflow-requirements-clarification/SKILL.md:31`；「现有实现、接口等 AI 必须自己读代码获取」，`skills/workflow-system-design/SKILL.md:208`）。
- **所以「不维护现状规范库」是自洽选择，不是缺陷**：硬补一个 OpenSpec 式行为库，会和代码争真相、漂移、腐烂——这正是 `workflow-*` 当初不做归档的合理性。OpenSpec 能让 `specs/` 不漂移，靠的是「行为变更必经 `changes/` + validate/CI 强制」，`workflow-*` 没有这套纪律。
- **真正的缺口收窄为 intent**：代码是「现状（怎么做）」的真相，但**读不出**「intent（为什么/约束/放弃的方案/权衡）」。后者不沉淀就永久丢失——这才是 `workflow-*` 唯一该补的洞。

**因此**：第 2 节表格里 G2/G3/G6 标的「成立 / 高」，应理解为「相对 OpenSpec 的**能力差**」，而非「`workflow-*` 必须照搬的**缺陷**」。真正必补的是 **intent 沉淀**（ADR + 交付前沉淀检查），而非行为规范库。补法见 [03-roadmap.md](03-roadmap.md) P0。
