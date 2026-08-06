# 外部参考：Alibaba skill-up 及其与 HarnessX 的对比

> 本文档是 Alibaba `skill-up` 的外部项目研究与对照分析，不是当前框架的实现规格。项目自述、代码确认、推断与缺失证据分别标注；所有借鉴项在进入设计或实现前，仍须回到当前框架的代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 项目 | Alibaba `skill-up` |
| 定位 | Agent Skill 的评测与演进工具 |
| 代码仓库 | <https://github.com/alibaba/skill-up> |
| 用户手册 | <https://alibaba.github.io/skill-up/zh/> |
| 代码分析基准 | `c3b36d7ab6fd3fe2e4e31c21997f0b8cd241488c` |
| 技术栈 | Go 1.25、Cobra、YAML、OpenTelemetry；Apache License 2.0 |
| 核实范围 | README、CLI、Evaluator、Agent Adapter、Judge、Runtime、Report、`skill-upper`、E2E 测试布局与 CI 配置 |
| 运行验证 | 未完成。当前研究环境为 Go 1.20.4，无法解析项目 `go 1.25.0` 声明；`go test ./...` 未进入测试执行阶段，不能据此判断项目测试失败 |
| 微信文章 | 用户提供的微信文章页面因反爬未能可靠提取，未作为事实来源 |

## 一句话定性

`skill-up` 是面向 Agent Skill 作者的「评测执行器加对话式改进工作流」：它将 Skill 安装到真实 Agent Engine，运行声明式用例，进行 with-Skill / without-Skill 对照，通过规则、脚本或 Agent Judge 评分，并把报告交给 `skill-upper` 驱动下一轮修改。它不是 Agent Runtime，也不是类似 HarnessX AEGIS 的自主搜索算法。

## 为什么需要 skill-up

Agent Skill 通常由 `SKILL.md`、脚本、模板和参考资料构成。文件容易编写，但缺少统一机制回答以下工程问题：

1. Skill 是否被 Agent 正确触发和使用？
2. 换成 Claude Code、Codex、Qoder CLI 或 Qwen Code 后是否仍有效？
3. 安装 Skill 后是否真的优于没有 Skill？
4. 修改 Skill 后是否破坏已有行为？
5. 评测能否在本地和 CI 中复现？
6. 失败来自 Skill、Eval、Judge、Engine，还是运行环境？

`skill-up` 将「准备 Workspace、安装 Skill、调用 Agent、采集轨迹、评分、汇总报告」产品化为可版本管理的 CLI 流程。

## 核心组成

### skill-up：确定性评测执行器

主要职责：

- 加载并校验 `eval.yaml` 与 `cases/*.yaml`；
- 创建本地、Docker 或 OpenSandbox Runtime；
- 安装 Skill、MCP 和 Fixture；
- 调用真实 Agent Engine；
- 运行 with-Skill 和 without-Skill 对照；
- 执行 Expect、Judge、报告和 CI 退出码；
- 采集 Transcript、Token 与 Workspace 产物。

### skill-upper：对话式改进 Skill

`skill-upper` 本身是一份 Agent Skill，指导宿主 Agent：

1. 阅读目标 `SKILL.md` 并识别关键能力。
2. 创建或补充 Eval。
3. 执行 `skill-up validate` 和 `skill-up run`。
4. 根据结构化证据区分 Skill 缺陷与 Eval 缺陷。
5. 修改 Skill 或 Eval，并新增回归用例。
6. 先重跑失败用例，再运行完整评测集。

因此其「Evolution」本质上是「Agent 按工程流程执行测试驱动的文件修改」，修改质量仍依赖 Agent 归因、范围控制和 Review。它没有 HarnessX 的符号状态、开放编辑动作空间、Variant Isolation 或独立的候选推广算法。

## 配置与执行模型

### 目录布局

```text
my-skill/
├── SKILL.md
└── evals/
    ├── eval.yaml
    ├── cases/
    │   ├── basic.yaml
    │   └── edge-case.yaml
    └── fixtures/
        ├── repos/
        ├── scripts/
        └── mcp/
```

