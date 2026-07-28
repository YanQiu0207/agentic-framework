# §5.3 强制规则逐条挂载映射表（change 2043 Task 1）

> 生成时间：2026-07-27。每条规则的挂载转移与守卫内容；守卫只在 `profile=production` 时生效，缺失证据一律失败关闭。无任何一条退化为「由流程文档要求」。

| # | §5.3 规则 | 挂载的转移／门禁点 | 守卫实现 | 形态 |
| --- | --- | --- | --- | --- |
| 1 | Standard 为默认路径；Quick 仅限明确低风险 | Plan 总门（进入执行前） | `validate_change` plan 阶段（OPSX016/018/019 系检查） | 既有，经合同二挂载 |
| 2 | `validate_change.py` 负责三阶段确定性检查 | Plan 总门、Archive 门 | `validate_change.validate_change` 被引擎直接调用 | 既有，角色保留 |
| 3 | `verify.config.json` 必须有效 | 任务进入实现前（start） | `_require_verify_config_decision`（已有） | 既有 |
| 4 | 普通 Task 一次 `standard` 综合审核 | 任务 `完成` 转移前（merge_success） | `governance_guards.task_review_guard_errors`：`- Task Review: PASS`＋有效 scope=task 报告＋档位一致 | 新增 |
| 5 | 高风险 Task 一次 `strict` 审核＋独立 Judge | 同上（按 `review_profile`） | 同上守卫，`strict` 声明要求报告 `review_profile=strict` | 新增 |
| 6 | finding 修复后只定向 re-review | 同 4/5 | 守卫校验报告 verdict／计数／round 字段有效；re-review 语义由 Review 技能合同承载，门禁面为报告有效性 | 部分新增 |
| 7 | 同一波次内串行，不引入并行写入或 Run 状态机 | 全转移 | 无并行写路径引入、无 Run Context 创建（检索证明＋无新转移） | 既有约束保持 |
| 8 | 风险触发暂停＋批准证据 | escalate 转移与 merge_success 批准门 | change 2039：`escalate`／`approval_granted`／`approval_gate_errors` | 既有（2039） |
| 9 | per-task 模式全量批准 | merge_success 批准门 | change 2039：`approval_gate_errors` 的 per-task 分支 | 既有（2039） |
| 10 | `irreversible` ⟺ `strict` 双向绑定、错位声明失败关闭 | Plan 总门 | `validate_change` plan 阶段（OPSX055／OPSX053） | 既有，经合同二挂载 |
| 11 | `- 状态:` 与任务头标记双向一致 | Plan 总门＋Tooling lint | OPSX056（plan）＋`state_consistency_errors` | 既有 |
| 12 | 交付范围与工作区证据 | Delivery 门禁 | change 2038（OPSX057-061）＋`check_delivery` Scoped Delivery | 既有（2038/2033） |
| 13 | 全部完成后一次五维 `strict` 集成审核 | Delivery 门禁 | `check_delivery` 在 production 下要求集成 Review 报告 `review_profile=strict` | 新增 |
| 14 | 首轮存在 P0/P1 才进入修复循环 | 同 4/5/13 | 报告 `p0_count`／`p1_count` 非零即不可 PASS（报告校验既有） | 既有 |
| 15 | 修复后重跑受影响门禁再定向 re-review | 同 6 | 同 6 | 部分新增 |
| 16 | 定向 re-review 最多两轮，仍未过转人工 | 同 6 | round 语义由 Review 技能合同承载，门禁面为报告有效性 | 部分新增 |
| 17 | Archive 前知识影响检查与 Delta 同步 | Delivery／Archive 门禁 | change 2040 反自证（`check_delivery`）＋OPSX042-048（archive） | 既有（2040） |
| 18 | 发布、灰度等平台能力按风险条件启用 | 不在首轮建设 | 无对应门禁，保持不建设 | 范围外（原文即约束） |

## 两项硬合同的落实位置

- **合同一（逐任务 Review 粒度）**：`governance_guards.task_review_guard_errors`，挂在 `merge_success` 前；按任务声明的 `review_profile`（别名兼容）要求 `- Task Review: PASS`＋`validate_change._validate_review_report(..., scope="task")` 通过＋报告 `review_profile` 与声明一致。缺失、不合规、Judge 非独立（报告档位不符）时转移不发生。禁止统一收尾：守卫逐任务触发，无「全部完成后一次」的路径。
- **合同二（Plan 总门）**：`governance_guards.plan_gate_errors`，挂在每次 `start` 前；production 下直接调用 `validate_change.validate_change(repo, change, "plan")`，失败则无任务能进入执行。不拆散到各转移——执行期守卫（4/5/8/9/13）是总门**之外**的增量。
