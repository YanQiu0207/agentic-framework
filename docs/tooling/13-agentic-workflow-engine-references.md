# 独立 Agentic Workflow Engine 参考方案

## 结论

本框架若要从「Prompt-native 工作流 + 确定性控制流内核」升级为可独立运行的 Agentic Workflow Engine，最值得参考的不是另一个 Skill 集合，而是以下 4 类运行时：

1. **LangGraph**：参考图执行、Checkpoint、暂停恢复和人工审批。
2. **Microsoft Agent Framework Workflows**：参考类型化消息路由、Superstep、并发分支和完整 Checkpoint。
3. **Temporal**：参考副作用隔离、持久化执行、重试、超时和长任务恢复。
4. **OpenAI Agents SDK**：参考 Agent、Tool、Handoff、Guardrail 和 Trace 的运行时接口。

完整 Engine 对当前面向本地个人开发和非生产工具的框架偏重。建议只借鉴接口与状态模型，暂不建设独立 Workflow Engine。当前最小缺口是「运行证据层」，不是重写已有 DAG、状态机或建设调度平台。

## 核心原理

Agentic Workflow Engine 本质上只解决一个问题：

> 把「靠 Agent 记住自己做到哪」改成「由程序保存状态，并决定下一步做什么」。

### 确定性决策与不确定执行分离

```text
控制器：根据事实决定下一步执行什么
Agent：阅读上下文并完成开放式实现
```

控制器只处理依赖、状态、重试、阻塞、恢复和人工门，不参与代码实现。Agent 负责阅读、修改、测试和分析。现有 `workflow_control.py` 已经承担确定性决策职责，不需要重写。

### 副作用单独执行

Agent、Git、worktree、测试和 Review 都是可能失败、超时或重复执行的副作用：

```text
准备执行
→ 执行中
→ 成功或失败
→ 保存证据
→ 推进状态机
```

完整 Engine 会把每类副作用封装成 Executor 或 Activity。当前框架不需要先建立通用 Executor 平台，只需确保关键副作用留下可校验的结果。

### 状态持久化与恢复

没有持久状态时，中断恢复需要重新读取 `tasks.md`、Git 和聊天记录，再推断上次进度。有持久状态时，运行时读取同一个 `run_id` 和最后 Checkpoint，从下一步继续。

重点不是引入数据库，而是每个状态变化都有记录，恢复不依赖聊天上下文。

### 幂等与证据绑定

进程可能在 Git commit、Review 或 Verify 已完成，但成功结果尚未持久化时崩溃。恢复后直接重跑可能造成重复 worktree、commit 或 merge。

关键动作应绑定：

```text
run_id + task_id + attempt + action + commit_sha
```

恢复时先查已有 Artifact，再决定复用还是重跑。

## 为什么完整 Engine 偏重

完整实现通常需要：

- 数据库、Worker 和队列。
- Checkpoint 与事件历史。
- 超时、重试、取消和幂等控制。
- 人工审批和 Workflow 版本管理。
- 分布式锁、跨机器调度和 Web UI。

这些能力适合小时级或天级长任务、跨机器执行、大量并发、高风险发布和强审计场景。当前框架主要在本地宿主 Agent 中运行，直接引入 Temporal 或重写为 LangGraph，复杂度大概率超过收益。

## 当前框架缺少什么

现有 `workflow_control.py` 已负责：

- DAG 分波。
- 可调度任务判断。
- 状态迁移。
- 重试计数。
- 下游阻塞。
- 恢复决策。
- `tasks.md` 原子写与跨进程写锁。

缺少的独立运行时能力：

- 创建和销毁 worktree。
- 启动 Agent 并传入隔离上下文。
- 收集结构化 Agent 结果。
- 实际调用 Review 和 Verify。
- 校验质量门证据，而不是接受调用方提交的 `quality_passed`。
- 提交、合并和冲突处理。
- 持久化运行事件、成本、产物和外部副作用。
- 进程崩溃后自动恢复，而不是只生成恢复建议。
- 在人工审批点暂停，并从同一运行实例继续。

## 候选参考

### LangGraph

LangGraph 是低层图运行时，直接覆盖本框架最缺的暂停恢复能力：

