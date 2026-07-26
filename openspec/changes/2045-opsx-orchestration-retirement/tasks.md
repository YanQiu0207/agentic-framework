# 实施任务清单

> 由 proposal.md 生成
> 任务总数：6
> 核心原则：退役 ≠ 合并 ≠ 删除语义。`opsx-*` 兼有执行编排与方法论两类职责，本 Change 只退役编排，方法论逐项判定去向。文件本身删除与否不可逆，必须老板确认后才执行（Task 4 是决策门）。前置 2043、2044 未交付则不启动。

## 依赖关系总览

```
Task 0 (前置确认 2043 + 2044 已交付)
   │
   └──> Task 1 (职责拆解 + 引用清点)
          │
          └──> Task 2 (方法论逐项判定去向)
                 │
                 └──> Task 3 (安装器白名单 + 无残留核验)
                        │
                        └──> Task 4 (文件处置决策门——需老板确认)
                               │
                               └──> Task 5 (规格同步)
```

波次：W1 = {Task 0} → W2 = {Task 1} → W3 = {Task 2} → W4 = {Task 3} → W5 = {Task 4} → W6 = {Task 5}

> 全链串行。Task 4 是人工决策门，不可逆操作在此停下等确认。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `commands/opsx-*.md`、`skills/opsx-*/` | 处置待定 | Task 2, Task 4 | 编排退役，方法论逐项判定 |
| `scripts/install_agentic_framework.py` | 修改 | Task 3 | 白名单移除 `opsx-*` |
| 迁移的方法论内容 | 迁移 | Task 2 | 目标位置逐项定 |
| 长期规格 | 修改 | Task 5 | 见 Task 5 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 前置 | Task 0 | 2043、2044 确认 |
| `proposal.md` §5.1 职责拆解 | Task 1 | 编排 vs 方法论 |
| `proposal.md` §5.2 判定标准、§5.4 | Task 2 | 方法论去向 |
| `proposal.md` §5.3 安装器 | Task 3 | 白名单与验证 |
| `proposal.md` §5.4 文件处置 | Task 4 | 决策门 |
| `proposal.md` §7 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `install-agentic-framework` | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需核对：`framework-unification.md` §19.3 放弃「把两个 Skill 目录直接合并」。交付时须确认本 Change 的退役未被实现成变相的目录合并——退役编排与合并目录是不同动作，区别必须在文档中写明。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认归档中的 `opsx-*` 引用未改动。

---

### 任务 0：[ ] 确认 change 2043 与 2044 已交付

- 状态: 未开始
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §2 为什么这是最后一步
- 文件：无（只读确认）
- context_files: `openspec/changes/2043-governance-overlay-merge/`、`openspec/changes/2044-write-state-path-unification/`
- artifacts: 前置交付确认记录
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 确认 2043 交付：执行链已统一，治理语义由叠加门承载，三判据与强度判据均通过。
    - [ ] 确认 2044 交付：写状态路径已统一。
    - [ ] 缺任何一个，停止本 Change，记录阻塞，不提前退役。
    - [ ] 确认 `opsx-*` 当前已无活跃任务执行依赖（2043 已让任务不再走它）。

### 任务 1：[ ] 职责拆解与全仓库引用清点

- 状态: 未开始
- depends_on: Task 0
- review_profile: strict
- 文档映射：`proposal.md` §5.1 职责拆解
- 文件：无（只读清点，产出写入本 Change）
- context_files: `commands/opsx-*.md`、`skills/opsx-*/`、`scripts/install_agentic_framework.py`
- artifacts: 六入口职责拆解表、全仓库 `opsx-*` 引用清单
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 六个入口逐一拆解为「执行编排职责」与「方法论职责」。
    - [ ] 全仓库检索 `opsx-`，列出 Skill、Command、文档、脚本中的全部引用，标注活跃／归档。
    - [ ] 归档引用单独标注为不改动。
    - [ ] 确认编排职责已被叠加门承载，无残留依赖。
    - [ ] 记录每个入口方法论内容的具体清单（不是只给分类）。

### 任务 2：[ ] 方法论内容逐项判定去向

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §5.2 判定标准、§5.4 迁移目标
- 文件：迁移的方法论内容（目标位置逐项定）
- context_files: Task 1 的拆解表、`skills/`、`openspec/`
- artifacts: 逐项判定记录、迁移后的方法论内容
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 按三条标准逐项判定：已被承载→删除；仍有独立价值→迁移；只适用双链结构→删除。
    - [ ] 每项判定附理由，无「默认全删」或「默认全留」。
    - [ ] 迁移目标位置按内容性质逐项确定并记录，不预设统一目标。
    - [ ] 迁移的内容保留原文，不改写为「适配新结构」（改写属另一动作）。
    - [ ] 迁移后无方法论内容只存在于 `opsx-*` 中而未判定去向。

### 任务 3：[ ] 安装器白名单与无活跃残留核验

- 状态: 未开始
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §5.3 安装器改动、§6 验收标准 5-8
- 文件：`scripts/install_agentic_framework.py`
- context_files: `scripts/install_agentic_framework.py`、Task 1 的引用清单
- artifacts: 更新后的白名单、无残留核验结论
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 白名单移除 `opsx-*` 条目。
    - [ ] Tooling 安装验证不受影响。
    - [ ] Production 安装指向叠加门结构，验证可用。
    - [ ] `--switch-profile` 切换逻辑验证正确。
    - [ ] 活跃引用（Skill、Command、文档、脚本）中 `opsx-*` 执行编排引用清零。
    - [ ] 归档引用未改动。

### 任务 4：[ ] 文件处置决策门（需老板确认）

- 状态: 未开始
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §5.4 文件处置
- 文件：`commands/opsx-*.md`、`skills/opsx-*/`
- context_files: Task 2 的判定记录、Task 3 的无残留核验
- artifacts: 处置决策记录、执行结果
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 向老板提交处置方案：删除活跃 `opsx-*` 入口，还是保留为归档。
    - [ ] **明确删除不可逆**，列出将删除的具体文件清单。
    - [ ] 得到老板明确确认后才执行；未确认前不动任何文件。
    - [ ] 若保留为归档，记录归档位置与方式。
    - [ ] 执行后复核：无残留引用、安装器仍正确。

### 任务 5：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §7 知识影响
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/backend/framework/install-agentic-framework/overview.md`
- context_files: `openspec/changes/2045-opsx-orchestration-retirement/proposal.md`、Task 4 的处置记录
- artifacts: 两份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] `framework-unification.md` 记录 `opsx-*` 执行编排已退役，Production 语义由叠加门承载。
    - [ ] 记录退役与 §19.3「目录合并」的区别，明确本 Change 未做合并。
    - [ ] `install-agentic-framework/overview.md` 更新白名单。
    - [ ] 记录方法论内容的迁移去向汇总。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
