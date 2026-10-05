# 质量门概览

## 职责划分

框架把确定性质量门、机器 Verification 与语义 Code Review 分开：

| 层 | 入口 | 职责 |
| --- | --- | --- |
| Production 阶段门 | `scripts/validate_change.py` | 只读校验 Plan、Delivery、Archive 的 Artifact 与证据合同 |
| Tooling Task 门 | `workflow_control.py quality_passed` | 要求 Task 机器验证报告为 `PASS`（Native 只接受 v2） |
| Tooling Run 交付门 | `check_delivery.py` | 校验归档、终态、Review JSON、知识影响、工作区状态并输出有界 Verdict |
| 机器 Verification | `workflow-verification/scripts/verify.py` | 执行项目配置、比较基线、检查 Spec Drift 并生成 JSON 报告 |
| 语义 Review | `workflow-code-review` 与 `agents/` | 按风险分档审查 Diff；`lightweight` / `standard` 由 `comprehensive-reviewer` 自证并生成 Artifact，`strict` 由独立 Judge 输出最终 Markdown 与结构化 JSON |

这些层相互提供证据，但不能互相替代。

Tooling 的 Fast-Path、Native Delivery、Runtime Run 与 Scoped Delivery 都必须声明 `--knowledge-impact hit|none`。`none` 必须附非空理由；缺失、空理由或非法值均失败关闭。Scoped Delivery 因必须同时使用 `--native-delivery` 而沿用同一检查，但输出以 Scoped Delivery 标识，避免将四条路径混淆。

## Native v2 报告合同（change 2048）

standalone Verify 顶层必须具有 `schema_version: 2` 和 `subject_id`（`sha256:` 加 64 位小写十六进制）：检查前后核对同一内容主体，检查期间输入变化或覆盖不完整时结果无效（不产生 PASS）。Native Review v2 使用原六字段加版本和 subject；`strict` 额外必填 `implementer_actor`、`judge_actor`、`independence_basis`（非空且两参与者不同），standard/lightweight 不允许独立性字段；PASS 必须 P0/P1=0。声明只核验流程分离，不保证强身份隔离或语义正确性。subject 的固定检查基准由交付门显式 CLI／冻结 baseline 与公共固定分类算法提供；报告不能自选任意排除策略，不能给旧报告补造主体。v1 报告使用旧读路径，新完成证据（`quality_passed`、Native 交付门）不接受 v1；Runtime v1 Schema、字段语义及读取入口保持。

Native Verdict v2 由 `native_delivery.build_verdict` 从真实已校验的 Verify/Review 与当前 subject 构造，要求三者一致、两报告 PASS、Review scope=integration；产物保留路径引用及 canonical JSON SHA256 摘要，不内嵌重复报告。四种终态：

- Git `native-delivery-pass` 必填 git_clean=true 和 40 位 commit_sha；SVN 字段不允许混入。
- Git `git-scoped-delivery-pass` 必填 commit_sha（当前 HEAD）、冻结 scope_paths 与 S0 residue_snapshot_digest；Scoped Delivery 不用虚假 git_clean 包装脏工作区，成功仅表述为「本次交付范围干净，预存残留未变化」。
- SVN `svn-pending-commit` 必填 repository_uuid、repository_relative_url，绑定工作副本 subject；只表示本地验证待提交，不是正式交付 PASS。
- SVN `svn-revision-verified` 额外要求正整数 revision 与 revision_subject_id==subject_id；交付门经公共只读接口核验节点基准、范围、内容与属性（未版本化残留走 S0/S1 快照通道，不混入版本内容比对）；查询门不代执行 commit/update/revert，提交结果不明或提交后验证失败保留实际状态、不自动回退或重提。他人不同文件的提交被接纳后，提交前报告不算验证过该组合——必须按确切 revision 内容重新取证。

`validate_verdict` 不访问任意引用路径，不进行 VCS 写入，不初始化 Run。verified_claims 必须精确对应状态和档位；unprovable_claims 明确包括 Runtime Trust、宿主探测、Manifest 图、强身份隔离和语义正确性——不能凭 Verdict 已生成推断正式交付成功。

## Production 阶段门

`validate_change.py` 支持 `plan`、`delivery` 和 `archive` 三个阶段（`scripts/validate_change.py:17-57,1375-1479`）：

