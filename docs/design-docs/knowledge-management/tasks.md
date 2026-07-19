# 实施任务清单

> 来源：`spec.md`
> 状态：待实施
> 核心原则：先统一知识与 Change 契约，再迁移两个 Profile，最后迁移现有项目和公共知识库。

## 依赖关系总览

```text
Task 1（冻结统一契约）
    ↓
Task 2（改造 project-init 与安装归属）
    ↓
Task 3（重写 Shared project-knowledge）
    ↓
Task 4（改造 Production） ─┐
                            ├→ Task 6（统一验证器和测试）
Task 5（改造 Tooling） ────┘
    ↓
Task 7（迁移公共知识库）
    ↓
Task 8（迁移现有项目与历史文档）
    ↓
Task 9（端到端验收）
```

## 变更影响概览

### 框架契约与文档

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `docs/design-docs/knowledge-management/spec.md` | 已新建 | 当前统一知识管理设计 |
| `docs/design-docs/knowledge-management/tasks.md` | 已新建 | 实施任务和影响范围 |
| `docs/adr/002-unify-project-knowledge-layout.md` | 已新建 | 记录统一目录和知识生命周期决策 |
| `docs/design-docs/framework-unification/spec.md` | 待修改 | 恢复受控长期 Specs，统一两个 Profile 的 Artifact |
| `docs/framework-features-status-and-comparison.md` | 待修改 | 更新实现状态和能力边界 |
| `docs/tooling/09-personal-knowledge-base-plan.md` | 已修改 | 标记为被本方案取代 |
| `README.md` | 已修改 | 指向当前方案，说明尚未实施 |

### Shared Core 与项目初始化

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `skills/project-init/SKILL.md` | 待修改 | 统一 `openspec/` 骨架、Profile 选择、外置链接和公共库接线 |
| `commands/project-init.md` | 待检查 | 确保命令入口适用于两个 Profile |
| `skills/project-knowledge/SKILL.md` | 待重写 | 统一读取、写入、冲突、Delta 和晋升规则 |
| `scripts/install_agentic_framework.py` | 待修改 | 让 `project-init` 和 `project-knowledge` 可被两个 Profile 安装 |
| `scripts/test_install_agentic_framework.py` | 待修改 | 覆盖双 Profile 安装与 Pack 兼容性 |
| `scripts/test_profile_contracts.py` | 待修改 | 锁定统一 Artifact 与独立生命周期边界 |

### Production

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `skills/opsx-requirements-clarification/SKILL.md` | 待修改 | 接入项目索引，Delta 镜像长期 Specs 路径 |
| `skills/opsx-system-design/SKILL.md` | 待修改 | 接入业务、契约、模块人工知识和 Issues |
| `skills/opsx-code-generation/SKILL.md` | 待修改 | 接入模块约束和知识影响任务 |
| `skills/opsx-test-generation/SKILL.md` | 待修改 | 使用业务规则、共享契约和历史 Issues |
| `skills/opsx-archive/SKILL.md` | 待修改 | Archive 前执行知识同步和冲突检查 |
| `scripts/validate_change.py` | 待修改 | 校验 Delta 映射、知识影响和归档同步 |
| `scripts/test_validate_change.py` | 待修改 | 增加长期 Specs、冲突和 Archive 用例 |

### Tooling

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `skills/workflow-requirements-clarification/SKILL.md` | 待修改 | 从 `docs/design-docs/` 切换到 `openspec/changes/` |
| `skills/workflow-system-design/SKILL.md` | 待修改 | 使用统一项目知识入口 |
| `skills/workflow-quick-design/SKILL.md` | 待修改 | Quick Change 使用统一目录 |
| `skills/workflow-code-generation/SKILL.md` | 待修改 | 统一 Tasks 路径和知识影响检查 |
| `skills/workflow-test-generation/SKILL.md` | 待修改 | 使用统一 Change 和长期 Specs |
| `skills/workflow-verification/SKILL.md` | 待修改 | 更新 Spec Drift 路径和知识同步门禁 |
| `skills/troubleshooting/SKILL.md` | 待修改 | 从 `openspec/issues/` 和公共 Issues 定向查询 |
| `agents/codebase-researcher.md` | 待修改 | 将代码派生知识写入端、域和模块目录 |
| `scripts/workflow_control.py` | 待修改 | Tooling 状态改用统一 `tasks.md` 路径 |
| `scripts/test_workflow_control.py` | 待修改 | 覆盖统一路径、锁、恢复和知识任务状态 |

### 跨项目公共知识库

| 位置 | 操作 | 说明 |
| --- | --- | --- |
| `E:/work/shared-knowledge-base/index.md` | 待修改 | 收紧 `changes/` 职责，停用 `projects/` 日常入口 |
| `E:/work/shared-knowledge-base/scripts/lint_kb.py` | 待修改 | 增加公共作用域、边界和索引检查 |
| `E:/work/shared-knowledge-base/projects/` | 待标记废弃 | 不直接删除，停止新增项目指针 |
| `E:/work/shared-knowledge-base/domains/` | 待治理 | 修复元数据债务并执行真实查询验收 |

## 任务列表

### Task 1：冻结统一知识与 Change 契约

- 状态：待执行
- 目标：使目录、事实权威、冲突处理、Delta、Archive 和公共晋升规则成为当前框架合同。
- 主要文件：
    - `docs/design-docs/framework-unification/spec.md`
    - `docs/design-docs/knowledge-management/spec.md`
    - `docs/adr/002-unify-project-knowledge-layout.md`
