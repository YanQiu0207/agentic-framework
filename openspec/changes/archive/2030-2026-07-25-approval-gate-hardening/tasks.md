# 实施任务清单

> 由 proposal.md / design.md 生成
> 任务总数：3
> 核心原则：先补校验器逻辑（Task 1 含 OPSX055 + LOOSE，二者顺序耦合），再补测试（Task 2），最后同步长期规格（Task 3）。

- Code Review: PASS
- Review Report: openspec/changes/2030-approval-gate-hardening/review-reports/integration-review.json
- 构建: N/A：纯 Python 标准库仓库，无独立二进制构建产物；由 pytest 全量测试覆盖。
- 测试: PASS（`python -m pytest scripts -q` → 352 passed, 21 skipped, 131 subtests passed，退出码 0；基线 main 343 / 21 / 131，净增 9 个测试方法。`python scripts/lint_skill_graph.py` → errors=0。`python scripts/markdown_links.py openspec` 退出码 0。`verify.py` 总判定 PASS。）

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/validate_change.py` | 修改 | Task 1 | OPSX055 双向耦合 + LOOSE 正则 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 2 | OPSX055 与失败关闭正则测试 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 3 | 同步 OPSX055 行为 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 3 | §5.3 补 OPSX055 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `quality-gates-overview` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Completed | 无需更新：条目级修改。 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Completed | 无需更新：条目级修改。 |

## 知识冲突

- 状态: Resolved。本 Change 是对已归档 Change 2029 的增量硬化，不否定其决策。归档 2029 design §3 曾称「漏标 `irreversible` 会同时导致档位标错，因而更容易在 Plan 门禁暴露」，五维 Review 指出该推理不成立（OPSX037 不做交叉比对），本 Change 用 OPSX055 双向耦合补上这一层。归档记录的是当时证据，不回改。

## 实际 Diff 核对

- 核对状态：Task 1-3 全部完成，无降级替代。交付范围与 proposal §5 一致。
- 已执行：`python -m pytest scripts -q`（352 passed / 21 skipped / 131 subtests，退出码 0；基线 main 343 / 21 / 131，净增 9 个方法）、`python scripts/lint_skill_graph.py`（errors=0）、`python scripts/markdown_links.py openspec`（退出码 0）、`verify.py`（总判定 PASS）、`validate_change.py --phase plan/delivery`（PASS）。既有归档与活跃 Change 跑 plan/delivery 双阶段无回归。
- 审查结论：三个 Task 各自 task-scope standard Review（实现者自审，因本仓库为 Tooling Profile 且本次为聚焦的安全补丁）。已知限制（Approval 自证、gate-failure 自指、围栏内声明、两字段同时省略）在 design §4 显式记录，不在本 Change 解决。

---

### 任务 1：[completed] 校验器补 OPSX055 与 LOOSE 正则

- 状态：已完成
- attempts：1
- 依赖：无
- 文档映射：`design.md` §2 OPSX055、§3 LOOSE
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2030-approval-gate-hardening/review-reports/task-1-review.json
- 文件：`scripts/validate_change.py`
- verification：`python -m pytest scripts/tests/test_validate_change.py -q`
- 验收标准：
    - [x] OPSX055：声明了 `Escalation` 字段的 Task，`irreversible` 与 `Review Profile: strict` 双向一致，违例报 OPSX055。
    - [x] OPSX055 在 plan 阶段生效（不受 require_completed 门控）。
    - [x] 未声明 `Escalation` 字段的 Task 不参与 OPSX055，既有归档不回归。
    - [x] LOOSE 正则：缩进/列表式/错位声明报 OPSX053，不静默放行。
    - [x] LOOSE 探测在剔除围栏后的文本上做。

### 任务 2：[completed] 补测试与全量回归

- 状态：已完成
- attempts：1
- 依赖：Task 1
- 文档映射：`proposal.md` §4 验收标准
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2030-approval-gate-hardening/review-reports/task-2-review.json
- 文件：`scripts/tests/test_validate_change.py`
- verification：`python -m pytest scripts -q`
- 验收标准：
    - [x] OPSX055 双向各一条用例（含 plan 阶段生效）。
    - [x] opt-in 边界：未声明 Escalation 的 strict Task 不违规。
    - [x] LOOSE：缩进 Escalation、列表式批准模式、错位模式声明各一条用例。
    - [x] 围栏内示例不误报。
    - [x] 既有归档与全量测试不回归。

### 任务 3：[completed] 同步长期规格

- 状态：已完成
- attempts：1
- 依赖：Task 1
- 文档映射：`proposal.md` §6 知识影响
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2030-approval-gate-hardening/review-reports/task-3-review.json
- 文件：`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- verification：`python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] overview.md 补 OPSX055 双向耦合与 opt-in 边界、失败关闭正则行为。
    - [x] framework-unification.md §5.3 补 OPSX055。
    - [x] 链接校验通过。
