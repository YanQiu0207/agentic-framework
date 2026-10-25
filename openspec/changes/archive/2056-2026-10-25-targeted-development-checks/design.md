# 调整方案：开发反馈与正式验证分层

**状态**：已实施并归档；正式交付证据见验证与审查产物。

## 1. 范围与规则来源

仅修改以下 4 份执行指引；本 Change 文档为审批及实施记录，不是新的运行时规则来源。

| 文件 | 拟调整内容 |
| --- | --- |
| `skills/workflow-verification/SKILL.md` | 集中定义「开发定向检查」与「正式完整 Verify」；明确触发时机及证据效力，保留有配置／无配置分支。 |
| `skills/workflow-code-generation/SKILL.md` | 开发及修复循环先执行相关测试；完成实现并进入任务质量门、集成验证或最终 Review 前仍执行正式完整 Verify。 |
| `skills/workflow-code-generation/reference/delegated-execution-guide.md` | 子 Agent 内部迭代优先返回定向检查结果；提交任务质量门时提供完整验证证据，主编排方不得凭定向结果写入 quality_passed。 |
| `skills/workflow-code-generation/reference/delivery-guide.md` | 在正式完整 Verify 前增加快速结构检查及已知文档收口；保留后续 Review、知识同步、归档和交付门要求。 |

## 2. 两类检查的边界

### 开发定向检查

- 用于实现中、定位失败及修复后的快速反馈，不要求每次修改都调用完整 Verify。
- 手动选择已有相关 pytest 文件路径或用例 nodeid，不开发自动选择器。例如：`python -m pytest scripts/test_check_delivery.py`；用例级命令使用该文件中实际存在的 nodeid。
- 记录实际命令、退出码和必要输出；失败则继续修复或报告阻塞，不据此宣称正式验证通过。
- 不生成、覆盖或包装成局部正式 PASS 报告，不触发 quality_passed 或正式交付裁决。
- 其他技术栈使用项目已有相关测试命令，不强制所有项目采用 pytest。

### 正式完整 Verify

- 用于现有流程要求的任务质量门、合并前检查、集成验证及最终 Review 前验证。
- 完整执行适用配置和内置检查；无配置时沿用内置门禁及验证范围说明，不伪称项目全量测试已通过。
- 沿用现有基线、配置冻结、Spec Drift、Native／Runtime 报告、内容主体及失败处理合同。
- 定向测试通过不构成跳过正式完整 Verify 的理由；正式失败后可以先定向定位修复，但重新申请正式放行前仍须完整验证。

## 3. 交付前收口顺序

1. 完成实现及定向反馈，先运行低成本结构检查，例如 `git diff --check`；适用时检查 Skill 引用或任务状态一致性。
2. 核对修改范围，收口已知的 Change 文档、规格关联、知识影响说明及可提前完成的文档更新；未达成的验收不得提前勾选。
3. 按原流程执行正式完整 Verify、前端验证、最终 Review 和后续交付步骤。
4. Review 修复、知识同步、任务状态更新或归档等操作若改变受验证主体，仍按现有主体绑定合同重新完整验证。不得复用失效报告，也不调整指纹排除规则。

本次减少的是可避免的开发中途完整验证，不取消必要的任务级或交付级验证，不保证每次 Change 只跑一次完整 Verify。

## 4. 审批后实施与检查

- [x] 按上述范围精准修改 4 份指引。
- [x] 检查分类主定义及其引用，清理本次范围内相反或模糊的执行措辞。
- [x] 运行 `git diff --check`。
- [x] 运行 `python scripts/lint_skill_graph.py`，记录真实结果。
- [x] 核对 Diff 仅包含 4 份指引与本 Change 文档，禁改文件无变化。
- [x] 汇报检查范围及限制，不将快速静态检查冒充正式 Verify 或交付 PASS。

审批前只准备本 Change 文档。老板已追加正式交付要求，本轮按既有完整验证与交付合同执行全量 Verify、Review、归档、提交、合并推送及本地安装刷新。

## 5. 实施记录

- 四份指引已按方案修改，分类主定义位于 `skills/workflow-verification/SKILL.md`；其他入口引用并区分开发反馈和正式质量门。
- `git diff --check` 退出码为 0；`python scripts/lint_skill_graph.py` 退出码为 0，输出 `skills=30 commands=17 agents=8 | errors=0 warnings=0`。
- 禁改文件未修改；本次仅修改四份指引与本 Change 文档。
- 正式交付授权来源：老板本轮追加目标。基线从相同 HEAD 的独立干净 worktree `E:/github/aef-2056-baseline` 采集，未以改后内容重采。
- 首次基线命令因 Windows PATH 缺少 Git 的 `grep`／`true` 失败；补入 `C:/Program Files/Git/usr/bin` 后成功，不修改验证配置。
- 无长期 Spec Delta：此次仅修改执行指引，不改变机器门禁合同。分类约束在 Skill 主入口维护，不另建重复知识源。
- 沉淀检查：无不可逆架构决策；不新增自动选择器或局部 PASS 报告的取舍已记录于本设计第 2 节；正式验证红线保留在分类主定义。

## 6. 正式核验记录

- 已执行正式完整 Verify：`python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base ef57ed4821462c174819582dec90f1e0fc83f3bb`，退出码为 0，总判定为 PASS。
- 配置中的全量 pytest、测试定义数量不下降（762／762）与 Skill 图检查均通过；Spec Drift 为「无代码文件变更」。既有知识来源版本滞后为 WARN，未改写相关元数据。
- standard／integration 首审通过，P0／P1／P2 均为 0；审查方生成 `.agentic-framework/review/review-integration.md` 和 `.agentic-framework/review/review-integration.json`。
- 归档及本记录更新后，交付前重新核对主体；变化时重新完整 Verify 并定向复核，由审查方生成对应主体的报告。
- 本地安装注册表仅登记 `C:/Users/YanQi`，来源为主仓库；合并推送后通过安装器刷新，保留 Tooling Profile 与原有能力包选择。
