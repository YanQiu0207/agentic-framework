# 实施任务清单

> 任务总数：4
> Code Review：PASS

## 执行图

```text
Task 1 ─┬→ Task 2 ─┐
        └→ Task 3 ─┼→ Task 4
```

### 任务 1：[completed] 修复迁移器兼容性、扫描性能和链接解析

- 状态：完成
- attempts：1
- control_stage：merge_success
- review_profile: standard
- context_files: `scripts/migrate_project_knowledge.py`、`scripts/test_migrate_project_knowledge.py`、`design.md`
- verification: Legacy 映射、引用等价和剪枝测试通过
- artifacts: `scripts/markdown_links.py`、`scripts/migrate_project_knowledge.py`、`scripts/test_migrate_project_knowledge.py`、`openspec/migration-plan.json`
- Review Profile: standard
- Task Review: PASS
- Review Evidence: Standard 自审，无 P0/P1。
- 依赖：无
- 文件：`scripts/markdown_links.py`、`scripts/migrate_project_knowledge.py`、`scripts/test_migrate_project_knowledge.py`、`openspec/migration-plan.json`
- 文档映射：`proposal.md` §3、`design.md` §2.1、`specs/backend/engineering/tech/knowledge-management.md` 要求 1 和修改要求 2
- 验收标准：
    - [x] 所有 Legacy 来源区域的目标映射测试通过。
    - [x] 引用扫描结果与修复前语义一致。
    - [x] 忽略目录和目录链接不会被递归扫描。
- 子任务：
    - [x] 1.1：修复 `relative_to` 兼容性和路径深度检查。
    - [x] 1.2：提升引用循环不变量并统一链接解析。
    - [x] 1.3：改用可剪枝且不跟随目录链接的 Markdown 遍历。

### 任务 2：[completed] 修复公共知识校验器错误语义和重复读取

- 状态：完成
- attempts：1
- control_stage：merge_success
- review_profile: standard
- context_files: `scripts/validate_shared_knowledge.py`、`scripts/test_validate_shared_knowledge.py`
- verification: 错误退出码、违规输出和单次读取测试通过
- artifacts: `scripts/validate_shared_knowledge.py`、`scripts/test_validate_shared_knowledge.py`
- Review Profile: standard
- Task Review: PASS
- Review Evidence: Standard 自审，无 P0/P1。
- 依赖：Task 1
- 文件：`scripts/validate_shared_knowledge.py`、`scripts/test_validate_shared_knowledge.py`
- 文档映射：`proposal.md` §3～4、`design.md` §1～2.1、`specs/backend/engineering/tech/knowledge-management.md` 要求 2
- 验收标准：
    - [x] 非 UTF-8、读取或遍历错误返回退出码 `2`。
    - [x] 合同违规仍返回退出码 `1` 并输出 `violation:`。
    - [x] 同一批公共条目每次校验只读盘一次。
- 子任务：
    - [x] 2.1：复用共享链接 Helper。
    - [x] 2.2：增加单次校验读取缓存和错误映射。
    - [x] 2.3：补充损坏编码和退出码测试。

### 任务 3：[completed] 补齐 Fast-Path 和来源新鲜度信任门

