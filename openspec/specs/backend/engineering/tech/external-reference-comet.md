# 外部参考：Comet 流程编排状态机及与当前框架的对照

> 本文档是 `rpamis/comet` 的外部项目研究与迁移对照分析，不是当前框架的实现规格。项目自述（README）、随包 SKILL.md、可读源码确认、推断与缺失证据分别标注；所有借鉴与迁移项在进入设计或实现前，仍须回到当前框架的代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 项目 | `rpamis/comet` |
| 定位 | AI 编码的流程编排状态机（Agent Skill Harness）：Native/Classic 双工作流 |
| 代码仓库 | <https://github.com/rpamis/comet> |
| 代码分析基准 | master `899d1fb05cd4`（2026-09-22） |
| 版本与许可 | v0.4.0 stable，MIT，Node.js（22.16+/24+），~3.1k stars |
| 核实范围 | README、`assets/skills/*/SKILL.md`（comet/comet-any/comet-classic/comet-native）、`comet-resume-probe.mjs` 可读源码、`eval/README.md`、`docs/architecture/ARCHITECTURE.md`、`app/commands/` 源码目录 |
| 核实边界 | guard/state/hook 脚本为 esbuild 打包产物（单文件 200–700 KB），内部校验逻辑未逐行反读；未本地安装实测；`/comet-any` 扩展管线未实跑 |
| 公共知识库条目 | `E:/work/shared-knowledge-base/domains/agentic-engineering/comet-workflow-harness.md`（跨项目通用版） |

## 一句话定性

Comet 把「想法 → 验证 → 归档」固化成状态机：阶段推进不依赖 Agent 口头声称完成（*"phase exits do not rely on an agent saying 'done'"*），由脚本门禁强制；状态外置到每个 change 的 `.comet.yaml`，中断可确定性续跑；自评闭环（Rubric + Pass@k + 独立 LLM Judge）驱动 Skill 人工迭代。与当前框架属**同类竞品**（同为「状态机 + 阶段门禁 + 评测」路线）。

## 双工作流的设计动机（README 原文）

分界线是**模型能力**，不是任务大小：

- Native：*"for strong models that can plan and verify autonomously"*——plan/implement/test/review 由模型自选，Comet 只管状态检查、验收、可恢复归档；
- Classic：*"for scenarios that benefit from a complete phased methodology and stronger constraints"*——OpenSpec + Superpowers 合成五阶段（Open → Design → Build → Verify → Archive）；
- 不合流的原因：①代价不对称（自报评测：Native 比 Classic 总 token 少 76.8%、轮次少 57.4%）；②作者拒绝「猜」：`/comet` 只按 `.comet/config.yaml` 确定性转发，*"does not guess from task size"*；
- *"Native and Classic are not lightweight and heavyweight tiers, and neither upgrades into the other"*——平行独立，仅共享 config/状态/Dashboard/Eval 底座。

## 机制要点（SKILL.md + resume-probe 源码确认）

**可恢复**：`.comet.yaml` 记 `workflow`/`phase`/`verifyResult`/`buildPause`/`archived`；未知字段判 invalid；归档区目录名 `YYYY-MM-DD-<name>` 可解析，「已归档但交付未完成」会捞回待恢复列表。恢复判定是四选一确定性分类器（`auto_resume | ask_user | out_of_scope | none` + confidence + reason + evidence），素材三路：磁盘状态（phase→命令硬编码映射）、`git status --short`（脏工作区一律 ask_user：「uncommitted worktree changes require attribution」）、话语关键词表（恢复词/疑问词/拒绝词）。策略偏保守：多 active change、决策点一律 ask_user；只有 `auto_resume` 才自动进入。

**门禁**：门禁点在 phase 推进——过脚本校验（任务完成、状态字段齐、验证证据在）才写 state 并返回下一条 `continuation`；Native 的 Agent 「works only on the phase specified by Runtime」。口头越级三重堵死：SKILL.md 明文对话不得授权改 phase；`.comet` 目录 Hook 保护不可豁免（`hook.allow_paths` 默认空）；坏 state 报错不猜（*"Report malformed state rather than guessing a phase"*）。并发安全：Native 命令带 `--expected-state-version` / `--expected-action` 乐观锁。

