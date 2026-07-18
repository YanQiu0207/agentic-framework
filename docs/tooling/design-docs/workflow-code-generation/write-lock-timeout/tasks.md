# 实施任务清单

> 由 `spec.md` 生成  
> 任务总数：2  
> 核心原则：先实现跨平台排他锁，再接入写路径并完成回归验证。

## 依赖关系总览

```text
Task 1（写锁、接线与测试）
  ↓
Task 2（验证、记录与归档）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | 新增跨平台写锁与超时 |
| `scripts/test_workflow_control.py` | 修改 | Task 1 | 新增多进程锁测试 |
| `skills/workflow-code-generation/reference/delegated-execution-guide.md` | 修改 | Task 1 | 记录单写者与超时参数 |
| `docs/design-docs/workflow-code-generation/write-lock-timeout/spec.md` | 修改 | Task 2 | 验证后归档 |
| `docs/design-docs/workflow-code-generation/write-lock-timeout/tasks.md` | 修改 | Task 1、2 | 任务与验证记录 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `workflow_control.py --lock-timeout` | 新增可选参数 | 所有写入命令 | Task 1 |

### 构建系统变更

- 不新增依赖。

## 风险与假设

| # | 描述 | 影响任务 | 假设或处理 |
| --- | --- | --- | --- |
| 1 | Windows 与 POSIX 锁 API 不同 | Task 1 | 封装为同一上下文管理器并分别测试可用分支 |
| 2 | 读取发生在锁外仍会丢更新 | Task 1 | 写命令必须在获锁后重新读取和决策 |

## 任务列表

### 任务 1：[x] 实现写锁、超时和测试

- 状态：完成
- 文件：`workflow_control.py`（修改）、`test_workflow_control.py`（修改）、`delegated-execution-guide.md`（修改）
- depends_on：[]
- review_profile：standard
- spec 映射：3、4、7.1
- 说明：实现跨平台 OS 文件锁，将所有写路径放入同一临界区并补并发测试。
- context_files：
  - `agentic-framework/skills/workflow-code-generation/scripts/workflow_control.py`——写入实现
  - `agentic-framework/scripts/test_workflow_control.py`——现有控制流测试
- verification：
  - [x] 持锁时第二个写进程按指定时间超时
  - [x] 超时不修改 `tasks.md`
  - [x] 释放后等待者可以继续写入
  - [x] 现有控制流测试全部通过
- artifacts：
  - 修改后的控制流脚本、测试和执行手册
- 子任务：
  - [x] 1.1：实现跨平台锁上下文管理器
  - [x] 1.2：接入写命令并补 `--lock-timeout`
  - [x] 1.3：补多进程测试并运行
- 验证记录（2026-07-12）：
  - 标准档首轮 Review：`NEEDS_CHANGES`；发现非有限超时、锁异常吞噬范围过宽、等待测试依赖固定休眠 3 项问题，均已修复。
  - `python -m unittest agentic-framework/scripts/test_workflow_control.py`：18 个测试通过。
  - `python -m unittest discover -s agentic-framework/scripts -p "test_*.py"`：60 个测试通过，1 个跳过。
  - `python -m compileall -q agentic-framework/skills/workflow-code-generation/scripts agentic-framework/scripts`：通过。
  - `git diff --check`：通过。

### 任务 2：[x] 完成审核、机器验证和归档

- 状态：完成
- 文件：`spec.md`（修改）、`tasks.md`（修改）
- depends_on：[Task 1]
- review_profile：standard
- spec 映射：7.2、8、9
- 说明：完成标准档 Review、全量验证、文档记录与本地提交。
- context_files：
  - `verify.config.json`——机器验证配置
  - `spec.md`——验收契约
- verification：
  - [x] 全量单元测试通过：60 个通过，1 个跳过
  - [x] 机器验证通过
  - [x] `git diff --check` 通过
- artifacts：
  - Review 和验证记录、归档规格、本地提交
- 子任务：
  - [x] 2.1：执行标准档 Review
  - [x] 2.2：运行机器验证
  - [x] 2.3：记录结果、归档并提交

### 最终审核与验证记录

- 标准档首轮 Review：`NEEDS_CHANGES`，确认 1 项 P1 和 2 项 P2。
- 复审：`PASS`，3 项 finding 均已修复，未发现新增 P0/P1。
- 全量测试：60 个通过，1 个跳过。
- 锁边界：仅保障本机协作进程通过 `workflow_control.py` 写同一 `tasks.md`；绕过脚本直接写文件和网络文件系统不在保证范围内。

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
| --- | --- | --- |
| 3～4 | Task 1 | 锁行为、接口和临界区 |
| 7 | Task 1、2 | 并发测试与回归 |
| 8～9 | Task 2 | 运维说明与归档 |
