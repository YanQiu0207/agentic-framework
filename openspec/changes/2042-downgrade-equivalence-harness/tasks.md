# 实施任务清单

> 由 proposal.md 生成
> 任务总数：5
> 核心原则：「无法执行」与「不通过」同判越界但原因必须分开，这是本 Change 的语义核心。比对框架是独立脚本，不改动任一轨门禁的判定内容——Task 5 专门核对四个门禁零越界。依赖 change 2041 的 Profile 开关，未交付则本 Change 停止。

## 依赖关系总览

```
Task 0 (前置确认 change 2041 已交付)
   │
   └──> Task 1 (裁决实现位置与基线时机)
          │
          └──> Task 2 (降级路径与比对器)
                 │
                 └──> Task 3 (无法执行判定与越界报告)
                        │
                        └──> Task 4 (门禁零越界核对)
                               │
                               └──> Task 5 (规格同步)
```

波次：W1 = {Task 0} → W2 = {Task 1} → W3 = {Task 2} → W4 = {Task 3} → W5 = {Task 4} → W6 = {Task 5}

> Task 0 是阻塞式前置确认，不产生代码。其余全链串行——Task 2 与 Task 3 都改同一个比对器脚本。

## 变更影响概览

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/downgrade_equivalence.py` | 新增 | Task 2, Task 3 | 独立比对器（名称待 Task 1 定） |
| `scripts/` 测试目录 | 新增 | Task 1, Task 2, Task 3, Task 4 | 基线、三态用例、越界用例 |
| 四轨门禁脚本 | **不改** | Task 4 | 判定内容零改动 |
| `openspec/specs/backend/framework/quality-gates/overview.md` | 修改 | Task 5 | 回归门条目 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 5 | 判据已实现记录 |

## 文档覆盖映射

| 文档条目 | 任务 | 说明 |
| --- | --- | --- |
| `proposal.md` §2 前置依赖 | Task 0 | change 2041 交付确认 |
| `proposal.md` §6.4 未裁决项 | Task 1 | 实现位置与基线时机 |
| `proposal.md` §6.1、§6.2 | Task 2 | 降级路径与比对范围 |
| `proposal.md` §6.3 无法执行 | Task 3 | 五种情形与越界 |
| `proposal.md` §7 验收标准 10 | Task 4 | 门禁零越界 |
| `proposal.md` §8 知识影响 | Task 5 | 规格同步 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `quality-gates` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |
| `framework-unification` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | 未开始 | 既有条目，无需改索引 |

## 知识冲突

- 状态: 待交付时填写。已知需记录：降级等价判据只验「减去治理门后等于 Tooling」，不验治理强度。交付时须确认报告与规格都未把判据通过读成「收敛已证明」，两命题的区分在 change 2036 `design.md` §3.3 已立。

## 实际 Diff 核对

- 待交付时填写。须包含 `git diff --stat`，并单独确认四个门禁脚本零改动。

---

### 任务 0：[ ] 确认 change 2041 已交付

- 状态: 未开始
- depends_on: 无
- review_profile: standard
- 文档映射：`proposal.md` §2 前置依赖
- 文件：无（只读确认）
- context_files: `openspec/changes/2041-governance-profile-declaration/`、`scripts/`
- artifacts: 前置依赖确认记录
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 确认 change 2041 已交付，`--governance-profile` 参数存在且可切换。
    - [ ] 确认 Profile 读取模块存在并可被比对器导入。
    - [ ] 若 2041 未交付，停止本 Change 后续任务，记录阻塞原因，不自建 Profile 开关。
    - [ ] 记录 2041 提供的开关的确切参数名与取值集合，作为比对器的调用契约。

### 任务 1：[ ] 裁决实现位置与基线生成时机

- 状态: 未开始
- depends_on: Task 0
- review_profile: strict
- 文档映射：`proposal.md` §6.4 未裁决项、§6.2 比对范围
- 文件：无（只读清点与裁决记录，产出写入本 Change）
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`openspec/changes/2035-common-task-ast/design.md`
- artifacts: 两项裁决记录、比对范围定义、确定性归一规则
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 裁决降级开关实现位置：各门禁内加降级模式，还是独立包装脚本剥离治理参数。写明理由与被拒方案缺陷。
    - [ ] 若选包装脚本：确认「剥离不全」能被「无法执行」判定覆盖，给出检测方式。
    - [ ] 裁决基线生成时机：预冻结 golden 还是现跑现比。写明理由，并对「两路径同步漂移导致同时错」的风险给出对策。
    - [ ] 定义比对范围为「退出码 + 排序后错误编号集合」，或给出更细方案并说明可比性。
    - [ ] 写出确定性归一规则（时间戳、绝对路径等的处理），明确归一不静默丢弃差异。
    - [ ] 参照 change 2035 的 golden 基线方法，记录复用点与本 Change 的差异。

### 任务 2：[ ] 降级路径与逐字节比对器

- 状态: 未开始
- depends_on: Task 1
- review_profile: strict
- 文档映射：`proposal.md` §6.1 输入与输出、§6.2 比对范围
- 文件：`scripts/downgrade_equivalence.py`、`scripts/` 测试目录
- context_files: Task 1 的裁决记录、change 2041 的开关契约、`scripts/`
- artifacts: 比对器实现、通过与不通过用例
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 提供单条命令，对同一输入分别走「production 降级到 tooling」与「纯 tooling」两路径。
    - [ ] 两路径的结构化判定输出按 Task 1 的范围与归一规则逐字节比对。
    - [ ] 一致时给出「通过」，不一致时给出「不通过」并列出首个差异点。
    - [ ] 通过与不通过各有用例。
    - [ ] 比对器不修改任一轨门禁脚本，通过导入或子进程调用现有脚本。
    - [ ] 比对器自身不产生非确定性输出（无未归一的时间戳或随机序）。
    - [ ] 连续两次运行输出逐字节相同。

### 任务 3：[ ] 「无法执行」判定与越界报告

- 状态: 未开始
- depends_on: Task 2
- review_profile: strict
- 文档映射：`proposal.md` §6.3 无法执行的判定、§7 验收标准 3-6
- 文件：`scripts/downgrade_equivalence.py`、`scripts/` 测试目录
- context_files: Task 1 的裁决记录、change 2036 的判据定义
- artifacts: 三态结论实现、五种无法执行用例、越界报告格式
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 三种结论（通过／不通过／无法执行）各有独立退出码与报告标注。
    - [ ] 五种「无法执行」情形逐一枚举并各有用例：开关不存在、开关无效果、基线缺失、输出格式不可比、（对照）不通过不混入此类。
    - [ ] 「无法执行」与「不通过」同判越界，但报告分开标注原因。
    - [ ] 「无法执行」默认即失败，不存在按「暂不适用」放行的分支，用检索证明。
    - [ ] 报告头部固定写明判据局限：只验「减去治理门后等于 Tooling」，不验治理强度。
    - [ ] 报告可被后续门层 Change 作为回归门直接调用，输出为机器可解析格式。

### 任务 4：[ ] 门禁零越界核对

- 状态: 未开始
- depends_on: Task 3
- review_profile: strict
- 文档映射：`proposal.md` §7 验收标准 10
- 文件：`scripts/` 测试目录
- context_files: `scripts/validate_change.py`、`skills/workflow-code-generation/scripts/check_delivery.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`skills/workflow-code-generation/scripts/lint_task_deps.py`
- artifacts: 四门禁零改动核对结论
- verification: `python -m pytest scripts -q`
- 验收标准：
    - [ ] 四个门禁脚本逐字节未改动（除非 change 2041 已改的部分，须逐处归因）。
    - [ ] 对全部活跃与归档 Change 跑四门禁，输出与改动前逐一比对无差异。
    - [ ] 确认比对器只是**调用**门禁，未把任何判定逻辑搬入比对器；用检索证明比对器内无 OPSX 判定或状态机转移逻辑。
    - [ ] `python -m pytest scripts -q` 全量通过，通过／跳过数与基线对照记录在案。

### 任务 5：[ ] 长期规格同步

- 状态: 未开始
- depends_on: Task 4
- review_profile: standard
- 文档映射：`proposal.md` §8 知识影响
- 文件：`openspec/specs/backend/framework/quality-gates/overview.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`
- context_files: `openspec/changes/2042-downgrade-equivalence-harness/proposal.md`、Task 1 的裁决记录
- artifacts: 两份长期规格
- verification: `python scripts/markdown_links.py openspec`
- 验收标准：
    - [ ] `quality-gates/overview.md` 记录降级等价比对作为门层改动的回归门，含三种结论与越界处理。
    - [ ] `framework-unification.md` 记录 §8.1 的降级等价判据现已有可执行实现。
    - [ ] 明确记录判据不证明治理强度，治理强度由 §3.2 条件 3 另行承担；不夸大为收敛已证明。
    - [ ] 记录依赖 change 2041 的 Profile 开关。
    - [ ] `python scripts/markdown_links.py openspec` 退出码 0。
    - [ ] 按 md-zh 规范自检中文排版。
