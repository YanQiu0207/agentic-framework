# Agentic Engineering Framework 特性、进展与框架对比

**更新时间**：2026-07-19

**文档定位**：面向框架使用者和维护者，统一说明当前能力、开发进展、实际使用边界、历史演进及与开源框架的差异。

## 1. 结论

这套框架不是单一的代码生成 Prompt，而是一套安装到 Codex 和 Claude Code 项目中的工程约束与执行环境。其核心组合是：

> 单仓库双 Profile + 代码事实源 + 前重后自主 + 确定性控制 + Review/Verify 双门 + 有界定向复审 + Intent 沉淀。

当前成熟度不能笼统描述为「已完成」，必须分层判断：

1. **确定性代码最成熟**：安装隔离、OPSX 三阶段校验、Tooling DAG 状态机、任务依赖检查、Verification、Spec Drift 和离线遥测都有 Python 实现与测试。
2. **工作流已接线但依赖宿主 Agent**：需求澄清、系统设计、Agent 调度、worktree、Code Review 和知识写回主要由 Skills 约束 Codex 或 Claude Code 执行，不是一个独立 Workflow Engine。
3. **部分能力仍在建设**：跨项目共用知识库、触发评测、Telemetry 运行时采集、上下文效果验证尚未闭环。
4. **生产发布平台没有实现**：灰度、回滚、容量、安全、数据迁移和线上反馈仍是路线候选，不能宣传为已有能力。
5. **Production 尚缺真实生产项目验收**：当前测试能证明框架合同和确定性脚本工作，不能证明生产项目中的缺陷率、交付效率或 Token ROI。
6. **可靠性与安全治理已落地**：Tooling 写状态使用跨进程锁和原子替换；安装器提供事务回滚；未跟踪任务产物采用非破坏性废弃和会话历史恢复规则。

当前总合同见 `docs/design-docs/framework-unification/spec.md:14-31,97-126`；实现边界审计见 `docs/tooling/12-development-workflow-absorption-audit.md:3-32,141-188`。

## 2. 状态与证据口径

本文使用以下状态，避免把「写在文档里」误当成「已经可用」。

| 状态 | 判断标准 |
| --- | --- |
| 已实现并接线 | 有代码、测试，并已被当前 Profile 工作流调用 |
| 已实现但可选或需配置 | 有实现和安装入口，但需要 Pack、项目配置或外部工具 |
| 已接线，依赖宿主执行 | Skill 已定义流程，但真实调度由 Codex、Claude Code 或用户环境完成 |
| 部分实现 | 已有骨架或局部闭环，但缺少真实数据、自动 Runner 或端到端验收 |
| 仅规划 | 只有设计或路线，没有当前实现证据 |
| 已废弃 | 已被最终方案明确删除或替代，不应恢复 |

证据优先级为：

1. 当前代码和测试。
2. `docs/design-docs/framework-unification/spec.md` 当前合同。
3. 已归档的 Feature Spec、Tasks 和 ADR。
4. `docs/tooling/` 历史设计快照。

`docs/tooling/README.md:1-9` 已明确：该目录来自合并前 Tooling 框架，`project-knowledge`、`bp-cola-ddd` 和 Task 级 LLM Review 等描述已经废弃。本文只吸收其中仍被当前代码和最终合同支持的设计思想。

## 3. 总体架构

### 3.1 单仓库双 Profile

| Profile | 场景 | 执行方式 | Review 策略 |
| --- | --- | --- | --- |
| Production | 进入生产环境的功能、修复和架构变更 | 逐阶段批准、逐 Task 推进、确定性门禁 | 普通 Task 单综合 Review；高风险 Task 五维 Review；最终五维集成 Review |
| Tooling | 大型非生产工具 | Tasks 批准后 DAG 分波、自主执行 | Task 内不启动 LLM Review；全部完成后一次风险分级 Review |

两个 Profile 共用 Standards、Best Practices、Review、Verification、Self-Refinement 和 Troubleshooting，但生命周期入口相互隔离。安装时必须显式二选一，不能默认双装。

