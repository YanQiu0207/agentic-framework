# Design: 轻量默认流程与可选 Runtime

**作者**：Codex
**日期**：2026-10-03
**状态**：Draft

本文件描述待实施方案。当前代码仍按 proposal.md §1.2 工作。章节沿用项目设计模板的 4–9 编号。

## 4. 设计方案

### 4.1 方案概览

默认流程只有一条：明确需求与验收 → 实现与测试 → 机器验证 → 风险分级审查 → 交付检查。

需求复杂度决定是否需要 proposal、design 和 tasks；风险决定审查强度；并行和恢复决定是否使用执行辅助能力；明确的执行审计要求决定是否启用 Runtime。这四个判断各自负责一个问题。

| 层次 | 保留内容 | 启用条件 |
| --- | --- | --- |
| 默认核心 | 适用规范、实现、测试、Verify、最终 Review、知识影响与交付检查 | 所有代码任务；轻量任务保留现有文档豁免 |
| 任务辅助 | tasks、DAG、工作区隔离、委派、失败阻塞、恢复规划 | 有任务依赖、可并行工作或恢复需求 |
| 完整 Runtime | 输入冻结、Envelope、Manifest、Journal、能力探测、Trust Gate | 明确选择完整执行证据，且当前宿主/VCS 支持 |

任务辅助能力不需要一次全部启用。单任务或串行链允许主 Agent 直接实现；多 Agent 只用于有价值的并行或职责分离。strict 的 Reviewer/Judge 独立要求不因此取消。

完整 Runtime 暂时保持 Git-only。移除“为了启用 Runtime 而引入 Git”的初始化建议。

### 4.2 模块与接口

#### 4.2.1 路由：分开审查强度和证据要求

调整 `workflow_control.py` 的 `select_execution_route`。新增明确的 `execution_mode: native|runtime`，没有指定时为 native。项目强制策略可要求 runtime，但普通风险或复杂度推断不能产生该要求。

| 输入 | 新行为 |
| --- | --- |
| strict 风险 | Native + strict Review |
| 并行 Git Worktree | Native + 隔离与集成检查 |
| 中断恢复 | 依据 tasks、工作区和验证记录恢复 Native |
| “需要审计”但未说明要求 | 先确定所需证据；不自动等同于完整 Runtime |
| 明确选择完整 Runtime，且为受支持的 Git 环境 | runtime-run |
| 项目策略要求 Runtime，用户选择 Native | 报告冲突，不自动放宽项目策略 |
| 明确选择 Runtime，但为 SVN 或必需能力缺失 | 报告 unsupported；由用户决定改用较低保证的 Native 或更换环境 |

CLI 计划增加 `--execution-mode native|runtime`。默认值只在新任务开始时确定；存在 Run Context 的恢复任务保持原路径。

项目强制策略由编排方读取已有 `AGENTS.md` 或用户明确提供的项目约束后，作为显式 `audit_required` 输入（CLI 沿用 `--audit-required`）传给路由，并说明要求的来源。本期不增加策略文件或自动解析散文的配置层，也不从 governance Profile 名称推断 Runtime。该要求与 `execution_mode=native` 冲突时拒绝路由；能力不支持时也不能由一次模式选择覆盖强制策略，须先明确变更其来源约束。

旧 `--parallel-worktree-write`、`--long-task-recovery` 在一个兼容版本内仍接受，但只表示执行需求并提示新语义。旧 `--audit-required`、`--cross-host-capability-verification` 保留为明确 Runtime 需求的兼容输入，不能静默忽略；新调用者使用显式模式。旧返回字段先保留，说明变化后再版本化移除。

#### 4.2.2 Native 审查：严格审查也可独立执行

保留现有三个档位、五维 strict、Critic、独立 Judge、P0/P1 阻断与十轮定向复审。解除 Tooling strict 必须具有 Run Context 的限制。

- Native 使用 `scope: integration`，任务级 Production Review 仍为 `scope: task`。
- strict 报告由未参与实现的 Judge 生成，记录 `implementer_actor`、`judge_actor` 与流程分离依据。
- 实现者只能原样保存审查产物；不允许自行填充裁决。
- Profile 继续决定最低档位与批准门。Tooling 默认一次集成 Review；Production 保留逐任务守卫和 strict 集成 Review。

为独立 Native Review 增加版本化报告合同，优先复用现有裁决字段；不套用 Runtime Envelope。现有六字段 standard/lightweight 报告保留旧读路径，不据其推断独立 Judge 或新内容绑定证据。

