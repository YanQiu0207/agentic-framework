# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数：5
> 核心原则：五项互不依赖，脚本修复先写复现测试；文档改动以契约测试与技能图校验验证

## 依赖关系总览

Task 1 (OPSX018／029 豁免)
Task 2 (配置缺失不算覆盖不完整)
Task 3 (公共库 superseded)
Task 4 (Production 追加字段)
Task 5 (lint_spec 接线)

五个任务互不依赖，可并行。

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/validate_change.py` | 修改 | Task 1 | OPSX018 豁免、OPSX029 按 Delta 存在与否要求映射 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 1 | 复现测试 |
| `scripts/native_subject.py` | 修改 | Task 2 | 删除 `verify_config_missing` 限制 |
| `scripts/test_native_subject.py` | 修改 | Task 2 | 复现测试 |
| `scripts/validate_shared_knowledge.py` | 修改 | Task 3 | 增加 `superseded` 与 `superseded_by` 校验 |
| `scripts/test_validate_shared_knowledge.py` | 修改 | Task 3 | 复现测试 |
| `skills/project-knowledge/reference/knowledge-advanced.md` | 修改 | Task 3 | 写明状态合法值 |
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 修改 | Task 4 | 新增 Production 追加字段 |
| `skills/workflow-system-design/SKILL.md` | 修改 | Task 5 | 前置条件与设计完成前接入 `lint_spec.py` |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 5 | 步骤 2 接入 `lint_spec.py` |
| `docs/tooling/08-evaluation-strategy.md` | 修改 | Task 5 | 挂点描述与实际一致 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `validate_change._validate_change_type` / `_validate_plan` | 行为放宽（无影响时） | `governance_guards.plan_gate_errors`、CLI | Task 1 |
| `native_subject.capture_subject` | `limitations` 不再含 `verify_config_missing` | `verify.py`、`check_delivery.py` | Task 2 |

### 构建系统变更

- 无。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 公共库在另一个仓库 `E:/work/shared-knowledge-base` | Task 3 | 写入前 `git pull --ff-only`，失败即停；只做行级修改，不改已有条目 |
| 2 | 测试文件实际名称以仓库为准 | Task 1～3 | 实现时按现有测试文件落位 |

## 任务列表

### 任务 1：[x] Standard 无知识影响时豁免 OPSX018 与 OPSX029 的 Delta 要求
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/validate_change.py`（修改）, `scripts/tests/test_validate_change.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 验收标准第 1 条；§2.5 第 1 条
- 说明：Standard 路径读取 proposal「知识影响」，命中「无长期知识影响：<理由>」时不报 OPSX018；OPSX029 只在 Change 存在 Delta 时要求映射表覆盖 Delta；更新 OPSX018 修复提示。
- context_files:
  - `scripts/validate_change.py:915-938` — OPSX018／019
  - `scripts/validate_change.py:1569-1620` — `_validate_plan` 与 OPSX029
  - `scripts/validate_change.py:969-992` — 「知识影响」读取与 `no_impact` 正则（OPSX043）
  - `scripts/knowledge_sync.py` — `section_lines`、`delta_map`
- verification:
  - [x] 复现测试修复前失败、修复后通过：无影响无 Delta 不报 OPSX018／029；有影响无 Delta 仍报 OPSX018
  - [x] `python -m pytest scripts/tests/test_validate_change.py -q` 全部通过
- artifacts:
  - `scripts/validate_change.py`
  - `scripts/tests/test_validate_change.py`

### 任务 2：[x] 缺少 verify.config.json 不再算主体覆盖不完整
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/native_subject.py`（修改）, `scripts/test_native_subject.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 验收标准第 2 条；§2.5 第 4 条
- 说明：删除 `verify_config_missing` 限制；主体继续记录 `config_sha256: null`。
- context_files:
  - `scripts/native_subject.py:540-606` — 限制收集与主体摘要
  - `skills/workflow-verification/scripts/verify.py:1425-1455` — 覆盖不完整判 ERROR
  - `skills/workflow-code-generation/scripts/check_delivery.py:467-495` — 交付门重算主体
- verification:
  - [x] 复现测试修复前失败、修复后通过：无配置 `complete=True`；补配置后 `subject_id` 改变
  - [x] `python -m pytest scripts/test_native_subject.py skills/workflow-verification -q` 全部通过
- artifacts:
  - `scripts/native_subject.py`
  - `scripts/test_native_subject.py`

### 任务 3：[x] 公共库状态值增加 superseded 并写明合法值
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/validate_shared_knowledge.py`（修改）, `scripts/test_validate_shared_knowledge.py`（修改）, `skills/project-knowledge/reference/knowledge-advanced.md`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 验收标准第 3 条；§2.5 第 2 条；§3 知识影响
- 说明：允许值增加 `superseded`，缺 `superseded_by` 报错；晋升参考与公共库 `index.md` 写入规则写明五个合法值；长期 Spec 经 Delta 同步。
- context_files:
  - `scripts/validate_shared_knowledge.py:17-100` — 必填字段、允许值与条目检查
  - `skills/project-knowledge/reference/knowledge-advanced.md` — 晋升步骤第 3 条
  - `E:/work/shared-knowledge-base/index.md` — 写入规则第 5 条
  - `openspec/specs/backend/engineering/tech/knowledge-management.md` §11 — 证据等级
