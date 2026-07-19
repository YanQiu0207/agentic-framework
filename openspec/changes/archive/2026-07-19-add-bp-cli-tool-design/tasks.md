# 实施任务清单

> 由 `proposal.md` 生成
> 任务总数：4
> 核心原则：先建立最佳实践，再接入 Workflow 和安装器，最后统一验证与归档。

## 依赖关系总览

```text
Task 1（创建 bp-cli-tool-design）
  ├── Task 2（接入双 Profile Workflow）
  └── Task 3（接入安装器并补测试）
          Task 2 + Task 3
                  ↓
          Task 4（统一验证与知识归档）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/bp-cli-tool-design/SKILL.md` | 新建 | Task 1 | CLI 最佳实践入口 |
| `skills/bp-cli-tool-design/reference/cli-tool-design-principles.md` | 新建 | Task 1 | 详细原则与检查清单 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 2 | Production 按场景加载 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2 | Tooling 按场景加载 |
| `scripts/install_agentic_framework.py` | 修改 | Task 3 | 加入 Shared Core 和受管清单 |
| `scripts/test_install_agentic_framework.py` | 修改 | Task 3 | 验证两个 Profile 的安装结果 |
| `openspec/changes/add-bp-cli-tool-design/proposal.md` | 修改 | Task 4 | 状态与实际结果核对 |
| `openspec/changes/add-bp-cli-tool-design/tasks.md` | 修改 | Task 1～4 | 执行状态、证据与归档 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `CORE_SKILLS` | 新增成员 | `build_operations()` | Task 3 |
| `MANAGED_PROFILE_SKILL_ROOTS` | 新增受管路径 | 安装、切换与卸载逻辑 | Task 3 |
| Production / Tooling 编码规范加载表 | 新增条件规则 | 对应代码生成 Workflow | Task 2 |

### 构建系统变更

- 无构建系统变更；仓库使用 Python 测试和 Skill 引用图作为验证入口。

## 风险与假设

| # | 描述 | 影响任务 | 假设或处理 |
| --- | --- | --- | --- |
| 1 | 来源 Skill 含项目专属语言规则 | Task 1 | 只迁移通用 CLI 设计内容，语言规则由本仓库 `AGENTS.md` 管理 |
| 2 | Shared Core 使用显式安装白名单 | Task 3 | 同时更新当前选择集和兼容受管集合，避免安装与卸载语义不一致 |
| 3 | 工作区已有无关 `openspec` 改动 | Task 1～4 | 只提交本 Change 和明确列出的实现文件，不覆盖或提交无关改动 |

## 任务列表

### 任务 1：[x] 创建 `bp-cli-tool-design`

- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/bp-cli-tool-design/SKILL.md`（新建）、`skills/bp-cli-tool-design/reference/cli-tool-design-principles.md`（新建）
- depends_on：[]
- review_profile：lightweight
- 文档映射：`proposal.md` 1、2.1、2.2、2.3
- 说明：将来源 Skill 适配为本框架的 CLI 最佳实践，保持薄入口和单层参考结构。
- context_files：
    - `E:/work/linux/.codex/skills/cli-tool-design/SKILL.md` — 来源入口
    - `E:/work/linux/.codex/skills/cli-tool-design/references/cli-tool-design-principles.md` — 来源原则正文
    - `skills/bp-skill-authoring/SKILL.md` — 本框架 Skill 编写规范
- verification：
    - [x] `PYTHONUTF8=1 python C:/Users/YanQi/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/bp-cli-tool-design` 返回 `Skill is valid!`
    - [x] `python scripts/lint_skill_graph.py` 不报告新增 Skill 结构错误
    - [x] 人工按 `md-zh` 检查新增中文 Markdown
- artifacts：
    - `skills/bp-cli-tool-design/SKILL.md`
    - `skills/bp-cli-tool-design/reference/cli-tool-design-principles.md`
- 子任务：
    - [x] 1.1：改写名称、中文触发描述和工作流
    - [x] 1.2：迁移并精简通用原则，删除来源项目专属规则
    - [x] 1.3：运行 Skill 结构和 Markdown 自检

### 任务 2：[x] 接入双 Profile 代码生成 Workflow

- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/opsx-code-generation/SKILL.md`（修改）、`skills/workflow-code-generation/SKILL.md`（修改）
- depends_on：[Task 1]
- review_profile：lightweight
- 文档映射：`proposal.md` 1、2.1、2.2
- 说明：在两个代码生成入口的编码规范表中增加 CLI 场景条件加载规则。
- context_files：
    - `skills/opsx-code-generation/SKILL.md` — Production 入口
    - `skills/workflow-code-generation/SKILL.md` — Tooling 入口
    - `skills/bp-cli-tool-design/SKILL.md` — 新增被引用 Skill
