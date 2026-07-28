# Design：提取只读公共 Task AST

**变更**：common-task-ast
**日期**：2026-07-26

---

## 1. 职责边界

AST **拥有**四件事，这四件正是两个实现当前重复的部分：

1. **任务边界切分**：从整份文本中定位每个 `### 任务 N` 块的起止。
2. **任务头拆解**：编号、状态括号内原文、括号后的描述。
3. **元数据区域切分**：任务头下一行起，到下一个任意级别标题之前，剔除代码围栏内容。
4. **字段定位**：`- <名称>: <值>` 的定位与取值，含字段存在但值为空的区分。

AST **不拥有**任何裁决：

| 判定 | 归属 | 位置 |
| --- | --- | --- |
| 状态括号缺失是否违规 | Production | OPSX020 |
| 依赖串格式是否合规 | Production | OPSX023 |
| 依赖串数值如何提取 | Tooling | `parse_deps` |
| 重复任务 ID 如何处理 | 各自 | Tooling 抛 `ValueError`；Production 走 OPSX021 |
| 状态取值是否合法 | 各自 | Tooling `parse_state`（`lint_task_deps.py:91`）；Production `_state_field_kind`（`validate_change.py:593`） |
| 三向一致性 | 各自 | Tooling `state_consistency_errors`；Production OPSX056 |

## 2. 节点契约

```text
TaskNode
    number          int          任务编号
    status_raw      str | None   状态括号内原文；None 表示整个括号缺失
    description     str          括号后（或冒号后）的剩余文本，已 strip
    line            int          任务头行号，1-based
    end_line        int          下一个任务头行号（或文件末尾），1-based 半开
    body_start      int          任务头行结束处的字符 offset
    body_end        int          下一个任务头起始处的字符 offset（或文本长度）
    body            str          text[body_start:body_end]
    dep_field_name  str | None   实际出现的依赖字段名：depends_on 或 依赖
    dep_field_raw   str | None   依赖字段的原始值，未解析；字段缺失时为 None

TaskDocument
    tasks           list[TaskNode]      按出现顺序
    lines           list[str]           text.splitlines()
    duplicate_ids   list[int]           重复出现的编号，按首次重复顺序
```

### 2.1 两套坐标必须同时提供

Production 的 `Task` 用 1-based 行号（`line`、`end_line`），下游的区域切分、复选框扫描全部按行操作。Tooling 的 `parse_tasks` 用字符 offset 切出 `body`，下游 `field()` 在 `body` 上跑 `re.MULTILINE`。

统一到单一坐标系会改动两边的下游逻辑，扩大回归面，与「零行为变更」冲突。AST 两套都给，各取所需。

**不变式**：`"\n".join(lines[line - 1 : end_line - 1])` 与 `text[body_start:body_end]` 覆盖同一任务，仅差任务头行本身与末尾换行。该不变式需有专门用例。

### 2.2 `status_raw is None` 与空串的区分

- `### 任务 1：实现` → `status_raw is None`，括号整体缺失。
- `### 任务 1：[] 实现` → `status_raw == ""`，括号存在但内容为空。

Production 的 `TASK_HEADER_RE` 要求括号必须存在，前者不匹配（导致该任务整体不被识别，进而触发 OPSX020）；Tooling 的 `TASK_HEADER_LINE` 括号可选，前者按「未声明」处理。两边靠同一个 `None` 信号各自分流，语义不丢。

## 3. 放置与导入

模块路径：`scripts/task_ast.py`。

调用方导入方式沿用既有先例：

```python
# skills/workflow-code-generation/scripts/lint_task_deps.py
_FRAMEWORK_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_FRAMEWORK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_SCRIPTS))
import task_ast
```

`validate_change.py` 本就在 `scripts/` 内，直接 `import task_ast`。

`lint_task_deps.py` 目前没有 `_FRAMEWORK_SCRIPTS` 这段（它只从自身目录导入），需要新增，写法与 `check_delivery.py:31-33`、`workflow_control.py:23-24` 完全一致。

## 4. 两个调用方的委托方式

### 4.1 Tooling 侧

`parse_tasks` 改为：

```text
doc = task_ast.parse(text)
if doc.duplicate_ids: raise ValueError(f"重复任务 ID: {doc.duplicate_ids[0]}")
逐节点构造 {"files": ..., "deps": ..., "has_dep_field": ..., "body": node.body}
```

`parse_deps` 的实现原样保留在 `lint_task_deps.py`，但改为消费 `node.dep_field_raw` 与 `node.dep_field_name`，不再自己扫 `body`。`field`、`has_field` 保留为公开函数——`check_delivery.py` 直接调用它们（`check_tasks` 用 `lint_task_deps.field(info["body"], "状态")`），签名不能动。

`state_consistency_errors` 改为消费 `doc`，`_metadata_region` 删除，改调 AST。

### 4.2 Production 侧

`_parse_tasks` 改为：

```text
doc = task_ast.parse(text)
只保留 status_raw is not None 的节点  ← 维持 TASK_HEADER_RE 要求括号的既有行为
逐节点构造 Task(number, status=status_raw, description, line, end_line, dependencies)
返回 (tasks, doc.lines)
```

**关键点**：过滤 `status_raw is None` 是维持零行为变更的必要步骤。AST 宽松识别，Production 在委托层收紧回原有严格度。

