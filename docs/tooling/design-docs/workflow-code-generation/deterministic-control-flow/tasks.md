# 实施任务清单

> 由 `spec.md` 生成  
> 任务总数：3  
> 核心原则：先实现纯控制流内核和测试，再接入实际工作流文档入口，最后做全量验证与记录。

## 依赖关系总览

```text
Task 1（控制流内核与单元测试）
  ↓
Task 2（工作流入口接线）
  ↓
Task 3（集成验证与文档收口）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 新建 | Task 1 | 确定性分波、状态、阻塞、恢复与 CLI |
| `scripts/test_workflow_control.py` | 新建 | Task 1 | 固定控制流 case 与文本写回测试 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 2 | 将内核设为实际编排强制入口 |
| `skills/workflow-code-generation/reference/delegated-execution-guide.md` | 修改 | Task 2 | 补逐波调用、结果应用和恢复命令 |
| `docs/10-harness-engineering-practices.md` | 修改 | Task 3 | 记录控制流测试落地状态 |
| `docs/design-docs/workflow-code-generation/deterministic-control-flow/spec.md` | 修改 | Task 3 | 验证后归档 |
| `docs/design-docs/workflow-code-generation/deterministic-control-flow/tasks.md` | 修改 | Task 1～3 | 实时记录任务状态与证据 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `workflow_control.py` CLI | 新增 | `workflow-code-generation` 编排流程 | Task 1、2 |
| `lint_task_deps.parse_tasks()` | 复用，不改签名 | 控制流内核 | Task 1 |

### 构建系统变更

- 不新增第三方依赖或构建配置。

## 风险与假设

| # | 描述 | 影响任务 | 假设或处理 |
| --- | --- | --- | --- |
| 1 | Prompt 文档无法像 Hook 一样强制执行脚本 | Task 2 | 将命令列为 Phase 0、逐波和恢复的强制步骤，并由测试保证脚本决策正确 |
| 2 | 当前工作区已有 `10-harness-engineering-practices.md` 未提交修改 | Task 3 | 保留既有内容，只追加本功能状态，交付时单独标明来源 |
| 3 | 恢复需要 Git 与 worktree 事实 | Task 1 | 内核只消费 `merged_task_ids`，不直接调用 Git |

## 任务列表

### 任务 1：[x] 实现确定性控制流内核与测试

- 状态：完成
- 文件：`agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`（新建）、`agentic-framework/scripts/test_workflow_control.py`（新建）
- depends_on：[]
- review_profile：standard
- spec 映射：4.2、4.3、7.1、7.2
- 说明：复用现有解析器，实现稳定分波、可调度判断、结果应用、重试耗尽、阻塞传播、恢复计划、精准状态写回和最小 CLI。
- context_files：
  - `agentic-framework/skills/workflow-code-generation/scripts/lint_task_deps.py`——现有任务解析与状态契约
  - `agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`——控制流规则来源
  - `agentic-framework/scripts/test_lint_task_deps.py`——现有测试风格
- verification：
  - [x] `python -m unittest agentic-framework/scripts/test_workflow_control.py` 通过
  - [x] `python -m unittest agentic-framework/scripts/test_lint_task_deps.py` 通过
  - [x] 5 类核心控制流均有固定 case
  - [x] 测试不访问网络、不调用模型、不创建 worktree
- artifacts：
  - `agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`
  - `agentic-framework/scripts/test_workflow_control.py`
- 子任务：
  - [x] 1.1：定义最小不可变结果和决策数据类
  - [x] 1.2：实现分波、状态、阻塞和恢复逻辑
  - [x] 1.3：实现精准文本写回和 CLI
  - [x] 1.4：调用 `workflow-test-generation` 补齐正常路径和关键边界测试
  - [x] 1.5：运行测试，全部通过

### 任务 2：[x] 将控制流内核接入工作流入口

- 状态：完成
- 文件：`agentic-framework/skills/workflow-code-generation/SKILL.md`（修改）、`agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`（修改）
- depends_on：[Task 1]
- review_profile：standard
- spec 映射：4.1、4.3
- 说明：将波次生成、逐波推进、状态写回和恢复改为调用 `workflow_control.py`，删除与脚本冲突的手工判断表述。
- context_files：
  - `agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`——Task 1 新接口
  - `agentic-framework/skills/workflow-code-generation/SKILL.md`——实际工作流入口
  - `agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`——下放执行细则
- verification：
  - [x] 文档中的命令与 CLI `--help` 一致
  - [x] 分波、失败后阻塞和恢复均明确调用同一脚本
  - [x] `python agentic-framework/scripts/lint_skill_graph.py` 通过
- artifacts：
  - `agentic-framework/skills/workflow-code-generation/SKILL.md`
  - `agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`
- 子任务：
  - [x] 2.1：修改 SKILL 的波次与恢复入口
  - [x] 2.2：修改执行手册命令与顺序
  - [x] 2.3：核对 CLI 示例可执行

### Review 修复记录

- 2026-07-12：修复首轮 Review 的 8 项 finding：拆分质量门与合并事件、拒绝自依赖、统一合法状态转换、持久化修复次数、缺失依赖字段失败关闭、原子写回、拒绝 CR / LF 原因、补同波失败隔离集成测试。
- 2026-07-12：修复第二轮 Review 的 3 项 finding：持久化 `control_stage` 并限制合并阶段、启动前复核依赖、原子写回保留权限和 CRLF；补对应负向测试。

### 任务 3：[x] 完成集成验证与审核记录

- 状态：完成
- 文件：`agentic-framework/docs/10-harness-engineering-practices.md`（修改）、`agentic-framework/docs/design-docs/workflow-code-generation/deterministic-control-flow/spec.md`（修改）、`agentic-framework/docs/design-docs/workflow-code-generation/deterministic-control-flow/tasks.md`（修改）
- depends_on：[Task 2]
- review_profile：standard
- spec 映射：7、8、9
- 说明：运行仓库级测试和机器验证，记录实际结果、Review 结论与限制，归档规格。
- context_files：
  - `verify.config.json`——仓库机器验证配置
  - `agentic-framework/docs/10-harness-engineering-practices.md`——路线图状态
  - `agentic-framework/docs/design-docs/workflow-code-generation/deterministic-control-flow/spec.md`——验收契约
- verification：
  - [x] `python -m unittest discover -s agentic-framework/scripts -p "test_*.py"` 通过：40 个通过，1 个跳过
  - [x] `python -m compileall -q agentic-framework/scripts agentic-framework/skills/workflow-code-generation/scripts` 通过
  - [x] `python agentic-framework/skills/workflow-code-generation/scripts/lint_task_deps.py <tasks.md>` 通过：0 error，0 warning
  - [x] `git diff --check` 通过
- artifacts：
  - 更新后的 `spec.md`、`tasks.md` 和 Harness 实践文档
  - 测试与验证结果摘要
- 子任务：
  - [x] 3.1：运行全量单元测试与编译检查
  - [x] 3.2：执行标准档代码 Review 并处理 keep finding
  - [x] 3.3：记录验证结果和已知限制
  - [x] 3.4：归档规格并提交本地 Git

### 最终审核与验证记录

- 标准档首轮 Review：`NEEDS_CHANGES`，确认 4 项 P1 和 4 项 P2。
- 第一轮复审：6 项已修复，2 项部分修复，新增 1 项 P2。
- 第二轮复审：`PASS`，未发现新的 P0 或 P1。
- 全量测试：40 个通过，1 个跳过。
- 既存限制：Prompt 入口不具备 Hook 级强制性；恢复仍依赖编排层提供真实 Git 合并事实。

### 修复轮次记录（write-lock PR 双侧 Review）

- 2026-07-12：针对 `workflow_control.py` 写锁 PR 的两份独立 Review（A 侧 + B 侧）合计 4 条 P1、16 条 P2 及若干 follow-up。最重问题集中在 B 侧引入的状态机与文档契约层：`--reason` 被当 `re.sub` 替换模板可注入 / 破坏 `tasks.md`（P1-1）；「需人工」为零出边吸收态，人工恢复链死锁（P1-2）；多处文档要求「直接标需人工」但状态机无对应事件，修复轮次与内核 `attempts` 双重记账（P1-3）。新增 Task 4 收口全部 P1 + 可行 P2 + 部分 follow-up。

### 任务 4：[x] 修复写锁 PR Review 发现的状态机与解析健壮性问题

- 状态：完成
- 文件：`agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`（修改）、`agentic-framework/scripts/test_workflow_control.py`（修改）
- depends_on：[Task 2]
- review_profile：standard
- spec 映射：4.2.2、4.2.3、4.2.5、4.3、7.1、7.3、8.1（本任务同步扩写这些章节，见交付后的 spec.md 修订）
- 说明：修复 Review 报告的 P1-1/P1-2/P1-3 及可行 P2（P2-3 代码部分、P2-5、P2-6 代码部分、P2-7 代码部分）与 1 项 follow-up（`isdigit`→`isdecimal`）。文档侧（P2-1/P2-2/P2-4/P2-6 文档部分/P2-7 文档部分）不入本 task，由主会话在本 task 交付后直接改 4 份 `.md`（不走 agent 派发）。
- 设计决策（不可在实现中drift）：
  - 新增事件 `manual`：合法转换 `("进行中", "running", "manual")` → `TaskDecision(task_id, "需人工", "manual", reason, attempts, "manual")`；`reason` 为空必须 `raise ValueError`；不递增 `attempts`（区别于 `failure`）。用于 verify 门禁自身出错、owner/implementer 子 agent 崩溃或超时、复审 2 轮仍 `NEEDS_CHANGES`、owner 内部修复轮次耗尽等场景直接标需人工，不占用状态机自身的 `attempts` 重试预算。
  - 新增事件 `manual_resolved`：合法转换 `("需人工", "manual", "manual_resolved")` → `TaskDecision(task_id, "完成", "complete", reason, attempts, "completed")`；`reason` 可选。用于人工排查 `需人工` 任务、修复并合并其分支后闭环。
  - CLI `event` 子命令的 `choices` 增加 `"manual"`、`"manual_resolved"`。
  - `plan_recovery()` 按任务自身状态重新分支（顺序）：`完成`→`skip`；`需人工` 且在 `merged_task_ids`→`complete`（原因「任务已人工解决并合并」，执行时对应 CLI 事件 `manual_resolved`）；`需人工`（未合并）→新增 `manual` 动作（原因「等待人工处理，处理并合并后重跑 recover」，不再落入 `wait`/「前置依赖未完成」的假原因）；`进行中` 且在 `merged_task_ids`→`complete`（原因「任务分支已合并」，执行时对应 CLI 事件 `merge_success`，与需人工分支的 `complete` 用同一 action 字符串但对应不同 CLI 事件，由 guide 文档按任务原状态区分，不在数据结构层面拆两个动作名）；`进行中`（未合并）→`inspect`；`阻塞` 且 `deps_complete`→`unblock`；`未开始` 且 `deps_complete`→`dispatch`；否则→`wait`。
  - `plan_recovery()` 增加前置校验：`state` 为 `未开始` 或 `阻塞` 但 `task_id` 在 `merged_task_ids` 中时，`raise ValueError`（外部合并事实与持久化状态矛盾，fail-closed，对应 spec 4.2.5「立即失败」）。
  - `_validate_dependencies()` 内新增循环依赖检测（可复用 `build_waves()` 的 Kahn 分层逻辑抽出的共享私有函数），使 `dispatchable_tasks()` / `apply_event()` / `plan_recovery()` 在成环时与 `build_waves()` 一样立即失败，而不是静默给出部分结果。
  - `update_task_state()`：状态 / attempts / control_stage 三处正则替换统一改为捕获前导 `[ \t]*` 缩进并在替换时保留（不再拍平缩进），且全部通过可调用对象（lambda / 具名函数）传入 `re.sub`，禁止把含用户输入的字符串直接作为 `repl` 参数传给 `re.sub`（避免 `\1`/`\g<0>` 被当模板解析，这是 P1-1 根因）。
  - `_require_completed_dependencies()` 函数的依赖校验失败信息需包含原状态与目标事件（如「任务 {id} 的前置依赖尚未全部完成，无法从 {state} 执行 {event}」），修正 P2-6 指出的 :163/:190 错误信息缺要素问题。
  - `main()` 增加 `sys.stdout.reconfigure(encoding="utf-8")`（`hasattr` 守卫），对齐 `lint_task_deps.py` 的 Windows 控制台编码处理。
  - `_load()` 改用 `path.read_bytes().decode("utf-8-sig")`（去 BOM）；`lint_task_deps.py` 的 `main()` 读取改用 `read_text(encoding="utf-8-sig", errors="replace")`，同类问题一并修（用户已确认）。
  - `_attempts()` 的 `value.isdigit()` 改 `value.isdecimal()`。
  - `apply_event()` 拆分为分发 + 每事件私有处理函数，使主函数与新写的 `update_task_state()` 均满足 `std-python` 的单函数 ≤ 50 行（不含 docstring/空行）；同时补 `failure` 分支的显式 `if` 判断，去掉隐式 fall-through。
  - 全部改动行需满足 80 字符行长上限（black 规范）。
- context_files：
  - `agentic-framework/skills/workflow-code-generation/scripts/lint_task_deps.py`——`field()`/`parse_tasks()`/`main()` 读取契约与 BOM 同类修复点
  - `agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`——`需人工`/合并/恢复相关流程描述（本 task 不改，仅供理解上下文，Task 5 由主会话改）
  - `agentic-framework/docs/design-docs/workflow-code-generation/deterministic-control-flow/spec.md`——现有设计与接口约定（本 task 不改，Task 5 由主会话同步）
- verification：
  - [x] `python -m unittest agentic-framework/scripts/test_workflow_control.py` 通过，新增用例覆盖：`--reason` 含反斜杠（如 `C:\1foo`、`\g<0>`）不破坏状态行且正常持久化；`manual` 事件空 reason 报错；`manual` 事件成功转需人工且 `attempts` 不变；`manual_resolved` 事件需人工→完成；`plan_recovery` 对「需人工+已合并」输出正确 action/reason；`plan_recovery` 对「需人工+未合并」输出 `manual` action 而非假 `wait`；`plan_recovery` 对「未开始/阻塞+已合并」的矛盾输入报错；`dispatchable_tasks`/`plan_recovery` 在成环任务图上立即报错（不仅 `build_waves`）；缺失「状态」字段单独用例；100 任务规模的 `build_waves` 正确性用例；状态/attempts/control_stage 行原有缩进在写回后保留（含 `control_stage` 字段已存在场景的补测）；BOM 前缀 tasks.md 首任务可正常解析；`_attempts` 对非十进制数字字符（如 `isdigit()` 为真但非十进制）给出自定义错误而非裸 `int()` 异常
  - [x] `python -m unittest agentic-framework/scripts/test_lint_task_deps.py` 通过（含 BOM 场景新增用例）
  - [x] `python -m unittest discover -s agentic-framework/scripts -p "test_*.py"` 全量通过：79 个通过，1 个跳过
  - [x] `python -m compileall -q agentic-framework/scripts agentic-framework/skills/workflow-code-generation/scripts` 通过
  - [x] `workflow-code-review`（`standard` 档）结论 `PASS`：`comprehensive`/`standards`/`robustness`/`spec-compliance` 三独立维度审查（工程规范、健壮性、需求符合度）零 P0/P1，4 项 P2 已修复
- artifacts：
  - `agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`
  - `agentic-framework/scripts/test_workflow_control.py`
  - `agentic-framework/scripts/test_lint_task_deps.py`
  - `agentic-framework/skills/workflow-code-generation/scripts/lint_task_deps.py`
- 子任务：
  - [x] 4.1：`apply_event()` 新增 `manual`/`manual_resolved` 并拆分为分发 + 私有处理函数
  - [x] 4.2：`plan_recovery()` 重排分支、补矛盾输入校验
  - [x] 4.3：`_validate_dependencies()` 补循环检测；`update_task_state()` 缩进保留 + 消除模板注入；错误信息补状态/事件；BOM/`isdecimal`/stdout 编码修复
  - [x] 4.4：补齐上述全部回归用例（含 review 后新增的 `control_stage` 缩进保留用例）
  - [x] 4.5：`standard` 档 `workflow-code-review` + `workflow-verification`（`--spec-drift-reason`）均 `PASS`，按裁决修复 4 项 P2

### Review 修复记录（任务 4）

- 2026-07-12：`standard` 档三维度独立 review（工程规范 / 健壮性 / 需求符合度），零 P0/P1。裁决并修复 4 项 P2：
  1. `_validate_dependencies`/`_recovery_action_for` 两处新增 docstring 超 80 字符行长 → 精简改写，均已 ≤80 字符。
  2. `sys.stdout.reconfigure()` 在 `try` 块外、异常路径未 fail-closed → 移入 `try` 块，走统一 `except (OSError, ValueError)` 出口。
  3. `test_update_task_state_preserves_existing_indentation` 未覆盖 `control_stage` 字段已存在时的缩进保留路径 → 补 `test_update_task_state_preserves_existing_control_stage_indentation` 用例。
  4. `main()` 函数 79 行超 std-python 50 行上限（既存超限被本次边际加重）→ 拆出 `_build_arg_parser()` 承载 subparsers 构造，`main()` 降至 50 行。
- 记录但不改代码：`_require_completed_dependencies` 设计决策原文误写「类」，代码实现为函数，与 spec.md 4.2.1「不建立 WorkflowEngine 类」的既定架构一致，判定为 tasks.md 表述用词不准确（已在本条更新时顺手修正引用）。
- Handoff（记录不阻塞，供后续参考）：`_require_completed_dependencies` 内重复调用 `_states(tasks)` 有轻微重复计算；`plan_recovery` 对「进行中+未过质量门却已合并」当前判定为 `complete`（现有测试已断言为预期行为），是否收紧为矛盾属产品语义决策；需人工状态目前只能靠 `manual_resolved` 跳完成、无「人工修复后重跑质量门」的返回路径，是设计选择。

### 任务 5（文档同步，主会话直接执行，不下放 agent）

> 说明：`.md` 非代码文件，不受本 skill「必须 agent 下放」约束，仅在此记录范围便于追溯。Task 4 合并后由主会话直接改，改前按 `md-zh` 自查。

- 文件：`agentic-framework/skills/workflow-code-generation/reference/delegated-execution-guide.md`、`agentic-framework/skills/workflow-verification/SKILL.md`、`agentic-framework/skills/workflow-code-review/SKILL.md`（若涉及）、`agentic-framework/skills/workflow-code-generation/SKILL.md`、`agentic-framework/docs/design-docs/workflow-code-generation/deterministic-control-flow/spec.md`
- 范围：新事件（`manual`/`manual_resolved`）语义写入 guide 恢复中断章节；guide:74 语序调整避免诱导 strict 过早持久化 `quality_passed`；guide:113 句号后多余空格；guide:146 数字与中文间空格回归；SKILL.md:109 的 `args.waves` 契约措辞修正（int 数组→富化 task 对象）+ 加粗包裹句号修正；spec.md 补 `control_stage` 字段、新事件设计、§7.1 两个测试场景说明、§7.3 100 任务用例说明、:70 半角括号改全角、Changelog 追加本轮修复记录、归档状态复位为 `Archived`。

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
| --- | --- | --- |
| 4.1 | Task 2 | 编排层接入控制流内核 |
| 4.2 | Task 1 | 模块、接口、数据与错误处理 |
| 4.3 | Task 1、2 | 核心算法和实际入口 |
| 4.4～6 | Task 3 | 取舍与限制记录 |
| 7 | Task 1、3 | 单元和集成验证 |
| 8～9 | Task 3 | 运维说明与变更记录 |
