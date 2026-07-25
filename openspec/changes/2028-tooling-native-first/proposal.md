# Proposal: Tooling Native-first 交付路径（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：tooling-native-first
**状态**：Quick Draft

---

## 1. 问题与目标

### 问题

当前 Tooling 的中等及以上任务由 `workflow-code-generation` 强制进入完整 Runtime Run：执行前必须 `init-run`，任务质量通过必须绑定 Run 内 Verify Artifact，最终交付必须经过 Manifest、Journal、Harness Capability 与 Trust Gate 校验。该路径将 DAG 调度、质量反馈与跨宿主审计绑定为同一默认合同。

其中，`workflow-verification` 可以独立运行，`workflow_control.py` 的波次、状态转换、失败隔离和恢复也有独立价值；但 Run Context、Manifest、Journal、Adapter 探测与 Trust Gate 只为完整 Run 证据链服务。模型和原生 Coding Agent 能力提升后，将这些后者作为普通任务的默认前置，会增加 Token、时延和维护成本，并使补偿旧模型局限的假设难以按需退役。

### 目标

1. 为 Tooling 定义「Native Delivery」默认合同：原生 Agent 完成实现、测试、机器验证和一次最终 Review 后，可输出有界交付结论，无需建立完整 Runtime Run。
2. 保留完整 Runtime Run，且仅在高风险、并行隔离、长任务恢复、跨宿主能力验证或明确审计要求时升级启用。
3. 将 DAG 调度与任务恢复从完整 Run 协议中概念上解耦；只有实际存在任务依赖或并行写入时才启用。
4. 将现有 Fast-Path 的「主会话直接修改」分支收敛到 Native Delivery，避免按执行主体维护两套低／中风险交付路径。
5. 在删除或降级任何 Runtime 组件前，用真实任务数据确认 Native Delivery 没有降低交付质量。

### 非目标

- 本 Change 不删除 `runtime_*`、`run_*`、Harness Adapter 或现有 Schema。
- 不削弱测试、Lint、类型检查、行为验证、最终 Review 或高风险独立审查。
- 不改变 Production 的 `opsx-*` 生命周期、阶段门或审批边界。
- 不以模型名称或版本号作为升级／降级条件；只依据任务风险与可验证的执行需求。
- 不在本 Change 中建设新的观测平台、通用多 Agent 编排器或跨产品执行引擎。

### 验收标准

- 提供 Native Delivery、完整 Runtime Run 与高风险升级条件的明确合同，且每种结论的可证明与不可证明范围可审计。
- 明确 `workflow-code-generation`、`workflow_control.py`、`workflow-verification`、`workflow-code-review` 与 `check_delivery.py` 的迁移责任和依赖顺序。
- 运行至少 3 个公开 SWE-bench Verified 实例，并以本地路由 Fixture 验证升级条件；记录交付质量、人工介入、耗时、Token、重试和恢复需求，且不得把两类证据混同。
- 在真实任务尚未证明净收益前，不删除 Runtime 代码；实现阶段的回归测试必须覆盖原完整 Run 与新 Native Delivery 两条路径。

## 2. 设计方案

### 2.1 整体方案

Tooling 采用「Native-first，Runtime opt-in」的双路径，而不是将完整 Run 替换为无验证的自由执行：

```text
任务合同（目标、上下文、约束、完成条件）
    → 原生 Agent 实现、测试与机器验证
    → 一次最终 Review
    → Native Delivery Verdict

命中升级条件
    → 完整 Runtime Run
    → Manifest、Journal、Capability Probe、Trust Gate
```

Native Delivery 只声明已验证的测试／机器验证、最终 Review、知识影响和提交／工作区状态；不得声称已经证明 Harness 能力、跨会话恢复、Artifact 全链路来源或严格独立 Judge。完整 Runtime Run 继续提供这些更强声明。

### 2.2 核心组件

- **任务合同**：所有路径保持目标、相关上下文、约束和完成条件四项最小输入；复杂或模糊任务仍可先设计和拆分任务。
- **原生执行路径**：默认由当前宿主的原生 Agent 或边界明确的子 Agent 执行。测试、机器验证和最终 Review 不依赖 `init-run`。
- **可选 DAG 控制**：`workflow_control.py` 的波次、状态、失败隔离和恢复只在任务依赖、并行写入或中断恢复确有需求时使用。`init-run` 与 Run 绑定的 `quality_passed` 记录迁入完整 Runtime 路径。
- **Native Delivery Verdict**：由交付门消费非 Run 的验证与 Review 证据，输出有界裁决；它不是 `runtime_trust.validate_run` 的替代品。
- **完整 Runtime Run**：保留现有 Run Context、Manifest、Journal、Adapter、Capability Matrix 与 Trust Gate，不改变其严格失败关闭语义。

