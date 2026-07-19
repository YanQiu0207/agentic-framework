# 项目知识库与跨项目公共知识库统一方案

**作者**：Codex
**日期**：2026-07-19
**状态**：Archived（已实施并通过验收）

---

## 1. 背景

当前框架存在以下问题：

- Production 使用 `openspec/changes/<change>/`，Tooling 使用 `docs/design-docs/<module>/<feature>/`，两个 Profile 的项目产物目录不同。
- 当前 Production 只保留 Change，不维护项目长期 Specs，归档时也不把 Change 中的增量知识同步回长期知识。
- 当前 `project-knowledge` 以 `docs/adr/`、`docs/arch-snapshots/`、`docs/design-docs/` 和 `docs/issues/` 分桶，与 Production 的 OpenSpec 类结构没有统一。
- 项目专属知识与跨项目公共知识的作用域边界不够严格，未确认候选仍可能进入公共库的 `changes/`。
- 知识读取主要依赖常驻指令，缺少覆盖需求、设计、编码、测试、Review、排障和归档阶段的确定性读写路由。

本方案参考以下两篇实践资料，但不照搬其中的团队规模、固定文档数量和完整自动化管线：

- `E:/work/my-ai-resource/notes/从AI_Coding到Harness_Engineering的端到端工程开发实践.md`
- `E:/work/my-ai-resource/notes/开启Harness_Engineering探索之旅.md`

第一篇提供「总览 → 业务域 → 服务」三级知识组织、自动生成与人工补充分离、渐进式检索和 Git 版本新鲜度管理，见第 83～186 行。第二篇提供「项目长期 Specs + 单次 Changes」、Delta Spec 增量合并、两级查找和归档知识同步，见第 239～256、382～443 行。

## 2. 目标与非目标

### 2.1 目标

- Production 和 Tooling 使用同一套项目知识目录与 Change Artifact 协议。
- 项目知识库保持项目作用域，不被其他项目工作流主动检索。
- 项目知识库可以位于项目内，也可以位于外部私有目录并映射到项目路径。
- 跨项目公共知识库只保存经过泛化、脱敏、证据审查和用户确认的通用知识。
- LLM 能确定何时读取知识、读取哪些入口，以及交付时把知识写入哪个位置。
- 知识仅用于辅助理解；与代码、Schema、配置、测试或运行证据冲突时必须显式报告。
- Change 完成时只把值得长期保留的 Delta 同步到项目长期 Specs，避免完整复制任务文档。

### 2.2 非目标

- 不把项目专属知识集中到跨项目公共目录。
- 不让项目知识或公共知识替代代码事实源。
- 不在首版引入向量数据库、RAG、知识图谱或复杂多 Agent 编排。
- 不自动保存全部会话记录。
- 不自动把项目知识写入公共知识库。
- 不强制为每个项目生成全部前端、后端、业务域和服务文档。
- 不在未积累真实查询数据前固化严格的文件数或行数预算。

## 3. 核心原则

### 3.1 知识是辅助上下文

| 信息 | 定位 |
| --- | --- |
| 用户当前明确要求 | 当前任务目标 |
| 活跃 Change | 本次变更契约 |
| 代码、Schema、配置、测试和运行证据 | 当前系统事实 |
| 项目长期 Specs | 辅助理解项目背景、规则和历史上下文 |
| 项目 Issues | 辅助排障 |
| 跨项目公共知识 | 通用参考 |
| Archive | 历史证据，不代表当前状态 |

知识与代码发生冲突时，LLM 必须同时展示知识结论、代码证据、版本信息和不确定性，不得静默采用任意一方。

### 3.2 项目知识与公共知识严格分域

- 项目知识位于当前项目的 `openspec/`，只由当前项目工作流主动检索。
- 跨项目公共知识位于独立仓库，只保存跨项目仍然成立的结论。
- 公共索引禁止链接项目私有正文。
- 未完成用户确认、泛化和脱敏的候选不得写入公共仓库，包括公共库的临时目录。

「项目私有」默认表示不被公共索引收录、不被其他项目工作流主动检索；它不等于文件系统安全隔离。真正的保密需求需要额外的文件权限或执行环境隔离。

### 3.3 统一 Artifact，不统一生命周期

