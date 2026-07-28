# Proposal：裁决依赖字段方言

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：dependency-dialect-adjudication
**状态**：Draft

---

## 1. 问题

两轨对同一个依赖字段的解析规则不同，且严格度方向相反。

| 轨 | 实现 | 行为 | 出处 |
| --- | --- | --- | --- |
| Production | `re.fullmatch` 后发 OPSX023 | 只接受 `无`／`none`／`Task N` 或 `任务 N` 形式，裸数字判错 | `scripts/validate_change.py:23`（`DEPENDENCY_RE`）、`:1288`（fullmatch） |
| Tooling | `re.findall(r"\d+", dep_text)` | 抓取字符串里的所有数字，裸数字、行号、任意含数字文本全部接受 | `skills/workflow-code-generation/scripts/lint_task_deps.py:55-66` |

Production 的正则为：

```python
r"(?:无|none|(?:(?:Task|任务)\s*\d+\s*(?:[,，、]\s*)?)+)"
```

Tooling 的宽松语义有实际风险：`- depends_on: 见 2035 第 3 节` 会被解析为「依赖 Task 2035 与 Task 3」，静默产生不存在的依赖 ID，进而影响 `_kahn_waves` 的波次计算。这不是理论问题——`findall` 对任何含数字的自由文本都会出结果，不报错。

## 2. 实测规模

全仓库 `openspec/changes/**/tasks.md`：

| 指标 | 数量 |
| --- | ---: |
| 依赖字段声明总数 | 107 |
| 其中 `[]` 或空值 | 18 |
| 非空且符合 Production 严格式 | 52 |
| **非空但不符合 Production 严格式** | **37** |

37 处不合规分布在 12 个文件，其中：

- 活跃 Change：1 个（`openspec/changes/2-add-verify-ignore/tasks.md`）
- 归档 Change：11 个

所以收敛到严格式的**活跃成本只有一个文件**。真正需要裁决的是归档怎么办。

## 3. 归档是本 Change 的核心难点

这与 change 2035 的 Task 6、Task 7 方向相反。那两个任务是**放宽**——原本失败可转为通过，原本通过不受影响，可用单向翻转机械核对。本 Change 是**收紧**：Tooling 若改用严格式，11 个归档文件会从 Tooling 通过转为 Tooling 失败。

而 2035 Task 5 的 golden 基线明确覆盖「全部活跃与归档 Change」。也就是说这些翻转会出现在基线里，不能靠「归档不跑门禁」回避。

`framework-unification.md` §3.3 把 Archive 定义为「仅作为历史证据」。重写归档等于篡改证据，这条不能破。

## 4. 目标

1. 裁决唯一的依赖字段方言，两轨解析结果对同一输入一致。
2. 消除 `findall` 的静默误解析：不合规的依赖值必须报错，不得静默产出依赖 ID。
3. 归档文件不被改写，且不因本 Change 产生新的失败。
4. 活跃文件的不合规声明全部修正。

## 5. 非目标

- **不改依赖字段名**。`depends_on` 与遗留 `依赖` 的双写法不在本 Change 范围，由 change 2035 的 AST 统一读取。
- **不改重复任务 ID 的处理**。Tooling 抛 `ValueError`、Production 走 OPSX021 的分歧不动。
- **不改写任何归档文件**。
- **不放宽 Production**。采纳 Tooling 的宽松式会删掉 OPSX023 这个真实质量门，违反 §3.4「删除重复成本，不删除质量门」。
- **不新增第三种方言**。

## 6. 设计方案

### 6.1 方向：收敛到 Production 的严格式

三个选项：

| 方案 | 后果 | 取舍 |
| --- | --- | --- |
| 收敛到 Production 严格式 | Tooling 变严，11 个归档翻转，1 个活跃文件需修 | **采纳** |
| 收敛到 Tooling 宽松式 | Production 失去 OPSX023，静默误解析进入 Production | 拒绝，是质量门弱化 |
| 保持分歧 | 现状，两轨对同一文件给出不同依赖图 | 拒绝，与统一读层的目标直接冲突 |

采纳第一个。宽松方向的代价是引入静默错误，而严格方向的代价是一次性迁移，两者不对等。

### 6.2 归档处理：统一合同，不是调用方自选

