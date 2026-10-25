# 外部参考：Agentic Engineering 同类框架与模型演进

> 本文是截至 2026-10-25 的研究快照，不是当前实现规格、性能排名或已批准的架构决策。用户确认将研究沉淀到项目知识库，不等于批准实施下列候选路线。知识仅辅助理解，当前事实仍须回到代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 研究与沉淀日期 | 2026-10-25 |
| 最新发展观察窗口 | 2026-08-25 至 2026-10-25 |
| source_ref | `7441ecc96a2f6b71f3df6b7ba0e73530ce6a6c11`，结合研究时工作区读取；不是洁净工作区快照 |
| 本地核实范围 | README、知识索引、综合说明、安装器、治理守卫、执行路由、信任模型、宿主适配器、评测入口和试点记录 |
| 外部核实范围 | 同类项目当前 README、OpenAI 与 Anthropic 官方更新日志、Google 官方月度汇总 |
| 外部版本边界 | 网页检索与正文提取日期为 2026-10-25；未固定外部仓库提交，也未保存网页全文快照，后续引用须重新核实 |
| 运行验证 | 本轮未执行全量回归、同场基准、模型行为评测或生产验收 |
| 关联 Change | [2049-agentic-landscape-knowledge](../../../../changes/2049-agentic-landscape-knowledge/proposal.md) |

### 证据标签

- **已确认**：本地实现可直接读取，或一手项目文档明确描述该能力；外部文档描述不代表本项目已经集成或独立验证。
- **项目记录**：历史任务或试点记录中的结果，本轮未重新执行。
- **推断**：对定位、成本和适配方向的判断，不能替代对照实验。
- **候选建议**：待另行需求澄清、设计和验收，不构成当前约束。

## 1. 核心结论与项目定位

**定位推断**：本项目更接近「运行在 Codex／Claude Code 之上的工程交付治理层」，而非独立运行模型和工具的通用 Agent 引擎。最直接的对标对象是编码 Agent 工作流、工程方法和 Skills 插件。

直接证据：

1. [安装器](../../../../../scripts/install_agentic_framework.py) 的 `CLIENT_DIRS` 为 `.codex` 和 `.claude`。
2. [治理守卫](../../../../../skills/workflow-code-generation/scripts/governance_guards.py) 的 `plan_gate_errors`、`task_review_guard_errors` 和 `integration_review_guard_errors` 检查 Production 计划、任务和集成审核证据。
3. [执行路由](../../../../../skills/workflow-code-generation/scripts/workflow_control.py) 的 `select_execution_route` 默认选择 Native Delivery，遇到严格风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或审计要求时选择 Runtime Run。
4. [信任模型](../../../../../scripts/runtime_trust.py) 明确区分 `VERIFIED_CLAIMS` 和 `UNPROVABLE_CLAIMS`。

**候选定位**：跨宿主、可验证、按风险承担成本的工程交付治理层。长期价值应通过「通过了什么验证、证据是否属于当前交付、减少了什么风险并增加多少成本」衡量，而不是通过 Agent、Skill 或流程数量衡量。

## 2. 同类项目与相对优缺点

以下比较基于公开定位与能力，不是性能测试；没有证据证明本框架的缺陷率、速度或费用优于这些项目。

