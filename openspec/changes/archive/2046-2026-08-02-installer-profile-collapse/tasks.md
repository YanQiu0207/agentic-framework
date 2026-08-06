# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数：5
> 核心原则：坍缩等价常量、删失效死逻辑，纯实现追平 change 2045 已合并的设计；保留 `profile` 字段与两处有意差异

## 依赖关系总览

```
Task 1 (合并冗余常量)
  ├─▶ Task 2 (清理死逻辑)
  └─▶ Task 3 (等价性测试)
Task 4 (README 措辞)            ← 独立，可与 Task 1 并行
Task 1,2,3,4 ─▶ Task 5 (知识同步与归档)
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/install_agentic_framework.py` | 修改 | Task 1, 2 | 合并四组等价常量；删除 `_forbidden_entry_paths`／`_cross_pollution_errors` 及两处调用 |
| `scripts/test_install_agentic_framework.py` | 修改 | Task 3 | 新增两 profile 安装内容等价性断言 |
| `README.md` | 修改 | Task 4 | L113 措辞修正、L16-28 补两 profile 安装内容相同说明 |
| `openspec/specs/backend/framework/install-agentic-framework/overview.md` | 修改 | Task 5 | 补记安装器代码已坍缩为单一 delivery 常量 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| 模块常量 `PRODUCTION_SKILLS`/`TOOLING_SKILLS` 等 | 删除（合并为 `DELIVERY_*`） | 仅 `install_agentic_framework.py` 内部；测试不直接引用 | Task 1 |
| `_forbidden_entry_paths`/`_cross_pollution_errors` | 删除 | 仅 `install()` 内部 | Task 2 |

### 构建系统变更

无。纯 Python 模块内部重构，无新文件、无构建配置变化。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | `_cross_pollution_errors` 删除后是否丢失「拒绝替换未受管目标」防护 | Task 2 | 该防护由 `_preflight`（L987）独立承载，删除前用 grep 确认 `_preflight` 仍覆盖；现有 `test_unmanaged_leaf_link_is_refused_but_managed_leaf_is_allowed` 验证不退化 |
| 2 | `MANAGED_PROFILE_SKILL_ROOTS[profile]` 改为单一常量后，`_manifest_allowed_path` 对两个 profile 的路径校验是否等价 | Task 1 | 两个 key 的 frozenset 内容完全相同（已逐行核对 L133-182），合并后两 profile 校验结果不变；由 Task 3 等价性测试与现有 manifest 测试共同保证 |
| 3 | 测试文件是否直接引用被删常量名 | Task 1 | grep 确认 `test_install_agentic_framework.py` 不引用 `PRODUCTION_SKILLS` 等符号，全通过 `build_operations`／`install` 行为断言 |

## 任务列表

