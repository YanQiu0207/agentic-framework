# Proposal：Tooling 写状态路径的统一

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：write-state-path-unification
**状态**：Draft

---

## 1. 问题

`workflow_control.py` 有一套完整的写状态路径——DAG 波次、attempts、写锁、原子写回、失败恢复。这套逻辑目前只服务 Tooling。

`framework-unification.md` §8.3（由 change 2035 标注进度）规定了公共能力的提取顺序：

1. 先冻结两边现有 Fixtures 和行为。
2. 建立公共 AST 和 Profile Adapter。
3. 先迁移只读调用方。
4. **最后迁移 Tooling 写状态路径。**
5. 每迁移一个调用方都运行兼容性测试。

写状态路径排在最后，是因为它风险最高：读错了最多误判，写错了会破坏 `tasks.md` 这个唯一事实源。

## 2. 为什么它在门层合并之后

change 2043 把治理门叠加到 Tooling 状态机。但 2043 的前提是状态机**只有一份**、写路径**只有一条**。本 Change 是把这个前提坐实。

在 2043 之前做本 Change 没有意义——治理门还没挂上，统一写路径没有服务对象。在 2043 之后，写路径必须统一，否则「同一任务一条执行链」在写侧仍是分裂的。

§8.1（change 2036 改写）对写层的解除条件是：

> 读层与门层均已合并且稳定运行；且写层合并后 Production 的只读性质有等价替代。

注意第二条。`validate_change.py` 只读是 Production 可审计性的基础——校验器不改状态，判定永远可复现。写层统一后，`workflow_control.py` 会写状态，**Production 侧必须有一个等价的可审计性保证**，不能简单接受「现在它有写路径了」。

## 3. 目标

1. 任务状态的写路径只有一条，就是 `workflow_control.py` 的原子写回。
2. 写锁、attempts、失败恢复在收敛后的单一执行链上行为不变。
3. Production 的只读可审计性有等价替代，并被验证。
4. §8.3 第 4 步完成，公共能力提取全部就位。

## 4. 非目标

- **不改写状态机的转移逻辑**。转移与守卫在 change 2039、2043 已定，本 Change 只管写路径的物理统一。
- **不改 `tasks.md` 的格式**。写回产出的格式与现状一致。
- **不引入第二个写者**。任何对 `- 状态:` 或任务头标记的写入都收敛到 `workflow_control.py`。
- **不破坏 Production 的可审计性**。见 §5，这是解除条件的硬点。
- **不动 `validate_change.py` 的判定逻辑**。它保持只读裁决，只是不再承担「批量补裁」的隐性职责。

## 5. Production 只读性质的等价替代

这是本 Change 最难的部分，必须正面回答。

Production 当前的可审计性来自：`validate_change.py` 只读 → 它对 `tasks.md` 的判定不依赖它自己写入的任何状态 → 同一输入永远同一判定 → 判定可复现、可独立复核。

写层统一后，状态由 `workflow_control.py` 写入。等价替代需要保证：

| 原有保证 | 等价替代 |
| --- | --- |
| 判定可复现 | `validate_change.py` 仍只读，判定仍不依赖它自己的写入 |
| 状态写入可审计 | 写回是原子的、带锁的、可追溯的（谁在何时把哪个任务从哪态写到哪态） |
| 无平行状态 | 状态只在 `tasks.md`，`workflow_control.py` 原子写回，不另建副本 |

**关键区分**：写层统一不等于 `validate_change.py` 变成有写。它保持只读裁决器；变的是「状态由谁写」从「人手动改 `tasks.md` + 校验器事后批量核对」变成「`workflow_control.py` 执行期即时写回 + 校验器仍只读核对」。

可审计性没有消失，反而增强——手动改状态是无审计的，而 `workflow_control.py` 的写回天然带时机与原因。

### 5.1 未裁决项

**写入的审计痕迹形式。** `workflow_control.py` 的写回是否需要在 `tasks.md` 之外留下独立的转移日志，还是 `tasks.md` 本身（加 Git 历史）就足够。倾向后者——另建日志会引入第二事实源，违反 §3.3「不另建平行状态」。但需确认 Git 历史在 SVN 项目下的等价物。

## 6. 设计方案

### 6.1 写路径的物理统一

清点所有对任务状态的写入点，收敛到 `update_task_state`（`workflow_control.py:576`）与 `_atomic_write`（`:645`）：