- 验证：
    - [ ] 不再保留「禁止任何 `openspec/specs/`」的绝对规则
    - [ ] 明确长期 Specs 只是辅助知识，不是代码事实源
    - [ ] 明确两个 Profile 统一 Artifact、保留独立生命周期
    - [ ] 明确知识冲突不得静默处理

### Task 2：改造 `project-init` 与安装归属

- 状态：待执行
- depends_on: [Task 1]
- 目标：为两种 Profile 创建同一最小 `openspec/` 骨架，并支持项目内或外部私有目录存储。
- 验证：
    - [ ] Production 和 Tooling 都能安装 `project-init`
    - [ ] 项目内模式创建统一最小骨架
    - [ ] 外置模式验证链接、版本管理和恢复策略
    - [ ] 不覆盖已有目录、链接或未跟踪内容
    - [ ] 公共知识库接线与项目知识存储分开询问

### Task 3：重写 Shared `project-knowledge`

- 状态：待执行
- depends_on: [Task 2]
- 目标：让两个 Profile 共用读取、写入、冲突、归档和晋升规则。
- 验证：
    - [ ] 所有任务类型都有读取路由
    - [ ] 所有知识类型都有唯一建议位置
    - [ ] 未确认候选不能进入公共库
    - [ ] 知识与代码冲突输出双方证据
    - [ ] 自动内容禁止覆盖 `custom/`

### Task 4：改造 Production

- 状态：待执行
- depends_on: [Task 3]
- 目标：将项目长期 Specs、知识读取和归档同步接入 OPSX 生命周期。
- 验证：
    - [ ] Requirements 创建可映射到长期 Specs 的 Delta
    - [ ] Design、Code、Test 阶段按任务类型读取知识
    - [ ] Archive 校验实际 Diff、Delta、索引和知识同步
    - [ ] 未完成知识同步时 Archive 失败
    - [ ] Production Review 和人工门禁策略保持不变

### Task 5：改造 Tooling

- 状态：待执行
- depends_on: [Task 3]
- 目标：让 Tooling 改用 `openspec/changes/`，同时保留其自主执行和并行控制模型。
- 验证：
    - [ ] Fast-Path、Quick 和 Standard 路由正常
    - [ ] Standard Spec 与 Tasks 使用统一路径
    - [ ] DAG、Waves、Worktree、锁、失败隔离和恢复保持正常
    - [ ] Tooling 不恢复逐 Task LLM Review
    - [ ] 交付时执行统一知识影响检查

### Task 6：统一验证器、模板和测试

- 状态：待执行
- depends_on: [Task 4, Task 5]
- 目标：用确定性检查锁定统一目录和知识生命周期。
- 验证：
    - [ ] Proposal 和 Tasks 模板包含知识影响与知识同步章节
    - [ ] Delta 目标路径可机器验证
    - [ ] Profile 合同测试防止 Artifact 再次分叉
    - [ ] Spec Drift 检查覆盖 Change、长期 Specs 和无需更新理由
    - [ ] 既有 Verify、Review 和安装测试无回归

### Task 7：迁移跨项目公共知识库

- 状态：待执行
- depends_on: [Task 3]
- 目标：让公共库只保存经过批准的跨项目知识和自身治理记录。
- 验证：
    - [ ] `projects/` 不再出现在日常索引入口
    - [ ] 公共 `changes/` 明确禁止项目候选
    - [ ] 晋升条目包含状态、证据、适用与不适用范围
    - [ ] 修复现有 9 个条目元数据债务
    - [ ] 公共索引不会链接项目私有正文

### Task 8：迁移现有项目与历史文档

- 状态：待执行
- depends_on: [Task 4, Task 5, Task 6]
- 目标：建立旧目录到统一 `openspec/` 的可验证迁移路径。
- 验证：
    - [ ] 迁移前生成逐文件映射和引用清单
    - [ ] 旧目录先标记 `Superseded`，不直接删除
    - [ ] 历史 Change、ADR、Issue 和快照保留来源与引用
    - [ ] 所有 Workflow 已停止写入旧 `docs/design-docs/` 路径
    - [ ] 用户明确授权后才处理废弃未跟踪产物

### Task 9：端到端验收

- 状态：待执行
- depends_on: [Task 7, Task 8]
- 目标：用真实项目和真实问题证明方案可用。
- 验证：
    - [ ] Production 完整 Change 成功归档并同步长期 Specs
    - [ ] Tooling Standard Change 成功归档并同步长期 Specs
    - [ ] 外置链接模式在项目路径透明可读且能检测失效
    - [ ] 知识与代码冲突被显式报告
    - [ ] 项目问题不会检索到其他项目私有正文
    - [ ] 一条项目知识经确认后成功晋升公共库
    - [ ] Markdown、链接、Skill 图、Profile 合同和自动化测试全部通过

## Spec 覆盖映射

| Spec 章节 | 任务 |
| --- | --- |
| 1～3 背景、目标和原则 | Task 1 |
| 4～6 目录和存储 | Task 2、8 |
| 7～10 读写、Delta 和新鲜度 | Task 3～6 |
| 11 公共知识库 | Task 7 |
| 12～14 Profile、初始化和工作流 | Task 2～6 |
| 15 机器验证 | Task 6、9 |
| 16 迁移 | Task 7、8 |
| 17 验收 | Task 9 |

