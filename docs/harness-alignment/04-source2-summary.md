# 文章总结（来源二）：一文读懂 Harness Engineering！

> 来源：《一文读懂Harness Engineering！》，Yousa 博阳（腾讯云开发者）。
> 原文梳理 Anthropic / OpenAI / Cursor / LangChain 过去十五个月的公开工程博客，并对照 2026-03-31 Claude Code v2.1.88 source map 泄露暴露的 51.2 万行源码做交叉验证。不是单一项目案例，是跨公司实践的归纳综述。

## 1. 核心论点

Harness 组件存在的理由不是「它能做什么」，而是「模型做不到什么」。因此 Harness 不是越厚越强——它是一个随模型能力持续变形的**补偿面**，会随模型变强被主动拆除。**护城河不在补偿的厚度，在追踪补偿面迁移的速度。**这是与来源一（`01-source-summary.md`）互补的视角：来源一讲「怎么把 Harness 六个构件搭起来」，来源二讲「搭起来之后，什么时候该拆」。

## 2. 三层壳

| 层级 | 解决的问题 | 关键机制 | 提出方 |
| --- | --- | --- | --- |
| 第一层 | Agent 不听话（记不住、虚标完成、失忆） | JSON 物理锁（只能改状态字段，不能改描述）、三步唤醒仪式（`pwd` / `git log` / `progress.txt`）、Git 存档回滚、Context Reset；OpenAI 走 Repo-as-truth（仓库即唯一现实，linter 强制执行） | Anthropic vs OpenAI，两条路径同一目的 |
| 第二层 | 多 Agent 并发的无政府状态 | Cursor：Planner-Worker-Judge 三层门控 + DAG 引擎硬锁，Worker 未经 Planner 审批不得碰核心代码；Anthropic：借鉴二分查找 / delta debugging，用 GCC 标准答案定位 16 个并行 Claude 写崩 C 编译器的问题 | Cursor、Anthropic |
| 第三层 | 模型对自己工作的盲目自信 | Generator-Evaluator 对抗（GAN 式）、Sprint Contract（双方先谈验收标准）；Cursor 8 通道并行盲审 + 多数投票；严格只读沙盒防止模型篡改测试断言（把 `assert x==5` 改成 `assert True`） | Anthropic、Cursor |

## 3. 补偿面迁移：加法之后的减法

- Opus 4.5/4.6 之后，Anthropic **主动拆掉** Context Reset 和 Sprint Contract——不是未卜先知，是「先用老 Harness 跑一遍，再拆一个组件跑一遍，看数据说话」的实验结果倒逼。
- OpenAI、Cursor 仍在加阶段，尚未进入拆的周期。
- Cursor 独立发现：影响系统行为的因素排序是 Prompt > Harness 结构 > 模型本身——但前提是 Harness 已迭代到三层架构，这是边际影响力，不是基础重要性。
- 结论：声称「最完善 Harness 方案」不是护城河，是负担——组件越厚，意味着对当前模型短板的押注越重，转身越慢。

## 4. Claude Code 源码泄露对账的增量信息

源码验证了前三层理论，且产品实现比公开论文描述得更深：

- **六层记忆体系**：公司级组织策略 → 项目级配置 → 个人偏好 → 会话历史 → 交互中学到的习惯 → 当前对话，上层覆盖下层。
- **autoDream**：只读权限的后台程序，趁空闲整理记忆笔记——合并重复、删矛盾、把相对日期转绝对日期、精简到 200 行以内。
- **Team Mode**：Agent 不是用完即弃的临时工，而是长期驻扎的「队友」——独立上下文 / 独立 Git 工作区 / 点对点邮箱通信，上下文利用率控制在 40% 左右（而非扛到 80%-90% 才崩溃）。
- **Verification Agent**：指令明确要求「try to break it」，输出 PASS / FAIL / PARTIAL 三态判定。
- **44 个 feature flag**：「每次新模型发布拆一个组件」不是方法论口号，是日常操作。

## 5. 账外发现：壳正在从 Harness 向 Infra 蔓延

三个新系统不属于「执行长程任务的必需品」，解决的是「怎么让 Agent 好用、可控、可商业化」：

- **KAIROS**：常驻后台守护程序，自己判断「现在该不该做」，任何会打断用户超过 15 秒的操作自动延后。
- **YOLO Classifier**：风险分级权限判定（放行 / 软拒绝 / 硬拒绝），且会从用户的连续拒绝行为中学习，自动收紧同类操作。
- **Hooks**：流水线 8 个关键节点开放插槽，任何人可挂自己的检查脚本，壳从封闭产品变成开放平台。

## 6. 与来源一的关系

| 维度 | 来源一（白家杰） | 来源二（Yousa 博阳） |
| --- | --- | --- |
| 视角 | 单项目归纳（JK Launcher） | 跨公司综述 + 源码泄露对账 |
| 侧重 | 怎么把六个构件（Rule/Skill/Sub Agent/Workflow/Scripts/MCP）搭起来 | Harness 组件何时该拆、护城河在哪 |
| 独有内容 | 总验证脚本、基线对比、dev-map、任务看板 | 补偿面迁移、并发调试的二分定位、对抗性评估、沙盒防篡改、Team Mode、KAIROS/YOLO/Hooks |

两者不冲突，来源二补的是来源一没有覆盖的「大规模并发调试方法论」「验证防篡改的物理层要求」「组件生命周期治理」三个维度。

## 7. 局限

- 文章是二手综述 + 源码逆向对账，不是作者自己的项目实践，细节可信度依赖被引用公司的公开博客本身的准确性。
- 「补偿面迁移」目前只有 Anthropic 一家给出实证（Opus 4.5→4.6 对比数据未完全公开细节）。
- Claude Code 源码泄露部分基于逆向工程，无法验证是否已是最新实现。
