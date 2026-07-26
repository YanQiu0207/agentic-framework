# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：本 Change 是 §8.3 的最后一步，也是风险最高的一步——写错状态会破坏 `tasks.md` 这个唯一事实源。Production 只读可审计性的等价替代是硬点，不能靠「现在有写路径了」糊过去（Task 3 专项举证）。`validate_change.py` 全程保持只读。

## 依赖关系总览

```
Task 0 (前置确认 change 2043 已交付)
   │
   └──> Task 1 (清点全部状态写入点)
          │
          └──> Task 2 (写路径收敛到单一入口)
                 │
                 ├──> Task 3 (只读可审计性等价替代举证)
                 └──> Task 4 (写锁/恢复/并发回归 + 规格同步)
```

波次：W1 = {Task 0} → W2 = {Task 1} → W3 = {Task 2} → W4 = {Task 3, Task 4}

> Task 3 与 Task 4 都消费 Task 2 的收敛结果但验证维度不同，可并行。Task 4 含规格同步。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 2 | 收敛全部状态写入到单一入口 |
| 各 Skill 流程中手动改状态的做法 | 修改 | Task 2 | 改为调状态机 |
| `scripts/validate_change.py` | **不改判定** | Task 3 | 保持只读，仅核对 |
| `scripts/` 测试目录 | 新增 | Task 1, Task 3, Task 4 | 写入点清单、等价替代与回归用例 |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 修改 | Task 4 | 写路径统一语义 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 4 | §8.3 收尾 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 前置 | Task 0 | change 2043 确认 |
| `proposal.md` §6.1 物理统一 | Task 1, Task 2 | 写入点清点与收敛 |
| `proposal.md` §5 等价替代、§5.1 | Task 3 | 可审计性举证 |
| `proposal.md` §6.2 回归、§6.3 | Task 4 | 单链回归与 §8.3 收尾 |
| `proposal.md` §8 知识影响 | Task 4 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `workflow-control` | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需核对：`framework-unification.md` §8.1 写层解除条件要求「Production 的只读性质有等价替代」。交付时须展示等价替代的逐项对照，证明可审计性未因状态写入从「人手动改」变为「状态机写回」而下降——反而须说明其增强（手动改无审计，写回带时机与原因）。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认 `validate_change.py` 未新增任何写入调用。

---

### 任务 0：[ ] 确认 change 2043 已交付

- 状态: 未开始
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §2 为什么它在门层合并之后
- 文件：无（只读确认）
- context_files: `openspec/changes/2043-governance-overlay-merge/`、`skills/workflow-code-generation/scripts/workflow_control.py`
- artifacts: 前置交付确认记录
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 确认 change 2043 已交付：治理门已挂载到状态机转移。
    - [ ] 确认状态机只有一份、任务只在 Tooling 状态机推进。
    - [ ] 若 2043 未交付，停止本 Change，记录阻塞，不绕过。
    - [ ] 记录 2043 后状态机的转移图与守卫清单，作为本 Change 的输入。

### 任务 1：[ ] 清点全部任务状态写入点

- 状态: 未开始
- depends_on: Task 0
- review_profile: strict
- 文档映射：`proposal.md` §6.1 写路径的物理统一
- 文件：无（只读清点，产出写入本 Change）
- context_files: `skills/workflow-code-generation/scripts/workflow_control.py`、`skills/`、`scripts/validate_change.py`
- artifacts: 状态写入点清单、收敛方案
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 检索所有对 `- 状态:` 与任务头标记的写入点，逐一列出文件与位置。
    - [ ] 区分三类：`workflow_control.py` 内的转移函数、Skill 流程中的手动改状态、Production 流程中的人改 `tasks.md`。
    - [ ] 确认 `update_task_state`（`:576`）与 `_atomic_write`（`:645`）是收敛目标入口。
    - [ ] 列出每个非入口写入点的迁移方式（改为调状态机），不遗漏。
    - [ ] 确认写回产出的 `tasks.md` 格式与现状一致，本 Change 不改格式。

### 任务 2：[ ] 写路径收敛到单一入口

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 物理统一
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`、各 Skill 流程
- context_files: Task 1 的写入点清单、Task 0 的转移图
- artifacts: 收敛后的写路径、迁移用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 全部状态写入收敛到 `update_task_state` 与 `_atomic_write`。
    - [ ] Skill 流程中手动改状态的做法全部改为调状态机。
    - [ ] Production 流程中「人改 `tasks.md` 标记」改为状态机写回。
    - [ ] **不新增状态机转移**，不改 change 2039、2043 已定的转移与守卫。
    - [ ] 静态核验：收敛后无第二个写者，用检索证明。
    - [ ] 每次状态写入带时机与原因，可追溯。
    - [ ] `tasks.md` 写回格式与现状一致。

### 任务 3：[ ] Production 只读可审计性等价替代举证

- 状态: 未开始
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §5 等价替代、§5.1 未裁决项
- 文件：`scripts/` 测试目录
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- artifacts: 等价替代举证报告、审计痕迹形式裁决
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 逐项对照 `proposal.md` §5 的三条原有保证与等价替代，给出证据。
    - [ ] 证明 `validate_change.py` 仍只读：未新增任何文件写入，用检索证明。
    - [ ] 证明判定可复现：同一 `tasks.md` 输入，判定不依赖校验器自身写入。
    - [ ] 裁决写入审计痕迹形式：独立转移日志 vs `tasks.md` 加版本控制历史；写明理由，对「第二事实源」风险给出结论。
    - [ ] 若采纳 Git 历史方案，裁决 SVN 项目下的等价物。
    - [ ] 证明状态不另建副本，只在 `tasks.md`。
    - [ ] 举证结论：可审计性未下降，且因写回带时机与原因而增强。

### 任务 4：[ ] 单链回归与 §8.3 收尾

- 状态: 未开始
- depends_on: Task 2, Task 3
- review_profile: strict
- 文档映射：`proposal.md` §6.2 回归、§6.3、§8 知识影响
- 文件：`scripts/` 测试目录、`openspec/specs/backend/framework/workflow-control/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `skills/workflow-code-generation/scripts/workflow_control.py`、Task 3 的举证报告
- artifacts: 回归结果、两份长期规格
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 写锁（`_try_lock`／`_unlock`）在单一执行链上回归通过。
    - [ ] attempts 与 `plan_recovery` 行为与 change 2043 后一致。
    - [ ] 并发写回、失败中途恢复、worktree 合并三类场景用例通过。
    - [ ] §8.3 四步全部完成，`framework-unification.md` 进度记录更新，标注第 4 步由本 Change 完成。
    - [ ] `workflow-control/overview.md` 记录写路径统一、写锁与恢复在单链上的语义。
    - [ ] `framework-unification.md` 记录写层合并的只读等价替代结论。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