证据：`README.md:70-112`、`scripts/install_agentic_framework.py:23-95,266-320`。

### 3.2 代码是当前实现事实源

框架不维护 `openspec/specs/` 中央规范库：

- 代码描述当前模块、接口、数据流和行为。
- Change Artifact 描述本次为什么改、准备改什么。
- ADR 描述长期决策及权衡。
- Archive 保存历史变更证据。
- 架构快照只作有时效性的导航，不与代码争夺当前真相。

证据：`README.md:98`、`docs/design-docs/framework-unification/spec.md:97-116`。

### 3.3 LLM 与确定性程序分工

- LLM 负责需求语义、设计权衡、代码实现和风险判断。
- Python 脚本负责结构、状态、依赖、重试、阻塞、覆盖关系和退出码。
- Build/Test 证明可执行行为。
- Code Review 检查需求符合度、架构、健壮性、性能和工程规范。

框架刻意避免用关键词数量、文档长度或文件数量伪装成语义质量判断。

证据：`docs/design-docs/opsx/code-first-deterministic-validation/spec.md:64-80,322-355`。

## 4. 功能与开发进展

### 4.1 核心工作流

| 特性 | 当前状态 | 使用情况 | 证据与限制 |
| --- | --- | --- | --- |
| 需求澄清、设计、任务、执行 | 已实现并接线 | Production 与 Tooling 各有完整和 Quick 入口 | 当前存在两族 Lifecycle Skills；语义质量依赖宿主 Agent |
| Production OPSX | 已实现并接线 | 支持 Standard、Quick、Plan、Delivery、Archive | `scripts/validate_change.py`；不是官方 OpenSpec CLI |
| Tooling DAG 分波 | 已实现并接线 | 根据 `depends_on` 生成稳定 Wave | `workflow_control.py` 和 `lint_task_deps.py` 有测试 |
| 状态机与失败隔离 | 已实现并接线 | 支持重试、阻塞传播、人工接管和恢复 | 状态写回是代码；Agent 执行事实由外部编排提供 |
| worktree 隔离 | 已接线，依赖宿主执行 | 中高风险 Tooling Task 使用独立 worktree | 仓库没有自建 Git/worktree Runner |
| Fast-Path | 已接线，依赖语义判断 | 小改动由主会话直接完成 | 尚无稳定自动判级和端到端效果评测 |

Tooling 确定性内核实现了 Task 解析、拓扑分波、状态转换、阻塞、恢复、写锁和原子写回，但明确不直接调用 Agent、Git、Review 或 Verify。证据：`docs/tooling/design-docs/workflow-code-generation/deterministic-control-flow/spec.md:32-44,95-181`。

现有资料只有仓库测试、框架迁移和少量历史会话证据，没有统一的真实项目采纳率、成功率或长期缺陷数据。因此，DAG、状态和锁可以判断为「确定性代码已实现」，worktree、Dispatch 和 Review 只能判断为「宿主编排已接线」。

#### 写锁与恢复边界

所有修改 `tasks.md` 的控制 CLI 都在锁内重新读取文件，再完成决策和原子写回：

- Windows 使用 `msvcrt.locking`，POSIX 使用 `fcntl.flock`。
- 默认锁超时为 10 秒。
- 超时退出码为 `2`，原文件保持不变。
- 锁只保护本机、同一文件系统、且通过 `workflow_control.py` 协作的写者。
- 绕过控制脚本直接编辑文件，或跨机器共享目录，不在保护范围内。

证据：`docs/tooling/design-docs/workflow-code-generation/write-lock-timeout/spec.md:7-120`、`docs/tooling/design-docs/workflow-code-generation/write-lock-timeout/tasks.md:46-102`。

### 4.2 Production OPSX

Production 的当前流程是：

```text
Requirements
    → Change-local Specs
    → Design
    → Tasks
    → Plan 门禁
    → 逐 Task 实现、测试、机器验证和风险分档 Review
    → 全局 Verification
    → Delivery 门禁
    → 五维集成 Review
    → Archive 门禁
```

