# 实施任务清单

> 由 proposal.md / design.md 生成
> 任务总数：5
> 核心原则：先清点反向引用再改写（Task 1 → Task 2），否则改完主条文会与散文引用不一致。本 Change 零代码改动，`pytest` 全量通过用于**证明**未触碰实现，不是用于验证新功能。

## 依赖关系总览

```
Task 1 (反向引用清点)
   │
   └──> Task 2 (四处条文改写)
          │
          └──> Task 3 (可判定定义与重新评估条件)
                 │
                 └──> Task 4 (§21 生产验证陈述更新)
                        │
                        └──> Task 5 (一致性与零代码影响核对)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3} → W4 = {Task 4} → W5 = {Task 5}

> 全链串行。Task 2、Task 3、Task 4 都写同一份 `framework-unification.md`，存在写入冲突，无法并行。Task 4 在内容上独立于 Task 2 与 Task 3，串行仅出于写锁需要；若换用支持同文件分段写入的方式，Task 4 可与 Task 2 并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 2, Task 3, Task 4 | §1、§3.2、§8.1、§19.1 改写，新增可判定定义，§21 事实更新 |
| 反向引用文档 | 待定 | Task 1, Task 5 | 范围由 Task 1 清点结果决定，不预先假定 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §10 知识影响 | Task 1 | 反向引用范围确定 |
| `design.md` §2.1 至 §2.4 | Task 2 | 四处逐条替换措辞 |
| `proposal.md` §8.1、§8.2 已裁决事项 | Task 2 | 三层拆分与取代标注 |
| `proposal.md` §9 验收标准 1-2、4-5 | Task 2 | §1、§3.2、§8.1、§19.1 |
| `proposal.md` §9 验收标准 3 | Task 2, Task 3 | 重新评估条件 |
| `design.md` §3 可判定定义 | Task 3 | 三条判据与失败后果 |
| `proposal.md` §9 验收标准 6-7 | Task 3 | 降级等价判据绑定 |
| `design.md` §2.5、`proposal.md` §8.3 | Task 4 | §21 双段表述与证据边界 |
| `proposal.md` §9 验收标准 8-10 | Task 4 | §21 改写与范围约束 |
| `proposal.md` §9 验收标准 11-15 | Task 5 | 一致性、零代码、门禁 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 已完成 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 已核对（2026-07-27）。其一：§19.1 第一条理由保留原文并附「已被 §5.4、§6.3 取代」标注，两侧证据均在文内可定位，未单方面抹除。其二：§21 改写为双段表述——「已在真实生产项目中使用（框架作者声明，2026-07-26）」与「有效性证据仍缺失（无遥测／外部归档／缺陷数据）」并存，证据强度差保留，该条目仍属未决项。

## 实际 Diff 核对

- `git diff --stat` 显示改动全部落在 `openspec/` 下的 Markdown：`framework-unification.md` 的 §1 两条、§3.2 结论句（五项列举逐字未动）、§8.1 三层表、§19.1 标题与理由标注、§21 生产验证陈述，新增 §8.5「一条执行链的可判定定义」（三判据＋失败后果＋判据三局限）。无 `.py` 文件改动。
- Task 1 反向引用清点：检索词（两个独立生命周期／巨型状态机／巨型统一引擎／强行合成一条工作流／强行收敛／双 Profile）命中全部位于 `framework-unification.md` 本体（:27、:31、:94、:302、:680），无 Skill／Command／agents 散文引用结论；「仅提及双 Profile 架构」类不纳入。归档目录命中按规则只记录不改写。波及面为零，无拆分需要。
- 本 Change 的规格改写在 2042 交付期间补执行——2036 提交（8d88232）只含裁决文档，规格同步当时未执行；现按 design.md §2.1-2.5 与 §3 原文逐处落地，三判据因 §8.4 已被 2037 占用而落于 §8.5。
- 已交付的 2038-2042 各 Change 的「§3.2 条件 1/3 部分举证」记录均引用本节条文，举证编号与本节保持一致（条件 1＝策略参数化、条件 2＝降级等价实现、条件 3＝强制规则可机器强制）。

---

### 任务 1：[x] 清点四处结论的全仓库反向引用

- 状态: 完成
- depends_on: 无
- review_profile: standard
- 文档映射：`proposal.md` §10 知识影响
- 文件：无（只读清点，产出对照表写入本 Change）
- context_files: `openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/`、`skills/`、`commands/`、`AGENTS.md`
- artifacts: 反向引用对照表（引用位置、原措辞、是否受改写影响、处置结论）
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] 检索范围覆盖 `openspec/specs/`、`openspec/changes/`（含 archive）、`skills/`、`commands/`、`agents/`、仓库根 Markdown。
    - [x] 检索词至少包含：两个独立生命周期、巨型状态机、巨型统一引擎、一条工作流、不能合并、强行收敛、双 Profile。
    - [x] 每条命中标注文件与行号，并判定「受本次改写影响／不受影响」，判定附理由。
    - [x] 区分「引用结论」与「仅提及双 Profile 架构」两类，后者不纳入改写范围。
    - [x] 归档目录的命中一律标记为不改写，只记录（归档保存当时证据）。
    - [x] 若命中落在 Skill 散文且数量超过 3 处，给出「本 Change 一并改／另开 Change」的建议与理由，不擅自扩大范围。

### 任务 2：[x] 四处条文改写：拆开语义与承载

- 状态: 完成
- depends_on: Task 1
- review_profile: strict
- 文档映射：`design.md` §2.1 至 §2.4、`proposal.md` §8.1、§8.2、§9 验收标准 1-5
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2036-profile-boundary-readjudication/design.md`、`openspec/changes/2036-profile-boundary-readjudication/proposal.md`、Task 1 的反向引用对照表
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] §1「明确不采用」两条按 `design.md` §2.1 改写，「巨型」的语义保留。
    - [x] §3.2 五项差异列举逐字未动，仅改结论句；改写后明确「五项差异不得删减」为无条件约束。
    - [x] §8.1 拆为读层、门层、写层三层，与 `proposal.md` §8.1 的裁决一致，不得改用其他粒度。
    - [x] §8.1 每层标注当前状态与解除条件；读层引用 §8.2 已满足的证据，不重复举证。
    - [x] §8.1 写层的解除条件包含「Production 只读性质有等价替代」，不得省略。
    - [x] §19.1 标题改为「无前置条件地收敛为一条工作流」。
    - [x] §19.1 第一条理由保留原文并附「已被 §5.4、§6.3 取代」标注，文内可定位到这两处。
    - [x] §19.1 第二条理由保留，未删除、未弱化，并绑定 §8.1 的降级等价判据。
    - [x] 全文无「视情况」「必要时」「适当」类不可判定措辞进入新增的条件条目。
    - [x] Production 的 §5.3 强制规则一条未删、未弱化；改写前后逐条对照并记录。
    - [x] 文件状态行仍为 Approved，不改为 Draft（本 Change 是对已批准方案的修订，不是重新起草）。
    - [x] 按 md-zh 规范自检中文排版：中英文空格、中文与数字空格、全角中文标点、专有名词大小写。

