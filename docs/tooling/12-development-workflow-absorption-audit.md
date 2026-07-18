# 研发工作流吸收与实现审计

## 结论

本框架已经吸收主流 Agent 研发框架的大部分核心工程思想，并实现了可测试的确定性控制流内核，但还不是可独立运行的完整 Agentic Workflow Engine。

- **明确吸收**：Superpowers、OpenSpec、Spec Kit、Compound Engineering、Agent Skills 的主要方法已经进入 Skill、Agent 或确定性脚本。
- **部分吸收**：GSD Core、Everything Claude Code、Matt Pocock Skills、gstack、BMAD-METHOD、oh-my-claudecode 的部分能力。
- **未发现明确吸收证据**：HumanLayer 的产品层人机协作能力。
- **实现边界**：DAG、状态机、失败隔离、恢复计划和部分机器门有 Python 实现；Agent 调度、worktree、Review/Verify 调用和知识内容生成仍依赖宿主工具与 Prompt 协议。
- **当前重点**：不再继续增加工作流阶段，优先验证效果、记录成本并强化上下文控制。

判断标准不是是否出现相似术语，而是框架是否已经形成 Skill 接线、确定性脚本、机器门、测试证据或持久化产物。

## 审计范围与证据等级

本次审计不只检查 `docs/`，还检查：

- `commands/` 到 `skills/` 的入口接线。
- `workflow-code-generation` 到测试、Review、Verify 和知识归档的交叉引用。
- Reviewer Agent 是否存在并与风险档位匹配。
- DAG、任务状态、恢复、交付检查和机器验证脚本。
- 现有 Python 单元测试与 Skill 引用图检查。

证据分为 4 级：

| 等级 | 含义 |
| --- | --- |
| 真实实现 | 有确定性代码和测试，不依赖模型自行解释流程 |
| Prompt 编排 | Skill 明确要求宿主 Agent 调用工具或其他 Skill，但仓库没有独立执行器 |
| 文档设计 | 只在设计或比较文档中描述 |
| 未发现 | 没有找到对应实现或明确接线 |

验证结果：

- 逐个运行仓库中的 9 个 Python 测试文件，共 66 项测试通过，1 项因 Windows symlink 权限跳过。
- `lint_skill_graph.py --root agentic-framework --graph` 返回 0 个错误；唯一警告是 `open-code-review` 未被 Command、Skill 或文档引用，与主工作流无关。
- 首次使用 `unittest discover -s agentic-framework` 得到 0 项测试，因为测试目录不是可递归发现的 Python Package；随后改为逐文件执行。

## 已明确吸收

| 来源 | 吸收情况 | 本框架对应机制 |
| --- | --- | --- |
| Superpowers | 深度吸收，部分自动化 | DAG、状态机和失败隔离有真实实现；subagent、worktree、Review/Verify 调用由 Prompt 与宿主工具执行 |
| OpenSpec | 选择性吸收，部分机器门 | `spec.md`、`tasks.md`、原地归档和 Spec Drift 已接线；归档动作与 intent 内容主要由 Prompt 约束 |
| Spec Kit | 方法吸收 | 需求、设计、任务、实现的结构化产物链，以及关键阶段人工批准 |
| Compound Engineering | 深度吸收，内容靠 Prompt | ADR、架构快照、intent 门和交付检查已经接线；机器只能检查是否更新，不能判断内容质量 |
| Agent Skills | 功能上基本覆盖 | `/requirements-clarification`、`/system-design`、`/code-generation`、`/test-generation`、`/code-review`、`/verification` |
| GSD Core | 部分吸收 | task 级 `context_files`、状态持久化和恢复计划已实现；没有阶段级全新上下文管理器，恢复所需 Git 事实由外部提供 |

### Superpowers

本框架明确保留自身的分级 Review、机器验证和知识沉淀，只吸收 Superpowers 的执行形态：

```text
tasks.md 批准
→ DAG 分波
→ subagent 在独立 worktree 执行
→ task 级 Review 和 Verify
→ 合并回主分支
```

与 Superpowers 相比，本框架还增加了 Fast-Path、分级多维 Review、Critic/Judge、Spec Drift 和 intent 沉淀。

实现边界：

- `workflow_control.py` 真实实现稳定拓扑分波、可调度判断、状态迁移、重试计数、递归阻塞、恢复计划、原子写和跨进程写锁。
- `lint_task_deps.py` 真实检查悬空依赖、循环依赖、必填字段和同文件并行冲突。
- worktree 创建、Agent dispatch、Git 合并、Review 和 Verify 的实际调用由 `delegated-execution-guide.md` 约束宿主执行，仓库内没有端到端 Runner。
- 控制内核接受调用方提交的 `quality_passed` 等事件，不会自行验证 Review 报告、Verify 报告或 Git commit。

证据：[02-tool-landscape.md](02-tool-landscape.md)、[03-parallel-execution-mode.md](03-parallel-execution-mode.md)。

### OpenSpec 与 Spec Kit

本框架吸收了规格驱动开发的结构化工件和阶段门，但采用不同的事实来源策略：

- 代码负责描述系统现状。
- Feature Spec 和 ADR 负责保存需求、权衡与 intent。
- 架构快照只作为带时效性的导航工具。
- 不维护可能与代码争夺事实来源的中央现行规格库。

证据：[05-industry-comparison.md](05-industry-comparison.md)。原 `project-knowledge` 引用已随 Skill 退役，不再作为当前证据。

### Compound Engineering

本框架已经形成知识复利闭环：

