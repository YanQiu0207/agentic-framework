# Proposal：修复交付门知识影响检查的风险反转

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：knowledge-gate-risk-inversion
**状态**：Draft

---

## 1. 问题

`check_delivery.py` 的知识影响检查只对两条轻量路径生效，对两条重量路径完全跳过。门禁条件为：

```python
requires_knowledge_impact = args.native_delivery or (
    args.tasks is None and args.spec is None
)
```

出处：`skills/workflow-code-generation/scripts/check_delivery.py:608`。

runtime-run 与 scoped-delivery 都传 `--tasks` 与 `--spec` 且不传 `--native-delivery`，因此两者都落到 `False`。实测四条路径：

| 交付路径 | `requires_knowledge_impact` | 触发条件 |
| --- | ---: | --- |
| native-delivery | `True` | Tooling 默认路径 |
| fast-path | `True` | 局部低风险兼容别名 |
| runtime-run | **`False`** | `strict` 风险、并行 worktree 写入、长任务恢复、跨宿主验证或审计要求 |
| scoped-delivery | **`False`** | 预存残留基线交付 |

**结果是风险越高、机器知识门越少。** 最轻的 fast-path 有检查，`strict` 档且带审计要求才会进入的 runtime-run 一条都没有。这不是「Tooling 比 Production 宽松」的档位差异，而是 Tooling 自身档位排序反了。

runtime-run 的实际检查清单为：任务终态（`check_tasks`）、spec 已归档（`check_spec`）、工作区干净（`check_git_clean`）、Review 报告 `verdict=PASS` 且 P0/P1 计数为 0（`check_review_report`），加上 `--run-dir` 带来的 Manifest、Journal、Harness 启动证据与 Trust Gate 检查。其中不含任何知识项。证据：`check_delivery.py:628-700`。

`skills/workflow-code-generation/SKILL.md:148` 的散文确实要求归档前加载 `project-knowledge` 完成 Delta、索引、Issues 与冲突检查，但那由宿主 Agent 语义执行，不是机器门；缺失时没有非 0 退出码。

产出格式其实已经齐备。仓库内归档的 Change 都在 `tasks.md` 写了「知识同步」「知识冲突」「实际 Diff 核对」三个小节：

- `openspec/changes/archive/2029-2026-07-25-risk-triggered-task-approval/tasks.md:46,161,165`
- `openspec/changes/archive/2032-2026-07-26-task-status-consistency-gate/tasks.md:40,48,52`

但没有任何 Tooling 脚本读取它们。缺的是校验，不是格式。

## 2. 目标

1. 四条交付路径都必须声明知识影响结论，`runtime-run` 与 `scoped-delivery` 缺失时失败关闭。
2. 保持现有输出的逐字可引用格式，不改变 `PASS` / `ERROR` 行的既有措辞结构。
3. `SKILL.md` 中 runtime-run 与 scoped-delivery 的调用示例同步补齐新参数。

## 3. 非目标

- **不引入 Delta 与磁盘文件的交叉核对**。Production 侧 `validate_change.py` 的 OPSX042 至 OPSX051 从 `change/specs/` 反推期望映射，再与声明表逐项比对，其中 OPSX043 的「声明无影响但存在 Delta 文件即判错」是反自证机制。把这套移进 Tooling 属于统一核心改造的范围，与本 Change 的排序修复是两件事，混做会让回退粒度失控。
- **不解决知识影响的自证问题**。`--knowledge-impact none --knowledge-impact-reason "..."` 由执行方在命令行声明，无磁盘核对。本 Change 只把这条弱检查补齐到全部路径，不改变其强度。这一限制与 change 2030、2032 记录的同类边界一致：门禁改善的是覆盖与一致性，不是证据可信度。
- **不改 `tasks.md` 三个知识小节的格式**，不动 `lint_task_deps.py` 的字段集合。
- **不回填已归档 Change**。归档目录记录当时证据，回改等于篡改历史。新门禁只对之后的交付生效。

## 4. 验收标准

1. runtime-run 路径缺少 `--knowledge-impact` 时，`check_delivery.py` 以非 0 退出并指明缺失参数。
2. scoped-delivery 路径缺少 `--knowledge-impact` 时，同样非 0 退出并指明缺失参数。
3. 四条路径传入 `--knowledge-impact none` 但 `--knowledge-impact-reason` 为空或纯空白时，均非 0 退出。
4. `--knowledge-impact` 取值不在 `hit` 与 `none` 之内时非 0 退出，不静默跳过。
5. 四条路径的 `PASS` 行都包含各自路径名与知识影响结论；取 `none` 时逐字包含理由原文。
6. `checks` 计数在四条路径上都包含知识影响这一项，交付报告的检查总数与实际执行项一致。
7. `python -m pytest scripts -q` 全量通过；新增用例覆盖上述每条，且覆盖四条路径各自的成功与失败形态。
8. `SKILL.md` 的 runtime-run 与 scoped-delivery 调用示例已补 `--knowledge-impact`，与实现后的参数合同一致。

## 5. 留给实现方的决策点

以下两点本 Proposal 不预先裁决，需实现方在 `design.md` 中给出结论与理由。

**参数合同的破坏性**。补齐检查后，现有不带 `--knowledge-impact` 的 runtime-run 与 scoped-delivery 调用会从通过变为非 0。这是期望行为，但需要明确：是直接失败关闭，还是设一个过渡期内的显式降级参数。倾向直接失败关闭 —— 过渡参数本身会变成新的绕过入口，与 `verify.config.json` 不得弱化的既有原则同向。

**门禁条件的写法**。可以把条件直接改为恒 `True`，也可以按路径分别声明所需参数。前者最简，但会让 `requires_knowledge_impact` 这个变量失去意义；后者更显式，但引入四路分支。建议前者，并删除随之变为死代码的条件变量。

## 6. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED，补四条交付路径统一要求知识影响结论的行为。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED，§6.3 Tooling 强制规则补本条；§10 Verification 对照表的 Tooling 列需说明知识影响不再按路径豁免。

## 7. 参考资料

- 反转现场：`skills/workflow-code-generation/scripts/check_delivery.py:608`
- 弱检查实现：`skills/workflow-code-generation/scripts/check_delivery.py:446-452`
- runtime-run 检查清单：`skills/workflow-code-generation/scripts/check_delivery.py:628-700`
- 散文要求：`skills/workflow-code-generation/SKILL.md:148,150`
- Production 侧反自证机制（本 Change 不移植，仅作对照）：`scripts/validate_change.py:964-1151`
- 同类失败关闭先例：change 2030（OPSX055 与 LOOSE 正则）、change 2032（任务状态三向一致）
