# 实施任务清单

> 由 proposal.md / design.md / Delta 生成
> 任务总数：6
> 核心原则：先立约定后接线——先定义 research.md 与「实现参考」的统一写法（Task 1），再按数据流方向逐点接线（落盘两处 → 消费两处），最后同步长期知识并全量核验

## 依赖关系总览

Task 1 (约定定义：task_planning_guide 模板与自检)
  ↓
Task 2 (需求澄清落盘) ─┬─ 依赖 Task 1（落盘约定写法已在 Task 1 定稿）
Task 3 (系统设计落盘) ─┘
  ↓
Task 4 (编码入口通读) ← 依赖 Task 1（引用「实现参考」字段名）
Task 5 (knowledge-management Delta + 索引) ← 依赖 Task 1
Task 6 (交叉核验与全文自检) ← 依赖 Task 2, 3, 4, 5

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 修改 | Task 1 | 第二步信息项 + 模板字段 + 质量自检行 |
| `skills/workflow-requirements-clarification/SKILL.md` | 修改 | Task 2 | Step 1 落盘段 |
| `skills/workflow-system-design/SKILL.md` | 修改 | Task 3 | Step 0 落盘项 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 4 | 步骤 2 通读清单加 research.md |
| `openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md` | 新建 | Task 5 | MODIFIED Delta |
| `openspec/index.md` | 修改 | Task 5 | 知识同步索引更新列 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| 无代码接口 | 无 | 无 | 无 |

### 构建系统变更

- 无（全部为 Markdown 文本改动）

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | design.md §4.3 的行号锚定基于 HEAD `1d7fb1d`，main 已前进到 `fe418a8` 并已合入本分支 | Task 2, 3 | 已 merge main（`0ee6fbc`）并重新核实锚点：目标段落与 2053/deep-module 改动不重叠，按合并后文本锚定 |
| 2 | `knowledge-management.md` 长期文件在 main 上有 +8 行改动（`git log` 显示 2053 期间改过 §9.1 附近） | Task 5 | Delta 只在 §5.5 加一行，锚定合并后的最新文本，实施前重读目标文件 |
| 3 | 落盘与字段填写无机器校验，依赖模型执行 | 全部 | design.md §4.4 已接受；后续若执行率低再立 change 加校验 |

## 任务列表

### 任务 1：[x] 在 task_planning_guide 定义「实现参考」字段与 research.md 提取职责
- 状态：完成    （合法值：未开始 / 进行中 / 完成 / 需人工 / 阻塞；执行期由 code-generation 维护，是续跑的真相源）
- 文件：`skills/workflow-code-generation/reference/task_planning_guide.md`（修改）
- depends_on: []
- review_profile: lightweight
- 文档映射：design.md §4.2.3、§4.3 第 4 点
- 说明：约定统一在此定稿，后续任务只引用。三处改动：①第二步「本步骤需要获取的信息」加第 6 项（从 research.md 提取实现参考要点）；②原则 7 字段清单加可选字段 `实现参考` 并给出填写规则（接口级要点 + 章节指针，禁止贴源码，无则省略）；③模板正文任务字段区加 `实现参考` 示例行；④质量自检表加一行（有 research.md 时命中复用的任务已填实现参考或写明省略理由）
- context_files:
  - `skills/workflow-code-generation/reference/task_planning_guide.md` — 唯一修改目标，全部改动落在此文件
  - `skills/workflow-code-generation/SKILL.md:100` — 引用本 guide 的步骤 3，确认不与本任务字段冲突
- verification:
  - [x] `grep -n "实现参考" skills/workflow-code-generation/reference/task_planning_guide.md` 在「第二步信息项」「原则 7」「模板正文」「质量自检表」四处全部命中
  - [x] `grep -n "research.md" skills/workflow-code-generation/reference/task_planning_guide.md` 至少命中第二步信息项与质量自检表两处
  - [x] 模板中 `实现参考` 标注为可选（有「无则省略」语义）
- artifacts:
  - `skills/workflow-code-generation/reference/task_planning_guide.md`（修改后版本）
- 子任务：
  - [x] 1.1: 第二步信息项加第 6 项
  - [x] 1.2: 原则 7 加字段定义与填写规则
  - [x] 1.3: 模板正文加示例行
  - [x] 1.4: 质量自检表加检查行

