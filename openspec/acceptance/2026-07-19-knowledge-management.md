# 统一知识管理真实验收记录

**日期**：2026-07-19
**项目**：`agentic-engineering-framework`

## 结论

本轮在当前框架仓库和真实跨项目公共知识库上完成了目录迁移、边界治理和机器验证。自动化 E2E 继续使用临时目录隔离破坏性动作；本文件记录真实仓库证据，不把合成测试描述为真实生产流量。

## 六类真实问题验收

### 1. 查询项目术语和规则

- 问题：「Production 与 Tooling 的 Artifact 和项目知识能力有什么关系？」
- 读取路径：`openspec/index.md` → `openspec/specs/index.md` → `backend/engineering/tech/framework-unification.md` 与 `knowledge-management.md`。
- 项目规则：两个 Profile 统一 `openspec/` Artifact 和知识生命周期，但保留独立审批、Review、DAG、Worktree 与恢复策略；知识只辅助理解。
- 代码核对：`scripts/install_agentic_framework.py` 的 `CORE_SKILLS` 同时包含 `project-init`、`project-knowledge`，`TOOLING_ONLY_PACKS` 只包含 `frontend`。
- 结果：知识规则与当前安装器一致。

### 2. 查询模块接口、依赖和人工约束

- 问题：「框架安装器有哪些 CLI 入口、依赖和不可破坏约束？」
- 读取路径：`openspec/specs/backend/framework/install-agentic-framework/interfaces.md`、`dependencies.md`、`custom/constraints.md`。
- 代码核对：`scripts/install_agentic_framework.py:parse_args()` 定义 Profile、Pack、切换、刷新和卸载参数；安装集合与 Manifest/Registry 逻辑由同文件实现。
- 新鲜度证据：`openspec/specs/backend/framework/meta.yaml` 记录 `source_ref`、`source_paths` 和 `generated_at`。
- 结果：接口、标准库依赖和 Shared Core 约束均能定向定位，人工约束没有写入自动生成文件。

### 3. 使用历史 Issue 辅助核验

- 问题：「疑似废弃的未跟踪方案能否直接删除？」
- 读取路径：`openspec/issues/index.md` → `issues/incidents/2026-07-19-untracked-plan-deletion.md`。
- 代码与版本证据：`scripts/migrate_project_knowledge.py` 的安全合同明确 `writes_source=false`、`deletes_files=false`、`apply_supported=false`；`git log -- docs/design-docs/framework/dual-track-merge/spec.md` 显示恢复后的文件已进入提交 `046562b`。
- 结果：历史 Issue 的「先查来源、保留备份、禁止未授权永久删除」与当前迁移工具行为一致。

### 4. 从 Change Delta 更新长期 Specs

- Change：`openspec/changes/archive/2026-07-19-accept-knowledge-routing/`。
- Delta：`specs/backend/framework/install-agentic-framework/custom/constraints.md`。
- 长期目标：`openspec/specs/backend/framework/install-agentic-framework/custom/constraints.md`。
- 实际核对：Delta、长期目标、安装器 `CORE_SKILLS` 和 Profile 合同测试一致。
- Archive 门禁：`validate_change.py --phase archive` 返回 `ok: true` 后，Change 才移入 Archive。
- 结果：真实项目完成一次镜像 Delta、长期同步、索引更新和 Archive。

### 5. 发现知识与代码冲突

- 知识文件：`docs/tooling/09-personal-knowledge-base-plan.md` 历史快照。
- 知识结论：项目知识入口仍是 `docs/`，公共根索引包含 `projects/` 项目指针。
- 当前证据：`skills/project-init/SKILL.md` 使用项目 `openspec/`；公共库提交 `ca43f6f` 已移除 `projects/` 日常入口；两个公共校验器为 0 违规。
- 版本与状态：历史文件已标记为被当前统一方案取代，属于 Archive 证据，不代表当前状态。
- 结果：显式报告冲突后，根据文件状态和当前代码确认是历史知识过期；没有把它误报为代码缺陷，也没有静默覆盖历史正文。

