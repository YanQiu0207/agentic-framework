# 实施任务清单

> 由 proposal.md / design.md 生成
> 任务总数：4
> 核心原则：两轨实现互不依赖（Task 1 workflow 轨、Task 2 OPSX 轨），可并行；测试（Task 3）依赖两者；文档与 issue 记录（Task 4）最后同步。

- Code Review: PASS
- Review Report: openspec/changes/2032-task-status-consistency-gate/review-reports/integration-review.json
- 构建: N/A：纯 Python 标准库仓库，无独立二进制构建产物；由 pytest 全量测试覆盖。`python scripts/lint_skill_graph.py` errors=0；`python scripts/markdown_links.py openspec` 退出码 0。
- 测试: PASS（`python -m pytest scripts -q` → 376 passed / 21 skipped / 135 subtests，退出码 0；基线 7e864d3 为 352 passed / 21 skipped / 131 subtests，净增 24 个测试方法）。Windows 下须置 `PYTHONUTF8=1`，与 `verify.py` 的子进程环境一致。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 修改 | Task 1 | 新增一致性判定函数与 `--state-consistency` 开关 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 1 | `check_tasks` 内联一致性判定 |
| `scripts/validate_change.py` | 修改 | Task 2 | 新增 OPSX056 |
| `scripts/test_lint_task_deps.py` | 修改 | Task 3 | 一致性判定与 CLI 用例 |
| `scripts/test_check_delivery.py` | 修改 | Task 3 | 交付门一致性用例 |
| `scripts/tests/test_validate_change.py` | 修改 | Task 3 | OPSX056 用例 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 4 | 同步两轨一致性门行为 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 4 | §5.3 补 OPSX056 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 4 | 步骤 6 补归档前一致性检查 |
| `openspec/issues/` | 新增 | Task 4 | 双重状态已验证故障记录 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `design.md` §3 workflow 轨落点 | Task 1 | 函数、CLI 开关与交付门内联 |
| `design.md` §4 OPSX 轨落点 | Task 2 | OPSX056 判定与取值归类 |
| `design.md` §2 判定区域 | Task 1, Task 2 | 两轨共用区域定义 |
| `proposal.md` §4 验收标准 1-4 | Task 1 | workflow 轨四条 |
| `proposal.md` §4 验收标准 5-8 | Task 2 | OPSX 轨四条 |
| `proposal.md` §4 验收标准 9 | Task 3 | 全量测试 |
| `proposal.md` §4 验收标准 10 | Task 4 | issue 记录 |
| `proposal.md` §6 知识影响 | Task 4 | 长期规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `quality-gates-overview` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Completed | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Completed | 既有条目，无需改索引 |
| `dual-status-incident` | `openspec/issues/incidents/2026-07-26-dual-task-status-bypass.md` | ADDED | Completed | `openspec/issues/index.md` 已更新 |

## 知识冲突

- 状态: Resolved。无冲突。本 Change 对 `quality-gates/overview.md` 与 `framework-unification.md` §5.3 都是增量补充，不否定既有规则：OPSX056 与 OPSX030／OPSX031 判定的是不同信号（前者交叉核对状态字段与任务头，后两者各自单独判定任务头与复选框），三者并存无重叠也无矛盾。新增 `_metadata_region` 而非修改 `_task_block`，既有规则的判定边界保持不变。

## 实际 Diff 核对

