# Proposal：提取只读公共 Task AST

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：common-task-ast
**状态**：Draft

---

## 1. 问题

`framework-unification.md` §8.2 规定，只有同时出现三条信号才重新评估公共 AST。三条现已全部满足。

**触发条件 1：同一解析缺陷必须在两个实现重复修复。**

change 2032 为收窄任务元数据判定区域，在两个文件各写了一份 `_metadata_region`，函数名相同、逻辑逐行对应：

| 维度 | `scripts/validate_change.py:570-590` | `skills/workflow-code-generation/scripts/lint_task_deps.py:124-141` |
| --- | --- | --- |
| 函数名 | `_metadata_region` | `_metadata_region` |
| 围栏处理 | ` ``` ` 与 `~~~` 配对 toggle 后跳过 | 相同 |
| 终止条件 | `SECTION_RE.match(line)` 即 break | `ANY_HEADING.match(line)` 即 break |
| 差异 | 按 `task.line`／`task.end_line` 切片 | 按 `start` 起至列表尾 |

两个终止正则语义近乎等价，唯一分歧是孤立的 `### ` 空标题行：`ANY_HEADING`（`^#{1,6}\s+`）匹配，`SECTION_RE`（`^(#{1,6})\s+(.+?)\s*$`）不匹配。这类分歧正是双实现长期漂移的起点。

**触发条件 2：两边至少 3 个稳定字段具有相同语义和生命周期。**

任务编号、任务头完成标记、任务体区间、`- 字段: 值` 的定位规则，四项在两个实现中语义一致且都不随 Profile 变化。

**触发条件 3：Adapter 不需要丢弃 Profile 专属状态。**

成立，代价是把 AST 的职责收窄到只做分块，不做裁决。详见 §5。

## 2. 现状分歧的实测证据

两个解析器对同一份文本的输出并不总是一致。四个合成用例的实测结果：

| 用例 | `validate_change._parse_tasks` | `lint_task_deps.parse_tasks` |
| --- | --- | --- |
| A 带状态括号、依赖带 `Task` 前缀 | `{1: (), 2: (1,)}` | `{1: (), 2: (1,)}` |
| B 任务头无状态括号 | `{}`（不识别任何任务） | `{1: (), 2: (1,)}` |
| C 依赖写裸数字 `1, 2` | `{1: ()}` | `{1: (1, 2)}` |
| D 依赖写 `[]` | `{1: ()}` | `{1: ()}` |

用例 B 与 C 的分歧会被 Production 侧的 OPSX020 与 OPSX023 大声报错，不是静默错判。但两边对「什么算一个任务」「依赖字段怎么读」的理解确实不同，这两点必须在 AST 中显式建模，而不是靠巧合对齐。

**同一概念的字段名也已经分叉。** Review Profile 在两轨的写法互不兼容：

| 轨 | 字段名 | 匹配规则 | 出处 |
| --- | --- | --- | --- |
| Tooling | `- review_profile: standard` | 字面量，无 `IGNORECASE` | `lint_task_deps.py:39` |
| Production | `- Review Profile: standard` | `Review\s+Profile`，`IGNORECASE` 但不接受下划线 | `scripts/validate_change.py:28` |

同一份 `tasks.md` 无法同时满足两者，除非把同一字段写两遍。本仓库为 Tooling Profile，故 `openspec/changes/2035-common-task-ast/tasks.md` 采用 `review_profile`，`validate_change.py --phase plan` 会因此报 OPSX037 与 OPSX038。

## 3. 目标

1. 新增 `scripts/task_ast.py`，提供只读解析：任务边界切分、任务头拆解、元数据区域切分、字段定位。
2. `lint_task_deps.parse_tasks` 与 `validate_change._parse_tasks` 改为委托 AST，对外签名与返回结构不变。
3. 零行为变更：两个实现对全仓库现有 `tasks.md` 的输出逐字节不变。
4. 消除 `_metadata_region` 的重复实现。
5. 两轨接受 Review Profile 的两种字段名写法，取值集合不变。

目标 1 至 4 零行为变更，由 golden 基线证明。目标 5 是**显式放宽**，单独成 Task 6，排在等价性证明之后，不与前四项混做。

## 4. 非目标

- **不统一依赖方言**。Production 用 `re.fullmatch` 严格校验后发 OPSX023，Tooling 用 `re.findall(r"\d+")` 宽松接受裸数字。AST 只交出依赖字段的原始字符串，两边各自解释。把这层下沉等于强制统一方言，那是行为变更。
- **不统一重复任务 ID 的处理**。Tooling 抛 `ValueError`，Production 交给 OPSX021。AST 把重复作为数据返回，不抛异常。
- **不迁移 Tooling 写状态路径**。`workflow_control.py` 的 waves、attempts、写锁与恢复不在本 Change 范围内，按 §8.3 第 4 步单独评估。
- **不改任何字段的取值集合**。`REQUIRED_FIELDS`、`TASK_STATES`、`REVIEW_PROFILES` 的合法取值一律不动；Task 6 只放宽 Review Profile 的**字段名**写法。
- **不做字段改名迁移**。既有归档与活跃 Change 的写法一律不改写。字段名双写法是转场合同，若要收敛到单一写法，另开 Change。
- **不把别名机制推广到其他字段**。`context_files`、`artifacts`、`verification`、`状态`、`depends_on` 在两轨的现状差异不在本 Change 范围。
- **不改安装器白名单**。见 §5.2。

