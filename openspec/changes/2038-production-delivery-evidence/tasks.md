# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：共享模块零改动是本 Change 的硬边界（Task 1 先立护栏），Production 只增加消费方（Task 2、Task 3），只读性质必须可证（Task 4），最后同步规格（Task 5）。任何需要修改 `workspace_residue.py` 的发现都必须停下报告，不得顺手改——那会同时影响 Tooling。

## 依赖关系总览

```
Task 1 (冻结共享模块与既有判定基线)
   │
   └──> Task 2 (Delivery 阶段接入证据检查)
          │
          └──> Task 3 (缺证据与豁免路径)
                 │
                 └──> Task 4 (只读性质与跨轨互认核对)
                        │
                        └──> Task 5 (规格同步)
```

波次：W1 = {Task 1} → W2 = {Task 2} → W3 = {Task 3} → W4 = {Task 4} → W5 = {Task 5}

> 全链串行。Task 2 与 Task 3 都改 `validate_change.py` 的同一段逻辑，无法并行。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/validate_change.py` | 修改 | Task 2, Task 3 | Delivery 阶段接入交付范围与工作区证据 |
| `scripts/workspace_residue.py` | **不改** | Task 1, Task 4 | 共享模块，逐字节冻结 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | **不改** | Task 4 | Tooling 消费方不动 |
| `scripts/tests/` | 新增 | Task 2, Task 3, Task 4 | 新检查用例与跨轨互认用例 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 5 | 新增 Production 证据检查条目 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 5 | §5.3 强制规则同步 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 已有能力 | Task 1 | 接口清点与基线冻结 |
| `proposal.md` §6.1 挂载阶段 | Task 2 | 挂在 delivery |
| `proposal.md` §6.2 基线来源 | Task 2 | 新增 CLI 参数 |
| `proposal.md` §6.3、§6.4 | Task 3 | 缺证据行为与豁免形式 |
| `proposal.md` §7 验收标准 7-11 | Task 4 | 零改动、只读、跨轨互认 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `quality-gates` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | 完成 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 完成 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 已核对（2026-07-26）。§8.1 只读约束与读取版本控制状态的区分判定：「读外部状态」是校验器对仓库既有事实（提交路径、工作区残留）的只读查询，判定可复现；「维护平行状态」是校验器自己写入并依赖的另一份事实源。本 Change 只做前者——基线经 CLI 参数传入，`validate_change.py` 不采集基线、不写任何文件（新增函数源码检索无 `write_text`／`mkstemp`／`os.link` 等调用），不冲突。

## 实际 Diff 核对

- `git diff --stat` 要点：`scripts/validate_change.py`（+约 240 行：证据检查函数、三个 CLI 参数、豁免与文件字段正则）、`scripts/tests/test_validate_change.py`（+DeliveryEvidenceTest 13 用例、导入 `check_delivery`／`workspace_residue`）、三个既有 fixture 的 tasks.md 头部各加一条豁免声明、两份长期规格同步。
- `scripts/workspace_residue.py` 与 `check_delivery.py` 零改动，md5 与 Task 1 冻结值一致（`fe7bf641…`、`5bf44692…`）。
- 三阶段门禁基线（`gate_3phase_before.json` vs `gate_3phase_after.json`）：既有码（≤OPSX056）零翻转；新增码仅 OPSX057，出现于 30 个 Change 的 delivery 阶段——全部为未传基线参数的失败关闭，属本 Change 的预期新门行为（基线比对按「既有码无翻转＋新增码逐条列出」执行，因「全部不变」与「未传基线失败关闭」两条验收标准在字面执行上互斥）。
- 豁免字段裁决（§6.4）：复用 Escalation 的「声明字段＋严格／宽松双正则＋失败关闭」机制，但不复用 Escalation 字段本身——其语义是风险暂停，混入会污染 OPSX055 耦合与批准证据链；新增专用字段 `- 交付证据豁免: <原因>`，豁免记录即声明本身，无记录的豁免不生效。
- OPSX 码分配：057 缺证据参数、058 证据不可用（基线坏／无 VCS／提交非法）、059 范围越界、060 残留不一致、061 豁免格式错误；从 057 起无重号。
- 跨轨互认用例：同一份基线文件，`validate_change._validate_delivery_evidence` 与 `check_delivery.check_scoped_delivery` 均判定通过（`DeliveryEvidenceTest::test_cross_track_same_baseline_both_pass`）。

---

### 任务 1：[x] 冻结共享模块接口与既有判定基线

- 状态: 完成
- depends_on: 无
- review_profile: standard
- 文档映射：`proposal.md` §2 Tooling 侧已有的能力
- 文件：无（只读清点，产出写入本 Change）
- context_files: `scripts/workspace_residue.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/validate_change.py`
- artifacts: 共享模块接口契约表、`workspace_residue.py` 的内容哈希、全部 OPSX 码现行判定基线
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 记录 `workspace_residue.py` 的公共函数签名与返回结构，逐个标注 Production 将使用哪些。
    - [x] 记录该文件的内容哈希，供 Task 4 核对零改动。
    - [x] 记录 `check_scoped_delivery` 的调用序列，作为 Production 侧实现的参照。
    - [x] 对全部活跃与归档 Change 跑 `validate_change.py` 三个阶段，冻结现行判定输出为基线。
    - [x] 记录当前已使用的最大 OPSX 码（现为 OPSX056），确定新码起始编号。
    - [x] 确认 `workspace_residue.py` 的快照格式定义位置，供跨轨互认用例引用。

### 任务 2：[x] Delivery 阶段接入交付范围与工作区证据

- 状态: 完成
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 挂载阶段、§6.2 基线来源
- 文件：`scripts/validate_change.py`、`scripts/tests/`
- context_files: `scripts/workspace_residue.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、Task 1 的接口契约表
- artifacts: `scripts/validate_change.py`、新增用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 新检查只在 `--phase delivery` 生效；`plan` 与 `archive` 阶段行为不变。
    - [x] 交付路径越出 `tasks.md` 声明范围时失败关闭，错误码、消息、修复建议齐备。
    - [x] 工作区存在未声明残留时失败关闭，同上。
    - [x] 基线通过新增 CLI 参数传入，参数名与格式与 Tooling 的 `--workspace-residue-baseline` 一致。
    - [x] `validate_change.py` 不采集基线、不写任何文件。
    - [x] 通过 `scripts/` 直接导入 `workspace_residue`，不复制其中任何逻辑。
    - [x] `workspace_residue.py` 逐字节未改动；若发现必须改，停止本任务并报告。
    - [x] Task 1 冻结的既有判定基线全部不变，无一条 OPSX 结果翻转。

