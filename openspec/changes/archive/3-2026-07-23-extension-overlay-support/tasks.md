# 实施任务清单

> 由 proposal.md 生成
> 任务总数: 3
> 核心原则: 先定义并验证 Overlay 合同，再接入安装生命周期和 workflow，最后完成文档与全局验证。

## 依赖关系总览

```text
Task 1（Overlay 合同和安装生命周期）
    ↓
Task 2（Workflow 发现规则和文档）
    ↓
Task 3（集成验证和知识同步）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/install_agentic_framework.py` | 修改 | Task 1 | 解析、链接、刷新和卸载 Overlay。 |
| `scripts/test_install_agentic_framework.py` | 修改 | Task 1、Task 3 | 覆盖 Overlay 成功与失败路径。 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 2 | 增加 Overlay 规范发现。 |
| `skills/opsx-test-generation/SKILL.md` | 修改 | Task 2 | 增加 Overlay 规范发现。 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2 | 增加 Overlay 规范发现。 |
| `skills/workflow-test-generation/SKILL.md` | 修改 | Task 2 | 增加 Overlay 规范发现。 |
| `README.md` | 修改 | Task 2 | 说明 Core + Overlay 使用方式。 |
| `openspec/specs/backend/framework/install-agentic-framework/overview.md` | 修改 | Task 2 | 同步长期安装协议。 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `parse_args()` | 新增可重复 `--extension` 参数 | `main()` | Task 1 |
| `install()` | 新增 Overlay 选择参数 | `main()`、`refresh_all()`、测试 | Task 1 |
| `refresh_all()` | 按登记选择刷新 Overlay | `main()` | Task 1 |

### 构建系统变更

- 无。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | 现有 Manifest v2 未记录 Overlay。 | Task 1 | 升级 Schema，并使旧 Manifest 继续可读；刷新旧状态时要求显式单目标升级。 |
| 2 | 目标项目可存在自有 Skill。 | Task 1 | 只管理清单声明的唯一 Skill 名称；遇到已有非预期路径立即失败。 |
| 3 | Workflow 是 Markdown 指令，无法执行清单解析代码。 | Task 2 | 规定从当前核心 workflow 定位受信框架根，通过只读校验入口消费 JSON，按 `files` 后缀匹配。 |

## 任务列表

### 任务 1: [x] Overlay 合同和安装生命周期
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `scripts/install_agentic_framework.py`（修改）、`scripts/test_install_agentic_framework.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md 1、2.1、2.3、2.4、2.5、4
- 说明: 实现清单解析、受管链接、独立状态、Registry/刷新/卸载接线及失败原子性。
- context_files:
  - `scripts/install_agentic_framework.py:parse_args()` — CLI 参数入口。
  - `scripts/install_agentic_framework.py:install()` — 现有核心安装事务。
  - `scripts/install_agentic_framework.py:uninstall()` — 现有安全删除路径。
  - `scripts/install_agentic_framework.py:refresh_all()` — 已登记目标批量刷新。
  - `scripts/test_install_agentic_framework.py:InstallTest` — 链接拓扑和安全性回归测试。
- verification:
  - [ ] `python -m unittest discover -s scripts -p 'test_install_agentic_framework.py'` 返回 0。
  - [ ] 合法 Overlay 的两类客户端链接、刷新、卸载和只读校验均由测试覆盖。
  - [ ] 非法清单、冲突名称、孤立状态和被篡改链接均由测试覆盖且失败。
- artifacts:
  - `scripts/install_agentic_framework.py`
  - `scripts/test_install_agentic_framework.py`
- 子任务:
  - [ ] 1.1: 定义并校验 Overlay 清单与安装状态数据结构。
  - [ ] 1.2: 接入安装、刷新、卸载和 Registry。
  - [ ] 1.3: 调用 `workflow-test-generation` 为成功与失败路径生成测试。
  - [ ] 1.4: 运行安装器测试。

### 任务 2: [x] Workflow 发现规则和用户文档
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/opsx-code-generation/SKILL.md`（修改）、`skills/opsx-test-generation/SKILL.md`（修改）、`skills/workflow-code-generation/SKILL.md`（修改）、`skills/workflow-test-generation/SKILL.md`（修改）、`README.md`（修改）、`openspec/specs/backend/framework/install-agentic-framework/overview.md`（修改）
- depends_on: [Task 1]
- review_profile: standard
- 文档映射: proposal.md 1、2.2、2.3、2.5、3、4
- 说明: 让两个 Profile 的编码与测试入口通过只读校验 JSON 加载适用的私有 Skill，并记录无冲突更新流程与运维边界。
- context_files:
  - `skills/opsx-code-generation/SKILL.md:步骤 4` — Production 编码规范加载位置。
  - `skills/opsx-test-generation/SKILL.md:4.1` — Production 测试规范加载位置。
  - `skills/workflow-code-generation/SKILL.md:步骤 4` — Tooling 编码规范加载位置。
  - `skills/workflow-test-generation/SKILL.md:4.1` — Tooling 测试规范加载位置。
  - `README.md:如何扩展` — 公开扩展说明。
  - `openspec/specs/backend/framework/install-agentic-framework/overview.md` — 长期安装协议。
