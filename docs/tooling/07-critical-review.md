# 框架独立批判性评估

> 区别于 [05-industry-comparison.md](05-industry-comparison.md) 的横向对比，本文是一份**独立批判**：补充对比文档没说或说轻了的短板，并标注后续已补的部分。结论以代码与接线为准。

## 一句话结论

这套框架在「执行自主性 × 审查深度」象限确实占右上角，定位（前重后自主、面向大型非生产工具）清醒且差异化。最容易自我麻痹的地方是**把「审查深度」当成「质量深度」**——审查维度做到业界顶配，但「机器可验证」这条腿一度明显短。

## 真正领先的地方

| 维度 | 评价 |
| --- | --- |
| 多维 review + 对抗 critic | 5 维 reviewer + `review-critic` 驳斥层，比 Superpowers 单 reviewer、Spec Kit 静态门都深。这是真差异化。 |
| 前重后自主三段式 | DAG 分波 + worktree 隔离 + 失败隔离，执行形态对标 Superpowers 且多了复杂度路由 Fast-Path。 |
| 知识沉淀闭环 | ADR + arch-snapshot + intent 门，几乎所有竞品都没有。 |
| 零运行时、纯 prompt-native | 跨 Claude Code / Codex 可移植，无锁定，个人开发者采用成本低。 |

## 短板（独立批判）

**1. 客观门禁缺失——曾是定位裂缝。** review-critic 抓的是推理错误，抓不了运行时错误；一段逻辑自洽但跑不起来的代码，5 维 reviewer 都可能放行。「质量深度高」一度实质是「审查深度高」。
> ✅ **已补**：`workflow-verification`（配置驱动 build/test/lint + 基线对比 + 内置 spec drift 检查）已接入执行段，作为 merge 前与 review 并列的机器门。详见 `05` 的「客观门禁」格。

**2. 自主与独立审查的张力。** 模式 A 的 `lightweight` / `standard` 仍由 owner 实现 + 自审 + 自修；`strict` 已将 review 和最终裁决上提给主 agent 或独立 Judge Agent，owner 只修复 keep finding。高风险 task 已实现执行主体分离，低风险档继续接受同模型家族自审的成本权衡。

**3. token 成本无显式预算闸。** 3 档 × 5 维 + critic + 并行 agent + worktree，对功能多的大工具是数量级开销，地板偏高，无显式预算上限。

**4. 方法论是断言而非实测。** 框架对自身有效性没有度量——并行执行是否真比串行缺陷更少，没有 benchmark；手握 `skill-evolver`（带 eval harness）却没拿它验证 workflow skill 本身。
> 🟡 **部分补**：评测体系已分层落地（[08-evaluation-strategy.md](08-evaluation-strategy.md)）——Tier 0 结构门卫零成本接入（`lint_skill_graph` 增 frontmatter / 档位映射闭环），Tier 1 触发评估立样板。但「并行 vs 串行缺陷率」「workflow skill 效果」仍需 Tier 2 / Tier 3 实测，前置评测集尚在起步。

**5. skill 图靠手写 prompt 引用维系，会漂移。** 23+ 个 skill，跨 skill 接线是 prompt 引用，改名/删除/新增易留断点。
> ✅ **已补**：`scripts/lint_skill_graph.py`（dangling / orphan / name 一致 / command 目标）+ `--graph` 输出供 LLM 判语义遗漏。但它只查「目标存不存在、连不连通」，查不出「语义没接对」——后者仍靠 review。

**6. tasks.md 依赖正确性是阿喀琉斯之踵。** 并行分波正确性全压在 `depends_on` 上，而它由人审批，人最不擅长发现「缺失的依赖」，漏一条就可能静默错。
> ✅ **已补**：`skills/workflow-code-generation/scripts/lint_task_deps.py`（dangling 依赖 / 循环依赖 / 「改同一文件却无依赖关系」的并行冲突 / 必填字段）已接入执行段 Phase 0，构建波前机器校验。它给客观信号（文件重叠 + 无依赖），是否真要串行仍由人判断。

## 改进建议（按性价比，标注状态）

| 建议 | 状态 |
| --- | --- |
| 补通用客观门禁（机器能验的不靠 LLM 背书） | ✅ 已做（`workflow-verification`） |
| skill-graph lint（防接线断点） | ✅ 已做（`lint_skill_graph.py`） |
| spec drift 门禁（改代码但不改规格时必须写明原因） | ✅ 已做（`workflow-verification` 内置检查） |
| 高风险 task 的 review 从 owner 剥离，恢复对抗性 | ✅ 已做（`strict` 上提给主 Agent 或独立 Judge） |
| 执行段加 token 预算旋钮 + spend 留痕 | 🟡 已有离线会话遥测，运行时预算闸仍待做 |
| tasks.md 依赖校验（按改动文件重叠自动提示缺失 `depends_on`） | ✅ 已做（`lint_task_deps.py`） |
| 评测体系分层落地（结构门卫 / 触发 / 效果 / 自进化） | 🟡 Tier 0 有 Runner；Tier 1 只有 case 资产，自动执行器待做 |
| 用 `skill-evolver` 实测并行 vs 串行缺陷率 | ⏳ 待做（前置评测集起步中） |

## 总评

**架构判断力一流，质量基建曾偏科。** 审查维度做到了业界顶配，机器验证这条腿在补上 `workflow-verification` 后才算名副其实。严格档的独立审查边界已经补齐；剩余短板是运行时 token 预算、Tier 1 自动执行器和有效性实测。
