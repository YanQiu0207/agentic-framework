# 实施任务清单

> 由 `spec.md` 生成
> 任务总数：4
> 核心原则：代码是当前实现的唯一事实源；机器校验结构，Code Review 校验语义
> Code Review：PASS

## 依赖关系总览

```text
Task 1 → Task 2 → Task 4
              ↗
Task 3 ──────┘
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/validate_change.py` | 新建 | Task 1 | 三阶段只读校验器 |
| `scripts/tests/test_validate_change.py` | 新建 | Task 2 | 单元测试 |
| `scripts/tests/fixtures/validate-change/` | 新建 | Task 2 | 正反例 Fixture |
| `skills/opsx-*/SKILL.md` | 修改 | Task 3 | 接入 Plan、Delivery、Archive 门禁 |
| `README.md` | 修改 | Task 3 | 补充确定性校验说明 |
| `spec.md`、`tasks.md` | 修改 | Task 4 | 回写实施和验证结果 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `validate_change.py --repo --change --phase [--json]` | 新增 CLI | `opsx-*` Skills、人工验证 | Task 1、3 |

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 当前 Markdown 模板并非完全统一 | Task 1、2 | 只解析稳定的最小契约，正反例 Fixture 固化边界 |
| 2 | Quick Design 允许缺少 `specs/` 和 `design.md` | Task 1、2 | 通过 Proposal 中的 `Quick Draft` 标记路由 |
| 3 | 部分变更无需测试 | Task 1、2 | 接受明确的 `N/A` 及理由，不用关键词猜测测试充分性 |
| 4 | 仓库已有未提交改动 | Task 4 | 只纳入当前连续需求产生的改动，不覆盖无关文件 |

## 任务列表

### 任务 1：[completed] 实现三阶段只读校验器

- 依赖：无
- 文件：`scripts/validate_change.py`
- 文档映射：`spec.md` §7、§8、§9、§11
- context：
  - `skills/opsx-code-generation/reference/task_planning_guide.md`：Tasks 当前格式
  - `skills/opsx-quick-design/reference/quick-proposal-template.md`：Quick Draft 格式
  - `skills/opsx-requirements-clarification/reference/proposal_template.md`：标准 Proposal 格式
- 验收标准：
  - [x] 支持 `plan`、`delivery`、`archive` 三阶段
  - [x] 支持文本与 `--json` 输出
  - [x] 退出码严格为 `0/1/2`
  - [x] 错误包含规则编号、文件、行号和修复提示
  - [x] 检测任务依赖缺失、自依赖和多节点环
  - [x] 禁止 `openspec/specs/` 中央规范库
  - [x] 只读取文件，不修改用户文档

### 任务 2：[completed] 建立 Fixtures 与单元测试

- 依赖：Task 1
- 文件：
  - `scripts/tests/test_validate_change.py`
  - `scripts/tests/fixtures/validate-change/**`
- 文档映射：`spec.md` §12、§16
- context：
  - `scripts/validate_change.py`：被测接口
  - `scripts/lint_skill_graph.py`：仓库脚本风格参考
- 验收标准：
  - [x] 覆盖 Standard 与 Quick 正例
  - [x] 覆盖缺失文件、依赖环、未完成任务、Review 未通过和中央规范库反例
  - [x] 覆盖 JSON 输出和退出码
  - [x] `python -m unittest discover -s scripts/tests -p "test_*.py"` 通过

### 任务 3：[completed] 接入 OPSX Skills 并同步 README

- 依赖：无
- 文件：
  - `skills/opsx-requirements-clarification/SKILL.md`
  - `skills/opsx-quick-design/SKILL.md`
  - `skills/opsx-system-design/SKILL.md`
  - `skills/opsx-code-generation/SKILL.md`
  - `skills/opsx-test-generation/SKILL.md`
  - `skills/opsx-archive/SKILL.md`
  - `skills/opsx-project-knowledge/SKILL.md`
  - `README.md`
- 文档映射：`spec.md` §10、§13
- context：
  - `scripts/validate_change.py`：CLI 契约
  - 各 Skill 当前阶段和强制规则
- 验收标准：
  - [x] Plan、Delivery、Archive 调用时点与方案一致
  - [x] 校验失败时失败即停
  - [x] 测试阶段不启动第二次 Code Review
  - [x] `opsx-project-knowledge` 明确代码事实源和无中央规范库
  - [x] README 描述与 Skill 一致

### 任务 4：[completed] 全量验证、最终 Review 与文档回写

- 依赖：Task 2、Task 3
- 文件：`spec.md`、`tasks.md` 及 Review 修复涉及的文件
- 文档映射：`spec.md` §13、§15、§16、§18
- 验收标准：
  - [x] Python 编译检查通过
  - [x] 单元测试通过
  - [x] Skill 图检查 `errors=0 warnings=0`
  - [x] `git diff --check` 通过
  - [x] 全部变更只执行一次完整 Code Review
  - [x] P0/P1 finding 修复后定向 re-review PASS
  - [x] `Code Review` 状态更新为 `PASS`

## 验证执行记录

- 构建执行记录：`python -m py_compile scripts/validate_change.py scripts/tests/test_validate_change.py`，退出码 0。
- 测试执行记录：`python -m unittest discover -s scripts/tests -p "test_*.py" -v`，20 项测试通过。
- Skill 图执行记录：`python scripts/lint_skill_graph.py`，`errors=0 warnings=0`。
- Diff 执行记录：`git diff --check`，退出码 0。

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
|---------|------|------|
| §7 确定性校验器 | Task 1、2 | CLI 与测试 |
| §8 校验阶段 | Task 1、2、3 | 规则实现和 Skill 接线 |
| §10 Skill 接入点 | Task 3 | 全部 OPSX Skills |
| §12 测试策略 | Task 2 | Fixtures 和测试 |
| §13 分阶段实施 | Task 1～4 | 完整实施顺序 |
| §16 验收标准 | Task 2、4 | 机器验证和 Review |
