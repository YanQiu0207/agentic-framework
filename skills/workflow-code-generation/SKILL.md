---
name: workflow-code-generation
description: 代码文件修改的统一入口。当用户请求任何代码变更（新功能、优化、Bug 修复、重构）时必须首先调用此 skill。仅适用于代码文件（如 .cc/.cpp/.h/.go/.py 等），修改 .md 等非代码文件时不需要调用。它会评估复杂度、检查 spec.md、生成 tasks.md、并逐个任务执行。
---

> 输出一行：`Using workflow-code-generation`

# 代码生成

> 所有代码修改的统一入口。**先加载规范，再写代码。**

## 工作流程

### 步骤 1：评估复杂度与路径路由

> ⚠️ **防御性检查**：如果 AI 无法明确回答"要改什么模块/文件"、"要实现什么行为"、"怎样算完成"这三个问题中的任何一个，则**立即停止**，调用 `workflow-requirements-clarification`。本 skill 不负责需求澄清。

**默认走标准流程**（步骤 2 → 3 → 4 → 5）。Fast-Path 仅当改动为**单文件、局部改动**（能在路由阶段确定完整文件列表，且只涉及 1 个文件的局部修改）时才可进入。

> **无法确定 → 标准流程。**

#### Fast-Path 执行

0. **采集基线（仅当存在 `verify.config.json`）**：动代码前，加载 `workflow-verification` skill，运行 `verify.py --save-baseline .verify/baseline.json`；无配置文件则跳过。
1. 加载编码规范（同步骤 4）
2. 实现改动
3. 执行过程中发现实际需要改多个文件 → **立即退出**，回到步骤 2 进入标准流程
4. 询问用户是否需要 code review
   - **需要** → 加载 `workflow-code-review` skill（指定 `skip_reviewers: [magical-prompt-reviewer]`）→ 修复循环
   - **不需要** → 跳过 review，进入 4.5
4.5. **门禁验证（仅当存在 `verify.config.json` 或 `.verify/baseline.json`）**：code review 完成（或用户选择不 review）后，加载 `workflow-verification` skill。触发规则：只要「config 或 baseline 其中之一存在」就必须运行门禁，防止通过删除 config 绕过已采集的基线。
   - `.verify/baseline.json` 存在 → `verify.py --baseline .verify/baseline.json`（config 不存在时脚本自动报 ERROR）
   - 仅 `verify.config.json` 存在（首次引入配置）→ `verify.py`（无基线绝对校验）
   - 退出码 0：进入下一步；退出码 1（FAIL，有新增违规）：修复后重跑；退出码 2（ERROR，门禁自身故障）：**停止交付**，排查 config/工具/基线后再跑。**门禁通过前禁止向用户汇报完成。**
4.6. **交付前沉淀检查（🚨 强制，与 verify 门禁无关）**：本检查与 4.5 的 verify 门禁无关，**无论是否存在 `verify.config.json` 都强制执行**。加载 `project-knowledge`，**逐条对照其沉淀检查信号表**（架构决策 / 放弃方案 / 新红线约束），每行明确「命中 → 已沉淀到 <具体 ADR/章节>」或「未命中」，**禁止用一句笼统的「判定无需沉淀」代替逐条判定**；命中则写或更新 ADR 后再继续。Fast-Path 为无 spec 的局部改动，本步骤只做 intent 沉淀判定、不涉及 spec 归档。**未给出逐条判定结论前，禁止宣布完成。**
5. 输出改动说明（含沉淀判定结论），**结束**，不进入后续步骤

#### 标准流程入口

查找 `docs/design-docs/<module>/<feature>/spec.md`：
- 存在且完整 → **仔细通读全文**（不要只读关注的章节），确认理解
- 存在且状态为 `Quick Draft` → 检查是否至少包含问题、目标、核心方案、关键接口/数据模型（如适用）和验收标准；满足则可进入任务规划，否则调用 `workflow-quick-design` 补齐
- 不存在/不完整 → **调用 `workflow-requirements-clarification`**（禁止自行澄清）

**强制**：`spec.md` 与 `tasks.md` 同时存在时，编码前必须完整读取两者。

### 步骤 2：选定当前任务

从 `tasks.md` 中找第一个未完成任务，记录其编号和上下文。

