# 实施任务清单

> 由 proposal.md 生成
> 任务总数：6
> 核心原则：这是汇聚型 Change，前置六个 Change 未全部落地则不启动（Task 0 阻塞确认）。三条判据——状态源唯一、门为叠加、降级等价——必须**同时**通过，外加治理强度判据，缺一条不交付。本 Change 只挂载守卫，不新增状态机转移，不删除任何治理规则。

## 依赖关系总览

```
Task 0 (前置六 Change 交付确认)
   │
   └──> Task 1 (冻结转移图基线 + §5.3 逐条映射)
          │
          └──> Task 2 (治理门挂载到转移)
                 │
                 ├──> Task 3 (三判据举证)
                 └──> Task 4 (治理强度判据举证)
                        │
                 Task 3 ┴──> Task 5 (规格同步)
```

波次：W1 = {Task 0} → W2 = {Task 1} → W3 = {Task 2} → W4 = {Task 3} → W5 = {Task 4} → W6 = {Task 5}

> Task 3 与 Task 4 都向 `scripts/` 测试目录写用例，存在写入冲突，改为串行。三判据与治理强度判据必须都过，Task 5 才启动。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | Task 2 | 转移上挂载治理守卫，不新增转移 |
| 治理守卫模块 | 新增 | Task 2 | 守卫实现（位置与形态由 Task 1 定） |
| `scripts/` 测试目录 | 新增 | Task 1, Task 3, Task 4 | 转移图基线、判据与强度用例 |
| `opsx-*` 文件 | **不删** | Task 4 | 不再被走，但保留至 change 2045 |
| 三份长期规格 | 修改 | Task 5 | 见 Task 5 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 前置 | Task 0 | 六 Change 交付确认 |
| `proposal.md` §6.1 挂载点、§6.3 | Task 1 | 映射表与两项裁决 |
| `proposal.md` §5 三判据、§6.2 | Task 2, Task 3 | 挂载与判据举证 |
| `proposal.md` §3 目标 5 | Task 4 | 治理强度判据 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `quality-gates` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `workflow-control` | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需核对：本 Change 交付后 `framework-unification.md` §3.2「两个独立生命周期」的语义将发生实质变化——差异保留，但不再由两条链承载。交付时须确认 §3.2 的改写如实反映「语义差异保留、承载合并」的最终形态，且 §5.3 强制规则一条未删。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认未删除任何 `opsx-*` 文件、未新增状态机转移。

---

### 任务 0：[ ] 确认前置六个 Change 全部交付

- 状态: 未开始
- depends_on: 无
- review_profile: strict
- 文档映射：`proposal.md` §2 本 Change 的大前提
- 文件：无（只读确认）
- context_files: `openspec/changes/2035-common-task-ast/`、`2038-production-delivery-evidence/`、`2039-tooling-approval-gate/`、`2040-tooling-knowledge-anti-self-certification/`、`2041-governance-profile-declaration/`、`2042-downgrade-equivalence-harness/`
- artifacts: 前置交付确认清单
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] change 2035 交付：统一读层可用，AST、字段名别名、状态取值归一就位。
    - [ ] change 2038 交付：交付证据核对可复用。
    - [ ] change 2039 交付：状态机含「待批准」与恢复路径。
    - [ ] change 2040 交付：知识反自证核对可用。
    - [ ] change 2041 交付：Profile 开关与 `review_profile` 下限就位。
    - [ ] change 2042 交付：降级等价比对器可执行。
    - [ ] 缺任何一个，停止本 Change，记录阻塞项，不绕过。

### 任务 1：[ ] 冻结转移图基线并逐条映射 §5.3

