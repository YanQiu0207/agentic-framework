# 选型调研与决策

> 围绕「快速搭大型非生产工具，既要快又要质量、执行段自主并行、不想人逐步干预」这一诉求，对当下 AI 开发工作流做的横向核实。所有事实附来源（2026-06 联网核实）。

## 1. 选型排名

| 方案 | 适配 | 一句话 | 来源 |
| --- | --- | --- | --- |
| 方法论：Walking Skeleton + Skeleton Architecture | 高 | 骨架手写锁抽象 + AI 填叶子 + 一条 e2e 烟测当机械门禁 | [InfoQ](https://www.infoq.com/articles/skeleton-architecture/) |
| **Superpowers**（obra） | 高 | 前置设计硬门 + 执行段自主 + subagent-driven + 并行 agent，**几乎照本诉求长的** | [repo](https://github.com/obra/superpowers) |
| OpenSpec（Fission-AI） | 高 | 轻量 fluid，给承重决策做轻文档 | [repo](https://github.com/Fission-AI/OpenSpec) |
| Taskmaster | 高 | PRD→带依赖任务清单，无强制审批 / 无多 reviewer | [repo](https://github.com/eyaltoledano/claude-task-master) |
| GitHub Spec Kit | 中 | 有精简四步路径，但默认气质偏生产、完整路径三道质量门 | [quickstart](https://github.com/github/spec-kit/blob/main/docs/quickstart.md) |
| BMAD / Agent OS v3 / Kiro | 中/中/低 | 流水偏重 / 不替你编排 / 要换整套 IDE | — |

> 关键发现：**没有哪个现成工具是为「大型非生产工具」量身定做的**。真正贴合的是方法论，工具只做点缀。而本诉求（前重后自主）最接近的现成形态是 **Superpowers**。

## 2. Superpowers 是什么（核心范本）

Jesse Vincent（obra）的「给编码 agent 的完整开发方法论」，本质是**一组可组合的 `SKILL.md` + 让 agent 必须遵守它们的引导机制**。MIT，已进 Anthropic 官方 Claude Code 插件市场。

**原理三层**：
1. **Skills = 模块化 markdown 指令单元**（TDD / brainstorm / debug …）。
2. **session hook 引导 + 渐进披露**：会话开始注入「去读 getting-started skill」，教 agent「用脚本搜索 skill、有 skill 就必须用」，按需加载而非一次性塞满上下文。
3. **强制触发**：动作前必须查 skill，「1% 可能适用也要查」，不可协商；用户指令高于一切。

**工作流七阶段**：brainstorming（设计硬门，未批准不写代码）→ git worktree → writing-plans（2-5 分钟小任务）→ subagent-driven-development（每 task 独立 implementer + reviewer subagent）/ dispatching-parallel-agents（并发）→ TDD（强制 RED-GREEN-REFACTOR）→ code review → finishing branch。**批准计划后执行段自主连跑，不逐 task 停。**

来源：[README](https://github.com/obra/superpowers/blob/main/README.md)、[作者博客](https://blog.fsck.com/2025/10/09/superpowers/)、[using-superpowers SKILL](https://github.com/obra/superpowers/blob/main/skills/using-superpowers/SKILL.md)。

## 3. Superpowers × `workflow-*` 异同

| 维度 | `workflow-*` | Superpowers |
| --- | --- | --- |
| 执行节奏 | 逐 task 停等批准 | **批准计划后自主连跑** |
| 并行 | 基本串行（仅评审并行） | **dispatching-parallel-agents** |
| 实现 + 评审 | 主 agent 自己实现 → 调 review | **每 task 独立 implementer + reviewer subagent** |
| 隔离 | 无 worktree | **using-git-worktrees** |
| TDD | 独立阶段，非每 task 内嵌 | 每 task 强制 RED-GREEN-REFACTOR |
| 评审深度 | **分级 review**（轻量 / 标准 / 严格；严格为 5 维 + critic + judge） | 单 reviewer subagent |
| 客观门禁 | ❌ 无 | ❌ 无 |
| 复杂度路由 | **有**（fast-path） | ❌ 无 |
| 知识沉淀 | **project-knowledge / intent 沉淀** | ❌ 无 |

**`workflow-*` 已经更强的**：设计深度、分级评审、知识沉淀。
**值得借鉴的**：执行段自主连跑、subagent-driven、并行 dispatch、worktree 隔离。

## 4. 决策：基于 `workflow-*` 改造，而非迁移工具

不直接上 Superpowers，理由：

- `workflow-*` 在评审/复杂度路由/知识沉淀上**比 Superpowers 强**，迁移会丢掉这些。
- Superpowers 无文档化的「轻量跳过」模式，且换工具要重学整套习惯。
- 我们已把 `workflow-*` 打磨得很熟，它**唯一的洞**就是执行段（逐 task 停等）。

**方案**：把 Superpowers 的执行形态（自主 + 并行 + subagent-driven + worktree）嫁接到 `workflow-*` 的执行段，保留分级 review 和知识沉淀等质量基建 —— 即把 `workflow-code-generation` 执行段从「逐 task 停等」改造为「下放 agent + 并行」，详见 [03](03-parallel-execution-mode.md)。

## 5. 来源盲区（诚实标注）

- Spec Kit 完整路径三道门是「建议」还是「硬阻断」官方未量化；Superpowers 是否有官方「轻量跳过 brainstorm」模式未确认（所读文档中没找到）；其 star 数 / 进官方市场时间来自二手摘要，未直连 GitHub 核对；README 未标具体版本号。
- Skeleton Architecture 出自 2026 实践者文章（InfoQ），非正式标准。
- 各工具命令清单 / 版本随时间变动，以实际安装版本为准。