### 步骤 3：检查/创建 tasks.md

- **已存在** → 找第一个未完成任务，进入步骤 4
- **不存在** → **先读取** [reference/task_planning_guide.md](reference/task_planning_guide.md)，然后严格按其流程创建 `tasks.md`

创建或更新 `tasks.md` 时，如果本次改动可能涉及不可逆/高影响的架构决策、放弃某方案或新增红线约束，加载 `project-knowledge`，预留一个「intent 沉淀」任务（最终在步骤 6 的交付前沉淀检查中收口）。

> 🚨 **创建 tasks.md 后必须停下来等用户确认。** 展示任务列表，然后**停止并等待用户回复**。禁止自动进入步骤 4。

### 步骤 4：加载编码规范（🚨 强制前置）

> **未加载规范就写代码 → 立即停止，先加载。**

#### 必须加载

| 规范 | 说明 |
|------|------|
| `bp-coding-best-practices` | 通用编码最佳实践 |
| `bp-performance-optimization` | 性能优化（所有代码都是性能敏感的） |

#### 按需加载

| 规范 | 何时加载 |
|------|----------|
| `std-cpp` | `.cc`/`.cpp`/`.h` 文件 |
| `std-go` | `.go` 文件 |
| `std-python` | `.py` 文件 |
| `bp-distributed-systems` | 涉及网络通信、多节点协调、一致性、故障恢复 |

### 步骤 5：逐个任务实现

**核心规则：一个 Task → review 通过 → 门禁通过 → 报告 → 等用户批准 → 下一个 Task**

#### Phase 0: 采集验证基线（仅当存在 `verify.config.json`）

若项目根存在 `verify.config.json`，在**动代码前**采集基线，供 Phase 2.5 对比：加载 `workflow-verification` skill，按其说明运行 `verify.py --save-baseline .verify/baseline.json`（脚本在该 skill 目录，不在项目根）。

> ⚠️ **信任前提**：verify.config.json 中的命令会以 shell 执行。在你自己的仓库中可直接运行；如果你在审查外部 PR 或分支，且 `verify.config.json` 包含未经审查的变更，**必须先人工确认其命令安全**再允许本 Phase 执行。

无 `verify.config.json` 时跳过本 Phase（对存量项目无侵入）。

#### Phase 1: 实现

修改代码，更新 tasks.md 标记 In Progress。

#### Phase 2: Code Review 与修复循环（🚨 强制）

**4a. 执行 Code Review**

加载 `workflow-code-review` skill，按其工作流执行（指定 `skip_reviewers: [magical-prompt-reviewer]`）。该 skill 会并行调用 reviewer subagent 执行审查——**禁止主 agent 自己做 review 代替 subagent**。

**4b. 逐条反思犯错原因**

对报告中**每条** keep 的 finding，反思犯错原因：

| 原因分类 | 含义 |
|---------|------|
| **Spec 理解偏差** | spec 写清楚了但理解错误 |
| **规范未遵守** | 编码规范有要求但未执行 |
| **执行遗漏** | 漏掉边界/细节 |
| **设计考虑不足** | 需更深层设计思考 |

**4c. 自动修复 → Re-review 循环**

修复 finding → 重新加载 `workflow-code-review` skill 执行 re-review → 重复 4b-4c，直到结论为 PASS。

中间轮次的报告和反思不需要展示给用户，内部处理即可。

**4d. 输出 Review 总结**

所有轮次结束（PASS）后，向用户输出一份总结，包含：
- 经历了几轮 review
- 每条发现的问题、修复方式和犯错原因
- 最终 PASS 的 review 报告

#### Phase 2.5: 客观门禁验证（仅当 `verify.config.json` 或 `.verify/baseline.json` 其一存在）

Code Review PASS 后、汇报前，跑 verify 门禁做客观判定。触发条件：**config 或 baseline 任意一个存在即运行**——防止通过删除 config 绕过已采集的基线。加载 `workflow-verification` skill，按其说明运行（脚本在该 skill 目录，不在项目根）：

- 若 `.verify/baseline.json` **存在**（Phase 0 已采集）→ `verify.py --baseline .verify/baseline.json`（config 不存在时脚本返回 ERROR，阻止交付）
- 若 `.verify/baseline.json` **不存在**（本次变更新增配置，Phase 0 跳过）→ `verify.py`（无基线绝对校验）