- 状态：完成
- attempts：1
- control_stage：merge_success
- review_profile: strict
- context_files: `skills/workflow-code-generation/scripts/check_delivery.py`、`skills/workflow-verification/scripts/verify.py`、`openspec/specs/backend/framework/meta.yaml`
- verification: Fast-Path 知识影响和来源新鲜度测试通过
- artifacts: `skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/test_check_delivery.py`、`skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/scripts/test_verify.py`
- Review Profile: strict
- Task Review: PASS
- Review Evidence: Strict 复审第 1 轮，无 P0/P1/P2。
- 依赖：Task 1
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/test_check_delivery.py`、`skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/scripts/test_verify.py`
- 文档映射：`proposal.md` §3～4、`design.md` §2.2～2.3、`specs/backend/engineering/tech/knowledge-management.md` 要求 3～4
- 验收标准：
    - [x] Fast-Path 缺少知识影响结论或无影响理由时失败。
    - [x] Standard Change 交付门保持兼容。
    - [x] 来源路径晚于 `source_ref` 时输出 `WARN` 且总判定不失败。
    - [x] 当前有效 `meta.yaml` 不产生误报。
- 子任务：
    - [x] 3.1：扩展 Fast-Path 交付门参数和测试。
    - [x] 3.2：实现 Git 来源新鲜度告警和测试。

### 任务 4：[completed] 校准操作契约、历史验收和端到端证据

- 状态：完成
- attempts：1
- control_stage：merge_success
- review_profile: strict
- context_files: `skills/project-knowledge/SKILL.md`、`docs/design-docs/knowledge-management/tasks.md`、`openspec/acceptance/2026-07-19-knowledge-management.md`、`scripts/test_knowledge_management_e2e.py`
- verification: 操作契约、历史验收、双项目公共索引边界、共享 Artifact Archive/Delta 和独立 Profile 合同测试通过
- artifacts: `skills/project-knowledge/SKILL.md`、`skills/workflow-code-generation/SKILL.md`、`docs/design-docs/knowledge-management/tasks.md`、`docs/migrations/project-knowledge.md`、`docs/migrations/shared-knowledge-base.md`、`docs/incidents/README.md`、`openspec/changes/archive/2026-07-19-unified-knowledge-management/tasks.md`、`openspec/acceptance/2026-07-19-knowledge-management.md`、`scripts/test_knowledge_management_e2e.py`
- Review Profile: strict
- Task Review: PASS
- Review Evidence: Strict 复审第 1 轮，无 P0/P1；P2 已同步修正。
- 依赖：Task 2、Task 3
- 文件：`skills/project-knowledge/SKILL.md`、`skills/workflow-code-generation/SKILL.md`、`docs/design-docs/knowledge-management/tasks.md`、`docs/migrations/project-knowledge.md`、`docs/migrations/shared-knowledge-base.md`、`docs/incidents/README.md`、`openspec/changes/archive/2026-07-19-unified-knowledge-management/tasks.md`、`openspec/acceptance/2026-07-19-knowledge-management.md`、`scripts/test_knowledge_management_e2e.py`
- 文档映射：`proposal.md` §4～5、`design.md` §1 和 §3、`specs/backend/engineering/tech/knowledge-management.md` 要求 5 和修改要求 1
- 验收标准：
    - [x] `meta.yaml` 和 `custom/` 文件清单存在唯一操作契约。
    - [x] 历史迁移状态表述与实际文件一致。
    - [x] 两项目私有正文不能经公共索引互相桥接。
    - [x] 共享 Standard Change Artifact 覆盖 Archive 与 Delta 同步；Profile 差异由独立合同测试覆盖。
    - [x] 全量测试、Skill 图和 Verification 通过。
- 子任务：
    - [x] 4.1：校准历史验收与公共边界表述。
    - [x] 4.2：补足共享 Artifact、Profile 合同和两项目公共索引边界测试。
    - [x] 4.3：更新 Shared Core 操作契约。

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §3 | Task 1～3 | 实现已确认的代码修复 |
| `proposal.md` §4 | Task 2～4 | 验证成功标准 |
| `design.md` §1 | Task 1～4 | 逐项处理 Finding |
| `design.md` §2 | Task 1～3 | 实现关键设计 |
| `design.md` §3 | Task 1、2、4 | 处理接受的 P2 |
| `spec.md` 新增要求和修改要求 | Task 1～4 | 实现知识管理 Delta |
| Delta 新增要求 | Task 1～4 | 落实新增合同 |

## 验证记录

- 构建命令：`python -m py_compile scripts/markdown_links.py scripts/migrate_project_knowledge.py scripts/validate_shared_knowledge.py skills/workflow-code-generation/scripts/check_delivery.py skills/workflow-verification/scripts/verify.py`，退出码 0。
- 测试命令：`python -m pytest scripts -q`，退出码 0；172 passed，17 skipped，39 subtests passed。
- `python scripts/lint_skill_graph.py`：errors=0，warnings=0。
- `python skills/workflow-verification/scripts/verify.py --baseline E:/github/agentic-engineering-framework/.verify/knowledge-review-fixes-baseline.json --diff-base bfc3bda`：PASS；测试数 189，基线 172；Spec Drift PASS。
- Task 3 Strict Review：首审发现 2 个 P1 和 2 个 P2；复审第 1 轮 PASS。
- Task 4 Strict Review：首审发现 3 个 P1 和 1 个 P2；复审第 1 轮无 P0/P1，遗留 P2 已同步修正。
- 最终集成 Strict Review：首审发现 5 个 P1 和 2 个 P2；复审第 1 轮新增 1 个 P1；复审第 2 轮 PASS，无 P0/P1/P2。
- `validate_change --phase delivery`：临时 Review 前快照 PASS。
- `validate_change --phase archive`：合法 Archive Target PASS。

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/engineering/tech/knowledge-management.md` | `openspec/specs/backend/engineering/tech/knowledge-management.md` | MODIFIED | Done | 无需更新，路径未变化 |

## 知识冲突

- 结论：无冲突。长期 Spec、操作 Skill、机器门禁和历史验收已按同一边界更新。

## 实际 Diff 核对

- 已核对实际 Diff、Change 和测试证据：PASS。实际 Diff 与 Task 1～4 的 artifacts 一致。
