# Code Review 报告

## 审查范围

- **Spec**：N/A；仅提供源码文档契约。
- **Tasks**：`.agentic-framework/research/historical-review-strict-v1/r01/tasks.md`
- **Feature**：历史源码严格评测 r01。
- **Task**：冻结源码审查。
- **Review Profile**：strict
- **轮次**：首审（0）。
- **审查文件**：`r01/astropy/modeling/separable.py`，全部 317 行。
- **Scope**：run；仅绑定评测 Runtime，不是框架交付批准。

## 总体结论：NEEDS_CHANGES

P0：0；P1：1。完整报告保留所有 keep；submission 依 severity、file、line 排序取前 5 项，本次只有 1 项，无截断。

## Reviewer 意见汇总

- performance-reviewer：0 项正式发现，line 245 的跨维度线索归入 F-1。
- robustness-reviewer：1 项 P2 候选，归入 F-1。
- standards-reviewer：0 项发现。
- magical-prompt-reviewer：0 项正式发现、1 项源级 P2 候选，40 项义务已逐项分析；无父版本，未升级为变更缺陷。
- spec-compliance-reviewer：1 项 P2 候选，归入 F-1。

五位最终报告全部收齐后，才派 Critic。magical 在 Critic 期间再次运行仅为原样持久化已经提交的报告，不是继续审查。

## Critic 对抗性验证

F-1：`not_rebutted`。算术操作的保守语义不能推广到 `&`；自定义协议可绕过，但默认递归分支中不存在纠正。Critic 建议维持 P2，并明确具体 Shift 实现、树结构未提供。

## 裁决明细

- **F-1**［robustness／spec，原始 P2］→ Critic `not_rebutted` → **keep，P1**。
    - Judge 在 Critic 返回后独立读取全部源码。第 225–226 行接受坐标矩阵；第 240 行保留左矩阵，第 245 行覆盖右矩阵；第 307–309、316 行建立递归调用链；第 78–81 行给出独立输出矩阵契约。
    - 严重度调整依据：冻结 workflow 将 P2 定义为不影响正确性的建议，将 P1 定义为特定条件触发但风险明确的问题。这里返回错误依赖结果，不是建议，故 P1；没有扩大为 P0 的证据。
- magical C1 → **follow-up note**，源级证据并入 F-1；无 parent/history，不虚构 delta，不宣称其满足变更升级门槛。
- performance handoff → **follow-up note**，并入 F-1；不计性能 finding。
- **drop**：无。

## 正式问题

### P0（必须修复）

无。

### P1（应该修复）

#### P1-1：右侧嵌套并行模型走默认递归路径时，_cstack 用全 1 覆盖右依赖矩阵，误报独立输出相关且不可分离

- **维度**：健壮性、契约符合度。
- **位置**：`r01/astropy/modeling/separable.py:245`
- **问题**：当右子树的坐标矩阵含零元素且进入默认递归路径时，嵌入时被全 1 替换，已知独立性丢失。
- **独立证据**：对文档允许的坐标矩阵 `left=[[1]]`、`right=[[1,0],[0,1]]`，第 234 行计算 3 个输出，第 239–245 行创建并填充两个块，第 247 行得到 `[[1,0,0],[0,1,1],[0,1,1]]`，而不是三阶单位矩阵。
- **调用影响**：第 307–309、316 行将默认递归 `&` 子矩阵送入该函数；第 100–101 行公开额外的 True，第 60–62 行将后两个输出标为 False。
- **触发边界**：具体模型必须走第 304 行的 `NotImplemented` 回落路径；不声称任何指定 Shift 对象已经运行复现。
- **建议**：保留右矩阵元素，而不是标量填充；增加右侧嵌套独立模型测试。本评测不修改源码、不修复、不复审。

### P2（建议改进）

无。

## Follow-up Notes

- 缺少上游 Model／CompoundModel 实现、parent、diff、history，不判定引入时间、不作集成保证。
- Runtime commit 仅绑定评测工作树，不代表上游 checkout；本报告不是框架交付批准。
- Judge：`/root/strict_r01_judge`；材料准备者：`/root`，后者不是上游实现者。
- allowlist 为指令约束，不是硬隔离；精确模型版本、tokens、费用未知。
- 前两个 worker 因 Judge 额外施加的角色文本隔离顺序要求提前终止并重派。主编排后澄清：冻结角色同属公开 treatment 材料，不是答案。全部失败尝试及附加成本保留，不宣称在原计划总预算内。
- PowerShell 转义、GBK 输出及一次未设置指定环境变量的元数据读取偏差详见 `decisions.json`；未执行待审代码。
- 原始报告、失败尝试、全部候选、Critic 及实际 actor 路径保存在 `.agentic-framework/evaluation/historical-review-strict-raw-v1/r01/`。