- 每一步保存图状态 Checkpoint。
- 使用 `thread_id` 标识可恢复运行。
- 节点失败后从上一个成功步骤恢复。
- 同一 Superstep 中已成功节点的 Pending Writes 可保留，恢复时不必全部重跑。
- `interrupt()` 可暂停执行，等待人工 approve、edit 或 reject 后继续。
- 可读取历史状态、回放旧 Checkpoint，并从历史状态分叉。

官方资料：[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)、[Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)、[LangGraph GitHub](https://github.com/langchain-ai/langgraph)。

**最值得吸收**：

- `run_id/thread_id` 与 `checkpoint_id` 分离。
- 每个状态转换后生成不可变 Checkpoint。
- 人工门不是退出流程，而是持久化的 `WAITING_APPROVAL` 状态。
- 恢复使用同一个运行标识，不重新猜测任务进度。

**不宜直接照搬**：

- 当前框架已经有自己的 Markdown 任务合同和控制流内核，直接改成 LangGraph StateGraph 会造成双状态源。
- LangGraph 恢复节点时可能从节点开头重新执行，因此节点内副作用必须幂等；Git、文件写入和模型调用需要单独设计幂等键。
- LangGraph 恢复时默认应用最新图定义，长任务跨版本恢复需要额外记录 Workflow 版本。

### Microsoft Agent Framework Workflows

Microsoft Agent Framework 已于 2026-04-03 GA（1.0 版本合并 Semantic Kernel 与 AutoGen）。Agent 与 Workflow 分开：Agent 负责开放式推理，Workflow 负责显式执行路径。图执行 API（`WorkflowBuilder`）已随 1.0 GA，支持图路由、类型化消息、Checkpoint 和 Human-in-the-loop；另一套基于 `@workflow` / `@step` 装饰器的 Functional API 仍标注 Python Experimental。

它的 Checkpoint 会在每个 Superstep 完成后保存：

- 各 Executor 的状态。
- 下一 Superstep 的待处理消息。
- Pending Request/Response。
- Shared State。

官方资料：[Agent Framework Overview](https://learn.microsoft.com/en-us/agent-framework/overview/)、[Workflow Checkpoints](https://learn.microsoft.com/en-us/agent-framework/workflows/checkpoints)。

**最值得吸收**：

- Executor 与消息类型显式化，不让节点之间传任意自然语言。
- 以 Superstep 作为并行波次与 Checkpoint 边界。
- Checkpoint 同时保存任务状态和待处理消息，避免恢复时丢失尚未消费的事件。
- Agent Session、Middleware、MCP Client 和 Workflow Runtime 分层。

**不宜直接照搬**：

- 图执行 API 已 GA（2026-04-03），可作为长期参考；但 Functional API 仍标注 Experimental，接入前需按具体使用的 API 分别核对稳定性。
- 引入完整框架会改变当前零运行时、跨 Claude Code/Codex 的安装方式。
- 本框架短期只需要本地代码 Agent 编排，不需要先建设通用企业 Agent 平台。

### Temporal

Temporal 是通用 Durable Execution 平台，不负责 Agent 推理，但能保证 Workflow 在进程崩溃、网络失败或基础设施故障后从原位置恢复。

官方资料：[Temporal Documentation](https://docs.temporal.io/)、[Gemini + Temporal Durable Agent 示例](https://ai.google.dev/gemini-api/docs/temporal-example)。

**最值得吸收**：

- Workflow 只做确定性决策，LLM、Git、文件系统和外部命令作为 Activity 执行。
- Activity 具备独立的 Retry、Timeout、Heartbeat 和 Cancellation 语义。
- 使用 Signal/Update 表达人工批准、取消和外部状态变化。
- 通过事件历史重放恢复 Workflow，而不是从散落文件推断进度。
- 每个副作用使用幂等键，避免崩溃恢复后重复提交或重复合并。

**不宜直接照搬**：

- 自建 Temporal Server、Worker 和持久化存储对个人本地框架过重。
- Workflow 代码需要满足确定性重放约束，现有 Prompt 和动态文件扫描不能直接放入 Workflow 决策层。
- 更适合跨机器、小时级或天级任务；本地分钟级任务先用 SQLite 事件日志即可。

### OpenAI Agents SDK

OpenAI Agents SDK 提供 Agent、Runner、Tool、Handoff、Guardrail、Session 和 Trace。官方将编排分成两类：由 LLM 决定下一步，或由代码显式决定执行顺序，两者可以混合。

内置 Trace 可记录：

- LLM Generation。
- Tool Call。
- Handoff。
- Guardrail。
- 自定义事件。

官方资料：[Agent Orchestration](https://openai.github.io/openai-agents-python/multi_agent/)、[Agents](https://openai.github.io/openai-agents-python/agents/)、[Tracing](https://openai.github.io/openai-agents-python/tracing/)。

**最值得吸收**：

- `AgentRunner` 统一封装 Agent 调用和结构化结果。
- Manager-as-tools 与 Handoff 两种协作方式分开。
- Guardrail 在工具副作用前执行。
- Trace/Span 为 Agent、Tool、Handoff 和自定义质量门提供统一事件模型。

**不宜单独作为 Workflow Engine**：

- Agents SDK 重点是 Agent Runtime 和 Trace，不等同于 Durable Workflow Runtime。
- 若需要进程崩溃恢复、长时间暂停和可靠副作用，仍需外接 LangGraph、Temporal 或自有 Checkpoint 层。

## 横向选择

| 能力 | LangGraph | Microsoft Agent Framework | Temporal | OpenAI Agents SDK |
| --- | --- | --- | --- | --- |
| 显式图执行 | 强 | 强 | 强 | 由应用代码负责 |
| Checkpoint / Resume | 强 | 强 | 最强 | 非核心能力 |
| Human-in-the-loop | 内置 Interrupt | 内置 Request/Response | Signal/Update 实现 | 由应用编排 |
| 并行波次 | Superstep | Superstep | Child Workflow / Activity | 由应用代码负责 |
| 副作用可靠性 | 需要节点幂等 | 需要 Executor 处理 | Activity 原生支持 | 由应用负责 |
| Agent/Handoff 抽象 | 可组合 | 内置 | 不负责 | 强 |
| Trace | 通常配 LangSmith | Telemetry/Middleware | Event History | 内置 Trace/Span |
| 本地最小引入成本 | 中 | 中 | 高 | 低 |
| 与本框架最接近 | 状态与恢复 | 类型化 Executor | 可靠副作用 | Agent 调用接口 |

## 完整 Engine 的候选架构

如果未来满足升级条件，不直接选择一个框架替换现有实现，而采用「控制内核 + 副作用执行器 + 事件存储」三层：

```text
CLI / API
    ↓
Workflow Runtime
    ├── 加载 Workflow Definition
    ├── 调用 workflow_control.py 作确定性决策
    ├── 持久化 Run / Task / Event / Artifact
    └── 调度 Executor
            ├── Agent Executor
            ├── Worktree Executor
            ├── Review Executor
            ├── Verify Executor
            └── Git Merge Executor
```

### 控制内核

继续复用 `workflow_control.py`，只接收可序列化事实并返回决策：

- `waves()`。
- `dispatchable()`。
- `apply_event()`。
- `recover()`。

禁止控制内核直接调用模型、Git、文件系统命令或网络。

### 副作用执行器

每种外部动作定义统一接口：

```python
class Executor(Protocol):
    def execute(self, command: Command, context: RunContext) -> Result:
        ...
```

`Result` 至少包含：

- `status`。
- `evidence`。
- `artifacts`。
- `started_at` / `finished_at`。
- `attempt`。
- `idempotency_key`。
- `error_type` / `error_message`。

### 事件存储

第一版使用 SQLite，不继续把 `tasks.md` 扩成数据库：

- `workflow_runs`：运行实例、Workflow 版本、状态和恢复游标。
- `task_runs`：任务、档位、状态、attempt 和 Executor。
- `events`：只追加的状态转换与外部事实。
- `artifacts`：commit、worktree、Review 报告、Verify 报告和日志路径。
- `approvals`：人工审批请求、决定和理由。

`tasks.md` 保留为人类可读计划，SQLite 是运行状态真相源。状态变化后可以回写 Markdown 展示，但不能双向任意修改。

### 质量门证据

不允许调用方只发送 `quality_passed`：

- Review Executor 必须返回结构化报告路径、结论和 finding 摘要。
- Verify Executor 必须返回 `.verify/report.json`、检查项和退出码。
- Merge Executor 在执行前验证 Review/Verify Artifact 属于同一 task、attempt 和 commit。
- 所有证据绑定 `run_id + task_id + attempt + commit_sha`。

### 暂停与恢复

参考 LangGraph Interrupt 和 Temporal Signal：

- 人工批准点写入 `WAITING_APPROVAL`，不把任务标成失败或「需人工」后退出。
- CLI 提供 `approve`、`reject`、`retry`、`cancel` 和 `resume`。
- 每次恢复读取事件历史与最后 Checkpoint，不扫描聊天记录猜状态。
- 所有外部副作用使用幂等键，恢复时先查已有 Artifact，再决定是否重跑。

## 当前推荐：轻量运行证据层

当前只补 3 个小闭环。

### 质量门证据校验

控制流不能只接受没有证据的 `quality_passed`。至少保存：

```json
{
    "task_id": 2,
    "attempt": 1,
    "commit_sha": "abc123",
    "review_report": "artifacts/review-2-1.md",
    "verify_report": "artifacts/verify-2-1.json",
    "review_status": "PASS",
    "verify_status": "PASS"
}
```

合并前校验 Review、Verify、task、attempt 和 commit 是否对应同一次执行。

### 统一运行目录

暂不引入 SQLite，先使用项目内运行目录：

```text
.agentic/runs/<run-id>/
├── run.json
├── events.jsonl
├── tasks/
│   └── 1.json
└── artifacts/
    ├── review-1.md
    └── verify-1.json
```

`tasks.md` 继续作为人类可读计划，运行目录保存机器事实。第一版只允许运行时单向回写展示状态，避免形成两个可任意修改的状态源。

### 薄 Runner

第一版 Runner 只需要：

```text
读取 tasks.md
→ 调用 workflow_control.py
→ 输出或执行一个动作
→ 保存结果与证据
→ 再调用 workflow_control.py
```

它不需要负责通用 Agent 插件、跨机器执行或 Web UI。即使暂时仍由宿主 Agent 执行副作用，Runner 也可以先负责校验证据并阻止错误合并。

## 完整 Engine 的实施顺序

### 第 1 阶段：本地 Runner

- 新增 `workflow_runner.py`。
- 使用 SQLite 保存 Run、Task、Event 和 Artifact。
- 只实现单任务串行执行。
- 接入 Verify Executor，证明质量证据合同可行。

### 第 2 阶段：Git 与恢复

- 接入 Worktree Executor 和 Merge Executor。
- 增加幂等键、超时、取消和进程崩溃恢复。
- 用进程中断测试证明恢复不会重复提交和重复合并。

### 第 3 阶段：Agent 与 Review

- 定义 Claude Code、Codex 的 Agent Adapter。
- 将 Agent 输出转换为统一 `Result`。
- 接入 Review Executor，并校验证据与 commit 绑定。

### 第 4 阶段：并行与人工门

- 使用现有 DAG wave 并行调度。
- 增加 `WAITING_APPROVAL` 和 CLI 恢复命令。
- 补限流、token 预算和取消传播。

## Stop/Continue 判断

**停止建设完整 Agentic Workflow Engine；可以继续补轻量运行证据层。**

当前不引入 Temporal Server，不建设 Worker 集群、Web UI 和跨机器调度，也不把整个框架重写成 LangGraph。

只有出现以下任一信号，再评估建设完整 Engine：

1. 经常出现会话中断后无法恢复。
2. 出现重复提交或重复合并。
3. Review/Verify 被跳过，或报告对应了错误的 commit。
4. 单次任务经常运行超过 1 小时。
5. 需要无人值守、跨机器运行或强审计。

这些信号出现前，现有「Skill 编排 + 确定性控制内核」已经足够。最有价值的补强是证据绑定，不是平台化。
