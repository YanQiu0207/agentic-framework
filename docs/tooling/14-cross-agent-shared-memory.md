# 跨 Agent 共享记忆业界调研与落地方案

## 结论

业界在「跨 CLI 共享记忆」上分三条路线：官方原生记忆（互不相通）、文件型共享层、服务型记忆层。本框架采用的「Markdown + Git + 分层索引」属于文件型路线，与 2026 年业界针对个人/小团队场景的主流共识一致，**不需要换路线**。

调研识别出四个可直接吸收的设计点：定量检索预算、写侧半自动草稿、摘要先行的读取顺序、多写入者冲突纪律。本文第 5 节给出四步实施方案，全部改动不新增运行时依赖，保持零运行时、跨 Claude Code / Codex 可移植。

这四点均为机制加固，不替代 [`09-personal-knowledge-base-plan.md`](09-personal-knowledge-base-plan.md) 阶段一的主线瓶颈（导入首批 20 篇真实条目 + 4 类问题验收）。

**状态**：已审核通过并实施（2026-07-19）。第 6 节决策已拍板，拍板结果见该节。

## 1. 调研范围与方法

- 调研日期：2026-07-19，方式为 Web 检索 + 逐个来源核读。
- 检索角度：跨 agent 共享记忆方案、开源记忆层项目、Claude Code / Codex 官方原生记忆能力。
- 来源清单与可信度标注见第 7 节。凡未经官方文档核实的二手信息，正文中已逐处标注。

## 2. 业界三条路线

### 2.1 官方原生记忆（各家自建，互不相通）

**Codex CLI** 官方记忆分两层：

- **AGENTS.md 静态指令层**：会话启动时读取，支持全局 / 项目 / 目录三级合并；上限 32 KiB（约 8000 token），超出静默截断。
- **Memories 生成层**：空闲 6 小时后后台自动汇总历史会话，写入 `~/.codex/memories/`；下次会话先读 `memory_summary.md`，需要时再 grep `MEMORY.md`；内置凭证脱敏和 30 天过期清理。

官方方案的局限：不跨设备、不跨工具、不支持手工编辑，且欧盟等地区未开放。

**Claude Code** 侧为 CLAUDE.md + auto-memory。另有报道称 Anthropic 推出「Dreaming」——定时进程回顾会话并整理记忆。**此点仅见二手报道（MindStudio），未在官方文档核实，不作为确定事实使用。**

**AGENTS.md** 已成跨工具事实标准：规范挂在 Linux Foundation 的 Agentic AI Foundation 下，Codex、Cursor、Aider、Jules 等均已采用。

官方路线的共同问题：记忆锁在各自工具内，无法在 Claude Code 与 Codex 之间共享。

### 2.2 文件型共享层（与本框架同路线）

**agentmemory**（jayzeng）：纯本地 Markdown 存储（`MEMORY.md` + 每日日志 + 主题文件），核心设计是「CLI 作为单一数据层」——Claude Code / Codex / Cursor 各装一个薄 SKILL.md 适配器调用同一个 CLI，新增工具支持成本极低。上下文注入按优先级分层限额，总上限 16K 字符；语义检索（qmd）为可选增强，未安装时核心功能完全可用（graceful degradation）。

**Markdown + Syncthing 三 agent 实践**（dev.to）：在 Claude Code、Codex、Hermes 三个 agent 间用纯 Markdown 文件共享记忆，约 30 行的 `INDEX.md` 做导航、详细文件按需加载——与本框架知识库的两跳索引结构一致，构成独立验证。该实践的核心经验是五条写入纪律（见 4.4），并明确将向量库 / Mem0 方案判为「过度工程、调试困难」，理由是 Markdown 方案可用 `cat` / `grep` / `diff` 调试、零 SDK 集成成本。

**claude-mem**：介于文件型与服务型之间。hook 自动捕获会话工具调用 → AI 压缩 → 注入下次会话；已支持 Claude Code / Codex / Gemini CLI / OpenCode 等（83.9k stars，数据截至 2026-06）。

### 2.3 服务型记忆层（MCP 接入）

- **Mem0 / OpenMemory**：Apache-2.0 记忆层，会话中抽取事实入向量库，新会话按语义 + 关键词 + 实体检索后注入；MCP 接入多工具。自报 LoCoMo 91.6 / LongMemEval 94.8（厂商自述，未独立核实）。
- **Letta**：有状态 agent 运行时，记忆块、归档记忆由运行时统一管理；另有记忆优先的 CLI 编码 agent（Letta Code）。

服务型路线解决的是团队共享与跨设备问题；对个人 / 小团队场景，2.2 节的实践者结论是文件型更优。

## 3. 对本框架的对照结论