`validate_change.py` 提供三个确定性阶段：

| 阶段 | 主要检查 |
| --- | --- |
| Plan | Change 路径、Proposal、Standard/Quick Artifact、Task 依赖、环、覆盖关系 |
| Delivery | Task 完成状态、构建/测试记录、任务 Review 元数据、覆盖映射 |
| Archive | Delivery 条件、最终 Review、归档目标和命名 |

稳定退出码为：`0` 通过，`1` 规则违规，`2` 调用或校验器内部错误。证据：`docs/design-docs/opsx/code-first-deterministic-validation/spec.md:182-320`。

当前边界：

- OPSX 是采用 OpenSpec Change Artifact 思想的本地 fork，不是官方 OpenSpec CLI 的兼容层。
- 不执行官方 Delta Sync，也不维护中央 Specs。
- Production 要求项目根存在有效 `verify.config.json`；缺失或失效时不得进入 Review。证据：`skills/opsx-code-generation/SKILL.md:84-103`。
- 尚无真实生产项目验收证据。证据：`docs/design-docs/framework-unification/spec.md:698-704`。

实施账本显示 OPSX 代码事实源方案的 4 个 Task 已完成，三阶段校验、Fixtures 和稳定退出码均已落地；其中早期 `opsx-project-knowledge` 接线后来已被最终方案删除。证据：`docs/design-docs/opsx/code-first-deterministic-validation/tasks.md:46-122`。

### 4.3 Code Review

共享 Review 合同提供 `profile`、`review_profile`、`mode` 和 `scope` 四个维度。

Production：

- 普通 Task：独立综合 Reviewer。
- 高风险 Task：规格、健壮性、性能、规范和信任边界五个 Reviewer，加独立 Judge。
- 全部 Task 完成后：一次五维集成 Review。

Tooling：

- Task 内只跑测试和机器检查，不启动 LLM Review。
- 全部 Task 完成后执行一次风险分级 Review。

共同收敛规则：

- 每个 Scope 只有一次 Initial Review。
- 只有 P0/P1 触发修复。
- Re-review 只检查原 Finding 与修复 Diff，不得扩大范围。
- 最多两轮定向复审，仍不通过则转人工。

证据：`skills/workflow-code-review/SKILL.md:14-57`、`docs/tooling/adr/003-review-fix-loop-convergence.md:13-42`。

当前限制：Reviewer、Critic 和 Judge 的定义及路由合同已经存在，但实际 Subagent 启动依赖宿主 CLI，框架没有独立 Review 服务。

### 4.4 Machine Verification 与 Spec Drift

状态：**已实现；项目级检查需要配置。**

功能包括：

- 配置驱动运行 Build、Test、Lint 等检查。
- 改动前保存基线，改动后只拦截新增违规。
- 识别「改了代码但相关 Spec、Tasks 或 ADR 没有同步」的 Spec Drift。
- 验证配置在实现期间冻结，禁止为过门而删除检查项或重采基线。
- `verify.config.json` 只允许通过 `/verify-config` 维护。

无配置时，共享 Verification 仍执行内置 Spec Drift；Tooling 必须显式报告降级，Production 则要求有效配置。

证据：`skills/workflow-verification/SKILL.md:12-104`、`skills/workflow-verification/scripts/verify.py:181-233,338-474,638-776`。

信任边界：配置命令使用 Shell 执行，只能自动运行可信仓库的配置；外部 PR 或不可信分支必须先人工检查。

### 4.5 Frontend Pack

状态：**已实现但可选，仅 Tooling。**

包含以下闭环：

1. `workflow-frontend-design`：确定设计方向和 UI Spec。
2. `bp-frontend-layout`：页面骨架、区域和响应式结构。
3. `std-react`：React、Next.js、TypeScript 和 shadcn/ui 规范。
4. `bp-frontend-taste`：视觉质量收尾。
5. `frontend-playwright-verification`：浏览器、交互、响应式和截图验证。

