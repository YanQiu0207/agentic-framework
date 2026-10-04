---
name: workflow-code-generation
description: 代码修改的统一入口；新增功能、修复、优化或重构代码前调用。评估任务范围，组织实现、验证、审查和交付。仅修改 Markdown 等非代码文件时不调用。
---

> 输出一行：`Using workflow-code-generation`

# 代码生成

**在明确需求和验收标准后实现代码，通过验证与审查完成交付。** 先确定执行路径，再加载规范。标准任务须完成设计和任务批准，所有路径都做交付前沉淀检查。

前端任务先由本地 `workflow-frontend-design` 确定设计，本流程按其 `ui-spec.md` 实现。

## 执行形态总览

| 复杂度 | 默认执行形态 | 前置 |
| --- | --- | --- |
| **轻量**（请求即计划的局部低风险修改） | **Native Delivery**：当前宿主直接执行；Fast-Path 仅作兼容别名 | 免 spec / tasks |
| **中等**（已明确目标与验收标准，需拆分或委派） | **Native Delivery**：下放 Agent 执行，按需使用 DAG | spec + tasks 批准 |
| **strict** 风险（仍为 Native，strict Review + 独立 Judge） | **Native Delivery**：三档审查独立执行，不因风险自动建 Run | spec + tasks 批准 |
| **显式选择 Runtime**（`--execution-mode runtime`、硬性审计要求或跨宿主验证） | **完整 Runtime Run**：下放 Agent 执行并初始化 Run | spec + tasks 批准 |

## 步骤 1：评估范围与执行路径

先确认要实现的行为和验收标准，再选择路径：

| 当前信息 | 下一步 |
| --- | --- |
| 需求或验收标准不清楚 | 调用 `workflow-requirements-clarification` |
| 目标清楚，仍需定位文件或确定方案 | 调用 `workflow-quick-design` |
| 请求已明确完整改法，且满足下列轻量条件 | 进入轻量任务执行 |
| 已有规格和任务，或 Quick Design 已完成 | 进入标准流程 |

**轻量条件须同时满足：**

- 请求已确定改什么、怎么改，无需补充设计决策；路由时能列出全部改动文件。
- 修改局部，不改变函数签名、模块边界或公开接口。
- 不涉及数据、权限、并发、安全或性能关键路径。
- 通常不超过 3 个文件。超过时仅允许同一种机械变换，如统一改名或多处应用同一防护补丁；变换不改变接口、契约、控制流或模块交互。

轻量兼容路径使用 `lightweight` Review。Quick Design 若发现安全、权限、数据迁移、并发、分布式、性能关键路径、公共 API 或大范围重构，升级到完整需求与系统设计。

**Runtime 启用条件（change 2048）：** 只有显式 `--execution-mode runtime`、项目硬性审计要求（`--audit-required`，来源由编排方说明）或跨宿主验证（`--cross-host-capability-verification`）才使用完整 Runtime Run。`strict` 风险走 Native strict Review（独立 Judge），并行 Worktree 写入与长任务恢复按需使用隔离和恢复规划，均不自动升级；文件数量和模型版本不作为升级依据。硬性要求与显式 native 冲突、或 Runtime 在当前 VCS 下不受支持时，路由明确报错，不静默降级。

风险无法判断时使用 `standard`；「需要审计」但未说明证据要求时，先确定所需证据，不自动等同于完整 Runtime。SVN 工作副本不支持完整 Runtime：显式 Runtime 需求会被拒绝并说明原因，默认任务直接 Native，不创建 Run Context。

## 步骤 1.5：确认 Verify 配置

路由确定后，先检查仓库根 `verify.config.json`，再读取或创建任务、委派 Agent、运行代码或测试。已有 `tasks.md` 也执行此检查。

| 配置状态 | 动作 |
| --- | --- |
| 已存在 | 继续；改动前按 `workflow-verification` 采基线 |
| 缺失 | 暂停，等待用户明确选择“初始化”或“跳过” |
| 用户选择初始化 | 运行 `/verify-config`，确认配置已生成后继续 |
| 用户选择跳过 | 只运行内置检查，并在最终报告注明 |

任务批准、内置检查或 `event start` 都不能代替配置选择。Standard / Runtime 路径须在任何 `event start` 之前记录已取得的选择：已有 `tasks.md` 时立即写入，否则创建后立即写入。

```bash
python <本 skill 目录>/scripts/workflow_control.py <tasks.md> verify-config-decision --choice initialize|skip --write
```

没有 `tasks.md` 的 Native Delivery 在最终报告中记录用户选择。步骤 3 只负责持久化已有选择，不重新询问或推断。

## 轻量任务执行