### 任务 2：[x] 需求澄清 Step 1 接入 research.md 落盘
- 状态：完成
- 文件：`skills/workflow-requirements-clarification/SKILL.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §4.3 第 1 点、§4.2.2
- 说明：在 Step 1「实时更新 Proposal」（约 `SKILL.md:148`）之后新增一段：subagent 返回并经用户确认后，将报告按六段结构追加写入 `openspec/changes/<ticket>-<change-name>/research.md`；多次调研追加新章节不覆盖；proposal.md `1.2 现状分析` 写摘要并指向 research.md。同时确认强制规则与反模式无需新增条目（落盘是现有「实时更新」模式的扩展，不立新规）
- context_files:
  - `skills/workflow-requirements-clarification/SKILL.md:118-148` — Step 1 全段，落盘段插入点
  - `skills/workflow-code-generation/reference/task_planning_guide.md` — Task 1 定稿的字段写法，保持措辞一致
- verification:
  - [x] `grep -n "research.md" skills/workflow-requirements-clarification/SKILL.md` 命中新增段落
  - [x] `git diff` 显示仅 Step 1 区域新增，无其他段落变动
  - [x] 路径写法与 design.md §4.2.2 一致（`openspec/changes/<ticket>-<change-name>/research.md`）
- artifacts:
  - `skills/workflow-requirements-clarification/SKILL.md`（修改后版本）

### 任务 3：[x] 系统设计 Step 0 接入 research.md 落盘
- 状态：完成
- 文件：`skills/workflow-system-design/SKILL.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §4.3 第 2 点、§4.2.2
- 说明：在 Step 0「AI 操作」列表第 4 项（约 `SKILL.md:163`）与第 5 项之间不动，改为在第 5 项「生成摘要向用户确认」后追加第 6 项：用户确认后调用方将报告追加写入本 Change 的 research.md；多次调研追加不覆盖。措辞与 Task 2 的落盘段保持同一约定
- context_files:
  - `skills/workflow-system-design/SKILL.md:153-185` — Step 0 全段
  - `skills/workflow-requirements-clarification/SKILL.md` — Task 2 产物，措辞对齐来源
- verification:
  - [x] `grep -n "research.md" skills/workflow-system-design/SKILL.md` 命中新增项
  - [x] `git diff` 显示仅 Step 0 区域新增一行，无其他段落变动
  - [x] 两处落盘段的关键词一致（追加式、六段结构、用户确认后）
- artifacts:
  - `skills/workflow-system-design/SKILL.md`（修改后版本）

