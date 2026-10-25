# 宿主与竞品增量核验（2026-10）

> 继 07 号《宿主原生能力对齐复查（2026-09）》之后的增量核验：窗口 2026-08-25 → 2026-10-25，覆盖宿主（Claude Code、Codex）、竞品与模型层三面，末尾给出 6 条跟进清单。属于「调研 + 规划」，不是 feature spec；实施项另走 `docs/design-docs/` 流程。

**更新日期**：2026-10-25（change 2049 落盘）
**证据分级**：〔官方〕官方 changelog / docs / Releases 直接确认；〔实测〕本机命令或 GitHub API 直接测量（2026-10-25）；〔社区〕社区口径、本次未复核。关键未确认项在正文显式标注。

## 1. 背景

07 号文档（2026-09-12）对标了 Claude Code 2026 年原生能力，给出 P1 门禁 hooks 化、P2 Workflow 波次深化、P3 plugin 双通道三个动作。此后两个月：

- Claude Code 完成模型全系换代（Fable / Opus / Sonnet / Haiku 5.5），新增 Claude Mods（宿主深层行为改造）与组织级 Code Review（GA），交互会话默认切到 auto mode；
- Codex 端 GPT-5.5 的 ChatGPT 登录形态退役，CLI daemon 化，hooks 体系与 9 月核验结论一致；
- 竞品侧 Comet 发布 0.5.0（补齐 SDK / Dashboard / Eval），superpowers 暴露并修复一起 Skill compaction 存活事故；
- 模型层 GPT-6.x、Gemini 4、DeepSeek V4.1 相继发布，`sonnet-4-5` 进入退役倒计时。

先更正一个背景认知（本次调研的副产物）：框架的批准语义不是「逐 Task 批准」——自 change 2029 起，`workflow_control.py` 缺省为 `risk-triggered` 批准模式（`APPROVAL_MODES` :52、`approval_mode()` :550 缺省返回 `risk-triggered`），即批准 tasks.md 后自主连跑，仅在 scope-change / irreversible / gate-failure / assumption-broken / user-requested 五类风险时暂停批准。07 号 :84 观察项的过时措辞由 change 2049 同步更正，本文观察项均按此语义展开。

## 2. 宿主增量

### 2.1 Claude Code 版本线（2.1.257 → 2.1.310）

| 版本 | 内容 | 与框架的关系 | 证据 |
| --- | --- | --- | --- |
| 2.1.248 | `--restricted` 启动模式（受限环境 / 评测 harness 用） | 行为级评测（跟进 2）的宿主入口之一 | 〔官方〕 |
| 2.1.257 | Fable 5.1 上线 | 模型基线更新 | 〔官方〕 |
| 2.1.233/268/277 | 新模型移除 Todo/Task 工具；TaskOutput 工具删除 | 依赖旧工具的 Skill 与评测脚本需查兼容性 | 〔官方〕 |
| 2.1.277/281 | 支持 AGENTS.md（无 CLAUDE.md 时读取） | 双宿主配置收敛机会（跟进 4） | 〔官方〕 |
| 2.1.280 | Opus 5.5 上线；Pro/Team 订阅默认模型 Sonnet → Opus | 模型基线更新 | 〔官方〕 |
| 2.1.283 | `/doctor prompt-audit`（提示词体检） | Skill 与文档质量体检工具（跟进 4） | 〔官方〕 |
| 2.1.284 | Sonnet 5.5 上线；ultracode 独立开关；交互会话默认 auto mode | 与批准门平行（07 §4.6），把关点移向风险升级（跟进 5） | 〔官方〕 |
| 2.1.287 | Claude Mods：TS 函数改写宿主深层行为（不沙箱） | 门禁执行新通道，但安全边界弱于 hooks 且 Codex 无对应物（跟进 3） | 〔官方〕 |
| 2.1.293 | Haiku 5.5 上线 | 模型基线更新 | 〔官方〕 |
| 2.1.295 | hooks 支持 `onFailure: "block"`（fail-closed） | 门禁 hooks 化（07 P1）的失败语义可用 | 〔官方〕 |
| 2.1.299 | idle compaction：200K+ 会话空闲约 54 分钟自动压缩 | 上下文治理宿主化；Skill compaction 存活问题更显性（跟进 1） | 〔官方〕 |
| 2.1.302 | `claude -p` 默认 Manual 批准；fork 子代理成为全端默认 | 子代理编排成为默认形态，与「主会话只编排」模式同向 | 〔官方〕 |
| 2.1.304 | Code Review GA（官方称提速约 3 倍）；组织级 Quick/Standard/Deep 分档 | 与框架 Review 分档重叠，边界待定（跟进 5） | 〔官方〕 |
| 2.1.310 | Monitor 工具扩展到 Bedrock / Vertex / Foundry | 无直接影响，记录备查 | 〔官方〕 |

发布日期（〔官方〕changelog）：2.1.257 = 2026-09-01、2.1.280 = 2026-09-22、2.1.284 = 2026-09-28、2.1.287 = 2026-10-01、2.1.293 = 2026-10-07、2.1.304 = 2026-10-15；其余条目本次未逐条记录发布日期。