- 核对状态：Task 1-4 全部完成，无降级替代。交付范围与 proposal §5 一致，未回填历史归档（proposal §3 非目标第一条的显式决定）。
- 实际 Diff：11 个跟踪文件、496 行新增 / 6 行删除；2 个新增未跟踪路径（Change 目录、故障记录）。代码改动集中在 `lint_task_deps.py`（+110）、`validate_change.py`（+132）、`check_delivery.py`（+7），测试 +220。
- 已执行：`python -m pytest scripts -q`（376 passed / 21 skipped / 135 subtests，退出码 0；基线 7e864d3 为 352 passed / 21 skipped / 131 subtests，净增 24 个测试方法）、`python scripts/lint_skill_graph.py`（errors=0）、`python scripts/markdown_links.py openspec`（退出码 0）、`verify.py --diff-base 7e864d3`（总判定 PASS，spec_drift pass，4 项检查全 pass）、`validate_change.py --phase plan/delivery`（PASS）。
- 测试环境注记：Windows 下直接跑 pytest 若未置 `PYTHONUTF8=1`，`test_runtime_trust::test_cli_outputs_machine_report_and_fails_closed` 会因 `subprocess` 沿用本机 GBK 解码而失败。`verify.py` 为子进程固定注入 `PYTHONUTF8=1`／`PYTHONIOENCODING=utf-8`（`verify.py:232-246`），故门禁路径不受影响。本次核对最初误判该失败为「既有缺陷」，补齐环境变量后基线与改动后均为全绿。
- 既有 Change 回归核对：对全部归档与活跃 Change 跑 plan／delivery 双阶段，与同基线干净 worktree 逐一比对错误数。仅 `archive/4`（+3）、`archive/5`（+5）与活跃 `changes/2-add-verify-ignore`（+5）新增 OPSX056，三者改动前已分别有 52、84、81 个错误，本就未通过 delivery，非新增回归。`changes/2` 由其负责会话在交付前自行修正。
- 集成审查发现并修复一个 P1 级实质缺口：初版把重复 `- 状态：` 声明下推给 `field_errors`，而 `field()` 用 `re.search` 只读第一行、对重复完全静默，使 `完成` 与 `阻塞` 并存的任务可整体通过 workflow 轨交付门——正是本 Change 要堵的绕过类型。已改为在 `state_consistency_errors` 直接报错并与 OPSX056 对齐，补 1 条用例；扫描确认既有文件无一触发该分支。
- 审查结论：四个 Task 各自 task-scope standard Review（实现者自审，本仓库为 Tooling Profile 且本次为聚焦的门禁补丁）。已知限制（状态字段与复选框均为 Agent 自产文本、前缀匹配对 `完成前需确认` 一类取值偏松、围栏内声明等价未声明）在 design §6 显式记录，不在本 Change 解决。
- 自校验：本 Change 自身通过新门禁——`lint_task_deps.py openspec/changes/2032-task-status-consistency-gate/tasks.md --state-consistency` 退出码 0。审查中因此发现并补齐了一处覆盖不足（四个非完成态原只测 2 态）与一条不实的验收表述（原写「全量通过」，实际存在既有失败）。

---

### 任务 1：[completed] workflow 轨一致性判定与归档前开关