安装：

```bash
python scripts/install_agentic_framework.py <project> \
    --profile tooling \
    --with frontend
```

证据：`docs/tooling/06-official-frontend-skills-installation.md:3-46`、`scripts/install_agentic_framework.py:77-95`。

当前限制：浏览器、页面环境和项目依赖需要目标项目提供；仓库内没有代表真实业务页面质量的统一 E2E 基准。

### 4.6 project-init 与跨项目共用知识库

`project-init` 状态：**已实现但可选，仅 Tooling。**

它负责：

- Git 或 Git+SVN 初始化。
- 创建 `.gitignore`、`CLAUDE.md`、`AGENTS.md`、README 和 Docs 骨架。
- 写入版本管理约束。
- 接线外部跨项目共用知识库。
- 创建首次提交。

知识库状态：**部分实现。**

- 设计采用 Markdown + Git + 分层索引 + 按需检索 + 增量更新。
- `project-init` 能从全局配置取得知识库路径，并向项目 `AGENTS.md` 写入检索和沉淀规则。
- 历史资料记录了 `domains/`、`issues/`、`sources/`、`changes/`、`projects/` 和 `archives/` 目录模型。
- 历史进度结论是「骨架和工作流挂点已有，真实条目规模、两级索引和四类真实问题验收尚未完成」。

证据：`skills/project-init/SKILL.md:159-176`、`docs/tooling/09-personal-knowledge-base-plan.md:113-209,275-338`。

重要边界：

- 知识库是外部跨项目知识资产，不是本框架的中央当前事实库。
- 旧 `project-knowledge` 和 `opsx-project-knowledge` Skills 已废弃。
- 本次研究没有进一步审计 `E:/work/shared-knowledge-base` 的当前内容和实际命中率，因此不能宣称知识库建设已经完成。

### 4.7 Telemetry Pack

状态：**已实现但可选，目前只完成第一层。**

当前实现：

- 离线解析 Claude Code 和 Codex 已落盘的会话 Transcript。
- 识别 Workflow 阶段、Review 轨迹、重试、人工介入、Task 归因和 Token 使用。
- 排除长 Idle，并支持按项目目录筛选。
- 不主动采集数据，对运行时零侵入。
- 本地账本不提交 Git。
- 任务归因使用固定字段记录 Feature、Task、Review Profile、Review/Verify 重试和人工介入；旧报告不推测缺失字段，重复任务保留最后一个完整记录。

尚未实现：

- Hooks 常态采集。
- OpenTelemetry 跨项目聚合。
- 运行时 Token 预算门。
- 完整 Codex Subagent 归因。

证据：`docs/tooling/11-session-telemetry.md:15-90`、`docs/tooling/design-docs/session-telemetry/task-attribution/spec.md:7-57`、`docs/tooling/design-docs/session-telemetry/task-attribution/tasks.md:49-96`、`metrics/README.md:1-5`。

历史资料中的「遥测账本随 Git 提交」已经过时，不应恢复。

### 4.8 Self-Refinement

状态：**已接线，依赖语义执行。**

当用户明确纠正了可复用、跨会话可能重复的错误时：

1. 先完成当前任务纠正。
2. 识别错误模式和根因。
3. 搜索已有 Rules/Skills，避免重复。
4. 给出不超过三条持久化建议。
5. 只有得到用户确认后才修改全局或项目规则。

也可以通过 `/reflect` 手动触发完整回顾。证据：`skills/self-refinement/SKILL.md:18-127`。

当前限制：没有独立效果评测 Runner，无法自动证明规则更新降低了同类错误复发率。

实际使用证据：本框架合并过程中曾误删未跟踪方案文档，之后从 Claude Code 会话 JSONL 恢复原始文件，并经用户确认把非破坏性删除规则写入全局 `AGENTS.md`。这证明 Self-Refinement 流程被真实使用，但不能证明同类错误的长期复发率已经下降。证据：`docs/incidents/2026-07-19-untracked-plan-deletion.md:15-21,37-61`。

