# Design: 变更调研结论落盘与实现参考传递

**作者**: YanQi
**日期**: 2026-11-27
**状态**: Draft

> **编号说明**：design.md 保留历史局部编号 4～9，可与 proposal.md 的编号重叠，不重新编号。跨文件引用必须带文件名，例如「design.md §4.1」。

---

## 4. 设计方案

### 4.1 方案概览

不改任何脚本与门禁，只改 5 个 Markdown 文件的文本，把两条新约定接进现有工作流：

1. **调研落盘约定**：需求澄清与系统设计阶段调用 `codebase-researcher` 后，调用方把报告写入本 Change 的 `openspec/changes/<ticket>-<change-name>/research.md`，追加式，按调研问题组织，保留 `file:line` 引用。
2. **实现参考传递**：任务拆解时从 research.md 提取结论，为每个任务填可选字段 `实现参考`；编码入口的强制通读清单加入「`research.md`（存在时）」，让新会话实现前先读调研结论。

数据流：

```text
需求澄清 Step 1 ─┐
                 ├─→ research.md（追加）←─ 系统设计 Step 0
任务拆解 Step 2 ─┘        │
        │                 │
        ├─ 提取 → tasks.md 每任务「实现参考」字段（指针）
        └─ 编码入口步骤 2 强制通读 research.md（存在时）
```

与既有机制的关系：`codebase-researcher` 第五步架构快照（长期 specs 写入）照旧独立运作，research.md 是 change 级中间产物，两者互不替代、互不阻塞。

### 4.2 组件设计

#### 4.2.1 涉及文件与改动性质

| 文件 | 改动性质 |
| --- | --- |
| `skills/workflow-requirements-clarification/SKILL.md` | Step 1 增加落盘动作一段 |
| `skills/workflow-system-design/SKILL.md` | Step 0 增加落盘动作一段 |
| `skills/workflow-code-generation/SKILL.md` | 步骤 2 通读清单加一行 |
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 第二步说明 + 任务模板字段 + 质量自检表 |
| `openspec/specs/backend/engineering/tech/knowledge-management.md` | §5.5 change 目录职责加 research.md 一行（经 Delta） |

#### 4.2.2 research.md 文件约定

- **位置**：`openspec/changes/<ticket>-<change-name>/research.md`，与 proposal.md 同目录。
- **写入者**：调用方 skill（需求澄清、系统设计的主会话），不是 `codebase-researcher` 本身。理由：researcher 的「保持只读」不变式不被破坏；并行启动多个调研 subagent 时不会产生写竞争；与需求阶段既有「实时更新 Proposal」的调用方写盘模式一致。
- **写入时机**：每次 subagent 返回报告、用户确认调研摘要后写入；同一文件多次调研追加新章节，不覆盖旧章节。
- **内容组织**：沿用 `agents/codebase-researcher.md:42-54` 的报告结构（摘要、关键发现、模块分析、依赖图、相关测试、待明确问题），一个调研问题一个二级标题。
- **引用纪律**：保留报告中的 `file:line` 引用；事实与推断分开标注；未找到的搜索也要记录。
- **与 specs 的边界**：research.md 是 change 级中间产物，随 Change 归档；它不进入 `openspec/specs/`，不触发 project-knowledge 确认门，不参与 `lint_task_deps.py` 校验。若某结论值得长期沉淀，仍走 researcher 第五步的架构快照询问，两不延误。
- **缺失合法**：小型 Change（如需求阶段无 subagent 调研）可以没有 research.md，所有下游消费都以「存在时」为条件。

#### 4.2.3 任务模板「实现参考」字段

- **字段形态**：任务半结构化字段区的可选行，形如 `- 实现参考: research.md §<N>（要点：复用 <X> / 基于 <Y> 扩展）`。
- **填写规则**：拆解第二步调研时，把「本任务必须复用或扩展的已有实现」从 research.md 提炼为一句要点 + 章节指针；接口级描述优先（模块、名称、签名、行为），不粘贴源码（依据 RepoReuse 的 interface memory 结论：接口清单使复用翻倍，源码粘贴无增益）。
- **省略合法**：任务确无既有实现可参考时省略，不写占位。

### 4.3 核心逻辑实现

四个接线点的具体文本位置（锚定到当前 HEAD `1d7fb1d` 的行号）：

1. **`workflow-requirements-clarification/SKILL.md`**：Step 1「实时更新 Proposal」段后新增一段：subagent 返回并经用户确认后，将报告写入 `openspec/changes/<ticket>-<change-name>/research.md`（追加式）；proposal.md `1.2 现状分析` 写摘要并指向 research.md。
2. **`workflow-system-design/SKILL.md`**：Step 0「AI 操作」列表第 4 项后追加第 5 项：调研结论经用户确认后追加写入 research.md；多次调研追加不覆盖。
3. **`workflow-code-generation/SKILL.md`** 步骤 2：在「同时读取 `openspec/index.md`…」段补一句：Change 目录存在 `research.md` 时将其一并纳入强制通读，实现前按任务的「实现参考」字段定位已有实现。
4. **`task_planning_guide.md`**：
   - 第二步「本步骤需要获取的信息」加第 6 项：从 research.md 提取每个任务的实现参考要点。
   - 任务模板（原则 7 字段清单与模板正文）加可选字段 `实现参考`。
   - 质量自检表加一行：有 research.md 时，命中复用的任务是否已填实现参考或写明省略理由（检查项，不进脚本）。
