# Proposal: 将 CLI 工具设计纳入 Shared Core（Quick Draft）

**作者**：Codex
**日期**：2026-07-19
**变更**：add-bp-cli-tool-design
**状态**：Archived

---

## 1. 问题与目标

### 问题

现有 `E:/work/linux/.codex/skills/cli-tool-design` 已沉淀 CLI、部署脚本和自动化命令的通用设计原则，但本框架尚未将这些原则作为 `bp-*` 最佳实践分发，也未在 Production 与 Tooling 的代码生成入口中按场景加载。

### 目标

- 将来源 Skill 适配为 `bp-cli-tool-design`，纳入框架 Shared Core。
- 让 Production 与 Tooling 在实现或修改 CLI、部署脚本、运维脚本及自动化命令时加载该最佳实践。
- 通过安装器契约和测试证明两个 Profile 都会安装该 Skill。

### 非目标

- 不新增独立 Command。
- 不提供 CLI 项目脚手架或代码生成器。
- 不改变 Production 与 Tooling 的生命周期、审批点或 Review 策略。
- 不把来源仓库的项目级语言规则复制进本框架 Skill。

### 验收标准

- `skills/bp-cli-tool-design/` 通过 Skill 结构校验和 Markdown 自检。
- `opsx-code-generation` 与 `workflow-code-generation` 都包含 CLI 场景的按需加载规则。
- 安装器把 `bp-cli-tool-design` 作为 Shared Core 安装到两个 Profile。
- 安装器测试、Profile 契约测试和 Skill 引用图检查通过。

## 2. 设计方案

### 2.1 整体方案

采用「薄 `SKILL.md` + 单层参考文档」结构，将通用 CLI 设计原则保存在 `skills/bp-cli-tool-design/`。安装器把它加入 Shared Core 白名单，两个代码生成 Workflow 只在 CLI 和自动化脚本场景按需加载。

### 2.2 核心组件

- `bp-cli-tool-design`：保存触发边界、执行流程、硬性底线和详细设计原则。
- Production / Tooling 代码生成 Skill：负责按任务类型加载最佳实践。
- 安装器与契约测试：保证两个 Profile 都能获得该 Shared Core Skill。

### 2.3 关键权衡

- 选择 Shared Core，而不是 Profile 或 Pack：该知识与生命周期无关，Production 与 Tooling 都适用。
- 选择适配后引入，而不是原样复制：统一 `bp-*` 命名、中文元数据和本仓库引用目录约定，并移除来源项目专属规则。
- 不新增 Command：最佳实践由 Workflow 按场景加载，避免增加与生命周期无关的用户入口。
- 不引入脚手架：本次只解决知识分发和执行约束，避免扩大范围。

## 3. 知识影响

- 新增长期最佳实践：`skills/bp-cli-tool-design/`。
- 更新 Shared Core 安装事实：`scripts/install_agentic_framework.py` 及其测试。
- `openspec/specs/backend/engineering/tech/framework-unification.md` 已定义通用 `bp-*` 属于 Shared Core，无需改变现有架构决策。

## 4. 参考资料

- `E:/work/linux/.codex/skills/cli-tool-design/SKILL.md`
- `E:/work/linux/.codex/skills/cli-tool-design/references/cli-tool-design-principles.md`
- `skills/bp-skill-authoring/SKILL.md`
- `openspec/specs/backend/engineering/tech/framework-unification.md`