Production 和 Tooling 共享目录、文件语义和知识同步契约，但继续保留不同的审批、Review、DAG、Worktree 和失败恢复策略。

### 3.4 自动知识与人工知识分离

- 自动生成内容记录代码版本，可以重新生成。
- 人工知识保存在 `custom/`，自动任务不得覆盖。
- 自动更新采用最小修改，并保留人工补充。

### 3.5 渐进式读取

每个任务先读取小型根索引，再按问题类型定位业务域、端、服务或公共主题。禁止默认加载整个知识库；受限范围内的 `grep` 可以作为索引未命中的兜底手段。

## 4. 项目知识库逻辑结构

项目内固定逻辑入口为 `<project>/openspec/`：

```text
openspec/
├── index.md
├── specs/
│   ├── index.md
│   ├── business/
│   │   ├── index.md
│   │   ├── glossary.md
│   │   └── <domain>/
│   │       ├── overview.md
│   │       ├── rules.md
│   │       ├── flows.md
│   │       └── custom/
│   ├── frontend/
│   │   ├── overview.md
│   │   ├── <domain>/
│   │   │   ├── meta.yaml
│   │   │   ├── custom/
│   │   │   └── <module>/
│   │   │       ├── overview.md
│   │   │       ├── interfaces.md
│   │   │       ├── architecture.md
│   │   │       ├── dependencies.md
│   │   │       ├── config.md
│   │   │       └── custom/
│   │   └── engineering/
│   │       ├── conventions/
│   │       ├── lib-usage/
│   │       └── tech/
│   ├── backend/
│   │   ├── overview.md
│   │   ├── <domain>/
│   │   │   ├── meta.yaml
│   │   │   ├── custom/
│   │   │   └── <service>/
│   │   │       ├── overview.md
│   │   │       ├── interfaces.md
│   │   │       ├── architecture.md
│   │   │       ├── dependencies.md
│   │   │       ├── storage.md
│   │   │       ├── config.md
│   │   │       └── custom/
│   │   └── engineering/
│   │       ├── conventions/
│   │       ├── lib-usage/
│   │       └── tech/
│   └── common/
│       ├── index.md
│       ├── protocols/
│       ├── data-models/
│       └── error-codes/
├── changes/
│   ├── <change-name>/
│   │   ├── proposal.md
│   │   ├── specs/
│   │   ├── design.md
│   │   └── tasks.md
│   └── archive/
└── issues/
    ├── index.md
    └── <issue>.md
```

`project-init` 默认只创建最小骨架：

```text
openspec/
├── index.md
├── specs/
│   └── index.md
├── changes/
│   └── archive/
└── issues/
    └── index.md
```

只有扫描项目后确认存在对应内容，或真实任务首次需要时，才创建 `business/`、`frontend/`、`backend/` 和 `common/`。

## 5. 目录职责

### 5.1 `openspec/index.md`

根索引只保存：

- 项目概述。
- 目录导航和关键词映射。
- 查询规则与写入规则。
- 活跃 Change 入口。
- 跨项目公共知识库入口。

它不保存大段知识正文。

### 5.2 `specs/business/`

保存与具体前后端实现无关的项目业务上下文：

- `glossary.md`：业务术语。
- `<domain>/overview.md`：业务域范围和能力。
- `<domain>/rules.md`：业务规则和不变量。
- `<domain>/flows.md`：跨模块业务流程。
- `<domain>/custom/`：人工补充的背景、例外和历史约束。

### 5.3 `specs/frontend/` 与 `specs/backend/`

按「端 → 业务域 → 模块或服务」组织代码派生知识和人工知识：

- 服务根目录的结构化 Markdown 默认是代码派生缓存。
- `custom/` 保存人工背景、约束、决策和踩坑。
- `engineering/` 保存当前项目在该端内部复用的开发规范、库指南和技术专题。

第一篇资料使用 `backend/common/` 表示后端跨业务域工程知识，第二篇使用顶层 `common/` 表示跨端协议。为避免同名不同义，本方案将前者改名为端内 `engineering/`，将后者保留为顶层 `common/`。

### 5.4 `specs/common/`

保存当前项目内跨端或跨模块共同使用的契约语义：

