# 外部参考：pstack（Cursor 插件技能包）及与当前框架的对照

> 本文档是 `cursor/plugins` 仓库中 pstack 技能包的外部研究与吸收记录，不是当前框架的实现规格。结论来自固定提交的技能原文和 Git 历史；pstack 的技能没有安装或运行。借鉴项以本文「已吸收」一节列出的当前文件为准，进入其他设计前仍须回到当前代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 项目 | pstack，作者 Lauren Tan（poteto） |
| 定位 | 面向 AI 编程 Agent 的工程行为规范：一个总入口、剧本、原则技能、子 Agent 定义和验证技能生成器 |
| 代码仓库 | <https://github.com/cursor/plugins/tree/main/pstack> |
| 分析基准 | `cursor/plugins` main `792440e8a560`（2026-11-21），插件版本 `0.15.46`；Git 历史取自 2026-10-15 之后 |
| 许可 | MIT |
| 规模（实测） | 58 个技能目录，其中 24 个 `principle-*`；22 个剧本；2 个子 Agent；`pstack/` 下 148 份 Markdown，另有 TLA+ 模型、TypeScript 脚本等 400 余个文件 |
| 触发来源 | 微信公众号「程叙架构与AI.」文章，主题为作者认为对抗式审查浪费 token、pstack 转向实证验证与形式化验证 |
| 核实边界 | 读了全部技能原文与 22 个剧本；用 `git log`／`git show --numstat` 核对文章提到的提交；作者推文原文与社区镜像星数没有核对；没有运行任何 pstack 技能 |
| 本地阅读包 | `.learn-by-gpt/pstack/`（已被 `.gitignore` 排除）：中文译文、核心思想、对比与 MkDocs 站点 |

## 一句话定性

pstack 把 token 和流程押在「运行出来的证据」上：少写代码，每一步可验证，把验证能力沉淀成项目自己的、可复跑的技能，人只在不可逆操作和产品取舍上介入。它与当前框架同样强调真实产物取证与子 Agent 规则传递，差异在于 pstack 默认自主执行、不设规划阶段，用复跑证明过滤审查意见；当前框架保留批准门，用 Critic 与 Judge 过滤审查意见，并有机器可核对的证据链。

## 机制要点

**入口与剧本**：`skills/poteto-mode/SKILL.md` 是唯一常用入口，把任务匹配到 22 个剧本之一，并把剧本步骤原样抄进待办清单；没有剧本适合时转 `figure-it-out`，现场设计一个可审计的剧本。回复必须点名影响决策的原则，且只能引用本次会话读过原文的原则。

**原则即技能**：24 条原则各是一个 `principle-*` 技能，`poteto-mode` 只放索引和触发条件；原则和多数技能设 `disable-model-invocation: true`。

**审查只认运行证据**：`interrogate` 的对手 Agent 只负责把变更搞坏，每条发现附命令、实际输出和意图要求的输出，主 Agent 复跑，复现不了的丢弃；风格、命名和假设性风险不报。现行 `poteto-mode` 只在设计有争议时路由到它。`blast-radius` 把「安全事实」的确信度分 5 级（说了、指出代码行、推演证明、跑脚本、在应用中复现）。

**验证技能生成**：`create-verification-skill` 从代码库推出 Launch、Doctor、Drive、Evidence、Cleanup 五部分和功能地图，生成后必须端到端跑一次；`create-formal-verification-skill` 在 bug 代价最高、测试最够不到的地方证明一条性质，检查必须先在故意改坏的代码上失败，现有代码违反性质时如实报告反例；对应的 `maintain-*` 技能处理漂移。

**纠错入结构**：`correct` 的落点顺序是架构、类型、能指明修法的 lint、测试，最后才是文档，并在指令文件里维护「规则 ↔ 强制手段」对照表。

**委派纪律**：启动子 Agent 时第一行要求读 `worker.md`；`worker.md` 规定「The bar in your kickoff is the whole bar」，子 Agent 不追加门禁，只为本 head 的失败或用户会遇到的 bug 阻塞，基线已有问题用一行报告。

**多模型与自主**：评审组默认 3 个厂商各一席，交叉评审不与父会话同厂商；`setup-pstack` 按角色写模型配置。可逆工作不问人，强推共享分支、部署、删数据、对外消息才停；Shipping 剧本只认非作者 Agent 实际运行给出的裁决，「Green CI and an approving bot review are not verdicts」。

**作者对自身工具做减法**：#1043（2026-10-27）删除 Orchestrate 背后的 `orch.ts`、`store.ts` 和测试共 3066 行；#1249（2026-11-16）删除 `orchestrate` 剧本本身，新增 `worker.md`。

## 文章说法核对

| 文章说法 | 仓库事实 |
| --- | --- |
| 31 条原则 | 2026-10-16、11-03、11-15、11-21 四个时点均为 24 个 `principle-*` |
| 本体是 58 个纯 Markdown 文件 | 58 是技能目录数；Markdown 共 148 份，另有大量非 Markdown 文件 |
| 23 个剧本含 orchestrate | 11-16 前正确，#1249 后为 22 个 |
| 默认 Grok 承担代码委派 | 已过时；现行默认为 Opus 5.5，`setup-pstack` 把 `grok-*` 视为旧默认值 |
| 删除 3066 行 orch 脚本 | 与 #1043 的 `--numstat` 一致（590 + 1681 + 795） |
| 10-27 #986 重写 interrogate | 存在该提交并修改 interrogate；重写细节未逐行核对 |

