# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：先冻结零触发基线（Task 1），因为「未命中升级条件时行为零变化」是本 Change 唯一可机械核验的性质。状态机扩展（Task 2）与证据校验（Task 3）分开，休眠等价单独核对（Task 4）。与 change 2035 Task 7 的状态集合冲突必须显式裁决，不得默认任一方。

## 依赖关系总览

```
Task 1 (冻结零触发基线 + 裁决状态集合冲突)
   │
   └──> Task 2 (状态机扩展：等待批准与恢复)
          │
          └──> Task 3 (批准证据校验与失败关闭)
                 │
                 └──> Task 4 (零触发等价核对)
                        │
                        └──> Task 5 (规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3} → W4 = {Task 4} → W5 = {Task 5}

> 全链串行。Task 2 与 Task 3 都改 `workflow_control.py`，无法并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 2, Task 3 | 等待批准状态、转移与恢复 |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 待定 | Task 2 | 若新增状态则需同步取值集合，范围由 Task 1 裁决决定 |
| `scripts/validate_change.py` | **不改** | Task 4 | Production 零改动 |
| `scripts/` 测试目录 | 新增 | Task 1, Task 3, Task 4 | 零触发基线与批准证据用例 |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 修改 | Task 5 | 状态与恢复路径 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 5 | §6.3 同步 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §3 默认自主性约束 | Task 1, Task 4 | 零触发基线与等价核对 |
| `proposal.md` §6.1 状态方案 | Task 1, Task 2 | 冲突裁决与状态机扩展 |
| `proposal.md` §6.3 未裁决项 | Task 1 | 升级条件判定归属 |
| `proposal.md` §7 验收标准 2-5 | Task 3 | 词表一致与失败关闭 |
| `proposal.md` §6.2 休眠证明 | Task 4 | 逐字节等价 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `workflow-control` | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | 完成 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 完成 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 已核对（2026-07-26）。其一：与 2035 Task 7「不新增第六个规范值」的冲突按 §6.1.1 状态合同化解——`待批准` 是执行期内部态，持久化映射为规范态 `需人工`（原因前缀 `待批准 <条件>`）加 `control_stage: awaiting_approval`；`TASK_STATES` 与 `parse_state` 不含 `待批准`，读侧恒 5 态，有测试断言（`test_read_side_states_stay_five`）。2035 的放宽前提、golden 基线与降级等价均基于同一套 5 态读侧语义，不受影响。其二：§2.2「执行段不再逐 Task 等待人工批准」原文保留并补记——这是默认行为，声明升级条件后的待批准暂停是风险触发的例外；零触发等价证据见 `zero_trigger_before.json`／`zero_trigger_after.json`（波次／恢复／阻塞／可派发规范化 JSON 逐字节相同）。

## 实际 Diff 核对

- `git diff --stat` 要点：`skills/workflow-code-generation/scripts/workflow_control.py`（+约 230 行：词表与字段正则抄录、两个新转移与新事件、批准门、恢复分支）、`scripts/test_workflow_control.py`（+ApprovalGateVocabularyTest／EscalateTransitionTest／ApprovalGateTest 共 20 用例）、两份长期规格同步；`scripts/validate_change.py` 与 `lint_task_deps.py` 未改（`git diff --name-only` 为空，`TASK_STATES` 未动）。
- Task 1 裁决记录：①新增状态 vs 复用 `需人工`——采纳新增执行期内部态（复用会把「失败需人工」与「等待批准」压进同一恢复分支，`plan_recovery` 无法区分）；②与 2035 Task 7 的冲突按 §6.1.1 化解（见知识冲突节其一）；③升级条件判定归属——沿用「人声明、机器验证」，状态机不承担语义判断（§2.2 第 4 条）；④`plan_recovery` 现有分支核对后新增 `await_approval` 独立分支，不与既有分支冲突。
- Task 4 等价核对：12 份文档（11 个活跃 Change＋1 份五态合成文档）的波次、恢复计划、阻塞传播、可派发集合前后规范化 JSON 逐字节相同；首次比对曾误报差异，查明为比对脚本自身的 list/tuple 序列化差异，规范化后相同，非行为差异。
- `propagate_blocked` 对待批准的结论：与失败需人工一样阻塞下游（暂停的任务不得放行下游），有用例（`test_awaiting_approval_blocks_descendants`）。
- 等价方法的可复用性记录（供 change 2042 引用）：冻结「全部活跃 Change＋五态合成文档」的 `waves`／`dispatchable`／`plan_recovery`／`propagate_blocked` 输出为规范化 JSON，改动后重跑逐字节比对；该方法依赖「读路径输出是行为的充分投影」，对写回内容的覆盖由 `update_task_state` 的既有用例与新转移用例补足。

---

### 任务 1：[x] 冻结零触发基线并裁决状态集合冲突

- 状态: 完成
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §3 默认自主性约束、§6.1 状态方案、§6.3 未裁决项
- 文件：无（只读清点与裁决记录，产出写入本 Change）
- context_files: `skills/workflow-code-generation/scripts/workflow_control.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`scripts/validate_change.py`、`openspec/changes/2035-common-task-ast/tasks.md`
- artifacts: 零触发行为基线、状态集合冲突裁决记录、升级条件判定归属裁决记录
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 对全部现有测试夹具与活跃 Change 跑 `workflow_control.py`，冻结波次、状态转移序列与写回内容为基线。
    - [x] 基线可重复：连续两次生成输出逐字节相同。
    - [x] 逐项抄录 Production 的 `ESCALATION_CONDITIONS`（`validate_change.py:102-111`）与 `APPROVAL_MODES`（`:113`），作为本 Change 的词表来源，不自行增删。
    - [x] 裁决新增状态 vs 复用 `需人工`，写明理由与被拒方案的具体缺陷。
    - [x] **若裁决为新增状态**：与 change 2035 Task 7「不新增第六个规范值」的冲突逐条展示双方原文，给出裁决与影响范围（是否需改 `lint_task_deps.py` 的 `TASK_STATES`）。
    - [x] 裁决升级条件的判定归属：人声明加机器验证，还是脚本自动识别。附理由，并对照 §2.2 第 4 条的职责边界。
    - [x] 记录 `plan_recovery`（`workflow_control.py:507`）现有的恢复分支，确认新状态的恢复路径不与既有分支冲突。