- verification:
  - [ ] `python scripts/lint_skill_graph.py` 返回 0。
  - [ ] `python scripts/test_lint_skill_graph.py` 返回 0。
  - [ ] README 包含安装、更新、冲突和安全边界说明。
- artifacts:
  - 上述 6 个 Markdown 文件。
- 子任务:
  - [ ] 2.1: 在四个加载入口加入同一 Overlay 发现步骤。
  - [ ] 2.2: 更新 README 和安装器长期 Spec。
  - [ ] 2.3: 按 `md-zh` 自检新增中文 Markdown。

### 任务 3: [x] 集成验证和知识同步
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `scripts/test_install_agentic_framework.py`（可能修改）、`openspec/changes/3-extension-overlay-support/tasks.md`（修改）
- depends_on: [Task 1, Task 2]
- review_profile: standard
- 文档映射: proposal.md 1、3、4
- 说明: 运行完整回归与静态校验，核对实际 Diff、知识同步和任务状态。
- context_files:
  - `verify.config.json` — 项目验证配置。
  - `scripts/test_install_agentic_framework.py` — 安装器回归入口。
  - `scripts/lint_skill_graph.py` — Skill 图校验入口。
  - `openspec/changes/3-extension-overlay-support/proposal.md` — 已批准范围和验收标准。
- verification:
  - [ ] `python -m unittest discover -s scripts -p 'test_*.py'` 返回 0。
  - [ ] `python scripts/lint_skill_graph.py` 返回 0。
  - [ ] `python skills/workflow-verification/scripts/verify.py --diff-base 718a45c` 返回 0。
  - [ ] `git diff --check` 返回 0。
- artifacts:
  - `.agentic-framework/verify/report.json`
  - `openspec/changes/3-extension-overlay-support/tasks.md`
- 子任务:
  - [ ] 3.1: 运行完整回归和 Skill 图校验。
  - [ ] 3.2: 运行配置驱动验证与 Diff 检查。
  - [ ] 3.3: 记录实际 Diff、知识同步和冲突核对结论。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal.md 1 | Task 1、Task 2、Task 3 | 解决冲突问题并验证验收标准。 |
| proposal.md 2.1-2.5 | Task 1、Task 2 | 安装协议、状态边界与 workflow 发现规则。 |
| proposal.md 3 | Task 2、Task 3 | 同步长期安装知识并核对。 |
| proposal.md 4 | Task 1、Task 2、Task 3 | 保留路径、并发和链接权限边界。 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| 安装器 Overlay 协议 | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | Completed | 不需要：索引路径不变。 |

## 知识冲突

- 结论：无冲突。`scripts/install_agentic_framework.py` 的 Overlay Descriptor、状态校验和链接生命周期与长期安装 Spec 一致；安装器和全量脚本测试通过。

## 实际 Diff 核对

- 核对状态：PASS。实际 Diff 覆盖安装器、安装器测试、四个 workflow 入口、README 和长期安装 Spec；`python skills/workflow-verification/scripts/verify.py --baseline E:/github/agentic-engineering-framework/.agentic-framework/verify/baseline.json --diff-base 718a45c670d4190c77a92f630e6946e3f48ed589 --run-dir .agentic-framework/runs/3-extension-overlay-support`、`python -m unittest discover -s scripts -p 'test_install_agentic_framework.py'` 和 `git diff --check` 均通过。

## 交付前 intent 沉淀检查

- 不可逆或高影响架构决策：命中 → 已记录到 `proposal.md` 的「2.5 关键权衡」和 `openspec/specs/backend/framework/install-agentic-framework/overview.md`。
- 放弃重要方案：命中 → 已记录到 `proposal.md` 的「2.5 关键权衡」：不允许 Overlay 补丁核心 workflow。
- 新增红线约束：命中 → 已记录到 `openspec/specs/backend/framework/install-agentic-framework/overview.md`：Overlay 不得覆盖核心资产或删除项目自有文件。
- 已验证故障根因：未命中。
- 跨项目知识候选：命中 → 本机制可跨项目复用，但仅保留在当前项目 Change；未获用户确认，不写入公共知识库。
- 普通变更：未命中。