### 2.3 交付接口与升级条件

实现阶段应将交付门明确分为三类：

| 路径 | 适用条件 | 必要证据 | 不得声明 |
| --- | --- | --- | --- |
| Native Delivery | 普通低／中风险任务；无跨宿主审计需求 | 机器验证、最终 Review、知识影响、提交或工作区状态 | Trust Gate PASS、Harness 能力、完整证据图、严格独立性 |
| 完整 Runtime Run | `strict` 风险、并行 worktree 写入、长任务恢复、跨宿主能力验证或审计要求 | 现有 Run 级 Artifact、Manifest、Journal、Capability Probe、Trust Gate | 超出当前 Trust Model 的业务正确性或身份隔离保证 |
| Fast-Path 兼容期 | 尚未迁移的局部低风险调用 | 现有 lightweight Review 与机器验证 | 对 Native Delivery 或完整 Runtime 的额外保证 |

升级必须由任务风险或执行需求触发，例如安全、权限、数据迁移、并发、分布式、性能关键路径、公共 API、大范围重构、并发写入冲突、会话恢复或审计。仅仅因为任务文件数增加，或模型版本变化，不自动触发完整 Run。

### 2.4 迁移顺序

1. **合同与测试先行**：定义 Native Delivery Verdict，补齐无 Run 的标准 Review／Verify／Delivery 正反用例；完整 Run 回归不变。
2. **入口解耦**：将 `workflow-code-generation` 的默认执行路径改为 Native Delivery；`init-run` 只在升级条件命中时执行。
3. **控制流拆分**：保持 `workflow_control.py` 的 DAG 与恢复能力，将 Run 初始化和 Run-bound Artifact 逻辑隔离到 Runtime 专用入口。
4. **收敛 Fast-Path**：迁移完成后，以 Native Delivery 替代「主会话直接修改」这一执行分支；仅保留兼容别名直到调用方完成迁移。
5. **基于数据退役**：真实任务未显示净收益的 Runtime 默认门禁退出默认路径；仍有明确场景价值的组件保留为 opt-in。

### 2.5 关键权衡

1. **保留验证，不保留默认重编排**：测试与 Review 直接提供质量反馈；Manifest、Journal 和 Capability Probe 提供的是更强审计与恢复保证，不应混为普通任务必需条件。
2. **双路径而非一次性删除**：完整 Runtime 已有 Schema、测试和严格审计语义。先让 Native Delivery 与其并存，可避免将高风险路径误降级。
3. **先验证再简化**：3 个真实任务只能作为试点，不构成普遍性能结论；若试点显示质量或恢复能力下降，应调整升级条件，而不是继续删除组件。
4. **统一低／中风险执行形态**：收敛 Fast-Path 能减少维护分支，但不能把其轻量裁决伪装成完整 Trust Gate。

## 3. 知识影响

- `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`：需补充 Native Delivery 与完整 Runtime Run 的声明边界。
- `openspec/specs/backend/framework/workflow-control/overview.md`：需说明 DAG／恢复与完整 Run 的可选关系。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：需更新 Tooling 默认路径与 Profile 路由。
- `README.md`、`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-review/SKILL.md`、`skills/workflow-verification/SKILL.md`：实施阶段同步当前合同。

## 4. 运维

- 不新增服务、凭据或后台进程。
- Native Delivery 继续复用仓库现有测试、Lint、浏览器验证和本地 Git 证据。
- 完整 Runtime Run 继续将本地运行产物写入 `.agentic-framework/runs/`；Native Delivery 不创建该目录。
- 试点任务的比较数据只用于路径决策；缺失 Token 或成本数据时记录 `unknown`，不得估算。

## 5. 参考资料

- [`skills/workflow-code-generation/SKILL.md`](../../../skills/workflow-code-generation/SKILL.md)：当前 Tooling 路由、完整 Run 前置与交付门。
- [`skills/workflow-code-generation/scripts/workflow_control.py`](../../../skills/workflow-code-generation/scripts/workflow_control.py)：DAG、状态恢复与 Runtime Run 初始化入口。
- [`skills/workflow-code-generation/scripts/check_delivery.py`](../../../skills/workflow-code-generation/scripts/check_delivery.py)：当前 Fast-Path 与 Run 级交付分支。
- [`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`](../../specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md)：当前 Trust Model 与 Skill 接入矩阵。
- [OpenAI：Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)。
- [OpenAI：Codex best practices](https://developers.openai.com/codex/learn/best-practices)。
