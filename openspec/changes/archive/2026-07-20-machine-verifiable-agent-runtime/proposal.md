# 建立机器可验证的 Agent 运行协议

- **作者**：Codex
- **日期**：2026-07-19
- **状态**：Archived

## 1. 背景

框架已经具备双 Profile、确定性控制流、结构化 Review/Verify 报告、失败恢复和会话 Telemetry，但这些能力尚未形成统一的运行协议：

- Verify、Review、Task 状态和 Telemetry 分别定义自己的字段与解析规则，缺少统一的 Run、Task、Attempt 和 Artifact 标识。
- 质量门能校验报告内容是否满足局部合同，但不能证明报告、代码提交、配置和当前 Task 来自同一次执行。
- 4 个核心路由 Skill 已有 `should-trigger`、`should-not-trigger` 和边界用例，但没有自动 Runner、稳定结果基线和回归门。
- Tooling 能根据 `tasks.md` 与已合并事实生成恢复动作，但没有可重放的 Run 级事件账本。
- 框架支持多个 Agent Harness，但没有显式能力矩阵和统一降级语义。
- 当前信任边界分散在 Skills、Agents、质量门和 ADR 中，尚未形成一份可检查的最小信任模型。

现状证据见 `openspec/specs/backend/framework/`、`openspec/specs/backend/engineering/tech/adr/003-quality-gate-evidence.md`、`docs/tooling/08-evaluation-strategy.md` 和 `docs/tooling/13-agentic-workflow-engine-references.md`。

## 2. 目标

### 2.1 P0：建立统一机器协议

- 定义可版本化的 Run Envelope，以及 Review、Verify、Task、Event 等分类型 Payload Schema。
- 定义 Run Manifest，把代码版本、配置、任务、产物摘要和质量结论绑定到同一次 Run。
- 把现有触发用例升级为可执行的 Agent 行为评测，并建立最小回归基线。

### 2.2 P1：补齐可移植性与可信恢复

- 定义 Harness Capability Matrix 和 Adapter 合同，明确支持、降级与失败关闭语义。
- 定义追加式 Run Event Journal，使恢复依据事件与 Checkpoint，而不是对会话文本进行推断。
- 定义最小 Trust Model，说明参与者、可信证据、独立性要求、用户覆盖和不可证明的边界。
- 将 Verify、锁、Telemetry 和 Run 等本地运行产物统一收口到 `.agentic-framework/`，避免框架私有状态散落在项目目录中。

### 2.3 非目标

- 不新增第三个 Profile。
- 不引入 RBAC、远程控制面、Web Console 或 OpenTelemetry 平台。
- 不构建通用 Workflow DSL，也不把 `tasks.md` 升级成大型 AST。
- 不实现自动自进化或全量 Skill 的高成本 LLM Judge 评测。
- 不用一个巨型 Schema 强行统一所有 Payload；统一的是信封、标识和证据关系。

## 3. 成功标准

- 任一 Run 产物都能回答「由谁、在什么 Profile/Harness、针对哪个 Task/Attempt、基于哪个 Commit 和配置生成」。
- 质量门拒绝 Run、Task、Attempt、Commit、配置摘要或 Artifact 摘要不匹配的证据。
- Run Manifest 能从一次执行的产物中建立完整证据链，并检测缺失、孤立和被替换的 Artifact。
- Tier 1 行为用例可自动执行，输出机器可读结果，并能阻止核心路由能力相对基线退化。
- 中断后能从事件账本与 Checkpoint 计算恢复动作；不依赖扫描聊天记录猜测状态。
- 每个受支持 Harness 都有明确能力声明；缺少必需能力时失败关闭，可选能力缺失时产生可观察的降级记录。
- Trust Model 明确哪些结论只能证明「证据存在且一致」，不能证明语义判断一定正确。
- 框架生成的本地运行状态只写入 `.agentic-framework/`；正式代码、测试、配置、Schema、OpenSpec 和文档继续由 Git 管理。

## 4. 知识影响

- 命中：新增框架级运行协议、证据链、行为评测、Harness 适配和信任边界设计。
- 当前只建立活跃 Change，不提前写入长期 Specs；实现并验证后再归档同步。
- 不修改跨项目公共知识库。
