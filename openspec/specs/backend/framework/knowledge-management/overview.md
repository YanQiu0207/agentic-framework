# 知识管理实现概览

source_ref: git:c5dd8c28a8111c05553a3b77e4613fd270db418d
source_paths:
    - skills/project-knowledge/SKILL.md
    - skills/project-init/SKILL.md
    - skills/bp-domain-modeling/SKILL.md
    - skills/bp-domain-modeling/reference/glossary-format.md
    - skills/bp-domain-modeling/reference/adr-format.md
    - openspec/specs/backend/engineering/tech/knowledge-management.md
generated_at: 2026-10-26

## 职责

知识管理实现由操作合同、初始化入口、迁移工具、公共库校验和交付门共同组成。长期语义以 [`knowledge-management.md`](../../engineering/tech/knowledge-management.md) 为准；本文件只定位当前实现。

## 实现入口

| 能力 | 当前入口 | 边界 |
| --- | --- | --- |
| 项目初始化 | `skills/project-init/SKILL.md` | 默认 Git 与项目内知识；高级初始化须启用 `knowledge-advanced`；不覆盖现有文件 |
| 读写与归档路由 | `skills/project-knowledge/SKILL.md` | 知识辅助理解，冲突显式报告，公共知识禁止自动写入 |
| Legacy 迁移规划 | `scripts/migrate_project_knowledge.py` | 只生成逐文件映射和引用清单，不复制、不删除、不覆盖 |
| 公共知识校验 | `scripts/validate_shared_knowledge.py` | 只读检查索引边界、元数据、私有链接和候选污染 |
| Change 知识门 | `scripts/validate_change.py` | 检查项目索引、代码派生元数据、Delta、冲突和归档同步 |
| 共享知识核对 | `scripts/knowledge_sync.py` | Delta 反推与知识同步表解析，Production 与 Tooling 共同消费（change 2040） |
| 来源新鲜度 | `workflow-verification/scripts/verify.py` | 对 `meta.yaml` 来源漂移输出非阻塞告警 |

项目内知识读取、冲突报告和归档属于 Core。SVN 初始化、外置正文、公共库接线及晋升需要 `knowledge-advanced`；普通 SVN 代码交付不受该初始化能力门限制。初始化先识别已有 Git／SVN 工作副本；发现 SVN 或状态未决时不得转而执行 `git init`。默认流程不主动询问外置存储或公共接线。

内部仍逐项检查知识影响；无命中只输出具体理由，命中只列命中项、目标路径与同步状态。机器 `--knowledge-impact` 字段及 `none` 理由不变；无 Change 的轻量 Native Delivery 只允许 `none`。

## 合同速查（2026-10-26 通读核对的导航性归纳，权威原文见各合同文件）

本节是对既有合同文件的定位性归纳，帮助快速找到权威原文；条款语义以链接文件为准，此处不复制完整规则。

### 位置与接线

- 位置是硬编码约定，不存在动态查询：项目知识固定逻辑入口 `<project>/openspec/`（`project-knowledge/SKILL.md` §2「工作流只使用逻辑入口」），外置模式下该入口是指向外部私有目录的链接，对消费方透明。工作流技能直接用相对路径（如 `workflow-requirements-clarification` 直接 `mkdir -p openspec/changes/...`）。
- 二次声明：`project-init` 第 8 步把「入口固定为 `openspec/index.md`」等规则写入项目 `AGENTS.md`。
- 公共知识库路径不是约定路径：接线时从 `~/.claude/CLAUDE.md`「跨项目共用知识库」读取并经用户确认，再追加进项目 `AGENTS.md`。
- 唯一的能力查询是 `knowledge-advanced` 包检查（`install_agentic_framework.py --show-packs`），查权限而非位置。
- 契约主从：`skills/project-knowledge/SKILL.md` 是操作合同权威；`openspec/specs/backend/engineering/tech/knowledge-management.md` 是方案记录（Active），其操作规则段落显式回指 SKILL.md。两者冲突时须按冲突报告流程展示双方证据。

### 目录结构

- 初始化最小骨架：`index.md`、`specs/index.md`、`changes/archive/`、`issues/index.md`；`business/`、`frontend/`、`backend/`、`common/` 按需创建，不为模板造空目录。
- 四目录是两条轴，不是业务包含实现：`business/` 是领域语义轴（与实现无关的「是什么」，人工维护）；`frontend/`、`backend/` 是实现轴（代码派生事实 + `meta.yaml` 版本元数据 + 人工 `custom/`）；`common/` 是共享契约轴（protocols、data-models、error-codes）。同一条知识选一个主位置，禁止复制多份正文。
- `business/` 文件分工：`glossary.md`（全项目唯一术语表，按业务上下文分节，同名概念不合并，格式见 `bp-domain-modeling/reference/glossary-format.md`）；`<domain>/overview.md`（概念职责、关系、边界）；`rules.md`（规则与不变量）；`flows.md`（跨模块流程）；`custom/` 三件套 `constraints.md`／`decisions.md`／`pitfalls.md`（§6.2，自动流程不可覆盖）。
- 读取路由：根索引 → `business/index.md` 定位共享领域模型 → 叠加当前 Change 已批准差异；按任务类型的路由表见 `project-knowledge/SKILL.md` §3.2，公共知识库仅 §3.3 五条件下查询。
- Change 目录含 `research.md`（追加式调研中间产物，随 Change 归档；`project-knowledge/SKILL.md` §2 目录树与 `knowledge-management.md` §5.5 均已列入，change 2059 对齐）。
- 公共库完整结构：`index.md`、`domains/`、`issues/`、`sources/`（允许跨项目消费的原始资料索引）、`changes/`（仅公共库自身治理）、`archives/`（整体退役主题，首版非日常重点）；`projects/` 已停止新增。
- 端内工程规范在 `specs/<端>/engineering/`（conventions、lib-usage、tech）；`engineering/tech/adr/` 是本仓库 ADR 现行落点，不再新建平行 ADR 目录（`adr-format.md`「本框架落点」）。