- 状态: 未开始
- depends_on: Task 0
- review_profile: strict
- 文档映射：`proposal.md` §6.1 挂载点、§6.3 未裁决项
- 文件：无（只读清点与映射，产出写入本 Change）
- context_files: `skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/validate_change.py`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- artifacts: 状态转移图基线、§5.3 逐条挂载映射表、两项裁决记录
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 从 `workflow_control.py` 提取当前完整状态转移图（含 change 2039 的「待批准」），冻结为基线。
    - [ ] §5.3 的每条强制规则都标出挂载的转移与守卫内容，映射表无缺漏。
    - [ ] 任何一条 §5.3 找不到挂载点时，停止并报告，不降级为「由流程文档要求」。
    - [ ] 裁决逐任务 Review 粒度，核对与 §3.4「普通 Task 一次综合审核」的一致性。
    - [ ] 裁决 Plan 总守卫与执行期转移守卫的关系。
    - [ ] 守卫模块的位置与形态确定，与现有共享模块机制一致。

### 任务 2：[ ] 治理门挂载到状态机转移

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §5 「叠加而非替换」、§6.2
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`、治理守卫模块
- context_files: Task 1 的映射表与转移图基线、change 2039 的状态机
- artifacts: 守卫实现、挂载后的状态机
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 每条 §5.3 规则按 Task 1 的映射挂载为转移守卫。
    - [ ] **不新增状态机转移**——守卫只增前置条件，转移图结构不变，用 Task 1 基线比对证明。
    - [ ] 守卫全部关闭后，状态机行为与纯 Tooling 一致（为 Task 3 降级等价铺路）。
    - [ ] 每条守卫在缺失证据时失败关闭，有用例。
    - [ ] 任务推进只经 `workflow_control.py` 状态机，不经第二条链。
    - [ ] 不删除任何 `opsx-*` 文件。

### 任务 3：[ ] 三判据举证

- 状态: 未开始
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §5 三判据、§7 验收标准 1-3
- 文件：`scripts/` 测试目录
- context_files: Task 1 的转移图基线、change 2042 的比对器、`skills/workflow-code-generation/scripts/workflow_control.py`
- artifacts: 三判据举证报告
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 状态源唯一：静态核验 `- 状态:` 与任务头标记只有 `workflow_control.py` 一个写入者，有检索证明。
    - [ ] 门为叠加：叠加 Production 门后转移图与 Task 1 基线逐字节相同。
    - [ ] 降级等价：change 2042 的比对器跑通，结论为「通过」。
    - [ ] 三判据任一不过，本 Change 不交付，记录未过项与原因。
    - [ ] 比对器的「无法执行」结论不被当作「通过」接受。

### 任务 4：[ ] 治理强度判据举证

- 状态: 未开始
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §3 目标 5、§7 验收标准 5-6
- 文件：`scripts/` 测试目录
- context_files: `openspec/specs/backend/engineering/tech/framework-unification.md:177-195`、Task 2 的守卫实现
- artifacts: 治理强度举证报告、`opsx-*` 保留确认
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] §5.3 每条强制规则验证仍被机器守卫强制，逐条列出证据。
    - [ ] 确认无任何一条退化为散文或流程文档要求；用检索证明每条都有对应代码守卫。
    - [ ] 治理强度判据与 Task 3 的降级等价判据**同时**通过，不只过其一。
    - [ ] 确认任务不再走 `opsx-*` 执行链，有调用路径证明。
    - [ ] 确认 `opsx-*` 文件全部仍在，未被删除。

### 任务 5：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 3, Task 4
- review_profile: strict
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/engineering/tech/framework-unification.md`、`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/framework/workflow-control/overview.md`
- context_files: Task 3 与 Task 4 的举证报告
- artifacts: 三份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] `framework-unification.md` §8.1 门层状态改为「条件已满足并合并」，附三判据与强度判据证据。
    - [ ] §3.2 改写为「语义差异保留、承载合并为一条执行链」的最终形态，五项语义差异一条未删。
    - [ ] §5.3 强制规则逐条保留，标注其守卫挂载点。
    - [ ] `quality-gates/overview.md` 记录治理门的挂载结构。
    - [ ] `workflow-control/overview.md` 记录守卫与转移的关系、门为叠加的约束。
    - [ ] 记录执行期推进控制是收敛带来的能力净增。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
