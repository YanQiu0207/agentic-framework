# 实施任务清单

> 由 proposal.md / design.md 生成
> 任务总数：8
> 核心原则：先冻结行为基线（Task 1），再建 AST（Task 2），两轨迁移互不依赖可并行（Task 3、Task 4），门禁级等价核对兜底（Task 5）。Task 1 至 Task 5 必须零行为变更；Task 6 与 Task 7 是两处显式放宽，都排在等价性证明之后，不污染基线。文档最后同步（Task 8）。

## 依赖关系总览

```
Task 1 (冻结 golden 基线)
   │
   └──> Task 2 (task_ast.py)
          │
          ├──> Task 3 (Tooling 迁移)  ─┐
          │                            ├──> Task 5 (全量回归与门禁核对)
          └──> Task 4 (Production 迁移)┘        │
                                                └──> Task 6 (字段名别名，显式放宽)
                                                       │
                                                       └──> Task 7 (状态取值放宽)
                                                              │
                                                              └──> Task 8 (规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3, Task 4} → W4 = {Task 5} → W5 = {Task 6} → W6 = {Task 7} → W7 = {Task 8}

> Task 3 与 Task 4 改不同文件，无写入冲突，可并行。Task 6 再次修改这两个文件，Task 7 修改 `lint_task_deps.py`，都靠依赖链串行，不构成并行冲突。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/tests/fixtures/task_ast/` | 新增 | Task 1 | 合成方言语料 |
| `scripts/test_task_ast_equivalence.py` | 新增 | Task 1, Task 5 | golden 基线与等价性断言 |
| `scripts/task_ast.py` | 新增 | Task 2 | 只读公共解析模块 |
| `scripts/test_task_ast.py` | 新增 | Task 2 | AST 单元测试 |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 修改 | Task 3, Task 6, Task 7 | 委托 AST，删除本侧 `_metadata_region`；接受字段名别名；状态取值归一 |
| `scripts/validate_change.py` | 修改 | Task 4, Task 6 | 委托 AST，删除本侧 `_metadata_region`；接受字段名别名 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 8 | §8.2 触发条件已满足、§8.3 进度标注、字段名与取值集合合同 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `design.md` §5 等价性验证方法 | Task 1, Task 5 | 基线生成与四步比对 |
| `design.md` §2 节点契约 | Task 2 | 字段、双坐标与不变式 |
| `design.md` §4.1 Tooling 侧 | Task 3 | 委托方式与保留的公开函数 |
| `design.md` §4.2 Production 侧 | Task 4 | 委托层收紧回严格度 |
| `design.md` §3 放置与导入 | Task 2, Task 3 | 模块位置与跨目录导入 |
| `proposal.md` §6 验收标准 1-5 | Task 2 | AST 本体 |
| `proposal.md` §6 验收标准 6 | Task 3 | Tooling 签名不变 |
| `proposal.md` §6 验收标准 7 | Task 4 | Production 签名不变 |
| `proposal.md` §6 验收标准 8 | Task 3, Task 4 | `_metadata_region` 收敛 |
| `proposal.md` §6 验收标准 9-11 | Task 5 | golden、全量测试、门禁核对 |
| `design.md` §7 字段名合同 | Task 6 | 别名归一与显式放宽的证据要求 |
| `proposal.md` §6 验收标准 12-13 | Task 6 | 别名接受与放宽方向约束 |
| `design.md` §7 字段名合同（同型） | Task 7 | 状态取值归一与放宽方向约束 |
| `proposal.md` §7 知识影响 | Task 8 | 长期规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。当前已知需核对项：`framework-unification.md` §8.2 现文表述为「第一阶段不提取共享解析模型」，本 Change 不否定该结论，而是记录三条重新评估条件已满足。两者是「条件未满足时不提取」与「条件已满足故提取」的先后关系，非矛盾；交付时需确认改写后仍保留原判断依据。

## 实际 Diff 核对

- 待交付时填写。

---

### 任务 1：[ ] 冻结解析行为 golden 基线

