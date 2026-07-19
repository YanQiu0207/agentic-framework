# 框架评测策略：分层落地，先零成本兜结构

> 本文把一份通用的 Skill / Harness 评测方法论（来源：仓库根 `notes/skill-evaluation-methods.md`，整理自公众号语料库）映射到本框架的实际现状，给出**可落地、按性价比分层**的评测方案。
> 解决框架长期缺的一块：prompt-native 没有单测兜底，改一处 prompt 可能让别处的触发 / 质量静默退化。

## 一句话原则

**评测 = 考题 + 评分器 + Trace + 人工基线 + 门控 + 回归。**

评分器优先级雷打不动：**确定性脚本 > Rubric（LLM judge）> 人工**。门控用 **AND**——任一关键维度退化就不合入，不用加权平均掩盖。能零 token 用脚本判的，绝不上 LLM。

## 四档分层（按性价比排序）

| 档 | 对应方法论 | 在本框架长什么样 | 成本 | 现状 |
| --- | --- | --- | --- | --- |
| **Tier 0 结构门卫** | 结构门禁 + L1 快速门卫 | `lint_skill_graph.py` / `lint_task_deps.py` / `lint_spec.py` / `check_delivery.py`：引用闭环、frontmatter 完整、档位→reviewer 映射、依赖与必填字段正确性、spec 章节完整性、交付门（任务终态 / 归档 / 工作区干净） | **零 token** | ✅ 已落地 |
| **Tier 1 触发评估** | 触发评估（should / should-not / boundary） | 核心路由 Skill 配 `evaluation/trigger-cases.md`，验 `description` 召回 / 误触发 | 低（单轮、不用 Judge） | ✅ 4 个核心路由 Skill 已有用例、Runner 与逐维基线 |
| **Tier 2 效果评估** | 效果评估 + 考题结构 + Rubric | 仅对改了 reviewer prompt / 路由逻辑的高风险改动，挑 1-2 道考题做 A/B | **高** | ⏳ 按需 |
| **Tier 3 自进化** | skill-evolver 8 阶段 Loop | 自动迭代优化 | 黑洞 | ⛔ 暂不做（前置：先有稳定评测集） |

落地顺序就是这个表的顺序：**Tier 0 零成本先做厚，覆盖面最大；Tier 2/3 押后、按需触发**。

## 本框架的三个特有难点（通用方法论没覆盖）

1. **workflow skill 是链式协作，不是孤立 skill**：测 `workflow-code-generation` 会级联触发 code-review → verification → test-generation。**一道效果评估考题 ≈ 跑半个真实项目**，这是 Tier 2 贵的根因。
2. **输出难确定性断言**：「这次审查有没有抓到该抓的 bug」基本只能 Rubric + LLM judge，要烧 token + 人工校准基线。确定性评分器覆盖不到效果维度。
3. **没有效果 GT / baseline**：4 个核心路由 Skill 已有触发 case，但尚未形成自动执行结果和效果基线。全铺不现实，这正是必须分层、只对核心 Skill 投入的原因。

## Tier 0：L1 结构门卫（零 token，已落地）

`agentic-framework/scripts/lint_skill_graph.py` 是评测体系的 L1 门卫，确定性、可进 CI / pre-commit。当前覆盖：

| 检查 | 拦什么 |
| --- | --- |
| dangling | 动词 / 箭头后引用了「像本框架 skill」但不存在的目标（改名、拼错、未创建） |
| command 目标 | command 指向的 skill 必须存在 |
| name 一致 | SKILL.md frontmatter `name` == 目录名 |
| frontmatter 完整 | 每个 SKILL.md 必须有非空 `description`（触发评估的依据，写歪会召回错） |
| review 档位映射闭环 | `workflow-code-review` 档位表 / 清单引用的每个 reviewer / critic 必须存在于 `agents/` |
| orphan | 无人引用的 skill（warning，不阻断） |

