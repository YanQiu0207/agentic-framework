# 实施任务清单

> 由 `proposal.md`（Standard）与 `design.md` 生成
>
> 任务总数：4
>
> 核心原则：先在校验器落地元数据格式与规则（Task 1），策略层与规划层再引用同一格式（Task 2 → Task 3）；长期知识同步（Task 4）与前三者无文件重叠，可并行。
>
- Code Review: PASS
- Review Report: openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/review-reports/integration-review.json

## 执行图

```text
Task 1 (校验器规则 OPSX052-054)     Task 4 (长期 Specs 同步)
   │                                  （独立，W1 并行）
   └──> Task 2 (SKILL.md 执行节奏)
          │
          └──> Task 3 (task_planning_guide 预标注)
```

波次：W1 = {Task 1, Task 4} → W2 = {Task 2} → W3 = {Task 3}

> Task 2 与 Task 3 都描述同一套元数据格式，格式以 Task 1 的实现为准，故串行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/validate_change.py` | 修改 | Task 1 | 新增 Escalation/Approval 解析与 OPSX052-054 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 1 | 新增批准证据校验用例 |
| `skills/opsx-code-generation/SKILL.md` | 修改 | Task 2 | 步骤 3/5 执行节奏、升级条件清单、波次推进 |
| `skills/opsx-code-generation/reference/task_planning_guide.md` | 修改 | Task 3 | 条件预标注、模式声明、元数据模板 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 4 | §2.2 第 70 行、§5.3 强制规则 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 4 | Production 阶段门补批准证据校验 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `tasks.md` Task 元数据 `- Escalation:` | 新增可选字段 | opsx-code-generation / 校验器 | Task 1, 2, 3 |
| `tasks.md` Task 元数据 `- Approval:` | 新增可选字段 | opsx-code-generation / 校验器 | Task 1, 2, 3 |
| `tasks.md` 头部 `> 批准模式：` | 新增可选声明 | 用户 / 校验器 | Task 1, 3 |
| `validate_change.py --phase delivery` | 新增 3 条规则 | opsx-code-generation | Task 1 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/framework/quality-gates/overview.md` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引。 |
| `specs/backend/engineering/tech/framework-unification.md` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Completed | 无需更新：条目级修改，不影响索引。 |
`workflow-control/overview.md` 不同步：Production 波次独立实现，不复用 Tooling 执行栈（`design.md` §5.1）。

---

### 任务 1：[x] 校验器新增批准证据校验

- 状态：完成
- attempts：0
- 依赖：无
- 文档映射：`design.md` §4 校验器改动、`proposal.md` 验收标准 2/3/4
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/review-reports/task-1-review.json
- Escalation: 无
- context_files：`scripts/validate_change.py`、`scripts/tests/test_validate_change.py`、`openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/design.md`
- 文件：`scripts/validate_change.py`、`scripts/tests/test_validate_change.py`
- verification：`python -m pytest scripts/tests/test_validate_change.py -q`；`python -m pytest scripts -q`
- artifacts：`ESCALATION_RE`、`APPROVAL_RE`、`APPROVAL_MODE_RE`、条件白名单常量、OPSX052-054 规则、回归用例
- 验收标准：
    - [x] 新增条件 ID 白名单常量，含 `scope-change`、`irreversible`、`gate-failure`、`assumption-broken`、`user-requested`、`per-task-mode` 六项。
    - [x] OPSX052：Task 为 Completed 且声明 `Escalation`（非「无」），缺 `Approval` 或为 `pending` 时失败，报错含 Task 编号与缺失条件 ID。
    - [x] OPSX053：`Approval` 条件集合与 `Escalation` 不一致，或含白名单外 ID 时失败，报错含不一致的 ID。
    - [x] OPSX054：头部声明 `批准模式：per-task` 时，全部 Completed Task 均要求 `Approval: granted`。
    - [x] 无 `Escalation`（或值为「无」）且模式为 `risk-triggered` 的 Task 不触发任何新规则。
    - [x] 新规则只在 `delivery` 阶段生效，`plan` 与 `archive` 阶段不因缺少这两个字段而拒绝。
    - [x] 归档目录与既有 Change 不回归；`python -m pytest scripts -q` 全量通过。

### 任务 2：[x] SKILL.md 改为风险触发执行节奏

- 状态：完成
- attempts：0
- 依赖：Task 1
- 文档映射：`design.md` §1/§2/§3/§5、`proposal.md` 验收标准 1/5
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/review-reports/task-2-review.json
- Escalation: 无
- context_files：`skills/opsx-code-generation/SKILL.md`、`openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/design.md`、`scripts/validate_change.py`
- 文件：`skills/opsx-code-generation/SKILL.md`
- verification：`python scripts/lint_skill_graph.py`；人工核对步骤 3/5 与 Task 1 的元数据格式一致
- artifacts：步骤 5 核心规则改写、升级条件清单表、Phase 2 改写、波次推进说明
- 验收标准：
    - [x] 步骤 5 核心规则改为「Tasks 整体批准后自主连续执行；每个 Task 仍须通过测试、Verification 与风险分档独立 Review；仅命中升级条件时暂停等待用户决定」。
    - [x] 新增六类升级条件清单，条件 ID 与 Task 1 白名单逐字一致。
    - [x] `irreversible` 明确引用既有高风险清单，并补充删除性操作、发布与外部副作用。
    - [x] Phase 2 改为：命中升级条件则暂停并写 `Approval: pending`，用户批准后更新为 `granted`；未命中则继续下一 Task。
    - [x] 步骤 3 改为按 `depends_on` 计算波次推进，波次边界输出汇总报告；依赖缺失或成环沿用既有失败路径。
    - [x] 明确升级条件优先于波次边界。
    - [x] Task 级 Review、Verification、Delivery 门禁、五维集成 Review 与 Archive 门禁的表述均不被削弱。
    - [x] `lint_skill_graph.py` 输出 `errors=0`。

