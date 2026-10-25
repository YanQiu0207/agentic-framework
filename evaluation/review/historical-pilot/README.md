# 大仓库历史 Bug：Review 技能试点

## 结论

2026-10-25 的单次试点中，普通审查与技能组的 standard 审查阶段均检出 **3/4** 个预注册官方目标 Bug。没有观察到目标检出数提升；样本太少，不能推断技能普遍无效或等效。

| 任务 | 仓库与上游修复 | 普通审查 | 技能阶段 |
| --- | --- | --- | --- |
| r01 | [Astropy #12907](https://github.com/astropy/astropy/pull/12907)：嵌套组合模型依赖矩阵丢失 | 命中 | 命中 |
| r02 | [Django #10554](https://github.com/django/django/pull/10554)：合并查询投影列与排序列不匹配 | 漏报 | 漏报 |
| r03 | [pytest #7571](https://github.com/pytest-dev/pytest/pull/7571)：日志 handler 级别跨测试泄漏 | 命中 | 命中 |
| r04 | [scikit-learn #13142](https://github.com/scikit-learn/scikit-learn/pull/13142)：多次初始化后的标签与最终模型不一致 | 命中 | 命中 |

以上为**隐藏组别后的独立 AI 静态初评**，不是人工验收或本地回归测试结果。裁定逐项引用源码行和上游补丁，见 `adjudication.json`、`target-assessment.json`。

## 实际执行了什么

- 4 个真实历史任务，每组每任务运行 1 次，共 8 份模型输出；不是合成预期输出。
- 取固定修复前 commit 的完整受影响模块：Astropy 1 个、Django 2 个、pytest 1 个、scikit-learn 1 个。不是整个仓库扫描，也不是原始缺陷引入 PR 的 diff 审查。
- 普通组由独立 Agent 直接审查；技能组由编排 Agent 加载实际 `workflow-code-review`，真实派发独立 `comprehensive-reviewer`，加载规定的编码规范，再原样转交结果及 6 字段 Artifact。
- 每个实际审查员最多 12 次只读工具调用、最多 5 条 finding；两组模型继承相同父级配置，但服务端精确模型版本不可观测。普通组 4 个审查 Agent，技能组 4 个编排 Agent 加 4 个审查 Agent，**总计算量不相等**。
- 被测 Agent 使用全新 `fork_turns=none` 会话，只提供白名单导出，不提供问题描述、修复补丁、答案或联网检索。文件访问限制是提示约束，不是系统级沙箱。
- 输出完成后移除组别与来源元数据、打乱顺序，交给另一个未参与被测审查的 AI 对 19 条 finding 逐一裁定。没有人工复核。

**流程限制**：r01 技能组提出需要升级 strict，但未执行升级。该输出只代表 standard 阶段发现；完整治理流程的 4/4 完成结论不成立。不能把「Using」字符串或最终 JSON 当作完整技能执行证明；本次另有真实子 Agent 派发与返回记录。

## 为什么不直接给 precision 总分

Django 两组、pytest 两组和 scikit-learn 技能组提出了官方目标之外的问题。独立 AI 初评认为这些额外问题有静态依据，但部分依赖未验证的入口条件或文档解释；不能直接当作已经证实的缺陷，更不能因为不在预期清单就记为误报。

当前框架采用封闭预期清单：只接受「匹配预期／误报」，且所有 finding 裁定完整后才计分。因此：

- 3 个单元完成外部裁定导入，5 个保留 `pending`，仅 1 个配对完整。
- `framework-report.json` 如实保留以上状态，不从已评分子集推导整场效果。
- 上表 3/4 是 `target-assessment.json` 对预注册目标的补充检出统计，不是框架已完成 8/8 全面评分。
- 不报告整体 precision、真实无缺陷误报率、成本收益或严重度优劣；没有无缺陷历史对照、完整答案清单、统一严重度校准和费用观测支持这些结论。

这次试点验证了缺失裁定的保守处理，也暴露了后续需要支持「已验证清单外问题／未确定问题」及按指标分别完成裁定，而不是强迫所有真实问题落入封闭答案集。

## 证据文件

| 文件 | 用途 |
| --- | --- |
| `experiment.json` | 冻结的任务、分组、预算声明与私有目标，不能交给被测 Agent |
| `sources.json` | 固定 commit 的源码 URL 与 SHA-256 |
| `provenance.json` | 数据集版本元数据、任务对应关系及技能材料摘要 |
| `observations.json` | 8 份实际模型输出，含真实 Agent 标识和来源限制 |
| `adjudication.json` | 去组别后的逐条 AI 初评 |
| `target-assessment.json` | 恢复组别后的官方目标检出结果，保留初评证据 |
| `framework-report.json` | 实际框架报告：3 scored、5 pending |

完整本地快照位于 `.agentic-framework/research/historical-review-pilot/`；运行记录位于 `.agentic-framework/evaluation/historical-review-pilot-v1/`。这两处不纳入 Git，不能作为唯一长期来源，故上表证据已另存于项目内。

### 重建输入

`experiment.json` 是需材料化的实验定义，不是免下载自包含数据集。按 `provenance.json` 的 r01～r04 对应关系，将 `sources.json` 的每个 URL 下载到定义旁的 `<任务 ID>/<原仓库路径>`，逐一校验 SHA-256；再按 `provenance.json.materials` 复制并校验框架技能材料。不要用当前上游分支替代固定 commit。之后运行 `agent_eval.py plan` 创建新目录，并仅将 `export` 结果交给被测 Agent。

源码来自各上游项目；本目录仅保存 URL、摘要与评测观察，没有重新发布上游完整源码。数据集参考为 [SWE-bench Verified](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified)，查询时版本标识见 `provenance.json`。上游 patch 与回归测试用于裁定依据，本次没有在本地安装这些历史项目或执行其测试。

## 可支持与不可支持的结论

可支持：这个固定小样本中，技能 standard 阶段未比普通审查多命中官方目标；真实大模块会产生清单外发现；r01 存在未完成的流程升级。

不可支持：技能无效、技能显著有效、真实成本更低、团队知识有效、完整 strict 流程已验证。公开历史 Bug 可能已进入模型训练数据，源码路径也可能触发记忆；禁止联网不能排除训练污染。

下一轮建议预注册更难的真实任务、加入修复后版本的定向负对照、增加重复次数、补完整调用上下文，并单独测标准阶段与完整治理流程。团队知识对照另设 Treatment，不与本轮技能包对照混为一谈。