```bash
python scripts/lint_skill_graph.py          # ERROR 即退出码 1
python scripts/lint_skill_graph.py --graph  # 输出引用图，交 LLM 判语义遗漏
# 以下三道门随 workflow-code-generation skill 分发（skills/workflow-code-generation/scripts/）
python skills/workflow-code-generation/scripts/lint_task_deps.py <tasks.md> # tasks.md 依赖与必填字段
python skills/workflow-code-generation/scripts/lint_spec.py <spec.md> --phase design|code  # spec 章节完整性门
python skills/workflow-code-generation/scripts/check_delivery.py --tasks <tasks.md> --spec <spec.md> --review-report <review-report.json>  # 交付门
```

流程门禁的挂点：`lint_spec.py` 挂在 `workflow-system-design` 前置条件（design）与 `workflow-code-generation` 步骤 2（code）；`lint_task_deps.py` 挂在任务规划检查表与执行段 Phase 0；`check_delivery.py` 挂在交付收尾（标准流程与 Fast-Path），非 0 禁止宣布交付。三道门随 skill 安装进目标项目，模板按兄弟 skill 目录解析。这三道门把「AI 自述完成」替换为机器判定；「AI 必须跑门禁」本身仍靠工作流指令遵循，客户端 hook 层强制（如 Claude Code Stop hook）另行立项评估。

**能力边界**：脚本只查「结构对不对、引用通不通」（客观），查不出「引用存在但语义没接对」——后者靠 review 与上层评测。

## Tier 1：触发评估（已有用例、Runner 与基线）

给**核心路由 skill** 配一个轻量评测目录，验 `description` 的召回与误触发：

```text
<skill>/evaluation/
└── trigger-cases.md   # should-trigger / should-not-trigger（含 near-miss）/ boundary
```

样板见 [`skills/workflow-code-review/evaluation/trigger-cases.md`](../../skills/workflow-code-review/evaluation/trigger-cases.md)。[`scripts/evaluation_runner.py`](../../scripts/evaluation_runner.py) 复用这 4 组 Markdown 用例，通过 JSON `stdin` / `stdout` Adapter 合同自动采集 Transcript 与结构化信号，输出版本化 `eval-results.jsonl`、`summary.json` 和 `summary.md`。触发类断言直接检查 Skill 首行标记（如 `Using workflow-code-review`），其余 Tier 1 维度检查确定性信号，不依赖 LLM Judge。

回归基线位于 [`evaluation/baseline/core-agent-behavior.json`](../../evaluation/baseline/core-agent-behavior.json)。Runner 对每个关键维度独立执行最小用例数与通过率门禁，并使用 AND 汇总；任一维度退化即整体失败，其他维度的高分不得抵消。

已覆盖的对象：路由关键的 4 个 skill——`workflow-code-generation`（总入口）、`workflow-code-review`、`workflow-verification`、`workflow-requirements-clarification`，各自 `evaluation/trigger-cases.md`。**不全铺 24 个**，其余按需再补。

## Tier 2 / Tier 3：按需与前置条件

- **Tier 2 效果评估**：只在「改了 reviewer prompt / 改了复杂度路由」这类高风险改动后，挑 1-2 道考题做改前 / 改后 A/B，用 Rubric + 双轨输出（`score.yaml` + `review.md`）。考题结构、三 / 四角色分离（Examiner 模拟多轮用户、Judge 上帝视角）见来源笔记 §7、§11。
- **Tier 3 自进化（skill-evolver）**：方法论 §9 明确「没有稳定评测集前不要做全自动」——会为了通过某个 case 把通用能力改坏。本框架连评测集都在起步，**暂不上**；待 Tier 1 / Tier 2 积累出 dev / holdout / regression 用例后，再对单个瓶颈 skill 用 `eval` / `benchmark` 模式试水（不是 `evolve` 自动迭代，那个最贵）。

## 现状与下一步

- ✅ Tier 0 L1 门卫已含 frontmatter 完整 + 档位映射闭环两条新校验。
- ✅ Tier 1 已为 4 个核心路由 Skill（code-generation / code-review / verification / requirements-clarification）建立 `trigger-cases.md`、自动 Runner、机器结果和逐维回归基线；其余 Skill 按需再补。
- ⏳ Tier 2 / Tier 3 不预置空壳，遇到具体高风险改动或稳定评测集后再启动。