| 对照项 | 业界现状 | 本框架现状 | 结论 |
| --- | --- | --- | --- |
| 存储形态 | 文件型为个人场景主流共识 | Markdown + Git | 路线一致，不改 |
| 索引结构 | `INDEX.md` 两跳导航被独立验证 | 根索引 + 主题索引两跳 | 结构一致，不改 |
| 检索预算 | agentmemory 分层限额，总上限 16K 字符 | 仅「禁止全量加载」定性规则 | **补定量预算**（4.1） |
| 写侧机制 | 自动捕获 + 异步汇总成趋势 | 工作流门禁人工确认 | **补半自动草稿**（4.2） |
| 读取顺序 | Codex 官方摘要先行、grep 兜底 | 两跳索引，无显式摘要层规则 | **固化读取顺序**（4.3） |
| 冲突处理 | Syncthing 实践五条纪律 | 单人单机 Git，无规则 | **预置写入纪律**（4.4） |
| 语义检索 | 实践者判文件型场景下为过度工程 | 阶段三按失败案例评估 | 立场一致，开始积累失败案例 |

## 4. 值得吸收的四个设计点

### 4.1 定量检索预算（源：agentmemory）

agentmemory 每轮注入按优先级分层限额（未完成事项 ≤ 2K、近期主题 ≤ 2K、今日日志 ≤ 3K、语义检索结果 ≤ 2.5K……总上限 16K 字符）。

**换算说明**：agentmemory 是 push 型「每轮注入」，本框架知识库是 pull 型「按需检索」，字符预算不可直接照搬，应换算为「文件数 + 行数」预算——可执行、可被脚本 lint。

### 4.2 写侧半自动草稿（源：claude-mem、Codex Memories 共同趋势）

业界正从「人工归档」走向「hook 自动捕获 → 后台异步汇总」。本框架写侧靠工作流门禁人工确认，质量更优但有遗漏风险。折中方案：AI 自动生成 delta 候选清单，人工只做逐条确认——保留「用户确认后方可写入」原则，同时规避全自动捕获的信噪比问题。对应 09 号文档阶段二的增量归档。

### 4.3 摘要先行、grep 兜底的读取顺序（源：Codex 官方 Memories）

先读小体积的 `memory_summary.md`，需要时才 grep 全量。本框架根索引已承担摘要角色，主题索引已带「结论」段；缺的是把「先读结论再决定是否下钻」固化为显式规则，以及两跳未命中后的受限 grep 兜底 + 失败案例记录。

### 4.4 多写入者冲突纪律（源：Syncthing 三 agent 实践）

五条纪律：会话开始读索引、按需读取不预加载、仅行级编辑、禁止整篇重写（用户明确要求重置除外）、写前必读。核心是「禁止 silent merge」——冲突必须停下、展示 diff、等用户裁决。本框架当前单人单机用不上冲突处理，但 Claude Code 与 Codex 同时写一个库的场景已现实存在，「写前必读 + 只追加不重写」现在就该写进接线模板。

## 5. 实施方案

改动落点横跨三处：框架仓库（`skills/project-init`）、知识库仓库（`E:/work/shared-knowledge-base`）、全局技能（`~/.claude/skills/project-knowledge/`）。

**单一权威原则**：所有查询 / 写入规则只写进知识库根 `index.md`（每次查询第一步必读，天然权威位置）；接线模板和 workflow skill 只留一句「遵守 index.md 查询与写入规则」，不复制细则，避免规则改一处漏三处。

### 第 1 步：定量检索预算（落地 4.1）

改知识库根 `index.md` 的「查询规则」，定性禁令升级为定量预算：

- 单次任务从知识库加载条目文件 ≤ 3 个；确需更多，先向用户说明原因。
- 根索引 ≤ 60 行；主题索引 ≤ 100 行。
- 单条目 ≤ 400 行，超限拆分为多条目并更新主题索引。
- 预算数字标注「初值，阶段一验收后校准」。

验证：第 3 步的 lint 脚本对行数预算做机器检查；加载数量约束靠规则 + 验收记录观察。

### 第 2 步：写入纪律（落地 4.4）

知识库根 `index.md` 新增「写入规则」章节，四条：

1. 写前必读目标文件最新版。
2. 行级追加 / 修改优先，禁止整篇重写（用户明确要求重置除外）。
3. Git 冲突禁止 silent merge——停下、展示 diff、等用户裁决。
4. 双 CLI 并发写同一库时，写前先 `git pull --ff-only`，失败即停。

同步改框架仓库 `skills/project-init/SKILL.md` 第 10 步接线模板：追加一行「读写均须遵守知识库根 `index.md` 的查询与写入规则」。

验证：模板与 `index.md` 无重复细则（人工对照）；规则生效靠后续真实双写场景观察。

### 第 3 步：摘要先行 + grep 兜底 + 确定性 lint（落地 4.3）

规则侧（改 `index.md` 查询规则的顺序描述）：

