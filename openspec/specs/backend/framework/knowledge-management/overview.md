# 知识管理实现概览

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