**评测**：pytest + Rubric（通用 7 维 / 工作流 9 维 / 生成包 11 维）+ LLM-as-judge（Judge 独立模型独立凭据 `BENCH_JUDGE_*`，不继承主任务配置）；被测 Agent 跑在 Docker（预装 Claude Code/Codex/Qoder/CodeBuddy），可接 LangSmith/LangFuse。**是评测驱动的人工迭代，非自进化**——无「eval 结果自动回写 Skill」闭环。

**扩展模型**（comet-any/SKILL.md + ARCHITECTURE.md）：三层扩展面，编译为 `workflow-protocol.json`（runtime source of truth，Factory/Eval/review/readiness 共用）：
1. **Required Skill Call**（最轻）：节点绑「必调依赖」，官方例：execute 必调 `elementui`、review 必调 `whitebox-code-standard`；
2. **Overlay**：`comet-five-phase-overlay` 保五阶段控制流与 `.comet.yaml` 语义；节点分权——control 节点（open/execute/verify/archive）不可覆写，producer 节点（design/plan）可覆但须满足原 Output Schema，handoff/guardrail 可增强；
3. **Workflow Kernel**：自建状态模型 + Output Schema + Guardrail；Native 本身即 kernel 成品示范。

扩展物同样过门禁：绑定/Schema 标强制级别（guarded/handoff-guarded/evidence-only/advisory）；*"failed eval, skipped eval, or stale-hash evidence cannot become ready"*；publish 须人工批准、install 先 preview 确认零写入。

## 与当前框架的结构对照

| 能力 | 当前框架 | Comet | 差异要点 |
| --- | --- | --- | --- |
| 流程骨架 | `workflow-*` 编排与框架脚本 | Comet Runtime 与阶段门禁 | 同一 Change 应只有一个流程控制者；规范、检查器和适配后的 producer 可以组合，不等于两套编排同时接管 |
| 交付门禁 | `check_delivery.py`、`verify.py` 等 | Classic guard、Native Runtime 与独立 Verifier | 存在职责重叠，但不能据此判定检查项完全等价或完全缺失；需逐项对照证据合同 |
| 知识体系 | `openspec/` + Delta、Issues 与知识影响检查 | Classic 使用 OpenSpec；Native 使用正式 Specs，并有 Project Memory 接口 | 不能称 Comet「无知识体系」；旧目录、Delta 合并和知识影响检查是否可保留，仍需明确映射与验收，见下文来源 |
| Skill 评测 | 无机器验收（skill 更新靠人工） | `comet eval`：Rubric + Pass@k + 独立 Judge | Comet 有、框架无 |
| 扩展门禁 | 无（skill 可任意改） | 扩展物强制过 eval/readiness 才可 publish | Comet 有、框架无 |

## 迁移对照（当前框架 27 个 skills → Comet）

> 2026-09-27 补核：当前框架基准为 `7441ecc96a2f6b71f3df6b7ba0e73530ce6a6c11`，Comet 仍固定为 `899d1fb05cd4`，不代表本机安装版本。扫描了全部 13 个 `std-*`、`bp-*` 技能的 28 个文件，并对照工作流及引用资料。下述依赖为静态确认，迁移取舍为建议；未做迁移后的端到端或效果对比实验。

不能用「未命中 `openspec/`」推导「零绑定」，也不能用「阶段职责相同」推导「能力等价」。依赖检查必须覆盖技能调用、Agent、脚本、参考文件、隐含工件契约及自动后续路由。

### 最终取舍建议

以下是基于本次静态核查的迁移决策建议，不是效果已优于 Comet 的实验结论。「迁移」包括必要的接线适配，不等于原样复制或替换 Comet 控制节点。