### 任务 4：[x] 编码入口步骤 2 加入 research.md 强制通读
- 状态：完成
- 文件：`skills/workflow-code-generation/SKILL.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §4.3 第 3 点
- 说明：在步骤 2「同时读取 `openspec/index.md`…」段（约 `SKILL.md:91`）补一句：Change 目录存在 `research.md` 时将其一并纳入强制通读，实现前按任务「实现参考」字段定位已有实现，避免重造现有代码已覆盖的方案。注意与下一段「回到代码核实现状」的顺序关系：research.md 是辅助理解，代码仍是事实源，冲突照既有规则报告
- context_files:
  - `skills/workflow-code-generation/SKILL.md:82-96` — 步骤 2 全段
  - `skills/workflow-code-generation/reference/task_planning_guide.md` — Task 1 定稿的字段名
- verification:
  - [x] `grep -n "research.md" skills/workflow-code-generation/SKILL.md` 命中新增句
  - [x] `git diff` 显示仅步骤 2 段落变动
  - [x] 新增句包含「存在时」条件（research.md 缺失不阻塞轻量与小型 Change）
- artifacts:
  - `skills/workflow-code-generation/SKILL.md`（修改后版本）

### 任务 5：[x] knowledge-management Delta 与索引同步
- 状态：完成
- 文件：`openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md`（新建）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §4.3 第 5 点、proposal.md §4
- 说明：创建 MODIFIED Delta（镜像长期 specs 相对路径）：在 §5.5 `changes/` 职责列表加一行 `research.md：本 Change 的代码调研结论（中间产物，追加式，随 Change 归档）`，并在 §7.2 编码实现路由行或紧邻处补 research.md 读取时机。长期文件本体不在本任务修改（归档时按 Delta 合并）。tasks.md「知识同步」表填 Delta 动作与状态，`openspec/index.md` 按既有格式登记本 Change
- context_files:
  - `openspec/specs/backend/engineering/tech/knowledge-management.md:213-222` — §5.5 职责列表
  - `openspec/specs/backend/engineering/tech/knowledge-management.md:268-278` — §7.2 读取路由表
  - `openspec/changes/2053-decision-interview-domain-modeling/specs/` — 既有 Delta 的格式参照（main 上已归档，路径在 archive 下）
  - `openspec/index.md` — 活跃 Change 登记
- verification:
  - [x] Delta 文件存在且相对路径镜像长期 specs：`ls openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md`
  - [x] `python scripts/lint_spec.py openspec/changes/2054-research-note-persistence/specs 2>&1` 无 ERROR（或确认该脚本按目录/文件用法无此校验时，记录实际执行的校验命令与结果）
  - [x] tasks.md 知识同步表已填写（非 Pending）
  - [x] `openspec/index.md` 已登记本 Change
- artifacts:
  - `openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md`
  - `openspec/index.md`（修改后版本）

### 任务 6：[x] 交叉核验、lint 与全量自检
- 状态：完成
- 文件：无新增修改（只读核验；发现问题时回到对应任务修复后重跑本任务）
- depends_on: Task 2, Task 3, Task 4, Task 5
- review_profile: standard
- 文档映射：design.md §7 测试计划、proposal.md §3.3
- 说明：①`grep -n "research.md"` 四个 skill 文件全部命中且路径写法一致；②`task_planning_guide.md` 三处「实现参考」描述自洽；③`python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2054-research-note-persistence/tasks.md` 通过；④五个文件逐个 `git diff` 核对无越界改动；⑤新增中文段落按 md-zh 规则（中英文空格、全角标点、专有名词大小写）自查；⑥与 design.md §4.3 逐点比对，全部接线点已覆盖
- context_files:
  - `skills/workflow-requirements-clarification/SKILL.md`
  - `skills/workflow-system-design/SKILL.md`
  - `skills/workflow-code-generation/SKILL.md`
  - `skills/workflow-code-generation/reference/task_planning_guide.md`
  - `openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md`
- verification:
  - [x] lint_task_deps.py 本 tasks.md 通过（含 --state-consistency 在任务全为终态时）
  - [x] grep 交叉核验全部命中
  - [x] 逐文件 git diff 无本 Change 之外的改动
  - [x] md-zh 自检通过
- artifacts:
  - 本任务勾选记录与核验输出（写在任务勾选项与最终报告）

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| design.md §4.2.2（research.md 约定） | Task 2, 3 | 两处落盘接线 |
| design.md §4.2.3（实现参考字段） | Task 1 | 字段定义唯一来源 |
| design.md §4.3 第 1 点 | Task 2 | 需求澄清接线 |
| design.md §4.3 第 2 点 | Task 3 | 系统设计接线 |
| design.md §4.3 第 3 点 | Task 4 | 编码入口接线 |
| design.md §4.3 第 4 点 | Task 1 | task_planning_guide 接线 |
| design.md §4.3 第 5 点 | Task 5 | 长期知识 Delta |
| design.md §7 测试计划 | Task 6 | 核验收口 |
| proposal.md §3.3 验收标准 | Task 6 | 逐条核对 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/engineering/tech/knowledge-management.md` | `openspec/specs/backend/engineering/tech/knowledge-management.md` | MODIFIED | Delta 已创建（Synced 于归档前核对） | 已登记 `openspec/index.md` 近期变更 |

## 知识冲突

- 结论：待核对。Task 5 实施前重读长期文件，发现与 design.md 描述冲突时记录双方证据并标记 `Resolved`。

## 实际 Diff 核对

- 核对状态：PASS（2026-11-27，worktree 分支 `2054-research-note-persist`）。
- 核对命令与结论：
  - `git diff --stat`：6 文件 +21/−12，全部落在本 Change 声明的目标文件内，无越界改动。
  - `grep -n "research.md"` 四个 skill 文件 7 处命中，路径写法一致（`openspec/changes/<ticket>-<change-name>/research.md` 与「存在时」条件齐全）。
  - `python skills/workflow-code-generation/scripts/lint_task_deps.py <tasks.md> --governance-profile tooling`：tasks=6 | errors=0 | warnings=0。
  - `lint_spec.py` proposal（--phase code）与 design（--phase design-code）：均 errors=0。
  - md-zh 排版抽查：新增行中英文空格、全角标点无违规。
