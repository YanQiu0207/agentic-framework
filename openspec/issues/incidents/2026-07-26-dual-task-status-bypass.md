# 任务双重状态绕过归档门事故复盘

**日期**：2026-07-26

**级别**：门禁失效（归档证据不可信）

**状态**：门禁已补齐（Change `2032-task-status-consistency-gate`），历史归档按惯例不回改

## 1. 事故摘要

`tasks.md` 把「任务是否完成」表达三次：任务头复选框（`### 任务 N: [x] 描述`）、状态字段（`- 状态：完成`）、验收标准与子任务复选框（`- [x] ...`）。两条轨的门禁各只校验其中一部分，没有任何规则做交叉核对，因此只更新 `- 状态：完成` 一行即可通过交付门并完成归档。

四个已归档 Change 在「状态字段说完成、复选框说没做完」的状态下通过了归档。其中 `2031` 是在本次修复进行期间由另一会话归档的——门禁落地前，这个绕过仍在持续产生新实例，这正是它需要机器判定而非文档约定的直接证据。

## 2. 实测数据

扫描命令（在仓库根执行）：

```bash
python -c "
import sys; sys.path.insert(0,'skills/workflow-code-generation/scripts')
import lint_task_deps as L, pathlib
for p in pathlib.Path('openspec/changes').rglob('tasks.md'):
    e = L.state_consistency_errors(p.read_text(encoding='utf-8'))
    if e: print(p.as_posix(), len(e))
"
```

结果：

| 位置 | 任务头 | 状态字段 | 未勾选复选框 |
| --- | --- | --- | --- |
| `openspec/changes/2-add-verify-ignore/tasks.md` | `[ ]` ×5 | 完成 | 33 |
| `archive/3-2026-07-23-extension-overlay-support` | `[x]` ×3 | 完成 | 20 |
| `archive/4-2026-07-25-review-report-dual-format` | `[ ]` ×3 | 完成 | 17 |
| `archive/5-2026-07-25-delivery-gate-hardening` | `[ ]` ×5 | 完成 | 31 |
| `archive/2031-2026-07-26-enforce-verify-config-dispatch-gate` | 无标记 ×2 | 完成 | 5 |

四个归档 Change 共 13 个任务、73 个未勾选验收项与子任务项。`2031` 的任务头完全没有 `[...]` 标记，因此只被复选框判定命中——这也说明标记缺失的形态同样需要复选框那一路判定，不能因为无标记就整体跳过。

## 3. 根因

### 3.1 两条轨各校验一半

- **workflow 轨**：`check_delivery.py:check_tasks` 只读 `- 状态：` 字段。任务头与验收复选框完全不进判定——`lint_task_deps.TASK_HEADER` 正则在冒号处截断，头部标记根本没被解析出来。
- **OPSX 轨**：`validate_change.py` 反过来只查任务头（OPSX030）和未勾选复选框（OPSX031），不与 `- 状态：` 字段比对。

两处缺口是对称的：任一轨都存在「改一处即可过门」的路径。

### 3.2 状态写入方与勾选方不是同一方

执行期 `workflow_control.py` 只写 `- 状态：` 字段，不动复选框。`delegated-execution-guide.md` 未规定复选框由谁勾选，也未把勾选列为合并前提。写入方职责明确、勾选方职责悬空，是 Agent 只改状态字段的直接诱因。

## 4. 影响

归档证据不可信：读者无法判断「验收项没勾」是「没做」还是「做了没勾」。归档目录的用途正是事后追溯当时的完成范围，这一层不可信会连带削弱基于它的所有判断（重复工作识别、回归定位、Change 之间的依赖推断）。

## 5. 纠正动作

- workflow 轨新增 `lint_task_deps.state_consistency_errors`，判定状态字段、任务头标记与任务块复选框三向一致；`lint_task_deps.py --state-consistency` 作归档移动前的前置检查，`check_delivery.check_tasks` 内联同一判定作兜底。
- OPSX 轨新增 OPSX056，在 delivery 与 archive 阶段交叉核对 `- 状态：` 字段与任务头标记，双向违例都报，取值无法归类时失败关闭。
- `workflow-code-generation/SKILL.md` 步骤 6 补前置检查，并明确复选框由执行方按真实完成情况勾选。

## 6. 不回填历史归档的决定

用户裁决：只报告，不回改 `archive/3`、`archive/4`、`archive/5`。`archive/2031` 在裁决之后、门禁合并之前归档，按同一理由一并不回填。

理由：归档目录记录的是当时的证据。事后补勾会让「当时真做完只是没勾」与「事后补勾」不可区分，归档的可信度反而比留着矛盾更低——矛盾至少是可见的。代价是这四个目录永久不满足新规则，由本记录抵消。

新门禁只对之后的归档生效。`openspec/changes/2-add-verify-ignore` 是活跃 Change，由其负责会话在交付前自行修正。

## 7. 已知残余风险

状态字段与复选框都是 Agent 自产文本。本门禁改善的是内部一致性，不提供「验收项真的达成过」的证据——Agent 同时勾选全部复选框并写 `完成` 即可通过。与 Change `2030` 记录的 `Approval: granted` 自证限制同类，需要把验收证据从文本移到确定性产物才能根治。
