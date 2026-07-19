---
name: project-init
description: |
  初始化当前项目：选择版本管理模式和框架 Profile，创建统一的 openspec 项目知识骨架，
  可将私有知识正文外置并链接到项目，按需独立接线跨项目公共知识库，最后仅提交本次产物。
  已存在的文件、目录、链接和未跟踪内容一律不覆盖。
  仅通过 /project-init 手动触发，禁止模型自动调用。
disable-model-invocation: true
---

> 输出一行：`Using project-init`

# 项目初始化

作用于当前工作目录，无参数。所有步骤遵循同一原则：**先检查，再创建；已存在的内容不覆盖、不改写、不删除**。

## 成功标准

- 项目记录明确的版本管理模式和框架 Profile。
- 项目路径 `openspec/index.md`、`openspec/specs/index.md` 和 `openspec/issues/index.md` 均可读取。
- 项目知识正文位于项目内，或位于用户指定的外部私有目录并通过 `openspec/` 链接透明访问。
- 外置模式明确版本管理或备份方式、链接恢复方法，并能检测失效链接。
- 是否接入跨项目公共知识库由用户单独决定，不与项目知识存储方式绑定。
- Git 只提交本次创建或修改的文件，不卷入既有未跟踪内容。

## 处理流程

### 1. 选择版本管理模式

向用户提问（单选），拿到答案前不执行后续步骤：

- **纯 Git**：Git 同时用于本地开发和正式提交。
- **Git + SVN**：本地用 Git，正式提交走 SVN。

### 2. 选择框架 Profile

单独询问并记录：

- **Production**：使用 OPSX 生命周期和 Production Review 门禁。
- **Tooling**：使用 Tooling 的 DAG、Worktree、失败隔离和统一最终 Review。

Profile 只决定执行生命周期；两种 Profile 使用相同的 `openspec/` Artifact 结构。

### 3. 选择项目知识库存储方式

单独询问（单选）：

- **项目内存储（推荐）**：在 `<project>/openspec/` 创建正文，随项目版本库管理。
- **外部私有目录**：在用户指定的绝对路径保存正文，并将 `<project>/openspec/` 创建为指向该目录的链接。

此问题只决定项目私有知识的物理位置，不代表是否接入跨项目公共知识库。

#### 3.1 通用覆盖检查

创建前同时使用存在性检查和链接检查，覆盖正常目录、符号链接、目录联接和失效链接：

- `<project>/openspec` 已存在或是任何类型的链接 → 停止创建该入口，报告类型和目标；不得删除、替换、合并或把它当作空目录。
- 发现未跟踪内容 → 只报告，不得以「未跟踪」为由移动或删除。
- 路径状态无法可靠识别 → 停止并要求人工确认。

#### 3.2 外置模式附加确认

在创建任何目录或链接前依次完成：

1. 要求用户提供绝对路径，不接受相对路径。
2. 解析项目根、外部目录和公共知识库的真实路径；外部目录不得位于跨项目公共知识库内，也不得与项目根或公共库重叠。
3. 外部目录不存在 → 可以创建；外部目录为空 → 可以使用；外部目录非空 → 展示清单并停止，只有用户明确确认复用后才继续，且不得覆盖其中任何文件。
4. 询问正文保护方式：由所在项目 Git 管理、独立 Git 仓库管理，或明确的备份系统。若用户选择无版本管理和无备份，说明丢失风险并停止外置初始化。
5. 要求确认恢复方案，至少记录外部绝对路径、链接类型和在新机器上重新创建链接的步骤。

创建链接时使用当前平台支持的目录符号链接；Windows 无权限创建符号链接时，先报告原因，再取得用户明确同意后使用目录联接。禁止静默复制正文作为降级方案。

### 4. 初始化 Git

两种版本管理模式都需要 Git。运行 `git rev-parse --is-inside-work-tree` 判断：

- 已是仓库 → 跳过，记录「已存在」。
- 不是仓库 → 运行 `git init`，记录「已初始化」。
- `git init` 失败 → 报告错误，继续执行不依赖 Git 的创建步骤；最后不得声称初始化完整成功。

