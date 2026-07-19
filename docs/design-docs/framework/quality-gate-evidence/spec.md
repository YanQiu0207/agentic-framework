# Tool/Service: 质量门证据校验（Verify/Review Evidence Gate）

**作者**：Claude Code（与用户对话确认）
**日期**：2026-07-19
**状态**：Archived

---

## 1. 问题与目标

### 问题

Tooling Profile 的 `workflow_control.py`（`quality_passed` 事件）与 Production Profile 的 `validate_change.py`（Task Review / Code Review 校验）当前都只信任**自由文本自述**来放行质量门：

- `workflow_control.py` 的 `quality_passed` 事件接受任意 `--reason` 字符串就允许状态迁移进入 merge，不校验 Review 或 Verify 是否真的发生过（`skills/workflow-code-generation/scripts/workflow_control.py:174-179,566-582`）。
- `validate_change.py` 的 OPSX038（`Task Review: PASS`）和 OPSX032（`Code Review: PASS`）只检查 `tasks.md` 里的一行文本标记，没有对应的真实报告文件佐证（`scripts/validate_change.py:27-35,1057-1081,1182-1204`）。

两者是同一类信任链漏洞：宿主 Agent 只要在文档里写一行 `PASS`，机器就无条件放行，无法察觉 Review 或 Verify 被跳过或谎报。

### 目标

- Tooling 的 Task 级 `quality_passed` 要求携带真实 `workflow-verification` 报告，校验其 `verdict == "PASS"`。
- Tooling 的 Run 级 `check_delivery.py` 要求携带真实 `workflow-code-review` 报告，校验其 `verdict == "PASS"` 且 P0/P1 计数为 0。
- `workflow-code-review` 的 Step 7 除现有 Markdown 报告外，额外产出结构化 `review-report.json`，作为上述校验的证据来源。
- Production 的 `validate_change.py` 在 OPSX038（Task 级）与 OPSX032（Code Review/集成级）同样要求 `tasks.md` 声明 `- Review Report: <path>` 字段，并校验对应文件。

### 非目标

- 不校验 Review 结论本身的语义正确性（Judge/Reviewer 主观判断错误不在本次范围内，这是 LLM 语义判断的固有边界）。
- 不改动 `validate_change.py` 里构建/测试执行记录（`_execution_record`，OPSX033/034）的自由文本校验——这是同类问题，但本次讨论未覆盖，留作后续可选项。
- 不新增独立 Runner 或 Workflow Engine，不新增 Skill。
- 不改变 Tooling「Task 级不跑 Review、Review 推迟到 Run 级」的既有架构决策（`docs/tooling/adr/003-review-fix-loop-convergence.md`）——`quality_passed` 只加 `--verify-report`，不加 `--review-report`。

### 验收标准

- `workflow_control.py event <id> quality_passed` 缺 `--verify-report`，或其指向文件缺失/非法 JSON/`verdict != "PASS"` → 非 0 退出，`tasks.md` 状态不写入。
- `check_delivery.py` 缺 `--review-report`，或其指向文件缺失/非法 JSON/`verdict != "PASS"`/`p0_count>0`/`p1_count>0` → 非 0 退出。
- `workflow-code-review` Step 7 输出模板新增 `.verify/review-report.json` 产出说明，字段与 Markdown 报告的总体结论一致。
- `validate_change.py` 在 `require_completed=True`（Delivery 阶段）时，Task 缺 `- Review Report: <path>` 字段或对应文件不满足 `verdict=="PASS" 且 P0/P1=0` → 报 OPSX038 finding；change 级 Code Review 同理报 OPSX032。
- 现有全部测试保持通过；新增测试覆盖每个改动点的「文件缺失／JSON 非法／verdict 不是 PASS／P0-P1>0」四类失败路径。

---

## 2. 设计方案

### 2.1 整体方案

把两个 Profile 现有的自由文本质量门统一改为「读取并校验结构化证据文件」，在各自已有的校验脚本上原地扩展参数/字段，不引入新服务、不改变现有 Task/Run 两级 Review 的架构分工。

### 2.2 核心组件

