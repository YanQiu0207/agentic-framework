# 2060：SVN 本地验证与本地目录排除

- 执行方式：Native Delivery。
- Verify 配置：已有 `verify.config.json`，保持既有检查及 `ignore_paths` 不变。
- 基准：`66a66ba436b8b214e067c97a5c175b02794859a4`。
- 基线：`.agentic-framework/verify/2060-baseline.json`，已在改码前采集。
- 批准：用户已确认方案及工单号，按批准范围执行。

## 依赖关系

Task 1 → Task 2

## 变更影响概览

| 文件 | 变更 | 任务 |
| --- | --- | --- |
| `scripts/vcs.py`、`scripts/native_subject.py` | 本地主体及目录剪枝 | Task 1 |
| `skills/workflow-verification/scripts/verify.py` | 本地知识来源检查及配置接线 | Task 1 |
| `scripts/test_native_subject.py`、`scripts/test_vcs.py`、`skills/workflow-verification/scripts/test_verify.py` | 回归保护 | Task 1 |
| `skills/workflow-verification/reference/config-guide.md`、`spec-drift-and-scope.md` | 使用说明 | Task 2 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 长期合同 | Task 2 |

## 任务列表

### 任务 1：[x] 实现本地捕获与目录排除
- 状态：完成
- attempts：0
- control_stage：completed
- depends_on: []
- review_profile: strict
- 文档映射：proposal.md §1、§2
- 文件：`scripts/vcs.py`、`scripts/native_subject.py`、`skills/workflow-verification/scripts/verify.py` 及对应测试。
- context_files:
    - `scripts/native_subject.py`：配置策略、显式输入与内容读取。
    - `scripts/vcs.py`：SVN 本地节点、捕获及远程交付验收。
    - `skills/workflow-verification/scripts/verify.py`：知识来源及主体接线。
    - `scripts/test_native_subject.py`、`scripts/test_vcs.py`、`skills/workflow-verification/scripts/test_verify.py`：真实仓库及边界测试。
- verification:
    - [x] SVN 离线捕获、删除节点、排除剪枝及已版本化／显式输入保护测试通过。
    - [x] 配置非法、本地知识来源边界及 Git 回归通过。
    - [x] 正式完整 Verify 通过并保留报告。
- artifacts:
    - 上述实现及测试文件。

### 任务 2：[ ] 集成验证与合同同步
- 状态：进行中
- attempts：0
- control_stage：running
- depends_on: Task 1
- review_profile: strict
- 文档映射：proposal.md §3、§4
- 文件：配置指南、范围指南及质量门长期知识。
- context_files:
    - `skills/workflow-verification/reference/config-guide.md`。
    - `skills/workflow-verification/reference/spec-drift-and-scope.md`。
    - `openspec/specs/backend/framework/quality-gates/overview.md`。
    - Task 1 的实现及回归证据。
- verification:
    - [ ] 使用说明与真实实现一致，中文 Markdown 按 md-zh 自检。
    - [ ] 集成完整 Verify 通过。
    - [ ] `git diff --check` 及任务依赖校验通过，交付级 Review 和交付门由主会话随后执行。
- artifacts:
    - 更新后的指南、长期知识及验证／审查报告。

## 文档覆盖映射

| 章节 | 任务 |
| --- | --- |
| proposal.md §1、§2 | Task 1 |
| proposal.md §3、§4 | Task 2 |

## 知识同步

质量门长期合同及 Verify 配置／范围指南需同步，当前 Pending。

## 知识冲突

现有指南声称核验 SVN revision 存在；本次经用户批准改为本地新鲜度核对，实施后同步更新，不把旧声明继续当作当前事实。
