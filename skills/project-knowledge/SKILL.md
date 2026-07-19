---
name: project-knowledge
description: Production 与 Tooling 共用的项目知识路由与归档规范。定义 openspec 项目知识的渐进读取、唯一建议写入位置、代码冲突报告、Change Delta 同步、公共知识晋升，以及交付前 intent 沉淀检查。当任务需要读取或更新项目知识、归档 Change、沉淀已验证故障、判断知识去向或识别跨项目候选时使用。
---

> 输出一行：`Using project-knowledge`

# 项目知识管理规范

本 Skill 是 Production 与 Tooling 的 Shared Core 合同。两个 Profile 共用知识目录、文件语义和归档规则；各自的审批、Review、DAG、Worktree 与失败恢复策略保持独立。

## 1. 不可违反的边界

1. **知识只辅助理解**：项目长期 Specs、Issues、Archive 和跨项目公共知识都不是当前实现的事实源。
2. **当前事实必须核实**：模块、接口、数据流和运行行为以代码、Schema、配置、测试与运行证据为准。
3. **活跃 Change 是本次任务契约**：实现和验收必须对照当前 `openspec/changes/<change>/`；它不是普通知识。
4. **冲突必须显式报告**：知识与当前事实不一致时，同时展示双方证据和不确定性，不得静默选择、覆盖或宣布任意一方错误。
5. **项目知识保持项目作用域**：其他项目不得主动检索当前项目的 `openspec/`。
6. **公共知识不得自动写入**：候选只保留在当前项目或交付报告；只有用户明确确认后才能晋升。
7. **人工知识不可被自动覆盖**：代码或 Schema 派生任务不得覆盖任何 `custom/` 内容。

## 2. 统一目录

项目知识的固定逻辑入口是 `<project>/openspec/`。正文可以位于项目内，也可以位于外部私有目录并链接到该路径；工作流只使用逻辑入口。

```text
openspec/
├── index.md
├── specs/
│   ├── index.md
│   ├── business/
│   ├── frontend/
│   ├── backend/
│   └── common/
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

`business/`、`frontend/`、`backend/` 和 `common/` 按需创建，不为满足模板制造空目录。

## 3. 什么时候读取

### 3.1 固定入口与渐进加载

处理项目任务时：

1. 先读取 `openspec/index.md`。
2. 按任务类型读取相关分类索引或活跃 Change。
3. 只加载直接相关的业务域、端、模块、服务、契约或 Issue。
4. 索引未命中时，才在 `openspec/` 的受限子目录内使用 `grep`。
5. 涉及当前实现时回到代码与运行证据核实。

禁止默认扫描整个 `openspec/` 或整个跨项目公共知识库。

### 3.2 任务读取路由

| 任务类型 | 优先读取 |
| --- | --- |
| 需求澄清 | `openspec/index.md`、相关 `specs/business/`、相似历史 Change、相关 Issues |
| 系统设计 | 当前 Change、相关业务域、`specs/common/`、相关模块或服务的 `custom/`、相关 Issues |
| 编码实现 | 当前 Change、相关模块或服务的 `custom/constraints.md` 与 `custom/pitfalls.md`，然后读取代码 |
| 测试生成 | 当前 Change 的验收条件、业务规则、共享契约、相关 Issues |
| Code Review | 当前 Change、相关业务规则、共享契约、模块约束、代码 Diff |
| 故障排查 | 项目 Issues、相关 `custom/pitfalls.md`、代码、日志和配置；必要时再查公共 Issues |
| 交付归档 | 当前 Change、实际 Diff、测试与运行证据、知识影响清单 |

### 3.3 什么时候查询公共知识

仅在以下情况查询：

- 用户明确要求。
- 设计需要通用工程方法或工具经验。
- 项目知识没有相关记录。
- 问题明显属于语言、框架、工具、网络或操作系统。
- 准备选择可跨项目复用的技术方案。

不得只凭公共知识回答当前项目的业务字段、接口实际行为、历史决策、内部部署或数据规则。

## 4. 知识与代码冲突

发现冲突后停止静默归并，输出以下证据：

```markdown
## 知识与代码冲突