`eval.yaml` 定义 Runtime、Engine、Model、Skill、MCP、并发、重试、Baseline 和报告；每个 `case.yaml` 定义 Prompt、Fixture、Expect 和 Judge。

### 执行链路

```text
加载配置和用例
  ↓
应用用例过滤与 CLI Override
  ↓
校验选中用例
  ↓
加载凭据并创建 Agent Adapter
  ↓
展开 case × configuration
  ├─ with_skill
  └─ without_skill（启用 Baseline 时）
  ↓
创建 Runtime
  ↓
上传 Fixture、安装 MCP 和 Skill
  ↓
调用 Agent Engine
  ↓
采集回复、Transcript、Token 与 Workspace 产物
  ↓
Expect 快速检查
  ↓
Judge 评分
  ↓
Result、Benchmark、JUnit 与 HTML 报告
```

Evaluator 将用例和 with/without 变体放入同一个并发池，由全局信号量限制并发。

## Agent Engine 与 Runtime

### Agent Engine

内置适配：

- Claude Code；
- Codex；
- Qoder CLI；
- Qwen Code；
- 自定义本地命令；
- 自定义 HTTP Agent 服务。

统一 Agent 接口负责安装 Engine、MCP、Skill，运行多轮消息并返回 SessionResult。跨 Engine 对照可以暴露 Skill 发现、Prompt 注入、Tool Schema、MCP、会话和 CLI 参数差异，但各 Engine 的 Token、成本与事件语义不必然可直接比较。例如代码文档明确记录 Qoder CLI 的本地 Session 通常不提供有效 Token 数据。

### Runtime

| Runtime | 特点 | 主要边界 |
| --- | --- | --- |
| `none` | 在宿主机临时目录直接执行 | 不是安全沙箱；实现允许访问绝对路径，不应运行不可信命令 |
| `docker` | 本地容器隔离，可设 `deny_all` 网络策略 | 依赖 Docker；`allow_declared` 精细出口策略尚不支持 |
| `opensandbox` | 远程沙箱 | 依赖外部服务、网络和凭据 |

## Judge 与证据层次

| Judge | 适用内容 | 优点 | 风险 |
| --- | --- | --- | --- |
| `rule_based` | 退出码、关键词、文本规则 | 便宜、快速、可复现 | 容易只验证表面文本 |
| `script` | 文件、Schema、编译、测试、Diff | 最接近机器事实 | 需要维护脚本和 Fixture |
| `agent_judge` | 报告质量、语义完整性、代码审查 | 表达能力强 | 成本、波动、同源偏差和提示注入 |

推荐证据优先级：

```text
机器运行或 Script Judge > Rule-based > Agent Judge
```

Evaluator 会在 Expect 失败时短路，不再调用后续 Judge，既降低成本，也让确定性失败优先暴露。

## 典型用法

### 安装 skill-upper

```bash
npx skills add \
    https://github.com/alibaba/skill-up/tree/main/skills/skill-upper \
    -g \
    -a codex \
    -y
```

### CLI

```bash
skill-up validate
skill-up list-cases
skill-up run
skill-up run --baseline
skill-up run --include-case-name "basic-*"
skill-up run --engine codex --model openai/gpt-5
skill-up run --format json --format html --format junit
```

### 建议的对话式流程

```text
先创建并运行评测，只总结失败证据，不修改 Skill。
确认归因后，修复 Skill 或 Eval，并补充回归用例。
先重跑失败用例，再运行完整评测集。
```

把「评测」与「自动修改」分成两个明确阶段，可降低同一个 Agent 同时设计测试、修改实现并自我验收的风险。

## 优点

