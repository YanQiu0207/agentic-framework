# Validator Requirements

## ADDED Requirements

### Requirement: 稳定退出码

校验器必须为合法变更返回退出码 0。

#### Scenario: 合法变更

- GIVEN 变更文档结构完整
- WHEN 执行 Plan 校验
- THEN 进程返回退出码 0