- `protocols/`：协议及其业务语义。
- `data-models/`：共享数据模型及约束。
- `error-codes/`：统一错误码语义。

若结构已经由 Proto、OpenAPI 或 Schema 定义，结构事实以源文件为准，Markdown 只补充源文件无法表达的业务语义和使用边界。

### 5.5 `changes/`

保存单次变更的任务契约：

- `proposal.md`：为什么改、改什么、非目标和验收标准。
- `specs/`：对长期 Specs 的 Delta。
- `design.md`：设计方案、权衡和风险。
- `tasks.md`：任务、验证和知识同步状态。

归档状态由目录位置表达：活跃 Change 位于 `changes/<change>/`，完成后移动到 `changes/archive/YYYY-MM-DD-<change>/`。

### 5.6 `issues/`

只保存已经验证的项目故障：现象、根因、修复、适用边界和证据。未确认猜测留在 Change 或排障记录中，不得进入 `issues/`。

## 6. 项目知识库存储方式

`project-init` 需要把存储位置与公共知识库接线拆成两个独立问题。

### 6.1 项目内存储

默认推荐直接创建：

```text
<project>/openspec/
```

正文随项目版本库提交，可以和代码一起 Review、迁移和回滚。

### 6.2 外部私有目录加链接

用户可以指定外部私有目录，然后将其映射为：

```text
<project>/openspec/
```

外置模式必须额外确认：

- 外部目录不位于跨项目公共知识库下。
- 外部正文由项目 Git、独立 Git 或明确的备份机制管理。
- 从 `<project>/openspec/index.md` 可以读取正文。
- 项目迁移到其他机器后的链接恢复方式已明确。
- 链接失效时初始化和验证必须失败，不得报告成功。

`project-init` 不得覆盖已有真实目录、链接或未跟踪内容。

## 7. 知识读取机制

### 7.1 通用入口

所有 Coding Agent 开始处理项目任务时，先读取 `openspec/index.md`，再按问题类型定位相关知识。根索引保持精简，不要求默认读取全部条目。

### 7.2 按任务类型路由

| 任务类型 | 优先读取 |
| --- | --- |
| 需求澄清 | `specs/business/`、相关历史 Change、相关 Issues |
| 系统设计 | 当前 Change、相关业务域、`specs/common/`、相关模块 `custom/`、相关 Issues |
| 编码实现 | 当前 Change、相关模块 `custom/constraints.md` 和 `custom/pitfalls.md`，然后读取代码 |
| 测试生成 | 当前 Change 验收条件、业务规则、共享契约和相关 Issues |
| Code Review | 当前 Change、相关业务规则、共享契约、模块约束和代码 Diff |
| 故障排查 | 项目 Issues、模块 `custom/pitfalls.md`、代码与运行证据，必要时再查公共 Issues |
| 交付归档 | 当前 Change、实际 Diff、测试证据和知识影响清单 |

### 7.3 公共知识查询时机

以下情况可以查询跨项目公共知识库：

- 用户明确要求。
- 设计阶段需要通用工程方法或工具经验。
- 项目知识库没有相关记录。
- 问题明显属于语言、框架、工具、网络或操作系统。
- 准备选择跨项目复用的技术方案。

当前项目的业务字段、接口行为、历史决策、内部部署和数据规则不得只靠公共知识回答。

### 7.4 冲突处理

知识与代码冲突时必须输出：

- 知识文件及其结论。
- 代码、Schema、配置、测试或运行证据。
- 知识记录的 `source_ref` 与当前版本。
- 冲突类型和仍然存在的不确定性。
- 建议的下一步：更新知识、修正代码、更新 Change 或继续调查。

未确认原因前，不得声称代码必然错误或知识必然过期，也不得静默修改任意一方。

## 8. 知识写入路由