1. **范围聚焦**：专门解决 Skill 的评测、回归和 CI，而不是重建 Agent Runtime。
2. **with/without 对照**：不仅检查任务是否成功，还验证 Skill 是否产生净增益。
3. **Eval 即代码**：YAML、Fixture 和脚本可版本管理、Review 和持续回归。
4. **多 Engine 支持**：同一 Skill 可以在不同宿主 Agent 中验证兼容性。
5. **Judge 分层**：确定性 Expect、Script 和语义 Judge 可以按成本与可信度组合。
6. **产物完整**：提供结构化 Result、Benchmark、Anthropic 兼容 Grading、JUnit 和 HTML。
7. **CI 友好**：退出码、GitHub Action、镜像 Digest 和版本固定策略较完善。
8. **工程证据丰富**：仓库包含 Unit、Integration、E2E、CodeQL、Release Workflow 和大量 Fixture。

## 缺点与证据边界

1. **「Evolution」不是独立优化算法**：主要依靠宿主 Agent 按 `skill-upper` 指令修改文件。
2. **Eval 质量决定结论质量**：关键词断言、模糊 Judge、狭窄用例和训练—测试混用都可能制造虚假进步。
3. **缺少强制密封测试集**：开发 Agent 可以反复看到同一 Eval，最终 PASS 不能证明未见任务泛化。
4. **Agent Judge 不稳定**：可能受到模型偏好、输出风格、同源模型和提示注入影响。
5. **成本呈乘法增长**：用例、with/without、重试、多 Engine、多轮和 Agent Judge 会共同放大调用量。
6. **`none` Runtime 不是安全隔离**：不可信 Skill、Fixture 和 Agent 命令应放入 Docker 或 OpenSandbox。
7. **跨 Engine 指标不完全同义**：成功率可对照，但 Token、成本、事件和默认系统行为必须逐项核实。
8. **单次 Baseline 不能消除随机性**：需要多次采样、置信区间或显著性判断才能形成稳健结论。
9. **本次缺少独立测试复跑**：当前环境的 Go 版本不满足项目要求。

## 与 HarnessX 的关系

### 总体定位

| 维度 | `skill-up` | HarnessX |
| --- | --- | --- |
| 核心对象 | 单个 Agent Skill | 完整 Agent Harness |
| 主要目标 | 评测、回归和改进 Skill | 组合、运行和演化 Agent 行为 |
| 产品形态 | Go CLI + `skill-upper` Skill | Python Runtime + CLI + Lab + Processor |
| 执行底座 | 调用外部 Agent Engine | 自身提供 Agent RunLoop |
| 行为扩展 | 修改 `SKILL.md`、脚本和 Eval | 插入或替换 Processor / Bundle |
| 演化方式 | Agent 根据报告修改文件 | AEGIS 生成 Harness 修改并经门禁筛选 |
| 优化范围 | Skill 与 Eval | Context、Memory、Tools、Control、Sandbox 等 |
| Baseline | 原生 with-Skill / without-Skill | 主要通过 Benchmark 配置比较 Harness |
| CI 定位 | 强 | 更偏 Runtime 与研究实验 |
| 模型训练 | 不涉及 | 支持轨迹到 SFT / RL 以及模型—Harness 共演化 |
| 采用门槛 | 较低 | 较高 |

两者不是同层竞品：`skill-up` 回答「这个 Skill 是否有效」，HarnessX 回答「整个 Agent 应如何组合和演化」。

### 两种演进

`skill-up`：

```text
Eval 失败 → Agent 诊断 → 修改 Skill / Eval → 回归
```

HarnessX：

```text
运行轨迹 → Digester / Planner / Evolver / Critic
→ 生成 Harness 变体 → Verifier 与回归门禁 → 推广候选
```

HarnessX 的搜索范围和研究创新更强，成本与风险也更高；`skill-up` 的工程边界更窄，更适合进入日常 Skill 开发和 CI。

### 可组合关系

```text
组件级：skill-up 评测单个 Skill 或 Skill Bundle
系统级：HarnessX 组合 Context、Memory、Tool、Control 与 Skill
整体级：HarnessX Benchmark 评测完整 Agent
```

一个合理的组合流程是：

