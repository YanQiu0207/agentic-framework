# 实施任务清单

> 由 proposal.md / design.md 生成
> 任务总数：4
> 核心原则：操作规则只在 `project-knowledge/SKILL.md` 写一处，写入方与方案文档引用之；不重排既有章节号

## 依赖关系总览

Task 1 (SKILL.md 三处合同改动：树、§3.4、新 §7.3)
  ↓
Task 2 (写入方 bp-domain-modeling 两处) ← 依赖 Task 1（措辞对齐）
Task 3 (Delta + 状态文档同步) ← 依赖 Task 1（§7.3 编号定稿后更新指针）
Task 4 (定向核验 + 全量 Verify + 独立 Review) ← 依赖 Task 1, 2, 3

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `skills/project-knowledge/SKILL.md` | 修改 | Task 1 | §2 树 + §3.4 职责澄清 + 新 §7.3 |
| `skills/bp-domain-modeling/SKILL.md` | 修改 | Task 2 | rules.md 判据一句 |
| `skills/bp-domain-modeling/reference/glossary-format.md` | 修改 | Task 2 | 分节-目录映射登记一条 |
| `openspec/changes/2059-knowledge-retirement-contracts/specs/backend/engineering/tech/knowledge-management.md` | 新建 | Task 3 | MODIFIED Delta 三处 |
| `openspec/specs/backend/framework/knowledge-management/overview.md` | 修改 | Task 3 | 速查节缺口状态更新 |
| `docs/framework-features-status-and-comparison.md` | 修改 | Task 3 | §4.6 补退役语义 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| 无代码接口 | 无 | 无 | 无 |

### 构建系统变更

- 无（全部为 Markdown 文本改动）

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 新 §7.3 使后续章节行号偏移 | Task 1, 4 | 外部引用均为章节号锚定；Task 4 grep 核验无行号引用 |
| 2 | `test_profile_contracts.py` 断言 SKILL.md 文本 | Task 4 | 先跑定向 pytest，断言命中改动文本时同步更新断言 |
| 3 | worktree 内跑全量 verify.py 需要干净环境 | Task 4 | worktree 为新建干净检出，无本地残留 |

## 任务列表

### 任务 1：[x] project-knowledge/SKILL.md 三处合同改动
- 状态：完成
- 文件：`skills/project-knowledge/SKILL.md`（修改）
- depends_on: []
- review_profile: lightweight
- 文档映射：design.md §2、§3.1、§3.4
- 说明：①§2 Change 目录树在 `tasks.md` 行后补 `research.md` 行（措辞对齐 knowledge-management.md §5.5：调研中间产物、追加式、随 Change 归档）；②§3.4 补 `business/index.md` 职责（域清单 + glossary 分节-目录映射登记 + 增改退役同轮更新）并把「小项目允许根索引直接链接条目」澄清为 `specs/index.md`；③在 §7.2 之后新增「### 7.3 共享条目的退役与删除」：直写路径状态标记表（glossary 行内标注 / rules-flows-overview 状态行 / issues 头部状态行 / custom 沿用 §6.2 + decisions 用 adr-format Status 枚举）、Change 路径指向既有 `REMOVED`、同轮索引与引用方更新义务、自动流程禁物理删除 + 物理删除仅限用户明确授权。§8-§10 编号与内容不动
- context_files:
  - `skills/project-knowledge/SKILL.md` — 唯一修改目标
  - `openspec/changes/2059-knowledge-retirement-contracts/design.md` — §2 标记法表与措辞裁决
  - `openspec/specs/backend/engineering/tech/knowledge-management.md` §5.5 — research.md 措辞来源
- verification:
  - [x] `grep -n "research.md" skills/project-knowledge/SKILL.md` 命中 §2 树（`:41`）
  - [x] `grep -n "business/index.md" skills/project-knowledge/SKILL.md` 命中 §3.4 职责段（`:92-93`）
  - [x] `grep -n "### 7.3" skills/project-knowledge/SKILL.md` 命中（`:229`）；§8/§9/§10 标题行仍在且编号不变（`:246/252/274`）
  - [x] `git diff` 仅上述三处区域变动
- artifacts:
  - `skills/project-knowledge/SKILL.md`（修改后版本）

