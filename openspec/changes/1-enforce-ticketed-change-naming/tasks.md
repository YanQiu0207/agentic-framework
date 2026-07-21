# 实施任务清单

> 当前阶段：已完成实现、测试和验证。
>
> 任务总数：3

## 执行图

```text
Task 1 → Task 2 → Task 3
```

### 任务 1：[x] 更新校验器与测试

- 状态：完成
- attempts：0
- 依赖：无
- 文档映射：工单号命名与校验器合同
- Review Profile: standard
- Task Review: PASS
- context_files：`scripts/validate_change.py`、`scripts/tests/test_validate_change.py`、本 Change `proposal.md`
- 文件：`scripts/validate_change.py`、`scripts/tests/test_validate_change.py` 及必要测试夹具
- verification：运行校验器测试；覆盖活跃目录和归档目录命名边界；执行 `git diff --check`
- artifacts：带工单号的路径校验、回归测试
- 验收标准：
    - [x] 活跃目录要求 `<ticket>-<change-name>`。
    - [x] `<ticket>` 只允许数字且不能为空。
    - [x] 归档目录要求 `<ticket>-YYYY-MM-DD-<change-name>`。
    - [x] 归档工单号和 Change 名称必须与活跃目录一致。
    - [x] 无效日期和旧格式均被拒绝。

### 任务 2：[x] 增加 workflow 工单号推荐脚本并更新文档

- 状态：完成
- attempts：0
- 依赖：Task 1
- 文档映射：workflow 与 opsx Skill 命名提示
- Review Profile: standard
- Task Review: PASS
- context_files：`skills/opsx-*`、`skills/workflow-*`、`skills/project-knowledge/SKILL.md`、`README.md`、`openspec/index.md`
- 文件：`scripts/suggest_ticket_number.py`、相关 Skill、README、项目知识文档
- 脚本接口：接收一个归档目录路径，遍历其**一级子目录**；对每个目录名按 `-` 切分，取第一段；第一段是纯数字时纳入候选；最终输出所有候选中的最大值加 1，无数字候选时输出 `1`。
- verification：脚本单元测试；推荐值计算测试；检索旧路径示例；Markdown 排版检查；执行 spec drift 检查
- artifacts：统一的工单号询问提示、开发路径、归档路径和 workflow 推荐逻辑
- 验收标准：
    - [x] Skill 明确要求向用户询问纯数字工单号。
    - [x] `scripts/suggest_ticket_number.py` 只遍历传入归档目录的一级目录。
    - [x] 目录名第一段为纯数字时才纳入候选，例如 `123-2026-07-22-add-mode` 纳入，`abc-2026-07-22-fix` 和 `12x-2026-07-22-fix` 不纳入。
    - [x] `workflow-*` 使用脚本结果推荐归档最大工单号加 1，无数字候选时推荐 `1`。
    - [x] `opsx-*` 只接受用户输入，不自动推荐工单号。
    - [x] 所有开发中路径统一为 `<ticket>-<change-name>`。
    - [x] 所有归档路径统一为 `<ticket>-YYYY-MM-DD-<change-name>`。

### 任务 3：[x] 全量验证与评审

- 状态：完成
- attempts：0
- 依赖：Task 2
- 文档映射：项目知识与 README 路径规范；proposal.md 验收标准
- Review Profile: standard
- Task Review: PASS
- context_files：Task 1、Task 2 的全部改动和验证产物
- 文件：无新增文件
- verification：运行相关 Python 测试、文档检查、项目验证和统一 Code Review
- artifacts：测试报告、机器验证报告、Review 报告
- 验收标准：
    - [x] 相关测试全部通过。
    - [x] 新旧格式边界行为与 Proposal 一致。
    - [x] 工作区中本次改动范围明确，不覆盖既有未相关修改。
