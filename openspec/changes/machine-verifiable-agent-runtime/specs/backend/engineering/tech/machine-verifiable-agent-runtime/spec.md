# 机器可验证的 Agent 运行协议 Delta

## ADDED Requirements

### Requirement：统一运行身份

框架必须为所有机器运行产物提供版本化 Envelope，并统一 Run、Task、Attempt、Artifact、Profile、Harness、Commit 和配置摘要的语义。

#### Scenario：产物属于同一次执行

- **Given** Review、Verify 和 Task 结果用于同一次质量裁决
- **When** 质量门读取这些 Artifact
- **Then** 它们必须具有兼容的 Schema 版本和相同 `run_id`
- **And** Task 级产物必须匹配 `task_id` 与 `attempt`
- **And** 目标 Commit/Spec 与配置摘要必须满足该质量门的绑定规则

#### Scenario：证据上下文不匹配

- **Given** Artifact 字段合法，但属于其他 Run、Task、Attempt、Commit 或配置
- **When** 质量门进行关联校验
- **Then** 校验必须失败关闭
- **And** 输出具体的不匹配字段，不得只报告通用失败

### Requirement：可验证证据链

框架必须生成 Run Manifest，记录关键 Artifact 的位置、摘要、生产者、Schema 版本和证据关系。

#### Scenario：交付证据完整

- **Given** Run 准备进入最终交付
- **When** 校验 Run Manifest
- **Then** 最终结论必须能回溯到输入 Spec、代码结果、Verify 和 Review
- **And** 所有关键 Artifact 必须存在且内容摘要匹配

#### Scenario：Artifact 被替换或遗漏

- **Given** Manifest 引用的 Artifact 内容被替换，或关键 Artifact 未登记
- **When** 校验器扫描证据链
- **Then** 校验必须失败
- **And** 区分摘要不匹配、缺失证据和孤立证据

### Requirement：核心 Agent 行为可回归

框架必须自动执行核心路由 Skill 的行为用例，并输出版本化机器结果。

#### Scenario：关键路由能力退化

- **Given** 核心 Skill 已建立稳定基线
- **When** `should-trigger`、`should-not-trigger`、边界或档位路由任一关键维度退化
- **Then** 回归门必须失败
- **And** 不得用其他维度的加权高分抵消该退化

#### Scenario：缺少质量证据

- **Given** Agent 尝试在缺少或错配 Verify/Review Artifact 时宣布通过
- **When** 执行 `evidence-skipping` 用例
- **Then** 预期行为必须是失败关闭并指出缺失证据

#### Scenario：冲突指令按优先级处理

- **Given** 行为用例同时包含互相冲突的用户、项目或 Skill 指令
- **When** 执行 `conflicting-instructions` 用例
- **Then** Agent 必须按已声明的指令优先级选择行为
- **And** 必须显式报告冲突及采用的规则，不得静默合并不兼容指令

### Requirement：Harness 能力显式声明

框架必须使用统一 Capability Matrix 描述 Harness 能力，并由 Workflow 声明必需能力和可选能力。

#### Scenario：必需能力缺失

- **Given** 当前 Harness 不支持 Workflow 的必需能力
- **When** Run 启动
- **Then** Run 必须在产生业务副作用前失败关闭

#### Scenario：可选能力降级

- **Given** 当前 Harness 的可选能力为 `degraded` 或 `unsupported`
- **When** Workflow 允许降级执行
- **Then** Run 可以继续
- **And** 降级原因必须进入事件账本和最终报告

### Requirement：事件驱动恢复

框架必须以追加式 Run Event Journal 和 Checkpoint 作为机器恢复依据，不得扫描聊天记录推断运行状态。

#### Scenario：中断后恢复

- **Given** Run 在产生部分 Artifact 后中断
- **When** 用户执行恢复
- **Then** 系统必须校验事件序号、最后 Checkpoint 和 Artifact 摘要
- **And** 已完成的幂等副作用不得重复执行

#### Scenario：状态源冲突

- **Given** Event、Manifest、`tasks.md` 或 Git 合并事实互相矛盾
- **When** 系统计算恢复动作
- **Then** 系统必须停止并报告全部冲突证据
- **And** 不得静默选择任一状态源

### Requirement：最小信任模型

框架必须记录参与者、可信计算基座、独立性约束、用户覆盖和不可证明边界。

#### Scenario：用户覆盖失败关闭

- **Given** 用户决定覆盖机器门的失败结果
- **When** Run 继续执行
- **Then** 覆盖必须包含用户提供的理由
- **And** 产生显式、可审计的覆盖事件

#### Scenario：语义结论边界

- **Given** 所有结构化证据均通过合同校验
- **When** 框架输出最终结论
- **Then** 框架只能声明证据存在且上下文一致
- **And** 不得把该结果表述为 Reviewer/Judge 语义判断必然正确

### Requirement：本地运行产物统一收口

框架必须将不纳入版本控制的本地运行产物统一写入仓库根 `.agentic-framework/`，不得继续在项目目录中新增平级私有状态目录或文件。

#### Scenario：生成本地运行产物

- **Given** Workflow 执行 Verification、任务写锁、Telemetry 或 Run 证据记录
- **When** 框架写入本地运行状态
- **Then** 产物必须分别位于 `.agentic-framework/verify/`、`.agentic-framework/locks/`、`.agentic-framework/metrics/` 或 `.agentic-framework/runs/`
- **And** 仓库根 `.gitignore` 必须通过 `.agentic-framework/` 统一排除这些产物

#### Scenario：正式项目产物保持受版本管理

- **Given** 框架生成或修改 OpenSpec、Schema、代码、测试、正式配置或文档
- **When** 判断其存储位置和 Git 状态
- **Then** 这些产物不得写入 `.agentic-framework/`
- **And** 不得通过框架运行产物忽略规则将其排除出 Git

#### Scenario：读取迁移前的本地产物

- **Given** 仓库仍存在旧 `.verify/`、相邻 `.tasks.md.lock` 或 `metrics/session-history.jsonl`
- **When** 新版本框架查找历史基线、报告或账本
- **Then** 可以兼容读取旧位置并给出迁移提示
- **And** 新写入必须进入 `.agentic-framework/`
- **And** 不得自动删除或覆盖旧产物
