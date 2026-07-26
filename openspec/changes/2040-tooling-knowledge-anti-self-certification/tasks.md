# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：共享模块提取会改动 Production，必须先冻结 Production 判定基线（Task 1）并用 golden 比对证明零行为变更（Task 2），才允许 Tooling 接入（Task 3、Task 4）。这与 change 2035 的手法相同——搬家可证，改判定不可证。

## 依赖关系总览

```
Task 1 (裁决方案 + 冻结 Production 判定基线)
   │
   └──> Task 2 (提取共享知识核对模块)
          │
          └──> Task 3 (Tooling 接入交叉核对)
                 │
                 └──> Task 4 (无 specs 形态与失败关闭)
                        │
                        └──> Task 5 (规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3} → W4 = {Task 4} → W5 = {Task 5}

> 全链串行。Task 3 与 Task 4 都改 `check_delivery.py`，无法并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/knowledge_sync.py` | 新增 | Task 2 | 共享的 Delta 反推与同步表解析（名称待 Task 1 裁决） |
| `scripts/validate_change.py` | 修改 | Task 2 | 改为委托共享模块，判定逻辑不变 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 3, Task 4 | 知识影响检查改为交叉核对 |
| `scripts/` 测试目录 | 新增 | Task 1, Task 2, Task 3, Task 4 | 基线与五类失败用例 |
| `openspec/specs/backend/framework/knowledge-management/overview.md` | 修改 | Task 5 | Tooling 侧反自证 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 5 | §6.3 同步 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §6.1 方案取舍 | Task 1 | 提取 vs 重实现裁决 |
| `proposal.md` §3 与 2034 的关系 | Task 1 | 前置依赖确认 |
| `proposal.md` §7 验收标准 4-5 | Task 2 | Production 零行为变更 |
| `proposal.md` §6.2 检查项 | Task 3 | 五类反自证骨架 |
| `proposal.md` §6.3 未裁决项 | Task 4 | 无 `specs/` 形态 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `knowledge-management` | `openspec/specs/backend/framework/knowledge-management/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需记录：`proposal.md` §5 写「不改 Production」，而 §6.1 倾向的共享模块方案必然改动 `validate_change.py`。这是本 Change 内部的约束冲突，交付时须展示裁决理由与零行为变更证据，不得默默改了了事。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独列出 `validate_change.py` 的改动性质（搬家 vs 判定变更）。

---

### 任务 1：[ ] 裁决方案并冻结 Production 判定基线

- 状态: 未开始
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §6.1 方案取舍、§3 与 2034 的关系
- 文件：无（只读清点与裁决记录，产出写入本 Change）
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`openspec/changes/2034-knowledge-gate-risk-inversion/proposal.md`
- artifacts: 方案裁决记录、Production 全量判定基线、OPSX042-051 覆盖清单
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 裁决共享模块提取 vs Tooling 重新实现，写明理由与被拒方案的具体缺陷。
    - [ ] 若裁决为提取：明确本 Change 的 `proposal.md` §5「不改 Production」被本裁决覆盖，记录覆盖理由。
    - [ ] 确认 change 2034 的交付状态；若未交付，记录本 Change 加强的检查在 Runtime Run 与 Scoped Delivery 上仍不生效这一事实。
    - [ ] 对全部活跃与归档 Change 跑 `validate_change.py` 三阶段，冻结 OPSX042 至 OPSX051 的判定输出为基线。
    - [ ] 基线可重复：连续两次生成逐字节相同。
    - [ ] 逐个记录 OPSX042 至 OPSX051 的检查语义，标注哪些属于 `proposal.md` §6.2 的五类骨架、哪些属于 Production 阶段特定。
    - [ ] 清点本仓库 Change 的目录形态分布：有 `specs/` 与无 `specs/` 各多少，供 Task 4 裁决使用。

### 任务 2：[ ] 提取共享知识核对模块

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §7 验收标准 4-5
- 文件：`scripts/knowledge_sync.py`、`scripts/validate_change.py`
- context_files: `scripts/validate_change.py`、Task 1 的基线与裁决记录、`openspec/changes/2035-common-task-ast/design.md`
- artifacts: 共享模块、改为委托后的 `validate_change.py`、golden 比对结果
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 共享模块只做解析与反推，不含 OPSX 编号、错误消息或退出码。
    - [ ] `_delta_targets` 与 `_knowledge_sync_rows` 的逻辑迁入共享模块，`validate_change.py` 改为委托。
    - [ ] OPSX042 至 OPSX051 的判定逻辑**留在** `validate_change.py`，不进共享模块。
    - [ ] Task 1 的基线重跑，全部活跃与归档 Change 的判定输出逐字节相同。
    - [ ] `validate_change.py` 中的原实现删除，无残留死代码或孤儿常量。
    - [ ] 共享模块不导入 `validate_change` 或 `check_delivery`，无循环依赖。
    - [ ] 模块放置与导入方式与 `workspace_residue.py` 一致，不引入新机制。

### 任务 3：[ ] Tooling 接入交叉核对

- 状态: 未开始
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §6.2 检查项的取舍
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/` 测试目录
- context_files: `scripts/knowledge_sync.py`、Task 1 的检查语义清单
- artifacts: 改造后的知识影响检查、五类失败用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 知识影响检查执行交叉核对，不再只做 `checks += 1` 计数。
    - [ ] 五类失败各有用例并失败关闭：Delta 漏报、声明误报、路径不匹配、同步状态未完成、知识冲突节为空或仍是占位文字。
    - [ ] `check_delivery.py:608` 的 `requires_knowledge_impact` 判定条件未被修改，用 diff 证明。
    - [ ] 不存在静默跳过分支，用检索证明。
    - [ ] Tooling 未引入 OPSX 命名空间，错误消息沿用 Tooling 现有风格。
    - [ ] 本仓库现有归档 Change 在新检查下的判定结果逐一列出；转为失败的条目附判定，不批量接受。

### 任务 4：[ ] 无 specs 形态的反推来源

- 状态: 未开始
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §6.3 未裁决项
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/` 测试目录
- context_files: Task 1 的目录形态分布、`openspec/changes/2034-knowledge-gate-risk-inversion/`
- artifacts: 无 `specs/` 形态的核对实现与用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 裁决无 `specs/` 目录时的反推来源，写明理由。
    - [ ] 无 `specs/` 时**不直接放行**，有用例证明。
    - [ ] 采用替代反向证据时，明确其强度低于 Delta 反推，并在错误消息或报告中体现这一区分。
    - [ ] 对 Task 1 清点出的无 `specs/` 形态 Change 逐一验证新逻辑，判定结果列表写入本 Change。
    - [ ] 有 `specs/` 与无 `specs/` 两条路径的检查项数量在交付报告中可区分。

### 任务 5：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/framework/knowledge-management/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2040-tooling-knowledge-anti-self-certification/proposal.md`、Task 1 的裁决记录
- artifacts: 两份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] `knowledge-management/overview.md` 记录 Tooling 侧的反自证核对与五类检查。
    - [ ] `framework-unification.md` §6.3 新增对应条目。
    - [ ] 记录知识核对逻辑现由共享模块承载，两轨共同消费。
    - [ ] 记录这是 §3.2 条件 3 的**部分**举证，明确其余强制规则仍未举证。
    - [ ] 记录无 `specs/` 形态的证据强度较弱这一已知限制。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