- 不可逆或高影响决策写入 ADR。
- 模块结构和洞察按需写入架构快照。
- Feature Spec 归档后保留需求和设计 intent。
- 在问题刚解决、上下文仍然新鲜时判断是否沉淀。

其中原地归档状态、Spec Drift 和交付终态有机器检查；ADR、架构快照和 intent 的内容生成与质量判断仍由 Agent 按 Skill 执行。

证据：[04-compound-engineering-comparison.md](04-compound-engineering-comparison.md)、[arch-snapshots/agentic-framework/insights.md](arch-snapshots/agentic-framework/insights.md)。

## 功能重合但未系统吸收

| 来源 | 判断 | 主要差异 |
| --- | --- | --- |
| Everything Claude Code | 部分重合 | 已有 Skills、Agents、Commands、Rules、验证和知识体系；没有完整的 Harness 控制面、持续学习和安全扫描发行版 |
| Matt Pocock Skills | 部分重合 | 已有需求澄清、ADR 和领域调研；没有明确的 `/grill-me` 式反向访谈和共享领域语言文档机制 |
| gstack | 部分重合 | 已有架构、前端、性能和代码等多维 Reviewer；没有 CEO、产品、设计、QA、发布经理组成的完整角色化链路 |
| BMAD-METHOD | 部分重合 | 已有需求、设计、实现和评审分层；没有 PRFAQ、PRD、UX、Story 等完整敏捷角色与工件体系 |
| oh-my-claudecode | 部分重合 | 已有 subagent 并行和分级 Reviewer；没有 Team、tmux 多 CLI Worker、跨模型运行时编排和多种执行模式 |
| HumanLayer | 未发现明确证据 | 有代码库研究和人工门，但没有 HumanLayer 产品层的人机协作界面；其原仓库已弃用，不作为后续吸收重点 |

这些项目与本框架存在能力交集，但目前没有足够证据证明相关能力是经过专项研究后有意识移植的，因此不能标记为「已系统吸收」。

## 当前完整主链

```text
项目约束加载
→ 需求澄清
→ 系统设计或 Quick Design
→ tasks.md 批准
→ DAG 分波
→ Agent + worktree 隔离执行
→ 测试
→ 分级多维 Review
→ Critic / Judge
→ 机器 Verify
→ Spec Drift 检查
→ 合并
→ ADR / 架构快照 / Feature Spec 归档
```

框架已经具备或明确接线以下能力：

- Fast-Path 复杂度路由已写入 Skill，但没有自动判级和端到端测试。
- 3 档 Review 已接线，按风险选择 Reviewer。
- 5 维 Reviewer + Critic/Judge 的 Agent 定义与引用真实存在，实际执行依赖宿主 Agent 工具。
- 机器验证独立于 LLM Review，执行 build、test、lint 和基线比较。
- Spec Drift 门要求解释代码与规格不同步的原因。
- `lint_task_deps.py` 真实检查循环依赖、悬空依赖和并行文件冲突。
- intent 沉淀已经成为交付协议，但内容质量无法由脚本证明。

证据：[07-critical-review.md](07-critical-review.md)、[10-harness-engineering-practices.md](10-harness-engineering-practices.md)。

## 尚未完全补齐

### 上下文工程

- 已有 task 级 `context_files` 必填字段和 dispatch Prompt。
- 当前脚本不检查 `context_files` 路径是否存在，也不能证明 Agent 实际读取了文件。
- 尚未强制 Research、Plan、Implement、Review 等重型阶段分别使用全新上下文。
- 当前状态应标记为「部分吸收」，不能等同于完整 GSD Core 架构。

### 产品角色链

- 工程 Reviewer 较完整。
- CEO、产品策略、用户价值和发布运营视角较弱。
- 框架面向大型非生产工具，这可能是范围取舍，不一定需要补齐。

### 跨模型运行时编排

- 当前核心是可在 Claude Code 和 Codex 中安装的 Prompt、Skill、Agent 和 Command。
- 尚未提供统一的多 CLI Worker 生命周期、tmux 编排和跨模型任务路由。

### 效果评测

- Tier 0 结构门卫有真实 Runner 和测试。
- Tier 1 已有触发用例文档，但未发现自动执行这些用例或计算命中率的 Runner。
- 「并行是否优于串行」「Workflow 是否降低缺陷率」仍缺少 Tier 2、Tier 3 实测。

### 成本治理

- 尚无统一的 token 预算闸门。
- 已有 Claude/Codex 会话离线分析器和历史账本，可统计 phase、model、Agent、token 和 Review Loop；它不是运行时预算闸门。
- 现有遥测样本存在乱码和 Review 数据偏少的问题，不能据此证明框架效果。
- 多 Reviewer、Critic 和并行 Agent 可能产生较高固定成本。

## 后续优先级

不再优先横向复制更多 Workflow，按以下顺序补强现有框架：

1. 建立 Workflow 效果评测，验证并行、分级 Review 和机器门禁的真实收益。
2. 记录 task、Agent、Reviewer 的 token、耗时和失败重试成本。
3. 强化阶段级新上下文、状态持久化和中断恢复协议。
4. 仅在产品型项目中增加 gstack 式产品评审 Profile。
5. 仅在明确需要多模型执行时建设 oh-my-claudecode 式运行时编排。

## Stop/Continue 判断

**停止继续堆叠研发阶段，继续补齐端到端执行证据、效果评测、成本观测和上下文控制。**

框架当前缺少的不是另一套需求、设计、实现、评审流程，而是把 Prompt 协议中的关键步骤进一步机器化，并证明已有流程有效且成本可控。