### 4.9 Troubleshooting

状态：**已接线，依赖宿主和真实环境。**

功能包括：

- 从代码、日志和可复现命令建立证据链。
- 明确列出假设并逐项验证。
- 修复后重跑原失败路径。
- 将可复用故障经验沉淀到 Issue 或知识库。

证据：`skills/troubleshooting/SKILL.md:10-18,56-76,90-151`。

它是一套排障流程，不是独立诊断程序；网络、环境和运行时问题仍需要目标机器提供证据。

### 4.10 安装器与 Pack

状态：**已实现并测试。**

安装器采用物理复制，不是软连接，同时写入目标项目的 `.codex/` 和 `.claude/`：

```text
<project>/
├── .codex/
├── .claude/
└── .agentic-framework/
    └── manifest.json
```

Manifest 记录框架版本、Profile、Packs、受管文件和 SHA-256。安装器支持：

- Profile/Pack 白名单。
- 显式 Profile 切换。
- 哈希校验。
- 事务快照和失败回滚。
- 安全卸载。
- 拒绝 Symlink、Junction 和 Reparse Point 穿透。
- 旧 Skill 或 Pack 退休后仍能卸载。

证据：`scripts/install_agentic_framework.py:337-418,480-665`、`scripts/test_install_agentic_framework.py`。

可选 Pack：

| Pack | 状态 | Profile | 用途 |
| --- | --- | --- | --- |
| `frontend` | 已实现 | Tooling | 前端设计、React 规范和浏览器验证 |
| `project-init` | 已实现 | Tooling | 项目初始化和外部知识库接线 |
| `open-code-review` | 已实现薄封装 | Production、Tooling | 调用已安装的外部 OCR CLI |
| `telemetry` | 第一层已实现 | Production、Tooling | 离线会话分析 |

`open-code-review` Pack 不负责安装全局 OCR CLI，只提供使用已有 CLI 的薄封装。

### 4.11 评测体系

状态：**部分实现。**

| 层级 | 目标 | 当前状态 |
| --- | --- | --- |
| Tier 0 | Frontmatter、引用、依赖图和固定结构检查 | 已实现 |
| Tier 1 | Should-trigger、Should-not-trigger 和边界路由 | 有 Evaluation Cases，缺统一自动 Runner |
| Tier 2 | 高风险机制的 A/B 效果评测 | 未形成稳定基线 |
| Tier 3 | 缺陷率、速度和 Token ROI | 未形成真实项目数据集 |

证据：`docs/tooling/08-evaluation-strategy.md:12-19,29-76`。

Tier 1 当前是评测资产，不是效果结果；存在 Case 文件不能证明模型触发准确率已经达标。

## 5. 当前验证快照

2026-07-19 使用当前环境执行：

```bash
black --check scripts/
pytest -q
python scripts/lint_skill_graph.py
python skills/workflow-code-generation/scripts/lint_task_deps.py \
    docs/design-docs/framework-unification/tasks.md
```

结果：

- Black 26.5.1：通过。
- Pytest：129 passed、2 skipped、28 subtests passed。
- 跳过项：Windows Symlink 权限相关测试；Windows Junction 测试实际通过。
- Skill 图：31 Skills、20 Commands、8 Agents，0 错误、0 警告。
- 双 Profile 临时安装已验证入口隔离。
- 框架合并的 7 个 Task 均为 Completed；旧 Tooling 目录只停止独立演进，没有物理删除。

验收记录：`docs/design-docs/framework-unification/tasks.md:1-75`。

这些结果证明当前代码回归通过，但不能证明：

- Production 已在真实生产项目长期运行。
- 多 Agent 并行一定比串行质量更高或 Token 更低。
- 每次宿主模型都严格遵守 Skill。
- 外部知识库和遥测已经形成足够样本。

## 6. 使用方式

### 6.1 Production

```bash
python scripts/install_agentic_framework.py <production-project> \
    --profile production
```