进入此路径前，读取 [交付指南的轻量交付流程](reference/delivery-guide.md#轻量交付fast-path-兼容)。

1. 完成步骤 1.5 的配置选择，加载步骤 4 的规范，有配置时在改动前采基线。
2. 实现并运行机器验证；超出轻量范围时转标准流程。
3. 涉及 UI 时完成视觉和浏览器验证；修复后重跑受影响的机器检查。
4. 调用一次 `workflow-code-review`：兼容路径为 `lightweight`，新的 Native Delivery 为 `standard`，均使用 `scope: integration`。
5. 按交付指南完成知识影响检查、本地提交、交付门和最终报告。复审遵循 Review Skill 的范围与 10 轮上限，禁止启动第二次全量首审。

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

创建 `tasks.md` 后，展示任务及依赖并等待用户确认；获批后自主执行，不再逐任务等待。由 `workflow-quick-design` 自动 pipeline 调用时，已确认的 spec 视为任务预授权。

提交任务确认前，先记录步骤 1.5 已取得的配置选择。实现期间冻结既有检查、`ignore_paths` 和基线；新增检查入口须按 `workflow-verification` 的受限追加规则处理。

### 步骤 4：加载编码规范

写代码前加载下列适用规范。委派时把规范要点交给 Agent，或要求其先读取对应 Skill。

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

编码或测试前，按 [执行准备](reference/execution-setup.md#overlay-规范发现) 验证扩展规范。通过当前 Skill 的真实路径定位受信框架根，只加载校验成功且匹配目标文件的规范。

### 步骤 5：委派执行

任务计划获批后，主会话负责编排，由 Agent 完成实现、测试和任务级机器验证。派发前读取 [执行准备](reference/execution-setup.md) 和 [下放执行指南](reference/delegated-execution-guide.md)。

- 默认 Native Delivery；仅显式 Runtime 需求（execution-mode/audit/cross-host）才路由 `runtime-run`，`strict`、并行与恢复不再自动升级。
- 单任务或串行依赖按任务顺序直接执行，不要求子 Agent、波次计算或宿主探测；并行分支、非线性依赖或恢复场景按需使用控制器的 `waves` / `dispatchable`。
- 每项产物通过测试和机器检查后才合并。失败或冲突标为 `需人工`，依赖它的任务标为 `阻塞`，其他独立任务继续。
- owner / implementer 禁止在 task 内启动 LLM Review；全部可合并任务完成后进行一次最终审核。
- 完整 Runtime Run 在派发前完成 `init-run` 和必需能力检查；Native Delivery 使用带内容主体的独立 v2 验证报告，不初始化 Run。

### 步骤 6：验证与交付

任务均进入 `完成` / `需人工` / `阻塞` 后，读取并执行 [交付指南](reference/delivery-guide.md#标准交付)：

1. 汇总实现、测试、失败与合并结果。
2. 对合并结果运行机器验证；涉及 UI 时再做视觉和浏览器验证。
3. 对全部变更做一次最终审核。Native Delivery 按任务实际档位出 v2 集成 Review（`standard`；任务声明 `strict` 时为 `strict` 并要求独立 Judge 与三项独立性声明）；完整 Runtime Run 使用 `strict run`。修复后重验并定向复审，最多十轮，禁止启动第二次全量首审。
4. 完成交付前沉淀检查、知识同步和任务状态一致性检查，再归档 Change。
5. 提交本次代码与归档产物，按路径运行交付门。失败则回到对应步骤处理。
6. 使用固定格式报告结果，列出待用户处理的 `需人工` / `阻塞` 项。

## Scoped Delivery（显式例外）

存在与任务无关的预存改动时，Native Delivery 可使用 Scoped Delivery。必须在改动前冻结范围并采集残留快照；采基线前读取 [Scoped Delivery](reference/delivery-guide.md#scoped-delivery显式例外)。完整 Runtime Run 仍使用干净工作区。

## 统一交付证据格式

输出最终报告前读取 [统一交付证据格式](reference/delivery-guide.md#统一交付证据格式)。保留遥测字段，列出提交、测试、Review、Verify、知识影响和未验证项。交付门结果逐字引用 `check_delivery.py` 的原始输出；失败或未运行时报告实际状态。

## 交付前沉淀检查

所有路径均按 [交付前沉淀检查](reference/delivery-guide.md#交付前沉淀检查)，逐条记录架构决策、放弃方案、新增约束是否需要沉淀，以及具体写入位置。

## 执行约束

- 轻量任务外，先取得规格和任务批准，再委派执行。Quick Design 自动 pipeline 的预授权按步骤 3 处理。
- 有依赖的任务按顺序执行；依赖缺失时先保守串行或询问，不能放入同一波并行。
- 测试与实现同批交付（Fast-Path 除外），接口层与核心逻辑覆盖关键路径。
- 进度按实际状态报告：“已查看”表示读取核对，“进行中”表示已派发或改码，“已完成”表示已落地、合并并核对。

## 用户跳过 spec 时

必须生成简化版 `proposal.md`（标 `状态: Quick Draft`）。**禁止无 Proposal 修改中等及以上代码。** 该路径交付前同样受步骤 6 约束。

## 恢复中断

中断后先收集已合并任务 ID，再运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> recover --merged <任务 ID...>` 生成恢复计划；按计划核对 worktree 和质量门，详见 [reference/delegated-execution-guide.md](reference/delegated-execution-guide.md) 的「恢复中断」。**恢复路径不豁免步骤 6 的交付前沉淀检查。**

## 与其他 skill 的关系

本 skill 是所有代码修改的统一入口。`workflow-code-review` 是 Native Delivery 与完整 Runtime Run 共用的分级评审门；`workflow-test-generation` 内嵌在每个 task 的执行流程中。设计阶段由 `workflow-requirements-clarification` / `workflow-system-design` / `workflow-quick-design` 承担。
