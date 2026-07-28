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
| `install-agentic-framework` | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | 已完成 | 既有条目，无需改索引 |
| `quality-gates` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | 已完成 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 已完成 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 已核对（2026-07-26）。散文声明与机器来源的关系已写入 `AGENTS.md`：本仓库有 `.agentic-framework/` 运行目录但无 `manifest.json`（实测修正 proposal「没有 .agentic-framework/」的表述），跑门禁经 `--governance-profile tooling` 显式取得；本仓库无 CI 配置，本地与技能流程同一路径，无「CI 传参、本地不传」的分裂。向上搜索会继承祖先链上的安装（实测本机 `C:\Users\YanQi\.agentic-framework\manifest.json` 会被 `%TEMP%` 下的目录命中）——这是 §5.1 设计的特性而非缺陷，但意味着「缺失失败关闭」只在整条祖先链都无安装时触发；本仓库在 E:\ 盘不受其影响。

## 实际 Diff 核对

- `git diff --stat` 要点：新增 `scripts/governance_profile.py` 与 `scripts/test_governance_profile.py`；`validate_change.py`（OPSX062/063 下限分支、`--governance-profile` 参数）、`lint_task_deps.py`（`field_errors`/`lint_report` 带 `governance` 参数、main 惰性读取）、`check_delivery.py`（`check_review_profile_floor` 挂载）、`workflow_control.py`（参数接线，2043 消费）；三个测试文件加用例；`AGENTS.md` 补记；三份长期规格同步。
- `install_agentic_framework.py` 逐字节未改动（md5 `d671f1a3…`，`git diff --name-only` 无此文件），`MANIFEST_SCHEMA_VERSION = 3` 未变。
- 门禁前后对照（对照 2038 后三阶段快照）：既有码零翻转；新增码 OPSX062 出现在 7 个含 `lightweight` 声明的归档 Change——这些文件本就因 OPSX037 失败，现为「无法取得 Profile 失败关闭」，**错误数不变、规则替换**（OPSX037 → OPSX062）；对照中的其余差异全部来自本会话对活跃 Change 的内容更新（同步状态更正、任务标完成），非代码行为翻转。
- 零越界检索：Profile 相关分支只存在于三处下限判定（`validate_change.py:1354-1376`、`lint_task_deps.py:193-199`、`check_delivery.py` 的 floor 检查），无任何其他按 Profile 分派判定的分支。
- Quick 例外裁决（Task 2）：不构成例外——现行实现对 Quick 与 Standard 的 Review 档位要求一致（OPSX037 系检查无 Quick 分支），与 §5.3「Standard 为默认路径」一致；Quick 的流程差异在工件（§5.4），不在 Review 档位。有对应用例。
- 惰性读取裁决：只在 `review_profile` 触及下限时读取 Profile——无 `lightweight` 声明时 Profile 取值与判定无关，读取是无谓耦合；读取失败（缺失／非法）在触及判定时失败关闭（OPSX062／lint exit 2／交付门 ERROR），「静默默认为 tooling」不存在（源码检索证明）。

---

### 任务 1：[x] Profile 读取与缺失时的失败关闭

