# 框架对比（来源二）：文章实践 × 本框架现状

> 对照对象：[04-source2-summary.md](04-source2-summary.md) 与本框架 agentic-engineering-framework 的当前实现。
> 证据以 `file:line` 标注，可直接跳转核对。本轮分析发生在来源一的 gap 1（客观门禁脚本）已经实现之后——`skills/workflow-verification/` 已落地，不在本轮候选范围内。

## 1. 主对照表

| 文章机制 | 本框架状态 | 证据 |
| --- | --- | --- |
| Repo-as-truth（仓库即现实） | ✅ 已有，等价物更强 | 代码是当前实现事实源 + 长期 Specs 辅助（`docs/framework-features-status-and-comparison.md:59-69`） |
| JSON 物理锁防虚标完成 | ✅ 等价物 | `validate_change.py` 三阶段确定性校验 + Verify 硬门禁（`docs/framework-features-status-and-comparison.md:128-136`） |
| Generator-Evaluator 对抗 | ✅ 等价物，更强 | 五维 Reviewer + 独立 Critic + Judge（`skills/workflow-code-review/SKILL.md:14-57`） |
| Sprint Contract（先谈验收标准） | ✅ 等价物 | Plan 门禁阶段的 Spec/Tasks 验收标准先于实现冻结（`docs/framework-features-status-and-comparison.md:130-134`） |
| 并发写入规避（worktree/DAG） | ✅ 已有，规避思路不同 | Tooling DAG 分波 + 高风险 Task 独立 worktree（`docs/framework-features-status-and-comparison.md:90-96`） |
| 组件生命周期治理（加了之后学会拆） | 🟡 已识别但未落地 | 框架自认 Tier 2 A/B 评测「未形成稳定基线」（`docs/framework-features-status-and-comparison.md:352`） |
| 验证防篡改（物理只读沙盒） | 🟡 只有行为约定，无物理层保证 | `skills/workflow-verification/SKILL.md:100`：「代码任务实现期间冻结」是对 Agent 的指令，非文件系统权限 |
| 大规模并发调试的二分定位方法论 | ❌ 缺 | `skills/troubleshooting/SKILL.md` 无对应场景（已检索确认） |
| Team Mode（常驻队友） | ➖ 有意不做 | 见第 3 节，属设计取舍 |
| KAIROS（主动判断该不该做） | ➖ 场景不适用 | 框架是一次性开发会话驱动，非常驻助手 |
| Hooks（开放插槽平台） | 🟡 部分等价 | `verify.config.json` 是项目可插拔检查点，但只在验证阶段一个节点，非贯穿流水线 8 个节点 |

## 2. 真正值得补的 gap（按价值排序）

### gap 1：验证防篡改是「约定」而非「物理只读」

`skills/workflow-verification/SKILL.md:60,100` 规定 `verify.config.json` 「代码任务全程只读配置」「实现期间冻结，验证失败后不得重采基线」——但这是**对 Agent 的行为指令**，没有文件系统层面的只读权限或独立签名校验。

文章第三层的关键洞察：光靠约定，模型在交不出成果时会直接篡改判分标准本身（把 `assert x==5` 改成 `assert True`）。框架的 `count` 类检查（`skills/workflow-verification/scripts/verify.py:295-369`）能抓「测试数量异常减少」，但抓不住「断言被弱化但数量不变」——比如把严格相等断言改成永真断言、放宽阈值比较等语义弱化，这类改动完全不影响行数或数量统计。

**当前防线**：这类篡改如果发生在被 Review 的 diff 里，理论上会被 Reviewer 的语义审查捕捉——但这是「可能被发现」而非「结构性无法发生」，与文章要求的物理隔离在保证强度上不同级。

### gap 2：Tier 2（A/B 效果评测）缺的是方法论，文章给了可抄的协议

`docs/framework-features-status-and-comparison.md:352` 已自认「高风险机制的 A/B 效果评测，未形成稳定基线」；`:519` 也提到「扩大 Telemetry 样本，再决定是否建设 Hooks 或预算门」。文章给的协议具体可落地：**每次新模型发布，先用老 Harness 跑一遍，再拆一个组件跑一遍，看数据说话**，用 feature flag 支撑受控对比。

框架现在默认「五维 Review、Critic 轮次、worktree 隔离」永远必需，但从未系统验证过——随着宿主模型（Claude Code / Codex）持续变强，这些维度里是否已有部分变成 overhead 尚无数据支撑。已有 Telemetry Pack（`docs/framework-features-status-and-comparison.md:246-266`）具备 Token、重试、人工介入等字段，具备做这类受控对比的数据基础，只是从未组织过「关闭某维度做对比」的实验。

### gap 3：并行任务集成失败缺一套二分定位的排障方法论

框架靠 worktree 隔离 + DAG 依赖顺序在**设计时**规避并发写冲突（`docs/framework-features-status-and-comparison.md:90-96`），但没有覆盖「多个并行分支合并后集成失败，如何定位是哪个分支引入的」这一实际会发生的场景。`skills/troubleshooting/SKILL.md` 目前无对应排障套路。

文章里 Anthropic 用 GCC 标准答案做二分查找，从 16 个并行 Claude 写崩的 C 编译器里精确定位问题文件——这套「用已知良好基线做二分排除」的方法论具备通用性，可以直接搬到「N 个并行 worktree 合并后集成失败」场景。

## 3. 不建议盲目补的（是设计取舍，不是缺陷）

- **Team Mode（常驻队友，独立上下文 + 点对点通信）**：会显著推高 Token 成本（每个队友维护独立上下文），且侵蚀框架「Workflow Skill 驱动 + 评审才并行 subagent」的省 token 设计（`02-gap-analysis.md:56`同类结论）。框架当前的按需 dispatch 已是更经济的等价物。
- **KAIROS（常驻后台主动判断）**：框架是一次性开发会话驱动，不是常驻助手产品，没有「该不该主动打断用户」的场景。
- **Hooks 全流水线开放插槽**：会侵蚀框架当前「阶段固定、`verify.config.json` 是唯一可插拔点」的简洁性；`verify.config.json` 已提供项目自定义检查的等价能力，没有证据表明需要扩展到 8 个节点。

## 4. 与来源一 gap 分析的衔接

来源一（`02-gap-analysis.md`）识别的最大缺口——客观门禁脚本 + 基线对比——已经实现（`skills/workflow-verification/`）。本轮三个 gap 与来源一没有重叠，是增量发现。
