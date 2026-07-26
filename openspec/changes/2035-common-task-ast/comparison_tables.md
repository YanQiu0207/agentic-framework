# 前后对照表（change 2035 交付证据）

> 生成时间：2026-07-26。对照双方均为同一仓库内容下的两次运行，唯一变量是待验收的代码改动。
> 基线文件：`gate_before.json`（迁移前）、`gate_after.json`（AST 迁移后、Task 6 前）、`gate_task6.json`（Task 6 后）、`equivalence_before.json`／`equivalence_after.json`（解析输出快照）。

## 1. Task 1–5 零行为变更证据

| 对照 | 结果 | 判据 |
| --- | --- | --- |
| 合成 fixtures golden 基线 | 迁移后重跑逐字节相同 | `scripts/test_task_ast_equivalence.py` 通过 |
| 全仓库 tasks.md 解析输出（34 个文件，活跃＋归档不抽样） | `equivalence_before.json` 与 `equivalence_after.json` 逐字节相同 | 零行为变更 |
| 全部门禁（31 个 Change × plan／delivery 两阶段） | 错误数与错误编号集合逐一相同（`gate_before.json` vs `gate_after.json`） | 零行为变更 |
| `python -m pytest scripts -q` | 412 passed, 21 skipped | 全量回归通过 |
| `python scripts/lint_skill_graph.py` | errors=0 | 图完整性 |

## 2. Task 6 Review Profile 字段名双写法（显式放宽）

Production 门禁（`gate_after.json` vs `gate_task6.json`，同一仓库内容）：

| 方向 | 数量 | 说明 |
| --- | --- | --- |
| 错误减少 | 42 项（Change × 阶段） | 全部为 OPSX037 因接受 `review_profile` 写法而消失 |
| 错误增加 | 0 项 | 单向翻转成立 |

Tooling 字段校验（34 个 tasks.md、153 个任务，旧语义 = 大小写敏感单写法）：

| 方向 | 数量 | 说明 |
| --- | --- | --- |
| 失败 → 通过 | 15 个任务 | 归档中使用 `- Review Profile:` 写法的任务 |
| 通过 → 失败 | 0 个任务 | 单向翻转成立 |

### 2.1 实施中发现的同值双写法实例与处理

归档 `2028-2026-07-25-tooling-native-first` 与 `2026-07-19-knowledge-management-review-fixes` 的每个任务同时声明 `- review_profile: standard` 与 `- Review Profile: standard`（同值）。初版实现以「匹配数 != 1 即报错」处理，把这两处原本通过的翻转成失败，违反单向约束。修正为 `_review_profile_value`：两种写法取值相同则接受、不同则报错；完全同形的重复声明维持原基数报错。修正后单向翻转成立（上表）。

## 3. Task 7 任务状态取值归一（显式放宽）

实测前提复核（2026-07-26，AST 元数据区内全部 `- 状态:` 行，34 个 tasks.md 共 148 行）：

| 前提 | 实测 | 结论 |
| --- | --- | --- |
| Production 集合是 Tooling 严格超集 | Tooling 五项全部落在 Production 前缀集合内（`完成` → completed，其余 → other） | 成立 |
| 全仓库取值 Production 判非法 | 0 个 | 成立 |
| 全仓库取值 Tooling（旧）判非法 | 7 个，全部为 `已完成` | 成立 |

翻转明细（旧语义 = 仅五个规范值前缀匹配）：

| 文件 | 任务 | 取值 | 旧判定 | 新判定 |
| --- | --- | --- | --- | --- |
| `archive/2030-2026-07-25-approval-gate-hardening/tasks.md` | 1、2、3 | `已完成` | 非法 | `完成` |
| `archive/2032-2026-07-26-task-status-consistency-gate/tasks.md` | 1、2、3、4 | `已完成` | 非法 | `完成` |

反向翻转（通过 → 失败）：0 个。`TERMINAL_STATES` 与 `NEEDS_REASON` 未改动，未引入第六个规范值。

## 4. 已知语义分歧声明（委托层的收紧／放宽点）

以下为设计已知的两轨解析分歧，迁移后保留为「一份 AST 加两个显式收紧／宽松层」，零语料影响（golden 与门禁对照均覆盖）：

| 分歧点 | 旧行为 | 新行为 | 影响 |
| --- | --- | --- | --- |
| 同一任务多个依赖字段行 | Production 跨全部行累积依赖 | 取 depends_on 优先的单字段 | 全仓库零命中；方向与 change 2037 严格式一致 |
| 依赖字段名大小写 | Tooling 大小写敏感 | 大小写不敏感（与 Production `DEPENDENCY_RE` 对齐） | 全仓库零命中；防止大小写变体绕过 OPSX023 |
| 依赖行位于围栏内或子标题后 | 两侧旧实现均扫原始块 | 取围栏剔除后、标题终止前的元数据区 | 全仓库零命中（golden 的围栏伪任务头用例验证区域行为一致） |