- Plan 检查 Change 类型、Proposal、Tasks、依赖、文档映射和 Task Review 合同。
- Delivery 检查任务完成、执行记录、Task 级 Review 证据和风险触发批准证据。
- Archive 检查集成 Review、知识同步、Delta 映射、冲突记录、索引影响和归档目标。
- 目录边界、命名、重解析点和代码派生知识元数据均采用失败关闭。

校验器只读取 Change 和证据，不维护第二套执行状态。对应回归测试位于 `scripts/tests/test_validate_change.py`。

风险触发批准由 Change `2029-risk-triggered-task-approval` 定义：Completed Task 声明 `Escalation` 时，必须具有条件集合一致的 `Approval: granted`；`pending`、缺失、重复、条件非法或不一致均失败关闭。头部声明 `批准模式：per-task` 时，全部 Completed Task 都必须获批；默认 `risk-triggered` 模式的未升级 Task 不要求 Approval。

OPSX055（Change `2030-approval-gate-hardening`）双向强制 `irreversible` ⟺ `Review Profile: strict`，且在 `plan` 阶段即生效——两个字段都是规划期产物。反向约束是关键：`strict` 档却未声明 `irreversible` 意味着高风险 Task 不触发暂停，这是风险触发门唯一可能弱于「无条件逐 Task 批准」的路径。该校验只对声明了 `Escalation` 字段的 Task 生效（值为「无」也算声明），未声明该字段的 Task 不参与，既有归档 Change 不回归。

OPSX056（Change `2032-task-status-consistency-gate`）交叉核对 `- 状态：` 字段与任务头标记，在 `delivery` 与 `archive` 阶段生效。双向都判：`- 状态：完成` 配 `[pending]` 任务头，与 `[completed]` 任务头配 `- 状态：阻塞`，都是矛盾；后者更危险，因为读者按任务头会认为任务已完成。该字段是可选的，未声明的 Task 跳过（保兼容）；声明但取值无法归类为完成／未完成时失败关闭，区域内重复声明同样报错。

判定区域为任务头行到下一个任意级别 Markdown 标题之前，围栏内内容剔除。这比 OPSX030／OPSX031 依赖的任务块更窄：末任务的任务块会延伸到文件末尾，吞掉 `## 知识同步`、`## 知识冲突` 等尾部小节，而这些小节自带 `- 状态: Resolved` 一类字段。

同源失败关闭规则：缩进的 `  - Escalation:`、列表式 `- 批准模式：`、写在头部之外的批准模式声明，均在 `plan` 或 `delivery` 阶段报 OPSX053 而非静默放行。`Escalation` 与 `Approval` 是可选字段，写错位置的默认后果是升级门无声消失，与必填字段的失效方向相反，因此方向必须是失败关闭。

OPSX057-061（Change `2038-production-delivery-evidence`）在 `delivery` 阶段接入交付范围与工作区残留证据，复用 Tooling 的共享模块 `scripts/workspace_residue.py`（逐字节未改动）：未提供 `--workspace-residue-baseline` 或交付提交参数（OPSX057）、基线不可用或无法识别版本控制（OPSX058）、交付提交越出 `tasks.md` 声明的 `- 文件:` 范围（OPSX059）、工作区残留与基线不一致（OPSX060），均失败关闭。唯一出口是 tasks.md 头部的 `- 交付证据豁免: <原因>` 显式声明；豁免声明重复或缩进错位按 OPSX061 失败关闭，豁免记录即声明本身（随版本控制历史可审计）。快照格式与 Tooling 一致，同一份基线文件两轨都能校验。

## 治理 Profile 与 review_profile 下限（change 2041）

门禁从 `.agentic-framework/manifest.json` 的 `profile` 字段读取治理 Profile（共享模块 `scripts/governance_profile.py`），`--governance-profile` 显式覆盖优先；缺失或非法失败关闭，不存在「静默默认为 tooling」的分支。读取是惰性的，只在 `review_profile` 触及下限时发生。

`review_profile` 的 Profile 级下限：`production` 下不得为 `lightweight`（Production 侧 OPSX063，Tooling lint 与交付门同规则）；`tooling` 下三个取值均合法；两轨都允许向上声明 `strict`。无法取得 Profile 时失败关闭（OPSX062）。**Quick 不构成下限例外**：现行实现对 Quick 与 Standard 的 Review 档位要求一致（OPSX037 系检查无 Quick 分支），与 §5.3「Standard 为默认路径；明确低风险且范围稳定时才允许 Quick」一致——Quick 的流程差异在工件（§5.4），不在 Review 档位。