- 查询顺序固化为：根索引「结论 + 分类表」→ 主题索引「结论」→ 条目正文；先读结论再决定是否下钻。
- 两跳未命中 → 允许在 `domains/`、`issues/` 范围内 grep 兜底，禁止全库通配。
- 无论兜底是否命中，检索失败案例追加到 `changes/retrieval-failures.md`（问题、期望命中、实际结果）——即 09 号文档阶段三「按真实失败案例升级检索」所需的原始数据。

工具侧：知识库仓库新增 `scripts/lint_kb.py`（Python 3、4 空格缩进），机器检查：

- 每个 `domains/<topic>/` 有 `index.md` 且含「结论」章节。
- 根索引分类表 ↔ 实际目录一一对应；索引表链接目标存在。
- 行数预算（第 1 步三条）。
- 条目 frontmatter 齐全（`status` / `source` / `source_version`）。

验证：对当前库实跑一遍。现有 backend-system-design 条目预计会暴露 frontmatter 缺失——属预期收益，正好在导入首批 20 篇前堵住模板缺口。

### 第 4 步：delta 半自动草稿（落地 4.2，依赖前三步完成）

改 `~/.claude/skills/project-knowledge/SKILL.md` 的「交付前沉淀检查」：

- 检查时 AI 主动扫描本次会话，自动生成 delta 候选清单：可复用结论 / 踩坑 / 可晋升共用库的项，每条附建议去向（项目 `docs/` 某目录，或共用库 `domains/` / `issues/` / `changes/`）。
- 用户逐条确认后才写入；未确认的标记 dropped，不自动写入——保持「用户确认后方可写入」既有原则。
- 共用库 `changes/` 条目模板：`changes/<日期>-<slug>.md`，字段含来源、候选内容、状态（pending / merged / dropped）。

验证：下一次真实交付走完整流程，确认清单能生成、确认前零写入。

### 顺序与工作量

第 1、2 步为纯规则编辑（半小时级）；第 3 步一个脚本 + 对现有库实跑（半天级）；第 4 步 skill 编辑 + 一次真实交付验证。

## 6. 拍板决策（2026-07-19 已拍板）

1. **project-knowledge 的权威源**：✅ 采纳推荐方案——收编进框架仓库 `skills/project-knowledge/`（Tooling Profile），全局 `~/.claude/skills/` 副本由框架仓库同步。
   - 收编前冲突检查发现：`scripts/test_profile_contracts.py` 曾断言该 skill 不得存在，framework-unification spec §7.3 / §14.5 / §22 亦记录「防 project-knowledge 回流」。经确认，当初禁的是**旧版**的「现状真相机制」（维护 `architecture/` 现状文档，与代码事实源冲突）；现行版本已重写为「只沉淀 intent、不维护现状文档」，被禁机制不复存在。
   - 契约相应调整：禁令测试改为「防旧机制回流」的正向断言（收编版必须含「不维护现状文档」标记、不得出现 `architecture/overview.md`）；`README.md` 与 `docs/tooling/README.md` 注记同步更新。放弃的备选：直接改全局文件（无版本记录）、仓库内快照收编（双源易漂移）。
2. **lint 脚本归属**：✅ 采纳推荐方案——放知识库仓库 `scripts/lint_kb.py`，知识库自包含。

## 7. 来源清单

| 来源 | 链接 | 可信度说明 |
| --- | --- | --- |
| agentmemory（jayzeng） | <https://github.com/jayzeng/agentmemory> | 开源项目 README，已核读 |
| Sharing memory between three AI agents | <https://dev.to/arasovic/sharing-memory-between-three-ai-agents-claude-code-codex-and-hermes-394h> | 个人实践文，已核读 |
| Codex CLI Memory: How It Works + What Mem0 Adds | <https://mem0.ai/blog/how-memory-works-in-codex-cli> | Mem0 厂商博客，含官方机制描述与自家产品推介，已核读 |
| claude-mem | <https://github.com/thedotmack/claude-mem> | 开源项目，star 数据截至 2026-06 |
| Mem0 | <https://github.com/mem0ai/mem0> | 开源项目；benchmark 数据为厂商自述 |
| claude-mem v13.8.0 介绍 | <https://www.augmentcode.com/learn/claude-mem-v13-persistent-agent-memory> | 第三方介绍文 |
| AI agent memory systems in 2026 | <https://hermesos.cloud/blog/ai-agent-memory-systems> | 第三方综述 |
| Code with Claude 2026（MindStudio） | <https://www.mindstudio.ai/blog/code-with-claude-2026-new-agent-features> | 二手报道，「Dreaming」未经官方核实 |

## 变更记录

| 日期 | 变更 | 作者 |
| --- | --- | --- |
| 2026-07-19 | 创建调研与实施方案，状态待审核 | Claude |
| 2026-07-19 | 审核通过；第 6 节两项决策拍板（收编 + 修契约、lint 入知识库仓库）；第 5 节四步全部实施 | Claude |
