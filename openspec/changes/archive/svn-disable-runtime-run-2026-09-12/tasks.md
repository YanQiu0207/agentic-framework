# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 1
> 核心原则: 单任务线性执行，实现与测试同批交付

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | 新增 `_detect_vcs`，route 在 SVN 下强制 native-delivery |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 1 | 步骤 1 / 步骤 5 补 SVN 限制 |
| `scripts/test_workflow_control.py` | 修改 | Task 1 | SVN 降级与 `_detect_vcs` 探测测试 |
| `openspec/specs/backend/framework/workflow-control/overview.md` | 修改 | Task 1 | 主链路节同步 route 契约 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `workflow_control.py route` 输出 | 行为变更（SVN 下恒 native-delivery） | `workflow-code-generation` 步骤 5 主编排 | Task 1 |

### 构建系统变更

- 无（纯 Python 标准库脚本，pytest 直跑）。

## 任务列表

### 任务 1: [x] route 在 SVN 工作副本强制 native-delivery
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-code-generation/scripts/workflow_control.py`（修改）, `skills/workflow-code-generation/SKILL.md`（修改）, `scripts/test_workflow_control.py`（修改）, `openspec/specs/backend/framework/workflow-control/overview.md`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md 1. 问题与目标 / 2.1 实现 / 2.2 权衡
- 说明: `_detect_vcs` 语义与 `verify.py:348-377` 一致（Git 优先、二进制缺失降级探测、两者皆无返回 None），git 调用补 `-C` 比参考实现更稳。route 仅在命中 `runtime-run` 时探测：SVN 下 stderr 明示并重建 `ExecutionRoute("native-delivery", reasons)`，升级原因保留供下游核对；未命中时不探测（零开销，语义等价）。测试覆盖降级主路径、reasons 保留、stderr 明示，以及 `_detect_vcs` 的 Git 优先 / SVN 回退 / 皆无 / git 二进制缺失四条分支。SKILL.md 与 overview.md 同步契约。Review（standard，integration）首审 PASS，零 P0/P1。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:_detect_vcs` — 探测语义参考实现（:348-377）
  - `skills/workflow-code-generation/scripts/workflow_control.py:_repository_root` — VCS 探测目录来源
  - `openspec/specs/backend/framework/workflow-control/overview.md` — 契约同步目标
- verification:
  - [x] `python -m pytest scripts/test_workflow_control.py -q` 全部通过（89 项）
  - [x] `python -m pytest scripts -q` 全量通过（verify B-tests-pass exit=0）
  - [x] `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json` 总判定 PASS
  - [x] `python scripts/lint_skill_graph.py` 退出码 0
- artifacts:
  - `skills/workflow-code-generation/scripts/workflow_control.py`（修改）
  - `skills/workflow-code-generation/SKILL.md`（修改）
  - `scripts/test_workflow_control.py`（修改）
  - `openspec/specs/backend/framework/workflow-control/overview.md`（修改）
- 子任务:
  - [x] 1.1: 新增 `_detect_vcs` 探测函数
  - [x] 1.2: route 分支 SVN 强制降级 + stderr 明示
  - [x] 1.3: SKILL.md 与 overview.md 契约同步
  - [x] 1.4: 补测试并跑通全量验证

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal 1. 问题与目标 | Task 1 | 根因与验收标准 |
| proposal 2.1 实现 | Task 1 | 探测与降级逻辑落地 |
| proposal 2.2 权衡 | Task 1 | 禁用而非补齐、探测时机 |
| proposal 3. 知识影响 | Task 1 | 长期规格与 SKILL.md 落盘 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Completed | 条目级修改，不影响索引 |

> 本 Change 为 Quick Draft，未创建 `specs/` Delta。长期知识修改由 Task 1 直接落盘，归档阶段由 `project-knowledge` 核对。

## 知识冲突

- 结论：Resolved。本 Change 仅新增 SVN 禁用契约，未改动既有 Git 路径行为；`workflow-control/overview.md` 的修改段为新增句子，与既有内容无冲突。

## 实际 Diff 核对

- 核对状态：PASS。核对命令：`git diff --stat HEAD`（4 个文件：workflow_control.py、SKILL.md、test_workflow_control.py、overview.md）；`python -m pytest scripts -q` 全部通过（verify B-tests-pass exit=0）；`verify.py` 总判定 PASS；standard integration Review 首审 PASS（零 P0/P1）。
