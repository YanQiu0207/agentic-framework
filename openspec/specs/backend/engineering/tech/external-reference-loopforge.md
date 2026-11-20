# 外部参考：Tencent LoopForge 及与当前框架的对照

> 本文档是 `Tencent/LoopForge` 的外部项目研究与接入评估，不是当前框架的实现规格。项目自述（README 与 docs）、可读源码确认、推断与缺失证据分别标注；任何借鉴项在进入设计或实现前，仍须回到当前框架的代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 项目 | `Tencent/LoopForge` |
| 定位 | 自部署的编码 Agent 交付工作台：编排现成编码 CLI，外加角色、沙箱、SOP、人工关口与留痕 |
| 代码仓库 | <https://github.com/Tencent/LoopForge> |
| 分析基准 | main `dd56585276d8`（2026-11-15 取样）；最新 Release `v0.3.8`（2026-11-12） |
| 版本与许可 | MIT（README 徽章与 `LICENSE`；GitHub API 识别为 Other），Go，约 1.1k stars，2026-07-28 创建 |
| 核实范围 | `README.zh-CN.md`、`docs/local/usage.zh-CN.md`、`docs/local/editions.md`、`docs/architecture.md`、仓库文件树、`internal/runtime/skill_tree.go` 与 `skill_md.go` 的函数签名和注释 |
| 核实边界 | 未本地安装或部署实测；未读 `docs/deployment.md`、`local/` 工作流源码与 SOP 引擎源码；平台行为以 README 自述为主 |
| 同名项目 | `matheus3301/loopforge`：Go CLI，按搜索摘要为「PRD 驱动的迭代式编码 Agent 循环」，4 stars，最后推送 2026-01-24，未纳入分析 |

## 一句话定性

LoopForge 不自研 Agent，而是**编排现成的编码 CLI**（CodeBuddy、Codex、Claude Code、OpenCode、Cursor CLI 等 10 种），自己只负责外层：谁来做、在哪个沙箱、按什么顺序、经过哪些检查、由谁签字。它和当前框架同属「阶段流程 + 角色分离 + 人工关口」路线，但重心在**团队平台化与运行隔离**，而当前框架的重心在**本地治理、确定性门禁与证据链**。

## 两种形态（README 自述）

| | 平台版 | Local 版 |
| --- | --- | --- |
| 形态 | Docker Compose 部署的服务（Go + MySQL + Web） | `npx -y loopforge-cli install <agent>` 写入项目目录 |
| 工作流 | Main Bot 对话 + 画布自定义 SOP | 只有内置 Classic / Portable devflow |
| 执行位置 | 每次 SOP 运行和对话工作区各起 Docker 沙箱；也可连接本地执行机器 | 宿主编码 CLI 直接在本机执行 |
| 证据留存 | Web 工作台中的运行详情、审批与指标 | `artifacts/{task_slug}/` 下 `01-requirement` ~ `05-knowledge` 与 `workflow-summary.md` |
| 宿主覆盖 | 10 种执行器 | Classic：CodeBuddy、Codex、Cursor、Claude Code；Portable 另含 Pi、DeepSeek Harness、Hermes |

文档明确：「平台 SOP 导出和独立执行尚未实现」，两种形态的工作流资产互相独立（`docs/architecture.md`：Classic、Portable 资产与平台角色定义分开）。

## 机制要点

**SOP 节点**（README）：Agent（角色）、脚本（确定性 Shell）、人工关口（放行／补充信息重跑／退回上游）、子 SOP、预览构建。每个节点声明产物和依赖，依赖完成后自动推进；支持失败打回、从任意节点重跑、版本发布。

**角色**（README）：提示词 + 执行器 + 模型 + Rules + Skills + MCP 工具 + 产物与门禁；同一角色既可做 SOP 节点，也可在对话中作为子 Agent 调用。

**Skill 下发**（源码注释确认）：`WriteSkillTree` 为每个 Skill 写一个含 `SKILL.md` 的目录，使「扫描该目录作为 skills 目录的 CLI」可以原生调用；`compileSelectedSkill` 的落点为 `<agentRel>/skills/<id>/SKILL.md`，缺 frontmatter 时补齐；另有 `WriteInertSkillTree` 让 `SKILL.md` 经过 `InertCLIText` 处理，避免加载时执行内容。仓库另有 Skill Hub 市场与 zip 上传相关代码（`internal/httpapi/skillhub_*.go`、`skill_zip_entries*`），未逐行核实。

**执行器限制**（README）：需求澄清、通知 AI 汇总、Bot 回复和运行评测目前只接受 CodeBuddy 模型；Claude Code 之后的 7 种 CLI 每次运行在私有 HOME 中生成配置，始终使用需求责任人填写的个人 Key。