### 5. 创建并补全 `.gitignore`

不存在则创建，已存在则只追加缺失条目，不改写、排序或删除已有内容。追加前先执行 `git check-ignore -v <path>` 核实已有规则，避免添加重复或范围过大的模式。

#### 5.1 通用本地产物

所有项目追加以下缺失条目：

```gitignore
# Agentic Engineering Framework 本地运行产物
.agentic-framework/

# OS / 编辑器
.DS_Store
Thumbs.db

# AI 客户端本地配置
.claude/settings.local.json

# Agentic Engineering Framework 本地运行产物
.agentic-framework/
.verify/
**/.tasks.md.lock
```

这些框架产物的边界是：

- `.agentic-framework/`：安装器生成的目标项目 Manifest、Pack 链接和后续框架本地状态；内容包含本机安装路径，不作为项目源码提交。
- `.verify/`：`workflow-verification` 和 `workflow-code-review` 生成的本地基线、验证报告与 Review 证据；长期结论应写入 `openspec/`，不直接提交 `.verify/`。
- `**/.tasks.md.lock`：`workflow-code-generation` 控制器生成的任务写锁；只用于并发保护，不是任务状态正文。

Git + SVN 模式额外追加 `.svn/`。

#### 5.2 按项目事实追加

只在当前项目已存在对应工具、配置或产物时追加，不凭技术栈名称猜测：

```gitignore
# Python 缓存（项目包含 Python 代码或 Python 工具时）
__pycache__/
*.pyc
.pytest_cache/

# 会话遥测（项目使用本框架 analyze_session_metrics.py 时）
metrics/session-history.jsonl
```

发现其他候选忽略项时，必须先说明其创建者、用途和是否可重建；不能仅因文件未跟踪、位于隐藏目录或看起来像生成物就加入 `.gitignore`。

#### 5.3 禁止忽略的项目产物

以下内容属于项目自身的可审查产物，默认必须纳入版本管理，不得加入 `.gitignore`：

- `AGENTS.md`、`CLAUDE.md`、`README.md` 和 `verify.config.json`。
- `openspec/index.md`、`openspec/specs/`、`openspec/changes/`、`openspec/issues/` 及其 `proposal.md`、`design.md`、`spec.md`、`tasks.md`、ADR、审计报告和归档文件。
- 项目代码、测试、Schema、配置、脚本、Skill、Agent、Command 和正式文档。
- 用于保留约定空目录的 `.gitkeep`。

若项目已有规则忽略上述内容，停止修改该规则，展示 `git check-ignore -v` 的来源并要求用户确认；不得静默取消忽略，也不得继续声称这些产物会被 Git 提交。

若 `openspec/` 是指向项目外部的链接，先询问用户是否跟踪该链接本身；不要擅自把 `openspec/` 加入 `.gitignore`。

### 6. 配置 SVN 忽略（仅 Git + SVN 模式）

运行 `svn info` 判断当前目录是否为 SVN 工作副本：

- 是工作副本 → 先读取 `svn:ignore`，合并 `.git` 与 `.gitignore` 后写回。
- 不是工作副本或未安装 SVN → 跳过，并在报告和 `AGENTS.md` 中记录接入 SVN 后的补做项。

### 7. 判断项目类型

扫描当前目录，排除 `.git/`、`.svn/`、`node_modules/` 等依赖目录：

- 除本 Skill 将创建的文件外没有实质内容 → 空项目。
- 存在代码或文档等实质内容 → 已有代码项目。

### 8. 创建 `CLAUDE.md`、`AGENTS.md` 和 `README.md`

`CLAUDE.md` 不存在时只写入：

```markdown
@AGENTS.md
```

`AGENTS.md` 不存在时创建最小骨架；存在时只追加缺失章节。不得覆盖已有同名章节。必须记录：

- 版本管理模式。
- 框架 Profile。
- 项目知识入口固定为 `openspec/index.md`。
- 项目知识和公共知识只用于辅助理解；代码、Schema、配置、测试和运行证据用于确认当前事实。
- 知识与代码冲突时展示双方证据，不得静默选择或修改任意一方。
- 外置模式的正文路径、链接类型、保护方式和恢复步骤。