当前 `check_native_delivery_review` 已接受 Production 的 strict 六字段报告（change 2043），Tooling 仍固定 standard。本次新增 Tooling strict，并为新流程的 strict 报告补充独立性与内容绑定校验；保留 Production 既有审查流程。新的 Native Verdict 使用 v2 Schema，允许准确描述实际审查档位；只有实际存在独立声明的 strict 才列出对应流程检查，仍不声称强身份隔离或语义必然正确。

`check_delivery.py` 当前用 `NATIVE_DELIVERY_REVIEW_FIELDS` 限制六字段报告，并在 Verify 结果中递归检查 `NATIVE_DELIVERY_FORBIDDEN_CLAIM_FIELDS`。实施时按产物类型、版本和审查档位分派白名单：仅 v2 strict Review 的指定字段允许 `implementer_actor`、`judge_actor`、`independence_basis`，不全局删除禁止项，也不允许任意嵌套豁免。Verify 的结果字段与递归禁止集保持，v1 读路径保持原合同；v2 Verdict 只由交付门产生已核验的流程声明，不能将输入中的 `strict_independent_review: true` 当作证明。Runtime/Trust 声明仍不属于 Native 保证。

#### 4.2.3 最小证据与内容变化

Native 默认保留已有 Verify、Review 和最终 Verdict。具有多个任务时继续使用 tasks.md。无需额外 Manifest、Journal、Capability 文件或运行目录树。

为防止使用旧报告，在 Verify 中复用或补充一个共同的 `subject_id`：由版本库身份、检查基准、参与验证的项目内容及配置摘要计算。Review 与最终门引用同一标识。它只表示“检查的是哪份内容”，不记录任务事件、不重建 Runtime。

| v2 产物 | 必填内容与生成责任 |
| --- | --- |
| standalone Verify | 顶层 `schema_version: 2`、`subject_id`；Verify 程序计算，检查前后核对输入一致后写出 |
| Native Review | 顶层 `schema_version: 2`、`subject_id`；审查方针对对应内容生成，不由实现者补填 |
| Native Verdict | 顶层 `schema_version: 2`、`subject_id`；交付门重算并验证 `review.subject_id == verify.subject_id == 当前 subject_id` 后生成 |

v2 Verify 顶层白名单新增版本与内容标识，不放宽 `results`/`spec_drift` 的字段或独立性禁止集。缺字段、未知版本、内容不一致或覆盖范围无法确定时，新交付门拒绝通过。三份产物分别校验 Schema，不能仅凭其中一份声明与当前内容相同便复用其余报告。

规则与限制：

- 内容摘要覆盖测试实际依赖的项目输入，不只覆盖提交路径；未跟踪但参与构建的文件也必须处理。生成目录和报告目录使用明确的分类，不能通过通用 ignore 隐藏代码变化。
- 文件内容、路径、类型及影响行为的属性进入摘要。测试期间相关输入改变时，这次结果无效。
- 更新、合并或用户编辑导致 subject 改变后，重跑受影响检查并重新取得针对当前内容的 Review。
- 同一主体的 finding 修复继续定向复审；导入新的上游变更导致原审查范围不再成立时，建立新的集成审查主体，重新定义范围，原报告保留。这是需要同步修改 Review 规则的显式行为变化，不用改轮次绕过十轮限制。
- 老报告没有 subject 时只能按旧合同展示历史结果；新完成门要求新证据，不给旧报告补造摘要。

实现中先定义一个公共内容标识计算函数，Verify、Review 门和交付门共同使用；不让 Agent 手算摘要。默认保守覆盖项目工作区，明确排除 VCS 元数据、生成和报告目录；不建设测试依赖自动推导系统。排除项若包含构建输入，必须显式纳入覆盖；项目外输入无法确定时报告限制。具体摘要算法与路径分类在实施任务中以真实 Git/SVN fixtures 确定。

#### 4.2.4 VCS：只抽取当前有两个实现的操作

在 `scripts/` 内建立小型 VCS 模块，GitAdapter 与 SvnAdapter 共用接口。先收拢当前散落在 verify、workspace_residue、workflow_control、check_delivery 中的根目录探测、状态和改动识别，不重构 Runtime 的全部 Git 操作。

对调用者暴露四项职责：

| 接口职责 | 结果与约束 |
| --- | --- |
| inspect_workspace | VCS、工作区根、仓库身份、冲突、混合版本、外部依赖及能力 |
| capture_subject | 固定基准与内容标识，标明覆盖范围和不可验证项 |
| collect_changes | 新增/删除/修改/重命名及属性变化，不依赖本地化终端列宽 |
| verify_delivery | 按 Git commit 或 SVN revision 核验正式交付范围与内容 |

