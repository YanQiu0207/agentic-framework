# Feature：确定性工作流控制流

**作者**：Codex  
**日期**：2026-07-12  
**状态**：Archived

---

## 1. 背景（Background）

### 1.1 问题描述

- `workflow-code-generation` 已定义依赖分波、失败隔离、下游阻塞、有限重试和中断恢复规则，但这些规则主要存在于 Prompt 和执行手册中。
- 当前没有可执行的控制流内核，无法通过零 Token 自动化测试证明实际编排遵守上述规则。
- 修改 Prompt 或执行手册后，可能出现依赖任务提前执行、失败影响无关任务、下游错误执行、无限重试或重复执行已完成任务等回归。

### 1.2 现状分析

- `lint_task_deps.py` 已提供 `tasks.md` 字段、依赖和状态解析，以及悬空依赖、循环依赖和潜在并行冲突检查。
- `delegated-execution-guide.md` 要求主 Agent 根据 `depends_on` 构建波次，并根据执行结果更新 `tasks.md`，但没有对应的 Python 实现。
- `check_delivery.py` 只在交付阶段检查任务是否处于合法终态，不参与调度和状态转换。
- `test_lint_task_deps.py` 只覆盖解析和字段校验，没有覆盖控制流。

### 1.3 主要使用场景

- 标准代码生成流程根据 `tasks.md` 计算可执行波次。
- Agent、Review 或 Verify 失败后，确定是否重试、转人工或阻塞下游。
- 同一波中的任务部分失败时，保持无关任务继续执行。
- 会话中断后，根据 `tasks.md` 状态和外部提供的合并事实计算恢复动作。
- 框架升级或 Prompt 调整后，通过固定 case 回归关键控制流。

## 2. 目标（Goals）

- 将确定性的调度和状态转换规则下沉到 Python 控制流内核，实际工作流必须调用该内核。
- 保持 `tasks.md` 为进度唯一真相源，相同输入始终产生相同的波次、状态和恢复动作。
- 无需调用真实模型即可自动验证关键控制流。

### 2.1 非目标（Non-Goals）

- 不封装真实 Agent、Review、Verify、Git 或 worktree 操作。
- 不引入数据库、服务端组件或通用 DAG 框架。
- 不通过 LLM Judge 判断确定性状态转换。
- 不在首版自动执行 `git branch --merged` 或发现 worktree，只消费编排层提供的事实。
- 不保证 Agent 生成代码的质量，该问题继续由测试、Review 和 Verify 处理。

## 3. 需求细化（Requirements）

### 3.1 功能性需求

- 解析现有 `tasks.md`，复用已有任务 ID、依赖和状态契约。
- 按 `depends_on` 构建稳定、可重复的拓扑波次。
- 根据任务当前状态和前置依赖状态返回可调度任务。
- 接收任务执行结果，执行合法的状态转换并记录失败原因。
- 同波单任务失败不得改变无依赖任务的执行结果。
- 上游转为「需人工」后，所有依赖后代必须转为「阻塞」。
- 修复次数达到上限后停止重试，并将任务转为「需人工」。
- 恢复时跳过已完成任务；根据外部提供的已合并任务集合处理「进行中」和「阻塞」任务。
- 精准更新 `tasks.md` 的状态和原因字段，不重排或全量重写文档。
- 实际工作流入口必须调用控制流内核，不得保留另一套手工波次和状态规则。

### 3.2 非功能性需求

- Python 3，UTF-8 编码，使用标准库实现。
- 单元测试不访问网络、不调用模型、不创建 worktree。
- 保持现有 `tasks.md` 格式向后兼容，包括旧 `依赖` 字段的解析兼容。
- 状态机函数应为纯函数或显式输入输出，方便 Mock 和重复执行。
- 相同输入多次运行必须得到相同结果；同波任务按任务 ID 稳定排序。
- 首版只覆盖当前工作流需要的状态和事件，不预建扩展框架。

