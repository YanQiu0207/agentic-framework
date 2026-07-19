# 最小 Trust Model 长期候选

- **状态**：候选，等待 Run 级独立 Strict Review、知识同步和归档门收口
- **适用范围**：Production 与 Tooling 共用的机器运行证据协议
- **长期目标路径**：`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`
- **当前验证入口**：`scripts/runtime_trust.py`

## 1. 结论

第一版 Trust Model 只证明「受版本约束的证据存在，且 Schema、路径、摘要、Run 绑定、事件历史、Harness 探测和流程独立性声明相互一致」。它不证明 Reviewer 或 Judge 的语义结论必然正确，也不抵御已完全控制主机的攻击者。

## 2. 参与者与信任边界

| 参与者 | 可执行职责 | 不直接信任的自述 | 机器约束 |
| --- | --- | --- | --- |
| 用户 | 批准、拒绝、重试、取消或覆盖机器门 | 聊天中的口头覆盖 | 必须写入带非空理由的 `user-*` 事件 |
| 主 Agent | 编排 Run、收集 Artifact、触发最终门 | 「任务已完成」「Review 已通过」 | 必须提交 Manifest、Journal、Checkpoint 和质量 Artifact |
| 实现 Agent | 实现、测试、机器验证和修复 | 自己对质量和完成度的判断 | Strict 最终裁决不得由同一 actor 完成 |
| Reviewer | 发现候选 Finding | Finding 一定成立 | 输出结构化 Review Artifact，由独立 Judge 裁决 |
| Judge | 裁决 Finding 和 Run 结论 | 语义裁决必然正确 | Strict Run 报告声明实现者、Judge 和流程分离依据 |
| 确定性脚本 | 校验字段、摘要、路径、绑定、命令结果和状态迁移 | 未执行检查所覆盖的行为 | 只按版本化合同失败关闭 |
| Harness Adapter | 探测宿主能力、转换调用和工具结果 | 静态能力声明等于当前事实 | 每个 Run 使用可执行探测，必需能力缺失时停止 |
| 文件系统与 Git | 保存 Artifact、提交和合并事实 | 在恶意主机上仍可信 | 属于第一版可信计算基座 |

## 3. 可信计算基座

第一版信任以下基座未被完全攻破：

- 运行确定性脚本的 Python 解释器与操作系统进程边界；
- Run 目录所在文件系统、Git 对象库和工作区读取结果；
- 被执行的 Harness Adapter 与 `verify.config.json` 中命令；
- 当前仓库内受 Git 管理的 Schema、脚本和活跃 Change。

任一基座被完全控制时，攻击者可同时替换 Artifact、摘要、脚本与输出；本模型不声称能发现该类攻击。

## 4. 强制约束

### 4.1 证据而非 Agent 自述

最终 Trust Gate 先执行 Manifest 全量校验，确认关键 Artifact 存在、位于 Run 目录内、摘要匹配且未串 Run。自由文本、聊天记录和 Agent 自述不能替代 Artifact。

### 4.2 Strict Judge 独立性

Run 级 Review 必须满足：

- `scope: run`、`review_profile: strict`；
- `verdict: PASS` 且 `p0_count`、`p1_count` 均为 `0`；
- `implementer_actor` 与 `judge_actor` 均非空且不同；
- `independence_basis: process-separated-agent`。

这是可审计的流程分离声明，不是强身份隔离。实现者若能完全控制主机，仍可能伪造 actor 字段。

### 4.3 Harness 能力漂移

静态 Capability Matrix 只提供统一词汇，不作为运行事实。最终门只接受：

- `evidence_source: runtime-adapter-probe`；
- `run_id` 和 `harness` 与 Manifest 一致；
- 必需能力当前探测结果均为 `supported`；
- 可选能力降级已形成可观察证据。

### 4.4 事件、恢复和用户覆盖

恢复只使用 `events.jsonl`、最后 Checkpoint、Manifest、`tasks.md` 与 Git 事实。事件序号必须连续，外部副作用必须使用幂等键。所有 `user-*` 事件必须由 `user` actor 提供非空理由；覆盖不会删除原失败证据。

## 5. 威胁与残余风险

威胁用例及测试映射见 `evaluation/runtime-threat-cases.md`。这些控制可以发现伪造但缺少独立性声明的报告、被替换 Artifact、串 Run、重复副作用、运行时能力漂移和静默覆盖。

以下结论不可由第一版证明：

- Reviewer 或 Judge 的语义判断正确；
- actor 字段对应强认证的不同自然人或安全主体；
- 已完全控制主机的攻击者没有伪造文件、进程、Git 或命令输出；
- 未在 `verify.config.json`、行为用例或 Harness 探测中声明的行为正确。

## 6. 迁移说明

1. 旧 Review Artifact 仍可按 Schema 解析，但缺少 `scope: run` 或 actor 独立性声明时不能通过最终 Trust Gate。
2. 新的 Strict Run Review 同步填写 `implementer_actor`、`judge_actor` 和 `independence_basis`。旧 Artifact 不原地改写。
3. Harness 探测命令增加 `--run-id <run-id>`。无 Run 绑定的旧探测报告只作诊断信息，不能用于最终放行。
4. 每次 Run 把实际探测报告作为 `input_type: capability-matrix` 的快照登记到 Manifest，不能只引用仓库静态声明。
5. 归档前由主编排执行 Run 级独立 Strict Review；通过后把本候选同步到长期目标路径并更新相关索引，再归档 Change。

## 7. 当前收口状态

- Task 级实现与端到端威胁测试：由 Task 7 完成并提供机器验证证据。
- Run 级独立 Strict Review：等待主编排在 Tasks 2～7 合并后执行。
- 长期知识同步、Proposal 状态变更与 Change 归档：等待 Run 级 Review 通过后执行。
- 归档记录与最终交付门：本 Task 不生成，避免用实现者自审替代独立裁决。