`README.md` 不存在时按项目类型生成最小内容；无法从代码确认的信息写 `TODO`，禁止编造。

### 9. 创建统一最小 `openspec/` 骨架

项目内模式在 `<project>/openspec/` 创建；外置模式先在外部私有目录创建正文，再创建项目入口链接。两种 Profile 都使用相同骨架：

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

不要预先创建空的 `business/`、`frontend/`、`backend/` 或 `common/`；在真实知识首次产生时再创建。

三个索引保持精简：

- `openspec/index.md`：项目概述、读取入口、活跃 Change、写入规则和冲突规则。
- `openspec/specs/index.md`：长期辅助知识的分类索引，初始可为空。
- `openspec/issues/index.md`：已验证项目故障的索引，初始可为空。

`changes/archive/` 为空时放置 `.gitkeep`。所有中文 Markdown 写入前按 `md-zh` 规则自检。

### 10. 验证项目知识入口

创建完成后必须从项目路径验证，而不是只检查外部正文：

1. `openspec` 存在；外置模式还必须确认它是预期类型的链接，且目标等于用户确认的绝对路径。
2. 从 `<project>/openspec/` 读取三个索引文件成功。
3. 外置目录暂时不可达或链接失效 → 验证失败；不得报告成功，也不得自动新建同名真实目录掩盖失效链接。
4. 记录正文保护方式和恢复步骤已写入 `AGENTS.md`。

### 11. 单独询问公共知识库接线

无论是否检测到已有公共库路径，都单独询问：

- **接入跨项目公共知识库**。
- **暂不接入**。

用户选择接入后：

1. 优先读取 `~/.claude/CLAUDE.md` 中「跨项目共用知识库」路径，并向用户展示确认；没有有效路径时再请求绝对路径。
2. 验证公共库根 `index.md` 可读取。
3. 确认公共库与外置项目私有知识目录不重叠。
4. `AGENTS.md` 已有公共知识库章节则不覆盖；否则追加查询入口和边界规则。

公共接线规则必须说明：

- 公共库只保存经用户确认、脱敏和泛化后的跨项目知识。
- 项目专属知识不得写入公共库，未确认候选只能留在当前项目。
- 公共知识只作通用参考，与项目代码冲突时必须报告冲突。

用户选择暂不接入时，不修改全局配置，也不影响项目知识库初始化。

### 12. 首次 Git 提交

仅提交本次 Skill 创建或修改的文件，使用逐路径 `git add`，禁止 `git add .`。外置正文不在当前 Git 工作树内时，不得假装它已随项目提交；报告其独立 Git 或备份状态。

提交信息：

```text
chore: 初始化项目脚手架
```

Git + SVN 模式只提交到本地 Git，不执行 `git push` 或 `svn commit`。

### 13. 汇总报告

```markdown
| 项目 | 结果 |
| --- | --- |
| 版本管理模式 | 纯 Git / Git + SVN |
| 框架 Profile | Production / Tooling |
| Git | 已初始化 / 已存在 / 失败 |
| 项目知识存储 | 项目内 / 外部私有目录 |
| `openspec/` 入口 | 已创建 / 已存在（未改动） / 验证失败 |
| 正文保护 | 项目 Git / 独立 Git / 备份系统 / 不适用 |
| 链接恢复 | 已记录 / 不适用 / 未完成 |
| 公共知识库接线 | 已接线 / 暂不接入 / 验证失败 |
| 首次提交 | 已提交 / 跳过 / 失败 |
```

## 边界情况

- 所有产物都已存在 → 不做任何覆盖性修改，报告「无需初始化」及未验证项。
- 已有 `openspec/` 但结构不完整 → 只报告缺失项，先取得用户明确授权，再补齐；不得把初始化规则当成覆盖授权。
- 外置路径与公共知识库重叠 → 拒绝创建。
- 外置链接失效 → 报告失败，禁止创建同名目录或复制正文掩盖问题。
- 用户未确认正文保护和恢复方案 → 外置模式停止；可以改选项目内模式。
- 生成的中文 Markdown 必须遵循 `md-zh` 排版规范。