推荐入口：

```text
/opsx-requirements-clarification
    → /opsx-system-design
    → /opsx-code-generation
    → /opsx-archive
```

低风险 Quick 变更：

```text
/opsx-quick-design
    → /opsx-code-generation
    → /opsx-archive
```

### 6.2 Tooling

```bash
python scripts/install_agentic_framework.py <tooling-project> \
    --profile tooling
```

完整路径：

```text
/requirements-clarification
    → /system-design
    → /code-generation
```

轻量路径：

```text
/quick-design
    → /code-generation
```

安装 Pack 时重复传入 `--with`：

```bash
python scripts/install_agentic_framework.py <tooling-project> \
    --profile tooling \
    --with frontend \
    --with project-init \
    --with telemetry
```

## 7. 与开源框架的对比

> 本节基于 2026-06-28 的公开资料研究，没有重新联网，也没有逐一安装运行各框架最新版。外部项目迭代很快，以下内容是历史比较基线，不是其当前版本的保证。正式对外发布前应重新核验官方文档。

| 框架 | 相对优势 | 本框架的差异化优势 | 取舍 |
| --- | --- | --- | --- |
| Superpowers | 并行 Dispatch、worktree、Subagent 和 TDD 执行形态成熟 | 双 Profile、Fast-Path、风险分级 Review、Critic/Judge、Verify 和 Intent | 本框架覆盖更宽、复杂度更高；吸收其执行思想但不是兼容实现 |
| OpenSpec | 官方 CLI、中央 Specs、Delta、Archive 和生态标准化 | 代码事实源、硬门禁、DAG 多 Agent、深度 Review | 存在哲学冲突；本框架刻意不维护中央 Specs，OPSX 不是官方兼容层 |
| Spec Kit | Constitution、Specify、Plan、Tasks、Implement 路径和 GitHub 生态 | 并行执行、机器 Verification、Critic/Judge 和 ADR/Intent | Spec Kit 更标准化；本框架更本地化、质量链更重 |
| Taskmaster | PRD 拆解、依赖管理、Loop 和 Cluster 执行专门化 | 覆盖需求澄清、系统设计、Review、Verify、Spec Drift 和 Intent | 只需要任务编排时 Taskmaster 更聚焦 |
| Compound Engineering | 问题解决后即时沉淀和 Overlap Detection | 同时覆盖 ADR、Feature Intent 和时效架构快照 | 本框架未证明系统化 Overlap Detection 的实际效果 |
| BMAD-METHOD | PRFAQ、PRD、UX、Story 和完整敏捷角色链 | 更聚焦工程执行、质量 Reviewer 和机器门 | 本框架没有完整产品角色链，只存在部分重合 |
| GSD、oh-my-claudecode 等 | 阶段上下文或多 CLI、多模型编排更专门 | 已有 Task Context、状态恢复和双质量门 | 仅部分吸收，当前没有跨模型 Worker Runtime，不能宣称等价 |

详细历史资料：`docs/tooling/05-industry-comparison.md:60-168`、`docs/tooling/12-development-workflow-absorption-audit.md:40-49,98-109`。

以下项目只作为未来运行时设计参考，不是已经集成的同类能力：

| 参考项目 | 可借鉴机制 | 当前框架状态 |
| --- | --- | --- |
| LangGraph | Checkpoint、Interrupt 和恢复 | 只有 `tasks.md` 状态与本机恢复，没有通用 Checkpoint Store |
| Microsoft Agent Framework | Typed Routing、Superstep | 只有 Task DAG 和状态机，没有通用多 Agent Runtime |
| Temporal | Durable Activity 和崩溃恢复 | 没有持久化 Workflow Service |
| OpenAI Agents SDK | Handoff 和 Trace | 没有 SDK 级 Handoff/Trace 集成 |

来源：`docs/tooling/13-agentic-workflow-engine-references.md:73-95,211-342`。这些外部项目的版本和当前能力同样需要联网复核。

### 7.1 本框架真正的差异化