### 2.2 重点一：Code Review GA 与框架 Review 分档

2.1.304 起，宿主 `/code-review` GA 且支持组织级 Quick / Standard / Deep 三档，官方称提速约 3 倍。框架的 Review 分档（`review_profile: standard / lightweight`）与多维评审与之重叠。处置倾向（跟进 5 观察项）：宿主 Code Review 适合作第一道快筛，框架多维评审（含 Judge 独立性）保留为最终语义门；不急于改，先在真实变更上对比两者的 finding 重合度。

### 2.3 重点二：idle compaction 与 Skill 存活

2.1.299 起 200K+ 会话空闲约 54 分钟即自动压缩；叠加既有手动 compaction，Skill 的长会话存活成为一等风险。竞品 superpowers 已实际踩雷（§3.2）：compaction 后只回挂 Skill 前 20,000 字符，写在 Skill 后半段的约束因此丢失。框架 27 个 Skills 中存在多个长文 Skill，暴露于同一机制——这是跟进 1（新增 P0）的直接依据。

### 2.4 重点三：Claude Mods

2.1.287 的 Mods 允许用 TS 函数改写宿主深层行为（权限判定、工具路由等），官方明示不沙箱。对框架是双刃：门禁执行可以更深（不止 PreToolUse 拦截），但安全边界弱于 hooks，且 Codex 无对应机制。跟进 3 的结论：hooks 仍是双宿主公约数与主通道；Mods 只作为 Claude 侧的观察性增强，不进入承诺路径。

### 2.5 Codex

| 事项 | 内容 | 证据 |
| --- | --- | --- |
| GPT-5.5 登录形态退役 | 2026-10-14 起，ChatGPT 登录的 Codex 不再可用 GPT-5.5 | 〔官方〕 |
| daemon 自启 | 0.157.0（2026-09-25）起 daemon 可自启常驻 | 〔官方〕 |
| DevDay 新入口 | 语音交互、`/agents`、`/presets`（2026-09-29 DevDay 前后） | 〔官方〕 |
| hooks 体系 | 与 07 号 P1 节 9 月核验结论一致，无破坏性变化 | 〔官方〕+ 07 号存档 |

对框架：P1 门禁 hooks 化的前提（双宿主均有 hooks）不变；模型退役影响双宿主评测的基线选择（与跟进 4 的模型 ID 清理一并处理）。

## 3. 竞品动作（GitHub API 2026-10-25 实测）

### 3.1 同域项目版本线

| 项目 | Star（实测 2026-10-25） | 最新版本 | 窗口内动作 | 证据 |
| --- | --- | --- | --- | --- |
| Comet | 3,230 | v0.5.0（10-23） | 新增 Comet Any、SDK（约 14 项能力）、Dashboard、Eval | 〔实测〕GitHub API + Releases |
| spec-kit | 142,737 | v1.2.3 | 常规迭代 | 〔实测〕GitHub API |
| OpenSpec | 72,913 | v1.15.0（10-24） | 常规迭代 | 〔实测〕GitHub API |
| superpowers | 304,650（异常，待复核） | v7.0.1（10-21） | compaction 存活事故修复与 Skill 重构（§3.2） | 〔实测〕GitHub API；star 数待复核 |
| BMAD | 54,519 | v7.0.0（10-10） | 大版本 | 〔实测〕GitHub API |
| Taskmaster | 28,271 | — | 窗口内无版本动作，最近实质更新停在 2026-04-28，项目趋于停滞 | 〔实测〕GitHub API |

superpowers 的 star 数与 9 月社区口径（3-4 万）差一个量级，疑似抓取口径或统计异常，标注待复核；不影响其版本动作结论。

### 3.2 superpowers 的 compaction 存活事故（跟进 1 的直接依据）

v7.0.1（2026-10-21）前后的社区披露：compaction 后宿主只回挂 Skill 前 20,000 字符，写在 Skill 更后位置的轮次上限约束因此丢失，实测 5 轮上限的任务跑成 18 轮。修复路线：把长 Skill 重构为「主文件短 + references/ 渐进加载」，并加约 20,000 字符的体积红线测试防回归。

对框架的含义：这不是 superpowers 的个例，而是宿主 compaction 回挂机制的结构性约束。框架 Skill 体系（含 workflow-code-generation 等长文 Skill）与 superpowers 同构，应视为已知风险而非他山叙事。事故细节属〔社区〕级证据，机制数字（20,000 字符）列入跟进 1 实施时的本地验证项。

### 3.3 Comet 0.5.0

Comet 从 0.4 系到 0.5.0（10-23）补齐三块：Comet Any（入口形态）、SDK（约 14 项能力，把编排暴露为可编程接口）、Dashboard 与 Eval（运行面板 + 评测闭环）。对框架：评测闭环（约 20 个确定性场景）被对手先交卷，跟进 2 升级为 P0；SDK 化方向与 native-first（change 2028 落地）同向，维持既有路线即可（跟进 6）。相对既有对照文档（`openspec/specs/backend/engineering/tech/external-reference-comet.md`，基于 0.4.0）的 0.5.0 增量补录，因该文件存在另一会话的未提交改动，另行开 Change 处理。