- 状态: 未开始
- depends_on: 无
- review_profile: standard
- 文档映射：`design.md` §5 等价性验证方法
- 文件：`scripts/tests/fixtures/task_ast/`、`scripts/test_task_ast_equivalence.py`
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`openspec/changes/`
- artifacts: `scripts/test_task_ast_equivalence.py`、`scripts/tests/fixtures/task_ast/*.md`、golden JSON
- verification: `python -m pytest scripts/test_task_ast_equivalence.py -q`
- 验收标准：
    - [ ] 语料覆盖全仓库 `openspec/changes/**/tasks.md`（活跃与归档全部纳入，不抽样）。
    - [ ] 合成语料覆盖：任务头无状态括号、空状态括号 `[]`、依赖写裸数字、依赖写 `[]`、依赖用 `depends_on` 与遗留 `依赖`、重复任务 ID、代码围栏内的伪任务头、孤立 `### ` 空标题行。
    - [ ] 基线记录 Production 侧 `(number, status, description, line, end_line, dependencies)`。
    - [ ] 基线记录 Tooling 侧 `(tid, sorted(deps), has_dep_field, len(body))`。
    - [ ] 解析抛异常的输入，把异常类型与消息一并记入基线，不跳过。
    - [ ] 基线 JSON 提交入库；测试在当前代码上通过，退出码 0。
    - [ ] 连续两次生成基线，输出逐字节相同（无字典序或路径序不稳定）。

### 任务 2：[ ] 实现只读公共 Task AST

- 状态: 未开始
- depends_on: Task 1
- review_profile: standard
- 文档映射：`design.md` §2 节点契约、§3 放置与导入
- 文件：`scripts/task_ast.py`、`scripts/test_task_ast.py`
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`skills/workflow-code-generation/scripts/check_delivery.py`
- artifacts: `scripts/task_ast.py`、`scripts/test_task_ast.py`
- verification: `python -m pytest scripts/test_task_ast.py -q`
- 验收标准：
    - [ ] `scripts/task_ast.py` 只提供解析，不含 OPSX 编号、错误消息、退出码或 `argparse`。
    - [ ] `TaskNode` 提供 `number`、`status_raw`、`description`、`line`、`end_line`、`body_start`、`body_end`、`body`、`dep_field_name`、`dep_field_raw`。
    - [ ] `TaskDocument` 提供 `tasks`、`lines`、`duplicate_ids`。
    - [ ] 状态括号整体缺失时 `status_raw is None`；括号存在但为空时 `status_raw == ""`，两者可区分。
    - [ ] `dep_field_raw` 为原始字符串，不做数值提取；`dep_field_name` 区分 `depends_on` 与遗留 `依赖`。
    - [ ] 重复任务 ID 记入 `duplicate_ids`，不抛异常。
    - [ ] 提供元数据区域切分函数：任务头下一行起至下一个任意级别标题前，代码围栏内容剔除。
    - [ ] 提供字段定位函数，区分「字段不存在」与「字段存在但值为空」。
    - [ ] 双坐标不变式有专门用例：行号区间与字符 offset 区间指向同一任务。
    - [ ] 孤立 `### ` 空标题行的区域终止行为有显式用例与结论注释（`ANY_HEADING` 与 `SECTION_RE` 在此分歧）。
    - [ ] 模块不导入 `validate_change` 或 `lint_task_deps`，无循环依赖。

### 任务 3：[ ] Tooling 侧迁移至 AST

- 状态: 未开始
- depends_on: Task 2
- review_profile: standard
- 文档映射：`design.md` §4.1 Tooling 侧、§3 放置与导入
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/task_ast.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`skills/workflow-code-generation/scripts/workflow_control.py`
- artifacts: `skills/workflow-code-generation/scripts/lint_task_deps.py`
- verification: `python -m pytest scripts/test_lint_task_deps.py scripts/test_check_delivery.py -q`
- 验收标准：
    - [ ] `parse_tasks` 委托 AST，返回结构仍为 `dict[int, {files, deps, has_dep_field, body}]`。
    - [ ] 重复任务 ID 仍抛 `ValueError`，消息文本不变。
    - [ ] `parse_deps` 的 `re.findall(r"\d+")` 宽松语义不变，改为消费 `dep_field_raw`。
    - [ ] `field`、`has_field`、`parse_state` 保持公开且签名不变（`check_delivery.py` 直接调用）。
    - [ ] 本文件的 `_metadata_region` 删除，`state_consistency_errors` 改调 AST。
    - [ ] 按 `check_delivery.py:31-33` 的写法新增 `_FRAMEWORK_SCRIPTS` 导入段。
    - [ ] `TASK_HEADER`、`TASK_HEADER_LINE` 若不再使用则一并删除；仍被使用则保留，不留孤儿常量。
    - [ ] `workflow_control.py` 不改动，其经由 `lint_task_deps` 的调用路径行为不变。
    - [ ] `--state-consistency` 与默认模式的 CLI 输出与退出码不变。

