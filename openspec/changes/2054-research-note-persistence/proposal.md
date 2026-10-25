# Proposal: 变更调研结论落盘与实现参考传递

**作者**：YanQi
**日期**：2026-11-27
**变更**：2054-research-note-persistence
**状态**：Draft

---

## 1. 背景

### 1.1 问题描述

当前框架中 `codebase-researcher` subagent 的调研报告只存在于调用方会话的对话上下文里。新会话执行 tasks.md 实现时拿不到「此前调研发现了什么、应该复用哪些现有代码」，只能拿到 `context_files` 这类文件级指针，需要自己重新读代码、重新归纳，归纳偏差会导致实现时重新造方案、没有复用已有代码。

这一问题有实证研究支撑：RepoReuse 基准（arXiv:2609.35357，2026-09）测量 3000 轮多轮编码任务发现——agent 会逐步停止探索仓库中相关代码，到第 5 轮 50.8% 的任务链留下重复实现，而 pass rate 几乎不动；关键对照是「interface memory」实验：在需求里列出「已有函数的模块、名称、签名、返回值、行为」并鼓励复用，self reuse 从 30.0% 提升到 67.8%（翻倍以上），而把完整源代码塞进上下文（source memory）反而停在 29.2%，与不给任何信息无异。结论：agent 需要的不是更多信息，而是「哪些已存在、去哪找」的紧凑清单。

### 1.2 现状分析

- 调研触发点共 4 处：需求澄清 Step 1（`skills/workflow-requirements-clarification/SKILL.md:122`）、系统设计 Step 0（`skills/workflow-system-design/SKILL.md:161`）、任务拆解第二步（`skills/workflow-code-generation/reference/task_planning_guide.md:21`）、故障排查（`skills/troubleshooting/SKILL.md:98`）。前三处报告均不落盘。
- 唯一落盘通道是 `codebase-researcher` 第五步「架构快照确认」（`agents/codebase-researcher.md:56`）：仅当产出模块级概览/跨模块调用链/设计权衡时才询问，且需用户确认，写入长期 `openspec/specs/`。它面向「长期知识」，不承接「本次 change 实现该参考什么」的中间结论。
- design.md 只记录用户确认的设计内容（`workflow-system-design` 强制规则 9），不承载调研发现；proposal 侧唯一落点是需求确认后的 `1.2 现状分析` 摘要。
- tasks.md 每个任务的 `context_files` 是指针字段，模板注释只写「理解现有实现」，不携带复用结论；编码入口（`workflow-code-generation/SKILL.md:89`）的强制通读清单不含任何调研产物。
- 业界已有同类实践：Anthropic「structured note-taking / agentic memory」将 agent 的关键发现持久化到上下文窗口外的文件并在后续拉回（effective context engineering for AI agents，2025-09）；「Effective harnesses for long-running agents」（2025-11）用 progress 文件 + git history 让每个新会话快速恢复工作状态；mattpocock/skills 的 `research` 技能要求调研结果写成仓库内 Markdown 文件、每条主张引用一级来源、位置遵循仓库已有约定。

### 1.3 主要使用场景

- 新会话（或压缩后的会话）执行 `tasks.md` 实现：先读本 change 的调研文件，按任务的「实现参考」直接定位已有实现，不再重新造方案。
- 多阶段流程（需求→设计→拆解）中调研结论跨阶段传递，不依赖单次会话存活。
- Change 归档后，调研文件随目录归档，成为「当时为什么这样实现」的证据链一部分。

## 2. 目标

把「调研结论落盘为带引用的文件」与「任务级实现参考字段」接进现有工作流，使实现会话能直接消费先前调研结论，减少重复探索与重复实现。

### 2.1 非目标

- 不新增独立技能或命令（借鉴设计，不整套安装外部技能）。
- 不改变 `codebase-researcher` 的只读边界和第五步架构快照流程（长期知识沉淀照旧独立运作）。
- 不触碰交付门、Review、门禁脚本；本轮全部是 Markdown 文本改动。
- 不改变 `openspec/specs/` 长期知识的写入条件与确认门槛。

## 3. 需求概览

### 3.1 功能性需求

1. **调研落盘**：需求澄清 Step 1 与系统设计 Step 0 调用 `codebase-researcher` 后，调用方将报告追加写入本 change 的 `research.md`（约定位置：`openspec/changes/<ticket>-<change-name>/research.md`）；按调研问题组织，保留 `file:line` 引用，沿用 `codebase-researcher` 的六段报告结构；多次调研追加不覆盖。
2. **实现参考字段**：`task_planning_guide.md` 模板中每个任务新增可选字段 `实现参考`，值形如 `research.md §N（要点：复用 X / 基于 Y 扩展）`；拆解第二步调研时负责从 research.md 提取并填写；无内容时省略该字段。
3. **编码入口通读**：`workflow-code-generation` 步骤 2 的强制通读清单加入「`research.md`（存在时）」。
4. **状态字段不受影响**：research.md 不进入 `lint_task_deps.py` 校验范围，不影响任务状态机。

### 3.2 非功能性需求

- 落盘文件是 change 级中间产物，随 Change 归档，不写入长期 specs，不触发 project-knowledge 确认门。
- `codebase-researcher` 保持只读；research.md 由调用方 skill 写入（并行调研多个 subagent 时不产生写竞争）。
- 中文 Markdown 遵守 `md-zh` 排版规范；不使用破折号写作约定仅适用于 `.learn-by-gpt/` 译本目录，不约束本仓库。

### 3.3 验收标准

- [ ] `openspec/changes/2054-research-note-persistence/specs/` 下 Delta 与目标文件一一对应，且每个改动文件的现行文本已核对。
- [ ] `research.md` 约定在三处出现且一致：需求澄清 SKILL.md、系统设计 SKILL.md、编码入口 SKILL.md。
- [ ] `task_planning_guide.md` 模板含 `实现参考` 字段及填写规则，质量自检表相应更新。
- [ ] `grep -n "research.md" skills/workflow-requirements-clarification/SKILL.md skills/workflow-system-design/SKILL.md skills/workflow-code-generation/SKILL.md skills/workflow-code-generation/reference/task_planning_guide.md` 全部命中。
- [ ] 全部任务完成后按 tasks.md 逐项 verification 通过，工作区无本 change 之外的意外改动。

## 4. 知识影响

- 命中长期知识：`openspec/specs/backend/engineering/tech/knowledge-management.md` 需 MODIFIED（新增 research.md 这一 change 级知识形态的约定）；创建镜像 Delta `specs/backend/engineering/tech/knowledge-management.md`。
- 其余为 skill 内工作流文本，不产生长期知识 Delta。

## 5. 参考资料

- `agents/codebase-researcher.md`（报告结构与只读边界）
- `skills/workflow-requirements-clarification/SKILL.md`、`skills/workflow-system-design/SKILL.md`、`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-generation/reference/task_planning_guide.md`
- RepoReuse: Do Coding Agents Reuse Existing Code or Reinvent the Wheel?（arXiv:2609.35357，2026-09-28）
- Anthropic: Effective context engineering for AI agents（2025-09-29）；Effective harnesses for long-running agents（2025-11-26）
- mattpocock/skills `research` 技能（本仓库 `.learn-by-gpt/mattpocock-skills/zh-CN/skills/engineering/research/SKILL.md`）