## 降级等价比对（change 2042）

`scripts/downgrade_equivalence.py` 是门层改动的回归门：对同一输入分别走「production 降级到 tooling」与「纯 Tooling」两条命令路径，归一为「退出码＋排序后错误编号集合」（集合语义，重复计数不参与——归一规则显式声明）逐字节比对。三种结论：通过（退出码 0）、不通过（1，两路径都跑出可比结果但不一致，报告列首个差异点）、无法执行（3——开关不存在、开关无效果、基线缺失、输出格式不可比）。「无法执行」与「不通过」同判越界但原因分开标注；不存在按「暂不适用」放行的分支。报告头部固定写明判据局限：只验「减去治理门后等于 Tooling」，不验治理强度（后者由 §3.2 条件 3 承担）。当前两轨输出格式不可比（Tooling lint 无错误编号体系），默认路径对如实报告「无法执行」；门层合并后的回归门以合并引擎的两路径调用。比对器只调用门禁，不搬入任何判定逻辑；降级开关由 change 2041 的 `--governance-profile` 提供。

## 治理门的挂载结构（change 2043）

Production 治理门作为可声明策略叠加在 Tooling 状态机的转移上（门为叠加：只增前置条件，不新增转移；`tooling` 下全部关闭，与纯 Tooling 逐字节一致）：

- `skills/workflow-code-generation/scripts/governance_guards.py`：`plan_gate_errors`（合同二——Plan 总门，production 下 start 前调 `validate_change` plan 阶段，失败则无任务进入执行）、`task_review_guard_errors`（合同一——逐任务 Review，merge_success 前按 `review_profile` 校验 `- Task Review: PASS`＋有效 scope=task 报告＋档位一致，禁止统一收尾）、`integration_review_guard_errors`（production 集成 Review 须 `strict`）。
- 挂载点：`workflow_control` 的 start／merge_success 事件路径（先 2039 批准门，后 2043 守卫；Profile 无法取得失败关闭）；`check_delivery` 的 Native Delivery 分支按 Profile 选择集成 Review 档位（production → strict）。
- 三判据与治理强度同时通过的证据：`openspec/changes/2043-governance-overlay-merge/evidence_report.md`（状态源唯一、转移图不变、降级等价比对通过、§5.3 逐条守卫与用例）。
- `validate_change.py` 的角色变化：从「只在阶段末尾批量裁决」变为「Plan／Archive 总门被引擎直接调用」，执行期推进控制由状态机承担——这是收敛带来的能力净增。

## Tooling 任务状态一致性

`tasks.md` 把「任务是否完成」表达三次：任务头复选框、`- 状态：` 字段、验收标准与子任务复选框。三者必须同向，否则归档记录自相矛盾——只改状态字段即可过门。

`lint_task_deps.state_consistency_errors` 定义判定：`完成` 要求任务头标完成且区域内无未勾选复选框；`需人工`、`阻塞`、`进行中`、`未开始` 要求任务头不标完成，未勾选复选框不作约束（那正是「哪些验收项没达成」的记录）。任务头标记整体缺失时跳过标记比对，复选框判定不受影响。

区域内重复声明 `- 状态：` 一律报错：`field()` 用 `re.search` 只读第一行，重复声明在 `field_errors` 里是静默的，若也在此跳过，`- 状态：完成` 配 `- 状态：阻塞` 就能整体过门。

两个消费点：`lint_task_deps.py --state-consistency` 只读 `tasks.md`，在归档移动前作前置检查；`check_delivery.py` 的任务终态门内联同一判定作兜底。一致性不并入 `field_errors`——执行期 `workflow_control.py` 只写状态字段、不动复选框，若并入 plan 阶段字段校验，执行中途重跑 lint 会对每个刚完成的任务报错。

门禁只判定不自动勾选：自动勾选会把「未验证」洗成「已验证」，比不一致更坏。复选框由执行方按真实完成情况勾选。

历史背景与残余风险见 `openspec/issues/incidents/2026-07-26-dual-task-status-bypass.md`。

## Verification