- verification:
  - [x] 复现测试修复前失败、修复后通过：`superseded` 缺 `superseded_by` 报错，填写后通过
  - [x] `python -m pytest scripts/test_validate_shared_knowledge.py -q` 全部通过
- artifacts:
  - `scripts/validate_shared_knowledge.py`
  - `scripts/test_validate_shared_knowledge.py`
  - `skills/project-knowledge/reference/knowledge-advanced.md`
  - `E:/work/shared-knowledge-base/index.md`

### 任务 4：[x] 任务拆解指南补 Production 追加字段
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/reference/task_planning_guide.md`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 验收标准第 4 条
- 说明：新增「Production 追加字段」小节，列出验收标准、Task Review／Review Report、文件或无需修改代码、文档映射与覆盖映射写法、头部 Code Review、Production 下不得使用 lightweight。
- context_files:
  - `scripts/validate_change.py:1262-1560` — Tasks 字段规则（OPSX022～038、063～064）
  - `scripts/validate_change.py:1954-2000` — 交付阶段头部 Code Review（OPSX032）
- verification:
  - [x] 按新小节写的样例在临时目录通过 `validate_change --phase plan --governance-profile production` 的 Tasks 规则
  - [x] `python -m pytest scripts/test_skill_slimming_contracts.py scripts/test_profile_contracts.py -q` 全部通过
- artifacts:
  - `skills/workflow-code-generation/reference/task_planning_guide.md`

### 任务 5：[x] lint_spec 接入系统设计与代码生成
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-system-design/SKILL.md`（修改）, `skills/workflow-code-generation/SKILL.md`（修改）, `docs/tooling/08-evaluation-strategy.md`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 验收标准第 5 条；§2.5 第 3 条
- 说明：系统设计前置条件跑 `proposal.md --phase design`，设计完成前跑 `design.md --phase design-code`；代码生成步骤 2 跑 `proposal.md --phase code` 与 `design.md --phase design-code`；失败时按指令退回对应阶段；修正 08 文档描述。
- context_files:
  - `skills/workflow-system-design/SKILL.md` — 前置条件、设计完成后
  - `skills/workflow-code-generation/SKILL.md` — 步骤 2
  - `skills/workflow-code-generation/scripts/lint_spec.py` — 参数与退出码
  - `docs/tooling/08-evaluation-strategy.md:47-52` — 挂点描述
- verification:
  - [x] `python scripts/lint_skill_graph.py` 0 错
  - [x] `python -m pytest scripts/test_skill_slimming_contracts.py scripts/test_profile_contracts.py -q` 全部通过
- artifacts:
  - `skills/workflow-system-design/SKILL.md`
  - `skills/workflow-code-generation/SKILL.md`
  - `docs/tooling/08-evaluation-strategy.md`

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal.md 验收标准第 1 条 | Task 1 | OPSX018／029 |
| proposal.md 验收标准第 2 条 | Task 2 | 配置缺失 |
| proposal.md 验收标准第 3 条、§3 | Task 3 | 公共库状态值与长期 Spec |
| proposal.md 验收标准第 4 条 | Task 4 | Production 字段 |
| proposal.md 验收标准第 5 条 | Task 5 | lint_spec 接线 |
| proposal.md 验收标准第 6 条 | Task 1, Task 2, Task 3, Task 4, Task 5 | 全量测试与技能图 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/engineering/tech/knowledge-management.md` | `openspec/specs/backend/engineering/tech/knowledge-management.md` | MODIFIED | Completed | `openspec/specs/backend/engineering/tech/` 无索引文件 |

## 知识冲突

- 结论：无冲突。全局规则要求的 `superseded` 与 `superseded_by` 已通过 Delta 就位并在归档时合并；`validate_shared_knowledge.py` 已同步。

## 实际 Diff 核对

- 核对状态：PASS。
- 核对命令与结论：`git log 10e7d1b..HEAD --stat`（5 个任务分支合并，改动文件与任务声明一致）；`pytest scripts skills -q`（全量通过，见交付说明）；`lint_task_deps.py --state-consistency`（0 矛盾）；`lint_skill_graph.py`（0 错）。