| 知识内容 | 项目内目标 |
| --- | --- |
| 项目概述与关键入口 | `openspec/index.md` |
| 业务术语 | `specs/business/glossary.md` |
| 业务域概述 | `specs/business/<domain>/overview.md` |
| 业务规则与不变量 | `specs/business/<domain>/rules.md` |
| 跨模块业务流程 | `specs/business/<domain>/flows.md` |
| 前端模块代码事实 | `specs/frontend/<domain>/<module>/*.md` |
| 前端人工背景与约束 | `specs/frontend/<domain>/<module>/custom/` |
| 后端服务代码事实 | `specs/backend/<domain>/<service>/*.md` |
| 后端人工背景与约束 | `specs/backend/<domain>/<service>/custom/` |
| 前后端共享协议与数据模型 | `specs/common/protocols/`、`specs/common/data-models/` |
| 统一错误码语义 | `specs/common/error-codes/` |
| 端内项目工程规范 | `specs/frontend/engineering/` 或 `specs/backend/engineering/` |
| 单次需求、设计和任务 | `changes/<change>/` |
| 已完成历史 Change | `changes/archive/` |
| 已验证项目故障 | `issues/` |
| 跨项目可复用方法 | 公共库 `domains/`，须先完成晋升流程 |
| 跨项目可复用故障 | 公共库 `issues/`，须先完成晋升流程 |

## 9. Delta 与归档机制

### 9.1 Change 期间

活跃 Change 先在自身 `specs/` 中记录 Delta，不直接把未确认结论写入长期 Specs。Delta 目录镜像长期 Specs 的相对路径：

```text
openspec/changes/add-refund/specs/common/protocols/refund-api/spec.md
    ↓ 归档时合并
openspec/specs/common/protocols/refund-api/
```

Delta 使用 `ADDED`、`MODIFIED`、`REMOVED` 和 `RENAMED` 表达变化。

### 9.2 归档门禁

归档前必须执行：

1. 对照 Git Diff、测试和运行证据核对实际结果。
2. 检查代码、活跃 Change 与长期知识是否冲突。
3. 只把值得长期保留且已经验证的 Delta 合并到 `openspec/specs/`。
4. 更新相关索引和代码派生文档的版本元数据。
5. 把已验证故障写入 `issues/`。
6. 生成跨项目知识候选，但不自动写公共库。
7. 完成机器校验后移动 Change。

以下内容不合并到长期 Specs：

- 临时实现细节。
- 一次性迁移步骤。
- 已被最终实现推翻的草案。
- 未确认的故障猜测。
- 仅用于本次执行的中间状态。

## 10. 自动生成与新鲜度

### 10.1 `meta.yaml`

端或业务域索引使用 `meta.yaml` 记录代码派生知识的来源：

```yaml
services:
    refund-service:
        source_ref: git:<commit>
        source_paths:
            - services/refund/
        generated_at: YYYY-MM-DD
        status: active
```

### 10.2 自动生成文件

`overview.md`、`interfaces.md`、`architecture.md`、`dependencies.md`、`storage.md` 和 `config.md` 可以由代码或 Schema 生成，但必须：

- 标记来源版本和相关路径。
- 根据相关路径的实际变化判断是否需要复核，不能只因仓库 HEAD 变化就全部失效。
- 修改前读取现有文件，采用最小更新。
- 不覆盖任何 `custom/` 内容。

### 10.3 人工知识

`custom/` 中的内容只能增量修改。人工知识与代码冲突时必须报告，不得自动覆盖；确认后再更新内容、适用范围或状态。

## 11. 跨项目公共知识库

公共库保持独立：

```text
shared-knowledge-base/
├── index.md
├── domains/
├── issues/
├── sources/
├── changes/
└── archives/
```

- `domains/` 保存跨项目方法、概念和实践。
- `issues/` 保存通用且已验证的工具、框架、语言、网络或操作系统问题。
- `sources/` 保存允许跨项目消费的原始资料或来源索引。
- `changes/` 只记录公共库自身治理，不保存任何项目知识候选。
- `archives/` 只用于整体退役主题，首版不作为日常流程重点。
- 原有 `projects/` 停止新增入口，迁移时先标记废弃，不直接删除。

### 11.1 晋升流程

```text
项目知识或 Issue
    → 交付报告列出候选
    → 用户确认允许晋升
    → 去除项目名、内部路径、内部接口和业务数据
    → 提炼通用机制、适用范围和不适用范围
    → 检查公共库是否已有权威条目
    → 标记证据等级
    → 写入公共 domains/ 或 issues/
    → 更新公共索引
```

证据等级：

- `provisional`：只有一个真实案例，边界已经写明。
- `verified`：有官方依据和真实验证，或多个独立案例一致。
- `uncertain`：证据冲突或无法复核。
- `deprecated`：已经被新证据取代。

