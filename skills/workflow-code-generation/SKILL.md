---
name: workflow-code-generation
description: 代码文件修改的统一入口。任何代码变更（新功能、优化、Bug 修复、重构）必须先调用此 skill。按复杂度路由：默认 Native Delivery；Fast-Path 仅为轻量兼容别名，中等及以上按升级条件进入完整 Runtime（tasks.md 批准后自主连跑，worktree 隔离、全部完成后统一一次 workflow-code-review、末尾 intent 沉淀）。仅适用于代码文件（.cc/.cpp/.h/.go/.py 等），改 .md 等非代码文件不调用。
---

> 输出一行：`Using workflow-code-generation`

# 代码生成（统一执行入口）

**先加载规范再写代码。** 设计门（需求 / 设计 / tasks 批准）与质量基建（review + intent 沉淀）不跳过，执行形态按复杂度路由——见下表。

前端分支由本地 `workflow-frontend-design` 定方向；本 skill 只消费其产出的 `ui-spec.md`，不维护外部前端技能选择表。

## 执行形态总览

| 复杂度 | 默认执行形态 | 前置 |
| --- | --- | --- |
| **轻量**（请求即计划的局部低风险修改） | **Native Delivery**：当前宿主直接执行；Fast-Path 仅作兼容别名 | 免 spec / tasks |
| **中等**（已明确目标与验收标准，需拆分或委派） | **Native Delivery**：下放 Agent 执行，按需使用 DAG | spec + tasks 批准 |
| **strict** 或命中 Runtime 升级条件 | **完整 Runtime Run**：下放 Agent 执行并初始化 Run | spec + tasks 批准 |

> Runtime 升级条件仅包括：`strict` 风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或明确审计要求。任务文件数或模型版本不是升级条件。下放执行再分：**单 task / 串行依赖** → 单 Agent 按任务顺序连续执行，不调用 `waves` / `dispatchable`；**存在可并行分支** → 控制器分波并行。

---

## 步骤 1：评估复杂度与路由

> ⚠️ **防御性检查**：无法明确回答「实现什么行为」「怎样算完成」中任一个 → **立即停止**，调用 `workflow-requirements-clarification`。需求和验收标准清楚、但尚不能确定文件或实现方案，不等于需求不清；按下方规则进入 `workflow-quick-design`。

- **轻量改动** → **Native Delivery**。核心判据是**请求即计划**：用户请求本身已完整确定改什么、怎么改，AI 无需替用户做任何未言明的设计决策。在此前提下须全部满足：路由阶段就能确定完整文件列表；每处修改是局部的（不改函数签名 / 模块边界 / 公开接口）；不碰数据 / 权限 / 并发 / 安全 / 性能关键路径。文件数只作护栏不作主判据：超过 3 个文件默认不走此分支，除非是同一模式的机械重复（如统一改名、同一防护补丁多点应用）。机械重复是指每处应用相同变换，不改变接口、契约、控制流或模块交互。兼容期仍沿用 `lightweight` Review；报告与交付口径按兼容合同处理。
- **需求与验收标准清楚，但需要补实现方案或文件定位** → 直接调用 `workflow-quick-design`，不先走需求澄清。若 Quick Design 识别出安全、权限、数据迁移、并发、分布式、性能关键路径、公共 API 或大范围重构，再升级为完整需求与系统设计流程。
- **需求或验收标准不清楚** → 调用 `workflow-requirements-clarification`。
- **其余一切**（已有 spec / tasks，或 Quick Design 完成）→ **标准流程**（默认下放到 Native Delivery）。
- **完整 Runtime Run** 仅在 `strict` 风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或明确审计要求命中时启用。无法确定风险时选 `standard`，不因不确定自动升级 Runtime；若无法确认是否命中执行条件，先澄清再开始。

## 步骤 1.5：Verify 配置选择（路由后无条件）

步骤 1 已得出可执行路由后，**无条件**检查仓库根 `verify.config.json`；此检查不依赖 `tasks.md` 是否存在。必须在进入 Native Delivery、读取／创建任务、下放 Agent、运行代码或测试前完成：