### 写入与退役语义

- 写入前置：每条知识按 `project-knowledge/SKILL.md` §5 唯一位置表归位；业务域、端或模块判断不了时不得猜目录，候选留当前 Change 待确认。
- 双轨更新（§7.1）：既有知识澄清（确认 + 授权 + 事实核实 + 无未决冲突）可直写共享位置并记录来源日期；未来业务变化走 Change Delta（`ADDED`/`MODIFIED`/`REMOVED`/`RENAMED`），归档验证后同步。用户确认含义不等于允许写入。
- 交付前强制做 §9 intent 沉淀检查；机器参数 `--knowledge-impact` 与理由字段见本文件「实现入口」。
- 退役/删除：操作合同见 `project-knowledge/SKILL.md` §7.3（change 2059 补全）——直写路径状态标记替代物理删除（glossary 行内标注、rules/flows/overview 状态行、`issues/` 头部状态行、`custom/` 沿用 §6.2 + decisions 沿用 adr-format Status 枚举），自动流程禁止物理删除，物理删除仅限用户明确授权；Change 路径删除沿用 Delta `REMOVED`。既有四种状态机制（ADR Status、公共库证据等级、`meta.yaml` status、`REMOVED`）与其衔接。
- 定位链（change 2059 补全）：`business/index.md` 职责为业务域清单 + glossary 分节-目录映射登记（`project-knowledge/SKILL.md` §3.4）；小项目不建空层级，映射写在 `specs/index.md` 对应条目旁；glossary 分节创建时同轮登记映射（`glossary-format.md` 结构规则）。

## 数据流

```text
项目任务
    → openspec/index.md 渐进路由
    → 活跃 Change 保存本次契约和未归档 Delta
    → 代码、测试与运行证据核实
    → 归档前同步长期 Specs / Issues / 索引
    → Change 移入 archive/

跨项目候选
    → 只留项目 Change 或交付报告
    → 查询 knowledge-advanced，失败或缺包即停止
    → 用户确认
    → 泛化、脱敏和边界检查
    → 公共库 domains/ 或 issues/
```

## 安全与失败边界

- `migrate_project_knowledge.py` 的输出声明 `mode: plan-only`，安全字段明确所有写入和删除能力均为 `False`（`scripts/migrate_project_knowledge.py:182-233`）。
- 公共校验器发现合同违规返回 `1`；读取、编码、遍历或根目录错误返回 `2`（`scripts/validate_shared_knowledge.py:218-253`）。
- 公共索引不得桥接项目私有正文；操作边界不是文件系统 ACL。
- 代码派生知识使用 `meta.yaml` 记录 `source_ref`、`source_paths` 和生成时间；`custom/` 不允许自动覆盖。

## Tooling 侧反自证核对（change 2040）

Tooling 的知识影响门不再只是「声明即算数」的计数：`check_delivery.py` 在声明 `hit` 且存在 `tasks.md` 时执行交叉核对——从 Change 的 `specs/` 反推应同步目标，与 tasks.md 的知识同步表比对。五类失败各自关闭：Delta 漏报、声明误报、目标路径不匹配、同步状态未完成、知识冲突节为空或占位。声明 `none` 时只做矛盾核对（有 Delta 却称无影响）。无 `specs/` 目录时退回同步目标存在性核对——只能证明「声明的目标存在」，不能证明「该同步的都同步了」，证据强度低于 Delta 反推，交付报告的核对模式行会体现该区分。解析逻辑由共享模块 `scripts/knowledge_sync.py` 承载，Production（OPSX042-048）与 Tooling 共同消费；这是 §3.2 条件 3 的部分举证。

## 主要验证证据

- `scripts/test_knowledge_management_e2e.py`：覆盖 Delta 同步、外置链接、知识冲突、公共候选和两个项目的隔离边界。
- `scripts/test_profile_contracts.py`：覆盖两个 Profile 共用 Change Artifact 和项目知识合同。
- `scripts/tests/test_validate_change.py`：覆盖项目索引、代码派生元数据和 Archive 知识同步门。
