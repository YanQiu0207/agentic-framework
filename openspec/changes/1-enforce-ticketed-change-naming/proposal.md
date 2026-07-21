# 强制 Change 使用工单号命名

**状态**：Quick Draft
- **工单号**：1
- **日期**：2026-07-22
- **作者**：主会话

## 1. 背景

当前 Change 目录只校验小写 kebab-case，无法将一次变更与外部工单稳定关联。归档目录也只保留日期和变更名称，缺少工单号。

## 2. 目标

- `opsx-*` 系列在创建目录前，必须由用户输入一串纯数字工单号，不自动生成或推荐。
- `workflow-*` 系列根据已归档 Change 中的最大工单号加 1，向用户推荐下一个工单号；最终仍需用户确认，也允许用户改用其他纯数字工单号。
- 正在开发的 Change 使用 `openspec/changes/<ticket>-<change-name>/`。
- 已归档的 Change 使用 `openspec/changes/archive/<ticket>-YYYY-MM-DD-<change-name>/`。
- 校验器拒绝缺少工单号、工单号非纯数字或归档目录格式不匹配的路径。
- 保留现有 `<change-name>` 的小写 kebab-case 约束。

## 3. 方案

### 设计方案

1. 将 Change 名称校验拆成「纯数字工单号」和「小写 kebab-case 变更名」两部分。
2. 活跃目录校验 `<ticket>-<change-name>`，其中 `<ticket>` 为一串数字，且 `<change-name>` 至少包含两个小写英文片段。
3. 归档目标校验 `<ticket>-YYYY-MM-DD-<change-name>`，日期必须是有效日期，且工单号和 Change 名称必须与活跃目录一致。
4. `workflow-*` 系列扫描 `openspec/changes/archive/` 下符合新格式的目录，提取最大工单号并加 1；无历史归档时从 `1` 开始推荐。
5. `opsx-*` 系列只显示输入提示并校验用户输入，不调用自动推荐逻辑。
6. 更新 `opsx-*`、`workflow-*`、项目知识和 README 中的路径示例及交互提示。
7. 更新校验器测试，覆盖合法路径、缺少工单号、非法工单号、归档前缀不一致和无效日期。

### 关键权衡

- `workflow-*` 只推荐工单号，不自动占用或锁定工单号；`opsx-*` 完全由用户输入。
- 旧归档目录保留原路径，新归档统一使用带工单号的格式。

## 4. 非目标

- 不修改已有归档目录。
- 不改变 Change 文档内容、归档审批或知识同步流程。
- 不为工单号推荐增加跨进程或跨仓库的全局序列号锁；`workflow-*` 的推荐值最终以用户确认值为准。
- 不要求脚本判断 `<change-name>` 的自然语言词性；「动词-名词」仍是命名约定，机器只校验结构。

## 5. 成功标准

- `openspec/changes/1-add-dark-mode/` 能通过名称校验。
- `openspec/changes/add-dark-mode/` 被拒绝。
- `openspec/changes/abc-add-dark-mode/` 被拒绝。
- `openspec/changes/archive/1-2026-07-22-add-dark-mode/` 能通过归档目录名校验。
- 工单号或 Change 名称不一致的归档目标被拒绝。
- `workflow-*` 能从归档目录推荐最大工单号加 1，并在无归档时推荐 `1`。
- `opsx-*` 不自动推荐工单号，必须等待用户输入。
- 现有校验器测试及新增测试全部通过。

## 6. 知识影响

- 命中：Change 生命周期路径约定、校验器命名合同及相关 Skill 文档。
- 在实现完成后同步项目 README、相关 Skill 和长期项目知识；不修改跨项目公共知识库。
