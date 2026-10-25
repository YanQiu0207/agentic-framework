# 实施任务清单

用户已批准设计与实施范围。依赖关系：Task 1 → Task 2。

### 任务 1：[x] 统一 Task 隔离并复制手动技能
- 状态：完成
- depends_on: []
- review_profile: standard
- context_files: skills/workflow-code-generation/SKILL.md、reference/execution-setup.md、reference/delegated-execution-guide.md、evaluation/trigger-cases.md
- verification: python scripts/lint_skill_graph.py；python -m pytest scripts/test_skill_slimming_contracts.py -q
- artifacts: 执行文档、skills/handoff/、skills/prototype/、commands/handoff.md、commands/prototype.md、长期合同
- 验收标准：旧串行例外移除，手动调用策略与相对引用完整。

### 任务 2：[x] 安装接线与集成验证
- 状态：完成
- depends_on: Task 1
- review_profile: standard
- context_files: scripts/install_agentic_framework.py、scripts/test_interview_installation.py、proposal.md
- verification: python -m pytest scripts/test_interview_installation.py scripts/test_skill_slimming_contracts.py scripts/test_lint_skill_graph.py -q
- artifacts: 安装集合、扩展的既有安装测试、验证记录
- 验收标准：两个 Profile、两个客户端可选择、安装、重装和卸载新入口；最终只读复核无阻塞项。

## 执行说明

按用户「文档变更敏捷快速」要求，本次直接使用当前独立 Worktree 修改文档，安装接线委派 Agent；不为本次文档任务递归建立任务 Worktree。新规则用于后续标准代码流程。
