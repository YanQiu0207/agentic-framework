# 单仓库双 Profile 合并任务

**状态**：Completed

### 任务 1：方案裁决与合同冻结

- depends_on：无
- review_profile：strict
- context_files：`spec.md`、`../framework/dual-track-merge/spec.md`
- verification：两份方案均保留；胜出方案明确吸收项与拒绝项
- artifacts：两份 `spec.md` 的状态和对比结论
- 文件：`docs/design-docs/framework-unification/spec.md`、`docs/design-docs/framework/dual-track-merge/spec.md`
- 状态：完成

### 任务 2：合并 Tooling 资产与共享 Review

- depends_on：任务 1
- review_profile：strict
- context_files：两个仓库的 `skills/`、`agents/`、`commands/`
- verification：不存在 `bp-cola-ddd`、`project-knowledge`、`opsx-project-knowledge`；两轨入口均存在
- artifacts：合并后的 Skills、Agents、Commands
- 文件：`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-review/SKILL.md`、`agents/comprehensive-reviewer.md`
- 状态：完成

### 任务 3：实现 Profile 安装隔离

- depends_on：任务 2
- review_profile：strict
- context_files：`scripts/install_agentic_framework.py`、安装器测试
- verification：Production 与 Tooling 临时安装互不污染；Manifest 可验证受管文件
- artifacts：安装器、Manifest、回归测试
- 文件：`scripts/install_agentic_framework.py`、`scripts/test_install_agentic_framework.py`
- 状态：完成

### 任务 4：统一 Review 和 Verification 合同

- depends_on：任务 2
- review_profile：strict
- context_files：两轨代码生成、测试和 Review Skills
- verification：Production 使用风险分档 Task Review 和最终五维集成 Review；Tooling 每个 Run 只有一次首轮 Review
- artifacts：更新后的工作流合同和 Production 确定性校验
- 文件：`skills/opsx-code-generation/SKILL.md`、`scripts/validate_change.py`
- 状态：完成

### 任务 5：文档、图检查与整体验收

- depends_on：任务 3、任务 4
- review_profile：strict
- context_files：`README.md`、`CONTRIBUTING.md`、`scripts/lint_skill_graph.py`
- verification：全量测试、Skill 图、Profile 安装测试通过；Production 只执行一次最终五维集成 Review，不重复启动整体初审
- artifacts：README 路由、治理规则、验收记录
- 文件：`README.md`、`CONTRIBUTING.md`
- 验收记录：使用 `pytest -q` 共收集 131 项测试，129 项通过，2 项 Symlink 权限相关测试跳过，另有 28 个 Subtest 通过；Skill 图、Task 图、Spec Lint、Black 26.5.1 和双 Profile 临时安装均通过；五维 Review、定向复审和 Review Critic 均为 PASS
- 状态：完成

### 任务 6：非破坏性退役旧目录

- depends_on：任务 5
- review_profile：standard
- context_files：旧 Tooling 仓库 `README.md`、`MIGRATION.md`
- verification：旧目录明确指向主仓库且停止独立演进；历史实现仍可恢复
- artifacts：迁移提示和回退边界
- 文件：`E:/work/my-ai-resource/agentic-framework/README.md`、`E:/work/my-ai-resource/agentic-framework/MIGRATION.md`
- 验收记录：旧目录已明确停止独立演进并指向主仓库；历史文件未删除
- 状态：完成

### 任务 7：误删事故复盘

- depends_on：任务 6
- review_profile：standard
- context_files：恢复后的双轨方案、Claude Code 会话恢复证据
- verification：复盘包含影响、根因、恢复证据、预防步骤和待确认的持久化规则
- artifacts：事故复盘文档
- 文件：`docs/incidents/2026-07-19-untracked-plan-deletion.md`
- 状态：完成
