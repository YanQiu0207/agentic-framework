# 实施任务清单

> 用户已授权自主落实和免人工审核。验证配置：使用现有 `verify.config.json`，不修改。

## 依赖关系总览

Task 1 → Task 2 → Task 4
Task 3 → Task 4

## 变更影响概览

安装器及共享能力查询、交付门与 Runtime 入口、Skill／Command／Agent 指令及引用、回归测试和长期项目知识。

## 风险与假设

选装是功能入口控制，不是文件保密隔离。旧安装保持既有能力；源码工作区完整能力仅对可核实的框架根适用。原始候选不直接整体覆盖当前源码。

## 任务列表

### 任务 1：[x] 能力包选择与安全迁移
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/install_agentic_framework.py`，`scripts/framework_packs.py`，`scripts/test_install_agentic_framework.py`，`scripts/test_framework_packs.py`
- depends_on: []
- review_profile: strict
- 文档映射：proposal.md 第 2～3 节；design.md 第 4.1～4.2 节
- context_files:
  - `scripts/install_agentic_framework.py`
  - `scripts/governance_profile.py`
  - `scripts/test_install_agentic_framework.py`
- verification:
  - [x] 安装器和能力查询测试通过
  - [x] 默认核心、显式选装、继承、移除和旧清单迁移均有覆盖
- artifacts:
  - `scripts/framework_packs.py`
  - `scripts/test_framework_packs.py`

### 任务 2：[x] 统一交付路径与 Runtime 启用检查
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`，`skills/workflow-code-generation/scripts/workflow_control.py`，`scripts/test_check_delivery.py`，`scripts/test_workflow_control.py`，`scripts/test_delivery_route_fixture_runner.py`，`scripts/delivery_route_fixture_runner.py`，`evaluation/fixtures/`
- depends_on: Task 1
- review_profile: strict
- 文档映射：design.md 第 4.1～4.3 节
- context_files:
  - `skills/workflow-code-generation/scripts/check_delivery.py`
  - `skills/workflow-code-generation/scripts/workflow_control.py`
  - `scripts/framework_packs.py`
  - `scripts/test_check_delivery.py`
- verification:
  - [x] 门禁、路由及相关回归测试通过
  - [x] 旧路径拒绝、伪造证据拒绝和缺包停止均有覆盖
- artifacts:
  - `skills/workflow-code-generation/scripts/check_delivery.py`
  - `skills/workflow-code-generation/scripts/workflow_control.py`

### 任务 3：[x] Skill 精简、报告降噪与冲突修复
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/` 下指令与参考 Markdown，`commands/`，`agents/`，`scripts/test_skill_slimming_contracts.py`，`scripts/lint_skill_graph.py`，`scripts/test_lint_skill_graph.py`
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 第 2～3 节；design.md 第 4.2～5 节
- context_files:
  - `skills/workflow-code-generation/SKILL.md`
  - `skills/project-init/SKILL.md`
  - `skills/project-knowledge/SKILL.md`
  - `skills/workflow-code-review/SKILL.md`
- verification:
  - [x] 四处规则冲突已统一且有回归检查
  - [x] Skill 引用图校验通过
  - [x] 触发边界、强制检查和选装缺失停止点可定位
- artifacts:
  - `scripts/test_skill_slimming_contracts.py`
  - `skills/workflow-code-generation/SKILL.md`

### 任务 4：[ ] 集成验证、独立审查与知识同步
- 状态：进行中
- attempts：0
- control_stage：quality_passed
- 文件：`openspec/specs/backend/framework/`、`openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/backend/engineering/tech/knowledge-management.md`、`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md`、`README.md`、当前 Change
- depends_on: Task 2, Task 3
- review_profile: strict
- 文档映射：proposal.md 第 3～4 节；design.md 第 6～7 节
- context_files:
  - `verify.config.json`
  - `scripts/analyze_session_metrics.py`
  - `openspec/specs/backend/framework/quality-gates/overview.md`
  - `openspec/specs/backend/framework/install-agentic-framework/overview.md`
- verification:
  - [x] 全量测试与引用图通过，核对改动前后基线
  - [x] 独立审查完成，P0／P1 修复并定向复核
  - [x] 文档与代码一致，用户既有改动未卷入
- artifacts:
  - 当前 Change 的验证报告

## 文档覆盖映射

| 范围 | 任务 |
| --- | --- |
| 安装与迁移 | Task 1 |
| 交付与 Runtime | Task 2 |
| 六类精简与四处冲突 | Task 3 |
| 验证与长期知识 | Task 4 |

## 知识同步

安装、质量门、工作流和知识管理的 4 份模块说明、3 份工程合同与 README 已按实际实现同步；Delta 位于本 Change 的 `specs/backend/framework/`。相关来源元数据同步至已集成提交，未修改遥测模块的既有元数据。

## 知识冲突

以本次批准的新行为替换活跃规则；历史 Change 与旧候选不覆盖。

## 实际 Diff 核对

Task 1～3 已分别通过机器验证并合入。Task 4 的实际文档范围补全到上方文件清单；历史 `docs/tooling/` 不改写。最终全量 Verify 和定向复审通过，见 `execution-report.md` 与 `review.md`。本任务完成只核销上述实现、验证和知识同步验收项，不把冻结规划 SHA 的诊断结果当作实际实现的完整 Runtime 证明。
