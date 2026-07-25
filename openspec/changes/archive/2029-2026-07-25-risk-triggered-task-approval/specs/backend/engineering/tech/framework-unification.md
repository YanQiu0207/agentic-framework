# Delta：Production 执行段按依赖波次推进

**目标路径**：`openspec/specs/backend/engineering/tech/framework-unification.md`

## MODIFIED Requirement：执行段消费任务依赖

Production 执行段必须按 `depends_on` 计算的稳定拓扑波次推进，不得忽略规划阶段产出的依赖信息。

### Scenario：无升级条件的波次连续执行

- **Given** 某波次内多个任务互无依赖且均未声明升级条件
- **When** 执行段推进该波次
- **Then** 波次内不得中断
- **And** 波次边界必须输出汇总报告

### Scenario：依赖字段缺失或成环

- **Given** `tasks.md` 的 `depends_on` 缺失或存在环
- **When** 计算波次
- **Then** 必须沿用现有 lint 失败路径
- **And** 不得静默退化为线性推进

## 不变部分

Task 级测试、Verification、风险分档独立 Review、Delivery 门禁、五维 strict 集成 Review 与 Archive 门禁的触发条件与判定标准均不变。Production 不因本变更引入 worktree、并行写入、Run Context 或 Trust Gate。