这些默认只读。SVN update、commit 由明确的工作流步骤调用，不能藏在状态查询中。工具错误返回结构化原因，不能转成空变更。

SVN 使用 XML 输出解析状态、info、log/diff 摘要；仓库身份采用 UUID + repository-relative URL，单独 revision 不足以识别项目。工作副本根的一个 revision 不能代表全部节点，混合版本、switched 子树和稀疏检出需要检测。

第一阶段 SVN 支持普通、完整、单分支工作副本与串行执行。遇到无法完整确定的 switched/sparse/externals 输入，不给出完整项目通过结论；明确报告限制并允许人工继续一般开发。后续能力须以场景测试增加，不能默默忽略 external。

#### 4.2.5 恢复与并发

- tasks.md 继续是任务执行状态的唯一可写来源。恢复时核对实际集成结果、文件和验证报告，不依赖聊天中的完成声明。
- Native 恢复不创建 Run，也不伪造历史事件。不能证明是否已完成的步骤标为需核对，必要时重跑无副作用验证。
- Git 并行任务使用独立 Worktree；主编排方串行集成，并在最终集成内容上验证与审查。
- SVN 第一阶段串行写工作副本，允许并行只读调研/审查。不将 `merge_success` 解释为 SVN 已提交；它只代表任务结果已纳入本地集成内容。该语义需在控制器、Skill 和测试中同步定义。
- 用户进程不受框架文件锁控制，所有交付前检查仍核对内容是否变化；检测到外部改动即使持有锁也不能沿用旧结果。

### 4.3 核心流程

#### 4.3.1 Git 日常开发

1. 保留现有需求、设计、任务批准和 Verify 配置选择规则。
2. 根据任务选择直接执行、DAG 或 Worktree，不据此创建 Runtime。
3. 实现、测试、机器验证、最终风险分级 Review。
4. 完成知识影响与需要的归档，执行本地提交规则。
5. 在当前内容上运行 Native 交付门，准确列出已验证和未验证事项。

默认 standard，现有低风险兼容 lightweight 继续可用；不把 lightweight 改名或扩展为高风险例外。

#### 4.3.2 SVN 原生开发

1. 识别工作副本并检查预存修改，保护用户文件。干净副本可更新后开始；有修改时先展示影响，不能自动 revert 或用更新覆盖未知状态。
2. 完成必要更新后，记录仓库身份、节点基准与检查范围。能明确验证完整状态时才开始框架托管交付。
3. 串行开发、测试和 Review。使用 SVN 工作副本作为唯一开发内容，不创建 Git 镜像。
4. 提交前查询上游。相关上游内容有变化时更新、解决冲突，并按新主体重新验证。不能把 `svn status -u` 的一次结果当作之后不会再变化的保证。
5. 没有提交授权时输出“本地已验证，待 SVN 提交”。这是一种完成报告状态，不是正式交付 PASS，也不要求提交作为本地验证的前提。
6. 有授权时展示明确范围与差异，执行 `svn commit`，记录实际返回 revision；失败保留工作副本。超时导致结果不明时先核对服务器日志与实际内容，不盲目重提、不推断成功。
7. 从确切 revision 获取隔离内容核验并执行必要测试。SVN 可能接纳别人在不同文件上的提交，文本无冲突不代表验证过该组合；正式交付声明只绑定确认过的 revision。

“本地已验证待提交”和“已提交版本已验证”写入现有最终结果，不新增任务状态机或常驻服务。SVN 的待提交代码是预期改动，不能被当前 Git clean 条件一概当成失败。

Native Verdict v2 的 `verdict` 明确区分：`native-delivery-pass`（Git 正式交付）、`svn-pending-commit`（本地验证通过，未正式交付）、`svn-revision-verified`（指定 SVN revision 已核验）。后两项分别要求工作副本内容标识，或仓库 UUID、repository-relative URL、revision 及该版本内容标识；不填充 `git_clean`。正式交付判断显式匹配成功类型，不能把“生成了 Verdict”当作 PASS。提交后隔离版本若改变 subject，必须取得对应 Verify/Review 后才能输出 `svn-revision-verified`，旧报告只保留为提交前证据。

提交后才出现验证失败时如实报告“已提交、版本验证失败”；不能自动回滚共享版本或伪称提交未发生。是否修复或回退由后续明确任务决定。

文件属性、二进制、空目录、关键字/EOL 转换分别建立 fixture；内容核验须区分工作副本表示与版本库存储表示。无法可靠匹配时返回不确定，而非仅凭 revision 存在宣告通过。

