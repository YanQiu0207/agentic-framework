# Trust Model Delta — 显式启用下的声明边界

## MODIFIED Requirements

### Requirement：Runtime/Trust 声明只来自完整 Runtime Run

完整 Runtime 仅经显式选择或硬性审计要求启用后，其 Manifest、Journal、能力探测与 Trust Gate 声明才可产生。默认 Native 流程零 Runtime 初始化、零能力探测、零 Journal 写入；Native 产物（含 v2 subject 绑定报告与 Verdict）不得声明 runtime-trust-gate、harness-capability-probe、run-manifest-evidence-graph、强身份隔离或语义正确性——这些固定列入 `unprovable_claims`。

#### Scenario：路由不再自动产生信任升级

strict、并行 Worktree、普通恢复在未显式要求 Runtime 时全部走 Native；不因风险高而自动获得 Run 证据链。用户覆盖（例如在 SVN 上强求 Runtime）失败关闭，不产生降级的信任声明。

#### Scenario：Native v2 的有界裁决

Native Verdict v2 只声明实际核验过的事实：内容主体三方一致（Review/Verify/当前内容同 subject）、机器验证、对应档位 Review 与知识影响。strict 的三项独立性字段只核验流程分离声明（implementer/judge 不同且依据非空），不保证强身份隔离或语义正确性；这些边界写入 `unprovable_claims`，交付门不得把「生成了 Verdict」当作正式交付成功。

#### Scenario：旧报告不升级为新证据

无 subject 的 v1 报告只按旧合同展示历史结果；新完成门（quality_passed、Native 交付门）要求 v2 证据，不为旧报告补造主体或独立性声明。Runtime v1 证据继续按原合同读取与校验。

## Verification

`python -m pytest scripts/test_runtime_trust.py scripts/test_native_delivery.py scripts/test_check_delivery.py scripts/test_workflow_control.py -q`。