与其说本框架「功能最多」，不如说它强调以下组合：

1. 同一共享底座下隔离 Production 与 Tooling 的质量成本。
2. 用代码而不是中央规范文档表示当前实现。
3. 用确定性脚本管理状态和门禁，用 LLM 处理语义。
4. 同时保留语义 Review 和机器 Verification。
5. 通过有限修复、定向复审和转人工控制 Token 与无限循环。
6. 不把 Agent 调度能力包装成已经完成的独立 Workflow Engine。

### 7.2 适合与不适合

适合：

- 需要强审计、变更证据和风险分层的生产代码变更。
- 大型非生产工具，希望在需求和设计批准后自主执行。
- 同时使用 Codex 和 Claude Code，希望共享一套工程规则。
- 愿意维护 `verify.config.json`、Tests 和 Change Artifact 的团队。

不适合：

- 单文件、一次性、几分钟即可完成的小脚本。
- 只需要 PRD 拆 Task，不需要完整质量闭环的场景。
- 不愿维护测试、验证配置和结构化 Artifact 的项目。
- 希望开箱即得完整发布、灰度和监控平台的团队。

## 8. 未完成路线

### 8.1 优先补齐

1. 选择低爆炸半径 Production 项目，积累真实验收数据。
2. 建立 Tier 1 自动触发评测 Runner。
3. 核验跨项目知识库的真实内容、两级索引和问题命中率。
4. 为 Frontend Pack 建立代表性页面 E2E 基准。
5. 扩大 Telemetry 样本，再决定是否建设 Hooks 或预算门。
6. 在不建设巨型 Engine 的前提下，补端到端 Runner、执行证据绑定和可恢复 Run Store。
7. 评估持久 Checkpoint 与自动崩溃恢复是否值得引入。

### 8.2 暂不宣称已有

- 生产发布、灰度、回滚和线上反馈平台。
- 统一多 CLI、多模型 Worker Runtime。
- Temporal、LangGraph 级独立 Workflow Engine。
- 自动知识淘汰和全自动自进化。
- 集中式 OTel 可观测平台。
- 经过统计证明的质量、速度或 Token ROI 优势。

## 9. 已废弃或被覆盖的历史设计

以下内容仍可能出现在历史文档中，但不是当前合同：

- Tooling 每个 Task 或产物都启动 LLM Review。
- Production 全部 Task 完成后才进行唯一一次 Review。
- 通过旧 `project-knowledge` 或 `opsx-project-knowledge` Skill 维护知识。
- 维护 `openspec/specs/` 中央当前真相库。
- 将 `metrics/session-history.jsonl` 提交 Git。
- 使用 `rapid` 作为 Tooling Profile 名称。
- 声称 OPSX 没有机器校验。
- 声称 Harness 仍缺少 Verify 或基线比较。
- 声称 Tooling 仍然串行、逐 Task 停等、没有 worktree 或机器门禁。
- 声称 OpenSpec Intent 触发点尚未接线。
- 将旧 Structure Snapshot 当作当前架构图。

判断冲突时，以当前代码、`README.md` 和双 Profile 总体设计为准。

## 10. 资料研究覆盖范围

- 扫描目录：旧 `E:/work/my-ai-resource/agentic-framework/docs` 与当前仓库 `docs/`。
- 扫描方式：递归，Markdown。
- 扫描文件：68 篇。
- 去重后候选：45 篇；23 篇是新旧目录中的重复副本。
- 全文阅读：45/45 篇唯一候选；没有候选因数量上限被排除。
- 交叉核验：当前 README、31 个 Skill、安装器、控制流、Verify、Telemetry 和测试。

检索词包括：`profile`、`production`、`tooling`、`workflow`、`opsx`、`openspec`、`spec kit`、`taskmaster`、`compound`、`BMAD`、`superpowers`、`verify`、`spec drift`、`telemetry`、`frontend`、`project-init`、`knowledge`、`self-refinement`、`troubleshooting`、`worktree`、`DAG`、`review`、`deterministic`、`install` 和 `harness`。

