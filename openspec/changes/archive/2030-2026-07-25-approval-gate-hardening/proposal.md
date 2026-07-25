# Proposal：批准门安全硬化（补 OPSX055 与失败关闭正则）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-25
**变更**：approval-gate-hardening
**状态**：Quick Draft

---

## 1. 问题

Change `2029-risk-triggered-task-approval` 已归档并合并到 main，把 Production 的「逐 Task 无条件暂停」改为「风险触发升级门」。但归档版本的实现（`scripts/validate_change.py` 当前 main 版本）在事后的五维 strict 集成 Review 中暴露出两类安全缺口，本 Change 专门补齐。

### 1.1 缺 OPSX055 双向耦合：高风险 Task 可绕过暂停（P1）

`irreversible` 与 `Review Profile: strict` 在设计上共用同一份高风险清单（Change 2029 design §3）。但归档实现没有任何规则把两者关联。后果：

- `Review Profile: strict` + `Escalation: 无`（或省略 Escalation 字段）的 Task 能完整通过 plan、delivery、archive 全部门禁。
- 这是一个 `strict` 档（即高风险）却不触发暂停的 Task——正是 Change 2029 想堵住的削弱路径，也是它唯一可能弱于「无条件逐 Task 批准」的方向。

归档版 design §3 曾认为「漏标 `irreversible` 会同时导致档位标错，因而更容易暴露」，但五维 Review 指出该推理不成立：Plan 门禁里唯一涉及档位的是 OPSX037，它只校验 `Review Profile` 取值属于 `{standard, strict}`，不与 `Escalation` 交叉比对，无法暴露漏标。

### 1.2 声明写错位置时静默退回，升级门无声消失（P2）

`Escalation`、`Approval` 与「批准模式」声明是可选字段。归档实现的严格正则只认顶层 `>` 或 `-` 前缀，遇到缩进、列表式或错位的声明时不报错也不识别，等价于「没写」：

- `  - Escalation: irreversible`（缩进）→ 不被识别，升级门消失。
- `- 批准模式：per-task`（列表式，而非 `>`）→ 静默退回 `risk-triggered`，用户显式要求的全量批准门整体失效。
- 声明写在首个 Task 标题之后（头部之外）→ 同样静默退回。

这与必填字段（如 `Review Profile`）的失效方向相反：必填字段写错位置会因「字段缺失」失败关闭，而可选字段写错位置的默认后果是门禁无声消失（失败打开）。

## 2. 目标

1. 新增 OPSX055：双向强制 `irreversible` ⟺ `Review Profile: strict`。标 `irreversible` 必须是 `strict` 档；是 `strict` 档必须标 `irreversible`。后者更关键——堵住 §1.1 的削弱路径。
2. 新增失败关闭正则（`LOOSE_*`）：缩进、列表式或错位的声明必须报格式错误（OPSX053），不得静默退回。
3. OPSX055 在 `plan` 阶段即生效：两个字段都是规划期产物，越早暴露越好。

## 3. 非目标

- **不改 Change 2029 已归档的 design/proposal/spec delta**。归档记录的是当时的决策与证据，按 openspec 惯例不回改。本 Change 是在其之上的增量硬化。
- **不解决「`Approval: granted` 是 Agent 自证」**。这是结构性限制：该字段是 Agent 写入 `tasks.md` 的文本，校验器只验「存在且格式对」，无法区分「用户真批准」与「Agent 自己写」。这需要把批准证据从文本移到确定性产物（如 Run Context），属另一个 Change 的范围。本 Change 在 design §4 显式记录此限制，不试图用代码假装解决。
- **不补围栏内字段、单字段内重复 ID 等低概率边界**。记入 design「已知限制」。
- **不动 `workflow_control.py`、`runtime_*`、`verify.py`、`_stable_waves`**。Change 2029 落地的 `_stable_waves` 与解耦的 `_condition_set`/`_approval_conditions`/`_validate_approval_evidence` 结构保留，本 Change 适配这套结构。

## 4. 验收标准

1. `Review Profile: strict` + 声明了 `Escalation` 字段但未含 `irreversible` 的 Task，`plan` 阶段失败关闭，报 OPSX055 并指出 Task 编号与实际档位。
2. `Escalation` 含 `irreversible` 但 `Review Profile` 不是 `strict` 的 Task，同样失败关闭。
3. 未声明 `Escalation` 字段的 Task 不参与 OPSX055 校验——保兼容，既有归档 Change（含 2 个使用 `strict` 的归档）不回归。
4. 缩进的 `  - Escalation:`、列表式 `- 批准模式：`、错位的批准模式声明，均在 `plan` 或 `delivery` 阶段报 OPSX053，不静默放行。
5. `python -m pytest scripts -q` 全量通过；新增用例覆盖上述每条。

## 5. 设计方案

### 5.1 OPSX055 落点

在 `_validate_approval_evidence`（Change 2029 已有的独立函数）内，解析每个 Task 的 `Escalation` 与 `Review Profile` 后，补一段双向判定。该函数当前只在 delivery/archive 调用（受 `require_completed` 门控）；为了让 OPSX055 在 plan 也生效，需要把「档位耦合」这部分提到一个不受门控的路径，或在 `_validate_tasks` 主循环里独立调用。

关键约束：只对**声明了 `Escalation` 字段**的 Task 生效。未声明的 Task 直接跳过——这是兼容性的根基，仓库内 2 个归档 Change 使用 `strict` 且无 `Escalation`，必须继续通过。

### 5.2 LOOSE 正则

新增三个宽松正则，与严格正则配对：

- `LOOSE_ESCALATION_RE` / `LOOSE_APPROVAL_RE`：允许行首空白与列表标记。
- `LOOSE_APPROVAL_MODE_RE`：允许 `>` 与 `-`/`*` 两种前缀（tasks.md 头部本身混用 `> 任务总数：` 与 `- Code Review:`）。

判定规则：宽松命中数 > 严格命中数 ⇒ 格式错误，报 OPSX053。方向必须是失败关闭。

### 5.3 关键权衡

**OPSX055 用 opt-in 而非 opt-out**。opt-out（所有 `strict` 档必须声明 `Escalation`）能堵得更彻底，但会让 2 个归档 Change 立即违规，且把「必须声明字段」的负担加到所有未来 strict Task。opt-in（只有写了 `Escalation` 才校验）保兼容，代价是「两个字段同时省略」仍无法发现——这是 §3 明确接受的残余风险。

**已知限制（不在本 Change 解决）**：

- `Approval: granted` 是 Agent 自产文本，校验器无法验证「用户真批准过」。本 Change 的所有工作都建立在这个前提下——它改善的是「留痕与一致性」，不是「可信证据」。
- `gate-failure` 依赖 Agent 产出的 `review-report.json` 的 p0/p1 字段，Agent 可构造 p0=0/p1=0 绕过。同属自证类限制。
- 围栏（```...```）内的声明被 `_metadata_text` 剔除后不被识别，等价于没写。

## 6. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，补 OPSX055 双向耦合与失败关闭正则的行为。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED，§5.3 强制规则补 OPSX055。

## 7. 参考资料

- 归档基线：`openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/`（proposal、design）
- 五维 Review 结论：OPSX055 缺失（维度 5 S5）、声明错位静默退回（维度 2 P2-2）
- 现场证据：`scripts/validate_change.py`（`_validate_approval_evidence`、`_condition_set`、`_approval_conditions`、`_stable_waves`）
