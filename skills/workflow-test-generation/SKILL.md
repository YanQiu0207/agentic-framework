---
name: workflow-test-generation
description: 基于活跃 Change 或代码生成测试。用户要求补测试、采用 TDD，或代码生成流程内嵌写测试时使用。
---

> 输出一行：`Using workflow-test-generation`

# 测试生成

## Step 0: 意图识别与路径路由

根据调用上下文判断走哪条路径：

| 信号 | 路径 | 执行步骤 |
|------|------|---------|
| 由 `workflow-code-generation` 的 owner/implementer 在 task 内**内嵌调用**（无人值守） | **内嵌路径** | Step 2 → 3 → 4；**跳过 Step 1.5**（遇到前端 UI 场景自动降级为单元/集成测试并记录原因）**、跳过 Step 3 用户确认、跳过 Step 5**（测试通过后交还编排方，全部任务完成后统一 Review） |
| 用户明确提到完整需求管理链接 | **完整流程** | Step 1 → 2 → 3 → 4 → 5 |
| 用户直接说"给 X 写个测试"/"补个单测"，指定了具体代码 | **快速补测试** | Step 2 → 3 → 4 |
| 由 `workflow-system-design` 讨论测试计划章节时加载 | **测试策略设计** | Step 1 → 2 → 3，只输出计划，不生成代码 |

> 如果无法判断，默认走**完整流程**。

---

## Step 1: 收集测试上下文

> **完整流程**和**测试策略设计**执行本步骤。**快速补测试**跳过（用户已指定了被测代码）。

先读取 `openspec/index.md`，再尝试读取
`openspec/changes/<ticket>-<change-name>/proposal.md`、`design.md` 和 Delta。按测试范围定向读取相关
`openspec/specs/business/`、`openspec/specs/common/` 和 `openspec/issues/`，并用代码与测试证据核实知识：

**有活跃 Change**：
1. 读取 "7. 测试计划"
2. 测试计划明确 → 进入 Step 2
3. 测试计划不完整 → 补充读取 "2. 目标"、"3. 需求"、"4. 设计方案"，自行判断

**无活跃 Change**（为已有代码补测试）：
- 询问用户要测哪些函数/类，基于代码生成

知识与代码冲突时必须同时报告知识结论和代码证据；不能把知识或当前实现直接当作预期行为。

## Step 1.5: 前置条件检查（仅浏览器测试）

如果测试范围涉及前端 UI 操作路径，检查以下浏览器测试前置条件；不以 `.tsx` 后缀作为唯一判断依据。纯 API、CLI 或消息驱动的系统级 E2E 不需要 Playwright，在 Step 3 检查其服务、数据与依赖环境。

```
检测到前端 UI 场景。
浏览器验证优先使用 playwright-mcp-parallel MCP，以支持多个隔离浏览器实例并行执行。
若要生成可提交到项目的 E2E 测试代码，项目仍需要 Playwright 测试运行器。
请确认：
- MCP 可用：playwright-mcp-parallel
- 项目 E2E 测试运行器可用：npx playwright --version
- 项目 E2E 浏览器已下载：npx playwright install chromium
```

未安装 / 未配置时告知用户命令，等待确认后继续；若用户跳过则只生成单元 / 集成测试，记录「E2E 未生成，原因：未配置 playwright-mcp-parallel 或项目 Playwright 测试运行器」。

---

## Step 2: 确定测试类型

根据代码特征自动判断需要哪些测试类型（**可组合，非互斥**；一个 feature 常组合多种），无法判断时才询问：

| 特征 | 测试类型 |
|------|----------|
| 纯函数、无外部依赖 | 单元测试 |
| 多组件或服务之间的协作 | 集成测试；跨服务接口兼容时补充契约测试 |
| 从系统入口到最终业务结果的完整链路（API、CLI、消息或 UI） | 系统级 E2E；按声明的系统边界验证真实协作，不按进程数量判断 |
| proposal.md 或 design.md 有性能指标要求 | 性能测试 |
| 前端 UI 操作路径 | 前端隔离测试；关键完整业务链路补充浏览器 E2E（Playwright） |
| 网络通信、多进程协作、复制或故障恢复 | 按风险增加分布式专项场景，与上述测试层级组合 |
| 多线程、共享状态或并发生命周期 | 按风险增加并发专项场景，与上述测试层级组合 |

非内嵌路径选中浏览器测试后，先执行 Step 1.5，再进入 Step 3；测试策略设计路径仅记录前置条件，不安装或执行测试。内嵌路径保持 Step 0 的降级与记录规则。

## Step 3: 制定测试计划

先检查当前 Change 是否已有用户批准的测试计划及接点；范围和契约未变时直接复用，不重复要求用户确认。Quick Draft 从 proposal.md 读取，标准 Change 从 design.md 第 7 节读取。需要选择或改变测试接点时，加载 `bp-component-design` 并读取其 `reference/deep-modules.md`，按「行为 → 模块／接口 → 替换依赖 → 验证证据」补齐计划。优先验证公开行为，不绑定内部函数或对象布局；重构时先建立等效保护再迁移测试。