## 4. 设计方案（Design）
### 4.1 方案概览

采用「副作用编排层 + 确定性控制流内核」两层结构：

```text
编排层
Agent / Workflow / Git / worktree
        │
        │ 提供任务结果和外部事实
        ▼
确定性控制流内核
解析 → 分波 → 状态转换 → 阻塞传播 → 恢复决策
        │
        ▼
tasks.md
```

- 编排层负责调用 Agent、Review、Verify、Git 和 worktree，并将执行结果及外部事实传给控制流内核。
- 控制流内核负责生成波次、判断可调度任务、计算状态转换、传播阻塞和生成恢复决策，不直接执行外部副作用。
- `tasks.md` 继续作为进度唯一真相源；内核精准更新状态和原因，不全量重排文档。
- 依赖方向保持单向：编排层依赖控制流内核，控制流内核复用现有 `tasks.md` 解析能力。
- 该方案优先保证确定性和可测试性，代价是编排层仍需负责收集 Git、worktree 和 Agent 的真实执行结果。
### 4.2 组件设计（Component Design）

#### 4.2.1 核心模块设计

新增 `workflow_control.py`，使用纯函数实现控制流，不建立 `WorkflowEngine` 类：

| 组件 | 职责 |
| --- | --- |
| `build_waves()` | 对任务 DAG 做稳定拓扑分层 |
| `dispatchable_tasks()` | 根据状态和依赖返回当前可调度任务 |
| `apply_event()` | 校验当前状态并处理 dispatch、质量门、合并、失败和解阻事件 |
| `propagate_blocked()` | 将未完成上游造成的阻塞递归传播到下游 |
| `plan_recovery()` | 根据任务状态和外部合并事实生成恢复动作 |
| `update_task_state()` | 精准修改 `tasks.md` 中单个任务的状态与原因 |

`workflow_control.py` 复用 `lint_task_deps.py` 的任务解析能力。状态计算与文本写回分离，调用方可以先检查决策，再执行持久化。

#### 4.2.2 接口设计

```python
@dataclass(frozen=True)
class TaskDecision:
    task_id: int
    state: str
    action: str
    reason: str = ""
    attempts: int = 0
    control_stage: str = ""
```

公开函数只接收普通映射、集合和不可变数据类，返回新决策，不执行 Agent、Git 或 worktree 操作。非法任务、未知结果、循环依赖和非法状态抛出 `ValueError`。

除 `start`、`quality_passed`、`merge_success`、`merge_failure`、`failure`、`unblock` 六个初版事件外，`apply_event()` 还接受两个人工直达事件，用于解决「需人工」原为零出边吸收态、人工恢复链无法执行的问题：

- `manual`：仅接受 `("进行中", "running", "manual")`，转换为 `TaskDecision(task_id, "需人工", "manual", reason, attempts, "manual")`；`reason` 为空拒绝。不递增 `attempts`，供 `workflow-verification` 门禁自身出错、owner 子 agent 崩溃或超时、复审轮次仍 `NEEDS_CHANGES`、owner 内部修复轮次已耗尽等场景直接标记「需人工」，不占用状态机自身的重试预算。
- `manual_resolved`：仅接受 `("需人工", "manual", "manual_resolved")`，转换为 `TaskDecision(task_id, "完成", "complete", reason, attempts, "completed")`；`reason` 可选。供人工排查「需人工」任务、修复并合并其分支后闭环使用。

`plan_recovery()` 对「需人工」任务按其是否已出现在外部提供的 `merged_task_ids` 中分别返回 `complete`（已合并，执行时对应 `manual_resolved`）或 `manual`（未合并，提示人工排查），不再落入通用的 `wait` 分支给出「前置依赖未完成」的误导性原因。`plan_recovery()` 同时拒绝与持久化状态矛盾的外部合并事实：任务状态为 `未开始` 或 `阻塞` 时结构性不可能产生可合并的分支，若其 ID 出现在 `merged_task_ids` 中则立即失败。