### 10.1 全文阅读资料

1. `docs/design-docs/framework-unification/spec.md`
2. `docs/design-docs/opsx/code-first-deterministic-validation/spec.md`
3. `docs/tooling/01-why-and-methodology.md`
4. `docs/tooling/03-parallel-execution-mode.md`
5. `docs/tooling/04-compound-engineering-comparison.md`
6. `docs/tooling/05-industry-comparison.md`
7. `docs/tooling/06-official-frontend-skills-installation.md`
8. `docs/tooling/08-evaluation-strategy.md`
9. `docs/tooling/09-personal-knowledge-base-plan.md`
10. `docs/tooling/10-harness-engineering-practices.md`
11. `docs/tooling/11-session-telemetry.md`
12. `docs/tooling/12-development-workflow-absorption-audit.md`
13. `docs/tooling/adr/001-machine-verification-gate.md`
14. `docs/tooling/adr/003-review-fix-loop-convergence.md`
15. `docs/tooling/arch-snapshots/agentic-framework/insights.md`
16. `docs/tooling/design-docs/workflow-code-generation/deterministic-control-flow/spec.md`
17. `docs/tooling/design-docs/workflow-code-generation/deterministic-control-flow/tasks.md`
18. `docs/tooling/design-docs/workflow-verification/ai-maintained-config/spec.md`
19. `docs/openspec-alignment/01-openspec-core.md`
20. `docs/openspec-alignment/04-opsx-fork-vs-openspec.md`
21. `docs/design-docs/framework-unification/tasks.md`
22. `docs/design-docs/framework/dual-track-merge/spec.md`
23. `docs/design-docs/opsx/code-first-deterministic-validation/tasks.md`
24. `docs/harness-alignment/01-source-summary.md`
25. `docs/harness-alignment/02-gap-analysis.md`
26. `docs/harness-alignment/03-roadmap.md`
27. `docs/harness-alignment/README.md`
28. `docs/incidents/2026-07-19-untracked-plan-deletion.md`
29. `docs/openspec-alignment/02-gap-analysis.md`
30. `docs/openspec-alignment/03-roadmap.md`
31. `docs/openspec-alignment/README.md`
32. `docs/tooling/README.md`
33. `docs/tooling/02-tool-landscape.md`
34. `docs/tooling/07-critical-review.md`
35. `docs/tooling/13-agentic-workflow-engine-references.md`
36. `docs/tooling/adr/002-retain-and-widen-fastpath.md`
37. `docs/tooling/adr/004-lighten-default-workflow.md`
38. `docs/tooling/arch-snapshots/agentic-framework/structure.md`
39. `docs/tooling/design-docs/session-telemetry/task-attribution/spec.md`
40. `docs/tooling/design-docs/session-telemetry/task-attribution/tasks.md`
41. `docs/tooling/design-docs/workflow-code-generation/write-lock-timeout/spec.md`
42. `docs/tooling/design-docs/workflow-code-generation/write-lock-timeout/tasks.md`
43. `E:/work/my-ai-resource/agentic-framework/docs/08-evaluation-strategy.md`
44. `E:/work/my-ai-resource/agentic-framework/docs/10-harness-engineering-practices.md`
45. `E:/work/my-ai-resource/agentic-framework/docs/12-development-workflow-absorption-audit.md`

## 11. 不确定性

- 本轮没有联网核验开源框架最新版，对比结论可能随外部项目升级而过时。
- 没有审计外部 `E:/work/shared-knowledge-base` 的实际内容和使用数据。
- 没有 Production 长期运行、故障率、交付周期或 Token ROI 数据。
- Prompt 与 Skill 接线不能证明所有模型和所有会话都稳定遵从。
- 测试证明当前实现回归通过，不等同于真实业务效果评测。
- 没有统一的真实项目采纳率、成功率和长期缺陷数据。
- 历史 Tasks 中的测试数字只代表当时快照，当前状态以第 5 节实测结果为准。