1. 使用 `skill-up` 为每个高价值 Skill 建立 with/without Baseline。
2. 将通过组件级验证的 Skill 接入 HarnessX。
3. 使用 HarnessX Benchmark 比较整体 Harness。
4. HarnessX 调整 Context、Memory、Control 或 Tool 组合后，再由 `skill-up` 验证单 Skill 未因宿主变化退化。

## 对当前框架的参考价值

当前仓库本身包含大量 `skills/`，因此 `skill-up` 比 HarnessX 更接近近期可落地的质量能力。

### 值得借鉴

1. **Skill 自带 Eval**：高价值 Skill 在自身目录维护 `evals/`、Fixture 和回归用例。
2. **with/without Baseline**：用数据证明 Skill 的净价值，而不是只证明任务能完成。
3. **Judge 分级**：机器验证和 Script Judge 优先，Agent Judge 只覆盖难以确定性表达的语义。
4. **跨宿主兼容验证**：至少对 Claude Code 与 Codex 的高价值 Skill 做双 Engine 回归。
5. **结构化报告接入门禁**：用退出码、JUnit 和证据产物进入现有 Verification 流程。
6. **修复转回归**：每个已验证 Skill 缺陷都应形成永久用例，而不是一次性 Prompt 修补。

### 不应直接照搬

1. 不应允许 `skill-upper` 无 Review 地循环修改到 Eval 全部通过。
2. 不应让同一个 Agent 同时拥有全部测试设计、Skill 修改、断言修改和最终验收权限。
3. 不应把 Agent Judge 的 PASS 当成机器验证。
4. 不应默认使用 `none` 执行有副作用或不可信的 Skill。
5. 不应把开发期间反复暴露的 Eval 当作泛化证明。
6. 不应一次性为全部 Skill 建立重型多 Engine 矩阵；应从高价值且可确定性验证的 Skill 试点。

### 最小试点候选

选择一个高频、输入输出明确、有脚本或文件产物且当前缺少回归测试的 Skill：

1. 建立 3～5 个开发用例。
2. 建立 1～2 个失败或边界用例。
3. 保留 2 个不向修改 Agent 暴露的密封用例。
4. 优先采用 `script`，其次 `rule_based`，最后才用 `agent_judge`。
5. 先在一个 Engine 上稳定，再扩展到 Claude Code 与 Codex。
6. 第一阶段只把 `skill-up` 作为评测执行器，不启用自动修复循环。

上述内容仅为外部参考候选，不代表当前框架已决定引入 `skill-up`，也不代表现有 Skill 测试能力存在已确认缺口。

## 来源与不确定性

### 一手来源

- 项目仓库：<https://github.com/alibaba/skill-up>
- 中文 README：<https://github.com/alibaba/skill-up/blob/main/README.zh.md>
- 用户手册：<https://alibaba.github.io/skill-up/zh/>
- Quick Start：<https://alibaba.github.io/skill-up/zh/guide/getting-started>
- Eval 配置：<https://alibaba.github.io/skill-up/zh/guide/writing-evals>
- `skill-upper`：<https://github.com/alibaba/skill-up/blob/main/skills/skill-upper/SKILL.md>
- Evaluator：<https://github.com/alibaba/skill-up/blob/main/internal/evaluator/README.md>
- Runtime：<https://github.com/alibaba/skill-up/blob/main/internal/runtime/README.md>
- Release：<https://github.com/alibaba/skill-up/releases>

### 证据标签

- **已确认**：配置格式、执行链路、Agent Adapter、Judge、Runtime、报告、CI 与测试布局由一手代码或官方文档支持。
- **项目自述**：评测与演进定位、推荐使用流程来自 README 和 `skill-upper`。
- **推断**：与 HarnessX 和当前框架的适配关系基于公开架构对照，尚未形成 Change 或实施证据。
- **缺失证据**：未完成 Go 1.25 环境下的本地测试、真实模型 E2E、跨 Engine 成本对照、密封测试泛化和生产 CI 运行验证。
