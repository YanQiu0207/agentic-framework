# Proposal：门层合并——Production 治理门叠加到 Tooling 底座

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：governance-overlay-merge
**状态**：Draft

---

## 1. 问题

这是目标模型的核心一步，也是此前所有 Change 的汇聚点。

目标模型（用户提出）：

> Tooling 是统一执行底座；Production 是按风险启用的治理升级策略，而不是第二套独立流程。同一任务只走一条执行链；当风险命中时，在 Tooling 的节点上叠加 Production 门，而不是切换到另一套 `opsx-*` 生命周期。

当前结构是两条独立链：

```
Production：Requirements → Specs → Design → Tasks → Plan 门 → 波次实现+Review
           → 风险暂停+批准证据 → Verification → Delivery 门 → strict 集成 Review
           → 知识检查 → Archive 门

Tooling：  需求明确 → [Native Delivery / Quick Design / 完整 Tasks]
           → workflow_control route → Native Delivery（DAG/worktree/Review）
           → 或 Runtime Run（升级命中）
```

两条链各自推进任务，各自的门禁各自判定。**本 Change 把它们并为一条：任务只在 Tooling 的状态机上推进，Production 的治理门作为可声明的叠加，挂在同一状态机的转移上。**

### 1.1 与已批准总规的关系：语义差异保留，承载经授权合并

必须先说清楚：「两个长期独立的 Policy Profile」「不把 Production 与 Tooling 强行合成一条工作流」「不合并为同一状态机」这些约束，在 change 2036 之前是无条件禁令。单看旧条文，本 Change 的「并为一条」确实与之冲突。

但 **change 2036 已经裁决了这个边界**，且已提交（`8d88232`）。它把命题拆成两个：

- **语义差异必须保留**（人工介入点、执行策略、归档要求、Verification 失败策略、默认风险偏好）——无条件，本 Change 一条不删。
- **差异的承载方式**——从「两套独立实现」放宽为「可声明策略叠加」，条件式，由 §3.2 三条重新评估条件与 §8.1 的三层拆分（读层／门层／写层）把守。

因此本 Change 的「并为一条执行链」**不是推翻总规，而是在 2036 授权的门层路径内执行**。它合并的是承载，不是语义；它受 2036 的三判据（状态源唯一、门为叠加、降级等价）与治理强度判据约束，缺一不交付。任何「Production 治理语义被削弱」的读法都是对 2036 的误读——2036 把语义保留写成了无条件约束。

**前置关系的完整表述**：2036 是规格授权（为什么可以做），2035／2038／2039／2040／2041／2042 是能力前置（拿什么做）。本 Change 只在两者齐备后才可执行。

## 2. 本 Change 的大前提：前置 Change 全部就位

门层合并不是孤立改动，它消费前面五个 Change 的成果：

| 前置 | 提供什么 | 状态 |
| --- | --- | --- |
| change 2035 | 统一读层（AST、字段名别名、状态取值归一） | 已交付文档 |
| change 2038 | Production 复用交付证据 | 已交付文档 |
| change 2039 | Tooling 的审批／升级状态机能力 | 已交付文档 |
| change 2040 | Tooling 的知识反自证 | 已交付文档 |
| change 2041 | 可声明 Profile 开关 + `review_profile` 下限 | 已交付文档 |
| change 2042 | 降级等价判据的可执行实现 | 已交付文档 |

规格授权前置（不属于能力，但同样阻塞）：**change 2036**——它把「不合并」从无条件禁令改为条件式，并提供 §3.2 三条重新评估条件与 §8.1 三层拆分。没有 2036，本 Change 的「并为一条」直接撞旧禁令；有了 2036，它在授权路径内。已提交（`8d88232`）。

**前置未全部落地前，本 Change 不能执行。** 缺任何一个，门层合并都会在某一项治理规则上失去承载，违反 §3.2 条件 3。

### 2.1 「一条执行链」不引入并行写入或 Run 状态机

`framework-unification.md` §5.3（`:185`）规定 Production「同一波次内保持串行，不引入 Tooling 的并行写入或 Run 状态机」。这条必须明确保留，否则「并为一条」会被误读为 Production 也改用 Tooling 的并行写。

**本 Change 的「一条」指的是同一条任务状态机与写路径，不是同一套并发模型。** 叠加到 Production 时：

- 同一波次内**保持串行**，不启用 Tooling 的并行 worktree 写入。
- **不创建 Run Context**，不进入 Runtime Run 编排；治理门挂在转移上，不触发 Run 状态机。
- Production 复用的只是状态机的串行推进与原子写回，并发策略仍按 §5.3 与 §3.4 由各自 Profile 决定。

