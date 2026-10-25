# Review 评测首例

这是离线评测管线，不是自动 Agent 执行器。实现入口为 `scripts/agent_eval.py`，不执行待审代码，不调用模型、Docker 或 Comet。

真实 Agent 的历史 Bug 试点见 [Django、pytest、scikit-learn 与 Astropy 对照报告](historical-pilot/README.md)。下方合成案例只用于验证框架合同，两者不可混作效果证据。

## 实验步骤

在仓库根目录使用 PowerShell：

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
python scripts/agent_eval.py plan evaluation/review/experiment.json .agentic-framework/evaluation/review-demo
python scripts/agent_eval.py export .agentic-framework/evaluation/review-demo checkout--CONTROL--1 control-input.json
python scripts/agent_eval.py export .agentic-framework/evaluation/review-demo checkout--KNOWLEDGE--1 knowledge-input.json
```

`plan` 冻结全部文本、私有预期问题、分组、执行条件和重复矩阵。只向被测 Agent 提供 `export` 的文件，不提供原仓库、实验定义或运行目录。`CONTROL` 没有额外知识；`KNOWLEDGE` 包含业务规则、架构踩坑和编码规范。两组的任务和私有验收相同。

**安全边界**：导出白名单不是文件系统沙箱。人工运行须另行隔离祖先 `AGENTS.md`、全局知识、HOME、会话历史和检索源；本工具不能证明这些条件成立。计划、导入结果及裁定文件应只交给可信评测操作员。

提交 JSON 示例（摘要从导出文件复制）：

```json
{
    "plan_digest": "<export.plan_digest>",
    "cell_id": "checkout--CONTROL--1",
    "execution_digest": "<export.execution_digest>",
    "status": "completed",
    "findings": [
        {"id": "f1", "title": "客户邮箱被写入标准输出", "file": "public/checkout.py", "line": 8, "severity": "P2"}
    ],
    "provenance": {"producer": "实际模型与宿主版本", "session": "独立会话标识", "isolation": "实际隔离方式或明确未知"},
    "usage": {"tokens": null, "cost_usd": null}
}
```

```powershell
python scripts/agent_eval.py import .agentic-framework/evaluation/review-demo submission.json
```

导入返回 `submission_digest`。执行状态还允许 `error`、`timeout`、`cancelled`，此时 findings 必须为空。未导入的单元为 `missing`，已完成但未裁定为 `pending`，均不冒充零分或成功。来源和执行条件仅是声明。

由未参与被测 Review 的外部裁定者阅读私有期望与实际 finding，提供裁定 JSON。裁定可来自人工或 AI，`reviewer` 必须如实声明来源及身份；AI 初评不等于人工复核。本工具只导入裁定，不调用 Judge，也不验证裁定者身份或独立性：

```json
{
    "plan_digest": "<export.plan_digest>",
    "cell_id": "checkout--CONTROL--1",
    "submission_digest": "<import.submission_digest>",
    "reviewer": "实际裁定来源（人工或 AI）与身份标识",
    "decisions": {"f1": "logging"}
}
```

`decisions` 必须覆盖每条 finding；值为预期问题 ID，误报为 `null`。同一预期只能匹配一条 finding，重复报告不得重复计分，应合并判断或将重复项裁定为误报。没有 findings 时仍需导入空 decisions，表明外部裁定已提交，不代表完成了人工复核。工具不验证裁定者身份或独立性，不用关键词和行号重合推断语义匹配。

**清单外问题**：期望清单不代表现实中的全部缺陷。发现清单外真实问题或裁定有争议时，不强制标误报，应保持该单元 `pending`，人工修订数据集并建立新计划重评。已导入记录不可覆盖，不能通过补跑挑选最好成绩；补跑必须预先定义新实验。

```powershell
python scripts/agent_eval.py adjudicate .agentic-framework/evaluation/review-demo adjudication.json
python scripts/agent_eval.py report .agentic-framework/evaluation/review-demo
```

## 指标与解释

- 每单元分别报告检出、漏报、误报、recall、precision、匹配项的严重度准确率，以及三类知识的检出和 recall。
- 无预期缺陷的任务 recall 为 `null`；无 findings 时 precision 为 `null`；没有匹配项时严重度准确率为 `null`。
- 配对按任务和重复编号关联全部分组，缺失或未裁定的配对不称完整。报告不以成功样本替代预定矩阵。
- 每对以定义中第一个 Treatment 为参照，报告其余组减参照组的指标差值；任一值不可得时差值为 `null`，不自动做显著性或因果判断。
- 费用未知为 `null`；已知费用小计和覆盖率同时报告，不把部分小计说成实验总成本。
- `report` 成功退出只表示报告生成成功，不代表所有单元已评分或模型达标。CLI 主结果为 JSON；失败返回非零，中断返回 130。

该示例的知识包同时包含三类知识。按类别的结果不等于三类知识各自的因果贡献；要做消融须在新定义中分别建立知识子集 Treatment，并保持其他执行条件一致。模型、工具、预算及会话条件未受本工具强制执行；只能在可信外部执行证据支持同条件时解释知识净效应。

`checkout` 的私有预期包含知识依赖规则，而 `CONTROL` 未获得这些规则；该任务测量上下文可得性对识别团队违约的影响，不等同一般缺陷检测能力。`clean` 是知识无关对照。公开导出中的 `response_contract` 给出 JSON 输出合同，不含私有期望。

本例包含一个有缺陷任务与一个知识无关、无预期缺陷任务，仅验证评测合同，不证明真实模型或团队知识的收益。摘要用于检测意外变更，不防范有权重写全部本地证据的恶意操作员。输出和快照可能包含敏感代码与知识，应仅存于受控本地目录。
