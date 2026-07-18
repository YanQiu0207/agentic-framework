---
name: opsx-code-generation
description: OpenSpec 代码生成。代码文件修改的统一入口，适用于 openspec 工作流。读取 openspec/changes/<change-name>/ 下的 proposal.md 和 design.md，生成 tasks.md，并逐个任务执行。
---

> 输出一行：`Using opsx-code-generation`

# OpenSpec 代码生成

> 所有代码修改的统一入口。**先加载规范，再写代码。**

## 工作流程

### 步骤 1：评估复杂度与路径路由

> ⚠️ **防御性检查**：如果 AI 无法明确回答「要改什么模块/文件」、「要实现什么行为」、「怎样算完成」这三个问题中的任何一个，则**立即停止**，调用 `opsx-requirements-clarification`。本 skill 不负责需求澄清。

**默认走标准流程**（步骤 2 → 3 → 4 → 5）。Fast-Path 仅当改动为**单文件、局部改动**时才可进入。

#### Fast-Path 执行

1. 加载编码规范（同步骤 4）
2. 实现改动
3. 执行过程中发现实际需要改多个文件 → **立即退出**，回到步骤 2 进入标准流程
4. 询问用户是否需要 code review
   - **需要** → 加载 `workflow-code-review` skill（指定 `skip_reviewers: [magical-prompt-reviewer]`）→ 修复循环
   - **不需要** → 输出改动说明
5. **结束**，不进入后续步骤

#### 标准流程入口

在 `openspec/changes/` 下查找变更目录，确认 `proposal.md` 存在：

- `proposal.md` 存在且完整 → **仔细通读全文**，同时读取 `design.md`（如有）和所有 `specs/*/spec.md`
- `proposal.md` 状态为 `Quick Draft` → 检查是否至少包含问题、目标、核心方案、验收标准；满足则可进入任务规划，否则调用 `opsx-quick-design` 补齐
- `proposal.md` 不存在/不完整 → **调用 `opsx-requirements-clarification`**（禁止自行澄清）

**强制**：`proposal.md` 与 `tasks.md` 同时存在时，编码前必须完整读取两者。

### 步骤 2：检查/创建 tasks.md

- **已存在** → 进入步骤 3
- **不存在** → **先读取** [reference/task_planning_guide.md](reference/task_planning_guide.md)，然后严格按其流程创建 `tasks.md`

> 🚨 **创建 tasks.md 后必须停下来等用户确认。** 展示任务列表，然后**停止并等待用户回复**。禁止自动进入步骤 3。

### 步骤 3：选定当前任务

从 `tasks.md` 中找第一个未完成任务，记录其编号和上下文。若全部任务均已完成且 Code Review 状态不是 `PASS`，直接进入步骤 5 的 Phase 3；状态已为 `PASS` 时结束，禁止重复评审。旧版 `tasks.md` 没有 Code Review 状态时，按 `Pending` 处理。

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

**核心规则：一个 Task → 实现 → 报告 → 等用户批准 → 下一个 Task；全部 Task 完成后统一执行一次 Code Review**

#### Phase 1：实现

修改代码，更新 `tasks.md` 标记 In Progress。当前 Task 涉及测试代码时，加载 `opsx-test-generation` skill 生成并运行测试；测试任务也是本次统一 Code Review 的审查范围。

#### Phase 2：汇报 → 继续或停止等待

输出报告，更新 `tasks.md` 标记 Completed：

- 仍有未完成 Task → **停止等待用户批准**
- 全部 Task 已完成 → 不再等待，直接进入 Phase 3

#### Task 完成报告模板

```markdown
---
## ✅ Task N 完成

### 改动文件
- `path/to/file.cc`: [改动说明]

### 改动内容
[做了什么，为什么]

---

仍有未完成 Task 时，询问用户下一步操作，提供以下选项：
- **继续/LGTM** → 下一个任务
- **修改** → 重新提交（用户附带修改要求）
- **回滚** → 撤销本次改动
```

#### Phase 3：全部任务完成后统一 Code Review（🚨 强制）

仅当 `tasks.md` 中全部 Task 均为 Completed 时执行一次统一 Code Review。加载 `workflow-code-review` skill，按其工作流审查本次变更的完整 diff，并指定 `skip_reviewers: [magical-prompt-reviewer]`。该 skill 会并行调用 reviewer subagent 执行审查——**禁止主 agent 自己做 review 代替 subagent**。

对报告中**每条** keep 的 finding，反思犯错原因：

| 原因分类 | 含义 |
|---------|------|
| **文档理解偏差** | proposal.md/design.md 写清楚了但理解错误 |
| **规范未遵守** | 编码规范有要求但未执行 |
| **执行遗漏** | 漏掉边界/细节 |
| **设计考虑不足** | 需更深层设计思考 |

修复 finding 后，按照 `workflow-code-review` 的 re-review 流程仅复核保留项和修复 diff，直到结论为 PASS。

评审通过后，将 `tasks.md` 中的 `Code Review` 状态更新为 `PASS`。

最终向用户输出 Review 总结，包含：

- 经历了几轮 review
- 每条发现的问题、修复方式和犯错原因
- 最终 PASS 的 review 报告

---

## 用户跳过文档时

必须生成简化版 `proposal.md`（标注 `状态：Quick Draft`）。**禁止无文档修改中等及以上复杂度的代码。**

## 恢复中断的任务

读取 `tasks.md` → 找未完成任务 → **重新加载编码规范** → 继续执行。