## 与当前框架的对照

| 维度 | pstack | 当前框架（证据） |
| --- | --- | --- |
| 真实产物取证 | Prove It Works 原则 | 交付门逐字引用原始输出（`skills/workflow-code-generation/SKILL.md`「交付」节）；不接受「应该没问题」（`skills/workflow-verification/SKILL.md`） |
| 子 Agent 先读规则 | `worker.md` | owner／implementer 编码前自行读取 `AGENTS.md`／`CLAUDE.md`（`skills/workflow-code-generation/reference/delegated-execution-guide.md` Phase 1） |
| 入口 | 单一总入口 + 剧本 | 按阶段拆入口，编码按风险分 4 档 |
| 规划 | 「the best spec is code」，无规划技能 | 中等及以上任务先 spec／tasks 并批准 |
| 审查 | 复跑证明的发现才保留 | 综合／五维审查，strict 加 Critic 与独立 Judge（`skills/workflow-code-review/SKILL.md`） |
| 验证 | 核心环节，生成项目级验证技能 | Verify 默认不启用，需用户明确要求 |
| 自主 | 可逆工作不问人，可过夜跑到合并 | 关键节点批准；push 由用户决定 |
| 多模型 | 按角色配模型，跨厂商评审 | Agent 均为 `model: inherit` |
| 知识与证据链 | 无知识库；无一致性校验 | `openspec/`；Review、Verify 与当前内容按 `subject_id` 绑定 |

## 已吸收（2026-11-22）

| 候选 | pstack 来源 | 落点 |
| --- | --- | --- |
| 审查发现分证据等级（推理／代码／复现），可低成本复现的 P0/P1 先复现 | `blast-radius`、`interrogate` | `skills/workflow-code-review/reference/reviewer-prompts.md` 的 `[Evidence]` 与汇总模板；`agents/review-critic.md` 规则 5（证据不足且复现不了的给 `not_proven`） |
| 审查和编码子 Agent 只按给定标准工作，基线问题一行报告 | `worker.md` | `reviewer-prompts.md`（基线问题不计 P0/P1，假设性风险最多 P2）；`delegated-execution-guide.md` Phase 1 第 1 条 |
| 先审测得的数字再使用 | Explain the Number、`benchmark-checklist` | `skills/bp-performance-optimization/SKILL.md`「测量数字审查」；`agents/performance-reviewer.md` 规则 3 |
| 缺陷修复留下失败→通过的证据；新测试说明能抓住哪种错误 | Bug fix 剧本、`tdd`、Test Behavior 原则 | `skills/workflow-test-generation/SKILL.md` 强制规则 7、9（「先红后绿」原已存在） |
| 纠错落点优先级与「规则 → 强制手段」对照表 | `correct` | `skills/self-refinement/SKILL.md` Step 2、建议模板、Step 6 |

吸收时的取舍：

- 没有照搬「复现不了就丢弃」：设计、契约类问题往往无法运行，仍由 Critic 与 Judge 判断。
- 没有要求「失败测试先于修复单独提交」：交付提交由编排方完成，单独提交一个失败状态会让逐提交检查失败；改为要求在摘要中附修复前失败、修复后通过的输出。

## 不采用

- **取消或大幅削弱审查**：作者的依据是个人经验；本框架已有评测，`evaluation/review/historical-pilot/README.md` 记录 strict 四案的三组输出在独立盲评中各命中 3/4 个预注册目标。
- **默认自主到合并**（Autonomous run、Autopilot、Shipping）：与批准门和「push 由用户决定」冲突，且依赖 GitHub PR 栈、Cursor 云 Agent 和 `/loop`。
- **按角色配置模型**：依赖 Cursor 的模型 slug 与 Task 参数，收益不明。
- **单一总入口加剧本路由**：迁移成本高于收益；剧本中的个别步骤可作为现有 Skill 的参考。
- **形式化验证作为常规能力**：只对并发、协议、状态机密集的项目划算；需要时按 `create-formal-verification-skill` 的「检查必须见过失败、如实报告反例、记录同步提交」三条执行。

## 待评估候选

- Verify 增加「驱动真实产物」的检查配方（参考 `create-verification-skill` 的五段结构）。
- 交接文档或交付报告对照会话转录核对（参考 `show-me-your-work` 的审计步骤）。
- `evaluation/` 对候选方盲测：候选看不到评测字眼，不让候选自报用了哪些技能。
- strict 档的 Judge 或 Critic 由另一个宿主执行，先在 `evaluation/` 试点。

## 缺失证据

- 没有运行 pstack 的任何技能或剧本，行为描述以技能原文为准。
- 作者「审查价值低」的判断没有在 pstack 仓库中找到对应评测。
- 本次吸收的 5 项只做了文本与引用图检查，尚无效果评测。
