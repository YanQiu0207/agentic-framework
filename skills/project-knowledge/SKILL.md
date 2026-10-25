---
name: project-knowledge
description: 项目知识读取、更新和归档规范。处理 Change、长期知识、已验证故障或知识影响检查时使用。
---

> 输出一行：`Using project-knowledge`

# 项目知识管理规范

本 Skill 是 Production 与 Tooling 的 Shared Core 合同。两个 Profile 共用知识目录、文件语义和归档规则；各自的审批、Review、DAG、Worktree 与失败恢复策略保持独立。

## 1. 不可违反的边界

1. **知识只辅助理解**：项目长期 Specs、Issues、Archive 和跨项目公共知识都不是当前实现的事实源。
2. **当前事实必须核实**：模块、接口、数据流和运行行为以代码、Schema、配置、测试与运行证据为准。
3. **活跃 Change 是本次任务契约**：实现和验收必须对照当前 `openspec/changes/<ticket>-<change>/`；它不是普通知识。
4. **冲突必须显式报告**：知识与当前事实不一致时，同时展示双方证据和不确定性，不得静默选择、覆盖或宣布任意一方错误。
5. **项目知识保持项目作用域**：Agent 只能从当前项目的逻辑根和已接线的公共知识库主动检索，不得把兄弟项目目录加入检索范围。该规则是人工操作边界，不是文件系统 ACL；保密需求仍需权限或执行环境隔离。
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
│   ├── <ticket>-<change-name>/
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

### 3.4 跨 Change 共享领域模型

领域模型属于项目，不属于某个 Change。解释领域需求、开展工程访谈或决定相关设计前，必须先由 `openspec/index.md` 定位并读取相关共享模型，再叠加当前 Change 已批准的差异。实现、测试与 Review 涉及领域语义时沿同一路由读取。

- 默认通过 `openspec/specs/business/index.md` 定位术语及相关业务域；小项目允许根索引直接链接条目，不创建空层级。
- 模型包括术语、概念职责与关系、规则与不变量、跨模块流程，位置见第 5 节。不能只读当前 Change 或把术语表当作整个模型。
- 同会话已加载且内容未变时复用，新会话或模型变化后重新读取相关条目。索引未命中按 §3.1 定向查找，确无定义才询问，不重复让用户解释已有术语，也不扫描全部历史 Change。
- 同名概念按业务上下文区分，无法判定所属上下文时先询问。业务定义辅助理解，不代表实现已满足；涉及当前行为仍按第 4 节核对证据。

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
| 业务域概述、概念职责、关系与领域边界 | `openspec/specs/business/<domain>/overview.md` |
| 业务规则与不变量 | `openspec/specs/business/<domain>/rules.md` |
| 跨模块业务流程 | `openspec/specs/business/<domain>/flows.md` |
| 业务背景、例外和人工解释 | `openspec/specs/business/<domain>/custom/` |
| 前端模块代码派生事实 | `openspec/specs/frontend/<domain>/<module>/` 的对应生成文件 |
| 前端模块人工背景、约束和踩坑 | `openspec/specs/frontend/<domain>/<module>/custom/` |
| 后端服务代码派生事实 | `openspec/specs/backend/<domain>/<service>/` 的对应生成文件 |
| 后端服务人工背景、约束和踩坑 | `openspec/specs/backend/<domain>/<service>/custom/` |
| 前端模块或后端服务的代码来源元数据 | 对应模块或服务目录的 `meta.yaml` |
| 前后端共享协议 | `openspec/specs/common/protocols/` |
| 共享数据模型 | `openspec/specs/common/data-models/` |
| 统一错误码语义 | `openspec/specs/common/error-codes/` |
| 端内项目工程规范 | `openspec/specs/frontend/engineering/` 或 `openspec/specs/backend/engineering/` |
| 单次需求、设计、任务和 Delta | `openspec/changes/<ticket>-<change>/` |
| 已完成历史 Change | `openspec/changes/archive/<ticket>-YYYY-MM-DD-<change>/` |
| 已验证项目故障 | `openspec/issues/<issue>.md` |
| 跨项目通用方法候选 | 当前 Change 的知识候选清单，或 轻量 Native Delivery 交付报告 |
| 跨项目通用故障候选 | 当前 Change 的知识候选清单，或 轻量 Native Delivery 交付报告 |

无法确定业务域、端或模块时，不得猜测目录；把候选留在当前 Change 或交付报告，列出待确认的归属。

## 6. 自动生成与人工知识

### 6.1 代码派生内容

模块或服务目录可按需包含：

```text
meta.yaml
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

`custom/` 的权威文件清单如下；同类知识不得另起近义文件名：

```text
custom/
├── constraints.md    # 长期约束、红线和适用边界
├── decisions.md      # 长期有效的决策及理由
└── pitfalls.md       # 已验证的踩坑与规避方式
```

不属于以上三类的人工知识先留在当前 Change，确认形成新的长期知识类型后，必须先更新本节合同再新增文件名。

## 7. Change Delta 与 Archive

### 7.1 Change 期间

活跃 Change 优先写自身 `specs/` 中的 Delta，不直接把未验证结论写入长期 Specs。Delta 相对路径镜像 `openspec/specs/`：

```text
openspec/changes/<ticket>-add-refund/specs/common/protocols/refund-api/spec.md
    → openspec/specs/common/protocols/refund-api/
