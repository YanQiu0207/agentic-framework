# Proposal：Production 逐 Task 批准改为风险触发升级门

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：risk-triggered-task-approval
**状态**：Archived

---

## 1. 问题

Production（OPSX）当前规定每个 Task 完成后无条件停止等待用户批准（`skills/opsx-code-generation/SKILL.md:97,112-117`；合同来源 `openspec/specs/backend/engineering/tech/framework-unification.md:70`）。核查后确认三个缺陷。

### 1.1 该门禁在已有证据链上不产生新的客观证据

单个 Task 到达人工批准点之前已经通过：Plan 门禁、实现、测试、`workflow-verification` 机器检查，以及独立 Reviewer 审核并产出 `verdict == "PASS"`、`p0_count == 0`、`p1_count == 0` 的 `review-report.json`（`SKILL.md:103-110`）。其后还有 Delivery 门禁、五维 strict 集成 Review 和 Archive 门禁（`openspec/specs/backend/framework/quality-gates/overview.md:19-26`）。

关键证据：标准档 `comprehensive-reviewer` 明确包含「需求/设计符合度维」，会「定位当前 Task 验收标准，逐项对照实现」，且「spec 要求了但未实现的通常至少 P1」（`agents/comprehensive-reviewer.md:15,32,38`）。因此「早期偏离检测」这一原本用于支持无条件暂停的理由，已被 Task 级 Review 覆盖大部分。人工批准的独有残余价值只剩「Review 判定符合 spec，但 spec 本身表达偏离用户真实意图」，该残余真实存在但显著小于其施加的固定成本。

作为对照，Tooling 在任务级**禁止启动 LLM Review**（`framework-unification.md:239-251` §6.3；`README.md:94`）。即 Production 任务级已有一次 Tooling 完全没有的独立审查，在此之上再叠加无条件人工批准，冗余程度高于两条链路对等时的估计。

### 1.2 Task 粒度不是业务决策点，且当前设计产生反向激励

Task 是工程拆分单位。「补测试」或「改调用点」这类 Task 暂停没有决策价值；而权限、数据迁移、公共 API、发布这类改动即使只占一个 Task 才值得人工确认。

把中断绑定到 Task 数量会推动任务趋粗——为减少中断次数而合并本应分开的改动，这与 `skills/opsx-code-generation/reference/task_planning_guide.md:36` 的「可编译优先、粒度适中」原则方向相反，并使偏离检测更晚。

同时，门禁有效性随频率衰减：一次变更被要求批准八次且多数为机械确认时，真正需要判断的那一两次也会被同等地快速放过。无差别暂停因此反向侵蚀它所服务的正确性目标。

### 1.3 该门禁没有确定性强制，也不留审计证据

`validate_change.py` 只有 `plan`、`delivery`、`archive` 三个阶段（`scripts/validate_change.py:17`），没有任何 Task 级批准校验。规格已明示「校验器只读取 Change 和证据，不维护第二套执行状态」（`quality-gates/overview.md:25`）。

暂停因此只存在于 SKILL.md 的一行文本约束。这与框架自身分工原则「确定性脚本负责状态、依赖、恢复、锁和门禁，LLM 负责语义判断」（`framework-unification.md:64`）矛盾。后果是：`tasks.md` 记录了可机器校验的 `Task Review: PASS`，却完全不记录用户批准是否发生过。Production Profile 以审计和机器证据为目标，其最高频门禁却无法被审计，也无法回答「这道门被跳过过几次」。

### 1.4 规划阶段产出的 DAG 被执行阶段丢弃

`task_planning_guide.md:76-79` 强制要求标注 `depends_on`、依赖必须无环、无依赖关系的任务须标注可并行，并要求提供依赖关系总览图。但执行逻辑是「从 `tasks.md` 中找第一个未完成任务」（`SKILL.md:68`），严格线性，依赖信息一次未被使用。Tooling 侧 `workflow_control.py waves` 消费的正是同一数据结构。