- 状态：已完成
- attempts：1
- 依赖：无
- 文档映射：`design.md` §2 判定区域、§3 workflow 轨落点
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2032-task-status-consistency-gate/review-reports/task-1-review.json
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`、`skills/workflow-code-generation/scripts/check_delivery.py`
- verification：`python -m pytest scripts/test_lint_task_deps.py scripts/test_check_delivery.py -q`
- 验收标准：
    - [x] `state_consistency_errors(text)` 判定状态字段、任务头标记与任务块复选框三向一致。
    - [x] 区域内重复声明 `- 状态：` 报错（`field()` 只读第一行，`field_errors` 对重复是静默的）。
    - [x] `状态：完成` + 任务头 `[ ]` 报错，消息含任务号与两侧实际取值。
    - [x] `状态：完成` + 存在未勾选复选框报错，消息含未勾选条目数。
    - [x] 任务头完成标记 + 状态为 `需人工` / `阻塞` / `进行中` / `未开始` 报错（四态各一 subTest）。
    - [x] `状态：需人工（原因）` + `[ ]` + 未勾选复选框判为一致。
    - [x] 判定区域为任务头到下一个任意级别标题或下一个任务头之前，围栏内剔除。
    - [x] `lint_task_deps.py` 新增 `--state-consistency` 开关，只读 tasks.md，违例退出码非 0。
    - [x] 任务头标记整体缺失时跳过标记比对，但仍判定复选框。
    - [x] `field_errors` 行为不变，一致性不并入 plan 阶段字段校验。
    - [x] `check_delivery.check_tasks` 内联一致性判定，违例进交付门错误列表。
    - [x] `TASK_HEADER` 正则与 `workflow_control.py` 调用路径不改。

### 任务 2：[completed] OPSX 轨新增 OPSX056

- 状态：已完成
- attempts：1
- 依赖：无
- 文档映射：`design.md` §2 判定区域、§4 OPSX 轨落点
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2032-task-status-consistency-gate/review-reports/task-2-review.json
- 文件：`scripts/validate_change.py`
- verification：`python -m pytest scripts/tests/test_validate_change.py -q`
- 验收标准：
    - [x] OPSX056 交叉核对 `- 状态：` 字段与任务头标记，双向违例都报。
    - [x] 只在 `require_completed=True`（delivery / archive）生效。
    - [x] 未声明 `- 状态：` 字段的任务跳过，既有 5 个无该字段的归档任务不回归。
    - [x] 状态取值无法归类时报 OPSX056，失败关闭。
    - [x] 区域内多个 `- 状态：` 声明报 OPSX056。
    - [x] 判定区域收窄到下一个任意级别标题之前，尾部小节的 `- 状态: Resolved` 不被误判。
    - [x] `_task_block` 本体不改，OPSX030 / OPSX031 / OPSX037 判定不变。

### 任务 3：[completed] 补测试与全量回归

- 状态：已完成
- attempts：1
- 依赖：Task 1, Task 2
- 文档映射：`proposal.md` §4 验收标准 9
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2032-task-status-consistency-gate/review-reports/task-3-review.json
- 文件：`scripts/test_lint_task_deps.py`、`scripts/test_check_delivery.py`、`scripts/tests/test_validate_change.py`
- verification：`python -m pytest scripts -q`
- 验收标准：
    - [x] workflow 轨：三向一致、四种矛盾方向、终态非完成的正常形态各有用例。
    - [x] workflow 轨：`--state-consistency` CLI 退出码用例。
    - [x] OPSX 轨：双向违例、字段缺失跳过、取值无法归类、重复声明各一条用例。
    - [x] OPSX 轨：尾部小节 `- 状态: Resolved` 不误判的用例。
    - [x] 围栏内状态声明与复选框不误报的用例。
    - [x] `python -m pytest scripts -q` 全量通过，退出码 0：376 passed / 21 skipped / 135 subtests（基线 352，净增 24），无既有用例回归。
    - [x] 既有活跃与归档 Change 跑 `validate_change.py` 双阶段无新增违例（仅 `archive/4`、`archive/5` 新增 OPSX056，二者改动前已分别有 52 / 84 个错误）。

### 任务 4：[completed] 长期规格同步与故障记录

- 状态：已完成
- attempts：1
- 依赖：Task 3
- 文档映射：`proposal.md` §6 知识影响、`proposal.md` §4 验收标准 10
- Review Profile: standard
- Task Review: PASS
- Review Report: openspec/changes/2032-task-status-consistency-gate/review-reports/task-4-review.json
- 文件：`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`、`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-generation/reference/delegated-execution-guide.md`、`openspec/issues/`
- verification：`python scripts/markdown_links.py openspec`、`python scripts/lint_skill_graph.py`
- 验收标准：
    - [x] `quality-gates/overview.md` 记录两轨一致性门行为与判定区域（新增「Tooling 任务状态一致性」小节与 OPSX056 段）。
    - [x] `framework-unification.md` §5.3 补 OPSX056。
    - [x] `workflow-code-generation/SKILL.md` 步骤 6 归档前补 `--state-consistency` 前置检查，并明确复选框由执行方按真实完成情况勾选。
    - [x] `delegated-execution-guide.md` 补勾选责任方（根因 3.2：状态写入方职责明确、勾选方职责悬空）。
    - [x] `openspec/issues/` 新增双重状态故障记录，含 3 / 4 / 5 实测数据与扫描命令。
    - [x] 故障记录明确「不回填归档」的决定与理由。
    - [x] `markdown_links.py` 与 `lint_skill_graph.py` 退出码 0。
    - [x] 按 md-zh 规范自检中文排版（对本次全部新增行机械扫描中英/中数空格与半角标点，hits=0）。
