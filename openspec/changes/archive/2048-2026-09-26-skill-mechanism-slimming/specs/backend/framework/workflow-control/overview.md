# 路由与规则 Delta

## MODIFIED

- `skills/workflow-code-generation/scripts/workflow_control.py` 在 Runtime 路由和初始化前检查 `runtime` 能力。缺包停止；SVN 命中 Runtime 条件时明确拒绝，不降低风险或静默改走 Native Delivery。
- 测试内嵌路径进入规范加载步骤；Quick Design 可复用批准，但不跳过路由和 Verify 配置检查。
- React 消费活跃 Proposal、存在的 Design／Delta 及 UI 规格；旧 Spec 仅迁移读取。
- Proposal 与 Design 使用各自局部章节编号，跨文件引用必须带文件名。
- 任务依赖示例使用解析器支持的 `Task 1`／`Task 2, Task 3`；定向复审统一最多 10 轮，机器失败重试规则不变。

同步目标：`openspec/specs/backend/framework/workflow-control/overview.md` 及相关 Skill。
