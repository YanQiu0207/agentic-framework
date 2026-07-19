# Runtime Trust Model 威胁用例

这些用例固定最小 Trust Gate 的失败关闭边界。端到端实现位于 `scripts/test_runtime_trust.py`，不得用人工口头确认替代。

| ID | 威胁 | 攻击或漂移方式 | 预期结果 | 自动化证据 |
| --- | --- | --- | --- | --- |
| `TRUST-01` | 伪造 Review 报告 | 构造 Schema 合法的 `PASS`，但省略独立 Judge 声明，或令 Judge 与实现者相同 | Trust Gate 失败 | `test_forged_or_self_judged_strict_report_is_rejected` |
| `TRUST-02` | 替换 Artifact | Manifest 生成后修改 Verify Artifact 内容 | 摘要校验失败 | `test_replaced_artifact_and_cross_run_report_are_rejected` |
| `TRUST-03` | 串 Run | 把其他 Run 的 Review Artifact 换入当前 Manifest，并同步文件摘要 | Run binding 校验失败 | `test_replaced_artifact_and_cross_run_report_are_rejected` |
| `TRUST-04` | 重复副作用 | 恢复时使用相同幂等键再次提交副作用 | 相同副作用去重，不同副作用冲突失败 | `test_duplicate_side_effect_is_deduplicated_or_conflicts` |
| `TRUST-05` | Harness 能力漂移 | 静态声明或旧探测允许执行，但当前运行探测显示必需能力缺失 | 启动门和 Trust Gate 均失败 | `test_harness_capability_drift_fails_before_trust_passes` |
| `TRUST-06` | 静默人工覆盖 | 构造无用户理由的 `user-override` 事件 | Trust Gate 失败 | `test_user_override_without_reason_is_rejected` |
| `TRUST-07` | 过度声明 | 所有结构化证据均通过后，声称语义结论必然正确或主机未被攻破 | 报告必须列入不可证明边界 | `test_complete_run_passes_with_explicit_unprovable_boundaries` |

用例只验证仓库内合同在可信主机上的行为，不模拟已完全控制文件系统、进程和 Git 的攻击者。