### 任务 3：[x] 写入「一条执行链」的可判定定义

- 状态: 完成
- depends_on: Task 2
- review_profile: strict
- 文档映射：`design.md` §3 可判定定义、`proposal.md` §7、§9 验收标准 6-7
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2036-profile-boundary-readjudication/design.md`、`openspec/changes/2035-common-task-ast/design.md`
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] 三条判据（状态源唯一、门为叠加、降级等价）全部写入，各含核验方式。
    - [x] 明确以降级等价为主判据，并说明另两条为何不单独充分。
    - [x] 失败后果写明：判据无法执行与判据不通过同等处理，均须回退；「无法执行」不得按「暂不适用」放行。
    - [x] 记录判据三的局限：只能证明关掉 production 后等于 tooling，不能证明打开后治理强度不低于现状。
    - [x] 判据三与 §3.2 条件 3（强制规则仍可机器强制）绑定为「须同时满足」，不得二选一。
    - [x] 判据一引用 §3.3 既有的「不另建平行状态」表述，标明是延续而非新增要求。
    - [x] §8.2 与 §8.3 未被改动。
    - [x] 按 md-zh 规范自检中文排版。

### 任务 4：[x] 更新 §21 生产验证陈述

- 状态: 完成
- depends_on: Task 3
- review_profile: standard
- 文档映射：`design.md` §2.5、`proposal.md` §8.3、§9 验收标准 8-10
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2036-profile-boundary-readjudication/design.md`、`openspec/changes/2036-profile-boundary-readjudication/proposal.md`
- artifacts: `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] §21 生产验证条目按 `design.md` §2.5 改写为双段表述：使用事实已确立、有效性证据仍缺失。
    - [x] 证据来源写为「框架作者声明」并附日期 2026-07-26，不写成有材料支撑的结论。
    - [x] 逐项列出缺失的证据形态：遥测记录、外部项目 Change 归档、缺陷或回归数据。
    - [x] 改写后仍可检索到未决语义，未被简化为「已验证」或整条删除。
    - [x] §21 其余四条不确定项（`arch-snapshots/` 时效性、发布平台边界、迁移工作量估算、基线要求）逐字未动。
    - [x] 本任务不改动 §1、§3.2、§8.1、§19.1，与 Task 2、Task 3 的改动区域不重叠。
    - [x] 按 md-zh 规范自检中文排版。

### 任务 5：[x] 一致性回扫与零代码影响核对

- 状态: 完成
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §9 验收标准 11-15
- 文件：Task 1 清点出的受影响文档（范围以其对照表为准）
- context_files: Task 1 的反向引用对照表、`openspec/specs/backend/engineering/tech/framework-unification.md`
- artifacts: 一致性核对结论、`git diff --stat` 输出、`pytest` 前后对照
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] Task 1 对照表中判定为「受影响」的每一条，逐条给出已同步或已记录为待处理的结论，无遗漏。
    - [x] 重跑 Task 1 的检索词，确认无新增的不一致措辞。
    - [x] 确认 Task 2、Task 3、Task 4 的改动在同一文件内无相互覆盖，章节编号与交叉引用全部可定位。
    - [x] `git diff --stat` 显示改动全部落在 `openspec/` 下的 Markdown，无 `.py` 文件。
    - [x] `python -m pytest scripts -q` 全量通过，通过／跳过数与改动前相同；差异为零用于证明本 Change 零代码影响。
    - [x] `python scripts/markdown_links.py openspec` 退出码 0。
    - [x] `python scripts/lint_skill_graph.py` 输出 errors=0。
    - [x] 「实际 Diff 核对」与「知识冲突」两节填写完毕，不留占位文字。