### 任务 4：[ ] Production 侧迁移至 AST

- 状态: 未开始
- depends_on: Task 2
- review_profile: standard
- 文档映射：`design.md` §4.2 Production 侧
- 文件：`scripts/validate_change.py`
- context_files: `scripts/task_ast.py`、`scripts/tests/test_validate_change.py`
- artifacts: `scripts/validate_change.py`
- verification: `python -m pytest scripts/tests/test_validate_change.py -q`
- 验收标准：
    - [ ] `_parse_tasks` 委托 AST，返回结构仍为 `(list[Task], lines)`。
    - [ ] 委托层过滤掉 `status_raw is None` 的节点，维持 `TASK_HEADER_RE` 要求状态括号的既有严格度；OPSX020 触发条件不变。
    - [ ] 依赖去重逻辑（`tuple(dict.fromkeys(...))`）保留在本文件，改为消费 `dep_field_raw`。
    - [ ] OPSX023 的 `re.fullmatch` 校验保留在本文件，判定结果不变。
    - [ ] 本文件的 `_metadata_region` 删除，OPSX056 改调 AST。
    - [ ] `Task` dataclass 字段不变。
    - [ ] `SECTION_RE` 若仍被其他逻辑使用则保留，否则删除，不留孤儿常量。
    - [ ] OPSX020、OPSX021、OPSX023、OPSX030、OPSX031、OPSX037、OPSX056 的既有用例全部通过。

### 任务 5：[ ] 全量回归与门禁级等价核对

- 状态: 未开始
- depends_on: Task 3, Task 4
- review_profile: standard
- 文档映射：`proposal.md` §6 验收标准 9-11、`design.md` §5 第 3 至 4 步
- 文件：`scripts/test_task_ast_equivalence.py`
- context_files: `scripts/task_ast.py`、`scripts/validate_change.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- artifacts: golden 比对结果、门禁双阶段错误数对照表
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] Task 1 的 golden 基线在迁移后重跑，逐字节相同，基线文件本身未被修改。
    - [ ] 对全部活跃与归档 Change 跑 `validate_change.py --phase plan` 与 `--phase delivery`，错误数与错误编号集合与改动前逐一相同；对照表写入本 Change。
    - [ ] `python -m pytest scripts -q` 全量通过，退出码 0；通过／跳过数与基线对照记录在案。
    - [ ] `python scripts/lint_skill_graph.py` 输出 errors=0。
    - [ ] 若出现任何输出差异，记录差异内容与判定（是缺陷还是基线本身有误），不静默接受。
    - [ ] Windows 下执行需置 `PYTHONUTF8=1`，与 `verify.py` 子进程环境一致。

### 任务 6：[ ] 统一 Review Profile 字段名合同（显式放宽）

- 状态: 未开始
- depends_on: Task 5
- review_profile: standard
- 文档映射：`design.md` §7 字段名合同
- 文件：`scripts/task_ast.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`scripts/validate_change.py`
- context_files: `openspec/changes/`、`scripts/tests/test_validate_change.py`、`scripts/test_lint_task_deps.py`
- artifacts: 别名归一实现、全仓库 `tasks.md` 双轨通过状态前后对照表
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] AST 的字段定位支持别名组，`review_profile` 与 `Review Profile` 归一为同一逻辑字段。
    - [ ] 别名匹配规则限定为：大小写不敏感、`_` 与空格等价。不引入模糊匹配、缩写或前缀匹配。
    - [ ] Tooling 的 `REQUIRED_FIELDS` 校验接受两种写法。
    - [ ] Production 的 OPSX037、OPSX038、OPSX055 接受两种写法。
    - [ ] 取值集合完全不变：Tooling 仍限 `lightweight` / `standard` / `strict`，Production 仍限其既有集合。
    - [ ] 同一任务同时出现两种写法且取值不同时报错，不静默取其一。
    - [ ] 本任务是显式放宽：Task 1 的 golden 基线中原本失败的条目可转为通过，但**原本通过的不得转为失败**；每一条状态翻转逐条列出并判定。
    - [ ] 产出「本仓库全部 `tasks.md` 在两轨门禁下的通过状态」前后对照表，写入本 Change。
    - [ ] 不做字段改名迁移，不改写既有归档，不新增第三种写法。
    - [ ] 别名只覆盖 Review Profile 这一个字段；`context_files`、`artifacts`、`verification`、`状态`、`depends_on` 的现状差异不在本任务范围。

