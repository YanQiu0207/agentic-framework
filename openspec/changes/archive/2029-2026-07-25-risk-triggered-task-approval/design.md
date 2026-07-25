# Design：Production 逐 Task 批准改为风险触发升级门

**变更**：2029-risk-triggered-task-approval

**状态**：Draft

---

## 1. 范围

三处改动，互相独立但不可裁剪其中的 §3（见 `proposal.md` §5.4 权衡二）：

1. `skills/opsx-code-generation/SKILL.md`：执行节奏与升级条件（策略层）。
2. `scripts/validate_change.py`：`delivery` 阶段批准证据校验（确定性层）。
3. `skills/opsx-code-generation/reference/task_planning_guide.md`：条件预标注与波次产出要求（规划层）。

不改动：`workflow_control.py`、`runtime_*`、`verify.py`、`workflow-code-review`、任何 Agent 定义。

## 2. 升级条件的判定归属

条件分两类，判定主体不同：

| 类别 | 条件 ID | 判定时机 | 判定主体 | 写入时机 |
| --- | --- | --- | --- | --- |
| 预标注 | `scope-change`、`irreversible` | 规划阶段 | 规划期 LLM，用户在 Tasks 批准时复核 | 创建 `tasks.md` 时 |
| 动态 | `gate-failure`、`assumption-broken`、`user-requested` | 执行期 | 机器门（`gate-failure`）或 Agent（其余） | 命中时追加 |
| 模式 | `per-task-mode` | Tasks 批准时 | 用户 | `tasks.md` 头部 |

`gate-failure` 是唯一完全由机器判定的条件：Verification 非零退出、Review 报告 `p0_count` 或 `p1_count` 非零、re-review 轮次达到上限 2（`framework-unification.md:187`）任一成立即命中。其余条件依赖语义判断，因此 §4 的校验只验证「声明了条件就必须有批准记录」，不验证「该不该声明」——后者由 Plan 门禁的 Task Review 合同检查与用户 Tasks 批准共同拦截。

## 3. `irreversible` 与 strict Review 清单同源

`SKILL.md:108` 已定义高风险清单：安全、权限、数据迁移、并发、分布式、生产关键路径、公共 API、大范围重构。本变更不新建风险清单，`irreversible` 直接引用它，并补充「删除性操作、发布或外部副作用」——这三项在原清单中未显式列出但同属不可逆范畴。

结果是同一份定义驱动两个后果：命中即 `review_profile: strict`（既有行为，不变），且强制暂停等待用户决定（新增）。规划期漏标时两个后果同时失效，这使漏标更容易在 Plan 门禁的 Task Review 合同检查中暴露，而不是只丢掉暂停。

## 4. 校验器改动

### 4.1 位置

扩展 `delivery` 阶段既有的任务完成与执行记录检查（`validate_change.py:1484`），不新增阶段、不新增第二套状态。

### 4.2 元数据格式

Task 元数据新增两行（均可选）：

```text
- Escalation: irreversible, scope-change
- Approval: granted (irreversible, scope-change)
```

`Escalation` 声明命中的条件，逗号分隔；`Approval` 取值 `granted` 或 `pending`，括号内条件集合必须与 `Escalation` 一致。`tasks.md` 头部的模式声明：

```text
> 批准模式：per-task
```

缺省为 `risk-triggered`。

### 4.3 规则

新增三条规则，均失败关闭：

| 规则 | 条件 | 报错内容 |
| --- | --- | --- |
| OPSX0xx-A | Task 为 Completed 且有 `Escalation`，但缺 `Approval` 或为 `pending` | Task 编号 + 缺失的条件 ID |
| OPSX0xx-B | `Approval` 的条件集合与 `Escalation` 不一致，或含白名单外 ID | Task 编号 + 不一致的 ID |
| OPSX0xx-C | 头部声明 `per-task` 但存在 Completed Task 缺 `Approval: granted` | Task 编号 |

规则编号在实现时按 `validate_change.py` 现有序列分配。无 `Escalation` 且模式为 `risk-triggered` 的 Task 不触发任何新规则，保证既有 Change 不回归。

### 4.4 向后兼容

现存 Change（含已归档）均无 `Escalation` 与 `Approval` 字段，且无头部模式声明，落入「不触发新规则」分支。归档目录不重新校验。因此本改动对历史 Change 零影响，无需数据迁移。

## 5. 波次推进

### 5.1 为何不复用 `workflow_control.py`

该模块的 `waves` 与状态、锁、失败隔离、恢复和 Run Context 耦合在同一执行栈（`framework-unification.md:243`：DAG、waves、状态、锁、失败隔离和恢复可独立使用，但同属 Tooling 执行栈）。Production 只需要拓扑排序这一项，引入整个模块会跨越 Profile 边界，并可能被误读为 Production 获得了 worktree 与 Run 语义。

### 5.2 实现方式

在 `validate_change.py` 已解析 `tasks.md` 依赖的基础上（Plan 阶段已检查依赖与无环）输出波次分组，供 SKILL.md 执行段读取。算法与 `_kahn_waves` 一致：反复取出入度为零的任务，按编号排序保证稳定性。

Production 波次只决定「允许连续执行的范围」与「汇总报告边界」，不改变波次内任务的串行执行、各自的测试、Verification 与 Review。因此不引入并发写入风险，也不需要 worktree。

### 5.3 与升级条件的交互

波次内任一 Task 命中升级条件时，在该 Task 处暂停，而不是推迟到波次末尾。批准后继续该波次剩余任务。即：升级条件优先于波次边界。

## 6. 不确定性

- 规划期 LLM 对 `irreversible` 的识别准确率没有历史数据支撑，本变更依赖 §3 的双后果耦合与用户 Tasks 批准复核作为缓解，但无法量化漏标率。这是本变更最主要的残余风险。
- 本仓库自身使用 Tooling Profile，Production 执行段的改动无法在本仓库的日常开发中获得真实使用证据；验证只能依赖校验器单测与构造夹具。