- 配置存在 → 继续；动代码前仍按 `workflow-verification` 采基线。
- 配置缺失 → **立即暂停**，要求用户明确选择「初始化」或「跳过」；不得把任务确认、内置 Spec Drift 或后续 `event start` 当成该选择的替代品。
- 用户选择「初始化」→ 实际运行 `/verify-config` 并确认配置已生成后继续；用户选择「跳过」→ 本次只可运行内置门禁，并在最终报告标注。
- 对 Standard／Runtime 路径，`tasks.md` 已存在时立刻写入该已作出的选择；尚未创建时，创建后第一时间写入，且必须早于任何 `event start`。使用 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md> verify-config-decision --choice initialize|skip --write`。Native Delivery 没有 `tasks.md` 时，保留用户明确选择并在最终报告如实记录。

步骤 3 的任务确认**不再首次询问或推断**该选择，只负责持久化步骤 1.5 已取得的选择。任何预存 `tasks.md` 都不得绕过本暂停点。

---

## Native Delivery（轻量改动；Fast-Path 兼容别名）

轻量任务由当前宿主执行；中等任务可下放 Agent 并按需使用 DAG。两者都属于 Native Delivery，不创建或伪造 Run Context。**Fast-Path 只是旧调用方的兼容别名，不再按「主会话直接修改」定义另一条默认路径。**兼容别名保留 lightweight integration Review；新的低／中风险标准交付使用 standard integration Review。两者都不增加完整 Runtime 的声明。

1. 加载编码规范（同步骤 4）。
2. 实现改动（步骤 1.5 已完成配置选择；有 `verify.config.json` 时，动代码前先 `workflow-verification` 采基线；选择跳过时只跑内置门禁并在交付报告标注）。发现外溢（超出步骤 1 路由判据）→ **立即退出**，转标准流程。
3. **机器验证**：加载 `workflow-verification`（有 config 比基线；无 config 也跑内置 spec drift 检查），绿才继续；失败回第 2 步修复，若只是无法证明相关规格已更新且确实无需更新，则补 `--spec-drift-reason` 后重跑。
4. **前端验证**：若涉及 UI / 样式 / `.tsx` / 用户操作路径，加载 `bp-frontend-taste` 后再用 `frontend-playwright-verification` 做浏览器验证；产生代码改动时回到第 3 步重验。
5. **统一 Code Review**：实现、测试和机器验证全部完成后，加载一次 `workflow-code-review`（Fast-Path 兼容别名使用 `review_profile: lightweight`；新的 Native Delivery 使用 `standard`；均为 `scope: integration`，`mode: initial`）。Review Artifact 必须由审查流程生成，implementer 只能原样保存，不得依据对话手写 JSON。结论为 `NEEDS_CHANGES`（存在 keep 的 P0 / P1）→ 自行修复、重跑受影响的机器验证，再按 `mode: re-review` 定向复核，最多 2 轮；禁止启动第二次全量首审。
6. **交付前沉淀检查**：见下方[「交付前沉淀检查」](#交付前沉淀检查)（强制，Fast-Path 不豁免）。
7. **提交**：将本次改动提交本地 git（push / `svn commit` 由用户决定）；用户明确要求不提交时，在交付报告标注「未提交待用户处理」。
8. **交付门（机器判定）**：Fast-Path 兼容别名免传 spec / tasks 与 `--run-dir`，但必须传由审查流程生成的 lightweight integration Review、独立机器验证报告与长期知识影响结论：命中时运行 `python <本 skill 目录>/scripts/check_delivery.py --review-report <review-report.json> --verify-report <.agentic-framework/verify/report.json> --knowledge-impact hit`；未命中时运行 `python <本 skill 目录>/scripts/check_delivery.py --review-report <review-report.json> --verify-report <.agentic-framework/verify/report.json> --knowledge-impact none --knowledge-impact-reason "<具体理由>"`。门禁校验 `scope: integration` 的 lightweight Review（P0／P1 = 0）、机器验证 verdict = PASS、工作区干净与知识影响结论；通过则输出兼容裁决 `fast-path-pass`，不得声明 strict Review 或 Trust Gate PASS。交付报告只能逐字引用该命令的原始输出，并标为「Fast-Path 兼容裁决」；由于没有归档路径，不得把它概括为「交付门 PASS」。新的标准 Native Delivery 必须走下方标准流程的 `--native-delivery` 门。非 0 → 补齐 Review 报告、机器验证、知识影响结论或提交后重跑。
9. 按[「统一交付证据格式」](#统一交付证据格式)输出改动说明，**结束**。

---

## 标准流程

### 步骤 2：查找 / 确认 spec

查找 `openspec/changes/<ticket>-<change-name>/proposal.md`：
- Standard：完整读取 `proposal.md`、`design.md`、`specs/` 下的 Delta 和 `tasks.md`；缺 Proposal 路由到 `workflow-requirements-clarification`，缺 Design 路由到 `workflow-system-design`。
- Quick：`proposal.md` 标记 `Quick Draft`，允许不创建 `design.md` 和 Delta；缺必要章节时调用 `workflow-quick-design`。
- 旧 `spec.md` 和 `docs/design-docs/` 只允许迁移读取，任何新 Change 禁止写入旧 Artifact。

**强制**：`proposal.md` 与 `tasks.md` 同时存在时，编码前必须完整读取；存在 `design.md` 和 Delta 时也必须完整读取。

同时读取 `openspec/index.md`，再按当前 Task 定向读取相关模块 `custom/` 约束和踩坑；随后回到代码核实现状。知识与代码冲突时必须显式报告双方证据，不得静默修改任意一方。

**前端分支检查**：任务涉及 `.tsx` 文件或 UI 页面时：
- 同目录下存在 `ui-spec.md` → 与 `proposal.md`、`design.md` 和 Delta 一起**强制通读**，`ui-spec.md` 是视觉与布局契约，代码实现须与其对齐。
- 同目录下不存在 `ui-spec.md` → **立即停止**，提示用户先运行 `/frontend-design` 生成视觉方案，再回到本工作流。

### 步骤 3：检查 / 创建 tasks.md

- **已存在** → 若步骤 1.5 时配置缺失，先持久化已作出的「初始化」／「跳过」选择，再进入步骤 4。
- **不存在** → 先读 [reference/task_planning_guide.md](reference/task_planning_guide.md)，严格按其流程创建。每个 task 须带 `depends_on`、`review_profile`、`context_files`、`verification`、`artifacts`——**`depends_on` 是分波并行的依据，`review_profile` 是分级 review 的依据，均必填**。

若本次改动可能涉及不可逆 / 高影响架构决策、放弃某方案或新增红线约束，预留一个「intent 沉淀」任务（步骤 6 收口）。

**前端任务闭环**：若本次涉及 UI / 样式 / `.tsx` / 用户操作路径，`tasks.md` 必须包含：
- 实现任务：按 `ui-spec.md` 实现页面 / 组件。
- 测试任务：通过 `workflow-test-generation` 生成或补齐关键交互 / 状态测试。
- 最终验证任务：执行 `bp-frontend-taste` 和 `frontend-playwright-verification`，失败则回到实现任务修复。

> 🚨 **创建 tasks.md 后必须停下等用户确认。** 展示任务列表（含依赖），**停止等待回复**。这是**人把关的最后一道闸**；批准后执行段自主连跑、不再逐 task 停。此处不得首次询问或推断 Verify 配置选择：若步骤 1.5 时配置缺失，先将已作出的「初始化」／「跳过」选择写入 `tasks.md`，再展示任务并等待确认。代码任务冻结既有检查和 `ignore_paths`。只有实现产生并已试运行、带非空 `_note` 的新入口时，才可按 `workflow-verification` 受限追加显式 `baseline_aware: false` 检查，不得改删既有配置或重采基线。

### 步骤 4：加载编码规范（🚨 强制前置）

> **未加载规范就写代码 → 立即停止，先加载。** 下放 agent 时，把规范要点写进 prompt 或令其自行加载对应 skill。

| 规范 | 何时加载 |
| --- | --- |
| `bp-coding-best-practices` | 必须 |
| `bp-performance-optimization` | 必须（所有代码都性能敏感） |
| `std-cpp` / `std-go` / `std-python` | `.cc/.cpp/.h` / `.go` / `.py` 文件 |
| `bp-cli-tool-design` | 实现或修改 CLI、部署脚本、运维脚本或自动化命令 |
| `std-react` | `.tsx` / `.ts` 前端文件；默认用 shadcn/ui 写基础组件 |
| `bp-frontend-layout` | 新页面、页面重排、导航结构、响应式骨架 |
| `bp-frontend-taste` | 可见 UI 实现完成后的收尾质检 |
| `bp-distributed-systems` | 网络通信 / 多节点协调 / 一致性 / 故障恢复 |

#### Overlay 规范发现

编码或测试前，从当前已加载的核心 workflow `SKILL.md` 真实路径（解析链接后）向上定位框架根，再运行 `python <framework-root>/scripts/install_agentic_framework.py --validate-extensions .`。无法确定该受信框架根时不得加载 Overlay，并报告失败。只消费其 JSON 输出；目标文件后缀匹配 `skills[].files` 时，才加载当前 client 的对应 Skill。不得直接读取 `.agentic-framework/extensions/*.json`，也不得从目标项目 Manifest 的 `source` 获得可执行路径。Overlay 只补充规范，不自动执行、不覆盖核心 Skill，也不修改 workflow。

### 步骤 5：下放 agent 执行（🚨 批准后自主连跑）

`tasks.md` 经用户批准后，执行下放给 Agent：**主会话只编排，不亲自写代码、不逐 task 停等**，全部跑完一次性汇总。除非命中 Runtime 升级条件，标准流程默认使用 Native Delivery，不创建 Run Context。

**先为每个 task 判定 review 档位**：

| 档位 | 适用 |
| --- | --- |
| `lightweight` | 小需求 / 低风险：局部改动，或不改变接口、契约、控制流与模块交互的跨文件机械重复改动；不碰数据 / 权限 / 并发 / 安全 / 性能关键路径 |
| `standard` | 默认档：普通功能、Bug 修复，或涉及多个模块之间的行为、契约、交互变化但风险可控 |
| `strict` | 高风险：生产关键路径、安全 / 权限 / 数据迁移 / 并发 / 分布式 / 性能敏感 / 公共 API / 大范围重构 |

无法判断风险时选 `standard`；命中高风险任一条件时选 `strict`。各 task 的档位用于选择最终 Review；owner / implementer 禁止在 task 内启动 LLM Review。无 `strict` 风险及 `--parallel-worktree-write`、`--long-task-recovery`、`--cross-host-capability-verification`、`--audit-required` 任一升级条件时，直接进入 Native Delivery，不运行恒为 `native-delivery` 的 `route` 步骤。可能命中升级条件时，主编排方才在业务副作用前运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> route --review-profile <最高档位>` 并传入对应 flag；输出 `runtime-run` 时才进入完整 Runtime Run，输出 `native-delivery` 时不得创建或伪造 Run Context。

**主会话只在并行分支、非线性依赖图或中断恢复时通过控制流内核构建波次（wave）数组**：先运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> waves` 得到任务 ID 分层数组，按 [reference/delegated-execution-guide.md](reference/delegated-execution-guide.md) 将当前一波的每个任务 ID 富化为 task 对象（从 `tasks.md` 取 `title`、`context_files`、`verification`、`artifacts`、`review_profile`）后再传入 Workflow 工具的 `args.waves`。仅该路径在每波 dispatch 前运行 `dispatchable`。单 task 或纯串行的小任务按 `tasks.md` 顺序直接执行 `event <id> start --write`；该命令仍校验前置依赖与 Verify 配置选择，不得绕过。缺 `depends_on` 时先由 `lint_task_deps.py` 报错，修复前禁止全并行。**禁止另写一套手工分波或状态判断**。

**先判定 CLI 嵌套能力**（派子 agent 试再派孙 agent；判定细则与 5 层上限见 reference 手册），选编排模式：
- **模式 A（默认，Claude Code 支持嵌套）**：每 task 派 owner 子 agent 执行实现、测试和机器验证。
- **模式 B（兜底，不支持嵌套）**：implementer 执行相同职责，由主 agent 负责状态编排。

**详细操作（Phase 0 准备 / Phase 1 逐波执行 / 失败隔离 / 合并 / 阻塞）见 [reference/delegated-execution-guide.md](reference/delegated-execution-guide.md)，按其执行。** 核心不变量：每产物必须完成实现、测试和任务级机器检查后才合并；LLM Review 只在全部任务合并并完成全局验证后启动一次。失败标 `需人工` 不阻塞其余；上游未合并则下游 `阻塞`；`tasks.md` 的 `状态:` 字段是续跑真相源。

当路由为 `runtime-run` 时，Phase 0 必须先调用 `workflow_control.py <tasks.md> init-run`，传入 `.agentic-framework/runs/<run-id>`、Spec、`AGENTS.md`、本 Skill、Harness 声明与 Adapter 命令。该命令在业务副作用前冻结规则输入与完整 Task Plan、生成 Run Context、执行 Harness 启动能力门并创建 Journal；失败时禁止 dispatch。此路径的每次 `quality_passed --write` 必须同时传 `--run-dir` 和该次执行生成的 Envelope Verify Artifact，旧式无 Run/Task/Attempt 绑定的顶层 `PASS` JSON 不得放行。路由为 `native-delivery` 时，不调用 `init-run`；`quality_passed --write --verify-report <standalone-report.json>` 必须校验 `PASS` 顶层结论、零错误／违规，以及每项完整的 `CheckResult` 合同，不写入任何 Run Artifact。

### 步骤 6：功能交付与 intent 沉淀（🚨 强制，全部 task 完成后触发）

全部 wave 处理完、`tasks.md` 任务为 `完成` / `需人工` / `阻塞` 时，**禁止直接宣布交付**，先走：

1. **汇总报告**（一次性，不逐 task）：汇总每个 task 的实现、测试和机器检查结果，列出哪些 `需人工`、哪些 `阻塞`、哪些合并冲突。
2. **机器验证**：对合并结果整体跑 `workflow-verification`。`runtime-run` 传 `--run-dir <run-dir>` 生成 Run 级 Verify Artifact；`native-delivery` 生成独立 Verify 报告，不创建 Run Artifact。有 config 时必须传 `--baseline <repo-root>/.agentic-framework/verify/baseline.json --diff-base <base_sha>`；无 config 时必须传 `--diff-base <base_sha>` 触发内置 spec drift 检查。FAIL → 派 fix Agent 修复后重验；仍 FAIL 标 `需人工`。
3. **前端验证**：若涉及 UI / 样式 / `.tsx` / 用户操作路径，加载 `bp-frontend-taste` 后再用 `frontend-playwright-verification` 做浏览器验证。失败则修复并回到第 2 步重验。
4. **一次最终审核**：对本次全部变更调用一次 `workflow-code-review`（`mode: initial`）。`native-delivery` 固定产出无 Run 的 `scope: integration`、`review_profile: standard` 报告；`runtime-run` 固定产出绑定 Run Context 的 `scope: run`、`review_profile: strict` Envelope。Artifact 必须由审查流程生成：`standard` 可由 `comprehensive-reviewer` 自证，`strict` 必须由未参与实现的独立 Judge 裁决；implementer 不得手写或改写 Artifact。存在 keep 的 P0 / P1 时派 fix agent 修复、重跑受影响的验证，再按 `mode: re-review` 只复核 finding 和修复 diff；最多 2 轮，禁止启动第二次全量首审。
5. **交付前沉淀检查**：见下方[「交付前沉淀检查」](#交付前沉淀检查)，执行统一知识影响检查，并逐条核销步骤 3 / Phase 1 预留的「intent 沉淀」任务。命中长期知识影响时记录目标 `openspec/specs/` 或 `openspec/issues/` 及同步状态；Fast-Path 未创建 Change 时必须说明无长期知识影响的理由。
6. **知识同步与归档**：加载 `project-knowledge`，对照实际 Diff 和验证证据完成 Delta、索引、Issues 与冲突检查；知识同步任务未完成时禁止归档。**归档移动前必须先跑 `python <本 skill 目录>/scripts/lint_task_deps.py <tasks.md 路径> --state-consistency`**：`tasks.md` 的任务头复选框、`- 状态：` 字段与验收标准／子任务复选框必须同向。`状态：完成` 的任务，任务头须标 `[x]` 且验收项与子任务全部勾选——复选框由执行方按**真实完成情况**勾选，不得为过门而批量勾选；未达成的验收项应改状态为 `需人工` / `阻塞` 并附原因。非 0 → 修正后重跑，不得带着矛盾状态归档。通过后把 `proposal.md` 头部 `状态` 改为 `Archived`，并将整个 Change 移到 `openspec/changes/archive/<ticket>-YYYY-MM-DD-<change-name>/`。
7. **提交归档产物**：将工作区本次残留的全部改动（fix 修复、spec / tasks / ADR / issues 等文档）提交本地 git，提交信息关联 feature，交付时工作区必须干净；push / `svn commit` 仍由用户决定。
8. **交付门（机器判定）**：`runtime-run` 对归档后的路径运行 `python <本 skill 目录>/scripts/check_delivery.py --run-dir <run-dir> --tasks <archived-tasks.md> --spec <archived-proposal.md> --review-report <run-dir>/artifacts/review-run.json --knowledge-impact hit|none`；`none` 时追加 `--knowledge-impact-reason "<具体理由>"`。门禁校验完整 Manifest 可达性、Journal、Harness 启动证据、Trust Gate、任务终态（含状态字段与复选框一致性）、归档、Git 状态与知识影响结论。`native-delivery` 运行 `python <本 skill 目录>/scripts/check_delivery.py --native-delivery --native-delivery-verdict <repo>/.agentic-framework/native-delivery/verdict.json --tasks <archived-tasks.md> --spec <archived-proposal.md> --review-report <review-report.json> --verify-report <verify-report.json> --knowledge-impact hit|none`；`none` 时追加 `--knowledge-impact-reason "<具体理由>"`。该门只接受由审查流程生成的无 Run standard integration Review 与独立 Verify，只能生成有界 Verdict，不得声明 Trust Gate 或 Harness 能力。**交付报告只能逐字引用 `check_delivery.py` 成功执行的原始 stdout，不得自行归纳为「交付门 PASS」或等价措辞。** 缺少归档路径、干净 Git 状态或有效 Review / Verify Artifact，或命令非 0 时，禁止任何「交付门 PASS」类表述；必须改报实际缺失项或失败输出。非 0 → 回对应步骤修复后重跑。
9. 按[「统一交付证据格式」](#统一交付证据格式)交付，等用户验收 `需人工` / `阻塞` 项的处理。

## Scoped Delivery（显式例外）

默认交付门保持「工作区干净」。只有本次任务已在动代码前冻结允许修改路径／生成目录，并由 `workflow-verification --save-baseline --delivery-scope <路径>` 写入 `workspace_residue_snapshot` 时，Native Delivery 才可显式传 `check_delivery.py --scoped-delivery --workspace-residue-baseline <baseline>`：

- Scoped Delivery 必须与 `--native-delivery` 一起使用，并声明 `--knowledge-impact hit|none`；`none` 时必须追加 `--knowledge-impact-reason "<具体理由>"`。Git 同时传 `--delivery-commit <HEAD>`，SVN 同时传 `--delivery-revision <已提交 revision>`。
- 交付门比较 S1 与 S0，并拒绝提交 Diff 超出冻结范围的路径；`--ignore`、`ignore_paths` 和 `changed_files_snapshot` 不参与此判定。
- Scoped Delivery 不适用于完整 Runtime Run；S0 与范围重叠、内容变化、提交证据缺失或无法判定时，切换干净 worktree／工作副本。
- Scoped 成功报告只能逐字引用「本次交付范围干净，预存残留未变化」，不得声称「Git 工作区干净」。

## 统一交付证据格式

最终报告必须包含：

```markdown
## 任务归因
- **Feature**: [feature 标识]
- **Task**: [Task ID/名称]
- **Review Profile**: lightweight / standard / strict
- **Review Retries**: [非负整数]
- **Verify Retries**: [非负整数]
- **Manual Intervention**: 无 / [介入阶段，多个位置用中文逗号分隔]
```

每个 task 输出一个完整区块；同一 task 再次交付时重新输出完整区块。字段名和标题是遥测解析接口，不得改写或省略，不得从对话推测未知值。

- **改动文件**：列出代码、规格、任务、ADR 和关键文档。
- **提交状态**：本地 commit hash（代码与归档产物），或「未提交待用户处理」及原因。
- **交付门**：完整粘贴 `check_delivery.py` 的原始 stdout，不增写 Verdict 摘要、PASS 结论或「交付门 PASS」类措辞。未运行、非 0、缺少归档路径、工作区不干净或 Artifact 无效时，只写实际状态和原始错误，不得声明交付通过。
- **测试命令**：列出实际运行命令、结果；未运行写原因。
- **review 结论**：列出 review_profile、通过 / finding / 需人工。
- **机器验证**：列出 `workflow-verification` 结果和 `.agentic-framework/verify/report.json` 路径；必须包含 `spec_drift` 结论；注明配置消费状态（使用现有 / 缺失已跳过 / 建议刷新及原因——如 exit 2 或配置引用的命令、路径失效，提示用户之后运行 `/verify-config`，不在任务内改配置）。
- **前端截图 / DOM 验证**：涉及 UI 时列截图路径、DOM / console / 交互检查；不涉及写「不涉及」。
- **未验证风险**：列出无法验证项、阻塞原因和建议补验方式。

---

## 交付前沉淀检查

> 🚨 **Fast-Path 与步骤 6 共用 · 强制**：

逐条检查「架构决策」「放弃方案」「新增红线约束」三个信号，并逐行作答「命中 → 已沉淀到 <具体 ADR / spec 章节>」或「未命中」。命中则更新相关 `proposal.md`、`design.md` 或长期 Specs；当前无法完成时在 `tasks.md` 建「intent 沉淀」任务。

---

## 🚨 强制规则

1. 轻量改动外，未经 spec + `tasks.md` 用户批准，**禁止**下放执行。*例外：由 `workflow-quick-design` 自动 pipeline 调用时，spec 用户确认已视为 tasks.md 预授权，本规则不触发。*
2. 有依赖的 task **禁止**同波并行；依赖缺失时保守串行或回问。
3. 每产物必须通过测试和任务级机器检查才合并；全部任务完成后必须统一执行一次首轮 `workflow-code-review`。
4. task 失败 / 冲突**必标** `需人工`（不得静默丢弃或假装通过），且不停其他 task；依赖它的后波**必标** `阻塞` 跳过 dispatch（上游合并后解阻）。
5. 收尾**必做** intent 沉淀检查并给逐条结论。
6. **测试与实现同批交付**（Fast-Path 除外）：接口层与核心逻辑须有覆盖关键路径、能跑通的测试，不允许先实现后补。
7. **进度表述校准**：「已查看」仅用于读取核对，「进行中」仅用于已 dispatch / 已改码，「已完成」仅用于已落地且已合并核对；禁止把「看过」说成「已开始」、把「想过」说成「在推进」。

## 用户跳过 spec 时

必须生成简化版 `proposal.md`（标 `状态: Quick Draft`）。**禁止无 Proposal 修改中等及以上代码。** 该路径交付前同样受步骤 6 约束。

## 恢复中断

中断后先收集已合并任务 ID，再运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> recover --merged <任务 ID...>` 生成恢复计划；按计划核对 worktree 和质量门，详见 [reference/delegated-execution-guide.md](reference/delegated-execution-guide.md) 的「恢复中断」。**恢复路径不豁免步骤 6 的交付前沉淀检查。**

## 与其他 skill 的关系

本 skill 是所有代码修改的统一入口。`workflow-code-review` 是 Native Delivery 与完整 Runtime Run 共用的分级评审门；`workflow-test-generation` 内嵌在每个 task 的执行流程中。设计阶段由 `workflow-requirements-clarification` / `workflow-system-design` / `workflow-quick-design` 承担。
