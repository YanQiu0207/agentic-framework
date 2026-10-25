# Agent 实验评测：Review 首例

## 定位

本次设计把实验管理与场景评分分开。通用层冻结任务、实验组与重复矩阵，保存输入、提交和裁定证据；首个评分场景为代码 Review。实现入口为 `scripts/agent_eval.py`，测试为 `scripts/test_agent_eval.py`，使用说明与合成案例位于 `evaluation/review/README.md`。

**证据状态**：首版代码与离线专项测试已落地；最终全量验证与审核以本次 Change 的证据为准。已完成四个真实历史 Bug 的普通组、standard 阶段及 strict 实验，详见下文。原「未运行真实模型实验」是首版离线阶段状态，已被实际运行证据更新；模型具体版本及费用仍不可观测。

## 使用入口

依次执行 `plan`、`export`、`import`、`adjudicate`、`report`，完整 JSON 格式与 PowerShell 命令见 `evaluation/review/README.md`。`plan` 接收实验定义和新建运行目录；`export` 接收单元 ID 并输出被测输入；`import` 导入实际 Review 结果；`adjudicate` 导入外部裁定；`report` 输出全部单元和同任务、同重复编号的分组差值。

首版实验定义为 `evaluation/review/experiment.json`，含 2 个任务、2 个分组与 2 次重复，共 8 个单元。`checkout` 覆盖三类团队约束，`clean` 是无预期缺陷的知识无关对照。此设计测量上下文可得性，不将 CONTROL 缺少团队规则时的漏报泛化为一般代码审查能力差。

## 实验与评分边界

- Task 的公开要求和待审代码与私有预期问题分离，导出采用白名单。将整个定义直接交给被测 Agent 会泄漏答案。
- Treatment 表示受控变化，例如团队知识、提示词或模型。比较知识效果时，其他条件应固定；同时改变模型与知识不能归因为知识收益。
- Experiment 固定任务、分组和重复次数，缺失、执行失败和未裁定记录都必须展示，不只报告成功样本。
- 模型输出的问题由外部裁定映射到私有预期问题，不能靠行号重合、关键词或声明信号确定语义正确性。裁定需绑定具体计划和提交；来源可为人工或 AI，必须在 `reviewer` 中如实声明，AI 初评不等于人工复核。
- 检出率、精确率及严重度判断分开计算；重复发现不重复增加检出，零分母和未知费用为 null。
- 导入模式不能证明模型实际配置、无历史会话污染或裁定者独立身份。材料摘要用于检测变更，不是对失陷宿主的防篡改承诺。

首版不调用模型、不执行提交代码、不启动容器、不引入自动 Judge。工具只导入外部裁定，不验证裁定者身份或独立性，裁定质量仍需复核；私有预期清单若不完整，不能将清单外的真实问题武断判为误报，应保持 pending，修订数据集并开启新实验。

## 团队知识实验如何复用

### 对 Review 的影响

同一任务分别运行 CONTROL 与 KNOWLEDGE，知识材料按业务规则、架构踩坑和编码规范分类。先比较「无知识／完整知识」，需要辨别各类贡献时再做分类消融，避免将任务类别差异误当成知识贡献。

待审代码、预期问题、重复编号、工具和预算应保持一致；被测会话不能访问私有验收与另一组会话。独立 worktree 不等于安全隔离，首版只提供输入协议，不证明外部宿主满足这些要求。

### 对代码生成的影响

复用任务快照、分组、矩阵、来源和报告机制；新增代码产物合同、隔离执行器及测试验收。Review 的外部问题匹配不能充当代码正确性测试，首版没有这一能力。

## 与原有工具的关系

`scripts/evaluation_runner.py` 的行为合同检查、`scripts/benchmark_runner.py` 的历史执行汇总与本实验层用途不同。本次不替换它们，也不改变 `scripts/codex_adapter.py` 或 `scripts/claude_code_adapter.py` 的探测协议。不能把原有探测声明称为真实模型实验。

## 真实历史 Bug 试点

2026-10-25 已运行 4 个成熟仓库历史案例、2 个分组，共 8 次真实审查。普通组和技能 standard 阶段各命中 3/4 个官方目标，没有在该小样本上观察到目标检出增益；这不是统计上的等效或无效证明。结果为独立 AI 静态初评，未由人工复核、未本地执行上游回归测试。

详见 [历史试点报告](../../../../../evaluation/review/historical-pilot/README.md) 及其冻结源码 URL、摘要、原始输出和逐项裁定。真实任务产生了预期清单外的问题：当前框架只为 3 个单元完成封闭清单评分，另外 5 个保留 pending；补充目标检出统计不能冒充 8/8 完整评分。r01 技能组的 strict 升档未执行，不能宣称完整治理流程全部完成。

**后续 strict 补测**：四案现均完成全部五维 reviewer、有候选时 Critic、独立 Judge；另一个 AI 对三组 12 份最终输出盲评，三组仍各命中 3/4 个目标，Django 目标均漏报。strict 的 8 条最终 finding 中 3 条匹配目标、5 条为静态支持的额外发现；封闭评分为 1 scored、3 pending，未把额外发现强行判为误报。四案缺少父版本／diff，因此不能声称契约角色的完整 delta 证明已验证。详见 [strict 结果与流程证据](../../../../../evaluation/review/historical-pilot/strict-results.md)。旧试点及其未升档记录保留，后续补测不追溯改写历史。

## Comet 方法参考来源

仅借鉴实验方法，不依赖或集成 Comet。源码研究固定于提交 `aeb1a6598034e28ce46b8422d4dbd8785e607bd7`：

- [aligned_comparison.py](https://github.com/rpamis/comet/blob/aeb1a6598034e28ce46b8422d4dbd8785e607bd7/eval/scaffold/python/aligned_comparison.py)：参考 `build_case_manifest` 的条件指纹、`align_records` 的任务与重复编号配对；公开条件和 Treatment 指纹分别比较。
- [test_tasks.py](https://github.com/rpamis/comet/blob/aeb1a6598034e28ce46b8422d4dbd8785e607bd7/eval/local/tests/tasks/test_tasks.py)：参考真实输出与逐例验证结果留存，而非只保存总分。
- [pass_at_k.py](https://github.com/rpamis/comet/blob/aeb1a6598034e28ce46b8422d4dbd8785e607bd7/eval/scaffold/python/pass_at_k.py)：不复制其中 `pass_pow_k` 口径，不将全样本通过标记解释为成功概率或统计下界。

合成案例只能证明框架能计算预定指标，不能证明真实团队知识有效。真实实验需要另行确定宿主、模型版本、预算、样本选择与裁定流程。