## 2. 目标

1. Production 的人工介入由**不可逆风险与范围变化**决定，不再由 Task 编号决定。Tasks 整体批准后可自主连续执行，仅命中升级条件时暂停。
2. 升级判定与用户决定进入 `tasks.md` 并由 `validate_change.py` 校验，使这道门禁成为可审计的确定性门，修复 §1.3 的矛盾。
3. 保留 Production 全部既有质量门：Task 级测试、Verification、风险分档独立 Review、Delivery 门禁、五维 strict 集成 Review、Archive 门禁一律不变。
4. 执行阶段消费规划阶段已产出的 `depends_on`，按波次推进，使 §1.4 的产出不再被丢弃。

## 3. 非目标

- 不削弱任何机器门禁或 LLM Review。Task 级独立 Review 与最终五维集成 Review 的触发条件、Profile 分档和 re-review 上限均不变。
- 不把 Production 改成 Tooling。Production 保留逐阶段批准（Requirements、Design、Tasks）、Task 级 LLM Review 和风险分档，这些是与 Tooling 的核心差异，本次不动。
- 不引入 Tooling 的 worktree、失败隔离、Run Context 或 Trust Gate 到 Production 执行段。波次只用于顺序编排，不创建 Run Envelope。
- 不在 Production 引入并行 worktree 写入。同一波次内的任务仍按顺序执行，波次仅决定批准边界与允许无中断连续执行的范围。
- 不改 `validate_change.py` 的现有三阶段语义；新增校验附加在 `plan` 与 `delivery` 已有检查上，不新建第二套执行状态机。
- 不修改 Fast-Path 行为（`SKILL.md:20-27`），其本身已无逐 Task 批准。

## 4. 验收标准

1. `SKILL.md` 步骤 5 的核心规则改为「Tasks 整体批准后自主连续执行；每个 Task 仍须通过测试、Verification 与风险分档独立 Review；仅命中升级条件时暂停等待用户决定」，并列出完整升级条件清单。
2. 升级条件命中时，`tasks.md` 对应 Task 必须记录 `- Approval: <granted|pending> (<condition-id>)`；`validate_change.py` 在 `delivery` 阶段对任一标记为 Completed 且声明了升级条件的 Task，若缺少 `Approval: granted` 记录则失败关闭，并输出该 Task 编号与条件 ID。
3. 未命中升级条件的 Task 不要求 `Approval` 记录；`plan` 与 `delivery` 阶段均不得因缺少该记录而拒绝。
4. 用户显式选择「逐 Task 批准」模式时，`tasks.md` 头部记录该模式，此时全部 Task 均要求 `Approval: granted`，校验行为回到当前语义。
5. 执行阶段按 `depends_on` 计算波次推进；同一波次内无升级条件时不中断，波次边界输出汇总报告。依赖字段缺失或成环时沿用现有 lint 失败路径，不静默退化为线性。
6. `python -m pytest scripts -q` 全量通过，且新增用例覆盖：升级条件缺批准被拒、未命中条件不要求批准、逐 Task 模式全量要求批准、条件 ID 非法值被拒。

## 5. 设计方案

### 5.1 升级条件清单

固定为六类，每类有稳定 ID 以便机器校验与后续统计：

| ID | 条件 | 判定依据 |
| --- | --- | --- |
| `scope-change` | 超出已批准范围，或需改变设计、接口、数据模型 | 实现偏离 `proposal.md` 或 `design.md` 已述范围 |
| `irreversible` | 权限、安全、数据迁移、删除性操作、发布或外部副作用 | 与 `SKILL.md:108` 高风险清单同源 |
| `gate-failure` | Verification 失败、P0/P1 未收敛或超过 re-review 上限 | 机器门与 Review 报告 |
| `assumption-broken` | 关键假设不成立、依赖阻塞或需业务取舍 | Agent 执行期发现 |
| `user-requested` | 用户明确要求在该点确认 | 会话指令 |
| `per-task-mode` | 用户选择逐 Task 批准模式 | `tasks.md` 头部声明 |