发现计划与当前契约冲突或范围变化时，不擅自改变预期行为；独立路径请求用户确认受影响决定，内嵌路径记录阻塞原因并交还编排方处理，不在无人值守任务中重复等待用户。未发现上述变化的内嵌路径按原路由继续。

分析被测代码，制定测试计划（不生成代码）：

1. 读取被测代码，识别公共接口、输入/输出、副作用、需要 mock 的依赖
2. 读取 [reference/boundary-checklist.md](reference/boundary-checklist.md)，选择适用的边界条件
3. 按实际测试范围加载专项参考，不要求每次运行完整场景库：
    - 前端 UI：[reference/frontend-testing.md](reference/frontend-testing.md)
    - 网络通信、多进程协作、复制或故障恢复：[reference/distributed-testing.md](reference/distributed-testing.md)
    - 多线程、共享状态或并发生命周期：[reference/concurrency-testing.md](reference/concurrency-testing.md)
    - 项目已有模块测试参考：按需读取并复用
4. 为每个测试目标列出：正常路径、边界条件、异常场景的具体测试点；专项场景记录适用条件、测试边界、真实／替换依赖、操作或故障注入、预期不变量、完成期限与验证证据。不适用项说明理由；环境缺失的适用项标记待验证，不冒充已覆盖。

创建测试任务清单，**与用户确认**后再继续（已有适用批准或内嵌路径除外，见上文及 Step 0）：

```
示例：
1. [pending] UnitTest - FooClass::Bar() 正常路径 + 边界条件
2. [pending] UnitTest - FooClass::Bar() 异常处理
3. [pending] IntegrationTest - 组件协作
4. [pending] E2E - 系统入口到最终业务结果
```

> **测试策略设计路径**到此结束。将测试计划输出为 design.md 测试计划章节的内容，不进入 Step 4。

## Step 4: 逐个生成测试

> **完整流程**、**快速补测试**和**内嵌路径**执行本步骤；内嵌路径跳过独立用户确认与 Step 5，测试通过后交还编排方。

### 4.1 加载编码规范（🚨 强制前置）

| 规范 | 何时加载 |
|------|----------|
| `bp-coding-best-practices` | 始终 |
| `std-cpp` | `.cc`/`.cpp`/`.h` 文件 |
| `std-go` | `.go` 文件 |
| `std-python` | `.py` 文件 |

根据项目需要，额外加载其他编码规范 skill。

#### Overlay 规范发现

编码或测试前，从当前已加载的核心 workflow `SKILL.md` 真实路径（解析链接后）向上定位框架根，再运行 `python <framework-root>/scripts/install_agentic_framework.py --validate-extensions .`。无法确定该受信框架根时不得加载 Overlay，并报告失败。只消费其 JSON 输出；目标文件后缀匹配 `skills[].files` 时，才加载当前 client 的对应 Skill。不得直接读取 `.agentic-framework/extensions/*.json`，也不得从目标项目 Manifest 的 `source` 获得可执行路径。Overlay 只补充规范，不自动执行、不覆盖核心 Skill，也不修改 workflow。

### 4.2 逐个生成

对每个测试任务生成测试代码。每个测试目标的用例集合必须覆盖三类适用场景，不要求单个用例混合执行全部场景：
1. **正常路径** — happy path
2. **边界条件** — 基于 Step 3 选出的 boundary-checklist 条目
3. **异常场景** — 错误输入、异常处理

生成后更新构建配置，复用项目现有的测试基类和断言工具（不要自己造）。

#### 专项测试执行

按 Step 3 选定的专项参考生成测试。浏览器测试使用 `frontend-playwright-verification` 的浏览器／Playwright 规范，并遵循前端参考中的隔离测试与全链路 E2E 边界；非浏览器 E2E 复用项目现有运行器，不强制引入 Playwright。

分布式和并发测试必须验证计划中的业务不变量及恢复／终止条件，不能只断言进程存活或无异常。故障注入仅在获授权的隔离测试环境执行，设置超时并在失败时恢复故障、清理本次创建的资源；未获授权或环境不可用时停止相关执行，报告待验证项，不修改生产环境。

每完成一个任务，标记 `[completed]`，继续下一个。

## Step 5: 收尾流程

> 仅**完整流程**执行本步骤（其余路径见 Step 0 路由表）。**前置条件**：所有测试用例已通过。

提示用户进入 `workflow-code-review` 进行 AI 代码评审（同时评审功能代码和测试代码）：
```
自测已全部通过。

推荐下一步：
- 说"CR"或"代码评审"进入 AI 代码评审阶段
```

---

## 强制规则

1. **测试计划必须经用户确认后才能生成代码**（已有适用批准直接复用；内嵌路径除外，见 Step 0；范围变化与契约冲突按 Step 3 处理）
2. **必须覆盖三类场景**：每个测试目标覆盖适用的正常路径、边界条件与异常场景，不适用项说明理由
3. **必须应用 boundary-checklist**：Step 3 中读取并选择适用条目
4. **必须可编译运行**：包含所有必要头文件/导入，更新构建配置
5. **复用现有基础设施**：使用项目的测试基类和断言工具，不要自己造
6. **测试全部通过才能推进**：编译失败或用例未通过时，先修复，确认全部 PASS 后才可进入 CR
