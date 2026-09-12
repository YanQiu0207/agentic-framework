# 宿主原生能力对齐复查（2026-09）

> 本专题的第三次对齐：前两次对标外部 Harness Engineering 方法论文章（来源一、来源二），本次对标宿主（Claude Code）2026 年原生新增能力。属于「调研 + 规划」，不是 feature spec；实施时按本目录「后续约定」走 `docs/design-docs/`。

**更新日期**：2026-09-12

## 1. 背景

2026 年 Claude Code 从「可配置 CLI」进化为「自带编排运行时」：原生 Workflow 工具、内置 `/code-review`、`--worktree`、plugins + marketplace、auto mode、OTEL 遥测相继上线。同期外部共识也在成型——Harness Engineering 被广泛讨论为 2026 年 AI 工程核心范式（Martin Fowler 于 2026-02 提出术语、Anthropic 发布长时运行 Agent 线束文章、腾讯与阿里社区密集发文）。

本框架的架构选择是「确定性内核 + 骑宿主编排」（工作流接线依赖宿主 Agent 执行，见 `docs/framework-features-status-and-comparison.md` 第 1 节）。宿主能力爆发直接影响这个选择的前提：哪些自建部分仍不可替代，哪些正在被宿主原生吸收，哪些缺口可以借宿主能力补齐。

## 2. 复查口径

| 侧 | 来源 | 说明 |
| --- | --- | --- |
| 宿主侧 | Claude Code 官方 What's New（Week 13-34，2026-03 至 2026-08） | 功能与时间窗口 |
| 宿主侧 | 官方 CHANGELOG 2.1.261-2.1.269（2026-09） | releasebot 转载自 `anthropics/claude-code` 官方 CHANGELOG.md |
| 宿主侧 | 2026-09-12 本会话工具面板直接观察 | Workflow、Monitor、CronCreate、ScheduleWakeup、SendMessage、TaskCreate 等工具的存在与形态 |
| 框架侧 | 2026-09-12 全仓核对 | 证据为 `file:line`，见各块 |

宿主迭代极快，本文是 2026-09-12 快照；时效风险与 `docs/framework-features-status-and-comparison.md` 第 7 节同口径。

## 3. 宿主能力进展摘要

| 宿主能力 | 上线时间 | 冲击的框架块 |
| --- | --- | --- |
| Workflow 工具：脚本编排多子代理，带 resume、journal、Schema 验证 | 2026-05（Week 22） | DAG 分波执行 |
| 内置 `/code-review`（先正确性审查，后变后台子代理）、`/ultrareview` 云端多 Agent、`claude ultrareview` 进 CI | 2026-04 至 2026-07 | Review 编排 |
| 原生 `--worktree`、`worktree.baseRef`、worktree 工具与 hooks | 2026-02 起持续增强 | worktree 编排 |
| plugins + marketplace + `claude plugin eval`（可打分、可复现的插件评测） | 2026 全年，2026-09 补齐 eval | 安装分发 |
| OTEL 遥测（如 `OTEL_METRICS_INCLUDE_REPOSITORY`） | 2026-09（2.1.269） | Telemetry（互补） |
| auto mode 权限分类器（2026-08-14 起 Pro/Max/Team 新会话默认） | 2026-03 预览 | 权限治理（平行） |
| hooks 体系（条件 `if` hooks、effort 感知、SessionEnd 超时） | 持续 | 门禁强制执行（缺口相关） |
| Agent Teams、fork mode、跨会话消息传递、子代理默认后台 | 2026-06 至 2026-08 | 多 Agent 编排 |

## 4. 逐块对齐结论

### 4.1 Tooling DAG 状态机：部分吸收

**框架现状**：确定性控制流内核 `skills/workflow-code-generation/scripts/workflow_control.py`（约 1254 行）负责全部状态机决策，与 Agent 调度严格分离：

- 确定性代码：Kahn 拓扑分波（:187-201）、10 个合法状态迁移（:389-400）、重试与转人工（:595-602）、阻塞传播（:647-677）、跨进程写锁（:900-979）、原子写回（:882-897）、批准门（:551-567）、治理 Profile 守卫（:1090-1118）、Verify 报告合同校验（:255-278）、中断恢复计划（:724-749）
- 依赖宿主执行的 Skill 指令：调度靠宿主 Subagent（SKILL.md:131-133）；`tasks.md` 的「状态：」字段是续跑真相源（SKILL.md:135）