这一点同时写入 `tasks.md` 的实现约束，防止实现方把「统一状态机」实现成「统一并发模型」。

## 3. 目标

1. 任务只在 Tooling 状态机上推进，不再有第二条执行链；同一波次内保持串行，不引入并行写入或 Run 状态机（§5.3 `:185` 保留）。
2. Production 的治理门（审批、风险分级、逐任务 Review、严格集成 Review、归档与知识沉淀）作为可声明策略叠加到该状态机。
3. §3.2 三条重新评估条件逐条举证。
4. 降级等价判据通过：减去治理门后，行为与纯 Tooling 逐字节相同。
5. 治理强度判据通过：§5.3 强制规则逐条仍可机器强制，不退化为散文。

## 4. 非目标

- **不删除 Production 的任何治理规则**。§5.3 一条不减，只是承载方式从独立链变为叠加门。
- **不改写状态机本身**。状态机已在 change 2039 扩展出等待批准，本 Change 复用它，不再新增转移。
- **不退役 `opsx-*`**。并行编排的退役由 change 2045 单独处理，本 Change 只让任务不再走它。
- **不改 Review 的语义**。各档 Review 的内容、维度、Judge 独立性不变，只是触发方式变为策略叠加。
- **不做降级等价判据的实现**。判据由 change 2042 建设，本 Change 只**接受其核验**。

## 5. 「叠加而非替换」的判定

change 2036 的 `design.md` §3.1 给了三条判据。门层合并必须满足判据二「门为叠加」：

> Profile 门只增加状态转移的前置条件，不新增、不删除、不重定向状态转移本身。即 `production` 能让一个转移**不发生**，但不能让它转向 `tooling` 下不存在的目标状态。

这条是本 Change 的结构性约束。它意味着：

- 状态转移图**只有一份**，就是 Tooling 的（含 change 2039 扩展）。
- Production 门是转移上的**守卫**，不是新的转移。
- 把守卫全部关掉，剩下的就是纯 Tooling——这正是降级等价判据要验的。

### 5.1 三判据的举证责任

| 判据 | 内容 | 本 Change 如何举证 |
| --- | --- | --- |
| 状态源唯一 | 任务状态只有一个写入者 | 静态核验：`- 状态:` 与任务头标记只有 `workflow_control.py` 写 |
| 门为叠加 | 守卫只增前置条件 | 转移图基线比对：叠加 Production 后转移图不变 |
| 降级等价 | 降级后等于纯 Tooling | change 2042 的比对器跑通 |

三条都过，才允许宣称「收敛为一条执行链」。任何一条不过，本 Change 不交付。

## 6. 设计方案

### 6.1 治理门的挂载点

`framework-unification.md` §5.3 的强制规则，逐条映射到状态机转移上的守卫：

| §5.3 规则 | 挂载的转移 | 守卫内容 |
| --- | --- | --- |
| `verify.config.json` 必须有效 | 任务进入实现前 | 配置缺失或弱化则阻塞 |
| 普通 Task 一次 `standard` 审核 | 任务 `完成` 前 | 无合规 Review 证据则不转移 |
| 高风险 Task 一次 `strict` 审核 + 独立 Judge | 同上（按 `review_profile`） | 无五维证据则不转移 |
| 风险触发暂停 + 批准证据 | 命中 `ESCALATION_CONDITIONS` 时进入 `待批准` | 无 `Approval: granted` 不恢复 |
| 五维 strict 集成 Review | 全部任务终态后、Delivery 前 | 无集成 Review 证据则不放行 |
| 知识影响检查 + Delta 同步 | Archive 前 | change 2040 的反自证核对 |
| 交付范围与工作区证据 | Delivery 前 | change 2038 的证据核对 |

这张表是**设计起点，不是终稿**。实现方必须核对每一条 §5.3 规则都有挂载点，漏一条即违反条件 3。

### 6.2 与「执行期推进控制」的关系

老板在目标模型诊断里指出 Production 的一个真实缺口：`validate_change.py` 只在 plan／delivery／archive 三个阶段**末尾批量裁决**，执行期没有状态推进控制。

门层合并恰好解决这一点：治理门挂在状态机转移上，状态机本身就是执行期推进控制。Production 不再需要「批量补裁」，因为每个转移都被即时守卫。**这是收敛带来的能力净增，不是简单的承载搬家。**

### 6.3 两条 Production 强制语义：硬合同，不留未裁决

