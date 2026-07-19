# 框架合并：单仓库双轨制方案

**状态**：Superseded

**日期**：2026-07-19

**替代方案**：`../../framework-unification/spec.md`

> 本文已从 Claude Code 会话历史完整恢复并保留。最终实施采用替代方案；本文中的平铺源码布局、独立 Judge 和共享底座治理规则已被吸收。

## 1. 背景

本仓库与 `E:\work\my-ai-resource\agentic-framework` 是同源分叉：

- **本仓库**（`agentic-engineering-framework`）：历史上曾双轨共存（见 `docs/openspec-alignment/README.md`「本仓库同时提供两套设计工作流」），后将 `workflow-*` 拆出，裁剪为 `opsx-*` 专属，服务**生产环境**与「对外符合 OpenSpec、不要中央真相库」的约束。
- **my-ai-resource 分叉**：复制 `workflow-*` 全套后独立演进（并行 agent 执行、机器验证、会话遥测、前端工作流等），服务**大型非生产工具**的「前重后自主」场景。

分叉后共享底座（`bp-*` / `std-*` / reviewer agents 等）出现双头维护漂移，实测已有 7 处小分叉 + 1 处实质分叉（`workflow-code-review`）。每次改底座需手动同步两边，成本持续累积。

## 2. 目标与非目标

### 目标

- 合并为**单仓库、双轨制**：生产轨 `opsx-*` 与工具轨 `workflow-*` 共存，共享底座归一为单一事实源。
- 消灭共享底座的双头维护与漂移。
- 保留两轨各自已明确记录的哲学取舍，不强行统一。

### 非目标（明确不做）

- 不把两条工作流收敛成一条流水线——场景差异（生产 vs 非生产工具）决定两档严格度配置各有存在理由。
- 不给 `opsx-*` 加中央规范库或知识沉淀（`docs/openspec-alignment/04-opsx-fork-vs-openspec.md` 已记录的有意取舍）。
- 不给 `workflow-*` 轨加变更目录制。

## 3. 已拍板决策

| 编号 | 决策 | 结论 |
|------|------|------|
| D1 | 合并后的家 | **本仓库**（`E:\github\agentic-engineering-framework`，独立仓库、有 LICENSE、便于分发） |
| D2 | opsx 统一 Review 与 strict 档独立 Judge 约束 | **opsx 的统一 Review 上提给独立 Judge agent**——主会话参与实现时不得自任 Judge。生产轨不应比工具轨高风险档更松 |
| D3 | 共享底座演进节奏 | **谁改谁保证两轨通用**——改 `bp-*` / `std-*` / agents 前先答「两轨是否通用」；只对某轨有意义的规则沉到该轨的 workflow skill 内。不强制共享底座改动走 opsx 流程 |

## 4. 目标形态

```text
agentic-engineering-framework/
├── skills/
│   ├── opsx-*/               # 生产轨：变更目录制 + 确定性门禁 + 统一 Review
│   ├── workflow-*/           # 工具轨：前重后自主 + 并行执行 + 分级 review + intent 沉淀
│   ├── bp-* / std-*          # 共享底座（单一事实源）
│   ├── workflow-code-review/ # 共享：两轨共用，三档制（见 6.1）
│   └── self-refinement / troubleshooting / project-knowledge / project-init / ...
├── agents/                   # 共享 reviewer / researcher（含 comprehensive-reviewer）
├── commands/                 # opsx-* 前缀与无前缀命令并存，零冲突
├── scripts/
│   ├── validate_change.py            # 生产轨三门（plan / delivery / archive）
│   ├── install_agentic_framework.py  # 新增 --profile opsx|workflow|all
│   ├── lint_skill_graph.py           # 扩展覆盖 opsx-*
│   └── analyze_session_metrics.py    # 会话遥测（自工具轨搬入）
├── metrics/session-history.jsonl
└── docs/
    ├── workflow-track/       # 工具轨设计文档（01~13 + adr/ + arch-snapshots/，整体搬入）
    ├── openspec-alignment/   # 原地保留
    ├── harness-alignment/    # 原地保留
    └── design-docs/          # 两边 feature spec 合并于此
```

### 双轨路由表（合并后写进 README 顶部）

| 判断维度 | 生产轨 `opsx-*` | 工具轨 `workflow-*` |
|---|---|---|
| 变更进生产吗 | 是 | 否（大型非生产工具） |
| 入口 | `/opsx-requirements-clarification` → `/opsx-system-design` → `/opsx-code-generation` → `/opsx-archive` | `/requirements-clarification` 或 `/quick-design` → `/code-generation` |
| 执行节奏 | 逐阶段停等批准 | tasks.md 批准后自主连跑（并行 agent + worktree） |
| 变更产物 | `openspec/changes/<name>/` 整目录，归档可溯源 | `docs/design-docs/<module>/<feature>/spec.md` |
| 机器门禁 | `validate_change.py` 三门 | `lint_spec` / `lint_task_deps` / `check_delivery` + `workflow-verification` |
| Review | Delivery 后统一一次，`strict` 档 + 独立 Judge（D2） | 每产物分级（lightweight / standard / strict） |
| 知识沉淀 | 不承担（变更文档即 intent 记录） | `project-knowledge`：ADR + arch-snapshot + 交付前 intent 门 |

## 5. 逐项裁决

### 5.1 直接搬入（工具轨独有，零冲突）