- 知识文件：`<path>`
- 知识结论：<原结论摘要>
- 知识版本：`source_ref: <value>`；缺失时写「未记录」
- 当前证据：`<code/schema/config/test/log path:line>`
- 当前现状：<证据所显示的行为>
- 冲突类型：自动知识可能过期 / 人工知识与实现不一致 / Change 与实现不一致 / 公共建议不适用
- 不确定性：<为什么暂时不能判断谁需要修改>
- 下一步：更新知识 / 修正代码 / 更新 Change / 继续调查，请用户确认
```

处理规则：

- 自动生成知识与代码冲突：先比较 `source_ref`、`source_paths` 和相关 Diff；可以判断「可能过期」，不能仅因仓库 HEAD 不同就断定失效。
- `custom/`、业务规则或共享契约与代码冲突：不得自动判断谁错，也不得自动修改任意一方。
- 活跃 Change 与实现冲突：实现阶段按任务继续推进；验证或交付阶段未满足契约时不得宣布完成。
- 公共知识与项目实现冲突：公共知识只作参考，不得据此擅自重构项目。

## 5. 唯一建议写入位置

同一条知识先按下表选择一个主位置，其他位置只建立引用，禁止复制多份正文。

| 知识内容 | 唯一建议位置 |
| --- | --- |
| 项目概述、关键入口与路由 | `openspec/index.md` |
| 业务术语 | `openspec/specs/business/glossary.md` |
| 业务域概述 | `openspec/specs/business/<domain>/overview.md` |
| 业务规则与不变量 | `openspec/specs/business/<domain>/rules.md` |
| 跨模块业务流程 | `openspec/specs/business/<domain>/flows.md` |
| 业务背景、例外和人工解释 | `openspec/specs/business/<domain>/custom/` |
| 前端模块代码派生事实 | `openspec/specs/frontend/<domain>/<module>/` 的对应生成文件 |
| 前端模块人工背景、约束和踩坑 | `openspec/specs/frontend/<domain>/<module>/custom/` |
| 后端服务代码派生事实 | `openspec/specs/backend/<domain>/<service>/` 的对应生成文件 |
| 后端服务人工背景、约束和踩坑 | `openspec/specs/backend/<domain>/<service>/custom/` |
| 前后端共享协议 | `openspec/specs/common/protocols/` |
| 共享数据模型 | `openspec/specs/common/data-models/` |
| 统一错误码语义 | `openspec/specs/common/error-codes/` |
| 端内项目工程规范 | `openspec/specs/frontend/engineering/` 或 `openspec/specs/backend/engineering/` |
| 单次需求、设计、任务和 Delta | `openspec/changes/<change>/` |
| 已完成历史 Change | `openspec/changes/archive/YYYY-MM-DD-<change>/` |
| 已验证项目故障 | `openspec/issues/<issue>.md` |
| 跨项目通用方法候选 | 当前 Change 的知识候选清单，或 Fast-Path 交付报告 |
| 跨项目通用故障候选 | 当前 Change 的知识候选清单，或 Fast-Path 交付报告 |

无法确定业务域、端或模块时，不得猜测目录；把候选留在当前 Change 或交付报告，列出待确认的归属。

## 6. 自动生成与人工知识

### 6.1 代码派生内容

模块或服务目录可按需包含：

```text
overview.md
interfaces.md
architecture.md
dependencies.md
storage.md
config.md
```

生成或更新时必须：

- 记录 `source_ref`、`source_paths` 和生成时间。
- 修改前读取旧文件，只更新相关内容。
- 依据相关路径的实际变化判断是否复核。
- 把 `custom/` 视为只允许人工增量编辑的边界。
- 不得覆盖、重写、移动或删除任何 `custom/` 文件。

### 6.2 人工知识

`custom/` 保存背景、约束、决策理由、例外和踩坑。修改前必须读取原文；与代码冲突时先按第 4 节报告，经确认后才能更新内容、适用范围或状态。

## 7. Change Delta 与 Archive

### 7.1 Change 期间

活跃 Change 优先写自身 `specs/` 中的 Delta，不直接把未验证结论写入长期 Specs。Delta 相对路径镜像 `openspec/specs/`：

```text
openspec/changes/add-refund/specs/common/protocols/refund-api/spec.md
    → openspec/specs/common/protocols/refund-api/