### 任务 2：[x] 状态机扩展：等待批准与恢复路径

- 状态: 完成
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 状态方案
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`
- context_files: `skills/workflow-code-generation/scripts/lint_task_deps.py`、Task 1 的裁决记录
- artifacts: `skills/workflow-code-generation/scripts/workflow_control.py`
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 按 Task 1 的裁决实现状态表达，不擅自改用另一方案。
    - [x] 「等待批准」的进入转移与恢复转移各有独立处理函数，与 `_handle_manual`／`_handle_manual_resolved`（`:368`、`:374`）的语义明确区分。
    - [x] `plan_recovery` 能区分「失败需人工」与「等待批准」，恢复动作不同，有用例。
    - [x] `propagate_blocked`（`:437`）对等待批准状态的传播行为明确：是否阻塞下游，有用例与结论。
    - [x] `dispatchable_tasks`（`:310`）不把等待批准的任务派发出去。
    - [x] 若 Task 1 裁决需改 `TASK_STATES`，同步改动并说明与 change 2035 Task 7 的先后关系。
    - [x] 未命中升级条件的执行路径代码未被修改；改动集中在新分支内。

### 任务 3：[x] 批准证据校验与失败关闭

- 状态: 完成
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §7 验收标准 2-5
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/` 测试目录
- context_files: `scripts/validate_change.py`、Task 1 的词表抄录
- artifacts: 批准证据校验实现、跨轨读取一致性用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 升级条件集合与 `validate_change.py:102-111` 逐项一致，用测试断言两侧集合相等。
    - [x] 批准模式集合与 `:113` 一致，同样有相等断言。
    - [x] 批准证据字段形式与 Production 一致；同一份 `tasks.md` 两轨读取结果相同，有用例。
    - [x] 声明缺失、`pending`、条件不一致、非法 ID 时失败关闭，逐项有用例。
    - [x] 缩进式、列表式或错位的声明失败关闭，与 OPSX053 的处理方式对齐，有用例。
    - [x] 不存在静默跳过分支，用检索证明。
    - [x] 本任务不实现 Review 档位联动（OPSX055 类双向绑定），确认未越界。

### 任务 4：[x] 零触发等价核对

- 状态: 完成
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §6.2 休眠证明、§3 默认自主性约束
- 文件：`scripts/` 测试目录
- context_files: Task 1 的零触发基线、`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/validate_change.py`
- artifacts: 零触发等价结论、状态翻转清单、`validate_change.py` 零改动确认
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] Task 1 的零触发基线重跑，波次、状态转移序列与写回内容逐字节相同。
    - [x] 出现任何差异时逐条记录并判定是缺陷还是基线本身有误，不静默接受。
    - [x] Native Delivery 默认路径未变为逐 Task 等待，有用例。
    - [x] `scripts/validate_change.py` 逐字节未改动。
    - [x] 该等价方法的可复用性记录在案，供 change 2042（降级等价判据实现）引用。
    - [x] `python -m pytest scripts -q` 全量通过，通过／跳过数与基线对照记录在案。

### 任务 5：[x] 长期规格同步

- 状态: 完成
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/framework/workflow-control/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2039-tooling-approval-gate/proposal.md`、Task 1 的裁决记录
- artifacts: 两份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] `workflow-control/overview.md` 记录等待批准状态、进入与恢复转移、对下游的传播行为。
    - [x] `framework-unification.md` §6.3 记录 Tooling 的风险触发升级，并明确默认路径不变。
    - [x] §2.2「执行段不再逐 Task 等待人工批准」不删除；补记这是默认行为，风险触发是例外。
    - [x] 记录这是 §3.2 条件 3 的**部分**举证，明确其余强制规则仍未举证。
    - [x] 若改动了 `TASK_STATES`，同步记录并说明与 change 2035 的关系。
    - [x] `python scripts/markdown_links.py openspec` 退出码 0。
    - [x] 按 md-zh 规范自检中文排版。
