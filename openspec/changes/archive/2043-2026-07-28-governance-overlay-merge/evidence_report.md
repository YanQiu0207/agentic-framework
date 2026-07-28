# 三判据与治理强度举证报告（change 2043 Task 3／Task 4）

> 生成时间：2026-07-27。两判据**同时**通过，不只过其一。

## 一、三判据（2036 §8.5）

### 判据一：状态源唯一——通过

静态检索（`grep -rn "状态：" scripts/*.py skills/*/scripts/*.py`）：全仓库构造 `- 状态：` 写行的位置只有 `skills/workflow-code-generation/scripts/workflow_control.py:806`（`update_task_state`）；`validate_change.py` 的命中全部为只读错误消息文本。任务头标记无独立写入点（由同一函数统一写回）。校验器只读由 change 2038 的检索证明覆盖。

### 判据二：门为叠加——通过

`transition_baseline.json`（Task 1 冻结，含 2039 的待批准转移共 10 项）与挂载守卫后的 `_VALID_TRANSITIONS` 逐字节相同：守卫只增前置条件，转移图结构不变。守卫统一走 `guard_errors`，`profile != "production"` 时全部返回空列表，结构上无法新增转移。

### 判据三：降级等价——通过

两项证据，非「无法执行」：

1. 事件序列基线重跑：Task 1 冻结的 7 事件序列（start→quality_passed→merge_success→start→failure×3）含决策、写回文本、阻塞传播与恢复计划，挂载守卫后重跑逐字节相同（库级行为零变化）。
2. change 2042 比对器跑通，结论「通过」：路径 A 为 `workflow_control --governance-profile tooling event 1 start`，路径 B 为同一输入经 manifest 声明 tooling 的无 flag 调用，归一输出逐字节相同——开关存在且有效，守卫关闭后与纯 Tooling 一致。

## 二、治理强度判据（2036 §3.2 条件 3）

§5.3 每条强制规则的机器守卫与证据，映射详表见 `s53_mount_mapping.md`：

| §5.3 规则 | 机器守卫 | 用例证据 |
| --- | --- | --- |
| Standard 默认／Quick 低风险 | Plan 总门（`plan_gate_errors` 调 `validate_change` plan） | `test_plan_gate_blocks_execution_on_plan_failure` |
| 三阶段确定性检查 | `validate_change` 保留 Plan／Archive 门角色 | 既有 OPSX 测试套件（`scripts/tests/test_validate_change.py`） |
| `verify.config.json` 有效 | `_require_verify_config_decision`（start 前） | 既有 `test_workflow_control.py` 用例 |
| 普通 Task `standard` 审核 | `task_review_guard_errors`（merge_success 前） | `test_task_review_guard_fails_without_pass_evidence` |
| 高风险 `strict`＋独立 Judge | 同上（报告档位须为 `strict`） | `test_task_review_guard_fails_on_profile_mismatch` |
| 定向 re-review | 报告 verdict／计数／round 有效性 | `_validate_review_report` 既有用例 |
| 波次内串行、无并行写入、无 Run | 无新转移；无 Run Context 创建；`_VALID_TRANSITIONS` 逐字节不变 | 转移图比对（判据二）＋检索证明 |
| 风险暂停＋批准证据 | 2039 `escalate`／`approval_granted`／批准门 | `EscalateTransitionTest`（7 用例） |
| per-task 模式 | 2039 `approval_gate_errors` per-task 分支 | `test_per_task_mode_requires_approval_without_escalation` |
| `irreversible` ⟺ `strict`、错位失败关闭 | Plan 总门（OPSX055／OPSX053） | 既有 `test_validate_change.py` 用例 |
| 状态三向一致 | OPSX056＋`state_consistency_errors` | 既有双轨用例 |
| 交付范围与工作区证据 | 2038 OPSX057-061＋Scoped Delivery | `DeliveryEvidenceTest`（13 用例） |
| 五维 `strict` 集成审核 | `integration_review_guard_errors`＋交付门 production 档 | `test_integration_review_guard_requires_strict` |
| P0/P1 修复循环与两轮上限 | 报告 `p0_count`／`p1_count`／`round` 校验 | 既有报告校验用例 |
| Archive 前知识影响 | 2040 反自证＋OPSX042-048 | `KnowledgeSyncCrossCheckTest`（10 用例） |
| 发布平台条件启用 | 保持不建设 | 范围外（原文即约束） |

无任何一条退化为散文：每条均有对应代码守卫与失败关闭用例（上表逐条可定位）。

## 三、执行链与 opsx-*

- 合并后的 Production 执行链：`workflow_control`（状态机）＋ `governance_guards`（转移守卫）＋ `check_delivery`（交付门）＋ `validate_change`（Plan／Archive 门，库调用）。检索：上述脚本均不引用 `opsx-*`（`grep -rn "opsx-"` 仅命中安装器 Registry）。
- `opsx-*` 文件全部保留：6 个 Skill（`skills/opsx-*`）与 6 个 Command（`commands/opsx-*`）均在，未删除（退役属 change 2045）。
- 执行期推进控制是能力净增：Plan 总门失败时无任务能进入执行；逐任务 Review 与批准门在转移点即时判定，不再只有阶段末尾批量裁决。
- Production 叠加后同一波次内保持串行：未引入并行 worktree 写入，未创建 Run Context，未进入 Run 状态机（无新转移、无 runtime 调用，检索证明）。