5. **knowledge-management.md（经 Delta）**：§5.5 `changes/` 职责列表加一行 `research.md：本 Change 的代码调研结论（中间产物，随 Change 归档）`；§8 写入路由表「单次需求、设计和任务」行不变（research.md 属于 change 目录，无需新行）。

**改动边界**：需求澄清与系统设计两个 SKILL.md 在主工作区有 2053 的未提交改动（摘要确认复用、决策依赖分组等），本 Change 的锚点以 HEAD 版本为准，改动段落（Step 1 / Step 0 的调研落盘段）与 2053 改动段落在文本上不重叠；合并回 main 时若同段落冲突，两边意图都保留。

### 4.4 方案优劣分析

**优点**：

- 全文本改动，无脚本、无门禁、无 schema 变更，回归面为零。
- 与既有写盘模式（实时更新 Proposal）和只读边界（researcher）一致，不引入新机制。
- 直接对应 RepoReuse 实证的「接口清单」形态，不引入被证明无效的「贴源码」形态。

**缺点 / 风险**：

- 依赖模型自觉执行落盘，无机器校验（与「实时更新 Proposal」同级，接受；本轮刻意不进门禁，见 §5）。
- research.md 与后续代码改动可能漂移；缓解：它是 change 级中间产物，生命周期与 Change 一致，归档后即为历史证据，无长期漂移问题。
- 追加式文件可能变长；缓解：按调研问题分节、实现参考只留指针，编码会话按需读节。

## 5. 备选方案

1. **给任务加独立的 `reuse_ref` 结构化字段**：被否，与「实现参考」相比只是形态差异，但拆出了新字段语义；合入「实现参考」一个字段承载要点 + 指针更简单。
2. **由 `codebase-researcher` 自己写 research.md**：被否，破坏「保持只读」不变式（`agents/codebase-researcher.md:91`），且并行调研会产生写竞争。
3. **落盘进长期 specs（放宽第五步询问阈值）**：被否，「本次实现参考什么」是 change 级信息，进长期知识会加重 specs 维护负担并触发确认门；归档后的 research.md 已可供历史 Change 检索。
4. **机器校验「实现参考」字段**（进 `lint_task_deps.py`）：被否，本轮目标是打通信息流，先观察执行率；若后续发现模型经常漏填，再立 change 加校验。

## 6. 业界调研

- **RepoReuse**（arXiv:2609.35357，2026-09-28）：3000 轮实测，agent 到第 5 轮 50.8% 任务链留下重复实现而 pass rate 不动；interface memory（需求中列已有函数的模块/名称/签名/行为并鼓励复用）使 self reuse 30.0%→67.8%，source memory（贴完整源码）29.2% 无增益。直接支撑「实现参考」字段的接口级指针形态。附带发现：有清单后 agent 对仓库的探索变少，清单未覆盖的代码更少被复用，故字段要求写「去哪找」（路径指针）。
- **Anthropic: Effective context engineering for AI agents**（2025-09-29）：structured note-taking / agentic memory——agent 把关键发现持久化到上下文窗口外的文件并按需拉回，Claude Code 的 todo list 与 NOTES.md 是同型实践。
- **Anthropic: Effective harnesses for long-running agents**（2025-11-26）：每个新会话开头强制读 progress 文件与 git log 恢复状态，对应「新会话执行 tasks.md 前先读 research.md」的设计。
- **mattpocock/skills `research`**：调研结果必须是仓库内 Markdown 文件、逐条主张引用一级来源、保存位置遵循仓库已有约定。本设计沿用三条不变式，落盘位置采用本仓库已有约定（change 目录），不安装外部技能。

## 7. 测试计划

本 Change 全部是 Markdown 文本，测试为文本核验：

1. 逐文件核对：五个目标文件的新增段落与 §4.3 描述一致，未触碰无关段落（对照 git diff 逐行核对）。
2. 交叉引用一致性：`grep -n "research.md"` 在四个 skill 文件的命中处，路径写法与 §4.2.2 约定一致。
3. 任务模板自洽：`task_planning_guide.md` 内模板、原则 7 字段清单、质量自检表三处对「实现参考」的描述一致。
4. Delta 校验：`python scripts/lint_spec.py`（如适用）对 Delta 目录通过；Delta 相对路径可映射到长期 specs。
5. 知识同步：tasks.md 知识同步表记录 Delta 与索引更新状态。
6. md-zh 排版自检：新增中文段落按中英文空格、全角标点规则自查。

## 8. 可观测性与运维

不涉及运行时系统。运维面即「归档后 research.md 随 Change 进入 `changes/archive/<ticket>-YYYY-MM-DD-<name>/`」，按既有归档机制处理，无新增运维动作。

## 9. 参考资料（design）

- RepoReuse: Do Coding Agents Reuse Existing Code or Reinvent the Wheel?（arXiv:2609.35357）
- Anthropic: Effective context engineering for AI agents（2025-09）；Effective harnesses for long-running agents（2025-11）
- mattpocock/skills `research` 技能（`.learn-by-gpt/mattpocock-skills/zh-CN/skills/engineering/research/SKILL.md`）
- 本仓库：`agents/codebase-researcher.md`、`openspec/specs/backend/engineering/tech/knowledge-management.md`
