# 实施任务清单

> 来源：proposal.md；用户已批准；任务总数：4。
> 执行形态：Native Delivery，串行，一次最终 Review。Verify 配置：使用现有配置。

## 依赖关系总览

Task 1 → Task 2 → Task 3 → Task 4

## 变更影响概览

| 文件 | 操作 | 任务 | 说明 |
| --- | --- | --- | --- |
| `skills/bp-component-design/SKILL.md`、`reference/deep-modules.md` | 修改／新增 | Task 1 | 方法唯一来源 |
| `skills/workflow-system-design/SKILL.md`、`skills/workflow-quick-design/SKILL.md`、`skills/workflow-test-generation/SKILL.md` | 修改 | Task 2 | 接点与授权复用 |
| `skills/workflow-architecture-improvement/`、`commands/architecture-improvement.md`、`scripts/install_agentic_framework.py`、`README.md` | 新增／修改 | Task 3 | 用户入口与安装 |
| `scripts/test_architecture_improvement_installation.py`、`skills/workflow-architecture-improvement/evaluation/trigger-cases.md`、`openspec/specs/backend/engineering/tech/architecture-improvement.md`、`openspec/index.md` | 新增／修改 | Task 4 | 回归、行为与知识 |

受影响接口：新增用户命令，无 Python 函数签名变化。构建系统：无需新增依赖，测试由现有 pytest 发现。

## 风险与假设

- 基线为 `1d7fb1d`，不依赖未提交的领域建模能力。
- 调查不自动创建 Change 或修改代码；选中后的实现按已有批准流程执行。

## 任务列表

### 任务 1：[x] 深模块判断法
- 状态：完成
- 文件：`skills/bp-component-design/SKILL.md`、`skills/bp-component-design/reference/deep-modules.md`
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md §1.1、§2.1
- context_files:
  - `skills/bp-component-design/SKILL.md`
  - `skills/workflow-code-review/SKILL.md`
- verification:
  - [x] `python scripts/lint_skill_graph.py` 通过
  - [x] 三种模块案例经独立行为演练核对
- artifacts:
  - `skills/bp-component-design/reference/deep-modules.md`

### 任务 2：[x] 设计与测试接点接线
- 状态：完成
- 文件：`skills/workflow-system-design/SKILL.md`、`skills/workflow-quick-design/SKILL.md`、`skills/workflow-test-generation/SKILL.md`
- depends_on: Task 1
- review_profile: standard
- 文档映射：proposal.md §1.2、§2.1
- context_files:
  - `skills/bp-component-design/SKILL.md`
  - `skills/workflow-system-design/SKILL.md`
  - `skills/workflow-test-generation/SKILL.md`
- verification:
  - [x] `python scripts/lint_skill_graph.py` 通过
  - [x] 已批准计划复用与契约冲突停止经行为演练核对
- artifacts:
  - `skills/workflow-system-design/SKILL.md`
  - `skills/workflow-test-generation/SKILL.md`

### 任务 3：[ ] 只读架构改善入口与安装
- 状态：需人工
- 原因：实现及无权限依赖的回归通过；真实安装、刷新、卸载测试因 Windows 符号链接权限跳过，待补环境复验。
- 文件：`skills/workflow-architecture-improvement/SKILL.md`、`commands/architecture-improvement.md`、`scripts/install_agentic_framework.py`、`README.md`
- depends_on: Task 2
- review_profile: standard
- 文档映射：proposal.md §1.3、§1.4、§2
- context_files:
  - `skills/project-knowledge/SKILL.md`
  - `skills/workflow-code-generation/SKILL.md`
  - `scripts/install_agentic_framework.py`
- verification:
  - [x] `python scripts/lint_skill_graph.py` 通过
  - [ ] 两 Profile 安装、刷新、卸载及失败保护回归通过
- artifacts:
  - `skills/workflow-architecture-improvement/SKILL.md`
  - `commands/architecture-improvement.md`
  - `scripts/install_agentic_framework.py`

### 任务 4：[ ] 验证、知识与最终审查
- 状态：需人工
- 原因：全量检查因 SVN 工具缺失与符号链接权限失败；保留原检查，不归档。详见 validation.md，独立 Review 证据在 `.agentic-framework/review/`。
- 文件：`scripts/test_architecture_improvement_installation.py`、`skills/workflow-architecture-improvement/evaluation/trigger-cases.md`、`openspec/specs/backend/engineering/tech/architecture-improvement.md`、`openspec/index.md`
- depends_on: Task 3
- review_profile: standard
- 文档映射：proposal.md §1.5、§3、§4
- context_files:
  - `verify.config.json`
  - `scripts/test_install_agentic_framework.py`
  - `skills/workflow-code-review/SKILL.md`
- verification:
  - [ ] `python -m pytest scripts -q` 通过
  - [x] `python scripts/lint_skill_graph.py` 通过
  - [x] 独立行为演练与最终 standard Review 完成
  - [ ] 原基线机器验证、状态一致性及交付门完成
- artifacts:
  - `scripts/test_architecture_improvement_installation.py`
  - `skills/workflow-architecture-improvement/evaluation/trigger-cases.md`
  - `openspec/specs/backend/engineering/tech/architecture-improvement.md`

## 文档覆盖映射

| 章节 | 任务 |
| --- | --- |
| proposal.md §1、§2 | Task 1、Task 2、Task 3 |
| proposal.md §3、§4 | Task 4 |
| proposal.md §5 | 调研来源，无独立实现 |

## 知识同步

目标：`openspec/specs/backend/engineering/tech/architecture-improvement.md`，根索引已接线；已同步，证据边界明确。

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| proposal.md §3（Quick Draft，无独立 Delta） | `openspec/specs/backend/engineering/tech/architecture-improvement.md` | ADDED | Completed | `openspec/index.md` 已接线 |

## 知识冲突

无已发现冲突；历史外部研究候选不视为已实施合同，新增实现合同独立接线，不覆盖历史研究。

## 实际 Diff 核对

已通过 `git diff --check`、定向安装测试与引用图核对，实际改动与批准范围一致；完整执行证据及未完成项见 validation.md。全量门禁失败，不归档、不宣称正式交付完成。