- 状态: 完成
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §5.1 来源、§5.2 缺失时的行为
- 文件：`scripts/governance_profile.py`、`scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- context_files: `scripts/install_agentic_framework.py`、`scripts/workspace_residue.py`
- artifacts: 共享读取模块、四个门禁的接入、缺失与非法用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 新增共享模块，放置与导入方式与 `workspace_residue.py` 一致，不引入新机制。
    - [x] 从被校验仓库根向上查找 `.agentic-framework/manifest.json`，读取 `profile` 字段。
    - [x] 四个门禁脚本都能取得 Profile。
    - [x] manifest 不存在且未传 `--governance-profile` 时失败关闭，有用例。
    - [x] manifest 的 `profile` 非法时失败关闭，**不回退默认值**，有用例。
    - [x] **不存在「静默默认为 tooling」的分支**，用检索证明；这是本 Change 最危险的失败方向。
    - [x] `--governance-profile` 参数在四个脚本中名称与取值集合一致。
    - [x] 不读 `AGENTS.md`，不做任何自然语言解析。
    - [x] 本任务只增加读取，不改变任何既有判定；全部活跃与归档 Change 的判定输出与改动前逐一比对无变化。

### 任务 2：[x] review_profile 的 Profile 级下限

- 状态: 完成
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §5.3 下限
- 文件：`skills/workflow-code-generation/scripts/lint_task_deps.py`、`scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`
- context_files: `openspec/specs/backend/engineering/tech/framework-unification.md`、Task 1 的读取模块
- artifacts: 下限实现、Quick 例外裁决记录、用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] `production` 下 `review_profile: lightweight` 失败关闭，有用例。
    - [x] `tooling` 下 `lightweight` 仍合法，有用例。
    - [x] 两轨都允许向上声明 `strict`。
    - [x] **查证并裁决** Production 的 Quick 流程是否构成下限例外，引用 `framework-unification.md` §5.3 与 §5.4 原文；不得默认 Quick 可用 `lightweight`。
    - [x] 裁决结果有对应用例。
    - [x] 下限检查是本 Change 唯一允许的判定变化；因下限而失败的既有文件逐条列出并判定。
    - [x] 取值集合 `REVIEW_PROFILES` 未变更，仍是三个值。
    - [x] 与 change 2035 Task 6 的字段名别名兼容：两种写法都受下限约束，有用例。

### 任务 3：[x] 本仓库自身的门禁调用路径

- 状态: 完成
- depends_on: Task 1
- review_profile: standard
- 文档映射：`proposal.md` §5.2 末段
- 文件：`AGENTS.md`、仓库内门禁调用说明文档（具体文件由实现方确定）
- context_files: `AGENTS.md`、`scripts/install_agentic_framework.py`、Task 1 的读取模块
- artifacts: 调用路径文档、CI 与本地用法一致性确认
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] 确认本仓库是否存在 `.agentic-framework/`；不存在时记录这一事实。
    - [x] 文档化本仓库跑门禁时如何取得 Profile（显式参数或其他方式）。
    - [x] 确认 CI 与本地开发使用同一路径，不出现「CI 传参、本地不传」的分裂。
    - [x] `AGENTS.md` 的散文声明保留不改；补记机器来源与散文声明的关系。
    - [x] 不修改安装器行为来迁就本仓库。

### 任务 4：[x] 零越界核对与长期规格同步

- 状态: 完成
- depends_on: Task 2, Task 3
- review_profile: strict
- 文档映射：`proposal.md` §6 验收标准 7-9、§7 知识影响
- 文件：`openspec/specs/backend/framework/install-agentic-framework/overview.md`、`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2041-governance-profile-declaration/proposal.md`、Task 1 与 Task 2 的比对结果
- artifacts: 零越界结论、三份长期规格
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 除 `review_profile` 下限外，两轨的判定结果对全部活跃与归档 Change 逐一比对无变化。
    - [x] 确认门禁只是**知道** Profile，没有任何按 Profile 分派判定的分支；用检索证明。
    - [x] `scripts/install_agentic_framework.py` 逐字节未改动。
    - [x] `MANIFEST_SCHEMA_VERSION` 未变更。
    - [x] `install-agentic-framework/overview.md` 记录 manifest 的 `profile` 字段现被门禁消费。
    - [x] `quality-gates/overview.md` 记录 `review_profile` 下限规则与 Quick 裁决结果。
    - [x] `framework-unification.md` 记录这是 §3.2 条件 1 的**部分**举证，明确五项差异中仅 Review 档位一项被参数化。
    - [x] 记录本 Change 为 change 2042 提供了可切换的 Profile 开关，但未实现降级行为。
    - [x] `python scripts/markdown_links.py openspec` 退出码 0。
    - [x] 按 md-zh 规范自检中文排版。