**与宿主的重叠**：**高**。波次编排职责与宿主 Workflow 工具重叠。框架已有一处接口约定——并行波次产出后「传入 Workflow 工具的 `args.waves`」（SKILL.md:129），但全仓仅此一处痕迹，未深化。

**处置**：部分吸收。Kahn 分波保留做**依赖校验**（确定性门禁的一部分）；执行调度正式交给宿主 Workflow 工具，其自带 resume、journal、Schema 验证，覆盖路线图中「可恢复 Run Store」的诉求。Python 内核保留写锁、批准门、失败关闭、恢复计划等**治理语义**——Workflow 工具是通用编排，不含工程变更契约。同时遵守 Bitter Lesson 警告（见第 5 节观察项），内核保持轻量可丢弃。

### 4.2 Review：保留

**框架现状**：Review 编排是纯 Skill 指令，无自建运行时；reviewer 与 Judge 全部是宿主 Subagent（`agents/*.md` 共 8 个定义，安装器软连到 `.claude/agents` 与 `.codex/agents`，install_agentic_framework.py:290-296）。差异全在合同层：五维分派（workflow-code-review/SKILL.md:26）、lightweight/standard 单综合 reviewer（:22-25）、独立 Judge（:10-18、:214-223）、机器产物 `review-report.json`（:279-339）、最多两轮定向复审后转人工（:50-64）。

**与宿主的重叠**：**高**，但重叠在「调度机制」（同源宿主 Subagent），不在「合同」。宿主 `/code-review` 是通用正确性审查，不带工程变更契约。

**处置**：保留。观察项：内置 `/code-review` 零配置，可能分流框架 lightweight 档用户，需留意使用数据。

### 4.3 worktree：保留

**框架现状**：无自建 Git/worktree Runner，只有指令约定——文档明确自认缺口（docs/tooling/13-agentic-workflow-engine-references.md:87）。Skill 指令定义「何时用、失败保留、恢复核对」（delegated-execution-guide.md:47、:64-65、:97）；确定性代码只把 `--parallel-worktree-write` 当 Runtime 升级的路由信号（workflow_control.py:133、:143、:1027），不执行任何 Git 操作。

**与宿主的重叠**：**高**，但零冲突——框架从未自建，宿主原生增强是纯利好。

**处置**：保留规则层（基线路径规则、失败保留策略是宿主不提供的）。可选优化：指令从手写 `git worktree` 命令对齐到宿主 `EnterWorktree` 工具（含 post-create/post-merge hooks）。

### 4.4 安装器：评估双通道

**框架现状**：自建 symlink 分发模型 `scripts/install_agentic_framework.py`（1400+ 行）：双宿主统一建链（:276-327）、manifest v3（:1189-1197）、用户级 registry（:1102-1132）、`--refresh-all` 批量刷新（:1341）、事务快照回滚（:960-1011）、Pack（:70-87）、Overlay 扩展（:20-21、:371、:797）、Windows Developer Mode 提示（:1020-1034）。

**与宿主的重叠**：**中**。官方 plugin 是 skills + hooks + subagents + MCP 打包的单一安装单元，走 marketplace 发现/更新/启用。框架安装器覆盖 skills、subagents、commands 三类资产，**不覆盖** hooks、MCP server 配置、marketplace 通道。反向优势：官方 plugin 只覆盖 `.claude`，框架双宿主（`.codex` + `.claude`）统一分发是 plugin 机制做不到的。

**处置**：评估双通道——Claude Code 侧输出官方 plugin 包（补 hooks/MCP 缺口、获得 marketplace），Codex 侧保留安装器。实施前需设计 plugin 化与 Overlay/Pack/registry 的关系。

### 4.5 Telemetry：不动

**框架现状**：telemetry Pack 仅分发离线脚本 `scripts/analyze_session_metrics.py`（install_agentic_framework.py:316-326），解析宿主已落盘 transcript（analyze_session_metrics.py:1-36）；三层演进定位明确：层 1 离线后处理已落地，层 2 hooks 采集、层 3 OTel 聚合未做（docs/tooling/11-session-telemetry.md:17-23）。

