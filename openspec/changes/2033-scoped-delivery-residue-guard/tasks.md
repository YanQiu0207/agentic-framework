# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数：4
> 核心原则：先冻结并采集独立 S0 合同，再接入 Git/SVN 交付门，最后同步契约并做全量回归。

## 依赖关系总览

```text
Task 1（Scoped S0 快照与范围冲突检查）
    ↓
Task 2（Git/SVN Scoped Delivery 门）
    ↓
Task 3（自动化测试与回归）
    ↓
Task 4（Skill 与长期 Spec 同步）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-verification/scripts/verify.py` | 修改 | Task 1 | 采集独立残留快照、冻结范围和冲突检查。 |
| `skills/workflow-verification/scripts/test_verify.py` | 修改 | Task 1, Task 3 | 覆盖 Git/SVN S0 采集与失败关闭。 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 2 | 新增 Scoped Delivery CLI、Git/SVN 范围和 S0/S1 校验。 |
| `scripts/test_check_delivery.py` | 修改 | Task 2, Task 3 | 覆盖 Scoped 门、报告措辞和回归。 |
| `skills/workflow-verification/SKILL.md` | 修改 | Task 4 | 记录 Scoped S0 与 `spec_drift` 的边界。 |
| `skills/workflow-code-generation/SKILL.md` | 修改 | Task 4 | 记录显式 Scoped Delivery 交付口径。 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 4 | 同步质量门长期契约。 |
| `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` | 修改 | Task 4 | 同步 Native Delivery 有界裁决。 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `verify.py --save-baseline` | 扩展 | `workflow-verification` | Task 1 |
| Verify 基线 JSON | 扩展 | `verify.py`、`check_delivery.py` | Task 1, Task 2 |
| `check_delivery.py --scoped-delivery` | 新增 | `workflow-code-generation` | Task 2 |

### 构建系统变更

- 无；Python 脚本与现有 `pytest` 测试入口不变。

## 风险与假设

| # | 描述 | 影响任务 | 假设／处理 |
| --- | --- | --- | --- |
| 1 | Git 的暂存区与工作树可能对同一路径具有不同内容。 | Task 1, Task 2 | 分别记录并比较状态和指纹。 |
| 2 | SVN 无本地提交等价物。 | Task 2 | 仅接受可查询的提交 revision；否则失败关闭。 |
| 3 | 通用测试读取范围无法可靠静态获取。 | Task 1 | 仅冻结可声明的修改路径和生成输出目录。 |
| 4 | 基线 `changed_files_snapshot` 已用于 `spec_drift`。 | Task 1, Task 2 | 新增独立字段，禁止复用或由 ignore 推导。 |
| 5 | 未跟踪目录可包含空目录、链接或读取失败条目。 | Task 1 | 规范化树摘要并对无法读取项失败关闭。 |

## 任务列表

### 任务 1：[ ] Scoped S0 残留快照与范围冲突检查
- 状态：未开始
- 文件：`skills/workflow-verification/scripts/verify.py`（修改）、`skills/workflow-verification/scripts/test_verify.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md 1.目标／验收标准、2.1、2.2、2.4、2.5（1、2、3、5）
- 说明：在采集基线前接收并验证冻结范围，采集与 `spec_drift` 路径快照隔离的 Git/SVN 残留 S0；范围重叠、VCS 状态异常或内容无法摘要时不写入基线。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:cmd_save_baseline()` — 基线写入入口。
  - `skills/workflow-verification/scripts/verify.py:_changed_files()` — 当前 Git/SVN 变更枚举。
  - `skills/workflow-verification/scripts/verify.py:_svn_status_changes()` — SVN 状态语义。
  - `skills/workflow-verification/scripts/test_verify.py` — Verify 回归测试。
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py -q` 返回 0。
  - [ ] Git 和 SVN 模拟用例验证 S0 内容指纹与范围重叠失败关闭。
  - [ ] 失败用例确认既有基线文件未被覆盖。
- artifacts:
  - `skills/workflow-verification/scripts/verify.py`
  - `skills/workflow-verification/scripts/test_verify.py`
- 子任务:
  - [ ] 1.1：定义并校验 Scoped 范围与独立残留快照结构。
  - [ ] 1.2：实现 Git、SVN 与未跟踪树的规范化 S0 采集。
  - [ ] 1.3：实现范围重叠和无法摘要时的失败关闭。
  - [ ] 1.4：补齐 S0 采集及不覆盖基线测试。

### 任务 2：[ ] Git/SVN Scoped Delivery 机器门
- 状态：未开始
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: [Task 1]
- review_profile: strict
- 文档映射：proposal.md 1.目标／验收标准、2.1、2.2、2.3、2.5（1、2、4、5）
- 说明：新增显式 Scoped Delivery CLI，读取 S0、比较 S1，校验 Git 提交或 SVN revision Diff 只覆盖冻结范围，并将成功报告限定为 Scoped 口径。
- context_files:
  - `skills/workflow-code-generation/scripts/check_delivery.py:check_git_clean()` — 现有绝对干净门。
  - `skills/workflow-code-generation/scripts/check_delivery.py:main()` — CLI 与裁决输出。
  - `skills/workflow-verification/scripts/verify.py:cmd_save_baseline()` — S0 产物消费者。
  - `scripts/test_check_delivery.py` — 交付门测试入口。
- verification:
  - [ ] `python -m pytest scripts/test_check_delivery.py -q` 返回 0。
  - [ ] Git 成功、范围外 commit Diff、S1 变化分别得到预期结果。
  - [ ] SVN 有 revision 成功，缺 revision 或范围外 Diff 失败关闭。
  - [ ] 成功 stdout 不含「工作区干净」，而含固定 Scoped 结论。
- artifacts:
  - `skills/workflow-code-generation/scripts/check_delivery.py`
  - `scripts/test_check_delivery.py`
- 子任务:
  - [ ] 2.1：增加 Scoped Delivery CLI 与参数互斥校验。
  - [ ] 2.2：实现 Git commit Diff 和 S0/S1 比较。
  - [ ] 2.3：实现 SVN revision Diff 和 S0/S1 比较。
  - [ ] 2.4：输出受限报告措辞并补齐机器测试。

### 任务 3：[ ] Scoped Delivery 集成回归
- 状态：未开始
- 文件：`skills/workflow-verification/scripts/test_verify.py`（修改）、`scripts/test_check_delivery.py`（修改）
- depends_on: [Task 1, Task 2]
- review_profile: standard
- 文档映射：proposal.md 1.验收标准（全部）
- 说明：补齐跨 Verify 与 Delivery 的契约测试，覆盖 ignore 隔离、快照篡改、未跟踪树变化、默认绝对干净路径不回归与 Windows UTF-8 输出。
- context_files:
  - `skills/workflow-verification/scripts/test_verify.py` — S0 产物测试。
  - `scripts/test_check_delivery.py` — Scoped 交付行为测试。
  - `verify.config.json` — 现有项目机器验证入口。
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py scripts/test_check_delivery.py -q` 返回 0。
  - [ ] `python skills/workflow-verification/scripts/verify.py --help` 显示新增接口。
  - [ ] `python skills/workflow-code-generation/scripts/check_delivery.py --help` 显示 Scoped 接口。