| 分类 | 技能清单 | 最终决策 |
| --- | --- | --- |
| 建议迁移：规范底座（13 个） | `std-cpp`、`std-go`、`std-python`、`std-react`；全部 9 个 `bp-*` | 保留长期积累的规范与参考资料。`std-react` 必须改工件接线；`bp-skill-authoring` 修来源链接；其余按下文闭包整目录迁移 |
| 建议迁移：辅助能力（2 个） | `frontend-playwright-verification`、`self-refinement` | 前者保留真实浏览器验收，后者保留经用户确认的经验沉淀；适配证据位置、写入目标和命令入口，不接管状态推进 |
| 建议拆分后迁移（4 个） | `workflow-frontend-design`、`workflow-code-review`、`workflow-test-generation`、`troubleshooting` | 分别保留 UI 设计、独立审查、测试策略和故障排查的核心方法。去掉旧目录、旧框架发现逻辑、交付合同及自动后续路由；所需 Agent 和参考资料一起处理。优先前端设计与 Review |
| 按需迁移，首批不做（2 个） | `workflow-verification`、`open-code-review` | 前者仅在确需历史基线／配置冻结时迁检查器，不迁 Verify 编排；后者仅在继续使用 `ocr` CLI 时保留，并改修复路由。没有实际需求就不迁 |
| 不迁移原技能（6 个） | `workflow-requirements-clarification`、`workflow-system-design`、`workflow-quick-design`、`workflow-code-generation`、`project-init`、`project-knowledge` | 使用 Comet 对应流程和工件管理；有用的提问清单或设计模板可按需抽取，但不安装第二套入口。不迁 `project-knowledge` 不等于丢弃已有知识，存量知识另行备份和映射 |

合计 27 个：建议迁移或适配保留 19 个，按需保留 2 个，不迁原技能 6 个。这不是要求一次安装 19 个：先验证规范底座的单个切片，再接前端、Review 等实际需要的组合。默认不替换 Comet 的设计 producer；只有对照实验确认旧设计方法更符合使用目标时，再考虑合法的 producer override。

### 依赖闭包与迁移处置

以下两组表加上后文 8 个 `workflow-*`，覆盖当前 27 个技能；不再沿用原文不一致的「零改动，12 个」分类。

| 技能 | 静态确认的依赖或约束 | 迁移处置 |
| --- | --- | --- |
| `std-cpp`、`std-go`、`std-python` | 各自的 `reference/full-standards.md`；未发现对不迁移工作流的调用 | 整目录迁移，不只复制 `SKILL.md` |
| `std-react` | 活跃 Change 的 proposal、design、Delta，以及必需的 `ui-spec.md`；缺 UI 规格回设计流程；实现后加载 `bp-frontend-taste`、`frontend-playwright-verification` | **必须适配接线**：保留 UI 规格生产者，或显式映射到 Comet 的正式需求和已确认设计；不能留下不存在的前置工件 |
| `bp-architecture-design` | `bp-component-design`、`bp-distributed-systems` | 引用的技能一起迁移 |
| `bp-coding-best-practices` | `bp-component-design`、本目录 `reference/` | 技能与参考资料一起迁移 |
| `bp-component-design` | `bp-distributed-systems`、`bp-performance-optimization` | 引用的技能一起迁移 |
| `bp-distributed-systems`、`bp-frontend-layout`、`bp-frontend-taste` | 本次未发现指向不迁移技能的引用 | 可保留规范正文；按需要调用，不据此宣称已有强制门禁 |
| `bp-performance-optimization`、`bp-cli-tool-design` | 本目录 `reference/` | 整目录迁移 |
| `bp-skill-authoring` | `reference/full-best-practices.md`；正文存在 `/docs/en/...` 和 `/docs/images/...` 站点相对链接 | 保留参考正文；核实原站后补完整 URL 或本地资源，不能把这些链接当本地文件；文中的示例脚本不等于实际运行依赖 |

