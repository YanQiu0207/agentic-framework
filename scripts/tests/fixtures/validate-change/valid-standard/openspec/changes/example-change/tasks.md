# 实施任务清单

> 任务总数：2
> Code Review：Pending

- Review Report: review-reports/review-report.json

## 任务列表

### 任务 1：[completed] 实现校验器
- Review Profile: standard
- Task Review: PASS
- Review Report: review-reports/task-1-review.json

- 依赖：无
- 文件：`scripts/validate_change.py`
- 文档映射：`spec.md` 稳定退出码、`design.md` §1
- 验收标准：
  - [x] `python -m py_compile scripts/validate_change.py` 返回退出码 0。
- 子任务：
  - [x] 1.1：实现 CLI。

### 任务 2：[completed] 添加测试
- Review Profile: standard
- Task Review: PASS
- Review Report: review-reports/task-2-review.json

- 依赖：Task 1
- 文件：`scripts/tests/test_validate_change.py`
- 文档映射：`proposal.md` §4、`design.md` §2
- 验收标准：
  - [x] `python -m unittest discover -s scripts/tests -p "test_*.py"` 返回退出码 0。
- 子任务：
  - [x] 2.1：覆盖正常路径。

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
|---------|------|------|
| `proposal.md` §4 | Task 2 | 验证成功标准 |
| `spec.md` 稳定退出码 | Task 1 | 实现退出码 |
| `design.md` §1 | Task 1 | 实现设计方案 |

## 验证记录

- 构建命令：`python -m py_compile scripts/validate_change.py`，退出码 0。
- 测试命令：`python -m unittest discover -s scripts/tests -p "test_*.py"`，退出码 0。

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| specs/business/validator/spec.md | openspec/specs/business/validator/spec.md | ADDED | Completed | openspec/specs/index.md 已更新 |

## 知识冲突

- 结论：无冲突。

## 实际 Diff 核对

- 已核对实际 Diff、Change 和测试证据：PASS。