`verify.py` 总是计算 Spec Drift；代码发生变化时，必须存在相关规格类更新或显式的无需更新理由（`verify.py:144-246`）。配置驱动检查支持退出码、输出匹配和数量基线，并对以下配置漂移失败关闭：

- 已有检查或 `ignore_paths` 被修改；只有本次实现产生且已试运行、带非空 `_note` 的新入口，才可追加显式 `baseline_aware: false` 检查并按绝对模式执行。
- 基线缺少 `ignore_paths` 快照、或新增检查不是显式 `baseline_aware: false`、缺少非空 `_note` 时失败关闭。
- 基线存在孤儿检查。

退出码语义为：`0` 表示 PASS，`1` 表示新增违规，`2` 表示工具或配置错误（`verify.py:750-895`）。长期知识来源晚于 `source_ref` 时只输出 `WARN`，不改变总判定。

本仓库的 `verify.config.json` 运行全量 Pytest、测试数量不下降检查和 Skill 图 Lint。

Verification 基线、机器报告和 Run 级 Review JSON 统一位于仓库根 `.agentic-framework/verify/`，不纳入 Git。旧 `.verify/` 只作为迁移期读取来源；检测到旧产物时提示迁移，新版本不再写入、删除或覆盖旧产物。

## Scoped Delivery

Tooling 的 `check_delivery.py` 对 Git 默认要求工作区干净；纯 SVN 的预期本地改动按「本地已验证待提交」处理，不适用 Git clean。对存量残留场景，可显式启用 Scoped Delivery：Verify 在采基线时冻结任务可写路径和生成目录，并记录独立的 `workspace_residue_snapshot`（S0）；交付门仅在提交 Diff 位于该范围且当前 S1 残留与 S0 状态、路径和内容摘要一致时通过。

`changed_files_snapshot`、`--ignore` 和 `ignore_paths` 仅用于 Spec Drift，不构成交付豁免。Git Scoped Delivery 需声明当前 `HEAD` commit（产出 `git-scoped-delivery-pass`）；SVN Scoped Delivery 需声明已提交 revision（产出 `svn-revision-verified`，确切版本隔离核验通过）。范围冲突、快照不完整、残留变化或提交证据缺失均失败关闭，并要求改用干净 worktree／工作副本。Scoped Delivery 仅用于 Native Delivery；框架自身 `.agentic-framework/` 本地运行产物不作为 SVN 残留。Scoped 成功只能声明「本次交付范围干净，预存残留未变化」。Production 的 `validate_change.py` 不消费该模式，但其交付证据门与 Tooling 共享基线格式；SVN 证据必须提供确切 revision，待提交不构成正式交付。

## Code Review

共享 Review 入口按风险选择：

- `lightweight`、`standard`：调用 `comprehensive-reviewer`。
- `strict`：调用 5 个专项 Reviewer；存在 Finding 时再调用 `review-critic`。
- `lightweight`、`standard` 的 `comprehensive-reviewer` 可自证并生成 Review Artifact；被审方只能原样持久化，不得手写或改写 Artifact。
- Strict 最终 Judge 必须与实现主体独立，并生成最终 Artifact。
- 修复后只定向 Re-review，最多 10 轮；不得启动第二次全量首审。

Review 同时输出 Markdown 和与交付路径匹配的 JSON。机器门校验 `verdict`、P0/P1 数量、`scope`、`review_profile` 和轮次；它只能验证 Artifact 合同，不能把被审方手写的 JSON 变成可信 Review。OPSX 阶段门（`validate_change.py`）接受双格式 Review 报告：Envelope（裁决字段在 `payload` 内）或旧式扁平 JSON（裁决字段在顶层），按同一套字段校验，Envelope 额外要求顶层 `artifact_type` 为 `review-report`，顶层字段仅限 Run Envelope schema 定义的 13 个键（与 `payload` 同时携带裁决字段、`payload` 非 JSON 对象、或顶层携带该白名单外的未知字段，均拒绝）；Tooling Run 级报告仍必须是绑定 Run Context 的 Envelope（见 trust-model.md §6）。

## 信任边界

- JSON 证据防止只靠自由文本宣称 PASS，但不能证明判断本身正确。
- Verification 只运行配置中的命令，不推断未声明的生产环境行为。
- 长期 Specs 只辅助理解；活跃 Change、代码、测试和运行报告用于当前裁决。
- Production 与 Tooling 共享证据字段，不共享生命周期状态机。
