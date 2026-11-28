---
name: workflow-system-design
description: 系统设计。当 proposal.md 的需求章节已完整，需要建立或完善 design.md 时调用。AI 调研代码后给出推荐方案，产出便于用户快速判断的设计文档；方案经用户确认后才算批准。
---

> 输出一行：`Using workflow-system-design`

# 系统设计

设计前加载 [project-knowledge](../project-knowledge/SKILL.md)，按 §3.1～§3.2 定向读取相关知识，按 §3.5 输出读取回执并在设计结果中说明采用依据。涉及领域语义时按其 §3.4 读取共享模型；需要改变领域模型时加载 `bp-domain-modeling`，按同一知识合同记录。

## 目标

产出一份让用户约 10 分钟内看懂方案、判断是否合理的 `design.md`。本技能只规定交付物和底线，不规定分析方法；调研和设计用 AI 判断最合适的方式完成。

## 前置条件

- `proposal.md` 已存在且背景、目标、需求和验收标准完整；不完整时停止，切换到 `workflow-requirements-clarification`。
- 开始设计前运行 `python <workflow-code-generation 目录>/scripts/lint_spec.py <proposal.md> --phase design`；退出码非 0 视为不完整，按上一条处理。
- `design.md` 不存在时，从 [reference/design_template.md](reference/design_template.md) 复制创建；旧 `spec.md` 只允许迁移读取，不作为新写入目标。
- **章节号约定**：design.md 保留历史局部编号 4～9，可与 proposal.md 的编号重叠，不重新编号。跨文件引用必须带文件名，例如「design.md §4.1」。

## 交付物

按模板写，每节只写本需求涉及的内容；不适用的节写 `N/A - 本需求不适用` 加一句原因。

| 章节 | 回答用户的问题 |
| --- | --- |
| §4.1 方案概览 | 要做什么、改哪里、规模多大，前提依据是什么 |
| §4.2 关键决定 | 为什么这样做，放弃了什么，代价是什么 |
| §4.3 对外行为 | 调用方和用户会看到什么变化：正常、边界、错误、兼容 |
| §4.4 实现要点 | 实现者还需要知道的模块职责、接口、数据和关键流程 |
| §5 假设与未决事项 | 哪些需要用户拍板 |
| §6 风险 | 哪里可能出错，怎么发现 |
| §7 验证方式 | 怎么证明做对了 |
| §8 发布与运维 | 上线、迁移、回滚和观测（适用时） |
| §9 参考资料 | 设计期引用来源 |

## 底线

1. **现状有证据**：关于现有代码的结论附 `file:line`。能从代码、配置或测试查到的事自己查，不问用户。
2. **只问用户才知道的事**：目标优先级、约束和偏好无法从需求或代码得出、且会改变方案时才问；其余写明假设后继续。
3. **假设单列**：需求没写、由 AI 推断的决定写进 §5，注明依据和影响的章节；未验证的外部依赖行为写明怎么确认。
4. **调研落盘**：调研摘要经用户确认后追加写入本 Change 的 `research.md`（按调研问题分节、保留 `file:line` 引用；多次调研追加新章节，不覆盖旧章节），design.md 只写摘要并引用对应章节。
5. **一个决定一个位置**：关键决定在 §4.2 完整写一次，其他位置引用。
6. **推荐不等于批准**：把方案和 §5 的待决项交给用户，确认后才写为已批准内容。用户提出的设计同样检查风险，不直接附和。实现与测试阶段复用已批准计划；契约冲突或范围变化返回受影响的设计决定，不把旧批准扩展到新行为。
7. **批准后定稿**：更新 §5 各项状态，删除「推荐」「待确认」等候选措辞，头部 `状态` 改为 `Approved`。

## 按需参考

需要时用以下规范自查，不要求逐项填写：`bp-architecture-design`（整体结构）、`bp-component-design` 及其 `reference/deep-modules.md`（模块、接口与测试接点）、`bp-distributed-systems`（网络、一致性、故障恢复）、`bp-performance-optimization`（性能）、`workflow-test-generation`（测试计划）。

## 设计完成后

用户批准并按底线第 7 条定稿后，宣布 design.md 已完成前运行 `python <workflow-code-generation 目录>/scripts/lint_spec.py <design.md> --phase design-code`；退出码非 0 时补齐对应章节（不适用标 `N/A - 本需求不适用`）后重跑，通过后再宣布完成。

**前端分支检查**：proposal.md 或 design.md 涉及前端 UI（新页面 / 新组件 / 用户操作路径 / `.tsx` 产物）时，进入编码前**先调用 `workflow-frontend-design`** 生成 `ui-spec.md`，再回到本流程。这与 `workflow-quick-design` 的前端分支对齐，避免到 `workflow-code-generation` 步骤 2 才因缺少 ui-spec 被动停下。

```
design.md 已完成。

你可以：
- 说"开始编码"进入 code generation 阶段（涉及前端 UI 时先走 /frontend-design 生成 ui-spec.md）
- 说"先写测试"进入 TDD 模式
- 如果某个 section 需要修改，告诉我具体哪个
```