| 项目与一手来源 | 当前公开重点 | 本框架相对侧重 | 本框架的代价或待验证短板 |
| --- | --- | --- | --- |
| [Superpowers](https://github.com/obra/superpowers) | 可组合 Skills、需求讨论、计划、TDD、worktree、子 Agent 实施与审核 | 双 Profile、确定性治理守卫和 Run 证据协议 | 对方宿主安装入口更广；本框架额外概念和流程的收益需要实测 |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) | 变更提案、规格、实施和归档；跨仓库 Stores 处于 beta | 将 Review、Verify、风险控制和证据绑定组合为交付治理 | 自有门禁并非官方 CLI 兼容层，需要承担协议分叉与跟进成本 |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 结构化过程、Extensions、Hooks、Workflows、Overlays、Bundles 和 Catalogs | 本地双宿主、审核规则及双 Profile 的直接控制 | 对方扩展、组合与分发机制更丰富，不应继续将其归类为纯文档模板 |
| [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin) | Brainstorm、Plan、Build、Review 与经验沉淀循环，多宿主支持 | 项目／公共知识边界、确定性交付门与信任声明 | 规划、审核和经验沉淀高度重合，需要证明额外治理的边际收益 |
| [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) | 从想法、需求、规划到构建验证，按工作规模调整过程 | 更集中于代码交付、机器证据和风险审核 | 若目标是完整产品研发方法，产品探索覆盖相对窄 |

### 不应继续沿用的旧判断

- Superpowers 当前也区分每任务子 Agent 加审核，以及当前会话实施加最终统一审核；控制审核成本不是本框架独有能力。
- Spec Kit 当前已有工作流、扩展和门禁接入机制，不能用「只有 Spec 模板」概括。
- 多宿主支持不等于多宿主等价可靠；每种宿主的版本、权限和实际能力仍须验证。
- 不把通用 Agent SDK 与工程工作流插件混为同一类竞品，也不将未读取的项目纳入已完成对比。

## 3. 当前项目值得保留的能力与缺口

### 3.1 值得保留的组合

1. **确定性规则与语义判断分工**：治理脚本检查结构、证据和状态，LLM 负责语义。脚本被执行时能拒绝不合规，不等于宿主无法绕过脚本。
2. **Native-first 与按需 Runtime**：已有风险升级路由，不需要为了追求轻量再创建一套平行入口。
3. **明确证明边界**：信任模型可校验 Artifact 摘要、Run 绑定和声明的审核主体分离，但明确不能证明语义正确、强身份隔离或完全失陷宿主下的完整性。

对应代码见第 1 节。以上是结构优势判断，不是已测得的质量优势。

### 3.2 增益证据不足

[Native Delivery 试点记录](../../../../../evaluation/native-delivery-pilot.md) 报告 3 个 SWE-bench 实例解决，同时明确区分真实代码修复结果、路由 Fixture 和 Runtime Trust Gate 证据。本轮未重新运行，也未独立核验记录引用的本地忽略目录产物。

因此，不能从这 3 个实例推导「有框架优于无框架」，也不能推导「Runtime 可以删除」。尚缺固定模型、任务、起点和验收条件的配对实验。

### 3.3 宿主能力与行为评测仍有接线缺口

- [Codex 适配器](../../../../../scripts/codex_adapter.py) 的 `_probe` 返回静态 `CAPABILITIES`；其中不承诺子 Agent、worktree 隔离和兼容生命周期 Hook。
- [Claude Code 适配器](../../../../../scripts/claude_code_adapter.py) 同样返回静态能力表。
- 两个适配器的 `_evaluate` 均返回 `not_executed`；[评测入口](../../../../../scripts/evaluation_runner.py) 的 `SubprocessAdapter.__call__` 期待 `transcript` 和 `signals`。

**结论边界**：本项目已有评测基础设施，但上述两个适配器没有真正执行行为评测。静态声明不代表能力已在当前宿主中探测成功；适配器不承诺支持，也不能用于否认宿主产品本身的能力。

### 3.4 已发现但未处理的知识冲突

| 项 | 证据 |
| --- | --- |
| 知识文件 | [综合说明](../../../../../docs/framework-features-status-and-comparison.md)，§4.3 |
| 知识结论 | 最多两轮定向复审 |
| 知识版本 | 文档标注更新日期 2026-09-12；本条未记录独立 `source_ref` |
| 当前工作流证据 | [Review Skill](../../../../../skills/workflow-code-review/SKILL.md)，「循环语义」规定最多 10 轮 |
| 冲突类型 | 综合知识说明与当前可加载工作流指令不一致 |
| 不确定性 | 未追踪两个数值的设计审批历史，也未验证所有调用方实际如何执行；不能单凭文件新旧决定应改哪一方 |
| 后续动作 | 单独核实预期复审上限与实际成本，再确认修改对象；本次只记录冲突，不修改任一方 |

## 4. 最近两个月的相关发展

以下发布事实来自本节列出的一手来源。厂商性能宣传不是本项目独立复现结果；API 或托管服务能力不能直接等同于本地 CLI 能力。

### 4.1 模型更新与任务成本

| 厂商 | 窗口内已核实的更新 | 对本项目的候选影响 |
| --- | --- | --- |
| OpenAI | 9 月 3 日 GPT-6 Astra；9 月 22 日 GPT-6 Sol／Luna；9 月 29 日 GPT-6.1 Sol | 按任务重新评估模型、推理强度和流程成本，不对所有模型套用固定重流程 |
| Anthropic | 9 月 22 日 Claude Opus 5.5；9 月 28 日 Sonnet 5.5；10 月 7 日 Haiku 5.5 | 重新测试任务级质量与费用，不仅比较 Token 单价 |
| Google | 9 月发布 Gemini 3.8 Flash，并介绍 Gemini 4 Argon；Argon 当时面向可信安全防御者分阶段开放 | 纳入适配观察，不把受限开放模型当作普遍可用方案 |

来源：[OpenAI 官方更新日志](https://developers.openai.com/api/docs/changelog)、[Claude 官方更新日志](https://platform.claude.com/docs/en/release-notes/overview)、[Google 9 月官方汇总](https://blog.google/innovation-and-ai/technology/ai/google-ai-updates-september-2026/)。

**推断**：模型变强可能降低细碎拆分与重复审核的收益，但不能自动替代项目验收、权限边界和真实测试；是否简化流程必须通过消融实验判断。

### 4.2 厂商提供更多 Agent 运行基础设施

- 9 月 10 日，OpenAI Agents API 公测，提供托管 Codex harness、持久会话、上下文压缩与恢复。
- 9 月 29 日，GPT-6.1 Sol 支持 Responses API 内多 Agent 委派，处于 beta。
- 10 月 9 日，Claude Managed Agents 增加动态工作流 beta，可由 Agent 编写分阶段多 Agent 工作流并交由服务端运行。

来源：上述 OpenAI 与 Claude 官方更新日志。

**候选分工**：宿主负责执行与会话能力，框架负责项目规则、验收、证据与放行。不为追赶厂商而重造通用运行引擎；现有 Runtime 的保留或替换仍须依据实测和信任边界。

### 4.3 长任务执行中干预

OpenAI 在 9 月 3 日加入异步工具调用、执行中指令调整（mid-turn steering）和会话中调整推理强度。来源：[官方更新日志](https://developers.openai.com/api/docs/changelog)。

候选验证问题：用户中途改需求后批准是否有效、哪些任务和证据需要失效、取消后的迟到工具结果是否可被采纳、恢复是否会重复副作用。重点是治理语义，不是照搬接口。

### 4.4 缓存与可观测性

- OpenAI：9 月 8 日 Prompt Cache Diagnostics GA；10 月 20 日增加 12 小时缓存选项。
- Anthropic：10 月 14 日 OpenTelemetry 导出进入 beta，可追踪 Messages API 与 Managed Agents。

来源：上述两份官方更新日志。

**候选建议**：在现有 Telemetry 上补齐可获取的模型、缓存、耗时和费用字段，不可得值记为 `unknown`。不把提示词更短直接等同于任务费用更低，也不先建设完整 OTel 平台。

### 4.5 模型与 API 兼容性

- GPT-6 Astra 的工具调用要求 Responses API，部分采样参数不支持。
- Claude 5.5 的 thinking、强制工具调用和 computer-use 工具版本有迁移差异。
- Anthropic 在 10 月 21 日发布新 API 版本及包含破坏性变化的 SDK 大版本。

来源：上述两份官方更新日志。

**适用边界**：先验证宿主能力契约；只有直接调用相关 API 的代码才需要对应迁移，不因发布信息批量修改框架。

## 5. 候选跟进优先级与验收方向

以下为研究建议，不是已批准实施任务。

| 优先级 | 候选动作 | 最小验收方向 |
| --- | --- | --- |
| P0 | 固定模型、任务和验收条件，比较原生宿主、本框架 Core／Native Delivery、Superpowers | 独立验收、重要缺陷、人工介入、返工、总耗时、费用及 Review 误报均可追溯；不以结构通过代替真实效果 |
| P0 | 从静态声明走向当前宿主能力验证，接通真实行为评测 | 区分产品支持、当前启用和框架已验证；缺能力、版本变化或权限不足时不误报可用 |
| P1 | 流程消融：综合／五维 Review、复审轮次、任务粒度、默认上下文 | 固定条件逐项比较收益与成本；删减依据证据，不因模型升级自动降低生产或安全门禁 |
| P1 | 验证中断、改需求和恢复对证据有效性的影响 | 修改前的通过报告不能自动证明修改后仍通过；迟到结果与重复副作用有针对性用例 |
| P2 | 按实际用户需求扩展分发、版本固定与宿主支持 | 个人使用先稳定双宿主；外部团队需求明确后再考虑插件分发和工件互操作 |

### 配对实验建议

1. 先选 10～20 个代表任务用于发现方向，不能把小样本包装成统计定论。
2. 固定模型版本、推理强度、起始提交、工具权限和验收标准；使用隔离工作区并重复运行。
3. 区分低风险与高风险任务；低风险 Native Delivery 的结果不能替代 Runtime 验收。
4. 复用现有评测与 Telemetry 设施，避免另建平台。
5. 优先回答「框架相对原生宿主减少什么风险、增加多少成本」，再决定扩充或删减能力。

### 暂不建议

- 为功能数量继续增加 Agent 或 Skill。
- 未验证收益就建设通用多模型运行时、完整 OTel 平台或自动自进化系统。
- 同时追求所有模型、所有 CLI 的适配。
- 将厂商基准、历史单元测试或少量成功实例当作框架生产收益证明。

## 6. 维护与再核实规则

- 外部 README、发布日志和 beta 状态变化后，重新读取原文，不将本快照当作永久事实。
- 本地适配器、路由、Review 策略或评测入口变化后，优先复核第 3 节。
- 首次获得配对评测或生产验收数据后，再评估定位与优先级；报告失败样本和缺失字段。
- 本文不覆盖已有综合说明，也不消除其冲突；若后续批准修复，应分别更新事实源和引用。
- 仅沉淀在当前项目，不自动晋升跨项目公共知识库。
