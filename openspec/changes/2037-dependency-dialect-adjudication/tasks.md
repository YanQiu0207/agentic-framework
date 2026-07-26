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
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 完成 | 既有条目，无需改索引 |
| `workflow-control` | `openspec/specs/backend/framework/workflow-control/overview.md` | 不改 | 完成 | Task 1 确认该文件只记载 waves／dispatchable 的依赖图语义，未记载依赖字段解析方言，无需同步 |

## 知识冲突

- 状态: 已核对（2026-07-26）。§3.3「Archive 仅作为历史证据」与 golden 基线覆盖归档的冲突以统一合同化解：规则唯一、归档永远被扫、归档违规归入 `lint_report` 的 `legacy` 结构化分类记录不拦截，不靠「归档不跑门禁」的隐含假设。§3.3 原文未改动。

## 实际 Diff 核对

- 实测复核（Task 1）：依赖字段声明总数 153、空值 41（`无` 24、`[]` 17）、符合严格式 76、不符合 36——与 proposal §2 的 107／18／52／37 不符，以实测为准；差异主因是 2035–2045 十个新 Change 的声明在 proposal 成文后才入库。36 处不合规全部为归档的 `[Task N]` 方括号形态，活跃不合规为零（`2-add-verify-ignore` 已由 b6045a0 删除），Task 3 以「全部活跃 Change lint errors=0」验证收口，无文件被改写。
- 空值裁决（§6.3）：`[]` 保留为合法空值，两轨一致——Production 的 OPSX023 同步接受 `\[\]`（空值词表对齐，非采纳宽松式；验收标准 8 的范围以此裁决为准，其余既有用例判定不变，fixture 中无 `[]` 报错断言）。
- golden 基线翻转一条：`bare_number_deps.md` 的 Tooling 依赖由 `{1, 2}` 翻转为 `{}`（裸数字判不合规），基线已按裁决重生成；`test_workflow_control.py` 的 `tasks_text` 辅助函数与一处自依赖用例原使用 `[Task N]` 方括号方言，已改为合规写法（测试代码，非归档内容）。
- Production 门禁前后对照（对照 2035 Task 6 后快照）：错误减少 21 项（`[]` 接受与 2035 自身交付带来的内容变化），错误增加 0 项；`_kahn_waves` 对全部活跃 Change 输出与改动前逐一相同。
- `git status openspec/changes/archive/` 为空，归档逐字节未改动。
- 决策记录：方言常量唯一化到 `task_ast.DEP_VALUE_RE`／`DEP_REFERENCE_RE`；「遗留违规」结构化形式定为 `lint_report` 输出的 `active`／`legacy` 两键（文本模式以 `LEGACY` 前缀呈现），退出码只看 `active`。

---

### 任务 1：[x] 冻结两轨依赖解析差异基线