#### 4.3.3 初始化与已有项目

- 沿用 project-init 已有纯 SVN 初始化能力，先探测 VCS，已有 SVN 推荐原生 SVN；本期调整默认推荐与探测，不重建其逐路径 `svn add`、不自动 commit 的行为，也不主动提供自动双向同步。
- Git/SVN 同时存在时展示识别结果并确认开发后端，不继续无条件 Git 优先。旧 `.git`、`.svn` 均保留，任何移除另行授权。
- 已配置桥接或团队镜像的项目保留现状，标注正式提交后端；不据 `.git` 存在推断桥接正确。
- 本期不新增运行模式配置体系。任务开始时决定 execution_mode；已有项目硬性审计要求通过显式输入传给路由。
- Profile 继续独立选择，修正初始化中的旧 OPSX 描述；不把 Production 等同于 Runtime。

#### 4.3.4 完整 Runtime

显式启用后继续使用现有 Git Run 输入、日志、宿主探测、严格 Judge 与 Trust Gate。已有 Run 不换路径、不删除日志、不重采历史输入。Native 中途确实需要 Runtime 时，从明确的新基准建立新 Run，记录承接关系，不补造此前执行的审计证据。

### 4.4 收益与代价

收益是默认流程少初始化、少协议文件、少上下文；高风险审查保持强度；SVN 不再为了日常开发引入第二套版本管理。

代价是 Native 不提供完整事件回放或跨产物审计；内容变化后的验证仍有成本；SVN 提交后的测试不能阻止失败版本先进入共享仓库。需要严格“验证后才进入目标分支”时，应由团队的集成分支/提交队列解决，本期不自建。

## 5. 备选方案

| 方案 | 判断 |
| --- | --- |
| 保持所有现有 Runtime 自动升级条件 | 能复用当前实现，但默认成本和 SVN 绕路问题没有解决 |
| 彻底删除 Runtime | 当前不选；破坏已有证据与明确审计用户，缺少使用数据支撑 |
| 将 Runtime 全量改造成 Git/SVN 通用平台 | 当前不选；投入大于日常流程需求，推迟原生 SVN 可用性 |
| 只改 Skill 文案，保留机器门限制 | 不可行；Native strict 仍被代码拒绝，形成新的规则冲突 |
| 默认 Native，按需辅助，显式 Runtime | 本方案；先用真实任务衡量收益，再决定是否进一步退役 Runtime |

## 6. 业界调研与取舍

SVN 的标准协作依靠 update、冲突处理与 commit；git-svn 是个人客户端桥接，SubGit 是集中镜像基础设施。它们表明版本同步可以交给成熟工具，但没有要求开发框架同时实现一套桥接。本方案采用原生 SVN 主路径，桥接留作已有环境能力。

Git/SVN 都需要验证实际集成内容。对 SVN 的混合版本和 externals 不作“一个 revision 就代表全部工作目录”的假设。行业资料支持这些版本控制事实；默认流程分层和 Runtime 收缩是本项目设计判断，不声称是行业统一标准。

## 7. 实施与测试计划

### 7.1 分阶段实施

| 阶段 | 主要修改 | 独立验收点 |
| --- | --- | --- |
| P0：固定回归场景 | route、Native Review/Verify、已有 Runtime/Production 测试与触发用例，含 `test_delivery_route_fixture_runner.py`、`test_downgrade_equivalence.py` | 先记录旧行为及预期变化，不先放宽路由 |
| P1：Native 支持严格审查 | check_delivery、独立报告/Native Verdict v2、内容标识、Profile 守卫 | strict Native 证据完整可通过，缺独立性或内容错配拒绝；旧 v1 可读但不冒充新证据 |
| P2：收窄 Runtime 路由 | workflow_control、三个核心 Skill 及 reference、恢复/评测 | strict/并行/恢复可走 Native；显式 Runtime 仍受完整门保护；串行可直接执行 |
| P3：SVN 原生串行闭环 | VCS 模块、verify、workspace_residue、check_delivery、validate_change、project-init | 真实 SVN fixtures 证明本地待提交和 revision 验证；Git 回归不变 |
| P4：文档与使用验证 | README、长期知识、安装刷新、真实任务评测 | 新旧入口一致，已有项目升级可恢复，记录成本及返工结果 |

依赖顺序 P0 → P1 → P2 → P3 → P4。P1、P2 的规则和实现作为同一可发布批次，避免路由已放开而交付门尚不支持。P3 可独立发布，不等待 SVN Runtime。文件清单由每阶段实施计划冻结，不在本设计中假装已完成任务。