## 4. 模型层变量

| 事项 | 内容 | 证据 |
| --- | --- | --- |
| Claude 5.5 全系 | Fable 5.1（9-1）、Opus 5.5（9-22）、Sonnet 5.5（9-28，$2/$10 每百万 token）、Haiku 5.5（10-7） | 〔官方〕 |
| GPT-6 Sol / Luna | 9-22 发布；Sol 约 1M 上下文为社区口径，未官方确认 | 〔官方〕发布 + 〔社区〕上下文数字 |
| GPT-6.1 Sol | 9-29 发布，价格约为前代 1/5 | 〔官方〕 |
| GPT-6.1 Astra | 发布后因对齐回归撤回 | 〔社区〕，未见官方撤回公告，标注未验证 |
| Gemini 4 Argon | 9-30 宣布、10-13 开放 | 〔官方〕 |
| DeepSeek V4.1 Flash | 9-10 发布 | 〔官方〕 |
| sonnet-4-5 退役 | 2026-11-30 退役 | 〔官方〕 |
| Claude API 2026-10-21 | API 新版本含破坏性变更 | 〔官方〕 |
| Agent SDK 订阅计费 | 窗口内多次调整（口径反复） | 〔官方〕+〔社区〕 |
| MCP | 2026-07-28 去状态化规范后生态持续铺开 | 〔官方〕 |
| Kimi K3.1 | 传闻，未验证 | 〔社区〕传闻，不跟进 |

对框架：评测与文档中的模型引用需随退役节奏清理（跟进 4）；GPT-6.x / Gemini 4 的快速迭代进一步支持「评测场景不绑单一模型」。

## 5. 跟进清单

按优先级 6 条；均为「调研 + 规划」产出，实施各自走 `docs/design-docs/` 流程，不在文档层直接动手。

| # | 级别 | 事项 | 依据 | 动作要点 |
| --- | --- | --- | --- | --- |
| 1 | 【新增 P0】 | Skill 压缩与 compaction 存活改造 | §2.3 + §3.2（superpowers 事故） | `/skill-doctor` 全量体检 + Skills 体积审计；长 Skill 重构为「主文件短 + references/ 渐进加载」；加体积红线测试（对齐宿主回挂上限）防回归 |
| 2 | 【P0 升级】 | 行为级评测闭环 | §3.3（Comet 0.5.0 已交卷）+ 宿主 `--restricted` / `claude plugin eval` | 选约 20 个确定性场景（三阶段门禁触发、批准升级、Delta 闭环等）做成可重复评测；先 `--restricted` 后 plugin eval 双通道评估 |
| 3 | 【P1 修订】 | 门禁 hooks 化 → hooks 为主、Mods 为辅 | §2.4（Mods 不沙箱、Codex 无对应）+ 07 号 P1（hooks 双宿主已核验） | 主通道维持 hooks（`onFailure: "block"` 提供 fail-closed 语义）；Mods 仅 Claude 侧观察，不进承诺路径 |
| 4 | 低成本立即做 | 提示与模型基线清理 | §2.1（`/doctor prompt-audit`、AGENTS.md）+ §4（sonnet-4-5 退役） | 跑一次 `/doctor prompt-audit` 体检 Skills 与 CLAUDE.md；全仓清理旧模型 ID（sonnet-4-5 等）；评估 AGENTS.md 单源收敛（CLAUDE.md 已 @ 转发，宿主 2.1.277/281 起直读 AGENTS.md） |
| 5 | 观察项升级 | 两个边界观察 | §2.2 + §2.1（auto mode 默认化） | ① auto mode 默认化 × 框架风险触发暂停批准：确认 irreversible / scope-change 升级条件在宿主默认少确认的环境下仍覆盖关键把关点；② 宿主 Code Review GA × 框架 Review 分档：真实变更上对比 finding 重合度，再定吸收边界 |
| 6 | 维持 | native-first 不动摇 | §3.3（Comet SDK 化同向） | native delivery 路线（change 2028 落地）继续；对手 SDK 化印证「运行时可编程」方向，无路线修正 |

## 6. 来源与证据分级说明

- Claude Code：官方 changelog（anthropics/claude-code 仓库 CHANGELOG.md）逐版本条目，〔官方〕级；发布日期以 changelog 标注为准。
- Codex：官方文档与 changelog，〔官方〕级；hooks 结论沿用 07 号 P1 节 2026-09-12 核验记录。
- 竞品版本与 star：GitHub API 经 `gh api` 实测（2026-10-25），〔实测〕级；superpowers star 数异常已标注待复核。
- superpowers compaction 事故：社区披露（v7.0.1 前后），〔社区〕级；机制数字（回挂 20,000 字符）未在官方文档复核，按事故报告采信并列入跟进 1 的本地验证项。
- 模型层：各厂商官方公告〔官方〕级；GPT-6 Sol 上下文数字、GPT-6.1 Astra 撤回、Kimi K3.1 为〔社区〕口径，正文已逐条标注。
- 本文不重复 07 号的历史基线，两文配合阅读。
