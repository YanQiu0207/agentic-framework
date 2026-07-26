# Proposal：退役 opsx-* 并行执行编排

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：opsx-orchestration-retirement
**状态**：Draft

---

## 1. 问题

目标模型的第 4 步：

> 最后逐步淘汰并行的 `opsx-*` 执行编排，避免两套事实来源。

当前仓库有两套 Skill／Command 入口：

```
commands/opsx-archive.md          skills/opsx-archive
commands/opsx-code-generation.md  skills/opsx-code-generation
commands/opsx-quick-design.md     skills/opsx-quick-design
commands/opsx-requirements-clarification.md  skills/opsx-requirements-clarification
commands/opsx-system-design.md    skills/opsx-system-design
commands/opsx-test-generation.md  skills/opsx-test-generation
```

这是 Production 的 `opsx-*` 生命周期入口。它们与 Tooling 的 `workflow-*` 入口并存。

`framework-unification.md` 的两条已立约束直接相关：

| 约束 | 内容 | 位置 |
| --- | --- | --- |
| 不同时安装 | 「在目标项目中默认同时安装两套生命周期入口」被明确不采用 | §1（`:28`） |
| 目录不合并 | 「把两个 Skill 目录直接合并」被放弃，因生命周期触发和安装语义竞争 | §19.3（`:667-672`） |

## 2. 为什么这是最后一步

退役 `opsx-*` 只有在它的全部职责都被新结构承载后才安全。这意味着：

- 任务执行链已统一（change 2043）。
- 写状态路径已统一（change 2044）。
- Production 的治理语义已由叠加门承载（change 2043）。
- 降级等价与治理强度判据都已通过（change 2043）。

**缺一不可。** 提前退役会删掉仍被依赖的入口。

### 2.1 退役 ≠ 合并，也 ≠ 删除语义

§19.3 放弃的是「把两个 Skill 目录直接合并」——理由是生命周期触发和安装语义竞争。本 Change **不**做目录合并。

退役的含义是：任务不再经 `opsx-*` 执行编排推进，Production 的治理语义由叠加门承载。`opsx-*` 中**仍有价值的非编排职责**（例如需求澄清、系统设计、测试生成的方法论文档）需要单独判定去向，不能跟着编排一起删。

这是本 Change 最需要小心的一点：`opsx-*` 不只有「执行编排」，还有方法论内容。退役编排，保留或迁移方法论。

## 3. 目标

1. `opsx-*` 的执行编排职责退役，任务不再经它推进。
2. Production 治理语义全部由叠加门承载，无残留依赖 `opsx-*`。
3. `opsx-*` 中的方法论内容逐项判定去向：迁移、保留为参考、或删除。
4. 安装器白名单移除 `opsx-*`，且不影响 Tooling 安装。
5. 无活跃引用残留：没有任何 Skill、Command、文档或脚本再引用 `opsx-*` 执行编排。

## 4. 非目标

- **不做目录合并**。§19.3 已放弃，本 Change 不重启。
- **不删除 Production 治理语义**。只退役承载它的旧编排，语义本身由 change 2043 的叠加门保留。
- **不自动删除方法论内容**。逐项判定，见 §3 目标 3。
- **不改 Tooling 的 `workflow-*` 入口**。它已是唯一执行链入口。
- **不回填归档中的 `opsx-*` 引用**。归档保存当时证据，不改。

## 5. 设计方案

### 5.1 职责拆解

`opsx-*` 六个入口，按职责分两类：

| 入口 | 执行编排职责 | 方法论职责 |
| --- | --- | --- |
| `opsx-code-generation` | 波次执行、任务推进 | 代码生成方法 |
| `opsx-archive` | 归档编排 | 归档方法论 |
| `opsx-test-generation` | 测试生成编排 | 测试方法 |
| `opsx-requirements-clarification` | 无（前置阶段） | 需求澄清方法 |
| `opsx-system-design` | 无（前置阶段） | 系统设计方法 |
| `opsx-quick-design` | 无（前置阶段） | 快速设计方法 |

**执行编排职责退役；方法论职责逐项判定。** 前三者两者兼有，后三者主要是方法论。

### 5.2 判定标准

方法论内容的去向，按三条判定：

1. 是否已被 Tooling／叠加门承载？是 → 删除 `opsx-*` 版本。
2. 是否仍有独立价值且未被承载？是 → 迁移到合适位置（共享 Skill 或文档）。
3. 是否只适用于已退役的双链结构？是 → 删除。

### 5.3 安装器改动

`install_agentic_framework.py` 的白名单移除 `opsx-*` 条目。需验证：

- Tooling 安装不受影响。
- Production 安装现在指向叠加门结构（由 change 2041 的 Profile 开关 + 2043 的守卫承载）。
- `--switch-profile` 的切换逻辑仍然正确。

### 5.4 未裁决项

**方法论内容的迁移目标位置。** 迁移到哪——共享 Skill、独立文档目录、还是并入现有 `workflow-*` 的文档——需要按内容性质逐项定，不预设统一目标。

**`opsx-*` 文件本身是删除还是保留为归档。** 倾向删除活跃入口、在归档中保留历史记录（与本仓库 change 归档的做法一致）。但「删除活跃 Skill 目录」不可逆，需老板确认。

## 6. 验收标准

1. 任务执行不再经 `opsx-*` 编排，调用路径证明。
2. Production 治理语义全部由叠加门承载，无任何残留依赖 `opsx-*`。
3. `opsx-*` 六个入口的职责逐项拆解，编排职责全部退役。
4. 方法论内容逐项判定去向并记录理由，无「默认全删」或「默认全留」。
5. 安装器白名单移除 `opsx-*`，Tooling 安装验证不受影响。
6. Production 安装指向叠加门结构，验证可用。
7. `--switch-profile` 切换逻辑验证正确。
8. 全仓库无活跃引用残留：`opsx-*` 执行编排在 Skill、Command、文档、脚本中的活跃引用清零（归档除外）。
9. `opsx-*` 文件处置方式（删除 vs 保留归档）经老板确认后执行。
10. 归档中的 `opsx-*` 引用不改动。
11. `python -m pytest scripts -q` 全量通过。
12. 按 md-zh 规范自检中文排版。

## 7. 知识影响

- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。记录 `opsx-*` 执行编排已退役，Production 语义由叠加门承载。
- `openspec/specs/backend/framework/install-agentic-framework/overview.md`：MODIFIED。白名单更新。
- 迁移的方法论内容：按 §5.4 裁决写入对应目标。

## 8. 参考资料

- 目标模型第 4 步：用户提出，见 §1
- `opsx-*` 入口清单：`commands/opsx-*.md`、`skills/opsx-*/`
- 不同时安装约束：`openspec/specs/backend/engineering/tech/framework-unification.md:28`（§1）
- 目录不合并约束：同文件 `:667-672`（§19.3）
- 安装器：`scripts/install_agentic_framework.py:132,185,369`（白名单与 profile 选择）
- 前置：change 2043（执行链统一）、2044（写路径统一）