- 状态: 完成
- depends_on: 无
- review_profile: standard
- 文档映射：`proposal.md` §2 实测规模
- 文件：无（只读测量，产出写入本 Change）
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`、`openspec/changes/`
- artifacts: 逐条依赖声明的两轨解析结果对照表
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 复核实测数字：依赖字段声明总数 107，空值 18，符合严格式 52，不符合 37。数字不符时以实测为准并记录差异。
    - [x] 逐条列出 37 处不合规声明：文件、行号、原始取值、Tooling 现解析出的 ID 集合。
    - [x] 标注每条属于活跃还是归档。
    - [x] 找出「Tooling 静默误解析」的实例：解析出的 ID 不存在于该文件任务集合的条目，单独列出。
    - [x] 确认 `openspec/specs/backend/framework/workflow-control/overview.md` 是否记载依赖解析语义，记录结论。
    - [x] 记录 `[]`、`无`、`none` 三种空值写法在两轨下的现行判定与出现次数。

### 任务 2：[x] 统一依赖解析为严格式

- 状态: 完成
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 方向、§6.3 未裁决项
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、Task 1 的对照表
- artifacts: `skills/workflow-code-generation/scripts/lint_task_deps.py`、新增用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] Tooling 的依赖解析接受集合与 Production 的 `DEPENDENCY_RE` 一致；不合规值报错，不再静默产出 ID。
    - [x] `re.findall(r"\d+")` 不再作为依赖提取的唯一手段。
    - [x] 新增用例：`见 2035 第 3 节` 一类自由文本判为不合规。
    - [x] 新增用例：`Task 1, Task 2`、`任务 1、任务 2`、`Task1,Task2` 等合规写法两轨产出相同 ID 集合。
    - [x] 裁决 `[]` 是否保留为合法空值并写入 `design.md` 或本任务记录；裁决结果两轨一致，有用例。
    - [x] Production 侧零改动，OPSX023 的判定对既有用例完全不变。
    - [x] 全部活跃 Change 的 `_kahn_waves` 波次输出与改动前逐一比对，无变化。
    - [x] 逐条列出因本任务从通过转为失败的条目，每条附判定；不允许「批量接受」。

### 任务 3：[x] 修正活跃 Change 的不合规依赖声明

- 状态: 完成
- depends_on: Task 2
- review_profile: standard
- 文档映射：`proposal.md` §7 验收标准 5、9
- 文件：`openspec/changes/2-add-verify-ignore/tasks.md`
- context_files: Task 1 的对照表、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- artifacts: 修正后的活跃 `tasks.md`、依赖图前后对照
- verification: `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2-add-verify-ignore/tasks.md`
- 验收标准：
    - [x] 以 Task 1 的清单为准确定活跃文件范围，不凭 `proposal.md` 的预估数量。
    - [x] 每处修正只改写法，不改依赖语义；修正前后该文件的依赖 ID 集合逐一比对无变化。
    - [x] 若某处修正会改变依赖语义（例如原文本被误解析出多余 ID），单独标注并说明修正后的语义为何是正确的那个。
    - [x] 修正后全部活跃 Change 的 `tasks.md` 通过 `lint_task_deps.py`，errors=0。
    - [x] 不顺手改动这些文件的其他内容。

### 任务 4：[x] 产出归档遗留违规清单并验证统一判定合同

- 状态: 完成
- depends_on: Task 2
- review_profile: standard
- 文档映射：`proposal.md` §6.2 统一合同、§7 验收标准 6-7a
- 文件：无（只读，清单写入本 Change）
- context_files: `openspec/changes/archive/`、Task 1 的对照表、`openspec/specs/backend/engineering/tech/framework-unification.md`
- artifacts: 归档遗留违规清单（文件、不合规取值、结构化标签）、统一判定合同验证结论
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 逐一列出受影响的归档文件，附具体不合规取值，不只给文件名。
    - [x] 归档违规带「遗留违规」结构化标签，引用 §3.3「Archive 仅作为历史证据」作为分类依据。
    - [x] 验证解析器实现中不含任何 `archive` 路径放宽分支，用检索证明；规则对活跃与归档一致。
    - [x] 验证报告层把归档违规归入独立的机器可解析分类（结构化字段，非消息文本），与活跃违规分开。
    - [x] 用至少两个不同调用路径验证：对同一归档输入，得到同一结构化判定，不存在「跳过归档」这一选项。
    - [x] 确认 `openspec/changes/archive/` 下逐字节未改动。
    - [x] 清单可被 change 2035 的 golden 基线直接引用为「已知遗留」输入。

### 任务 5：[x] 长期规格同步

- 状态: 完成
- depends_on: Task 3, Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2037-dependency-dialect-adjudication/proposal.md`、Task 4 的归档清单
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] 记录依赖方言已统一为严格式，附两轨实现出处。
    - [x] 记录归档范围豁免的方式与理由，明确规则唯一、豁免在调用方。
    - [x] 若 Task 1 确认 `workflow-control/overview.md` 记载了依赖语义，一并同步。
    - [x] 不改动 §3.3 对 Archive 的定位。
    - [x] `python scripts/markdown_links.py openspec` 退出码 0。
    - [x] 按 md-zh 规范自检中文排版。
