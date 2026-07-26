# 实施任务清单

> 由 proposal.md 生成。
> 任务总数：2。
> 核心原则：先以可测试的控制器契约封闭调度入口，再同步长期行为说明。

## 依赖关系总览

Task 1（实现 Verify 配置决策门禁与测试）
    ↓
Task 2（同步控制流合同与工作流说明）

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | 添加选择记录与调度门禁。 |
| `scripts/test_workflow_control.py` | 修改 | Task 1 | 覆盖阻断和放行行为。 |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 修改 | Task 2 | 记录控制流合同。 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2 | 记录选择命令和调度前置条件。 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `workflow_control.py ... dispatchable` | 新增前置门禁 | 委派执行编排方 | Task 1 |
| `workflow_control.py ... event <id> start` | 新增前置门禁 | 委派执行编排方 | Task 1 |
| `workflow_control.py ... verify-config-decision` | 新增 CLI | 用户或编排方 | Task 1 |

### 构建系统变更

- 无：项目使用现有 Python 测试与 Verify 配置。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | `tasks.md` 可能包含同名任务字段 | Task 1 | 只解析首个任务标题之前的全局记录，避免把任务字段误当选择。 |
| 2 | 配置可能在记录后被删除 | Task 1 | 每次调度重新核验文件；「初始化」记录在文件缺失时不能放行。 |

## 任务列表

### 任务 1：实现 Verify 配置决策门禁与测试
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`（修改），`scripts/test_workflow_control.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md §1、§2.1、§2.2、§2.3、§2.4
- 说明：实现全局选择记录、写入命令和三个调度入口的失败关闭检查；补充定向单测。
- context_files:
    - `skills/workflow-code-generation/scripts/workflow_control.py:214-223` — 当前可调度任务判定。
    - `skills/workflow-code-generation/scripts/workflow_control.py:606-612` — 仓库根定位。
    - `skills/workflow-code-generation/scripts/workflow_control.py:675-842` — CLI 解析与写入路径。
    - `scripts/test_workflow_control.py` — 控制器单元测试入口。
- verification:
    - [ ] `python scripts/test_workflow_control.py` 返回 0。
    - [ ] 缺配置且未记录时，`dispatchable` 和 `event start` 返回 2。
    - [ ] 「跳过」记录只在缺配置时放行；「初始化」记录只在配置存在时放行。
- artifacts:
    - `skills/workflow-code-generation/scripts/workflow_control.py`
    - `scripts/test_workflow_control.py`
- 子任务：
    - [x] 1.1：实现配置状态和决策记录的解析、校验与原子写入。
    - [x] 1.2：在 dispatch、恢复和启动任务前应用门禁。
    - [x] 1.3：添加并运行定向单测。

### 任务 2：同步控制流合同与工作流说明
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`openspec/specs/backend/framework/workflow-control/overview.md`（修改），`skills/workflow-code-generation/SKILL.md`（修改）
- depends_on: [Task 1]
- review_profile: standard
- 文档映射：proposal.md §1、§2.3、§3、§4
- 说明：使长期规格和执行入口与实际的决策命令、阻断范围及无配置边界一致。
- context_files:
    - `openspec/specs/backend/framework/workflow-control/overview.md` — 控制流长期合同。
    - `skills/workflow-code-generation/SKILL.md:83-84` — 当前用户选择提示。
    - `skills/workflow-code-generation/scripts/workflow_control.py` — Task 1 产出的 CLI 合同。
- verification:
    - [ ] `python scripts/lint_skill_graph.py` 返回 0。
    - [ ] 文档列出的命令、字段和值与 CLI 单测一致。
- artifacts:
    - `openspec/specs/backend/framework/workflow-control/overview.md`
    - `skills/workflow-code-generation/SKILL.md`
- 子任务：
    - [x] 2.1：更新控制流长期规格。
    - [x] 2.2：更新工作流入口说明。
    - [x] 2.3：运行文档引用图校验。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal.md §1 | Task 1、Task 2 | 实现门禁并记录其适用范围。 |
| proposal.md §2.1-§2.4 | Task 1 | 实现持久记录、命令和一致性校验。 |
| proposal.md §3-§4 | Task 2 | 同步长期合同和操作说明。 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| 控制流 Verify 决策门禁 | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Completed | 无需更新索引：入口路径不变。 |

## 知识冲突

- 结论：无冲突。`workflow_control.py` 的 CLI 门禁、`workflow-code-generation/SKILL.md` 的操作说明和长期规格均使用相同的选择命令与放行边界。

## 实际 Diff 核对

- 核对状态：Completed。已运行 `git diff --check`、`python scripts/test_workflow_control.py`、`python scripts/lint_skill_graph.py` 和配置驱动 Verify；交付门在提交后运行。
