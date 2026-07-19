# 知识管理实现概览

## 职责

知识管理实现由操作合同、初始化入口、迁移工具、公共库校验和交付门共同组成。长期语义以 [`knowledge-management.md`](../../engineering/tech/knowledge-management.md) 为准；本文件只定位当前实现。

## 实现入口

| 能力 | 当前入口 | 边界 |
| --- | --- | --- |
| 项目初始化 | `skills/project-init/SKILL.md` | 只补缺失骨架，不覆盖现有文件；项目知识存储与公共库接线分开确认 |
| 读写与归档路由 | `skills/project-knowledge/SKILL.md` | 知识辅助理解，冲突显式报告，公共知识禁止自动写入 |
| Legacy 迁移规划 | `scripts/migrate_project_knowledge.py` | 只生成逐文件映射和引用清单，不复制、不删除、不覆盖 |
| 公共知识校验 | `scripts/validate_shared_knowledge.py` | 只读检查索引边界、元数据、私有链接和候选污染 |
| Change 知识门 | `scripts/validate_change.py` | 检查项目索引、代码派生元数据、Delta、冲突和归档同步 |
| 来源新鲜度 | `workflow-verification/scripts/verify.py` | 对 `meta.yaml` 来源漂移输出非阻塞告警 |

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
    → 用户确认
    → 泛化、脱敏和边界检查
    → 公共库 domains/ 或 issues/
```

## 安全与失败边界

- `migrate_project_knowledge.py` 的输出声明 `mode: plan-only`，安全字段明确所有写入和删除能力均为 `False`（`scripts/migrate_project_knowledge.py:182-233`）。
- 公共校验器发现合同违规返回 `1`；读取、编码、遍历或根目录错误返回 `2`（`scripts/validate_shared_knowledge.py:218-253`）。
- 公共索引不得桥接项目私有正文；操作边界不是文件系统 ACL。
- 代码派生知识使用 `meta.yaml` 记录 `source_ref`、`source_paths` 和生成时间；`custom/` 不允许自动覆盖。

## 主要验证证据

- `scripts/test_knowledge_management_e2e.py`：覆盖 Delta 同步、外置链接、知识冲突、公共候选和两个项目的隔离边界。
- `scripts/test_profile_contracts.py`：覆盖两个 Profile 共用 Change Artifact 和项目知识合同。
- `scripts/tests/test_validate_change.py`：覆盖项目索引、代码派生元数据和 Archive 知识同步门。
