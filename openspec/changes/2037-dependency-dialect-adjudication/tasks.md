# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：先固化两轨现行解析差异（Task 1），再统一规则（Task 2），活跃文件修正与归档清单分开（Task 3、Task 4），最后同步规格（Task 5）。本 Change 是**收紧**，与 change 2035 的放宽方向相反，每一处状态翻转都必须逐条判定，不允许「批量接受」。

## 依赖关系总览

```
Task 1 (冻结两轨解析差异基线)
   │
   └──> Task 2 (统一为严格式)
          ├──> Task 3 (修正活跃文件)
          └──> Task 4 (归档已知失败清单)
                 │
          Task 3 ┴──> Task 5 (规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3, Task 4} → W4 = {Task 5}

> Task 3 改 `tasks.md` 内容，Task 4 只产出清单不改文件，无写入冲突，可并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 修改 | Task 2 | 依赖解析改为严格式，不再静默产出 ID |
| `openspec/changes/2-add-verify-ignore/tasks.md` | 修改 | Task 3 | 唯一不合规的活跃文件 |
| `openspec/changes/archive/**/tasks.md` | 不改 | Task 4 | 只列清单，逐字节不动 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 5 | 记录方言裁决与范围豁免 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 实测规模 | Task 1 | 基线复核 |
| `proposal.md` §6.1 方向 | Task 2 | 收敛到严格式 |
| `proposal.md` §6.3 未裁决项 | Task 2 | 空值写法裁决 |
| `proposal.md` §7 验收标准 5、9 | Task 3 | 活跃文件修正与依赖图不变 |
| `proposal.md` §6.2、§7 验收标准 6-7 | Task 4 | 归档范围豁免 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `workflow-control` | `openspec/specs/backend/framework/workflow-control/overview.md` | 待定 | 未开始 | 由 Task 1 确认是否记载依赖语义 |

## 知识冲突

- 状态: 待交付时填写。已知需记录：`framework-unification.md` §3.3 把 Archive 定为「仅作为历史证据」，而 change 2035 的 golden 基线覆盖归档；本 Change 的收紧会让归档在基线中出现失败。两者不是矛盾，但豁免方式必须显式记录，不得靠「归档不跑门禁」的隐含假设。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认 `openspec/changes/archive/` 下无任何改动。

---

### 任务 1：[ ] 冻结两轨依赖解析差异基线

- 状态: 未开始
- depends_on: 无
- review_profile: standard
- 文档映射：`proposal.md` §2 实测规模
- 文件：无（只读测量，产出写入本 Change）
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`openspec/changes/`
- artifacts: 逐条依赖声明的两轨解析结果对照表
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 复核实测数字：依赖字段声明总数 107，空值 18，符合严格式 52，不符合 37。数字不符时以实测为准并记录差异。
    - [ ] 逐条列出 37 处不合规声明：文件、行号、原始取值、Tooling 现解析出的 ID 集合。
    - [ ] 标注每条属于活跃还是归档。
    - [ ] 找出「Tooling 静默误解析」的实例：解析出的 ID 不存在于该文件任务集合的条目，单独列出。
    - [ ] 确认 `openspec/specs/backend/framework/workflow-control/overview.md` 是否记载依赖解析语义，记录结论。
    - [ ] 记录 `[]`、`无`、`none` 三种空值写法在两轨下的现行判定与出现次数。

### 任务 2：[ ] 统一依赖解析为严格式

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 方向、§6.3 未裁决项
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、Task 1 的对照表
- artifacts: `skills/workflow-code-generation/scripts/lint_task_deps.py`、新增用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] Tooling 的依赖解析接受集合与 Production 的 `DEPENDENCY_RE` 一致；不合规值报错，不再静默产出 ID。
    - [ ] `re.findall(r"\d+")` 不再作为依赖提取的唯一手段。
    - [ ] 新增用例：`见 2035 第 3 节` 一类自由文本判为不合规。
    - [ ] 新增用例：`Task 1, Task 2`、`任务 1、任务 2`、`Task1,Task2` 等合规写法两轨产出相同 ID 集合。
    - [ ] 裁决 `[]` 是否保留为合法空值并写入 `design.md` 或本任务记录；裁决结果两轨一致，有用例。
    - [ ] Production 侧零改动，OPSX023 的判定对既有用例完全不变。
    - [ ] 全部活跃 Change 的 `_kahn_waves` 波次输出与改动前逐一比对，无变化。
    - [ ] 逐条列出因本任务从通过转为失败的条目，每条附判定；不允许「批量接受」。

### 任务 3：[ ] 修正活跃 Change 的不合规依赖声明

- 状态: 未开始
- depends_on: Task 2
- review_profile: standard
- 文档映射：`proposal.md` §7 验收标准 5、9
- 文件：`openspec/changes/2-add-verify-ignore/tasks.md`
- context_files: Task 1 的对照表、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- artifacts: 修正后的活跃 `tasks.md`、依赖图前后对照
- verification: `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2-add-verify-ignore/tasks.md`
- 验收标准：
    - [ ] 以 Task 1 的清单为准确定活跃文件范围，不凭 `proposal.md` 的预估数量。
    - [ ] 每处修正只改写法，不改依赖语义；修正前后该文件的依赖 ID 集合逐一比对无变化。
    - [ ] 若某处修正会改变依赖语义（例如原文本被误解析出多余 ID），单独标注并说明修正后的语义为何是正确的那个。
    - [ ] 修正后全部活跃 Change 的 `tasks.md` 通过 `lint_task_deps.py`，errors=0。
    - [ ] 不顺手改动这些文件的其他内容。

### 任务 4：[ ] 产出归档已知失败清单

- 状态: 未开始
- depends_on: Task 2
- review_profile: standard
- 文档映射：`proposal.md` §6.2 范围豁免、§7 验收标准 6-7
- 文件：无（只读，清单写入本 Change）
- context_files: `openspec/changes/archive/`、Task 1 的对照表、`openspec/specs/backend/engineering/tech/framework-unification.md`
- artifacts: 归档已知失败清单（文件、不合规取值、豁免理由）
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 逐一列出受影响的归档文件，附具体不合规取值，不只给文件名。
    - [ ] 每个文件附豁免理由，引用 §3.3「Archive 仅作为历史证据」。
    - [ ] 明确豁免方式是**调用方范围豁免**，解析器中不含任何按路径放宽的分支。
    - [ ] 验证解析器实现中确无 `archive` 路径判断，用检索证明。
    - [ ] 确认 `openspec/changes/archive/` 下逐字节未改动。
    - [ ] 清单可被 change 2035 的 golden 基线直接引用为「已知失败」输入。

### 任务 5：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 3, Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2037-dependency-dialect-adjudication/proposal.md`、Task 4 的归档清单
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] 记录依赖方言已统一为严格式，附两轨实现出处。
    - [ ] 记录归档范围豁免的方式与理由，明确规则唯一、豁免在调用方。
    - [ ] 若 Task 1 确认 `workflow-control/overview.md` 记载了依赖语义，一并同步。
    - [ ] 不改动 §3.3 对 Archive 的定位。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