只有 `verified` 可以默认作为建议；其他状态必须同时说明限制。

## 12. 双 Profile 统一

两个 Profile 使用相同目录：

```text
openspec/
├── specs/
├── changes/
└── issues/
```

| 能力 | Production | Tooling |
| --- | --- | --- |
| Change 目录与文件语义 | 相同 | 相同 |
| Delta Spec | 相同 | 相同 |
| 项目长期 Specs | 相同 | 相同 |
| 知识读取与归档门禁 | 强制 | 强制 |
| Task Review | 逐 Task 风险分档 | 当前路径全部任务完成后一次 |
| DAG、Worktree 和失败恢复 | 按 Production 策略 | 中大型任务使用 Tooling 控制器 |
| Machine Verification | 强制 | Standard 及以上强制 |

原「禁止中央 `openspec/specs/`」和「Archive 只移动 Change」的规则已由本方案替代。长期 Specs 是辅助知识，不是当前实现事实源；相关 Skill、脚本和迁移任务按 `tasks.md` 分阶段实施。

## 13. `project-init` 契约

`project-init` 应执行：

1. 选择版本管理模式。
2. 选择项目 Profile：Production 或 Tooling。
3. 选择项目知识库存储方式：项目内，或外部私有目录加链接。
4. 确认外置正文的版本管理或备份方式。
5. 创建统一最小 `openspec/` 骨架。
6. 将项目知识入口和冲突规则写入 `AGENTS.md`。
7. 单独询问是否接入跨项目公共知识库。
8. 验证项目索引、目录链接和公共索引可读取。
9. 仅提交本次创建或修改的项目文件。

`project-init` 需要从 Tooling-only Pack 调整为两种 Profile 均可安装的公共 Pack。

## 14. 工作流接线

### 14.1 Shared Core

`project-knowledge` 调整为两种 Profile 共用的知识路由与归档规范，负责：

- 任务类型到读取入口的路由。
- 知识内容到写入位置的路由。
- 知识与代码冲突报告。
- 归档前知识影响检查。
- 公共知识晋升候选与用户确认。

### 14.2 Production

- `opsx-requirements-clarification`：需求前读取项目索引，Change-local Delta 镜像长期 Specs 路径。
- `opsx-system-design`：设计前读取相关业务、公共契约、模块人工知识和 Issues。
- `opsx-code-generation`：实现前读取当前 Change 与相关模块约束。
- `opsx-test-generation`：使用验收条件、业务规则、契约和 Issues 生成测试。
- `opsx-archive`：执行知识影响检查、Delta 合并和索引更新后再移动目录。

### 14.3 Tooling

- `workflow-requirements-clarification`、`workflow-system-design` 和 `workflow-quick-design` 改用 `openspec/changes/`。
- `workflow-code-generation` 和 `workflow_control.py` 继续保留 DAG、Waves、Worktree、锁和恢复语义，但状态写入统一的 `tasks.md`。
- `workflow-test-generation` 和 `workflow-verification` 使用相同的知识、Change 和 Spec Drift 路径。
- Tooling 的 Fast-Path 可以不创建 Change，但必须说明为什么没有长期知识影响。

## 15. 机器验证

### 15.1 项目知识校验

- `openspec/index.md`、`openspec/specs/index.md` 和 `openspec/issues/index.md` 存在。
- 索引链接目标存在。
- 活跃 Change 文件结构与 Profile 路径要求一致。
- Delta 相对路径可以映射到长期 Specs。
- 自动生成文档有 `source_ref`、`source_paths` 和生成时间。
- 知识影响命中时存在同步任务或明确的无需更新理由。
- 归档前知识同步任务已经完成。

### 15.2 公共知识校验

- 公共条目不得包含项目作用域正文。
- 公共 `changes/` 不得保存项目候选。
- 公共条目包含来源、状态、适用范围和不适用范围。
- 公共索引不得链接项目私有目录。
- `scope` 字段只作结构提示，不能替代人工脱敏和泛化检查。

检索文件数和行数先作为观测指标，不作为首版硬失败条件；积累真实问题数据后再校准预算。

## 16. 迁移方案

### 16.1 项目目录迁移

