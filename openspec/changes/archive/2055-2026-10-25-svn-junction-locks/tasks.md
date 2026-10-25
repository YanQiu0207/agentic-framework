# 实施任务清单

> 由 proposal.md 与 design.md 生成。
> 任务总数：2。
> 核心原则：先建立回归保护，再最小修复，最后同步知识与集成验证。

## 依赖关系总览

```text
Task 1（根定位与写锁修复、回归测试）→ Task 2（知识同步与集成验证）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | 逻辑根与真实身份锁 |
| `scripts/test_workflow_control.py` | 修改 | Task 1 | SVN、Junction 与进程竞争 |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 修改 | Task 2 | 同步锁保证与限制 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `_repository_root()` | 保持签名、修复作用域 | 配置定位与 CLI | Task 1 |
| `_task_write_lock()` | 增加共享锁、保持超时合同 | 写入命令 | Task 1 |

### 构建系统变更

无；沿用现有 pytest 和 Verify 配置。

## 风险与假设

| # | 描述 | 影响任务 | 假设／处理 |
| --- | --- | --- | --- |
| 1 | 并发写入安全 | Task 1 | strict 审查、进程竞争回归、固定锁序 |
| 2 | 共享临时目录范围 | Task 1、2 | 不承诺跨主机／跨用户协调 |
| 3 | 其他先解析路径的调用 | Task 1 | 用户追加批准，一并修复 CLI 的 VCS／能力检查作用域 |

## 任务列表

### 任务 1：[x] 修复根定位与共享任务写锁
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`（修改）、`scripts/test_workflow_control.py`（修改）
- depends_on: []
- review_profile: strict
- 文档映射：proposal.md 的范围及验收标准；design.md 的根定位、写锁、验证与限制
- 说明：先以回归测试重现，再最小修改实现，保留旧锁、统一 deadline、原子写入和状态机。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py` — `_repository_root()`、`_task_write_lock()`、`main()` 与配置读取
  - `scripts/test_workflow_control.py` — 子进程竞争与回归测试
  - `scripts/vcs.py` — 后端探测合同，不修改
- verification:
  - [x] `python -m pytest scripts/test_workflow_control.py -q` 通过。
  - [x] 新增回归在修复前失败，修复后通过；Windows Junction 与 CP936 兼容性有执行证据。
  - [x] 使用冻结基线运行现有 Verify 配置，未弱化检查。
- artifacts:
  - `skills/workflow-code-generation/scripts/workflow_control.py`
  - `scripts/test_workflow_control.py`
  - `.agentic-framework/verify/report.json`
- 子任务：
  - [x] 1.1：通过 workflow-test-generation 建立回归保护。
  - [x] 1.2：修复根定位及锁实现并运行测试。

### 任务 2：[x] 同步控制流知识并执行集成验证
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`openspec/specs/backend/framework/workflow-control/overview.md`（修改）
- depends_on: Task 1
- review_profile: strict
- 文档映射：proposal.md 的知识影响与验收标准；design.md 的写锁与限制
- 说明：同步锁的逻辑根与真实身份语义、边界，记录架构决策、放弃方案及约束；运行最终机器验证。
- context_files:
  - `openspec/specs/backend/framework/workflow-control/overview.md` — 长期控制流说明
  - `skills/workflow-code-generation/scripts/workflow_control.py` — 实现事实
  - `scripts/test_workflow_control.py` — 验证事实
- verification:
  - [x] 长期说明与根定位、锁顺序及范围一致，按 md-zh 自检。
  - [x] `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base ef57ed4` 通过。
- artifacts:
  - `openspec/specs/backend/framework/workflow-control/overview.md`
  - `.agentic-framework/verify/report.json`
- 子任务：
  - [x] 2.1：同步知识并检查冲突。
  - [x] 2.2：运行集成验证。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| Proposal 问题、范围及验收 | Task 1、2 | 实现、测试及验证 |
| Design 根定位、写锁 | Task 1 | 实现与回归 |
| 知识影响、验证与限制 | Task 2 | 长期说明 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| design.md 的写锁与限制 | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Synced | 已有入口，无需新增 |

## 知识冲突

- 结论：无未决冲突。原概览只说明项目锁，现已按实现同步身份锁，同时保留旧锁兼容、超时和原子写入约束。

## 实际 Diff 核对

- 核对状态：`git diff --check` 与 116 项定向测试通过；变更限于实现、回归测试、长期控制流说明及本 Change。真实 SVN 用例证据及对应源码快照详见 validation.md。

## 冻结与验收顺序

- 用户明确要求先冻结代码、文档及归档状态，再集中全量验证。因此预先固定最终归档目录与生命周期标记，但不提前声称验证完成；上述正式验证验收项保持未勾选，执行状态在最终报告产生后经状态机收口。
- 正式验证后仅更新任务执行元数据及复选框，不改变冻结的验收正文；不为状态回填反复运行全量测试。Native 内容主体按现有算法规范化这些执行字段，交付门仍重算并核对相同主体。
