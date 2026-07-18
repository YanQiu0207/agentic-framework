# 会话遥测体系：设计决策与演进路线

## 结论

框架的可监测性按三层演进，当前只落地第一层：**transcript 后处理**（`scripts/analyze_session_metrics.py`）。它不采集任何数据，只消费 Claude Code 与 Codex 本来就在落盘的会话记录，回溯重建每个工作流阶段的耗时、token、子 agent 成本和 review 结论轨迹。零运行时侵入，历史会话全部可回溯。

本文记录第一层的设计决策与指标解读边界，以及第二、三层的启动条件。脚本用法见 README 与脚本 docstring，本文不重复。

## 解决什么问题

- 「简单改动为什么耗时」这类问题此前只能靠感觉；排查 review 循环耗时问题时，全部证据都要临时手工翻 transcript。
- [10-harness-engineering-practices.md](10-harness-engineering-practices.md) 缺口 1「为执行过程增加轻量、结构化的运行指标」需要落点。
- [ADR 003](adr/003-review-fix-loop-convergence.md)（review 循环收敛）需要观测口验证「质量是否受损」：复审轮新增 P0/P1 比例、需人工率。

## 三层架构与当前落点

| 层 | 机制 | 状态 | 启动条件 |
|---|---|---|---|
| 1. transcript 后处理 | 手动跑脚本，解析已落盘会话数据 | ✅ 已落地 | — |
| 2. hooks 常态采集 | PreToolUse / PostToolUse / SubagentStop 等客户端 hook 实时写 `.phase-metrics.jsonl` | ⏳ 未做 | 第一层的启发式锚点被证明不够可靠，或需要实时指标时 |
| 3. OTel 聚合 | 官方遥测导出，跨项目仪表盘 | ⏳ 未做 | 有多项目横向对比诉求时 |

先做第一层的理由：唯一能覆盖**历史会话**的方案；第二、三层只对启用后的会话生效，且要配置维护。

## 第一层设计决策

### 数据源：复用落盘数据，不新建采集

两个 CLI 都已完整落盘：

- Claude Code：`~/.claude/projects/<proj>/<session>.jsonl`，每条 assistant 消息带 `usage`（四类 token）与时间戳；子 agent 转录在伴生目录 `<session>/subagents/`，`meta.json` 带 `agentType`，reviewer 成本可按类型归账。
- Codex：`~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`，token 在 `event_msg/token_count` 事件里，`session_meta.cwd` 可按项目过滤（Codex 会话集中存放不分项目）。

**风险**：两者都是 CLI 内部实现格式，不是稳定 API，版本升级可能需要适配解析。这是第二层（hook 是官方接口）的存在理由之一。

### 阶段锚点：三类，且放弃 tool_result 里的标记

切阶段的锚点：assistant 正文的 skill 首行标记（`Using workflow-xxx`，两源通用）；Claude 额外识别 `Skill` 工具调用和 `<command-name>` 命令注入。

**踩坑记录**：最初把出现在任何位置的标记都当锚点，实测发现 skill 正文（含标记原文）会通过 Read 工具返回值、Skill 工具返回值大量进入上下文——某会话 grep 到 21 处标记，真正的 assistant 回显只有 1 处。故只认 assistant 主动输出与显式加载动作，**不认工具返回值**。同类误报源：assistant 正文以列表罗列标记示例（`- Using xxx`），2026-07 起列表前缀不认，引用 / 加粗 / 反引号包裹仍认。

框架强制每个 workflow skill 首行输出标记，原本是给触发评估（[08-evaluation-strategy.md](08-evaluation-strategy.md) Tier 1）做确定性判据的，在这里兑现了第二个用途：阶段边界。

### Codex token：累计值差分，不直接累加事件

`token_count` 事件携带的 `total_token_usage` 是会话累计值。直接累加各事件的 `last_token_usage` 会被重复事件污染；取相邻事件累计值的差分，重复事件差分为 0，天然去重。

### 质量账与任务归因：格式即接口

review 结论轨迹（`首审 NEEDS_CHANGES(P1×5) → 复审1 PASS`）的提取完全依赖 `workflow-code-review` 的固定报告格式（`# Code Review 报告` + `## 总体结论` + `**轮次**` 字段 + `P{n}-{seq}` 编号 + 复审报告新 finding 的「（新增）」标记）。该格式是框架「整个系统唯一固定格式」，在这里兑现第二个用途：机器可解析的质量数据源。**改报告模板 = 改遥测接口**，动模板前先看本文。

ADR 003 两个质量验证指标的口径：

