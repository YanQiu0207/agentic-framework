# Code Review 报告

## 审查范围

- **Spec**：`.agentic-framework/research/historical-review-strict-v1/r03/scope.md` 与源码接口契约。
- **Tasks**：`.agentic-framework/research/historical-review-strict-v1/r03/tasks.md`。
- **Feature**：r03 冻结源码评测。
- **Task**：任务 1。
- **Review Profile**：strict。
- **轮次**：首审（round 0）。
- **审查文件**：`r03/src/_pytest/logging.py`，仅来自允许的 `input.json.files`。
- **Scope**：run，`2050-strict-r03`。
- **Judge**：`/root/strict_r03_judge`，未参与实现。

## 总体结论: NEEDS_CHANGES

共 6 条原始源码候选，去重后 3 条，均 keep（P0：0，P1：3）。完整报告保留全部 keep；submission 按 severity、file、line 排序后最多取 5 条，本轮未截断。未修改上游代码、未进行复审。

## Reviewer 意见汇总

五位 reviewer 均采用 `fork_turns=none`，两槽分批，全部最终返回之后才去重；未互传候选。

| 角色 | 实际 Agent ID | 原始候选 | 原始报告 |
| --- | --- | --- | --- |
| performance | /root/strict_r03_judge/performance | 无 | raw-performance.md |
| robustness | /root/strict_r03_judge/robustness | R03_ROB_01、R03_ROB_02 | raw-robustness.md |
| standards | /root/strict_r03_judge/standards | 无 | raw-standards.md |
| magical | /root/strict_r03_judge/magical | MP-1、MP-2，源码级候选 | raw-magical.md |
| spec | /root/strict_r03_judge/spec | SPEC-1、SPEC-2 | raw-spec.md |

## Critic 对抗性验证

独立 Critic：`/root/strict_r03_judge/critic`，报告见 `raw-critic.md`。全部 3 项均为 `not_rebutted`，并非自动成立；Judge 在其返回后独立读取 44–90、286–380、418–489、510–585、672–713 行，检查配置分支、恢复路径、阶段存储与同步前提。

## 裁决明细

- **F-1** [R03_ROB_01 / SPEC-1 / MP-2 · P1] → Critic：`not_rebutted` → **keep**。
    - 裁决依据：435–437 同时修改 logger 与 handler 但只保存 logger；350–358 finalize 仅恢复 logger。525–529 与 676–684 证明 handler 跨测试复用，298–299 在 level=None 时不重置阈值；423–424 承诺测试结束恢复。
- **F-2** [R03_ROB_02 · P1] → Critic：`not_rebutted` → **keep**。
    - 裁决依据：72–84 将级别名写入模板，88–89 修改共享 style 后再格式化；526–529 两个 handler 共用 formatter，573–584 为可达配置路径。B 已进入 report 时 A 可进入 caplog，二者覆盖同一模板。基于标准 logging handler 独立锁语义的静态推导，未运行且未读取标准库实现；514–515 的安全共享注释不是同步保护。
- **F-3** [SPEC-2 / MP-1 · P1] → Critic：`not_rebutted` → **keep**。
    - 裁决依据：683 在阶段运行前保存列表引用；420 调用 reset，329 换新列表，325 将后续日志追加至新列表；379 仍返回旧列表。367–375 没有限定仅结束阶段，且 688–689 阶段结束未重新发布列表，因此即使视为历史查询也遗漏后续日志。

## 正式问题

### P0（必须修复）

无。

### P1（应该修复）

#### P1-1: 未配置日志级别时，caplog.set_level() 未恢复共享 handler 阈值，导致后续测试漏捕 WARNING

- **编号**：F-1。
- **维度**：robustness、spec、magical。
- **位置**：`r03/src/_pytest/logging.py:437`。
- **问题与证据**：435–437 同时修改 logger 与 handler 但只保存 logger；350–358 finalize 仅恢复 logger。525–529 与 676–684 证明 handler 跨测试复用，298–299 在 level=None 时不重置阈值；423–424 承诺测试结束恢复。
- **建议**：保存首次修改前的 handler 阈值并在 finalize 恢复。

#### P1-2: 启用彩色日志且并发记录不同级别时，两个 handler 共享可变格式模板，导致输出错误的级别名称

- **编号**：F-2。
- **维度**：robustness。
- **位置**：`r03/src/_pytest/logging.py:88`。
- **问题与证据**：72–84 将级别名写入模板，88–89 修改共享 style 后再格式化；526–529 两个 handler 共用 formatter，573–584 为可达配置路径。B 已进入 report 时 A 可进入 caplog，二者覆盖同一模板。基于标准 logging handler 独立锁语义的静态推导，未运行且未读取标准库实现；514–515 的安全共享注释不是同步保护。
- **建议**：避免 formatter 格式化时修改共享状态，或让两个 handler 使用独立 formatter。

#### P1-3: 同阶段调用 caplog.clear() 后替换列表却未更新阶段存储，导致 get_records() 返回旧记录并遗漏后续日志

- **编号**：F-3。
- **维度**：spec、magical。
- **位置**：`r03/src/_pytest/logging.py:420`。
- **问题与证据**：683 在阶段运行前保存列表引用；420 调用 reset，329 换新列表，325 将后续日志追加至新列表；379 仍返回旧列表。367–375 没有限定仅结束阶段，且 688–689 阶段结束未重新发布列表，因此即使视为历史查询也遗漏后续日志。
- **建议**：区分同阶段 clear 与阶段切换 reset，保持当前阶段 records 列表身份或正确重绑存储；不要无差别将阶段 reset 改为原地清空。

### P2（建议改进）

无。

## Follow-up Notes

无另列候选。

## 证据与声明边界

- 仅静态源码推导，未执行源码、测试、网络搜索或读取历史。没有 parent、diff、上游 checkout，不能声称问题由某次变更引入。
- magical 的 delta evidence-gating 无法满足；其源码级候选按本轮明确的完整源码 scope 裁决，不伪造 introduced 分类。该限制不影响另两位 reviewer 的同根因源码证据。
- F-2 依赖标准 logging 各 handler 独立锁这一外部语义；未读取标准库实现或复现，不声称每次并发必现。
- Runtime Envelope 从真实 run-context 复制 run_id、profile、harness、commit_sha、config_digest。commit 只绑定评测 worktree，不绑定上游源码 checkout。
- `implementer_actor=/root` 仅指评测准备者，不是上游作者；本报告不是框架实现或正式交付批准。
- 路径 allowlist 是执行约束，不是硬沙箱。准确模型版本、tokens、费用未知，usage 为 null。
- 源码检查调用：Judge 2 次（首个混合读取输出截断，裁决前按区间再次完整读取）；Critic 2 次，均不超过 12 次。Reviewer 总只读调用分别为 3、4、4、5、5 次，均不超过 12 次；持久化另计。
- 原始报告保存全部候选和限制，`decisions.json` 提供每条原始候选至最终决策的映射。实际 Agent 标识采用工具返回的 canonical task ID，未提供 UUID。
- 中文 Markdown 写入前已检查中英文与数字空格、全角中文标点及专有名词大小写；原始报告按原样保存。