### 任务 7：[ ] 统一任务状态取值集合（显式放宽）

- 状态: 未开始
- depends_on: Task 6
- review_profile: standard
- 文档映射：`design.md` §7 字段名合同（同型放宽，取值集合版）
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`openspec/changes/`
- artifacts: 取值归一实现、全仓库任务状态取值前后判定对照表
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 实测前提复核：Production 的取值集合是 Tooling 的严格超集。Tooling `TASK_STATES`（`lint_task_deps.py:38`）五项全部落在 Production 的 `COMPLETED_STATE_PREFIXES` 或 `OPEN_STATE_PREFIXES`（`validate_change.py:91-101`）内。
    - [ ] 实测基线复核：全仓库任务元数据区 104 个状态取值中，Tooling 判非法 7 个（全部为 `已完成`），Production 判非法 0 个。
    - [ ] `parse_state` 改为归一化：接受 Production 集合的全部取值，返回 Tooling 的规范值。映射为 `已完成`／`completed`／`complete`／`done`／`x` → `完成`；`pending` → `未开始`；`in progress`／`in-progress` → `进行中`；`blocked` → `阻塞`。
    - [ ] `TERMINAL_STATES` 与 `NEEDS_REASON` 不改动。归一后 `已完成` 返回 `完成`，本就是终态，不需要扩表。
    - [ ] **原因抽取按原始匹配前缀长度切片，不得按规范值长度切片。** `check_delivery.py:63` 现为 `value[len(state):]`；归一后 `state` 是规范值而 `value` 是原始值，长度不再对应，`blocked 依赖外部审批` 一类取值会被切错。
    - [ ] `workflow_control.py` 的写回路径不改动，仍只产出五个规范值。本任务只放宽读侧校验，不引入写侧同义词。
    - [ ] 本任务是显式放宽：原本失败的条目可转为通过，**原本通过的不得转为失败**；每一条状态翻转逐条列出并判定。
    - [ ] Production 侧零改动——其集合已是超集，无需放宽。
    - [ ] 产出全仓库任务状态取值在两轨下的判定前后对照表，写入本 Change。
    - [ ] 不改写既有归档，不新增第六个规范值。

### 任务 8：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 7
- review_profile: standard
- 文档映射：`proposal.md` §7 知识影响
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2035-common-task-ast/proposal.md`、`openspec/changes/2035-common-task-ast/design.md`
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] §8.2 记录三条重新评估条件已满足，附 `_metadata_region` 重复实现的文件与行号证据。
    - [ ] §8.2 保留「条件未满足时不提取」的原判断依据，不改写为「当初判断有误」。
    - [ ] §8.3 标注第 1 至 3 步完成、第 4 步（Tooling 写状态路径）未启动。
    - [ ] §8.1「不建设巨型统一引擎」的结论不改动，本 Change 未合并两套控制逻辑。
    - [ ] 记录 Review Profile 字段名的双写法合同，并明确这是放宽而非收敛，未来若要收敛需单独 Change。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版：中英文空格、中文与数字空格、全角中文标点、专有名词大小写。