#### 4.2.3 数据模型

继续使用 `tasks.md` 的现有字段：

- 任务 ID：`### 任务 N`。
- 依赖：`depends_on`，兼容旧字段 `依赖`。
- 状态：`未开始`、`进行中`、`完成`、`需人工`、`阻塞`。
- 原因：状态行附注或独立 `原因` 字段，禁止包含 CR / LF。
- 修复次数：`attempts` 字段；缺失时按 0 兼容读取，首次写回时自动补齐。
- 控制阶段：`control_stage` 字段；记录 `pending`、`running`、`quality_passed`、`completed`、`manual` 或 `blocked`，防止跳过质量门直接合并。

内存模型沿用 `lint_task_deps.parse_tasks()` 返回的任务映射，不新增持久化格式。

#### 4.2.4 并发模型

N/A——控制流内核不创建线程或异步任务。它只计算波次和决策；波内并行由外部 Workflow 负责。

#### 4.2.5 错误处理

- 悬空依赖、循环依赖、重复任务 ID 和未知状态属于输入错误，立即失败。
- 单任务执行失败属于业务结果，不抛异常；未耗尽重试时返回「重试」，耗尽后返回「需人工」。
- 上游「需人工」或未满足恢复条件时，下游返回「阻塞」及上游原因。
- 状态写回找不到目标任务或状态字段时立即失败，禁止静默追加到错误位置。

### 4.3 核心逻辑实现

1. 读取 `tasks.md`，通过现有解析器获得任务 ID、依赖和状态。
2. `build_waves()` 使用 Kahn 拓扑排序：每轮选出入度为 0 的任务，按任务 ID 排序形成一波；无法消费全部任务时报告循环依赖。
3. 每波执行前调用 `dispatchable_tasks()`，只允许「未开始」且全部依赖为「完成」的任务进入调度。
4. 编排层通过 `start` 事件将任务标记为「进行中」，执行 Agent、Review 和 Verify。
5. 启动事件再次校验全部依赖为「完成」。质量门通过持久化 `control_stage=quality_passed`，状态保持「进行中」；仅该阶段接受 `merge_success` 并转为「完成」，`merge_failure` 转为「需人工」。失败事件原子递增并持久化 `attempts`；超过最大修复次数后转为「需人工」。
6. 每波收口后调用 `propagate_blocked()`，将依赖「需人工」或「阻塞」任务的后代标记为「阻塞」，同波无依赖任务不受影响。
7. 中断恢复时，编排层先收集 `merged_task_ids`，再调用 `plan_recovery()`：已完成任务跳过；进行中且已合并的任务补标完成；未合并的进行中任务重新检查；上游已完成的阻塞任务解除阻塞。
8. 所有状态变更先由 `apply_event()` 校验当前状态，再通过保留原换行风格及文件权限，通过临时文件 + `os.replace()` 原子写回状态、原因、`attempts` 和 `control_stage`；不提供绕过校验的通用 `set-state` CLI。
9. `delegated-execution-guide.md` 和 `SKILL.md` 改为要求逐波调用内核，避免一次性预构建全部波次后忽略前波失败。

### 4.4 方案优劣分析

**优点**：

- 确定性规则可以零 Token 单元测试。
- 实际编排和测试共用一套决策逻辑，避免两套规则漂移。
- 保持对不同 CLI 的兼容，不绑定 Agent SDK。
- 修改范围集中，继续复用现有 `tasks.md`。

**局限性**：

- 首版不会自动操作 Git 或 worktree，编排层必须准确提供外部事实。
- Prompt 是否实际调用脚本仍依赖客户端执行纪律；本期通过 SKILL 和手册建立强制入口，不建设 Hook。
- Markdown 是面向人的状态文件，不适合高并发写入；本框架按波次串行写回，首版不处理多写者竞争。

## 5. 备选方案（Alternatives Considered）

