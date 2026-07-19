# 完善框架项目知识设计

## 1. 方法

采用「源码证据图 → 知识缺口矩阵 → 最小长期知识」三步法：

1. 从用户入口沿 Skill、Agent、脚本和测试向下追踪核心链路。
2. 将当前 `openspec/` 条目分类为完整、索引遗漏、历史限定、缺少模块知识或重复。
3. 只为稳定且高价值的缺口增加长期知识；其他探索结果保留在本 Change。

## 2. 探索范围

| 链路 | 主要入口 | 重点 |
| --- | --- | --- |
| 安装与分发 | `scripts/install_agentic_framework.py` | Profile、Pack、链接、Manifest、Registry |
| Tooling 编排 | `skills/workflow-code-generation/` | DAG、Worktree、控制状态、交付门 |
| Production 生命周期 | `skills/opsx-*`、`scripts/validate_change.py` | Artifact、阶段门、归档 |
| Review 与 Verification | `skills/workflow-code-review/`、`skills/workflow-verification/`、`agents/` | Review 分级、独立角色、机器验证 |
| 知识与 Telemetry | `skills/project-*`、知识脚本、`scripts/analyze_session_metrics.py` | 知识路由、迁移、公共校验、会话指标 |

## 3. 写入策略

- 架构级稳定关系写入 `openspec/specs/backend/engineering/tech/framework-architecture.md`。
- 模块事实写入 `openspec/specs/backend/framework/<module>/overview.md`。
- 代码来源统一登记到 `openspec/specs/backend/framework/meta.yaml`。
- 人工约束继续保留在现有 `custom/`，不自动覆盖。
- 索引只建立导航，不复制正文。

## 4. 证据规则

- 当前行为优先使用源码、测试和配置核实。
- `source_ref` 使用对应来源路径最近一次变更的 Git Commit，而不是机械使用当前 HEAD。
- 历史 Change 只用于解释决策背景，不用于证明当前行为。
- 无法确认的关系标记为未知，不写入长期 Specs。

## 5. 知识缺口矩阵

| 区域 | 当前状态 | 证据 | 处理 |
| --- | --- | --- | --- |
| 框架总体架构 | 已有完整长期合同 | `framework-unification.md` 已覆盖双 Profile、Shared Core、Review 和 Verification | 不新增近义架构文件，只增强根索引路由 |
| 安装器 | 模块知识完整 | 已有 `overview.md`、`interfaces.md`、`dependencies.md` 和 `custom/constraints.md` | 保留，修正总体合同中的旧复制式表述 |
| Tooling 控制流 | 只有总体合同，缺少模块入口 | `workflow_control.py`、交付门和测试已有稳定边界 | 新增最小模块概览和来源元数据 |
| 质量门 | 有 ADR 和总体合同，缺少当前实现入口图 | Production、Tooling、Review、Verification 分散在多个 Skill 和脚本 | 新增统一模块概览；保留两个 Profile 的独立策略 |
| 知识管理 | 长期操作合同完整，缺少工具实现入口 | 初始化、迁移、公共校验和来源告警分散 | 新增最小模块概览，不复制操作合同 |
| Telemetry | 只有 `docs/tooling/` 设计文档，长期 Specs 无入口 | 脚本和测试已稳定，且属于可选 Pack | 新增模块概览和来源元数据 |
| 长期 Specs 索引 | 漏项 | ADR 003 已存在但未进入索引 | 补索引 |
| Archive 索引 | 漏项 | `2026-07-19-knowledge-management-review-fixes/` 已存在但未列出 | 补索引 |

## 6. 已确认知识与代码冲突

### 6.1 `project-init` 归属

- 知识文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- 知识结论：Packs 表仍将 `project-init` 标为 Tooling Pack。
- 当前证据：`scripts/install_agentic_framework.py:25-41` 将 `project-init` 和 `project-knowledge` 放入 `CORE_SKILLS`；`scripts/install_agentic_framework.py:82-98` 只为旧命令保留兼容 Pack 选择器。
- 处理：更新长期合同，明确它属于两个 Profile 的 Shared Core。

### 6.2 Manifest 资产模型

- 知识文件：`openspec/specs/backend/engineering/tech/framework-unification.md`
- 知识结论：Manifest 记录受管文件哈希，重装精确覆盖复制文件。
- 当前证据：`scripts/install_agentic_framework.py:823-838` 的 Schema 2 Manifest 记录链接路径、来源和类型；安装器校验并重建受管链接。
- 处理：更新为链接式 Manifest 与用户级 Registry 的当前合同。
