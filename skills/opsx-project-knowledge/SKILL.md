---
name: opsx-project-knowledge
description: OpenSpec 项目知识沉淀规范。定义 openspec 目录结构、变更生命周期与归档约定。当需要创建新变更目录或询问「某类文档放哪里」时参考此 skill。
---

> 输出一行：`Using opsx-project-knowledge`

# OpenSpec 项目知识沉淀规范

## 加载时机

- 创建或更新 `openspec/changes/*/` 下任意文件时加载
- 功能交付、任务完成、准备归档变更时加载
- 用户询问变更目录结构、归档约定或文档应放在哪里时加载

## 目录结构约定

```
openspec/
├── changes/                         # 活跃变更（开发中）
│   └── <change-name>/               # 单次变更目录（动词-名词，如 add-dark-mode）
│       ├── proposal.md              # 为什么改、改什么（必选）
│       ├── tasks.md                 # 实现任务清单（必选）
│       ├── design.md                # 技术设计（可选，见触发条件）
│       └── specs/                   # 增量规范（必选）
│           └── [capability]/
│               └── spec.md          # ADDED / MODIFIED / REMOVED
└── changes/archive/                 # 已归档变更
    └── YYYY-MM-DD-<change-name>/    # 整目录归档，名称加日期前缀
```

> **不维护中央真相库**：本工作流只有 `changes/`（活跃）与 `changes/archive/`（已归档），没有顶层 `openspec/specs/` 汇总规范库——这是为适配「使用 OpenSpec、但不要中央真相库」的约束而做的有意裁剪。系统现状以代码为准。

---

## 各类文档的定位与职责

### 变更目录（`openspec/changes/<change-name>/`）

每次功能开发或较大改动对应一个变更目录：

| 文件 | 职责 | 是否必选 |
|------|------|---------|
| `proposal.md` | 为什么改、改什么：背景、目标、需求概览、备选方案 | 必选 |
| `tasks.md` | 分几步做，每步的完成条件是什么 | 必选 |
| `design.md` | 怎么做：组件设计、核心逻辑、测试计划、可观测性 | 可选（见触发条件） |
| `specs/<capability>/spec.md` | 增量规范：该 capability 的规范变更内容 | 必选 |

> 「是否必选」指变更归档前应具备：`tasks.md` 由 `opsx-code-generation` 阶段产出；`specs/` 在完整需求路径必选，Quick Draft 轻量路径可不含独立增量规范。

#### design.md 触发条件

满足以下任一条件时需创建 `design.md`：

- 涉及新模块或子系统的设计
- 接口或数据模型有破坏性变更
- 核心逻辑存在算法复杂度或并发安全问题
- 需要明确测试计划或可观测性方案

简单的 bug 修复、配置调整、文案变更不需要 `design.md`。

#### 生命周期与归档

变更的活跃 / 归档状态由**目录位置**表达，不维护单独的状态文件：

- **活跃**：目录在 `openspec/changes/<change-name>/` 下。
- **Quick Draft**：由 `proposal.md` 头部「状态」字段标注（仅快速设计路径使用）。
- **已归档**：执行 `/opsx-archive` 后，整个变更目录移动到 `openspec/changes/archive/YYYY-MM-DD-<change-name>/`。

```
openspec/changes/add-dark-mode/
    ↓ /opsx-archive
openspec/changes/archive/2026-06-21-add-dark-mode/
```

归档只移动目录，**不把增量规范合并到任何中央库**（无中央库）。

---

## 文档与代码的同步原则

| 变更类型 | 需要做的 |
|---------|--------------|
| 变更交付完成 | 执行 `/opsx-archive` 归档（移入 `archive/`） |
| 编码规范变更 | 对应 `std-*` skill 文件 |
| 工程流程变更 | 对应 `workflow-*` / `opsx-*` skill 文件 |

**文档债务**：如果代码已变更但 `proposal.md` / `specs/` 尚未更新，在 `tasks.md` 中创建一个「更新文档」任务，不要跳过。

---

## 与其他工作流的关系

| 工作流 | 产出 | 路径 |
|-------|------|------|
| `opsx-requirements-clarification` | `proposal.md` + `specs/*/spec.md` | `openspec/changes/<change-name>/` |
| `opsx-system-design` | `design.md` | 同上 |
| `opsx-quick-design` | `proposal.md`（Quick Draft） | 同上 |
| `opsx-code-generation` | `tasks.md` + 代码 | 同上 |
| `opsx-archive` | 整目录移动 | `openspec/changes/archive/YYYY-MM-DD-<change-name>/` |
| `self-refinement` | skill 文件更新 | `skills/` 目录下对应 skill |