| 组件 | 职责 |
|------|------|
| `workflow_control.py`（Tooling task 级） | `quality_passed` 新增必填 `--verify-report <path>`，读取并校验 `verdict=="PASS"` |
| `workflow-code-review/SKILL.md` Step 7 | 输出契约扩展：Markdown 报告之外，额外写 `.verify/review-report.json` |
| `check_delivery.py`（Tooling run 级） | 新增必填 `--review-report <path>`，校验完整 schema、`scope=="run"`、`verdict=="PASS"` 且 `p0_count==p1_count==0` |
| `validate_change.py`（Production） | OPSX038（Task 级）与 OPSX032（集成级）新增校验 `tasks.md` 中 `- Review Report: <path>` 字段指向的仓库内文件，并分别要求 `scope=="task"` / `scope=="integration"` |

### 2.3 主要接口/API

- `python workflow_control.py <tasks.md> event <id> quality_passed --verify-report <path> [--reason ...] --write`
- `python check_delivery.py --tasks <tasks.md> --spec <spec.md> --review-report <path> [--repo <path>]`
- Fast-Path 交付（无 spec/tasks）同样必传 `--review-report`（Fast-Path Step 3 本就会跑一次 `workflow-code-review`）。
- `validate_change.py` 现有 CLI 不变，改动只落在其对 `tasks.md` 文本内容的解析规则上（新增字段读取，不新增命令行参数）。

### 2.4 数据模型

`review-report.json`（新，由 `workflow-code-review` Step 7 写出，路径由调用方决定，建议 `.verify/review-report.json`）：

```json
{
  "verdict": "PASS",
  "p0_count": 0,
  "p1_count": 0,
  "scope": "task | integration | run",
  "review_profile": "lightweight | standard | strict",
  "round": 0
}
```

- `verdict` 取值与现有 Markdown 报告「总体结论」字段一致（`PASS` / `NEEDS_CHANGES`）。
- `p0_count` / `p1_count` 统计「正式问题」区 P0/P1 数量（`follow-up` 与 P2 不计入）。
- `scope` 必须与消费门一致：Task 级为 `task`，Production 集成级为 `integration`，Tooling Run 级为 `run`。
- `review_profile` 只能是 `lightweight` / `standard` / `strict`。
- `round` 对应「轮次」字段：首审为 0，复审第 N 轮为 N。

`workflow-verification` 的 `.verify/report.json`（已存在，不新增字段，直接复用其 `verdict` 字段，见 `skills/workflow-verification/scripts/verify.py:776-783`）。

`tasks.md` 新增字段（仅 Production 需要）：`- Review Report: <path>`，与现有 `- Task Review: Pending|PASS`、变更头部 `Code Review: Pending|PASS` 配套出现。

### 2.5 关键权衡

- **堵什么，不堵什么**：这套改动堵住「跳过 Review/Verify 或忘了核对结论就直接宣布通过」这类流程性漏洞，并留下可审计的文件痕迹；堵不住 Reviewer/Judge 本身给出错误结论——语义正确性没有机器可验证的边界。
- **为什么 `review-report` 不挂在 `quality_passed` 上**：Tooling 故意把 Code Review 推迟到全部 Task 合并后才跑一次以收敛修复循环成本（ADR-003）；Task 级 `quality_passed` 触发时 Review 架构上还没跑，挂载会直接违反这条既有决策。因此 Review 证据门放在 Run 级 `check_delivery.py`。
- **破坏性变更**：新增必填参数/字段对现有正在跑的 change 有影响。落地前需确认仓库内当前没有其他活跃 Tooling/Production change 依赖旧 CLI 契约；若有，需要在对应 change 里同步升级调用方式。
- **范围边界**：`_execution_record`（构建/测试执行记录）的自由文本校验是同类问题，但本次讨论未覆盖，不在本次范围内，避免范围蔓延。
- **证据新鲜度边界**：当前 schema 不绑定 Task/change 标识、commit 或 diff hash，因此机器门禁不能证明报告与当前代码版本一一对应。补充 provenance/freshness 字段会改变生产者和所有消费者合同，留作独立后续设计，不在本次已批准范围内扩张。

---

## 3. 运维

不适用——本次改动是本地校验脚本的参数/字段扩展，不涉及部署、监控或告警。

---

## 4. 参考资料

- `skills/workflow-code-generation/scripts/workflow_control.py:174-179,566-582`
- `skills/workflow-code-generation/scripts/check_delivery.py`
- `skills/workflow-code-review/SKILL.md:221-268`
- `skills/workflow-verification/scripts/verify.py:776-793`
- `scripts/validate_change.py:27-35,1041-1081,1182-1204`
- `docs/tooling/adr/003-review-fix-loop-convergence.md`
- `skills/workflow-code-generation/reference/delegated-execution-guide.md`
