---
module: spec-artifact-gates
vcs_ref: git:d5f427cef2fc7b941a4942d9b113355d41ec61fb
generated_at: 2026-09-21
track: structure
expires_hint: 涉及 verify.py / lint_spec.py / 模板文件的提交后即失效，需复核
---

# spec 产物门禁链（proposal / design / tasks ↔ verify / lint / delivery）

## 模块边界

本次变更涉及的三类文件共同构成「spec 产物的生成 → 机器验证」链路：

1. **生成侧（skills 产物模板）**
   - `skills/workflow-requirements-clarification/reference/proposal_template.md`：标准 proposal，章节 1~5（1~3 需求、4 知识影响、5 参考资料）。
   - `skills/workflow-system-design/reference/design_template.md`：design，**沿用旧单文件 spec 的全局章节号 4~9**（4 设计方案、5 备选、6 业界调研、7 测试计划、8 可观测性与运维、9 参考资料）。编号不重叠是有意设计：跨文件「文档映射：proposal.md / design.md / 章节 X.Y.Z」引用时无歧义。
   - `skills/workflow-quick-design/reference/quick-proposal-template.md`：Quick Draft（`### 问题/目标/非目标/验收标准` + `## 2. 设计方案`）。
   - 旧 `spec_template.md` / `quick-spec-template.md` 已弃用（文件头有弃用注释），仅作历史迁移读取。
2. **验证侧（workflow-verification/scripts/verify.py）**
   - spec drift 内置检查：`_is_spec_file` 判「规格类文件」，`_related_spec_files` 判「与改动代码机械相关」。
3. **lint 侧（workflow-code-generation/scripts/lint_spec.py）**
   - 章节完整性 + 占位对照（复制模板未填写会被拦）。
   - 消费方：仅 `check_delivery.py`（用 `parse_status` 查 `Archived`）。章节 lint（`lint()` / CLI）无 SKILL 接线，属备用工具。

## 接口契约

### verify.py 文件分类（2026-09-21 修复后口径）

- `_SPEC_FILE_NAMES`：`spec.md`、`ui-spec.md`、`tasks.md`、`proposal.md`、`design.md`（任意目录，按文件名命中）。
- 路径命中：`openspec/specs|issues/**/*.md`（长期知识）、`openspec/changes/**/*.md`（Delta 等其余产物）、ADR 目录下 `.md`。
- 安全护栏：规格类文件永不可被 `--ignore` / `ignore_paths` / 基线快照剔除（`refused_ignores`）。

### `_related_spec_files` 关联判定

统一规则：**规格类文件正文出现任一改动代码路径（原样或 posix 形式）即算相关**。tasks.md、proposal.md、design.md、Delta、长期知识、ADR 一视同仁；ADR 依赖正文引用代码路径（旧版 ADR 永不计入，是本次修复点之一）。

推论：标准流程交付时，tasks.md 的 `文件` / `artifacts` 字段写真实代码路径，是最稳的关联锚点。

### lint_spec.py phase 参数

| phase | 校验对象 | 章节 | 默认模板 |
| --- | --- | --- | --- |
| `design` / `code`（默认） | proposal.md | 1~3 | proposal_template.md |
| `design-code` | design.md | 4~9 | design_template.md |
| 状态为 `Quick Draft` 时 | Quick proposal | `### 问题/目标/整体方案/验收标准` | quick-proposal-template.md |

状态合法值：`Draft / In Review / Approved / Archived / Quick Draft`。占位判定：正文行与模板行（去 HTML 注释后 strip）相同即占位；`TODO/TBD/XXX/待补充/待填写/待定` 单独成行也占位。

## 数据流

```
需求澄清（proposal_template.md）
  → 系统设计（design_template.md，章节 4~9 延续编号）
  → 任务拆解（task_planning_guide.md：### 任务 N： + depends_on + 状态五值）
  → 编码（workflow-code-generation）
  → verify.py spec drift（_is_spec_file → _related_spec_files 正文关联）
  → lint_spec.py / lint_task_deps.py（章节、状态一致性）
  → check_delivery.py（spec 状态 Archived + tasks 三向一致 + verify/review 报告）
```

## 关键权衡

- design 章节号 4~9 延续而非重编：保跨文件引用无歧义，代价是单文件看「不从 1 开始」。已在 design_template.md 头部与 workflow-system-design SKILL 前置条件写明。
- spec drift 判相关是**机械判定**（字符串包含），不做语义理解；判不出时走 `--spec-drift-reason` 逃生口，而不是让 LLM 自证。
- lint_spec 的章节 lint 无 SKILL 强制接线（只有 check_delivery 消费 `parse_status`），是「可用工具」而非门禁——判断它是否该强制需先看是否误伤 N/A 章节。

## 本次修复（2026-09-21）对应关系

| 问题 | 修复 |
| --- | --- |
| verify.py 不认 proposal.md / design.md / Delta，标准流程产物救不了 spec drift | `_SPEC_FILE_NAMES` 扩容 + `openspec/changes/**/*.md` 纳入 + 关联判定统一为正文含代码路径 |
| lint_spec 模板指针指向已弃用 spec_template，拦「复制模板未填写」失效 | 指针切到 proposal_template / quick-proposal-template，新增 design-code phase（4~9 章） |
| design.md 编号从 4 起、与 proposal「参考资料」撞名 | 保留延续编号 + 模板/SKILL 补编号说明 + design §9 标注「（design）」与引用口径 |
| workflow-verification SKILL 文案仍写旧 spec.md | 文案全面对齐现行产物名 |
