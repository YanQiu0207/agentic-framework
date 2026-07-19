# 安装器人工约束 Delta

## ADDED Requirements

### Requirement：项目知识能力属于 Shared Core

`project-init` 与 `project-knowledge` 必须由 Production 和 Tooling 共用，Profile 不得改变项目知识 Artifact 目录。

#### Scenario：安装任一 Profile

- GIVEN 用户选择 Production 或 Tooling
- WHEN 安装框架资产
- THEN 两种 Profile 都包含 `project-init` 和 `project-knowledge`
