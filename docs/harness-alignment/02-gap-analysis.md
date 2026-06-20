# 框架对比：文章实践 × 本框架现状

> 对照对象：本专题总结的 Harness 实践（见 [01-source-summary.md](01-source-summary.md)）与本框架 agentic-engineering-framework 的当前实现。
> 证据以 `file:line` 标注，可直接跳转核对。

## 1. 定位差异

两套体系出发点相反，落点也不同：

| 维度 | 文章（JK Launcher） | 本框架 |
| --- | --- | --- |
| 方法论 | 归纳——真实项目踩坑演化 | 演绎——3 公理 → 6 实践 → 框架（`agentic_engineering.md:137`、`:228`） |
| 核心载体 | 多 Agent（7 常驻角色）+ Scripts | Skill（Agent-Agnostic 纯 Markdown，`agentic_engineering.md:369`、`:506`） |
| 多 Agent 形态 | 中央 PM 全程路由 7 固定角色 | Workflow Skill 驱动，仅评审阶段并行 subagent（`skills/workflow-code-review/SKILL.md:12`） |
| 编排者 | 独立 PM Agent（Orchestrator） | 主 Agent / Workflow Skill（无独立 PM 角色） |
| 平台 | 强绑 Cursor | Agent-Agnostic（Claude Code / Cursor / CodeBuddy / Codex 通用） |

结论：文章里大部分「可落地点」，本框架已经有了，而且做得更细。真正的 gap 集中在「可执行脚本门禁」。

## 2. 主对照表

| 文章落地点 | 本框架状态 | 证据 |
| --- | --- | --- |
| SPEC 先行、禁模糊词 | ✅ 已有，更强 | `workflow-requirements-clarification` + spec 模板；实践 1.1 Spec-First |
| Rule（红线约束） | ✅ 已有 | `std-*` 规范 + Rules 全量预加载（`agentic_engineering.md:392`） |
| Skill（动作标准化） | ✅ 整个框架就是这个 | 26 个 `SKILL.md` |
| 多 Agent 角色拆分 | ✅ 已有（形态不同） | 评审 5 reviewer + critic + Judge（`skills/workflow-code-review/SKILL.md:12`） |
| 代码审查 | ✅ 远强于文章 | 文章 1 个审查 Agent；本框架五维 + 对抗性 critic（`skills/workflow-code-review/SKILL.md:118`） |
| 下游不改上游、中央路由 | ✅ 等价物 | Judge 模式：reviewer 只报 finding 不改（`skills/workflow-code-review/SKILL.md:10`） |
| 角色契约（I/O 边界） | ✅ 已有 | 各 reviewer subagent 职责固定；SKILL 有明确输入输出 |
| 知识库 / 索引 | 🟡 部分 | `project-knowledge` 有 `architecture/overview.md`，但偏架构级（`skills/project-knowledge/SKILL.md:53`） |
| 错题晋级 / 反馈闭环 | ✅ 已有，精准对应 | `self-refinement` 自动 + 手动（实践 6） |
| 上下文纪律 / 按需加载 | ✅ 已有，理论化 | L1 / L2 / L3 三层渐进式披露（`agentic_engineering.md:384`） |
| Memory 靠边站、知识进仓库 | ✅ 已有 | Docs as Code + Knowledge as Code（实践 1.2 / 5） |
| 复杂度路由 | ✅ 文章没有，本框架更先进 | `skills/workflow-code-generation/SKILL.md:14`、`skills/workflow-requirements-clarification/SKILL.md:86` |
| **总验证脚本（硬门禁）** | ❌ 缺 | 全 repo 无 `.ps1` / `.py` / `.sh`（Glob 验证） |
| **基线对比（前后 diff）** | ❌ 缺 | 同上，依赖脚本 |
| 流程定义文件 + 流程校验脚本 | 🟡 设计取舍 | 流程写在 `SKILL.md`，无独立状态机文件 |
| per-Agent 模型分档 | ➖ 不适用 | 刻意 Agent-Agnostic，模型配置交平台 |
| MCP 外接 | ➖ 对等 | 双方都列为未来 |

## 3. 真正值得补的 gap（按价值排序）

### gap 1：客观门禁脚本（最大缺口）

文章把「能判定的就该脚本化」作为核心——总验证脚本是它眼里最关键的基础设施。本框架靠 subagent 评审 + 测试收口，但**没有一个不可辩解的可执行门禁**。

关键洞察：本框架的 L3 设计**本就预留了 `scripts/` 槽位**（`agentic_engineering.md:388` 明写「scripts/（可执行脚本）」），**只是一个都没填**。所以补脚本**不破坏 Agent-Agnostic**——框架核心仍是纯 Markdown，具体项目在 Skill 的 `scripts/` 下挂 verify 脚本即可。这是「设计已支持、实践未兑现」的典型。

### gap 2：基线对比

与 gap 1 同源。有了能产出结构化报告的 verify 脚本，基线对比只是「跑两次 + 存一次 + diff 一次」的薄封装。专治 AI 拿「历史遗留」甩锅。

## 4. 不建议盲目补的（是设计取舍，不是缺陷）

- **7 个常驻角色 Agent / 独立 PM**：本框架「Workflow Skill 驱动 + 评审才并行 subagent」更省 token，Judge 模式已实现等价的「路由 + 收口」。照搬 7 常驻角色反而退步。
- **流程定义状态机文件 + per-Agent 模型**：都会侵蚀 Agent-Agnostic 这个核心优势。文章需要它们是因为强绑 Cursor。

## 5. 本框架反而更强的点

- **第一性原理推导**：文章是纯归纳叙事，本框架有公理 → 实践的演绎链（`agentic_engineering.md:137`）。
- **复杂度路由**：fast-path vs 标准流程，文章没有（`skills/workflow-code-generation/SKILL.md:14`）。
- **多维评审 + 对抗性验证**：五维 reviewer + critic + Judge 独立调研，远强于文章的单一审查 Agent。
- **Agent-Agnostic**：纯 Markdown 载体，不锁平台（`agentic_engineering.md:506`）。
- **乔哈里窗人机分工模型**：文章无对应理论框架（`agentic_engineering.md:266`）。