### 6. 经确认晋升公共知识

- 项目候选：知识与代码冲突时展示双方证据和不确定性，禁止静默选择。
- 确认依据：用户批准统一知识管理 Spec 与 Task 7、Task 9，并要求执行到全部完成。
- 泛化处理：移除当前项目路径和内部实现细节，补充适用范围、不适用范围和 `provisional` 证据等级。
- 公共目标：`E:/work/shared-knowledge-base/domains/agentic-engineering/knowledge-code-conflict-handling.md`。
- 验证：公共库自身 Lint 和框架只读校验器均为 0 违规；公共索引不链接当前项目私有正文。
- 独立提交：`92989d9`（`docs: 晋升知识冲突处理机制`）。
- 结果：完成一次真实的「项目候选 → 用户批准 → 泛化 → 公共条目 → 索引与提交」闭环。

## 项目知识库

- 当前仓库已建立 `openspec/index.md`、`openspec/specs/index.md` 和 `openspec/issues/index.md`。
- 双 Profile 与知识管理当前合同已迁入 `openspec/specs/backend/engineering/tech/`。
- 5 组历史设计产物已复制到 `openspec/changes/archive/`；已迁移的 `docs/design-docs/`、`docs/adr/` 和 `docs/incidents/` 均由目录级 `README.md` 标记 `Superseded`、停止写入并指向当前入口，不要求逐文件改写原历史状态。
- ADR 002 已复制到长期 Specs；迁移未删除、移动或覆盖旧文件。
- Tooling 与 Production 的新 Artifact 都使用 `proposal.md`、`design.md`、`specs/` 和 `tasks.md`；Profile 合同测试锁定该边界。

## 真实公共知识库问题

真实仓库 `E:/work/shared-knowledge-base` 原有 11 项违规：根索引仍暴露 `projects/` 两次，9 个知识条目缺少统一 frontmatter。

本轮完成：

- 移除 `projects/` 日常索引入口，并把 `changes/` 收紧为公共库自身治理。
- 为 9 个条目补充 `scope`、状态、来源版本、适用范围和不适用范围。
- 将 `projects/` 标记为停用，但不删除目录或未跟踪内容。
- 更新公共库自身 `lint_kb.py` 的字段和作用域合同。

验证结果：

```text
python scripts/lint_kb.py
checked root=E:\work\shared-knowledge-base | violations=0

python scripts/validate_shared_knowledge.py --root E:/work/shared-knowledge-base
checked root=E:\work\shared-knowledge-base | violations=0 | mode=read-only
```

公共库独立提交：`ca43f6f`（`feat: 收紧跨项目知识库边界`）。

## 知识与代码冲突

`scripts/test_knowledge_management_e2e.py` 使用未解决的知识与代码矛盾验证 Archive 门禁，确定性返回 `OPSX047`。`project-knowledge` 要求报告知识文件、知识结论、代码证据、版本和不确定性，禁止静默覆盖任意一方。

## 自动化回归

- 全量 `pytest scripts -q`：155 passed，17 skipped，39 subtests passed。
- E2E：覆盖共享 Standard Change Artifact 的 Archive/Delta、外置链接、冲突阻断、双项目公共索引边界和确认后条目校验。Production 与 Tooling Profile 的独立边界由 `scripts/test_profile_contracts.py` 验证，Tooling 控制流由 `scripts/test_workflow_control.py` 验证，不由共享 Artifact 测试推断。
- 私有边界验收仅证明公共索引及其 Validator 不会桥接两个项目的私有正文。Agent 主动检索范围另由 `project-knowledge` 人工合同约束；这些机制都不是文件系统 ACL，有保密需求时仍需独立的权限或执行环境隔离。
- Windows 无目录符号链接权限时，外置链接用例条件跳过；`project-init` 合同要求实际初始化失败闭合，不得静默复制降级。

## 未扩大声明

- 本记录证明当前两个真实仓库的结构、迁移和门禁闭环，不代表已经在真实生产业务流量中运行。
- 公共知识条目目前为 `provisional`，不能默认当作已验证建议。