**Local devflow**（`docs/local/usage.zh-CN.md`）：按复杂度分流（小改动单角色精简路径，中大型任务走澄清确认 → 设计 → 实现 → 独立审查 → 测试 → 交付），状态落盘可 `/resume-devflow` 续跑；安装状态记录在 `.devflow/install-state.json`，检测到用户修改或冲突时更新停止，提供 `plan`、`status`、`doctor`、`update`、`uninstall`。CodeBuddy Classic 自带本地可观测看板（Token 与成本趋势、Skill/Rule 使用、角色派发、阶段归因）。

## 与当前框架的对照

| 维度 | LoopForge | 当前框架（证据） |
| --- | --- | --- |
| 流程分档 | Local 按复杂度分小改动／中大型 | `skills/workflow-code-generation/SKILL.md` 的轻量／标准档 |
| 独立审查 | 评审角色与实现角色分离 | `agents/` 下 8 个 reviewer，五维审查与 strict Judge |
| 中断恢复 | SOP 节点重跑；Local `/resume-devflow` | workflow-control 以 `tasks.md` 为状态，`recover` 生成恢复计划 |
| 知识沉淀 | Local `05-knowledge/` | `openspec/` 长期 Specs、Changes 归档与 Issues |
| 治理门禁 | SOP 节点 + 人工关口 | Profile、确定性门禁脚本、Run Envelope 证据链 |
| 运行隔离 | 平台版 Docker 沙箱 | Git Worktree，Agent 仍在宿主执行 |
| 无人值守 | 定时任务、新需求自动派发 SOP | 无，需会话驱动 |
| 团队协作 | 账号、成员、共享运行记录、「待我确认」 | 单人本地 |
| 宿主覆盖 | 10 种执行器 | `scripts/install_agentic_framework.py:20` 的 `CLIENT_DIRS = (".codex", ".claude")` |
| 可视化 | SOP 画布、运行详情、成本报表、本地看板 | 有 `metrics/session-history.jsonl` 与 `scripts/analyze_session_metrics.py`，未发现可视化页面 |
| VCS | README 列 GitHub、GitLab、Gitea、Gogs、CNB，未提 SVN（`deployment.md` 未核实） | Git 与 SVN（change 2060） |

## 接入可行性

**Local 版不能承载当前框架**：它只运行内置 devflow，不提供角色、SOP 或外部 Skill 挂载点；且与 `workflow-*` 占据同一流程位置，同项目并装会形成双路由。只能作为对照或替代品，不是接入点。

**平台版可以作为外层编排**，路径按侵入度排序：

1. 角色挂 Skill：把 `skills/` 条目登记为角色 Skill，由平台物化进沙箱（依据上文源码注释；依赖 `scripts/` 与 `.agentic-framework/` 的 Skill 能否在沙箱中完整运行，未验证）。
2. 门禁脚本作为 SOP 脚本节点。
3. 将 `workflow-*` 的澄清 → 设计 → 实现 → 审查 → 测试 → 验收复刻为 SOP，批准点对应人工关口。

平台版的部署边界（README）：默认监听 `0.0.0.0:8090`；平台通过宿主 Docker socket 启动沙箱，只适用于可信团队，不构成多租户隔离；已登录用户可读取实例内各项目数据，默认允许自助注册。安装脚本只写了 Linux 与 macOS，Windows 支持**未说明**。另据 `docs/architecture.md` 的 MySQL 持久化分层推断，SOP 定义存于平台数据库而非仓库文件，未核实。

Local 版的风险（`docs/local/usage.zh-CN.md`）：部分宿主的 Classic 配置会启用自动执行或高权限模式，文档建议只在可信项目使用并先跑 `loopforge plan`；看板示例命令 `python3 -m http.server 8765` 默认监听所有网卡，应改用 `--bind 127.0.0.1`。

## 评估结论（2026-11-15）

针对当前使用条件（单人使用、不需要无人值守、目标项目含 SVN、目的是补框架短板），**平台版与 Local 版均不采用**：

- 平台版的增量集中在团队协作、无人值守与沙箱隔离，当前均不需要；SVN 项目无法纳入；Windows 部署未说明，运维与安全边界成本高于收益。
- Local 版与 `workflow-*` 能力重叠，宿主仍是 Claude Code / Codex，增量很小，并装还会冲突。

触发重新评估的条件：需要多人共享流程与审批、需要 Agent 无人值守运行、需要强运行隔离，或需支持 Cursor、CodeBuddy 等其他宿主。

## 借鉴候选及处置

| 候选 | 来源 | 处置 |
| --- | --- | --- |
| 安装器环境自检（类 `loopforge doctor`） | Local CLI | 已评估，用户判断必要性不足，暂不实施 |
| 基于 `session-history.jsonl` 的本地静态看板 | CodeBuddy Classic 可观测看板 | 已评估，用户判断必要性不足，暂不实施 |

## 缺失证据与后续动作

- 未部署平台版，SOP 引擎、沙箱生命周期与人工关口行为均以 README 自述为准。
- 未读 `docs/deployment.md`，SVN、Windows、执行机器细节未核实。
- 未验证当前框架的 Skill 在 LoopForge 沙箱中能否找到依赖的 `scripts/` 与运行目录。
- 重新评估时，先从上述三项补证据，再决定是否试点。
