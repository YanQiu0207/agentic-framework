# Proposal：Tooling 引入风险触发的升级与批准门

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：tooling-approval-gate
**状态**：Draft

---

## 1. 问题

Tooling 的执行引擎完全没有审批与升级概念。

实测：

```
grep -ci "approval\|escalation" skills/workflow-code-generation/scripts/workflow_control.py  →  0
```

`workflow_control.py` 有完整的任务状态机、DAG 波次、写锁、失败隔离与恢复，但没有任何一个���态或转移与「需要人工批准」有关。任务只有 `未开始`、`进行中`、`完成`、`需人工`、`阻塞` 五态，其中 `需人工` 是失败态的一种表达（配合 `NEEDS_REASON` 要求原因），不是「等待批准」。

Production 侧则有成套实现：

| 元素 | 内容 | 出处 |
| --- | --- | --- |
| `ESCALATION_RE` | 升级声明字段 | `scripts/validate_change.py:40` |
| `APPROVAL_RE` | 批准证据字段 | `:44` |
| `APPROVAL_MODE_RE` | 批准模式字段 | `:48` |
| `ESCALATION_CONDITIONS` | `scope-change`、`irreversible`、`gate-failure`、`assumption-broken`、`user-requested`、`per-task-mode` | `:102-111` |
| `APPROVAL_MODES` | `risk-triggered`、`per-task` | `:113` |
| OPSX053 / OPSX055 | 错位声明失败关闭、`irreversible` 与 `strict` 双向绑定 | `:186-188`（规格描述） |

## 2. 为什么这是收敛的必要条件

`framework-unification.md` §3.2 的重新评估条件 3（由 change 2036 引入）要求：Production 现有的强制规则在收敛后逐条仍可被机器门禁强制。

审批是 §5.3 的强制规则之一。只要 Tooling 的状态机不能承载「因风险暂停并记录批准证据」这个转移，条件 3 就无法举证，门层合并无从谈起。

换句话说：**这不是给 Tooling 加功能，是把 Production 的治理能力下沉到共享底座**。目标模型里 Production 是「按风险启用的治理升级策略」，而策略必须有地方可以挂。

## 3. 最大的设计约束：默认不得改变 Tooling 的自主性

`framework-unification.md` §2.2 明确记录了一条被最新决策覆盖的旧规则：

> Tooling 的 Tasks 获批后，执行段不再逐 Task 等待人工批准。

§6.1 与 §6.3 也把「前期把关、执行段自主」定为 Tooling 的定位。

因此本 Change 的实现必须做到：**未命中升级条件时，执行行为与改动前逐字节相同。** 审批能力是休眠的，只有风险触发才唤醒。这一点必须能被机械核验，不能靠代码审阅确认。

## 4. 目标

1. `workflow_control.py` 的状态机能表达「因风险条件暂停等待批准」并从批准证据恢复。
2. 升级条件集合与批准模式集合与 Production 一致，不新建第二套词表。
3. 批准证据的字段形式与 Production 一致，同一份 `tasks.md` 两轨都能读。
4. 未命中升级条件时，Tooling 的执行行为零变化。

## 5. 非目标

- **不改 Tooling 的默认路径**。Native Delivery 仍是默认，不因本 Change 变成逐 Task 等待。
- **不引入 Tooling 专属的升级条件**。条件集合直接采用 Production 的六项，不增不减。
- **不实现 Review 档位联动**。`irreversible` 与 `strict` 的双向绑定（OPSX055）属于 Review 策略，不在本 Change。
- **不改 Production**。`validate_change.py` 零改动。
- **不做批准的交互流程**。校验批准证据是否存在与是否合规，不负责去获取批准。

## 6. 设计方案

### 6.1 新增状态还是复用 `需人工`

两个选项：

| 方案 | 说明 | 取舍 |
| --- | --- | --- |
| 复用 `需人工` | 不动状态集合，用附注区分「失败需人工」与「等待批准」 | 拒绝：两者的恢复条件完全不同，混用会让 `plan_recovery` 无法区分 |
| **新增状态** | 例如 `待批准`，独立转移与恢复路径 | **采纳**，作为执行期内部态 |

采纳新增状态，但按下面的状态合同把它与读侧规范值解耦，使其不破坏 2035 的放宽前提。

### 6.1.1 状态合同：执行期内部态，不进入读侧规范集

对抗性审核指出：若 2039 新增状态，则 2035 Task 7「读侧规范值 = 5」与「状态机可进入第 6 态」会让 golden 基线、双轨对照、降级等价失去单一状态语义。这个风险真实存在，因此在提案层就把合同钉死，不留到实现时裁决。

**合同条款：**

