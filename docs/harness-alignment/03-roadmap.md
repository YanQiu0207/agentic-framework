# 改进路线图

> 输入：[02-gap-analysis.md](02-gap-analysis.md) 中排序后的四个 gap。
> 本文档为后续实施的轻量 spec；每项真正动手时，可在 `docs/design-docs/` 下展开为正式 spec / tasks。

## 总原则

1. **不破坏 Agent-Agnostic**：框架核心保持纯 Markdown；脚本只作为 Skill 的 L3 `scripts/` 资源，且语言中立、可选。
2. **最小足迹**：遵循 `CONTRIBUTING.md`——只写 AI 不知道的内容，改动对广泛项目有价值。
3. **配置驱动**：检查项 / 命令由具体项目填充，框架只提供运行器与规范。
4. **Spec-First**：本路线图先定稿，再照着实施。

---

## 改进 1：verify 脚本门禁 + 基线对比（gap 1 + 2）

### 动机
本框架缺少客观的「完成」判定，全靠 subagent 评审 + 测试，AI 可解释性执行、可拿「历史遗留」甩锅。

### 目标
提供一个语言中立、配置驱动的验证门禁：跑完产出结构化报告，并支持改动前后基线对比，只追究新增问题。「脚本通过」成为 `code-generation` 的硬性完成条件之一。

### 方案
新建 Skill `skills/workflow-verification/`：

- `SKILL.md`：门禁规范——何时跑、报告格式、基线对比语义、退出码约定、如何接入 `code-generation`。
- `scripts/verify.py`（Python 3，参考实现）：
  - 读 `verify.config.json`，顺序执行其中定义的 check。
  - 每个 check 字段：`name`、`type`（`exit_code` / `count` / `forbid_pattern`）、`command`、`baseline_aware`（是否参与基线对比）。
  - 三类 check 对应文章 A / B / C：`forbid_pattern`（静态规范，如禁止某语法 / 中文）、`exit_code`（编译 / 测试通过）、`count`（测试数量不减少、文件不超长）。
  - 两种模式：`--save-baseline <path>`（存基线）、默认模式（跑一遍 + 与基线 diff）。
  - 产出 `report.json`（结构化）+ 人类可读摘要；退出码：0 全过 / 非 0 有新增违规。
- `reference/verify.config.example.json`：含 A / B / C 三类示例（用通用命令演示，如 `grep`、`pytest`、`go build`）。

### 集成点（改 `skills/workflow-code-generation/SKILL.md`）
- 步骤 5 Phase 1 **实现前**：若项目存在 `verify.config.json`，先 `--save-baseline` 采集基线。
- Phase 2 review PASS **之后**、Phase 3 汇报**之前**：跑 verify 与基线对比；有新增违规 → 进修复循环；全绿才可汇报。
- Phase 3 完成报告附 verify 摘要。

### 涉及文件
- 新增：`skills/workflow-verification/SKILL.md`、`skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/reference/verify.config.example.json`
- 修改：`skills/workflow-code-generation/SKILL.md`（挂载门禁与基线）
- 可选：`agentic_engineering.md` 架构图补「Verification」反馈模块；新增 `commands/verification.md`

### 验收标准
- [ ] 给定一个含 `verify.config.json` 的样例项目，`verify.py` 能跑出 `report.json` 且退出码正确。
- [ ] 基线对比能区分「历史违规」与「本次新增」，只对新增 fail。
- [ ] `code-generation` 流程在 review PASS 后会触发门禁，未过不进汇报。
- [ ] 无 `verify.config.json` 时流程优雅跳过（不报错），保持对存量项目无侵入。

### Agent-Agnostic 说明
脚本是可选 L3 资源；不装 `verify.config.json` 的项目完全不受影响。Python 3 比绑定任一 Coding Agent 中立得多，符合框架定位。

---

## 改进 2：跨 feature 任务看板（gap 3）

### 动机
新需求进来时无项目级历史视图，易「新需求冲掉旧设计」。

### 目标
一份项目级任务总览，记录所有 feature 的状态、阶段、文档入口、交付结论；需求澄清前先读。

### 方案
- 在 `skills/project-knowledge/SKILL.md` 目录约定中新增 `docs/design-docs/TASKBOARD.md`（项目级，单文件）。
- 字段：feature 名 / 状态（对齐 spec 生命周期 Draft → … → Archived）/ 当前阶段 / spec 目录 / 一句话交付结论。
- 提供模板 `skills/project-knowledge/reference/taskboard_template.md`。
- 维护责任：
  - `workflow-requirements-clarification` Step 0 / 1：**先读 TASKBOARD**，判断是否旧需求延续、有无类似历史。
  - `workflow-code-generation` 任务完成 / spec 归档时：更新 TASKBOARD 对应行。

### 涉及文件
- 修改：`skills/project-knowledge/SKILL.md`、`skills/workflow-requirements-clarification/SKILL.md`
- 新增：`skills/project-knowledge/reference/taskboard_template.md`

### 验收标准
- [ ] `project-knowledge` 明确 TASKBOARD 的位置、字段、维护责任。
- [ ] `requirements-clarification` 在澄清前会读 TASKBOARD（流程中有显式步骤）。
- [ ] 交付 / 归档时有更新 TASKBOARD 的指令。
- [ ] 纯 Markdown，无新依赖。

### Agent-Agnostic 说明
纯文档约定，零平台依赖。

---

## 改进 3：dev-map 细粒度化（gap 4）

### 动机
`overview.md` 偏架构级，缺代码级落点导航；AI 易重复造轮子。

### 目标
提供「改代码前先查」的开发导航：功能落点、影响链路、既有标准写法；由动代码的流程顺手维护。

### 方案
- 在 `skills/project-knowledge/SKILL.md` 新增 dev-map 文档约定：`docs/architecture/dev-map.md`（或按子系统拆分）。
- 内容：功能 → 落点文件、配置定义位置、模块改动影响链路、项目既有写法 / 惯例。
- 提供模板 `skills/project-knowledge/reference/dev-map_template.md`。
- 维护责任（谁动代码谁更新）：
  - `workflow-code-generation` 步骤 1 / 4：改码前查 dev-map 定位落点。
  - 任务完成且涉及新模块 / 落点变化时：更新 dev-map（与现有「文档同步任务」机制一致，`skills/project-knowledge/SKILL.md:90`）。

### 涉及文件
- 修改：`skills/project-knowledge/SKILL.md`、`skills/workflow-code-generation/SKILL.md`
- 新增：`skills/project-knowledge/reference/dev-map_template.md`

### 验收标准
- [ ] `project-knowledge` 明确 dev-map 的位置、内容、与 `overview.md` 的分工（overview 偏架构、dev-map 偏代码落点）。
- [ ] `code-generation` 改码前有「查 dev-map」步骤。
- [ ] 落点变化时有更新 dev-map 的指令。

### Agent-Agnostic 说明
纯文档约定，零平台依赖。

---

## 执行顺序与检查点

1. 先做改进 1（价值最高、最能补「反馈」短板）；脚本与集成各自可独立验收。
2. 再做改进 2、3（纯文档，互不依赖，可并行）。
3. 每个改进完成后，按 `CONTRIBUTING.md` 附「问题证据 + 改进证据」。

> 注：本框架另有一套平行的 `opsx-*`（OpenSpec）工作流，本路线图只覆盖 `workflow-*` 主线。如需同步到 opsx，另开条目。
