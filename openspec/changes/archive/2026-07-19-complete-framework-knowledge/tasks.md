# 实施任务清单

> 任务总数：5

## 执行图

```text
Task 1 → Task 2 → Task 3 → Task 4 → Task 5
```

### 任务 1：[completed] 建立源码证据图

- 状态：完成
- 依赖：无
- 文件：核心 Skills、Agents、脚本、配置和测试
- 验收标准：
    - [x] 五条核心链路均记录入口、主要流转、产物、失败边界和测试证据。
    - [x] 关键事实能够回到源码路径和 Git 来源版本。

### 任务 2：[completed] 形成知识缺口矩阵

- 状态：完成
- 依赖：Task 1
- 文件：`openspec/`、`README.md`、`docs/`
- 验收标准：
    - [x] 区分完整、索引遗漏、历史限定、模块知识缺失和重复内容。
    - [x] 最终写入项均能追溯到已确认缺口。

### 任务 3：[completed] 补齐架构和模块长期知识

- 状态：完成
- 依赖：Task 2
- 文件：`openspec/specs/`
- 验收标准：
    - [x] 复用现有框架总体合同，通过根索引增加架构与模块路由，避免新增近义总览。
    - [x] 只为确认缺失的稳定核心模块增加最小知识。
    - [x] `meta.yaml` 记录来源路径、版本、生成日期和状态。

### 任务 4：[completed] 修复项目知识索引

- 状态：完成
- 依赖：Task 3
- 文件：`openspec/index.md`、`openspec/specs/index.md`、`openspec/changes/archive/index.md`
- 验收标准：
    - [x] 长期 Specs、ADR 和历史 Change 均可从索引访问。
    - [x] 索引不复制正文，不把历史记录表述为当前合同。

### 任务 5：[completed] 验证、Review 和归档

- 状态：完成
- 依赖：Task 4
- 验收标准：
    - [x] `git diff --check` 通过。
    - [x] Skill 图和全量测试通过。
    - [x] 完成知识同步、实际 Diff 核对和 intent 沉淀检查。
    - [x] Change 归档并更新历史索引。

## 验证记录

- 变更 Markdown 链接检查：11 个文件，0 个断链。
- `python scripts/lint_skill_graph.py`：`errors=0`，`warnings=0`。
- `python -m pytest scripts -q`：196 项通过，17 项跳过，另有 59 项 Subtests 通过。
- `python skills/workflow-verification/scripts/verify.py --report .verify/complete-framework-knowledge-report.json --diff-base HEAD`：PASS。
- `git diff --check`：PASS。
- 索引一致性检查：8 个历史 Change 目录全部进入 Archive 索引。
- 文档自审：未发现新增断链、无来源事实、重复总览或历史 Change 冒充当前合同。

## 知识同步

| 知识影响 | 长期目标 | 状态 |
| --- | --- | --- |
| Tooling 控制流实现入口 | `specs/backend/framework/workflow-control/overview.md` | Done |
| 质量门实现入口 | `specs/backend/framework/quality-gates/overview.md` | Done |
| 知识管理实现入口 | `specs/backend/framework/knowledge-management/overview.md` | Done |
| Telemetry 实现入口 | `specs/backend/framework/session-telemetry/overview.md` | Done |
| 双 Profile 安装合同漂移 | `specs/backend/engineering/tech/framework-unification.md` | Done |
| 根索引、Specs 索引和 Archive 索引 | 对应 `index.md` | Done |

## 知识冲突

- 已解决：`project-init` 从旧 Tooling Pack 表述校准为两个 Profile 的 Shared Core。
- 已解决：Manifest 从旧受管文件哈希表述校准为 Schema 2 受管链接与 Registry。
- 未发现其他需要阻止归档的知识与代码冲突。

## 实际 Diff 核对

- 实际改动仅位于 `openspec/`。
- 未修改代码、测试、Skills、Commands、Agents 或运行配置。
- 新增长期知识与 `meta.yaml` 的来源路径一致。

## 交付前 intent 沉淀检查

- 不可逆或高影响架构决策：未命中。
- 放弃重要方案：命中 → 已在 `design.md` 记录不新增近义架构总览，复用现有总体合同。
- 新增红线约束：未命中。
- 已验证故障根因：未命中。
- 跨项目知识候选：未命中。
- 普通变更：命中 → 文档导航和来源知识补齐，无代码行为影响。