外部 PR 场景需确认 verify.config.json 内容可信再执行。

- 门禁 **PASS**（退出码 0）→ 进入 Phase 3。
- 门禁 **FAIL**（退出码 1，有新增违规）→ 回到 Phase 2 修复循环，修掉违规后重跑门禁，直到 PASS。
- 门禁 **ERROR**（退出码 2，工具缺失/基线损坏/配置漂移/config 缺失等）→ **停止交付**，不进入 Phase 3，也不按「新增违规」修代码；先排查配置/工具/基线问题，修复后重跑验证。
- 两者均不存在时跳过本 Phase。

> 基线对比只追究本次改动**新增**的违规；历史遗留项不阻塞，但本次不得放大。

#### Phase 3: 汇报 → 停止等待

如本 Task 引入了值得沉淀的 intent（架构决策 / 放弃方案 / 新红线约束），先按 `project-knowledge` 趁热写或更新 ADR，或保留「intent 沉淀」任务；功能整体交付时在步骤 6 统一收口。

输出报告，更新 tasks.md 标记 Completed。

> 🚨 **进入步骤 6 的把守**：标记 Completed 后立即检查 `tasks.md` 是否还有未完成任务。**若本 task 是最后一个未完成任务，禁止停在本 Phase 直接宣布交付——必须先转入步骤 6 执行交付前沉淀检查、给出逐条判定结论，再做最终交付汇报。** 仍有未完成任务时，停止等待用户批准，再进入下一个 task。

#### Task 完成报告模板

```markdown
---
## ✅ Task N 完成

### 改动文件
- `path/to/file.cc`: [改动说明]

### 改动内容
[做了什么，为什么]

### Code Review 结果

**Review 轮次**: [第 K 轮通过]
[附 workflow-code-review 输出的报告]

### 门禁结果（若启用 verify）

[附 verify 摘要：PASS / 新增违规及修复；未启用则标注 N/A]

---

询问用户下一步操作，提供以下选项：
- **继续/LGTM** → 若仍有未完成 task，进入下一个；**若本 task 是最后一个，强制转入步骤 6（交付前沉淀检查），禁止直接宣布交付**
- **修改** → 重新提交（用户附带修改要求）
- **回滚** → 撤销本次改动
```

### 步骤 6：功能交付与 intent 沉淀（🚨 强制，全部 task 完成后触发）

当 `tasks.md` 中所有任务均为 Completed（功能整体交付）时，**禁止直接宣布交付完成**，先走本步骤：

1. 加载 `project-knowledge`，执行其「交付前沉淀检查」。
2. **逐条对照** `project-knowledge` 沉淀检查信号表，对每个信号**逐行作答**「命中 → 已沉淀到 <具体 ADR/spec 章节>」或「未命中」——单句笼统的「判定无需沉淀」不构成有效判定。命中时写或更新对应 ADR，或确认 spec 的「备选方案 / 权衡」章节已写清。并**逐条核销**步骤 3 / Phase 3 预留的所有「intent 沉淀」任务。
3. 沉淀处理完成后，按 `project-knowledge` 归档约定把 `spec.md` 头部 `状态` 改为 `Archived`（文件原地保留）。

> 🚨 **强制发生**：未给出显式沉淀判定结论前，不得宣布功能交付完成。沉默 = 未完成。
> **现状类信息**（模块/接口/数据流怎么变）不沉淀——那是代码的职责。
> 若判定需沉淀但当前无法完成，在 `tasks.md` 建「intent 沉淀」任务，不要跳过。

---

## 用户跳过 spec 时

必须生成简化版 spec.md（标注 `状态: Quick Draft`）。**禁止无 spec 修改中等+代码。** 该路径交付前同样受步骤 6 约束：须经交付前沉淀检查，并按归档约定把 Quick Draft 状态改为 `Archived`。

## 恢复中断的任务

读取 `tasks.md` → 找未完成任务 → **重新加载编码规范** → 继续执行直至全部 task Completed。**最后一个 task 完成后必须进入步骤 6 执行交付前沉淀检查、给出逐条判定结论，再宣布交付——恢复路径不豁免步骤 6。**