- verification：
    - [x] `python scripts/lint_skill_graph.py` 返回 0
    - [x] `rg -n "bp-cli-tool-design" skills/opsx-code-generation/SKILL.md skills/workflow-code-generation/SKILL.md` 在两个文件中均命中
    - [x] `python -m pytest scripts/test_profile_contracts.py -q` 通过
- artifacts：
    - `skills/opsx-code-generation/SKILL.md`
    - `skills/workflow-code-generation/SKILL.md`
- 子任务：
    - [x] 2.1：增加 Production 条件加载规则
    - [x] 2.2：增加 Tooling 条件加载规则
    - [x] 2.3：运行 Skill 图和 Profile 契约测试

### 任务 3：[x] 接入安装器并补契约测试

- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/install_agentic_framework.py`（修改）、`scripts/test_install_agentic_framework.py`（修改）
- depends_on：[Task 1]
- review_profile：standard
- 文档映射：`proposal.md` 1、2.1、2.2、2.3
- 说明：把新 Skill 加入 Shared Core 当前选择集和两个 Profile 的受管集合，并验证两个 Profile 均安装该 Skill。
- context_files：
    - `scripts/install_agentic_framework.py:CORE_SKILLS` — 当前安装选择集
    - `scripts/install_agentic_framework.py:MANAGED_PROFILE_SKILL_ROOTS` — Profile 受管集合
    - `scripts/test_install_agentic_framework.py:InstallTest` — 安装契约测试
    - `skills/bp-cli-tool-design/SKILL.md` — 被安装源资产
- verification：
    - [x] `python -m pytest scripts/test_install_agentic_framework.py -q` 通过
    - [x] `python -m pytest scripts/test_profile_contracts.py -q` 通过
    - [x] 测试断言 Production 与 Tooling 的 Codex、Claude Code 目标均包含 `bp-cli-tool-design`
- artifacts：
    - `scripts/install_agentic_framework.py`
    - `scripts/test_install_agentic_framework.py`
- 子任务：
    - [x] 3.1：更新当前选择集和兼容受管集合
    - [x] 3.2：增加双 Profile 安装契约测试
    - [x] 3.3：运行安装器和 Profile 契约测试

### 任务 4：[x] 统一验证与知识归档

- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`openspec/changes/add-bp-cli-tool-design/proposal.md`（修改）、`openspec/changes/add-bp-cli-tool-design/tasks.md`（修改）
- depends_on：[Task 2, Task 3]
- review_profile：standard
- 文档映射：`proposal.md` 验收标准、3
- 说明：对合并结果运行统一验证和 Review，核对长期知识影响并归档 Change。
- context_files：
    - `verify.config.json` — 统一机器验证配置
    - `openspec/changes/add-bp-cli-tool-design/proposal.md` — 本次契约
    - `openspec/changes/add-bp-cli-tool-design/tasks.md` — 状态与证据真相源
    - `openspec/specs/backend/engineering/tech/framework-unification.md` — Shared Core 现有决策
- verification：
    - [x] `python -m pytest scripts -q` 通过
    - [x] `python scripts/lint_skill_graph.py` 返回 0
    - [x] `workflow-verification` 报告为 PASS 且包含 `spec_drift` 结论
    - [x] Run 级 `workflow-code-review` 结论为 PASS，或所有 P0/P1 finding 已关闭
- artifacts：
    - `.verify/report.json`
    - Run 级 Review 报告
    - 归档后的 `proposal.md` 与 `tasks.md`
- 子任务：
    - [x] 4.1：运行统一机器验证
    - [x] 4.2：执行一次 Run 级 Code Review
    - [x] 4.3：核对实际 Diff、知识影响和归档状态

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| 1. 问题与目标 | Task 1、Task 2、Task 3 | 创建、接线和安装覆盖全部目标 |
| 2.1 整体方案 | Task 1、Task 2、Task 3 | 落实 Shared Core 与按需加载 |
| 2.2 核心组件 | Task 1、Task 2、Task 3 | 分别覆盖 Skill、Workflow 和安装器 |
| 2.3 关键权衡 | Task 1、Task 2、Task 4 | 保持适配边界并在归档时核对 |
| 3. 知识影响 | Task 4 | 核对长期知识与现有架构决策 |

## 知识同步

无独立 Spec Delta：新增 `bp-*` Skill 本身即长期最佳实践载体；Shared Core 的既有架构规则已覆盖通用 `bp-*`，Task 4 负责核对无需修改现有长期 Spec。

## 知识冲突

- 结论：无冲突。`framework-unification.md` 已将通用 `bp-*` 定义为 Shared Core，本次实现与该合同一致；当前工作区中的其他知识更新未纳入本次提交。

## 实际 Diff 核对

- 核对状态：PASS。已使用 `git diff 0c26b76d22145fed04e517903e52c3060411f6b2 -- <本任务文件>` 核对实际改动；全量 `workflow-verification`、安装器测试、Profile 契约测试和 Skill 引用图均通过，Run 级 Review 在第 2 轮定向复审后 PASS。