初稿写的是「调用方范围豁免」——`lint_task_deps.py` 严格校验一致生效，由调用方决定扫不扫归档。对抗性审核指出这会让同一份历史 `tasks.md` 的合法性**依赖调用上下文**：记得跳过归档的入口得到「通过」，不记得的得到「失败」，回归门无法回答哪个权威。这个批评成立，改为统一合同。

规则仍唯一（严格式对所有输入一致），但归档的处置必须是**结构化判定**，不是「有的入口跳过、有的入口报错」：

- 解析器对活跃与归档一律跑同一严格式，产出同一组违规。
- 报告层把归档违规归入独立的「遗留违规」分类，与活跃违规分开，带结构化标签（如 `legacy-archived`）。
- 任何调用方拿到的是**同一份结构化判定**：活跃违规 = 失败；归档违规 = 记录为遗留，不计入失败。
- 「不扫归档」不作为任何入口的选项；归档永远被扫，只是其违规被分类而非豁免。

这样：规则唯一、判定可复现、归档不被改写、且不存在「忘记跳过就批量报错」的调用方分叉。归档在 2035 golden 基线里登记为「已知遗留」，附逐文件清单。

### 6.3 未裁决项

**`[]` 与 `无` 的地位。** Tooling 现接受 `[]`、`无` 两种空值写法（`lint_task_deps.py:64`），Production 只接受 `无`、`none`。收敛后 `[]` 是否仍合法，需实现方在 `design.md` 中裁决。倾向保留 `[]`——本仓库 18 处空值声明大量使用它，且它无歧义。

**「遗留违规」的结构化标签形式。** 标签名与其在 JSON／文本报告中的字段位置，由实现方定，但必须是机器可解析的独立字段，不得只用消息文本区分。

## 7. 验收标准

1. 两轨对同一依赖字段值的解析结果一致：合规值产出相同 ID 集合，不合规值两轨都报错。
2. Tooling 不再使用 `re.findall(r"\d+")` 作为依赖提取的唯一手段；不合规值报错而非静默产出 ID。
3. `- depends_on: 见 2035 第 3 节` 一类自由文本被判为不合规，有专门用例。
4. 空值写法的裁决落地并有用例：`[]`、`无`、`none` 的接受与否明确且两轨一致。
5. 活跃 Change 中全部不合规依赖声明修正完毕，修正前后依赖图逐一比对无变化。
6. 归档文件逐字节未改动。
7. 产出归档「遗留违规」清单：11 个文件逐一列出、附不合规的具体取值，写入本 Change。
7a. 归档违规被归入独立的「遗留违规」结构化分类，与活跃违规机器可区分；任何调用方对同一归档输入得到同一结构化判定，不存在「跳过归档」这一选项。
8. Production 的 OPSX023 判定结果对既有用例不变，未放宽。
9. `_kahn_waves` 的波次输出对全部活跃 Change 与改动前一致。
10. `python -m pytest scripts -q` 全量通过。
11. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。记录依赖方言已统一为严格式，以及归档范围豁免的处理方式。
- `openspec/specs/backend/framework/workflow-control/overview.md`：待 Task 1 确认是否记载了依赖解析语义；若有，同步。

## 9. 依赖与排序

本 Change 与 change 2035 有实质耦合：2035 的 AST 交出 `dep_field_raw` 原始字符串，两轨各自解释。本 Change 统一解释规则。

**建议在 2035 交付后执行**，这样只需改 AST 消费侧的一处解释逻辑，而不是改两份独立实现。若先于 2035 执行，需在两个文件各改一次，且 2035 的 golden 基线要重新冻结。

## 10. 参考资料

- Production 严格式：`scripts/validate_change.py:23`、`:1288`（OPSX023）
- Tooling 宽松式：`skills/workflow-code-generation/scripts/lint_task_deps.py:55-66`
- 波次计算消费方：`skills/workflow-code-generation/scripts/workflow_control.py:120`（`_kahn_waves`）
- Archive 定位：`openspec/specs/backend/engineering/tech/framework-unification.md:108`（§3.3）
- 不删质量门原则：同文件 §3.4
- 同型但方向相反的放宽：`openspec/changes/2035-common-task-ast/tasks.md` Task 6、Task 7