对抗性复审指出，把下面两条留成「实现时再定」正是 2036 条件 3（强制规则不退化为散文）要防的口子——它们是 Production 生命周期的硬语义，不是文案细节。因此在提案层钉死为硬合同，实现方照此执行，不得另行选择。

**合同一：逐任务 Review 粒度——按 `review_profile` 声明逐任务触发，禁止统一收尾。**

- Production 下每个 Task 完成实现与测试后，按其 `review_profile` 触发一次对应档位 Review，作为该任务进入 `完成` 转移的前置守卫。
- `standard` 档由独立 `comprehensive-reviewer` 执行一次综合审核；`strict` 档由 5 个专项 Reviewer 加未参与实现的独立 Judge 裁决（§5.3 `:182-183`）。
- **禁止**把 Production 的逐任务 Review 退化为「全部完成后统一收尾」——那是 Tooling 的模型（§6.3），不是 Production 的。Production 叠加后，逐任务粒度**保留**，不与 Tooling 的「收尾一次」对齐。
- change 2041 的 `review_profile` 下限保证 Production 下不低于 `standard`，粒度与档位同为可声明策略但有下限。
- 与 §3.4（`:124`「Production 普通 Task 做一次综合审核，高风险 Task 做一次五维审核」）的一致性：本合同正是这条的机器承载，无冲突。
- 失败关闭：任务声明的 `review_profile` 对应 Review 证据缺失、不合规或 Judge 非独立时，该任务的 `完成` 转移不发生。

**合同二：Plan 总门保留为独立的进入执行前守卫，不拆散到各转移。**

- Production 的 Plan 门（Tasks 获批时的一批静态检查）**保留**为「进入执行前的总守卫」，与执行期的逐转移守卫是两个粒度，互不替代。
- 不得把 Plan 总门拆散下沉到各转移——那会丢失「Tasks 整体获批后才允许任何任务进入执行」这一整体把关语义。
- Plan 总门失败时，没有任何任务能进入执行状态机。
- 执行期转移守卫（§6.1）是 Plan 总门**之外**的增量，不是对它的替代。

这两条与 2036 `design.md` 的「语义不降」对齐：合并承载后，§5.3 的强制规则逐条保住且仍是机器可强制的单一合同。

## 7. 验收标准

1. 任务状态只有一个写入者，静态核验证明。
2. 状态转移图在叠加 Production 门后与纯 Tooling 一致，有基线比对。
3. change 2042 的降级等价比对通过。
4. §5.3 每条强制规则都有挂载守卫，逐条映射表完整无缺漏。
5. 每条守卫在缺失证据时失败关闭，有用例。
6. 治理强度判据：§5.3 强制规则逐条仍可机器强制，无任何一条退化为散文。
7. Production 叠加后同一波次内保持串行，未引入并行 worktree 写入，未创建 Run Context 或进入 Run 状态机，有用例与检索证明。
8. 逐任务 Review 粒度按合同一落地：Production 下每 Task 按 `review_profile` 触发一次对应档位 Review，作为 `完成` 转移前置守卫；`standard` 综合审核、`strict` 五维加独立 Judge 均保留；禁止退化为统一收尾，有用例。
9. Plan 总门按合同二落地：保留为进入执行前的独立总守卫，未拆散到各转移；Plan 总门失败时无任务能进入执行，有用例。
10. 任务不再走 `opsx-*` 执行链；但 `opsx-*` 文件未被删除（退役属 change 2045）。
11. 前置六个能力 Change 与规格授权 change 2036 的就位证据齐全，缺一则本 Change 不交付。
12. 降级等价判据与治理强度判据**同时**通过，不得只过其一。
13. `python -m pytest scripts -q` 全量通过。
14. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§8.1 门层状态改为「条件已满足并合并」；§3.2 三条条件举证记录。
- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED。治理门的挂载结构。
- `openspec/specs/backend/framework/workflow-control/overview.md`：MODIFIED。守卫与转移的关系。

## 9. 参考资料

- 目标模型：用户提出，见 §1
- 三判据：`openspec/specs/backend/engineering/tech/framework-unification.md` §8.1（change 2036）、change 2036 `design.md` §3.1
- 收敛条件：`framework-unification.md` §3.2（change 2036）
- Production 强制规则：`framework-unification.md:177-195`（§5.3）
- 不删质量门原则：`framework-unification.md:122-128`（§3.4）
- 前置 Change：2035、2038、2039、2040、2041、2042 的 `proposal.md`
- 执行期推进缺口：`scripts/validate_change.py`（只在阶段末尾批量裁决）
- 退役范围（非本 Change）：`openspec/changes/2045-opsx-orchestration-retirement/proposal.md`