```

Delta 使用 `ADDED`、`MODIFIED`、`REMOVED` 和 `RENAMED` 表达变化。临时实现细节、一次性迁移步骤和未确认猜测只留在 Change。

领域模型写入先分类，不能把所有词汇更新都当作未来功能，也不能以「澄清」提前发布未来规则：

| 类型 | 前置条件 | 动作与完成标准 |
| --- | --- | --- |
| 既有知识澄清 | 用户明确确认既有含义，并明确授权更新目标条目；相关事实已核实、无未决冲突、不引入未来行为 | 先读最新原文，最小更新第 5 节对应共享位置；记录确认来源、日期及适用范围，维护根索引到条目的可达路径。不必等功能交付，可无功能 Change |
| 未来业务变化 | 新增或改变概念、规则、关系或行为 | 先写当前 Change 的镜像 Delta；无已确认 Change 时按现有需求流程确认编号与范围，未授权前只讨论；按 §7.2 验证归档后同步 |
| 分类不明、冲突未决或无写入授权 | 任一前置条件不满足 | 有 Change 则在其中保留候选，否则留在对话待确认；不得覆盖共享模型 |

用户确认含义不等于允许写入。纯业务定义可注明用户确认为来源，不伪称代码已验证；一旦实际改变业务语义，必须走未来变化路径。此分支不豁免 `custom/` 人工内容保护、公共知识批准或交付前沉淀检查。

每次共享写入前，定向比较同一概念的最新共享条目及相关活跃 Change Delta；冲突显式报告，未交付规则不能自动晋升，已有澄清不能被过时 Delta 静默覆盖。不复制多份正文，不擅自迁移历史条目，不承诺操作规则能提供文件锁或并发事务隔离。

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

## 8. 高级知识操作（按需）

仅在用户要求 SVN 初始化、外置知识、公共库接线或晋升时，检查 `knowledge-advanced` 能力包，再读取 [reference/knowledge-advanced.md](reference/knowledge-advanced.md)。项目内知识、冲突报告、已接线公共知识查询和正常归档不依赖该包。

从已加载 Skill 的真实路径（解析链接后）向上定位同时包含 `scripts/install_agentic_framework.py` 和 `skills/workflow-code-generation/SKILL.md` 的受信根，运行 `python <trusted-framework-root>/scripts/install_agentic_framework.py --show-packs <project>`，只读取 JSON 的 `enabled` 数组。不得执行目标 manifest 的 `source`。找不到受信根、查询失败或缺包时停止高级操作，提示安装器 `--with knowledge-advanced`；不得自行推断旧安装或源码根的能力。

## 9. 交付前 intent 沉淀检查（强制）

每次向用户宣布「完成」或「交付」前，无论是否创建 Change，都必须先扫描本次会话、Diff、测试和运行证据，在内部逐项检查下表；输出只保留命中项，不要求逐行展示未命中项。

| 信号 | 命中后的唯一建议动作 |
| --- | --- |
| 做出不可逆或高影响架构决策 | 在当前 Change 的 `design.md` 记录完整决策；长期有效时同步到相关业务域、模块或服务的 `custom/decisions.md`，跨端工程决策写入对应 `engineering/tech/` |
| 放弃重要方案且理由值得保留 | 先写当前 Change 的备选方案与权衡；长期约束按上一行位置同步 |
| 引入性能、兼容或安全红线 | 写当前 Change；长期有效时同步到相关 `custom/constraints.md` 或端内 `engineering/` |
| 查证故障根因并完成验证 | 写入 `openspec/issues/<issue>.md`；未验证猜测只留当前 Change |
| 产生可跨项目复用的结论 | 只列入当前 Change 或交付报告；用户确认后再按第 8 节晋升 |
| 普通功能、配置或 Bug 修复，且没有长期知识影响 | 不新增知识文件，简述无长期影响的具体理由 |

输出规则：

- 无命中：只输出一句「无长期知识影响：<具体理由>」。内部检查不得省略；机器参数仍为 `--knowledge-impact none --knowledge-impact-reason "<具体理由>"`。
- 有命中：只列命中信号、目标路径与同步状态。跨项目候选保留在当前 Change 或交付报告，标记待用户确认，不自动晋升。
- 已满足 §7.1 前置条件的既有领域知识澄清：可直接更新获授权的共享条目和索引，报告目标与确认来源，不强制另建功能 Change；不得用此分支晋升未来变化或未验证事实。
- 其他有长期影响但没有 Change 的任务：先创建 Change 并完成同步，再交付；不得用 `none` 绕过。

若命中但当前无法完成沉淀，在当前 `tasks.md` 新建「知识同步」任务并保持未完成；不得归档或宣布全部完成。

## 10. 与工作流的关系

- Production 与 Tooling 统一的 `workflow-*` 必须调用本 Skill 的同一读写路由。
- 轻量 Native Delivery 可以不创建 Change，但必须完成知识影响检查，并说明为什么没有长期知识影响。
- Requirements、Design、Code、Test、Review、Troubleshooting 和 Archive 阶段分别按第 3 节读取，不得把公共知识当项目事实。
- Archive 必须执行第 7 节的同步门禁；只移动 Change、未完成知识同步的归档不合格。
- 工作流执行策略由各 Profile 自己定义，本 Skill 不改变 Review、审批、DAG、Worktree 或恢复语义。