来源：[`std-react` 接线](../../../../../skills/std-react/SKILL.md#接线)、[`bp-architecture-design`](../../../../../skills/bp-architecture-design/SKILL.md)、[`bp-coding-best-practices`](../../../../../skills/bp-coding-best-practices/SKILL.md)、[`bp-component-design`](../../../../../skills/bp-component-design/SKILL.md)、[`bp-skill-authoring` 参考正文](../../../../../skills/bp-skill-authoring/reference/full-best-practices.md)。扫描未发现其他有效本地 Markdown 链接缺失；示例路径与站点相对链接须单独分类，不作为零依赖证明。

| 其他技能 | 依赖或边界 | 迁移处置 |
| --- | --- | --- |
| `frontend-playwright-verification` | 浏览器能力、运行中的应用、UI 规格或已接受概念 | 可适配为浏览器验证方法；明确证据持久化位置，并映射到 Comet 验收项，不能把方法调用等同于 Verify 通过 |
| `troubleshooting` | `codebase-researcher` Agent、`openspec/index.md`、`openspec/issues/`、模块 `custom/pitfalls.md`、本目录案例和模板 | **不是零改动迁移**；改知识读写路由，保留或替换研究 Agent，整目录带走资料 |
| `self-refinement` | 本目录参考资料、Rules／Skills 写入目标、`/reflect` 入口 | 方法可保留；命令入口需另行接线，用户批准不替代 Comet 扩展物的 eval／readiness |
| `open-code-review` | 外部 `ocr` CLI；修复路由指向 `workflow-code-generation` | 可保留外部审查入口，但需核实 CLI 环境并改后续修复路由，不能称整个技能零绑定 |
| `project-init`、`project-knowledge` | 框架安装器、能力包、固定知识入口与 Change 归档约定 | 不原样迁移；若保留长期知识，先定义与 Comet 工件及归档的单向映射和唯一写入方 |

来源：以上均可在对应 [技能目录](../../../../../skills) 的 `SKILL.md` 核实；特别是 [`troubleshooting`](../../../../../skills/troubleshooting/SKILL.md) 的代码调研与案例沉淀、[`open-code-review`](../../../../../skills/open-code-review/SKILL.md) 的修复路由。此处只记录待适配项，不修改技能或删除旧资产。

### 工作流能力取舍：保留方法，不默认保留编排

「更好」必须限定目标：审查覆盖、误报率、设计质量、交互成本或可恢复性。下面是方法层面的增量价值判断，不是已验证的质量排名。

| 当前框架技能 | 与 Comet 对照后的候选价值 | 建议与替换边界 |
| --- | --- | --- |
| `workflow-requirements-clarification` | Why 追问、矛盾与遗漏清单；Comet Open 已强调复用确认事实、只问影响决策的缺口 | 保留提问方法，不替换 Open／Shape；若追求少交互，不建议保留旧流程的逐轮确认 |
| `workflow-system-design` | 专项规范按需加载、详细设计指导；旧流程偏苏格拉底式引导，Comet Design 会提出方案供确认 | 取决于是否需要设计辅导；可抽取模板和规范，也可作为 Classic `design` producer 的适配候选，不能携带旧路径与后续路由 |
| `workflow-quick-design` | AI 主动提案、设计与任务概要合并确认 | 可作为轻量设计方法；不是 hotfix／tweak 的直接等价物。去掉旧工单脚本、任务合同和自动进入代码生成的链路，保留 Comet 必要确认 |
| `workflow-frontend-design` | 多概念确认、UI Tokens、状态、响应式、保真与浏览器验收闭环 | **优先适配保留**；它实际绑定 `openspec/changes/`，并自动调用旧代码生成流程，不能原样独立使用 |
| `workflow-code-generation` | 局部任务规划、风险判据等方法 | 不迁整个编排器；否则重新引入框架 Profile、Run、交付门与第二套任务推进机制 |
| `workflow-code-review` | 风险分档、严格档 5 类 reviewer、critic、独立 Judge、定向复审 | **优先拆成审查能力**；需带上相应 `agents/*.md`，适配上下文和结果合同，去掉框架专属 Run／Profile／交付 Artifact。不得把审查报告当成 Comet 的阶段通过 |
| `workflow-test-generation` | 单元／集成／性能／E2E 分类、边界清单、测试策略输出 | 抽取策略和生成方法，作为 TDD 的补充；二者分别回答「测什么」与「如何按失败到通过推进」，不应判为能力等价。去掉旧 Overlay 安装器调用和后续 Review 路由 |
| `workflow-verification` | 历史基线对比、只拦新增违规、检查配置冻结、防止实现期弱化门禁 | **检查器适配候选**；不能只迁 `SKILL.md`，须继续审计 `verify.py`、`workspace_residue` 等脚本依赖和报告合同；不替换 Comet Verify 控制节点 |

本地来源：各项对应 [技能正文](../../../../../skills)，重点见 [`workflow-code-review`](../../../../../skills/workflow-code-review/SKILL.md) 的档位、复审及机器产物合同，[`workflow-test-generation`](../../../../../skills/workflow-test-generation/SKILL.md) 的类型选择、边界清单与 Overlay 发现，以及 [`workflow-verification`](../../../../../skills/workflow-verification/SKILL.md) 的配置驱动、基线和配置维护约束。

Comet 对照来源（固定提交）：[Open 的缺口澄清](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-open/SKILL.md#L75)、[Design 的方案与确认](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-design/SKILL.md#L131)、[Build 的执行、TDD 与 Review 模式](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-build/SKILL.md#L32)。特别注意：[Comet Review](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-review/SKILL.md#L9) 是手动只读审查，不是工作流阶段，也不替代 Build／Verify 的自动审查；不能用它单独代表 Comet 全部 Review 能力。

### 单独替换的合法边界

依据 [Comet Any 的 Protected Boundary](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-any/SKILL.md#L32)：

- Classic `comet-five-phase-overlay` 的 `design`、`plan` 是可替换 producer，但替代实现必须满足对应 Output Schema；不是把旧 `SKILL.md` 复制过去就完成替换。
- `open`、`execute`、`verify`、`archive` 是不可在普通 Overlay 中替换的 control 节点。
- Required Skill Call 只要求节点内部调用辅助能力，不替换节点实现；handoff／guardrail 可增强。新增绑定必须说明实际强制级别，不能把 `advisory` 说成机器门禁。
- 坚持替换 control 节点时，需要新的 Workflow Kernel、状态模型、Output Schema 和 Guardrail，不属于本次最小迁移建议。
- 上述明确规则针对 Classic Overlay。**不能据此断言 Native 安装后可直接套用同样绑定**；Native 的具体 Skill 接线仍待核实，检查命令则应按其 Runtime 返回的模板和证据合同接入。

### 检查项迁移：先查重，再决定是否补充

原文「唯一决策点是 `check_delivery.py`」过窄。迁移还涉及 `verify.py` 的配置与基线，以及以下合同。未反读打包脚本时，不能断言 Comet「只查字段存在、不查事实」。

| 检查项 | 当前框架的关注点 | 迁移前必须确认 |
| --- | --- | --- |
| spec drift | 代码变更与相关规格／知识是否同步，有理由豁免时需显式记录 | 与 Comet 正式文档漂移检查的覆盖差异；不能与冻结范围检查混为一项 |
| scoped delivery 与残留快照 | 交付提交是否落在冻结范围，交付前后无关残留指纹是否一致 | Comet 的 workspace／candidate 约束能否覆盖同类风险；不能仅凭单人或多 Agent 决定是否需要 |
| `lint_task_deps` 状态一致性 | 旧 tasks 复选框与状态字段一致 | 若不保留旧任务格式，不应搬旧解析器；改验 Comet 的任务证据、当前候选绑定和完成条件 |
| knowledge-impact | 长期知识与本次变更保持一致 | 先明确保留哪些 Specs／Issues，再映射更新与归档；不能因原目录不再使用就称需求不存在 |
| 基线与配置冻结 | 历史违规不阻塞，新增违规阻塞，禁止偷偷删检查或重采基线 | 评估是否真有增量价值；如接入，需验证失败传播、报告落点和原始基线不可被覆盖 |

Comet 已有相关约束的文档证据：[Native Build](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-native/SKILL.md#L55) 描述正式文档漂移检查；[Native Verify protocol](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-native/reference/commands.md#L113) 描述候选、工作区、命令与输入绑定，以及独立验收；[Classic Build](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-build/SKILL.md#L63) 描述任务权威与计划同步；[Project Memory](https://github.com/rpamis/comet/blob/899d1fb05cd4/assets/skills/comet-tweak/SKILL.md#L41) 有已验证知识的写入接口。这些证据足以否定「完全没有」的笼统判断，但尚不足以证明与旧框架逐项等价。

### 接入验收表与执行顺序（未实测）

迁移原则：**Comet 唯一负责状态推进；技能只提供被委派的方法、产物或证据**。先选择 Classic 或 Native，不混用两者的扩展合同。

| 接入对象 | 输入与输出 | 必须验证的成功／失败路径 |
| --- | --- | --- |
| 规范技能 | 当前任务、文件类型 → 实际加载记录与符合规范的产物 | 在不安装旧框架的沙箱中，引用均能解析；缺依赖时明确报告，不自动回旧流程 |
| Classic 设计／计划 producer | Comet 当前 Change 的正式工件 → 满足节点 Output Schema 的产物 | 合法产物可交回；缺字段或未确认方案不可推进；不另建主状态或跳过 Comet 门禁 |
| 前端能力组合 | 正式需求、已确认概念 → UI 规格、实现、DOM 与截图证据 | 缺 UI 规格、页面错误或视觉不符时不能宣称通过；证据与当前验收项对应 |
| Review／测试辅助能力 | 当前候选 diff、需求与验收项 → findings、测试与实际结果 | 实现者不能伪造独立审查；审查通过不冒充测试通过；后续修复仍由 Comet 调度 |
| Verify 检查器 | 受信配置、原始基线、当前候选 → 退出码与报告 | 人为制造新增违规应失败；检查器错误不能算 PASS；弱化配置、报告过期或候选变化需拒绝或重验 |
| Native 接入 | Runtime 返回的输入模板、当前候选和验收项 → Runtime 接受的检查与 Verifier 结果 | 先核实实际接入方式，再验证失败不推进；Classic Required Skill Call 示例不充当 Native 接线证据 |

执行顺序建议：

1. 固定目标 Comet 版本和工作流，建立迁移清单及每项依赖闭包；保留旧资产和可验证备份，不删除或覆盖旧安装。
2. 在独立沙箱中只迁 `std-python` 及其参考资料，验证能加载、能遵循规范、不会调用旧框架；若使用 Required Skill Call，额外验证其实际强制级别。
3. 再试前端组合或独立 Review 等单个高价值切片；每次只增加一类适配，跑上表的成功与失败路径。
4. 用同一组任务、模型和预算，对比默认 Comet 与适配版本的验收遗漏、Review 误报、交互轮次、token／耗时和恢复表现；没有对比证据前，只称「候选增强」，不称「更好」。
5. Classic 扩展物按 `/comet-any` 走确认、eval、review、readiness、人工批准与 install preview；Native 按已核实的接入方式验收。通过后才扩大迁移范围。

## 缺失证据与后续动作

- guard/state/hook 打包脚本内部逻辑未反读，不能断言现有检查只验证字段存在；逐项等价性仍缺测试与运行证据。
- 本次未执行安装或迁移验证，也未核实本机安装版本与分析基准是否一致。
- Classic producer 的具体 Output Schema、Required Skill Call 强制级别和 `/comet-any` 管线未实跑；Native 的辅助 Skill 接线方式待确认。
- 独立 Review 的 Agent 依赖、Verify 脚本的完整依赖与证据转换仍需在实施前核查，不能把方法层分析当作可直接安装的迁移包。
- 尚无默认 Comet 与适配版本的对照实验，未证明任何旧工作流整体优于对应 Comet 能力。