## 5. 设计方案

### 5.1 AST 只做分块，不做裁决

这是零行为变更能成立的前提。AST 提供的是**宽松超集解析**：它识别任务头的所有形态（有无状态括号都识别），交出原始文本片段与位置信息；至于「无状态括号是否合法」「依赖串是否合规」，由各 Profile 在自己的文件里判定。

因此 §1 用例 B 的分歧不会消失，也不应消失：AST 会把两个任务都解析出来并标记 `status_raw is None`，Production 据此照旧发 OPSX020，Tooling 据此照旧走「未声明」分支。

### 5.2 共享模块放 `scripts/`，机制已存在

`check_delivery.py:31-37` 今天就在做跨目录导入：

```python
_FRAMEWORK_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(_FRAMEWORK_SCRIPTS))
import runtime_workflow, runtime_schema, workspace_residue
```

`workflow_control.py:23-24` 同理。`task_ast.py` 与 `runtime_workflow.py` 同级，导入方式完全一致，不需要新机制，也不需要改安装器——`runtime_workflow.py` 同样不在任何安装白名单里。

**未验证项**：安装到目标项目后，`Path(__file__).resolve()` 是否穿过受管链接回到源仓库、从而让 `_FRAMEWORK_SCRIPTS` 指向源仓库的 `scripts/`。本仓库未自装 `.claude/`，无法实测。但 `task_ast.py` 与 `runtime_workflow.py` 处境完全相同，本 Change 不引入新风险；若该路径实际有问题，那是既有缺陷，另开 Change。

### 5.3 关键权衡

**为什么不让 AST 直接产出依赖 ID 集合。** 那样两边代码更短，但会把「依赖方言」这个 Profile 差异点隐式统一。Tooling 会突然开始拒绝裸数字，或 Production 会突然开始接受——无论哪个方向都是行为变更，且会与 §8.3「先冻结行为」的顺序冲突。代价是 AST 看起来「不够抽象」，这是刻意的。

**为什么同时保留行号与字符 offset。** Production 的 `Task` 用 1-based 行号，Tooling 的 `parse_tasks` 用 `match.end()` 到下一个 `match.start()` 的字符切片。强行统一坐标系会改动两边的下游逻辑，扩大回归面。AST 同时给出两套坐标，各调用方取自己需要的那套。

## 6. 验收标准

1. `scripts/task_ast.py` 存在，只提供解析，不含任何 OPSX 编号、错误消息或退出码逻辑。
2. AST 节点同时提供 1-based 行号区间与字符 offset 区间，两者对同一任务指向同一文本片段。
3. 任务头无状态括号时，AST 仍解析出该任务，并以 `status_raw is None` 表示括号缺失。
4. AST 返回依赖字段的原始字符串与字段名（`depends_on` 或遗留的 `依赖`），不做数值解析。
5. 重复任务 ID 由 AST 作为数据返回，不抛异常。
6. `lint_task_deps.parse_tasks` 委托 AST 后，返回结构仍为 `dict[int, {files, deps, has_dep_field, body}]`，重复 ID 仍抛 `ValueError`。
7. `validate_change._parse_tasks` 委托 AST 后，返回结构仍为 `(list[Task], lines)`。
8. 两个文件中的 `_metadata_region` 收敛为 AST 的单一实现，孤立 `### ` 行的边界行为有显式用例与结论。
9. golden 等价性测试：对全仓库全部 `tasks.md`（活跃与归档）加合成方言用例，改动前后两个解析器的输出逐字节相同。
10. `python -m pytest scripts -q` 全量通过，退出码 0，无既有用例回归。
11. 对全部活跃与归档 Change 跑 `validate_change.py` 的 plan 与 delivery 双阶段，错误数与改动前逐一相同。
12. 两轨均接受 `- review_profile:` 与 `- Review Profile:` 两种写法，匹配规则限定为大小写不敏感加 `_` 与空格等价；同一任务同时出现两种写法且取值不同时报错。
13. Task 6 的放宽只允许「原本失败转为通过」，不允许「原本通过转为失败」；全仓库 `tasks.md` 的双轨通过状态前后对照表写入本 Change。

## 7. 知识影响

- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§8.2 记录三条触发条件已满足及其证据；§8.3 标注第 1 至 3 步完成、第 4 步（Tooling 写状态路径）未启动；补记 Review Profile 字段名双写法合同，并明确这是放宽而非收敛。

## 8. 参考资料

- 重复实现现场：`scripts/validate_change.py:570-590`、`skills/workflow-code-generation/scripts/lint_task_deps.py:124-141`
- 提取条件与顺序：`openspec/specs/backend/engineering/tech/framework-unification.md` §8.2、§8.3
- 共享模块导入先例：`skills/workflow-code-generation/scripts/check_delivery.py:31-37`、`skills/workflow-code-generation/scripts/workflow_control.py:23-24`
- Production 解析入口：`scripts/validate_change.py:165`（`Task`）、`:427-462`（`_parse_tasks`）
- Tooling 解析入口：`skills/workflow-code-generation/scripts/lint_task_deps.py:68-88`
- 触发来源：change 2032（任务状态三向一致门）
