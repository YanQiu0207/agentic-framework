# 实施任务清单

> 由 proposal.md 生成
> 任务总数：4
> 核心原则：本 Change 只做「读取」与「下限」，不做行为分派。除 `review_profile` 下限外的任何判定变化都是越界（Task 4 专门核对这一点）。本仓库自身没有 `.agentic-framework/`，所以显式参数路径不是边角情况，必须一等对待。

## 依赖关系总览

```
Task 1 (Profile 读取与缺失行为)
   │
   ├──> Task 2 (review_profile 下限)
   │
   └──> Task 3 (本仓库自身的调用路径)
          │
   Task 2 ┴──> Task 4 (零越界核对与规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2, Task 3} → W3 = {Task 4}

> Task 2 改门禁判定，Task 3 改文档与调用约定，互不冲突，可并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/governance_profile.py` | 新增 | Task 1 | 共享的 Profile 读取（名称待实现方定） |
| `scripts/validate_change.py` | 修改 | Task 1, Task 2 | 接入读取与下限 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | Task 1, Task 2 | 同上 |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 1 | 接入读取 |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 修改 | Task 1, Task 2 | 同上 |
| `scripts/install_agentic_framework.py` | **不改** | Task 4 | 安装器零改动 |
| `openspec/specs/backend/framework/install-agentic-framework/overview.md` | 修改 | Task 4 | manifest 消费方 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 4 | 下限规则 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 4 | 条件 1 部分举证 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §5.1 来源、§5.2 缺失行为 | Task 1 | 读取与失败关闭 |
| `proposal.md` §5.3 下限 | Task 2 | 按 Profile 的最低档 |
| `proposal.md` §5.2 末段 | Task 3 | 本仓库自身路径 |
| `proposal.md` §6 验收标准 7-9 | Task 4 | 零越界与安装器零改动 |
| `proposal.md` §7 知识影响 | Task 4 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `install-agentic-framework` | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `quality-gates` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需核对：`AGENTS.md` 声明本项目使用 Tooling Profile，但本仓库没有 `.agentic-framework/manifest.json`。散文声明与机器来源在本仓库内不一致——不是矛盾，但必须记录门禁在本仓库如何取得 Profile，否则「机器可读来源」这一目标在本仓库内不成立。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认 `install_agentic_framework.py` 零改动、`MANIFEST_SCHEMA_VERSION` 未变。

---

### 任务 1：[ ] Profile 读取与缺失时的失败关闭

- 状态: 未开始
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §5.1 来源、§5.2 缺失时的行为
- 文件：`scripts/governance_profile.py`、`scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/install_agentic_framework.py`、`scripts/workspace_residue.py`
- artifacts: 共享读取模块、四个门禁的接入、缺失与非法用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 新增共享模块，放置与导入方式与 `workspace_residue.py` 一致，不引入新机制。
    - [ ] 从被校验仓库根向上查找 `.agentic-framework/manifest.json`，读取 `profile` 字段。
    - [ ] 四个门禁脚本都能取得 Profile。
    - [ ] manifest 不存在且未传 `--governance-profile` 时失败关闭，有用例。
    - [ ] manifest 的 `profile` 非法时失败关闭，**不回退默认值**，有用例。
    - [ ] **不存在「静默默认为 tooling」的分支**，用检索证明；这是本 Change 最危险的失败方向。
    - [ ] `--governance-profile` 参数在四个脚本中名称与取值集合一致。
    - [ ] 不读 `AGENTS.md`，不做任何自然语言解析。
    - [ ] 本任务只增加读取，不改变任何既有判定；全部活跃与归档 Change 的判定输出与改动前逐一比对无变化。

### 任务 2：[ ] review_profile 的 Profile 级下限

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §5.3 下限
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`、`scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`
- context_files: `openspec/specs/backend/engineering/tech/framework-unification.md`、Task 1 的读取模块
- artifacts: 下限实现、Quick 例外裁决记录、用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] `production` 下 `review_profile: lightweight` 失败关闭，有用例。
    - [ ] `tooling` 下 `lightweight` 仍合法，有用例。
    - [ ] 两轨都允许向上声明 `strict`。
    - [ ] **查证并裁决** Production 的 Quick 流程是否构成下限例外，引用 `framework-unification.md` §5.3 与 §5.4 原文；不得默认 Quick 可用 `lightweight`。
    - [ ] 裁决结果有对应用例。
    - [ ] 下限检查是本 Change 唯一允许的判定变化；因下限而失败的既有文件逐条列出并判定。
    - [ ] 取值集合 `REVIEW_PROFILES` 未变更，仍是三个值。
    - [ ] 与 change 2035 Task 6 的字段名别名兼容：两种写法都受下限约束，有用例。

### 任务 3：[ ] 本仓库自身的门禁调用路径

- 状态: 未开始
- depends_on: Task 1
- review_profile: standard
- 文档映射：`proposal.md` §5.2 末段
- 文件：`AGENTS.md`、仓库内门禁调用说明文档（具体文件由实现方确定）
- context_files: `AGENTS.md`、`scripts/install_agentic_framework.py`、Task 1 的读取模块
- artifacts: 调用路径文档、CI 与本地用法一致性确认
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] 确认本仓库是否存在 `.agentic-framework/`；不存在时记录这一事实。
    - [ ] 文档化本仓库跑门禁时如何取得 Profile（显式参数或其他方式）。
    - [ ] 确认 CI 与本地开发使用同一路径，不出现「CI 传参、本地不传」的分裂。
    - [ ] `AGENTS.md` 的散文声明保留不改；补记机器来源与散文声明的关系。
    - [ ] 不修改安装器行为来迁就本仓库。

### 任务 4：[ ] 零越界核对与长期规格同步

- 状态: 未开始
- depends_on: Task 2, Task 3
- review_profile: strict
- 文档映射：`proposal.md` §6 验收标准 7-9、§7 知识影响
- 文件：`openspec/specs/backend/framework/install-agentic-framework/overview.md`、`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2041-governance-profile-declaration/proposal.md`、Task 1 与 Task 2 的比对结果
- artifacts: 零越界结论、三份长期规格
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 除 `review_profile` 下限外，两轨的判定结果对全部活跃与归档 Change 逐一比对无变化。
    - [ ] 确认门禁只是**知道** Profile，没有任何按 Profile 分派判定的分支；用检索证明。
    - [ ] `scripts/install_agentic_framework.py` 逐字节未改动。
    - [ ] `MANIFEST_SCHEMA_VERSION` 未变更。
    - [ ] `install-agentic-framework/overview.md` 记录 manifest 的 `profile` 字段现被门禁消费。
    - [ ] `quality-gates/overview.md` 记录 `review_profile` 下限规则与 Quick 裁决结果。
    - [ ] `framework-unification.md` 记录这是 §3.2 条件 1 的**部分**举证，明确五项差异中仅 Review 档位一项被参数化。
    - [ ] 记录本 Change 为 change 2042 提供了可切换的 Profile 开关，但未实现降级行为。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