- **复审轮新增 P0/P1 比例** = 出现「（新增）」P0/P1 finding 的复审轮数 / 复审轮总数，衡量修复引入新问题的频率。
- **需人工率** = 需人工终止的循环数 / 修复-复审循环总数。循环由首审 `NEEDS_CHANGES` 开启；无首审报告的验证类修复复审链（SKILL.md 复审模式的验证类路径）在首个复审报告处开启，同样计为一个循环——否则其需人工终态会计入分子而分母不覆盖，比例可超 100%。

「需人工」不设显式标记，由「复审第 2 轮 + `NEEDS_CHANGES`」确定性推出——推导依赖 SKILL.md 与 ADR 003 固定的轮次上限（复审最多 2 轮），**改轮次上限 = 改遥测接口**。选推导不选显式标记的理由：轮次与结论是每份报告必有字段，格式遵从在每次 review 都被练习；显式需人工标记只在罕见路径出现，LLM 遗漏风险高。

循环归属按输出流分组（主链与每个子 agent 各自成流），避免并行 task owner 各自的 review 循环按时间戳交错串账。

统一交付报告的「任务归因」区块记录 `feature`、`task`、`review_profile`、`review_retries`、`verify_retries` 和 `manual_intervention`。脚本只消费这 6 个固定字段，不从其他对话推测；缺少完整区块的旧报告返回空列表。同一会话重复输出相同 feature/task 时，账本保留最后一份完整记录。

### 其他口径

- **活跃时长**：相邻条目间隔之和，单个间隔超过 `--idle-gap`（默认 300 秒）的部分按「等用户」剔除，避免人离开把阶段耗时撑大。
- **费率不硬编码**：成本折算走 `--rates` 外部费率表，过期费率产出错误数字的责任不进脚本。
- **账本**：`--history` 按 (source, session) upsert——新会话追加，已有会话用最新解析覆盖，进行中的会话入账后重跑自愈，不会冻结不完整快照。为「改 skill 前后对比」积累基线，衔接 08 号文档 Tier 2 效果评估的 trace 需求；条目带 `started_at` / `ended_at`（UTC），支撑前后对比的时间排序。本项目账本固定在 `agentic-framework/metrics/session-history.jsonl`，随 git 提交。已知限制：写入为全量重写、非原子，进程中断可能截断文件；账本进 git 且可从源 transcript 重跑重建，损坏时 git 恢复后重跑即可。

## 指标解读注意事项

- 「(未标记)」段 = 首个锚点前的全部活动（含纯对话），不代表异常。
- 内置命令（`/exit`、`/clear`）也是锚点，其后的闲聊会挂在该命令名下。
- Codex 会话子 agent 列恒为 0：Codex 不落盘子 agent 独立转录，是数据源限制不是脚本缺陷。
- Codex 侧若模型未按 skill 要求回显首行标记，该段归入「(未标记)」。
- fork 出来的 Codex 会话首个 token 差分可能含父会话累计量，账面表现为首条虚高。
- 子 agent 的 token 总量精确，但按启动时间整体归入启动时所处阶段，跨阶段运行的子 agent 不拆分；时间归属同为近似。
- 轮次字段是 2026-07 加入模板的，此前的历史报告无轮次——这些报告在轨迹中标「?」，且不进入「复审轮新增 P0/P1 比例」「需人工率」两个指标的分子分母。
- 首审 `NEEDS_CHANGES` 后无后续复审报告的循环（用户中断、会话截断）计为「未收敛」，不算需人工。

## 已产出的实测结论

- review 重的是 Judge 编排而非 reviewer 本身：一次 strict review 会话中主链 Judge 消耗 326k output token，7 个 reviewer 子 agent 合计仅 46.5k（约 7:1）。这是 ADR 003 砍「重复全量重审」而非砍 reviewer 数量的数据依据。
- 修复循环轨迹可直接观测：`NEEDS_CHANGES(P1×5) → PASS` 即一次两轮收敛的循环。

## 演进路线

1. **积累账本**：持续 `--history` 收数据，账本在 `metrics/session-history.jsonl` 随 git 提交。「复审轮新增 P0/P1 比例」「需人工率」两个指标（ADR 003 的质量验证口）的解析已实现（2026-07：报告模板加轮次字段与「（新增）」标记，脚本按流分组重建循环）；指标要有意义还需账本里积累足够多带轮次标记的新会话。2026-07 首次遵从率验证识别出 3 条新轨迹，均带明确轮次；账本中的 4 份「?」来自旧格式报告，因此暂不加固模板措辞。
2. **任务级归因字段**（2026-07 已落地）：统一交付报告携带 feature/task 标识、风险档位、review/verify 重试次数和人工介入位置；脚本写入账本顶层 `task_attributions`，支持按任务分析返工来源。
3. **第二层 hooks**：满足上表启动条件时再上；skill 首行标记可同步升级为结构化事件。
4. **第三层 OTel**：有跨项目对比诉求时评估。