- `workflow_control.py` 内的各 `_handle_*` 转移函数。
- 任何 Skill 流程中手动改 `- 状态:` 的做法，改为调状态机。
- Production 流程中「人改 `tasks.md` 标记」改为「状态机写回」。

**与已批准总规的关系，必须在实现前钉住。** 单看旧条文，「Production 状态机写回」会撞上两处：Production 是只读校验器，以及 §5.3（`:185`）「同一波次内保持串行，不引入 Tooling 的并行写入或 Run 状态机」。

两点澄清，缺一不可：

1. **授权来源是 change 2036。** §8.1 写层的解除条件是「读层与门层均已合并且稳定运行；且写层合并后 Production 的只读性质有等价替代」。本 Change 正是写层合并，§5 给出只读等价替代。它在 2036 授权路径内，不是单方面废除 Production 执行模型。前置仍是 2043（门层）已交付且稳定。
2. **统一的是写路径与原子写回，不是并发模型。** Production 在收敛后仍满足 §5.3 `:185`：同一波次内**串行**写回，不启用 Tooling 的并行 worktree 写入，不创建 Run Context、不进入 Run 状态机。`workflow_control.py` 的写锁与原子写回在串行模式下同样成立——锁退化为单写者自保，attempts 仍记录，恢复仍可读。**本 Change 不把 Production 绑到并行写语义上。**

「写回污染 `tasks.md`」的风险不因统一而新增：统一前是人手动改（无锁、无审计、无原子性），统一后是带锁、带时机与原因的原子写回。写路径集中恰恰是把唯一事实源的写入从「无保护的分散手动改」收紧为「有保护的单一入口」。

### 6.2 写锁与恢复在单链上的验证

写锁（`_try_lock`／`_unlock`）、attempts、`plan_recovery` 的行为在收敛后的单一执行链上逐一回归。重点：失败中途恢复、worktree 合并时的状态一致性。**Production 侧回归一律在串行模式下进行**——不引入并行写入或 Run 状态机（§5.3 `:185`），故「多任务并发写回」仅作为 Tooling 既有行为的回归，不作为 Production 的新能力。

### 6.3 §8.3 收尾

本 Change 完成后，§8.3 的四步全部就位：

| 步骤 | 承载 Change |
| --- | --- |
| 1 冻结 Fixtures 和行为 | 2035 Task 1 |
| 2 公共 AST + Adapter | 2035 Task 2-4 |
| 3 迁移只读调用方 | 2035 Task 3-5 |
| 4 迁移写状态路径 | **本 Change** |

## 7. 验收标准

1. 任务状态的写路径只有一条，静态核验证明无第二个写者。
2. `update_task_state` 与 `_atomic_write` 是所有状态写入的唯一入口。
3. 写锁、attempts、失败恢复在单一执行链上的行为与 change 2043 后一致，回归通过。
4. Production 的只读可审计性等价替代成立，并给出逐项对照证据。
5. `validate_change.py` 保持只读，未新增任何文件写入，用检索证明。
6. 状态不另建副本，只在 `tasks.md`；写入审计痕迹形式已裁决。
7. SVN 项目下的审计等价物已裁决（若采纳 Git 历史方案）。
8. 失败恢复、worktree 合并两类场景的用例通过；「并发写回」仅作为 Tooling 既有行为回归，不作为 Production 新能力。
8a. Production 状态写回全程串行，未引入并行 worktree 写入，未创建 Run Context 或进入 Run 状态机，有用例与检索证明（§5.3 `:185`）。
9. §8.3 四步全部完成，进度记录更新。
10. 任务状态的写入全部带时机与原因，可追溯。
11. `python -m pytest scripts -q` 全量通过。
12. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/framework/workflow-control/overview.md`：MODIFIED。写路径统一、写锁与恢复在单链上的语义。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§8.3 第 4 步完成；写层合并的只读等价替代结论。

## 9. 参考资料

- 提取顺序：`openspec/specs/backend/engineering/tech/framework-unification.md:311-317`（§8.3）
- 写层解除条件：同文件 §8.1（change 2036 改写）
- 写状态路径：`skills/workflow-code-generation/scripts/workflow_control.py:345-645`（`_handle_*`、`apply_event`、`plan_recovery`、`update_task_state`、`_atomic_write`、`_try_lock`）
- 只读约束：`framework-unification.md:299`（§8.1）、`:103`（§3.3）
- Production 判定器只读：`scripts/validate_change.py`
- 前置：change 2043（门层合并，单一执行链）
