# 历史 Bug 的 strict 补测结果

## 结论

2026-10-25，原四个经典案例均完成五维 reviewer → Critic → 独立 Judge 的实际执行。随后，另一个未参与审核的 AI 对三组共 12 份匿名最终输出、27 条 finding 重新盲评。

**普通组、standard 阶段与 strict 均命中 3/4 个预注册目标；本轮没有观察到 strict 的目标检出增益**。这不是技能无效或统计等效证明，也不是对团队知识效果的验证。

| 案例与固定上游目标 | 普通组 | standard 阶段 | strict |
| --- | --- | --- | --- |
| [Astropy #12907](https://github.com/astropy/astropy/pull/12907)：右侧嵌套依赖矩阵被覆盖 | 命中 | 命中 | 命中 |
| [Django #10554](https://github.com/django/django/pull/10554)：组合投影查询缺少排序列 | 漏报 | 漏报 | 漏报 |
| [pytest #7571](https://github.com/pytest-dev/pytest/pull/7571)：handler 日志级别跨测试泄漏 | 命中 | 命中 | 命中 |
| [scikit-learn #13142](https://github.com/scikit-learn/scikit-learn/pull/13142)：标签与最终最优模型不一致 | 命中 | 命中 | 命中 |

来源：[恢复组别后的统计](strict-comparison.json)、[独立逐项盲评](strict-adjudication.json)、[原始来源及 commit](sources.json)。上游修复和回归测试仅用于静态核验，本次没有本地执行这些历史测试。

## 输出数量不是效果分数

| 观察项 | 普通组 | standard 阶段 | strict |
| --- | --- | --- | --- |
| 最终 finding 数 | 9 | 10 | 8 |
| 目标匹配 | 3 | 3 | 3 |
| 静态支持的清单外发现 | 6 | 7 | 5 |

盲评未将任何一条判为明确错误或证据不足，但这**不意味着 precision 为 100%**。清单外发现没有上游确认或执行验证，且不存在经过核验的无缺陷对照集。公开 API 可达性、依赖锁语义和文档解释等限制逐项保留，不能把 `supported_extra` 改名为已验证真阳性。

strict 在 pytest 中新增了共享可变 formatter 的并发线索，但在 Django 中提出的问题少于旧组；更多或更少的条数都不能直接解释为更好。Django 的其他集合、排序或空查询问题与冻结目标不同，不能因为同文件或位置相近就算命中。

## strict 流程到底贡献了什么

| 案例 | 进入 Critic 的去重候选 | 最终 keep | 转 follow-up | 目标在候选／最终阶段 |
| --- | --- | --- | --- | --- |
| r01 | 1 | 1 | 0 | 命中／命中 |
| r02 | 2 | 2 | 0 | 未命中／未命中 |
| r03 | 3 | 3 | 0 | 命中／命中 |
| r04 | 3 | 2 | 1 | 命中／命中 |

来源：各 `strict-r01/` 至 `strict-r04/` 的 `decisions.json`、原始 reviewer 和 Critic 报告。候选阶段目标对应关系是基于原始主张与独立最终盲评的流程回溯，不是另一轮独立盲评或独立样本。

- Critic 对 9 项均给出 `not_rebutted`，没有提供可用于证明「降低误报」的驳回样本。
- r04 的 Judge 将「失败拟合后 warm-start 重试读取缺失状态」转为 follow-up，原因是恢复契约和外部调用证据不足；这不等于已经证实该候选为误报。
- 已发现的 3 个目标没有在过滤阶段丢失；不能据此证明一般情况下不会误删。
- 四案均调用全部角色，但 `magical-prompt-reviewer` 要求的历史 delta 证据在本实验中不可得。它们保留源级线索、明确未完成变更归因。因此只证明此 **source-review 条件下的编排链执行**，不是完整 PR 差异证明能力已经验证。
- r03 报告的「6 条原始源码候选」包含 magical 的 2 条未通过 delta 升级条件的源级线索；不要将其误读为 6 条均通过角色门槛的正式 finding。两个相关问题同时由其他角色独立提出。

## 预算与协议偏差

本轮 strict 使用 4 位 Judge、20 位完成审核的 reviewer、4 位 Critic；另有 r01 两次提前终止尝试，共 30 次被测 Agent 执行。旧普通组为 4 次，standard 组为 8 次。**这不是等计算预算实验**；角色数也不等于 token 用量。

r01 的额外尝试源于 Judge 临时施加了协议没有要求的角色文本隔离，随后已纠正。失败原文、真实 Agent 标识及额外成本不可观测的限制全部保留，不删除失败再报告「一次成功」。精确模型版本、token 与费用未知，费用为 null。

输入验证确认四案源码和需求与旧普通组一致，Run Envelope 绑定真实初始化上下文，四份提交均通过 CLI 导入。记录见 [证据验证](strict-evidence-validation.json)、[冻结协议](strict-protocol.md)、[材料哈希及重建说明](strict-provenance.json)。白名单仍是提示约束，不是硬隔离；Runtime commit 绑定评测工作树，不是上游完整 checkout。

## 对评测框架的验证

实际走通了 `plan → export → import → adjudicate → report`，不是仅把预制预期输出喂给单元测试。

- 四份 strict 提交均导入成功，缺失数为 0。
- r01 的唯一 finding 可以完整裁定，得到 1 个 scored 单元。
- 其余三案包含清单外发现，封闭答案集不能安全映射为误报，继续保持 3 个 pending；见 [实际框架报告](strict-framework-report.json)。
- 3/4 目标命中率来自补充的逐指标统计，不冒充框架已完成 4/4 全面评分。
- 框架专项测试重跑为 43 passed、1 skipped；它只验证工具功能，不证明审核效果。
- 收尾时连同两项旧测试所在套件重跑：`python -m pytest scripts/test_agent_eval.py scripts/test_knowledge_management_e2e.py scripts/test_workflow_control.py -q -rs`，结果为 142 passed、2 skipped。两项跳过均因 Windows 缺少符号链接创建权限，不视为实际符号链接路径验证通过。

归档自检确认 42 份原始报告／裁决／提交与运行目录字节一致，本地 Markdown 链接有效，三组统计与 27 条逐项裁定一致；见 [归档核验](strict-handoff-audit.json)。部分 PowerShell 生成的原始 JSON 含 UTF-8 BOM，自检按 `utf-8-sig` 读取，原件不改写；正式 submission 已由框架原有解析器实际导入。`git diff --check` 对原始报告末尾空行给出提示，未为消除提示而改写审核证据。

未修改生产评分逻辑以强行得到完整分数，未增加自动模型调用或自动裁判。已有 Runtime 重试／交付重跑问题仍单独记录，未因此篡改旧 Run，也未把本次上游源码审查报告当作框架交付放行证明。

## 后续应优先做什么

1. 使用真实 PR diff 与完整调用上下文，让 delta 角色的证据门槛可实际满足；这与继续重复扫描完整旧模块是不同实验。
2. 增加「普通多次审核＋聚合」近似计算量对照、重复试验和核验过的负例，才能进一步讨论分工收益和误报。
3. 对清单外发现提供开放分类及分指标裁定覆盖率，避免答案集不完备导致整单元长期 pending。
4. 团队知识实验复用当前 Task／Treatment／Experiment：固定审核流程、模型与预算，仅改变无知识、相关知识、无关知识；本轮技能包实验不能替代它。

以上是后续建议，不是本轮已经执行的实验。公开经典 Bug 可能存在训练污染；未做人工校准、真实上游回归或完整仓库审核，不推广为生产效果或成本收益结论。