- artifacts:
  - `skills/workflow-verification/scripts/test_verify.py`
  - `scripts/test_check_delivery.py`
- 子任务:
  - [ ] 3.1：补跨组件的 S0/S1 与 ignore 边界测试。
  - [ ] 3.2：补默认绝对干净和 Scoped 报告口径回归测试。
  - [ ] 3.3：运行目标测试集并记录结果。

### 任务 4：[ ] Workflow 与长期质量门契约同步
- 状态：未开始
- 文件：`skills/workflow-verification/SKILL.md`（修改）、`skills/workflow-code-generation/SKILL.md`（修改）、`openspec/specs/backend/framework/quality-gates/overview.md`（修改）、`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md`（修改）
- depends_on: [Task 3]
- review_profile: standard
- 文档映射：proposal.md 3、4、2.3、2.5
- 说明：写入 Git/SVN Scoped Delivery 适用条件、失败关闭、S0/S1 比较、报告禁语和与 `spec_drift` ignore 的隔离；文档以已完成实现和测试为准。
- context_files:
  - `skills/workflow-verification/SKILL.md` — 基线与 spec drift 合同。
  - `skills/workflow-code-generation/SKILL.md` — 交付门调用和报告格式。
  - `openspec/specs/backend/framework/quality-gates/overview.md` — 长期质量门知识。
  - `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` — Native Delivery 边界。
- verification:
  - [ ] `rg -n "Scoped Delivery|预存残留未变化|SVN" skills/workflow-verification/SKILL.md skills/workflow-code-generation/SKILL.md openspec/specs/backend` 有预期命中。
  - [ ] `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2033-scoped-delivery-residue-guard/tasks.md` 返回 0。
  - [ ] `git diff --check` 返回 0。
- artifacts:
  - 上述四份契约文档。
- 子任务:
  - [ ] 4.1：同步 Verify 的范围与 S0/S1 合同。
  - [ ] 4.2：同步 Delivery 的 CLI、成功措辞和失败口径。
  - [ ] 4.3：同步长期质量门和 Native Delivery 边界。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| 1. 问题与目标 | Task 1, Task 2, Task 3 | 独立 S0、范围与交付判定。 |
| 1. 非目标 | Task 1, Task 2, Task 4 | 读取范围、Trust 与 SVN 限制。 |
| 1. 验收标准 | Task 1, Task 2, Task 3 | 每项均有机器测试。 |
| 2.1-2.4 | Task 1, Task 2 | 组件、接口、数据模型实现。 |
| 2.5 | Task 1, Task 2, Task 4 | 显式模式、内容摘要、SVN 与 ignore 边界。 |
| 3-4 | Task 4 | 知识与运行口径同步。 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| Scoped Delivery 基线与范围合同 | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Pending | 无需索引变更 |
| Native Delivery 有界裁决 | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` | MODIFIED | Pending | 无需索引变更 |

## 知识冲突

- 结论：待核对。现有绝对干净合同与新的显式 Scoped Delivery 将并存，归档前须确认不存在静默替换。

## 实际 Diff 核对

- 核对状态：Pending。归档前记录实际 Diff、Change 和测试证据的核对命令与结论。
