# 实施任务清单

> 任务总数：2
> Code Review：Pending

## 任务列表

### 任务 1：[completed] 实现校验器

- 依赖：无
- 文件：`scripts/validate_change.py`
- 文档映射：`spec.md` 稳定退出码、`design.md` §1
- 验收标准：
  - [x] `python -m py_compile scripts/validate_change.py` 返回退出码 0。
- 子任务：
  - [x] 1.1：实现 CLI。

### 任务 2：[pending] 添加测试

- 依赖：Task 1
- 文件：`scripts/tests/test_validate_change.py`
- 文档映射：`proposal.md` §4、`design.md` §2
- 验收标准：
  - [x] `python -m unittest discover -s scripts/tests -p "test_*.py"` 返回退出码 0。
- 子任务：
  - [ ] 2.1：覆盖正常路径。

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
|---------|------|------|
| `proposal.md` §4 | Task 2 | 验证成功标准 |
| `spec.md` 稳定退出码 | Task 1 | 实现退出码 |
| `design.md` §1 | Task 1 | 实现设计方案 |

## 验证记录

- 构建命令：`python -m py_compile scripts/validate_change.py`，退出码 0。
- 测试命令：`python -m unittest discover -s scripts/tests -p "test_*.py"`，退出码 0。