### 7.2 必测场景

- 路由矩阵：三个审查档位 × 是否并行/恢复 × 显式 Runtime × Git/SVN；策略冲突和未知能力不能被静默忽略。
- 严格 Native：实现者代写、Judge 与实现者相同、报告缺字段、P0/P1 非零、旧报告错配和内容变化均拒绝。
- `test_check_delivery.py` 覆盖 v2 strict Review 合法独立性字段、v1/Verify 同名字段与嵌套字段仍拒绝；v2 Verify/Review/Verdict 的 subject 缺失、交叉错配和交付时变化均拒绝。路由 fixture 与 downgrade equivalence 测试同步更新预期，不删除旧 Runtime 保护场景。
- 保留 Production 下限、逐任务 Review 和审批门；已有 Runtime Journal/Manifest/Trust Gate 回归通过。
- Git 并行任务失败、合并冲突、中断后重跑、上游更新：任务状态与实际内容一致，无重复外部副作用。
- 本地 `svnadmin` 测试仓库与两个独立工作副本：另一开发者同文件冲突、不同文件更新、提交竞态、混合版本、属性修改、二进制与删除重命名。
- SVN 无提交授权、网络不可达、提交响应丢失、无效 revision、错误 UUID/URL、提交后验证失败；均不得误报正式交付。
- SVN 本地通过只能得到 `svn-pending-commit`；确切 revision 及对应证据通过才得到 `svn-revision-verified`；正式交付判定拒绝待提交状态，三类成功结果按 v2 各自必填证据检查。
- switched、稀疏和 externals：支持范围外必须给出明确限制，不能在缺输入时报告完整验证。
- 初始化已有双 VCS、Git 上级仓库包住 SVN 工作副本、预存未跟踪文件、旧混合模式：不自动转换，不破坏原内容。
- Markdown/JSON 固定字段、引用图和 Skill 触发用例同步检查，避免靠文本简化掩盖行为变化。

### 7.3 效果验证

选择小修复、普通功能、strict 修改、并行 Git 任务和 SVN 串行任务，记录必要命令数、产物数、人工停顿、耗时、token（环境可获取时）和实际返工。默认路径必须零 Runtime 初始化/探测；质量由测试、Review 与后续返工共同判断，不以协议文件减少直接声称质量提升。

暂不承诺固定时间或 token 降幅。保留现有 Git Runtime 对照；用实际审计需求和任务样本决定后续保留、冻结或退役，而非设一个缺乏数据的使用率阈值。

## 8. 兼容、可观测性与运维

- Runtime v1 Schema 和既有 Run 保持可读、可校验，保持原 Git 绑定规则；本次不迁移为通用 revision。
- 新 Native 报告及 Verdict 独立版本化，校验器显式分派 v1/v2；不修改旧字段语义来伪装兼容。旧产物只按旧保证展示，新流程缺新证据时重验。
- tasks 的现有状态集合保持；待提交/已提交属于最终结果，不作为重复任务状态存储。
- 初始化结果与交付结果说明 VCS、审查档位、所用辅助能力、Runtime 是否显式启用、已验证内容和实际提交位置。
- 发布时说明旧 CLI flag 的语义变化；安装器刷新后的已有任务按其记录模式恢复，不从新版默认值猜测。
- 回退代码时不能让旧校验器误读新报告；新格式版本不支持时明确报错。为已有 Run 保留旧入口直到其完成，不删除证据。
- 本阶段只产出设计草案。用户接受方案后，再生成可执行 tasks.md 与对应规格 Delta，进入代码实施。

## 9. 参考资料（design）

- [SVN 基本工作流程](https://svnbook.red-bean.com/en/1.8/svn.tour.cycle.html)：更新、合并冲突与提交。
- [SVN 工作副本与版本](https://svnbook.red-bean.com/en/1.8/svn.basic.in-action.html)：仓库版本与工作副本节点状态。
- [SVN externals](https://svnbook.red-bean.com/en/1.8/svn.advanced.externals.html)：外部依赖的独立版本语义。
- [Git as a Client](https://git-scm.com/book/en/v2/Git-and-Other-Systems-Git-as-a-Client)：git-svn 协作及提交后的集成状态。
- [git-svn](https://git-scm.com/docs/git-svn)：桥接与线性历史限制。
- [SubGit 文档](https://subgit.com/documentation/)：团队级双向镜像。

资料检索日期：2026-10-03。方案依赖的本项目实现清单见 proposal.md §1.2 与 §5。