### 任务 3：[x] 规划指南补条件预标注与模式声明

- 状态：完成
- attempts：0
- 依赖：Task 2
- 文档映射：`design.md` §2 判定归属表、`proposal.md` 验收标准 1/4
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/review-reports/task-3-review.json
- Escalation: 无
- context_files：`skills/opsx-code-generation/reference/task_planning_guide.md`、`skills/opsx-code-generation/SKILL.md`
- 文件：`skills/opsx-code-generation/reference/task_planning_guide.md`
- verification：`python scripts/markdown_links.py skills/opsx-code-generation`；人工核对元数据模板与 Task 1/2 一致
- artifacts：预标注要求、任务元数据模板新增字段、头部模式声明说明
- 验收标准：
    - [x] 新增规划期预标注要求：`scope-change` 与 `irreversible` 必须在创建 `tasks.md` 时标注。
    - [x] 任务元数据模板含 `- Escalation:` 字段，并说明无命中时写「无」。
    - [x] 说明 `- Approval:` 由执行期写入，规划期不预填。
    - [x] 说明头部 `> 批准模式：per-task` 的语义与缺省值 `risk-triggered`。
    - [x] 明确 `irreversible` 与 strict Review 档位同源，漏标同时导致档位标错。
    - [x] 链接校验通过。

### 任务 4：[x] 同步长期 Specs

- 状态：完成
- attempts：0
- 依赖：无
- 文档映射：`proposal.md` §6 知识影响、本清单知识同步章节
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/review-reports/task-4-review.json
- Escalation: 无
- context_files：`openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/backend/framework/quality-gates/overview.md`、本 Change `specs/backend/framework/quality-gates/spec.md`
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/backend/framework/quality-gates/overview.md`
- verification：`python scripts/markdown_links.py openspec`；核对与 Change Delta 无冲突
- artifacts：§2.2 与 §5.3 改写、Production 阶段门段落补充
- 验收标准：
    - [x] `framework-unification.md` §2.2 第 70 行不再表述为「Production 保留逐 Task 推进」，改为风险触发升级门。
    - [x] `framework-unification.md` §5.3 强制规则补充升级条件与批准证据要求，且不删除既有 Review 与门禁规则。
    - [x] `framework-unification.md` §5.2 生命周期图更新执行段表述。
    - [x] `quality-gates/overview.md` 的 Production 阶段门段落补充 `delivery` 阶段批准证据校验。
    - [x] 两处均标注来源为本 Change，不与 Delta 冲突。
    - [x] 链接校验通过。

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` 验收标准 1～6 | Task 1～4 | 覆盖确定性门、执行策略、规划元数据与长期知识同步。 |
| `specs/backend/framework/quality-gates/spec.md` 两项 MODIFIED Requirement | Task 1～4 | 覆盖批准证据与稳定依赖波次。 |
| `design.md` §1～5 | Task 1～4 | 覆盖校验器、策略层、规划层与长期合同。 |

## 执行记录

- 构建：N/A，纯 Python 标准库脚本与 Markdown 文档，无构建步骤
- 测试：退出码 0，`python -m pytest scripts -q` → 340 passed, 21 skipped（含 `scripts/tests/test_validate_change.py` 51 passed，覆盖 OPSX052-054 批准证据四类场景与波次输出）
- 辅助校验：`python scripts/lint_skill_graph.py` → errors=0；`python scripts/markdown_links.py openspec` 与 `skills/opsx-code-generation` → 退出码 0

## 知识冲突

- 状态：无冲突。本 Change 将 Production「逐 Task 停等」改为「风险触发升级门」，仅收紧人工介入时机并新增批准证据校验；既有 Task 级 Review、Verification、Delivery 门禁、五维 strict 集成 Review 与 Archive 门禁的触发条件与判定标准均不变，与 quality-gates/overview.md、framework-unification.md 现有规则一致。

## 实际 Diff 核对

- 核对状态：已核对，PASS。
- 已执行命令：`python -m pytest scripts -q`（340 passed, 21 skipped）、`python scripts/lint_skill_graph.py`（errors=0）、`python scripts/markdown_links.py openspec` 与 `skills/opsx-code-generation`（退出码 0）、`python scripts/validate_change.py --phase plan --json` 与 `--phase delivery --json`（退出码 0）。
- 审查结论：Task 1-4 均通过 standard 独立 Review（Task 2 经一轮 P1 修复后 re-review PASS）；五维 strict 集成 Review（scope: integration）PASS，0 P0/0 P1，12 条 P2 记入报告不阻塞。
