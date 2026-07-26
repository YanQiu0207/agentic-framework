# Proposal：归档前任务状态一致性门禁

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：task-status-consistency-gate
**状态**：Quick Draft

---

## 1. 问题

`tasks.md` 里同一个「任务是否完成」被表达三次：任务头复选框（`### 任务 N: [x] 描述`）、状态字段（`- 状态：完成`）、验收标准与子任务复选框（`- [x] ...`）。两条轨的门禁各只校验其中一部分，没有任何规则做交叉核对：

- **workflow 轨**：`check_delivery.py:check_tasks` 只读 `- 状态：` 字段（`skills/workflow-code-generation/scripts/check_delivery.py:41-68`）。任务头与验收复选框完全不进判定——`lint_task_deps.TASK_HEADER` 正则在冒号处截断（`lint_task_deps.py:24`），头部标记根本没被解析出来。
- **OPSX 轨**：`validate_change.py` 反过来只查任务头（OPSX030，`scripts/validate_change.py:1361`）和未勾选复选框（OPSX031，`:1372`），不与 `- 状态：` 字段比对。

后果是 Agent 只更新 `- 状态：完成` 一行就能过交付门并归档，留下自相矛盾的归档记录。仓库内已有 4 处实证：

| 位置 | 任务头 | 状态字段 | 未勾选复选框 |
| --- | --- | --- | --- |
| `openspec/changes/2-add-verify-ignore/tasks.md` | `[ ]` ×5 | 完成 | 33 |
| `archive/3-2026-07-23-extension-overlay-support` | `[x]` ×3 | 完成 | 20 |
| `archive/4-2026-07-25-review-report-dual-format` | `[ ]` ×3 | 完成 | 17 |
| `archive/5-2026-07-25-delivery-gate-hardening` | `[ ]` ×5 | 完成 | 31 |

三个归档 change 全部走 workflow 轨交付门，都在「状态字段说完成、复选框说没做完」的状态下通过归档。这类记录使归档证据不可信：读者无法判断「验收项没勾」是「没做」还是「做了没勾」。

## 2. 目标

1. workflow 轨：`check_tasks` 新增三向一致性判定——`状态：完成` ⟺ 任务头标记为完成 ⟺ 任务块内无未勾选复选框。
2. OPSX 轨：新增 OPSX056，交叉核对 `- 状态：` 字段与任务头标记。既有 OPSX030／OPSX031 保持不变。
3. 两轨都失败关闭：字段存在但取值无法解析时报错，不静默跳过。

## 3. 非目标

- **不回填已归档的 3 / 4 / 5**。归档目录记录的是当时证据，回改等于篡改历史。改为写入 `openspec/issues/` 作已验证故障记录；新门禁只对之后的归档生效。
- **不自动勾选复选框**。门禁只做判定，勾选由执行方按真实完成情况负责。自动勾选会把「未验证」洗成「已验证」。
- **不改 `- 状态：` 字段的合法取值集合**，不动 `lint_task_deps.TASK_STATES`、`workflow_control.py` 的状态写入路径。
- **不解决「状态字段本身是 Agent 自证」**。与 change 2030 记录的同类限制一致：门禁改善的是内部一致性，不是证据可信度。Agent 仍可同时勾选所有框并写 `完成`。

## 4. 验收标准

1. workflow 轨：`状态：完成` 但任务头为 `[ ]` 的任务，`check_tasks` 报错并指出任务号与两侧实际取值。
2. workflow 轨：`状态：完成` 但任务块内存在未勾选复选框的任务，`check_tasks` 报错并给出未勾选条目数。
3. workflow 轨：任务头为 `[x]` 但状态为 `需人工` / `阻塞` 的任务，同样报错——终态非完成时头部不得标完成。
4. workflow 轨：`状态：需人工（原因）` + 任务头 `[ ]` + 存在未勾选复选框，视为一致，通过。这是失败任务的正常形态。
5. OPSX 轨：`- 状态：` 与任务头标记矛盾时（任一方向），archive 阶段报 OPSX056 并指出任务号与两侧取值。
6. OPSX 轨：未声明 `- 状态：` 字段的任务跳过 OPSX056——保兼容，仓库内 2 个归档 change 无该字段。
7. OPSX 轨：声明了 `- 状态：` 但取值无法解析时报 OPSX056，不静默跳过。
8. 两轨都只在任务元数据区判定：从任务头到下一个任意级别标题之前，围栏内内容剔除。
9. `python -m pytest scripts -q` 全量通过；新增用例覆盖上述每条。
10. `openspec/issues/` 有 3 / 4 / 5 双重状态的已验证故障记录，含实际扫描命令与结论。

## 5. 设计方案

见 `design.md`。

### 5.1 关键权衡

**只报告不回填历史**。归档的 3 / 4 / 5 保持原样，改写 `openspec/issues/`。回改后无法区分「当时真做完只是没勾」与「事后补勾」，归档证据的可信度反而更低。代价是这三个目录永久不满足新规则，用 issue 记录抵消。

**workflow 轨主门放 `lint_task_deps.py` CLI，不放 `check_delivery.py`**。`check_delivery.py` 的 `--review-report` 是 required 参数，无法只传 `--tasks` 做归档前的轻量检查；拆参数会动交付门参数合同。新开关只读 tasks.md，无副作用，可在归档移动前单独跑；交付门内联同一判定作兜底。

**一致性不并入 `field_errors`**。执行期 `workflow_control.py` 只写 `- 状态：` 字段，不动复选框。若并入 plan 阶段字段校验，执行中途重跑 lint 会对每个刚完成的任务报错，主门变噪声源。

**门禁只判定不勾选**。自动勾选会把「未验证」洗成「已验证」，比不一致更坏。

## 6. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，补 workflow 轨任务终态三向一致与 OPSX056 的行为。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED，§5.3 强制规则补 OPSX056。
- `openspec/issues/`：ADDED，双重状态故障记录。

## 7. 参考资料

- 现场证据：`skills/workflow-code-generation/scripts/check_delivery.py:41`、`scripts/validate_change.py:1361`、`skills/workflow-code-generation/scripts/lint_task_deps.py:24`
- 不一致实例：`archive/3-2026-07-23-extension-overlay-support`、`archive/4-2026-07-25-review-report-dual-format`、`archive/5-2026-07-25-delivery-gate-hardening`
- 同类失败关闭先例：change 2030（OPSX055 与 LOOSE 正则）
