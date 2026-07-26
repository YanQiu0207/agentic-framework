# Design：归档前任务状态一致性门禁

**变更**：task-status-consistency-gate
**日期**：2026-07-26

---

## 1. 一致性定义

任务的完成信号有三处，判定为「一致」的充要条件：

| 状态字段 | 任务头标记 | 任务块内复选框 |
| --- | --- | --- |
| `完成` | 必须为完成标记 | 必须全部勾选 |
| `需人工` / `阻塞` / `进行中` / `未开始` | 必须**不是**完成标记 | 不约束 |

双向都判。反方向（头部标 `[x]` 但状态是 `阻塞`）同样是矛盾，且更危险——读者按头部会认为任务已完成。

`需人工` / `阻塞` 是终态但非完成态，未勾选的复选框正是「哪些验收项没达成」的记录，不能要求勾选，也不能允许头部标完成。

## 2. 判定区域

两轨统一：任务元数据区 = 任务头行之后，到**下一个任意级别 Markdown 标题**或下一个任务头之前，取最先出现者；围栏（```／~~~）内内容剔除。

现有 `validate_change._task_block` 的边界是「下一个任务头或文件末尾」，末任务会吞掉 `## 文档覆盖映射`、`## 知识同步`、`## 知识冲突` 等尾部小节。这些小节自带 `- 状态: Resolved` 一类字段（实测 `archive/2028`、`archive/2029` 各 1 处），若不收窄区域会把尾部状态误判为任务状态。

实测尾部小节当前不含复选框（全仓扫描 0 命中），但仍按同一区域判定，避免以后新增尾部清单时静默改变语义。

不改 `_task_block` 本体——OPSX030／OPSX031／OPSX037 等既有规则都依赖当前边界，改它会连带改动已通过的判定。新增独立的区域函数。

## 3. workflow 轨落点

新增 `lint_task_deps.state_consistency_errors(text) -> list[str]`，由两处消费：

1. `check_delivery.check_tasks`：交付门内联调用。这是**兜底**——该门在 SKILL.md 步骤 8，归档移动已发生。
2. `lint_task_deps.py` CLI 新增 `--state-consistency` 开关：可在归档移动前单独跑，作为步骤 6 的前置机器检查。这是**主门**，满足「归档前校验」。

**不加进 `field_errors`**。`field_errors` 是 plan 阶段验收项 1 的校验路径；执行期 `workflow_control.py` 只写 `- 状态：` 字段（`workflow_control.py:487-490`），不动复选框。若把一致性并进 `field_errors`，执行中途重跑 lint 会对每个刚完成的任务报错，把主门变成噪声源。用独立开关把「规划期结构校验」与「交付期状态一致性」分开。

`TASK_HEADER` 正则在冒号处截断，头部标记未被解析。不改该正则（`workflow_control.py:219/304/535`、`run_journal.py:278` 都依赖它），改为在新函数内单独匹配标题行的 `[...]` 段。

**重复声明由本函数报，不下推给 `field_errors`**：`field()` 用 `re.search` 只取第一处匹配，`field_errors` 对重复声明完全静默。若本函数也跳过，`- 状态：完成` 与 `- 状态：阻塞` 并存的任务会整体通过 workflow 轨交付门——正是本 Change 要堵的绕过类型。OPSX 轨的 OPSX056 同样报此形态，两轨对齐。

**标记整体缺失视为「未声明」**，跳过标记比对，与 OPSX 轨的 opt-in 取向一致：`### 任务 1：实现`（无 `[...]`）没有可与状态字段对立的完成信号，报错等于扩大到本 Change 之外的形态。实测 `scripts/test_runtime_workflow.py` 与 `archive/legacy-framework-unification`（7 个任务）都是这种形态。复选框判定不受影响——两者是独立信号，标记缺失不豁免未勾选项。

## 4. OPSX 轨落点

新增 OPSX056，在 `_validate_tasks` 主循环内判定，仅 `require_completed=True` 时生效（delivery 与 archive 阶段）。

- 未声明 `- 状态：` 字段 → 跳过。仓库内 `archive/2026-07-19-accept-knowledge-routing` 与 `archive/legacy-opsx-code-first-deterministic-validation` 共 5 个任务无该字段，必须继续通过。
- 声明但取值无法归类 → 报 OPSX056，失败关闭。与 change 2030 的 `LOOSE_*` 同向：可选字段写错内容的默认后果不能是门禁消失。
- 区域内出现多个 `- 状态：` → 报 OPSX056。与 OPSX037／OPSX038 的「唯一性」判定一致。

状态取值归类（前缀匹配，长者优先）：

- 完成态：`已完成`、`完成`、`completed`、`complete`、`done`、`x`
- 非完成态：`未开始`、`进行中`、`需人工`、`阻塞`、`pending`、`blocked`

前缀匹配沿用 `lint_task_deps.parse_state` 的既有语义（允许 `完成（附注）` 一类后缀），弱点相同：`完成前需确认` 会被判为完成态。不在本 Change 收紧——收紧会改变 workflow 轨已在用的解析行为，属另一个 Change。

## 5. 关键权衡

**只报告不回填历史**。归档的 3 / 4 / 5 保持原样，改为写 `openspec/issues/`。理由：归档目录是当时证据，回改后无法区分「当时真做完了只是没勾」与「事后补勾」。代价是这三个归档目录永久不满足新规则——用 issue 记录抵消。

**主门放 `lint_task_deps.py` CLI 而非 `check_delivery.py`**。`check_delivery.py` 的 `--review-report` 是 required 参数，无法只传 `--tasks` 做轻量前置检查；拆参数会动交付门的参数合同。新开关只读 tasks.md，无副作用。

**门禁只判定不勾选**。自动勾选会把「未验证」洗成「已验证」，比不一致更坏。

## 6. 已知限制

- 状态字段与复选框都是 Agent 自产文本。本门禁改善内部一致性，不提供「验收项真的达成过」的证据。Agent 同时勾选全部框并写 `完成` 即可通过。与 change 2030 记录的 `Approval: granted` 自证限制同类。
- 围栏内的状态声明被剔除后等价于未声明，走跳过分支。
- OPSX 轨只在 delivery／archive 判定；plan 阶段任务处于 `未开始` + `[ ]` + 未勾选，本就一致，无需前置。
