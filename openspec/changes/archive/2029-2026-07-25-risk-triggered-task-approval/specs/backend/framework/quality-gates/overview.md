# Delta：Production 任务级批准改为风险触发

**目标路径**：`openspec/specs/backend/framework/quality-gates/overview.md`

## MODIFIED Requirement：Production 人工介入由风险决定

Production 在 Tasks 整体批准后必须允许自主连续执行，人工暂停只在声明的升级条件命中时发生。

### Scenario：普通 Task 完成后不暂停

- **Given** 某 Task 已通过测试、Verification 与风险分档独立 Review
- **And** 该 Task 未声明任何升级条件
- **When** 执行段推进到下一个 Task
- **Then** 不得停止等待用户批准
- **And** `validate_change.py` 的 `plan` 与 `delivery` 阶段不得因缺少批准记录而拒绝

### Scenario：升级条件命中时强制暂停并留证

- **Given** 某 Task 声明了 `scope-change`、`irreversible`、`gate-failure`、`assumption-broken`、`user-requested` 或 `per-task-mode` 中任一条件
- **When** 该 Task 标记 Completed
- **Then** `tasks.md` 该 Task 必须含 `- Approval: granted (<condition-id>)`
- **And** 记录为 `pending`、缺失或条件 ID 不在白名单时，`delivery` 阶段必须失败关闭
- **And** 输出必须指出具体 Task 编号与条件 ID，不得只报告通用失败

### Scenario：逐 Task 批准模式回到全量要求

- **Given** 用户在 `tasks.md` 头部声明逐 Task 批准模式
- **When** 校验 `delivery` 阶段
- **Then** 全部 Task 均要求 `Approval: granted`