1. `待批准` 是 `workflow_control.py` 的**执行期内部态**，用于承载「命中升级条件、等待批准证据」这一转移。
2. **读侧规范集仍是 5 个。** `lint_task_deps.py` 的 `TASK_STATES` 不新增 `待批准`；`parse_state` 不把它作为合法取值返回。
3. `待批准` **不进入公共 AST 的状态语义**。change 2035 的 AST 只读取任务头标记与 `- 状态:` 字段，对它而言 `待批准` 不是一个规范任务状态。
4. **持久化映射。** 若 `待批准` 需要写回 `tasks.md` 的 `- 状态:` 字段，写回值映射为现有规范态 `需人工`（附 `原因: 待批准 <condition>`）；若它只是执行期内存态、不写回 `- 状态:`，则读侧永远看不到它。**二选一，由实现方定，但读侧规范集不变是硬约束。**
5. **降级等价与 golden 基线不受影响。** 因为读侧规范集不变，2035 的放宽前提（Production 是 Tooling 严格超集）、双轨判定前后对照、2042 的降级等价比对，都仍基于同一套 5 态读侧语义，无需为第六态特判。
6. 与 2035 Task 7 的关系：Task 7 约束的是「读侧不新增第六个规范值」，本合同正是守住这条——第六态只活在执行层，不下沉到读侧。两者不冲突。

这份合同把审核要求的「2035/2039 联合状态合同」内联进提案，实现方照此执行即可，无需另开裁决。

### 6.2 休眠证明：零触发等价

未命中升级条件时行为零变化，用与 change 2036 降级等价判据同型的方法核验：对全部现有测试夹具跑改动前后的 `workflow_control.py`，波次、状态转移序列、写回内容逐字节比对。

这也是本 Change 对 change 2042（降级等价判据实现）的先行验证——同一套方法在更小的范围上先跑一遍。

### 6.3 未裁决项

**升级条件由谁判定。** Production 中升级条件是人在 `tasks.md` 里声明的，校验器只验证声明的自洽性。Tooling 是否沿用「人声明、机器验证」，还是让 `workflow_control.py` 自动识别某些条件（例如并行 worktree 写入本就是 Runtime 升级条件，见 §6.3 现有规则），需要裁决。倾向沿用「人声明、机器验证」——自动识别会让状态机承担语义判断，违反 §2.2 第 4 条「确定性脚本负责状态、依赖、恢复、锁和门禁，LLM 负责语义判断」。

## 7. 验收标准

1. Tooling 状态机支持「等待批准」并从合规批准证据恢复。
2. 升级条件集合与 `validate_change.py:102-111` 逐项一致，无增减。
3. 批准模式集合与 `validate_change.py:113` 一致。
4. 批准证据字段形式与 Production 一致；同一份 `tasks.md` 两轨读取结果相同，有用例。
5. 声明错位、缺失、`pending` 或条件不一致时失败关闭，与 OPSX053 的处理方式对齐。
6. **零触发等价**：未命中升级条件时，全部现有夹具的波次、状态转移序列与写回内容与改动前逐字节相同。
7. 状态合同（§6.1.1）成立：`待批准` 为执行期内部态，`TASK_STATES` 与 `parse_state` 仍只含 5 个规范值；读侧规范集零扩张，有检索与用例证明。
8. `待批准` 的持久化映射已按 §6.1.1 第 4 条裁决并实现；无论选哪种，读侧规范集不变。
9. `scripts/validate_change.py` 逐字节未改动。
10. Native Delivery 仍是默认路径，未因本 Change 变为逐 Task 等待，有用例。
11. `python -m pytest scripts -q` 全量通过。
12. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/framework/workflow-control/overview.md`：MODIFIED。新增等待批准状态与恢复路径。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§6.3 记录 Tooling 的风险触发升级；记录这是 §3.2 条件 3 的部分举证。

## 9. 参考资料

- Tooling 无审批：`skills/workflow-code-generation/scripts/workflow_control.py`，`approval`／`escalation` 出现 0 次
- Production 实现：`scripts/validate_change.py:40,44,48,102-113`
- Production 规则描述：`openspec/specs/backend/engineering/tech/framework-unification.md:186-188`（§5.3）
- Tooling 自主性定位：同文件 `:70`（§2.2）、`:226`（§6.1）、`:247-259`（§6.3）
- 脚本与 LLM 的职责边界：同文件 `:63`（§2.2 第 4 条）
- 收敛条件 3：change 2036 引入的 §3.2 重新评估条件
- 状态取值约束冲突方：`openspec/changes/2035-common-task-ast/tasks.md` Task 7
- 来源变更：`openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/`、`archive/2030-2026-07-25-approval-gate-hardening/`