前两类须在规划阶段预标注（写入 Task 元数据），后四类可在执行期动态命中并追加记录。`irreversible` 与 `SKILL.md:108` 的 strict Review 触发清单同源：命中该条件的 Task 同时进入 strict 审核并强制暂停，二者共用一份风险定义，避免两套清单漂移。

### 5.2 批准记录与校验

`tasks.md` 的 Task 元数据新增一行：

```text
- Approval: granted (irreversible)
```

`validate_change.py` 在 `delivery` 阶段扩展现有任务完成检查：Task 标记 Completed 且携带升级条件声明时，要求存在 `Approval: granted` 且条件 ID 属于 §5.1 白名单；`pending` 或缺失一律失败关闭并指出 Task 编号与条件 ID。未声明条件的 Task 不做该检查。

这样这道门禁从纯文本约束变成有证据、可审计、可统计的确定性门，满足 §2.2。校验器仍只读取 Change 与证据，不维护执行状态，符合 `quality-gates/overview.md:25` 的既有边界。

### 5.3 波次推进

步骤 3 的「找第一个未完成任务」改为：解析 `depends_on` 计算稳定拓扑波次，按波次顺序推进；波次内任务仍逐个实现并各自完成测试、Verification 与 Review，只是无升级条件时不中断。波次边界输出汇总报告。

Production 不复用 `workflow_control.py`（它绑定 Tooling 的状态、锁与恢复语义，引入会跨越 Profile 边界）。波次计算逻辑与其 `_kahn_waves` 算法一致但独立实现于校验侧，避免 Production 依赖 Tooling 执行栈。

### 5.4 关键权衡

**权衡一：波次批准会推迟波次内的偏离检测。** 一个波次含四个任务且共享同一错误假设时，发现点从「一个任务后」变为「四个任务后」。接受理由：按规划指南的原则优先级（可编译 > 依赖拓扑 > 风险前置，`task_planning_guide.md:36`），Wave 1 承载基础与接口决策，通常很小或为单任务，最高价值的方向确认天然被保留；且 §1.1 已确认 Task 级 Review 覆盖需求符合度对照。

**权衡二：降低暂停频率会提高单次跳过的代价。** 留下的暂停恰是最不该被跳过的那些。这正是 §5.2 必须落地的原因——若升级条件同样只写在 SKILL.md，频率下降而强制强度不变，单次风险实际上升。批准证据机器化是本变更不可裁剪的部分，不能只做 §5.1 和 §5.3。

**权衡三：预标注条件依赖规划阶段判断准确。** 规划漏标 `irreversible` 会导致本应暂停的 Task 直接通过。缓解：该条件与 strict Review 清单同源，漏标同时意味着 Review 档位也标错，Plan 门禁的 Task Review 合同检查提供第二道拦截；执行期发现漏标时可动态追加。

## 6. 知识影响

- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED，§2.2 第 70 行「Production 保留逐 Task 推进」改为风险触发升级门；§5.3 强制规则补充升级条件与批准证据要求。
- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，Production 阶段门段落补充 `delivery` 阶段的批准证据校验。
- `openspec/specs/backend/framework/workflow-control/overview.md`：未变更，Production 波次不复用 Tooling 执行栈。

## 7. 参考资料

- 现场证据：`skills/opsx-code-generation/SKILL.md:68,97,103-117`、`scripts/validate_change.py:17`、`agents/comprehensive-reviewer.md:15,32,38`
- 合同来源：`framework-unification.md:64,70,176-189,239-251`、`quality-gates/overview.md:19-26`
- 规划契约：`skills/opsx-code-generation/reference/task_planning_guide.md:36,76-79`