`dependencies` 的解析（去重、`tuple(dict.fromkeys(...))`）留在 `validate_change.py`，消费 `node.dep_field_raw`。OPSX023 的 `re.fullmatch` 同样留在原处。

`_metadata_region` 删除，改调 AST。

## 5. 等价性验证方法

单靠单元测试不足以证明零行为变更，需要 golden 基线：

1. **输入集**：全仓库 `openspec/changes/**/tasks.md`（活跃 + 归档）、两边测试目录中已有的 fixture、§2 的合成方言用例（无括号、空括号、裸数字依赖、`[]` 依赖、重复 ID、围栏内伪任务头、孤立 `### ` 行）。
2. **基线生成**：在改动前用**当前**两个解析器跑全部输入，把 `(number, status, description, line, end_line)` 与 `(tid, sorted(deps), has_dep_field, len(body))` 序列化成 JSON。
3. **改动后比对**：同一脚本重跑，逐字节 diff。
4. **门禁级验证**：对全部活跃与归档 Change 跑 `validate_change.py --phase plan` 与 `--phase delivery`，错误数与错误编号集合逐一比对。

第 4 步是必须的——单测覆盖不到 OPSX020 至 OPSX056 全链路对解析输出的依赖。

## 6. 关键权衡

**AST 抽象度刻意压低。** 一个「更好」的 AST 会直接产出 `set[int]` 依赖、归一化状态枚举、统一坐标系。这里全部不做，因为每一项都会隐式统一一个 Profile 差异点，把行为变更混进结构重构。`framework-unification.md` §8.3 明确要求「先冻结两边现有 Fixtures 和行为」，抽象度是后续步骤的事。

**双坐标是已知的冗余。** `line`／`end_line` 与 `body_start`／`body_end` 描述同一件事。接受这个冗余，换取两边下游代码零改动。若后续 Tooling 写状态路径也迁移完毕，可再评估收敛到单一坐标。

**Tooling 侧新增跨目录导入是净增的耦合。** `lint_task_deps.py` 原本只依赖标准库，改动后依赖框架根 `scripts/`。这与 `check_delivery.py`、`workflow_control.py` 的现状一致，不是新模式，但确实让 `lint_task_deps.py` 不再能独立复制使用。判断：可接受，因为它本就与 `check_delivery.py` 同目录且被后者导入。

## 7. 字段名合同

Review Profile 在两轨的字段名互不兼容：

| 轨 | 写法 | 正则 | 出处 |
| --- | --- | --- | --- |
| Tooling | `- review_profile: standard` | `^\s*-\s*review_profile\s*[:：]`，无 `IGNORECASE` | `lint_task_deps.py:39` 与 `field`／`has_field` |
| Production | `- Review Profile: standard` | `^-\s*Review\s+Profile\s*[:：]\s*(\S.*?)\s*$`，`IGNORECASE` | `scripts/validate_change.py:28` |

`IGNORECASE` 不解决问题：Production 要求 `Review` 与 `Profile` 之间是**空白**，下划线不匹配。

### 7.1 选择放宽而不是改名

三个选项：

| 方案 | 后果 |
| --- | --- |
| 统一为 `review_profile` | 全部 Production 归档立刻失效，需要批量改写历史 |
| 统一为 `Review Profile` | 全部 Tooling 归档立刻失效，同上 |
| **两边都接受两种写法** | 原本失败的转为通过，原本通过的不受影响 |

选第三个。它是唯一可以用 Task 1 的 golden 基线证明「没有变紧」的方案：放宽的正确性判据是**状态翻转只允许单向**，这个判据可机械核对。

### 7.2 别名规则的边界

归一规则严格限定为两条：大小写不敏感、`_` 与空格等价。不引入前缀匹配、缩写、模糊匹配或标点归一——每多一条规则就多一类误匹配，而这个字段直接决定 Review 档位。

同一任务同时出现两种写法时：取值相同则接受，取值不同则报错。不静默取第一个——「哪个才算真」的矛盾必须暴露，这与 change 2032 对重复 `- 状态：` 声明的处理一致。

### 7.3 为什么排在 Task 5 之后

Task 1 至 Task 5 的价值全部来自「零行为变更」这个可证明的性质。把一个放宽混进去，golden 基线就会出现预期内的差异，而「预期内的差异」和「回归」在比对结果里长得一模一样。分开做，前五个任务的基线保持全等，Task 6 的基线差异逐条列出并判定。

### 7.4 不推广到其他字段

`context_files`、`artifacts`、`verification`、`状态`、`depends_on` 在两轨也有差异（有的只存在于一侧，`状态` 的合法取值集合两边不同），本 Change 一律不碰。字段名放宽和**取值集合**统一是两件事，后者必然破坏既有文件，需要独立的迁移方案。

## 8. 已知限制

- **不解决解析器分歧本身**。用例 B、C 的行为差异在本 Change 后依然存在，只是分歧点从「两份代码各自实现」变成「一份 AST 加两个显式的收紧／宽松层」。分歧是否应该消除，是独立的策略问题。
- **安装态导入路径未实测**。见 proposal §5.2。
- **`workflow_control.py` 不迁移**。它通过 `lint_task_deps` 间接受益于 AST，但自身的写状态路径不动，两套 Tasks 控制逻辑仍未合并——这符合 `framework-unification.md` §8.1「不建设巨型统一引擎」。
- **golden 基线依赖当前仓库内容**。仓库内 `tasks.md` 的方言覆盖不一定完整，合成用例是补充而非穷举。
