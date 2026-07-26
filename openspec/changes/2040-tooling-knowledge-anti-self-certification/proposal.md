# Proposal：Tooling 引入知识反自证核对

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：tooling-knowledge-anti-self-certification
**状态**：Draft

---

## 1. 问题

Tooling 的知识影响门只有一个布尔判断，Production 有一整套交叉核对。

实测：

```
grep -c "_delta_targets\|change/specs" skills/workflow-code-generation/scripts/check_delivery.py  →  0
```

Tooling 侧的全部知识门是 `check_delivery.py:608` 的一个 CLI 条件：

```python
requires_knowledge_impact = args.native_delivery or (
    args.tasks is None and args.spec is None
)
```

命中时 `checks += 1`，即「有没有做知识影响检查」这一个计数。**Agent 自己说做了就算做了**——没有任何东西核对它说的与实际改了什么是否一致。

Production 侧则从 Change-local `specs/` 反推目标，与 `tasks.md` 的知识同步表交叉比对：

| 元素 | 内容 | 出处 |
| --- | --- | --- |
| `_delta_targets` | 从 Change 的 `specs/` 反推应同步的长期目标路径 | `scripts/validate_change.py:964` |
| `_knowledge_sync_rows` | 解析 `tasks.md` 的知识同步表 | `:992` |
| `COMPLETED_SYNC_STATUSES` | 同步状态词表 | `:87`，判定在 `:1070` |
| OPSX042 至 OPSX051 | 十个错误码，覆盖漏报、误报、状态未完成、路径不匹配等 | `:978` 至 `:1140` |

核心机制是**反自证**：不问 Agent「你同步了吗」，而是从实际存在的 Delta 文件反推「你应该同步什么」，再核对声明。Agent 无法通过只写声明来蒙混。

## 2. 为什么这是收敛的必要条件

与 change 2039 同理：`framework-unification.md` §3.2 的重新评估条件 3 要求 Production 的强制规则逐条仍可被机器门禁强制。

§5.3 有一条：

> Archive 前必须完成知识影响检查；只将已验证且值得长期保留的 Delta 同步到 `openspec/specs/`，冲突未解决时不得静默合并。

Tooling 的布尔计数无法承载这条规则。条件 3 因此无法举证。

## 3. 与 change 2034 的关系

change 2034 修的是**覆盖问题**：知识门只在部分路径生效，Runtime Run 与 Scoped Delivery 跳过。本 Change 修的是**强度问题**：即使生效了，也只是自证。

两者互不替代，也无实现冲突——2034 改的是 `requires_knowledge_impact` 的判定条件，本 Change 改的是命中之后做什么。**建议 2034 先落地**，否则本 Change 加强的检查在两条重路径上仍然不跑。

## 4. 目标

1. Tooling 的知识影响检查从「计数」变为「交叉核对」。
2. 从 Change-local `specs/` 反推应同步目标，与声明比对，漏报与误报都失败关闭。
3. 同步状态未完成时失败关闭。
4. 知识冲突未解决时不得通过。

## 5. 非目标

- **不移植 OPSX 错误码编号**。Tooling 不用 OPSX 命名空间；错误消息形式沿用 Tooling 现有风格。
- **不改 Production**。`validate_change.py` 零改动。
- **不改 `requires_knowledge_impact` 的判定条件**。那是 change 2034 的范围，本 Change 不碰。
- **不统一两轨的知识同步表格式**。若格式已一致则复用解析，若不一致，本 Change 只适配不改格式。
- **不做知识内容的语义判断**。只核对声明与实际 Delta 的结构对应关系，不判断同步内容是否正确。

## 6. 设计方案

### 6.1 复用 Production 的解析逻辑，还是重新实现

Production 的 `_delta_targets` 与 `_knowledge_sync_rows` 都在 `validate_change.py` 内，不是共享模块。三个选项：

| 方案 | 取舍 |
| --- | --- |
| 提取到 `scripts/` 共享模块，两轨共用 | **倾向采纳**：与 change 2035 的 AST 同思路，避免第三次重复实现 |
| Tooling 直接 `import validate_change` | 拒绝：会把整个 Production 校验器拉进 Tooling 依赖 |
| Tooling 重新实现 | 拒绝：这正是 §8.2 触发条件 1「同一解析缺陷必须在两个实现重复修复」的成因 |

若采纳提取方案，Production 侧会有改动（改为 import 共享模块），与 §5「不改 Production」冲突。**实现方必须裁决：是接受 Production 的机械改动，还是另择方案。** 倾向接受——`validate_change.py` 的判定逻辑不变，只是解析搬家，可用与 change 2035 相同的 golden 基线证明零行为变更。

### 6.2 检查项的取舍

Production 的十个错误码不必逐一移植。必须有的是反自证骨架：

1. Delta 存在但未声明（漏报）。
2. 声明了但 Delta 不存在（误报）。
3. 声明的目标路径与 Delta 反推的路径不匹配。
4. 同步状态未达完成态。
5. 知识冲突节为空或仍是占位文字。

其余属于 Production 的阶段特定检查，不强求。

### 6.3 未裁决项

**Tooling 的 Change 是否都有 `specs/` 目录。** Production 的 Standard 流程必有（§5.4），Quick 流程没有。Tooling 的 Native Delivery 大量使用 proposal + tasks 两文件形态（本仓库 change 2034 即是）。无 `specs/` 时反推来源是什么，需要裁决。倾向：无 `specs/` 时改用「知识同步表声明的目标路径是否真实存在且被本次改动 touch」作为反向证据，而不是直接放行。

## 7. 验收标准

1. 知识影响检查执行交叉核对，不再只做计数。
2. 漏报、误报、路径不匹配、状态未完成、冲突未填写，五类各自失败关闭并有用例。
3. 无 `specs/` 目录时的反推来源已裁决并实现，不直接放行，有用例。
4. 若采纳共享模块方案：Production 的判定结果对全部活跃与归档 Change 逐一比对无变化。
5. 若采纳共享模块方案：`validate_change.py` 中的重复解析逻辑已删除，无残留死代码。
6. `check_delivery.py:608` 的 `requires_knowledge_impact` 判定条件未被本 Change 修改。
7. 不存在静默跳过分支，用检索证明。
8. Tooling 未引入 OPSX 命名空间。
9. `python -m pytest scripts -q` 全量通过。
10. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/framework/knowledge-management/overview.md`：MODIFIED。记录 Tooling 侧的反自证核对。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§6.3 新增条目；记录这是 §3.2 条件 3 的部分举证。

## 9. 参考资料

- Tooling 无反自证：`skills/workflow-code-generation/scripts/check_delivery.py`，`_delta_targets`／`change/specs` 出现 0 次
- Tooling 现有知识门：同文件 `:608`
- Production 实现：`scripts/validate_change.py:964`（`_delta_targets`）、`:992`（`_knowledge_sync_rows`）、`:87`／`:1070`（同步状态）、`:978-1140`（OPSX042-051）
- Production 规则描述：`openspec/specs/backend/engineering/tech/framework-unification.md:194`（§5.3）
- 覆盖问题的前置 Change：`openspec/changes/2034-knowledge-gate-risk-inversion/proposal.md`
- 重复实现的触发条件：`framework-unification.md:307`（§8.2 条件 1）
- 同思路的提取先例：`openspec/changes/2035-common-task-ast/`
