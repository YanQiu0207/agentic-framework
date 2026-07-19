# 实施任务清单

> 当前阶段：Tasks 1～3 已完成；机器验证与 Fast-Path 自举交付门均通过。
>
> 任务总数：3

## 执行图

```text
Task 1 → Task 2 → Task 3
```

### 任务 1：[completed] 立项与设计边界

- 状态：完成
- attempts：0
- depends_on：[]
- review_profile：lightweight
- context_files：本 Change `proposal.md`、`check_delivery.py`、`SKILL.md` 第 8 步、Trust Model §4.2
- 文件：本 Change `proposal.md`、`tasks.md`
- verification：Markdown 排版、相对链接、`git diff --check`
- artifacts：活跃 Change 文档
- 验收标准：
    - [x] 明确 Fast-Path 与 strict 路径边界，不削弱 Trust Gate。
    - [x] 明确 Fast-Path 裁决为 `fast-path-pass`，显式声明不可证明项。

### 任务 2：[completed] 实现 Fast-Path 有界裁决与测试

- 状态：完成
- attempts：0
- depends_on：[Task 1]
- review_profile：standard
- context_files：`check_delivery.py`、`test_check_delivery.py`、`runtime_workflow.finalize_run`
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、对应测试
- verification：Fast-Path 合法/非法用例、strict 路径回归、`git diff --check`
- artifacts：Fast-Path 分支实现、测试报告
- 验收标准：
    - [x] 无 `--run-dir` 时走 Fast-Path：lightweight review + 机器验证 + git 干净 + 知识影响。
    - [x] 输出 `fast-path-pass` + `verified_claims` + `unprovable_claims`。
    - [x] strict/standard review 无 Run、机器验证 FAIL、P0/P1≠0、工作区脏均被拒绝。
    - [x] strict Run 路径（`--run-dir`）回归通过。

### 任务 3：[completed] 同步 SKILL 与 Trust Model 文档

- 状态：完成
- attempts：0
- depends_on：[Task 2]
- review_profile：lightweight
- context_files：`workflow-code-generation/SKILL.md` 第 8 步、活跃 spec.md、Trust Model 文档
- 文件：`SKILL.md`、`openspec/specs/.../machine-verifiable-agent-runtime/spec.md`、Trust Model 文档
- verification：文档排版、spec drift 检查、全量 Verification
- artifacts：更新后的 SKILL 第 8 步、spec Scenario、Trust Model 说明
- 验收标准：
    - [x] SKILL 第 8 步描述 Fast-Path 有界裁决，不再宣称 lightweight 过 strict 门。
    - [x] spec.md 新增「Fast-Path 交付的有界裁决」Scenario。
    - [x] Trust Model 文档说明 Fast-Path 显式不声明 strict 独立审查。