- **只补 Mock 测试模型**：实现最少，但不能证明实际 Workflow 遵守规则，因此放弃。
- **构建完整 Python 编排器**：可以直接调用 Git 和 Agent，但会绑定执行平台并显著扩大范围，因此首版不做。
- **引入通用 DAG 库**：当前图规模小，标准库拓扑排序已足够，引入依赖没有收益。
- **将状态迁移到 JSON 或数据库**：机器处理更方便，但会破坏 `tasks.md` 唯一真相源并引入同步问题，因此不采用。

## 6. 业界调研（Industry Research）

本期不依赖外部框架。采用的 Kahn 拓扑排序和纯函数状态转换属于稳定基础算法；具体正确性以本仓库契约和固定 case 为准。

## 7. 测试计划（Test Plan）

### 7.1 单元测试

至少覆盖：

1. 依赖分波及同波稳定排序；
2. 单任务失败不影响同波无关任务；
3. 上游需人工后递归阻塞下游；
4. 修复次数耗尽后停止重试；
5. 中断恢复跳过已完成任务并处理已合并任务；
6. 循环依赖、自依赖、缺少 `depends_on`、非法事件和缺失状态字段失败；
7. 状态文本原子更新，拒绝原因字段的 CR / LF 结构注入；
8. 同波任务串联状态写回，证明单任务失败不改变独立任务的合并结果；
9. 修复次数和控制阶段写回后重新解析，证明中断后不会重置；
10. 未过质量门禁止合并、依赖未完成禁止启动；
11. 原子写回保持原文件权限和 CRLF 换行风格；
12. 缺失「状态」字段时 `_states()` 立即失败，而非静默跳过或返回部分结果；
13. 100 个任务的线性依赖链能在普通本地环境快速构建出正确的稳定拓扑波次，验证 `build_waves()` 在接近实际项目规模时仍保持正确性与性能。

### 7.2 集成测试

- 使用临时 `tasks.md` 串联解析、波次、结果应用、阻塞传播和状态写回。
- 运行现有 `test_lint_task_deps.py`，确认解析兼容性没有回归。
- 运行仓库全部 `test_*.py`。

### 7.3 性能测试

N/A——任务图规模小，控制流不在运行时性能关键路径。单元测试验证 100 个任务可在普通本地环境快速完成即可，不设置独立性能门槛。

## 8. 可观测性与运维（Observability & Operations）

### 8.1 可观测性

- 控制流函数不写日志，由 CLI 输出波次、决策和错误。
- 错误信息必须包含任务 ID、原状态、目标动作和原因。
- 不新增监控指标或告警。

### 8.2 配置参数

- 最大修复次数由调用方显式传入，默认值与现有工作流规则保持为 2。
- 不新增配置文件或环境变量。

### 8.3 运维接口

提供 Python CLI 子命令或参数，用于从 `tasks.md` 输出波次和恢复计划；具体接口以实现阶段保持最小为准。

### 8.4 运维注意事项

- 不改变 `tasks.md` 格式，无数据迁移。
- 回滚时删除控制流模块并恢复 SKILL 与手册入口即可。
- 状态文件写入失败时保留原文件，不输出部分更新结果。

## 9. Changelog

| 日期 | 变更内容 | 作者 |
| --- | --- | --- |
| 2026-07-12 | 创建需求与设计，确定两层控制流方案 | Codex |
| 2026-07-12 | 完成实现、两轮 Review 修复和机器验证，归档规格 | Codex |
| 2026-07-12 | 写锁 PR 双侧 Review 发现状态机死锁与解析健壮性问题，新增 `manual` / `manual_resolved` 事件、`control_stage` 字段接口定义、恢复矛盾校验，标准档 review 通过后重新归档 | Claude |

## 10. 参考资料（References）

- `skills/workflow-code-generation/SKILL.md`
- `skills/workflow-code-generation/reference/delegated-execution-guide.md`
- `skills/workflow-code-generation/scripts/lint_task_deps.py`
- `docs/10-harness-engineering-practices.md`