**与宿主的重叠**：**低**，互补——宿主 OTEL 实时导出当前事件，框架离线回溯历史会话，后者是唯一覆盖历史会话的方案。

**处置**：不动。层 2/层 3 的启动条件（先扩样本）依然成立。

### 4.6 权限治理：平行，观察

框架侧对应物是自建批准门（workflow_control.py:551-567）与治理 Profile 守卫（:1090-1118），与宿主 auto mode 无调用关系，属平行实现。语义不同：auto mode 治理「权限提示」，框架批准门治理「变更契约」。观察项：auto mode 默认化改变了「用户在权限提示处把关」的交互模式，需留意对 Production 逐 Task 批准假设的影响。

## 5. 优先级动作清单

### P1：门禁 hooks 化

**问题**：门禁的执行靠 Skill 义务自觉。状态文档反复承认「Prompt 与 Skill 接线不能证明所有模型和所有会话都稳定遵从」。宿主 hooks（PreToolUse/PostToolUse）是把约束从模型搬到 harness 的机制，正是本专题方法论的核心主张。

**方向**：把 `validate_change.py`（Plan/Delivery/Archive 三阶段）、`lint_task_deps.py`、Verify 基线校验等确定性脚本做成宿主 hooks（如 PreToolUse 拦截「无 Plan 门禁直接写代码」的路径）。做成后，门禁从「Skill 描述的义务」变为「宿主强制执行的约束」。

**未核实项**：本复查只核对了 Claude Code 侧 hooks 能力；**Codex 是否有等价 hooks 机制未核实**。双宿主框架不能只在一侧强制执行，实施前需确认 Codex 侧方案。

### P2：Workflow 波次深化

**方向**：落实 SKILL.md:129 已有约定——波次执行段正式走宿主 Workflow 工具，验证「波次数组 → pipeline 映射」与「宿主导入失败 → 框架状态机重试/阻塞联动」两个接缝；Python 内核保留第 4.1 节所列治理语义。

### P3：plugin 双通道评估

**方向**：Claude Code 侧评估输出官方 plugin 包；Codex 侧保留安装器。见第 4.4 节。

### 观察项（不落变更，跟踪即可）

- 内置 `/code-review` 对框架 lightweight 档的分流情况。
- auto mode 对 Production 交互模式的影响（第 4.6 节）。
- Bitter Lesson 警告：每次新模型发布都可能让既有「聪明」控制流变负资产，框架内核必须保持轻量、可丢弃。

## 6. 待决事项

1. P1/P2/P3 是否落变更、先后顺序。按仓库约定，实施时在 `docs/design-docs/<module>/<feature>/` 建 `spec.md` 与 `tasks.md`，本文件作为输入。
2. P1 的 Codex 侧 hooks 等价物确认（第 5 节未核实项）。
3. P3 的 plugin 化与 Overlay/Pack/registry 关系设计。

## 7. 参考资料

外部文章（详见本文生成时的对话检索，均为 2026 年发布）：

- 腾讯云开发者社区《Agent Harness：2026 年 AI 工程的核心范式》，2026-06-25：https://cloud.tencent.com/developer/article/2698416
- 腾讯云 ADP《Harness Engineering 如何驱动云端智能体：腾讯云 ADP 的设计实践》，2026-07-16：https://adp.tencent.com/zh/blog/agent-harness-engineering-adp-practice
- 阿里云开发者社区《AI 不缺智商缺纪律：我的 Harness 工程化实践》，2026-04：https://developer.aliyun.com/article/1740818
- 阿里云开发者社区《从零搭建 Harness Engineering 框架：Rule、Skill、Sub-Agent 等工程落完整路径》：https://developer.aliyun.com/article/1736724

宿主官方来源：

- Claude Code 官方 What's New：https://code.claude.com/docs/zh-CN/whats-new
- 官方 CHANGELOG 汇总：https://releasebot.io/updates/anthropic/claude-code（转载自 `anthropics/claude-code` 官方 CHANGELOG.md）