Skills：`workflow-code-generation`、`workflow-requirements-clarification`、`workflow-system-design`、`workflow-quick-design`、`workflow-test-generation`、`workflow-verification`、`workflow-frontend-design`、`bp-frontend-layout`、`bp-frontend-taste`、`frontend-playwright-verification`、`project-init`、`project-knowledge`、`bp-cola-ddd`、`std-react`、`open-code-review`。

其他：`comprehensive-reviewer` agent、13 个无前缀 command、`scripts/install_agentic_framework.py`、`scripts/lint_skill_graph.py`、`scripts/analyze_session_metrics.py`、`metrics/session-history.jsonl`。

### 5.2 保留本仓库（生产轨独有，零冲突）

全部 `opsx-*` skill 与 command、`bp-skill-authoring`、`scripts/validate_change.py`。

### 5.3 取新覆盖（微小分叉，5～15 行，多为 frontmatter 措辞）

`bp-architecture-design`、`bp-component-design`、`bp-performance-optimization`、`std-python`、`self-refinement`、`troubleshooting`、`codebase-researcher`——逐个看 diff 取较新一侧。

### 5.4 实质裁决：`workflow-code-review`

**分歧**：分叉侧已演进为三档制（`lightweight` / `standard` 用 `comprehensive-reviewer` 单趟综合审，`strict` 全量 5 维 + critic + 独立 Judge 约束 + 复审模式）；本仓库版无档位、始终全量 5 维。

**裁决**：以分叉侧三档版为唯一版本。理由：其 `strict` 档在审查维度上完全覆盖本仓库版行为，且多出复审收敛机制与独立性约束。

**适配动作**：

- `opsx-code-generation` / `opsx-test-generation` 调用点显式传 `review_profile: strict`，保持生产轨现有审查强度不变。
- 按 D2：opsx 的 Delivery 后统一 Review 派独立 Judge agent 执行，主会话参与实现时不得自任 Judge。
- `evaluation/` 评测集随 skill 搬入。

### 5.5 docs 合并

- 分叉侧 `docs/`（01~13 编号文档 + `adr/` + `design-docs/` + `arch-snapshots/`）整体搬入 `docs/workflow-track/`，保内部相对链接。
- 本仓库 `docs/openspec-alignment/`、`docs/harness-alignment/`、`docs/design-docs/opsx/` 原地保留。
- 两边 README 合并为一份：顶部放双轨路由表，双轨各自的文档索引分区列出。

## 6. 关键改造点

1. **安装脚本加 profile**：`install_agentic_framework.py --profile opsx|workflow|all`。生产项目装 opsx 轨 + 共享底座，工具项目装 workflow 轨 + 共享底座；共享底座始终随装。
2. **`lint_skill_graph.py` 扩展覆盖 `opsx-*`**：dangling / orphan / command 目标 / reviewer 档位映射闭环的检查范围扩到全仓库，消灭共存期接线断点。
3. **共享底座治理规则写进 CONTRIBUTING**（D3）：改共享底座前先答「两轨是否通用」；轨专属规则沉到该轨 skill 内。
4. **分叉退役**：`my-ai-resource/agentic-framework` 清空为一页指针 README（历史留在 monorepo git）；全局 `.claude` / `.codex` 副本改由本仓库安装脚本刷新。退役前确认 main 干净（防 2026-07 曾发生的功能分支 WIP 泄漏进全局副本）。

## 7. 迁移步骤与验收门禁

```text
1. 新建分支 merge-workflow-track           → 验证: git status 干净
2. 按 5.1/5.2/5.3 搬运与覆盖               → 验证: 逐 skill diff 复核
3. 裁决 workflow-code-review + opsx 调用点  → 验证: opsx-* 中 grep 到显式 review_profile
4. 扩展 lint_skill_graph 并全仓跑           → 验证: 退出码 0
5. 安装脚本 --profile + --dry-run 三档跑     → 验证: 三种 profile 文件清单符合预期
6. validate_change.py 三阶段自测 +
   工具轨三个 lint 脚本自测                 → 验证: 全部退出码正常
7. README / CONTRIBUTING 合并改写           → 验证: md-zh 排版自检
8. 合入 main，分叉退役为指针               → 验证: 全局重装后 /code-review 与
                                                  /opsx-code-generation 均可触发
```

预估一个工作日内完成（不含 D2 若需调整 opsx 流程细节的增量）。

## 8. 备选方案与权衡

| 备选 | 排除理由 |
|------|---------|
| 维持两仓库分立 | 共享底座双头维护成本持续累积，漂移已实际发生 |
| 收敛为一条工作流 | 两轨差异是各自文档记录过的有意取舍（生产可溯源停等 vs 工具并行自主），强行统一会丢掉一侧核心价值 |
| 以 my-ai-resource 为家 | monorepo 子目录不利于独立分发；本仓库已有 LICENSE / CONTRIBUTING 与独立 remote |
| opsx 调用 review 时豁免独立 Judge 约束 | 生产轨没有理由比工具轨高风险档更松（D2 已否决） |
| 共享底座改动一律走 opsx 流程 | 小改动过重，治理成本不随风险分级，违背两轨共同的分级投入哲学（D3 已否决） |

## 9. 风险与已知代价

- **共存期语义漂移**：两轨引用同一共享底座，某轨的需求可能悄悄污染共享规则。缓解：D3 治理规则 + `lint_skill_graph` 全仓检查。
- **`workflow-code-review` 三档版对 opsx 的行为等价性**：`strict` 档覆盖原全量行为是静态分析结论，实施后需以一次真实 opsx 变更走查确认。
- **分叉退役后的回滚成本**：monorepo git 历史保留完整，可随时找回；指针 README 保证不迷路。