### 任务 1：[x] 合并安装器四组等价 Profile 常量
- 状态：完成
- 文件：`scripts/install_agentic_framework.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md §2.2
- 说明：把 `PRODUCTION_SKILLS`/`TOOLING_SKILLS` 合并为 `DELIVERY_SKILLS`，`PRODUCTION_COMMANDS`/`TOOLING_COMMANDS` 合并为 `DELIVERY_COMMANDS`，`MANAGED_PROFILE_SKILL_ROOTS`（两 key 同值 dict）坍缩为单一 `MANAGED_SKILL_ROOTS`，`MANAGED_PROFILE_COMMAND_FILES` 坍缩为 `MANAGED_COMMAND_FILES`。更新 `_selected_names`（去掉 `if profile == "production" else` 分支）、`_all_core_skill_names`（union 一次）、`_manifest_allowed_path`（用单一常量，保留 `profile` 参数供 `scripts/validate_change.py` 规则）。
- context_files:
  - `scripts/install_agentic_framework.py:46-59` — `PRODUCTION_SKILLS`/`TOOLING_SKILLS` 定义
  - `scripts/install_agentic_framework.py:68-85` — `PRODUCTION_COMMANDS`/`TOOLING_COMMANDS` 定义
  - `scripts/install_agentic_framework.py:132-219` — `MANAGED_PROFILE_SKILL_ROOTS`/`MANAGED_PROFILE_COMMAND_FILES`
  - `scripts/install_agentic_framework.py:321-338` — `_selected_names` 按_profile 分支
  - `scripts/install_agentic_framework.py:408-417` — `_all_core_skill_names`
  - `scripts/install_agentic_framework.py:567-593` — `_manifest_allowed_path`
- verification:
  - [x] `grep -nE 'PRODUCTION_SKILLS|TOOLING_SKILLS|PRODUCTION_COMMANDS|TOOLING_COMMANDS|MANAGED_PROFILE_SKILL_ROOTS|MANAGED_PROFILE_COMMAND_FILES' scripts/install_agentic_framework.py` 无匹配
  - [x] 导入与 `build_operations` 构造无异常
  - [x] `python scripts/test_install_agentic_framework.py` 全部通过
  - [x] `python scripts/test_profile_contracts.py` 全部通过
- artifacts:
  - `scripts/install_agentic_framework.py`
- 子任务：
  - [x] 1.1: 定义 `DELIVERY_SKILLS`/`DELIVERY_COMMANDS`/`MANAGED_SKILL_ROOTS`/`MANAGED_COMMAND_FILES`，删除四个旧符号
  - [x] 1.2: 改 `_selected_names`、`_all_core_skill_names`、`_manifest_allowed_path` 引用
  - [x] 1.3: 运行 `test_install_agentic_framework.py` 与 `test_profile_contracts.py`，全部通过

### 任务 2：[x] 删除失效的交叉污染检查
- 状态：完成
- 文件：`scripts/install_agentic_framework.py`（修改）
- depends_on: Task 1
- review_profile: standard
- 文档映射：proposal.md §1、§2.5
- 说明：删除 `_forbidden_entry_paths`（L895）与 `_cross_pollution_errors`（L905）函数，以及 `install()` 中装前／装后两处调用。装前调用恒为空（死逻辑）；装后调用在受管链接创建后检查、退化为恒抛 `FileExistsError` 的 always-fail 隐患（change 2045 后引入，被符号链接守门的测试在无 Developer Mode 的 Windows 上 skip 掩盖）。删除同时清理死逻辑与修复该隐患；前置防护由 `_preflight` 承载。
- context_files:
  - `scripts/install_agentic_framework.py:895-915` — `_forbidden_entry_paths`/`_cross_pollution_errors`
  - `scripts/install_agentic_framework.py:1255-1266` — `install()` 装前调用点
  - `scripts/install_agentic_framework.py:1340-1351` — `install()` 装后调用点
  - `scripts/install_agentic_framework.py:967-996` — `_preflight`（确认仍承载「拒绝替换未受管目标」）
- verification:
  - [x] `grep -nE '_forbidden_entry_paths|_cross_pollution_errors|pollution' scripts/install_agentic_framework.py` 无匹配
  - [x] `python scripts/test_install_agentic_framework.py` 全部通过（重点 `test_unmanaged_leaf_link_is_refused_but_managed_leaf_is_allowed`、`test_profile_switch_requires_explicit_flag`）
  - [x] `python scripts/test_profile_contracts.py` 全部通过
- artifacts:
  - `scripts/install_agentic_framework.py`
- 子任务：
  - [x] 2.1: 删除两个函数与两处调用
  - [x] 2.2: 运行两个测试套件，全部通过

### 任务 3：[x] 新增两个 Profile 安装内容等价性测试
- 状态：完成
- 文件：`scripts/test_install_agentic_framework.py`（修改）
- depends_on: Task 1
- review_profile: standard
- 文档映射：proposal.md §1 验收标准 4
- 说明：新增 `test_both_profiles_install_identical_assets_except_validator`，断言 `build_operations(REPO_ROOT, "production", set())` 与 `build_operations(REPO_ROOT, "tooling", set())` 的 `relative_target` 集合完全相同，唯一差异为 Production 多 `.codex/scripts/validate_change.py` 与 `.claude/scripts/validate_change.py`。把 change 2045「两 Profile 文件集合一致」固化为机器断言。
- context_files:
  - `scripts/test_install_agentic_framework.py:108-124` — 现有 `build_operations` 测试风格参考
  - `scripts/test_install_agentic_framework.py:183-196` — `test_production_links_only_production_lifecycle` 参考
  - `scripts/install_agentic_framework.py:341-392` — `build_operations` 返回结构
- verification:
  - [x] 新增测试在 `python scripts/test_install_agentic_framework.py` 中通过
  - [x] 反向验证：临时要求两 profile 完全相同含 validator 时测试确实失败（差集报出两个 validate_change.py 路径），改回后通过
- artifacts:
  - `scripts/test_install_agentic_framework.py`
- 子任务：
  - [x] 3.1: 编写并运行新测试，通过
  - [x] 3.2: 反向验证测试有效性

### 任务 4：[x] 修正 README 两处与实际安装行为不符的措辞
- 状态：完成
- 文件：`README.md`（修改）
- depends_on: []
- review_profile: lightweight
- 文档映射：proposal.md §1 验收标准 5
- 说明：(a) L113「安装时必须同步复制根目录的 `scripts/` 目录」不准确——实际只把 `validate_change.py` 单文件以软链接装入 `.codex/scripts/` 与 `.claude/scripts/`，且仅 Production；改为准确表述。(b) L16-28「快速开始」补一句点明两个 Profile 安装的 Skill／Command 集合相同，`profile` 只影响运行时治理强度与 `validate_change.py` 是否装入。
- context_files:
  - `README.md:16-28` — 快速开始 Profile 选择
  - `README.md:100-115` — Production 工作流（L113 validate_change 表述）
  - `scripts/install_agentic_framework.py:369-379` — `validate_change.py` 仅 Production 的实际安装逻辑
- verification:
  - [x] `grep -n '同步复制根目录' README.md` 无匹配
  - [x] README L16-28 区间出现「两个 Profile 安装内容相同」或等义表述
  - [x] 人工通读修改段落，措辞与代码行为一致
- artifacts:
  - `README.md`
- 子任务：
  - [x] 4.1: 修正 L113 validate_change 表述
  - [x] 4.2: L16-28 补两 profile 安装内容相同说明

### 任务 5：[x] 知识同步与归档
- 状态：完成
- 文件：`openspec/specs/backend/framework/install-agentic-framework/overview.md`（修改）
- depends_on: Task 1, Task 2, Task 3, Task 4
- review_profile: lightweight
- 文档映射：proposal.md §3
- 说明：在 `overview.md`「白名单统一（change 2045）」节补记 change 2046：安装器代码已坍缩为单一 `DELIVERY_*` 常量，`_cross_pollution_errors` 两处失效检查已删除（装前死逻辑 + 装后 always-fail 隐患）；Profile 在安装内容层面已无差异，仅由 manifest `profile` 字段、运行时治理守卫与两处有意差异（`validate_change.py` 仅 Production、`frontend` pack 仅 Tooling）承载。随后做实际 Diff 核对、`lint_task_deps --state-consistency`、归档移动。
- context_files:
  - `openspec/specs/backend/framework/install-agentic-framework/overview.md:25-30` — 白名单统一节
- verification:
  - [x] `overview.md` 出现「坍缩」与「单一 delivery 常量」记录，并区分装前死逻辑／装后 always-fail
  - [x] `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2046-2026-08-02-installer-profile-collapse/tasks.md --state-consistency --governance-profile tooling` 通过
  - [x] 实际 Diff 核对完成并记录 PASS（见下）
  - [x] Change 移至 `openspec/changes/archive/2046-2026-08-02-installer-profile-collapse/`，proposal 头部状态改 Archived
- artifacts:
  - `openspec/specs/backend/framework/install-agentic-framework/overview.md`
- 子任务：
  - [x] 5.1: 更新 overview.md
  - [x] 5.2: 实际 Diff 核对
  - [x] 5.3: 状态一致性校验 + 归档

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal.md §1 问题／目标／验收 | Task 1, 2, 3, 4 | 常量合并、死逻辑清理、等价测试、README 措辞 |
| proposal.md §2.2 核心组件 | Task 1 | 四个新常量与三个调用点改写 |
| proposal.md §2.5 关键权衡 | Task 2 | 删除而非重定义 `_cross_pollution_errors` 的依据 |
| proposal.md §3 知识影响 | Task 5 | overview.md 补记 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `openspec/specs/backend/framework/install-agentic-framework/overview.md` | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | Done | 无需更新索引（已有条目） |

## 知识冲突

- 结论：无冲突。overview.md 更新与代码实际行为一致（`DELIVERY_*` 常量、`_preflight` 前置防护均经测试与 review 核实）。

## 实际 Diff 核对

- 核对状态：PASS。
- 改动文件（本次 change 范围）：`scripts/install_agentic_framework.py`、`scripts/test_install_agentic_framework.py`、`README.md`、`openspec/specs/backend/framework/install-agentic-framework/overview.md`。
- 核对命令与结论：
  - `python -m pytest scripts -q` → 545 passed, 21 skipped（0 failed）
  - `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base HEAD` → 总判定 PASS（test-count 566 vs 基线 565；skill-graph-lint exit 0；spec_drift pass）
  - `python skills/workflow-code-generation/scripts/lint_skill_graph.py` → exit 0
  - Code Review（standard / integration）：verdict=PASS，0 P0／0 P1，1 个 P2 文档措辞已修