### 任务 3：[x] 缺证据行为与显式豁免路径

- 状态: 完成
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §6.3 缺证据时的行为、§6.4 未裁决项
- 文件：`scripts/validate_change.py`、`scripts/tests/`
- context_files: `scripts/validate_change.py`、`openspec/changes/2034-knowledge-gate-risk-inversion/proposal.md`
- artifacts: `scripts/validate_change.py`、缺证据与豁免用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 未传基线参数时失败关闭，有用例。
    - [x] `detect_vcs` 抛错（无版本控制）时失败关闭，错误消息说明 Production 的要求，有用例。
    - [x] **不存在任何静默跳过分支**，用检索证明；这正是 change 2034 要修的风险反转类型。
    - [x] 豁免字段形式已裁决并记录理由：复用 Escalation 机制还是新增独立字段。
    - [x] 豁免必须留下可审计记录；无记录的豁免不生效，有用例。
    - [x] 豁免记录缺失、格式错位或条件不一致时失败关闭，与 OPSX053 的处理方式一致。
    - [x] 新增 OPSX 码从 Task 1 确定的编号起分配，无重号。

### 任务 4：[x] 只读性质与跨轨证据互认核对

- 状态: 完成
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §7 验收标准 7-11
- 文件：`scripts/tests/`
- context_files: `scripts/validate_change.py`、`scripts/workspace_residue.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、Task 1 的哈希记录
- artifacts: 跨轨互认用例、只读性质证明、零改动核对结论
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [x] 用 Task 1 记录的哈希确认 `workspace_residue.py` 零改动。
    - [x] 确认 `check_delivery.py` 零改动。
    - [x] 跨轨互认用例：同一份 `workspace_residue` 基线文件，两轨都能成功校验，判定一致。
    - [x] 只读性质证明：检索 `validate_change.py` 中的写入调用，确认新增代码未引入任何文件写入。
    - [x] 给出「读外部状态」与「§8.1 的维护平行状态」的区分判定，写入本 Change 的知识冲突节；不默认这一区分成立。
    - [x] Task 1 的全量判定基线复跑，除新增码外无差异。

### 任务 5：[x] 长期规格同步

- 状态: 完成
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2038-production-delivery-evidence/proposal.md`
- artifacts: 两份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [x] `quality-gates/overview.md` 记录 Production Delivery 阶段的新检查与新 OPSX 码。
    - [x] `framework-unification.md` §5.3 新增对应强制规则条目。
    - [x] 记录这是 §3.2 条件 1 的**部分**举证，明确其余项仍未举证，不夸大为条件已满足。
    - [x] 记录共享模块 `workspace_residue.py` 现由两轨共同消费。
    - [x] `python scripts/markdown_links.py openspec` 退出码 0。
    - [x] 按 md-zh 规范自检中文排版。