```

Delta 使用 `ADDED`、`MODIFIED`、`REMOVED` 和 `RENAMED` 表达变化。临时实现细节、一次性迁移步骤和未确认猜测只留在 Change。

### 7.2 归档前知识同步

归档前必须：

1. 对照实际 Diff、测试与运行证据核对 Change。
2. 检查代码、Change 和长期知识之间的冲突；未解决冲突不得伪装成确定结论合并。
3. 只把值得长期保留且已验证的 Delta 合并到 `openspec/specs/`。
4. 更新相关索引和代码派生知识的版本元数据。
5. 把已验证故障写入 `openspec/issues/`。
6. 生成跨项目候选，但只保留在项目内或交付报告。
7. 确认知识同步任务完成后，再将 Change 移入 `changes/archive/`。

不合并到长期 Specs 的内容：临时实现细节、一次性迁移步骤、被最终实现推翻的草案、未确认故障猜测和执行中间状态。

## 8. 跨项目公共知识晋升

### 8.1 候选的存放边界

- Standard Change：候选写入当前 Change 的「跨项目知识候选」章节或知识同步任务。
- Fast-Path：候选只写入交付报告。
- 未确认候选不得写入公共库的 `domains/`、`issues/`、`sources/`、`changes/` 或任何临时目录。
- 公共 `changes/` 只记录公共知识库自身治理，**禁止**保存项目知识候选。

### 8.2 晋升步骤

只有用户明确确认后，才执行：

1. 去除项目名、内部路径、内部接口和业务数据。
2. 提炼通用机制、适用范围与不适用范围。
3. 检查公共库是否已有权威条目。
4. 标注来源、证据等级和限制。
5. 通用方法写公共 `domains/`；通用且已验证的故障写公共 `issues/`。
6. 更新公共索引；公共条目不得反向链接项目私有正文。

## 9. 交付前 intent 沉淀检查（强制）

每次向用户宣布「完成」或「交付」前，无论是否创建 Change，都必须先扫描本次会话、Diff、测试和运行证据，生成知识 Delta 候选，再逐条完成下表。不得用一句「无需沉淀」代替逐项判断。

| 信号 | 命中后的唯一建议动作 |
| --- | --- |
| 做出不可逆或高影响架构决策 | 在当前 Change 的 `design.md` 记录完整决策；长期有效时同步到相关业务域、模块或服务的 `custom/decisions.md`，跨端工程决策写入对应 `engineering/tech/` |
| 放弃重要方案且理由值得保留 | 先写当前 Change 的备选方案与权衡；长期约束按上一行位置同步 |
| 引入性能、兼容或安全红线 | 写当前 Change；长期有效时同步到相关 `custom/constraints.md` 或端内 `engineering/` |
| 查证故障根因并完成验证 | 写入 `openspec/issues/<issue>.md`；未验证猜测只留当前 Change |
| 产生可跨项目复用的结论 | 只列入当前 Change 或交付报告；用户确认后再按第 8 节晋升 |
| 普通功能、配置或 Bug 修复，且没有长期知识影响 | 明确写「未命中」，不新增知识文件 |

逐项输出格式：

```markdown
## 交付前 intent 沉淀检查

- 不可逆或高影响架构决策：命中 → 已记录到 `<path>` / 未命中
- 放弃重要方案：命中 → 已记录到 `<path>` / 未命中
- 新增红线约束：命中 → 已记录到 `<path>` / 未命中
- 已验证故障根因：命中 → 已记录到 `<path>` / 未命中
- 跨项目知识候选：命中 → 已留在当前 Change 或交付报告，待用户确认 / 未命中
- 普通变更：命中 → 无长期知识影响 / 未命中
```

若命中但当前无法完成沉淀，在当前 `tasks.md` 新建「知识同步」任务并保持未完成；不得归档或宣布全部完成。

## 10. 与工作流的关系

- Production 的 `opsx-*` 和 Tooling 的 `workflow-*` 必须调用本 Skill 的同一读写路由。
- Tooling Fast-Path 可以不创建 Change，但必须完成知识影响检查，并说明为什么没有长期知识影响。
- Requirements、Design、Code、Test、Review、Troubleshooting 和 Archive 阶段分别按第 3 节读取，不得把公共知识当项目事实。
- Archive 必须执行第 7 节的同步门禁；只移动 Change、未完成知识同步的归档不合格。
- 工作流执行策略由各 Profile 自己定义，本 Skill 不改变 Review、审批、DAG、Worktree 或恢复语义。