### 任务 2：[x] bp-domain-modeling 写入方两处小改
- 状态：完成
- 文件：`skills/bp-domain-modeling/SKILL.md`、`skills/bp-domain-modeling/reference/glossary-format.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §3.2、§3.3
- 说明：①SKILL.md「记录边界」加一句：rules.md 只收可证伪的不变量（给定场景能客观判定成立或违反），倾向性描述与实现约定分别归 overview 与 custom；②glossary-format.md「结构规则」加一条：分节名与 `<domain>/` 目录名不必同词，映射登记在 `business/index.md`（小项目在 `specs/index.md`），未登记视为定位断链，创建分节时同轮登记
- context_files:
  - `skills/bp-domain-modeling/SKILL.md` — 记录边界节
  - `skills/bp-domain-modeling/reference/glossary-format.md` — 结构规则节
  - `skills/project-knowledge/SKILL.md` — Task 1 产物，措辞对齐（映射登记位置）
- verification:
  - [x] `grep -n "可证伪" skills/bp-domain-modeling/SKILL.md` 命中
  - [x] `grep -n "business/index.md" skills/bp-domain-modeling/reference/glossary-format.md` 命中且与 Task 1 登记位置措辞一致
  - [x] `git diff` 仅两文件各一处变动
- artifacts:
  - 两个修改后文件

### 任务 3：[x] Delta 与状态文档同步
- 状态：完成
- 文件：`openspec/changes/2059-knowledge-retirement-contracts/specs/backend/engineering/tech/knowledge-management.md`（新建）、`openspec/specs/backend/framework/knowledge-management/overview.md`（修改）、`docs/framework-features-status-and-comparison.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：design.md §3.4、§4 影响表
- 说明：①按 2054 先例写 MODIFIED Delta（镜像长期路径）：§4 树 `<domain>/` 内补 `research.md` 一行；§5.2 列表补 `index.md` 职责一行；§9.1「统一见 `skills/project-knowledge/SKILL.md` §5、§7.1」→「§5、§7.1、§7.3」。状态行标注 Created（归档前核对后 Synced）；②overview.md 速查节：退役缺口、`business/index.md` 缺口、映射缺口从「待 Change 处理」改为「已由 change 2059 补全」并各附一句摘要 + §7.3 指针（`source_ref` 归档时更新为实施后 HEAD）；③features 文档 §4.6 知识管理 bullet 列表补一条退役语义
- context_files:
  - `openspec/changes/2054-research-note-persistence/specs/backend/engineering/tech/knowledge-management.md` — Delta 格式先例
  - `openspec/specs/backend/engineering/tech/knowledge-management.md` — 长期目标文件（只读，实施锚定）
  - `openspec/specs/backend/framework/knowledge-management/overview.md` — 速查节现文
  - `docs/framework-features-status-and-comparison.md` — §4.6
- verification:
  - [x] Delta 文件相对路径镜像长期 specs（`specs/backend/engineering/tech/knowledge-management.md`）
  - [x] `grep -n "research.md" <delta>` 与 `grep -n "index.md" <delta>`（§5.2 段）命中
  - [x] overview.md 速查节三处缺口标记已更新（退役/定位链改为「change 2059 补全」、research.md 差异消除）
  - [x] features 文档 §4.6 新增 bullet 命中「退役」
- artifacts:
  - Delta 文件、两个修改后文档

### 任务 4：[ ] 定向核验、全量 Verify 与独立 Review
- 状态：进行中（定向校验已过，等全量 Verify 与独立 Review）
- 文件：无新增修改（只读核验；发现问题时回到对应任务修复后重跑本任务）
- depends_on: Task 1, Task 2, Task 3
- review_profile: standard
- 文档映射：design.md §6、proposal.md §3.3
- 说明：①`python scripts/lint_skill_graph.py`；②技能文件校验（quick_validate.py 在本仓库不存在，改以 lint_skill_graph + lint_spec + lint_task_deps 覆盖，已如实记录）；③`python skills/workflow-code-generation/scripts/lint_spec.py openspec/changes/2059-knowledge-retirement-contracts/proposal.md --phase code` 与 design.md `--phase design-code`；④`python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2059-knowledge-retirement-contracts/tasks.md --governance-profile tooling`；⑤定向 pytest：`test_skill_slimming_contracts.py`、`test_profile_contracts.py`；⑥`git diff --check` + 逐文件 diff 无越界；⑦md-zh 自检；⑧全量 `verify.py --diff-base 8668968`；⑨standard 档独立综合 Review，无未解决 P0/P1
- context_files:
  - 本 Change 全部产物文件
  - `scripts/lint_spec.py`、`scripts/lint_skill_graph.py` — 校验工具
- verification:
  - [x] ① lint_skill_graph：skills=32 commands=19 agents=8 | errors=0 warnings=0
  - [x] ③ lint_spec：proposal errors=0 warnings=0、design errors=0 warnings=0（design 首版缺 4-9 章与状态不合法，已按模板重写后复跑通过）
  - [x] ④ lint_task_deps：tasks=4 | errors=0 warnings=0 legacy=0
  - [x] ⑤ 定向 pytest：32 passed（test_skill_slimming_contracts + test_profile_contracts；合同文本断言未受影响，无需改断言）
  - [x] ⑥ git diff --check 通过；diff 范围 5 文件 +27/−6 + Delta 新建，全部在声明目标内
  - [x] 行号锚定抽查：specs 下唯一 `SKILL.md:行号` 引用指向未改动文件（workflow-code-review:65，其真实锚点在 :67），系既有漂移非本次引入
  - [x] ⑦ md-zh 自检：新增行半角标点紧邻中文零命中；括号均为全角或行内代码包裹
  - [ ] ⑧ verify.py 退出 0（进行中）
  - [ ] ⑨ 独立 Review 无未解决 P0/P1（进行中）
- artifacts:
  - 本任务勾选记录与核验输出（写在勾选项与最终报告，机器运行报告不提交进源码）

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/engineering/tech/knowledge-management.md` | `openspec/specs/backend/engineering/tech/knowledge-management.md` | MODIFIED | Delta 已创建（Synced 于归档前核对） | 归档前登记 `openspec/index.md` 近期变更 |
直接维护轨（不经 Delta）：`skills/project-knowledge/SKILL.md`、`skills/bp-domain-modeling/*`、`overview.md` 速查节、features 文档 §4.6——行为合同直接维护在技能与状态文档（2057/2058 先例）。

## 知识冲突

- 结论：Resolved。Task 1/3 实施前重读目标文件现文，与 design.md 描述一致，未发现冲突；lint_spec 对 design 首版的结构性报错（缺 4-9 章）属模板不符，已按模板重写，非知识冲突。