| 旧位置 | 新位置 |
| --- | --- |
| `docs/design-docs/<module>/<feature>/` | `openspec/changes/<change>/` 或 Archive |
| `docs/adr/` | 按作用域合并到相关 Specs 的 `custom/`、`engineering/tech/` 或保留历史引用 |
| `docs/arch-snapshots/<module>/` | 对应端、业务域和模块的代码派生文档 |
| `docs/issues/` | `openspec/issues/` |

迁移必须先建立映射和引用检查，不得直接删除旧目录。旧文档先标记 `Superseded` 或保留跳转入口，确认所有引用和工作流已切换后再由用户决定是否移除。

### 16.2 历史方案迁移

`docs/tooling/09-personal-knowledge-base-plan.md` 保留为历史研究证据，标记为被本方案取代，不继续承担当前规范和实施状态。

### 16.3 公共库迁移

- 保留现有 `domains/`、`issues/`、`sources/`、`changes/` 和 `archives/`。
- `projects/` 停止新增并从根索引日常入口移除，但不直接删除现有目录。
- 清理公共 `changes/` 的职责描述，限制为公共库治理记录。
- 修复现有条目元数据债务后，再进行真实问题验收。

## 17. 验收标准

### 17.1 项目知识库

- Production 和 Tooling 可以在同一项目目录上运行，不需要迁移 Change Artifact。
- 需求、设计、编码、测试、Review、排障和归档阶段都有明确读取入口。
- 给定一条知识，Agent 能根据路由表确定唯一目标位置。
- 代码与知识冲突时，Agent 会展示双方证据而不是静默选择。
- Change 归档后，值得长期保留的 Delta 已进入长期 Specs，不值得保留的内容只留在 Archive。
- 外置知识库从项目 `openspec/` 路径透明可读，链接失效能够被检测。

### 17.2 跨项目公共知识库

- 公共搜索不会命中其他项目的私有正文。
- 未经用户确认的候选不会进入公共 Git 历史。
- 公共条目能回答结论、证据、适用边界和状态。
- 公共知识与项目代码冲突时只作为参考，Agent 会报告冲突。

### 17.3 真实问题验收

至少使用以下场景验证：

1. 查询项目业务术语和规则。
2. 查询某个前端模块或后端服务的接口、依赖和人工约束。
3. 使用历史 Issue 辅助排障，并回到代码和日志验证。
4. 从 Change Delta 更新长期 Specs。
5. 发现知识与代码冲突并输出证据。
6. 将一条项目经验泛化为公共知识，并证明其他项目不会读到原始私有正文。

## 18. 风险与权衡

| 风险 | 处理 |
| --- | --- |
| 长期 Specs 与代码漂移 | 明确知识仅辅助理解；代码派生文档记录相关路径和版本；冲突强制报告 |
| 恢复 `openspec/specs/` 造成双事实源 | 重新定义为辅助知识，不作为当前实现事实源；活跃 Change 仍是本次任务契约 |
| Delta 合并增加归档成本 | 只同步长期价值内容，由机器检查结构、用户确认语义 |
| 外置链接失效或无法迁移 | 初始化时明确版本管理和恢复方式，交付前验证链接 |
| 前端、后端目录不适用所有项目 | 最小骨架不创建这些目录，按真实项目类型和内容增量创建 |
| 公共知识误收项目内容 | 候选留在项目内，用户确认后执行泛化、脱敏和人工检查 |
| 索引层级过多 | 小项目允许根索引直接指向条目，规模增长后再增加域级索引 |

## 19. 参考与决策记录

- 参考资料一：`E:/work/my-ai-resource/notes/从AI_Coding到Harness_Engineering的端到端工程开发实践.md`，重点见第 41～186、380～427 行。
- 参考资料二：`E:/work/my-ai-resource/notes/开启Harness_Engineering探索之旅.md`，重点见第 239～256、365～445、508～585 行。
- 当前双 Profile 合同：`docs/design-docs/framework-unification/spec.md`。
- 当前 Production Change 契约：`skills/opsx-*/SKILL.md`。
- 当前 Tooling 项目知识契约：`skills/project-knowledge/SKILL.md`。
- 架构决策：[ADR 002](../../adr/002-unify-project-knowledge-layout.md)。
