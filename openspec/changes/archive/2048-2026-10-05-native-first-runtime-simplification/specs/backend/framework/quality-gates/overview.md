# Quality Gates Delta — Native v2 合同

## MODIFIED Requirements

### Native 独立产物 v2

standalone Verify 顶层必须具有 `schema_version: 2` 和 `subject_id`（`sha256:` 加64位小写十六进制）。保留完整 CheckResult、结果数量、错误/违规计数与 Spec Drift 一致性；递归拒绝 Runtime、Trust 或独立审查声明，不能通过 value 嵌套绕过。缺字段、未知版本和非JSON类型失败关闭。

Native Review v2 使用原六字段加版本和 subject；strict 额外必填 implementer_actor、judge_actor、independence_basis，非空且两参与者经去首尾空白后不同。standard/lightweight 不允许独立性字段。PASS 必须 P0/P1=0。该声明只核验流程分离，不保证强身份隔离、语义正确性或执行历史。

subject 的固定检查基准由交付门显式 CLI/冻结 baseline 与公共固定分类算法提供；报告不能自选任意排除策略，不能给旧报告补造主体。报告 v1 使用旧读路径，新 v2 构造器拒绝 v1；Runtime v1 Schema、字段语义及读取入口保持。

### Native Verdict v2

`native_delivery.build_verdict` 消费真实已校验的 Verify/Review 与当前 subject，要求三者一致、两报告 PASS、Review scope=integration。最终产物保留路径引用及 canonical JSON SHA256 摘要；不内嵌重复报告。strict 分离摘要只能从真实已校验 Review 复制，不能从调用者布尔值产生。

- Git `native-delivery-pass` 必填 git_clean=true 和40位 commit_sha；SVN字段不允许混入。
- Git `git-scoped-delivery-pass` 必填 commit_sha（当前 HEAD）、冻结 scope_paths 与 S0 residue_snapshot_digest；Scoped Delivery 不用虚假 git_clean 包装脏工作区，成功仅表述为「本次交付范围干净，预存残留未变化」。
- SVN `svn-pending-commit` 必填 repository_uuid、repository_relative_url，绑定工作副本 subject；只表示本地验证待提交，不是正式交付 PASS。
- SVN `svn-revision-verified` 额外要求正整数 revision 与 revision_subject_id==subject_id；对应确切版本必须具有匹配的 Verify/Review。交付门经公共只读接口核验节点基准、范围、内容与属性（未版本化残留走 S0/S1 快照通道，不混入版本内容比对）；查询门不代执行 commit/update/revert，提交结果不明或提交后验证失败保留实际状态、不自动回退或重提。他人不同文件的提交被接纳后，提交前报告不算验证过该组合——必须按确切 revision 内容重新取证。

`validate_verdict` 不访问任意引用路径，不进行 VCS 写入，不初始化 Run。独立调用仅校验结构/声明；同时提供真实 Verify/Review 时核对摘要、subject、档位和严格分离摘要，单独提供一份报告拒绝。交付门负责读取真实文件并重算当前内容及正式交付事实，不能把结构有效解释为事实来源已经证明。

verified_claims 必须精确对应状态和档位；unprovable_claims 明确包括 Runtime Trust、宿主探测、Manifest图、强身份隔离和语义正确性。不能凭 Verdict 已生成推断正式交付成功。

## Verification

`python -m pytest scripts/test_native_delivery.py scripts/test_runtime_schema.py -q`：三档正常结果、版本拒绝、Verify递归禁止项、strict伪造与同人、subject/摘要错配、SVN状态条件与旧Runtime回归。交付门接线与真实 SVN 事实核验（两 WC 竞态、确切 revision 隔离验证、无远程写入）见 `python -m pytest scripts/test_check_delivery.py scripts/test_workspace_residue.py scripts/tests/test_validate_change.py -q`。
