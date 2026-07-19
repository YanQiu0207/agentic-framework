# 实施任务清单

> 当前阶段：设计已落文档，代码尚未实施。
>
> 任务总数：7

## 执行图

```text
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
```

### 任务 1：[completed] 建立现状证据与设计边界

- 状态：完成
- depends_on：[]
- review_profile：lightweight
- context_files：`openspec/index.md`、相关长期 Specs、ADR 003、评测与 Engine 设计文档
- 文件：本 Change 的 `proposal.md`、`design.md`、`tasks.md` 和 Delta Spec
- verification：Markdown 排版、相对链接、OpenSpec 索引和 `git diff --check`
- artifacts：活跃 Change 文档与验证记录
- 验收标准：
    - [x] 区分现有能力、真实缺口和非目标。
    - [x] 保留现有双 Profile、`tasks.md`、质量门和 Agent-Agnostic 边界。
    - [x] 明确 P0/P1 及实施依赖，不提前引入完整工作流引擎。

### 任务 2：[pending] 定义统一 Envelope 与 Artifact Schema

- 状态：完成
- attempts：0
- control_stage：completed
- depends_on：[Task 1]
- review_profile：strict
- context_files：本 Change、ADR 003、现有 Review/Verify JSON 生产与校验逻辑
- 文件：`schemas/runtime/`、Schema 校验器与测试、仓库根 `.gitignore`
- verification：Schema 正反例测试、配置摘要与 Attempt 映射测试、`git check-ignore .agentic-framework/runs/test/run-manifest.json` 和全量 Verification
- artifacts：版本化 Schema、校验报告和迁移说明
- 验收标准：
    - [ ] Run、Task、Attempt、Artifact、Profile、Harness、Commit 和配置摘要具有统一语义。
    - [ ] `config_digest` 固定摘要规范化有效配置文档；`AGENTS.md`、Skill、Spec 和 Task 计划作为独立输入 Artifact 记录摘要。
    - [ ] Envelope 的 `attempt` 与 `workflow_control.py` 的 `attempts` 按「执行序号 = 已消费失败重试次数 + 1」转换，并覆盖首次执行、失败重试和不消费预算事件。
    - [ ] Review、Verify、Task、Event 和 Eval 使用共享 Envelope、独立 Payload。
    - [ ] 未知版本、缺失必填字段和非法关联失败关闭。
    - [ ] 确认 `schemas/runtime/` 为受版本管理的顶层共享合同目录，并将本地运行目录 `.agentic-framework/` 加入仓库根 `.gitignore`。

### 任务 3：[pending] 建立 Run Manifest 与证据图校验

- 状态：完成
- attempts：0
- control_stage：completed
- depends_on：[Task 2]
- review_profile：strict
- context_files：Task 2 Schema、质量门、交付门和符号链接/重解析点约束
- 文件：Run Manifest 生成器、校验器与测试
- verification：缺失、孤立、替换、串 Run 和路径逃逸测试
- artifacts：Run Manifest、证据图校验报告和端到端 Fixture
- 验收标准：
    - [ ] Artifact 路径、摘要、生产者和关系可验证。
    - [ ] Review/Verify 与目标 Run、Task、Attempt、Commit/Spec 绑定。
    - [ ] 缺失、孤立、被替换和串 Run 证据均被检测。

### 任务 4：[pending] 自动执行核心 Agent 行为评测

- 状态：完成
- attempts：0
- control_stage：completed
- depends_on：[Task 3]
- review_profile：standard
- context_files：`docs/tooling/08-evaluation-strategy.md`、现有 4 组 `evaluation/trigger-cases.md` 和 Task 2 Eval Schema
- 文件：Evaluation Runner、结果 Schema、基线和核心用例扩展
- verification：Runner 单测、核心用例实跑、基线比较和失败门测试
- artifacts：机器可读 Eval Result、基线和人类可读摘要
- 验收标准：
    - [ ] 复用现有 4 个核心 Skill 的 `trigger-cases.md`。
    - [ ] 自动覆盖触发、误触发、边界、档位路由、恢复、指令冲突和跳过证据。
    - [ ] 输出机器可读结果，并对关键维度独立执行回归门。

### 任务 5：[pending] 定义 Harness Capability Matrix 与 Adapter

- 状态：未开始
- depends_on：[Task 4]
- review_profile：standard
- context_files：本 Change、安装器 Profile/Pack 合同、Codex 与 Claude Code 接入文档
- 文件：能力声明、Adapter 接口、启动探测与契约测试
- verification：能力三态、必需能力失败关闭和可选能力降级测试
- artifacts：Capability Matrix、Adapter 合同和探测报告
- 验收标准：
    - [ ] Codex 与 Claude Code 使用同一能力词汇和三态语义。
    - [ ] 必需能力缺失时失败关闭，可选能力降级时留存证据。
    - [ ] 核心 Workflow 不复制产品专属分支。

### 任务 6：[pending] 实现 Run Event Journal 与恢复

- 状态：未开始
- depends_on：[Task 5]
- review_profile：strict
- context_files：Task 2 Event Schema、Task 3 Manifest、`workflow_control.py` 和现有恢复测试
- 文件：`events.jsonl` 写入、Checkpoint、重放和恢复测试
- verification：原子追加、序号、重放、幂等、冲突和中断恢复测试
- artifacts：事件账本、Checkpoint、恢复计划和验证报告
- 验收标准：
    - [ ] 事件只追加、序号稳定，关键副作用具有幂等键。
    - [ ] 中断后从事件和 Checkpoint 恢复，不扫描聊天记录猜状态。
    - [ ] Event、Manifest、`tasks.md` 与 Git 事实冲突时失败关闭。

### 任务 7：[pending] 固化 Trust Model 并完成端到端验证

- 状态：未开始
- depends_on：[Task 6]
- review_profile：strict
- context_files：Tasks 2～6 产物、质量门合同、独立 Judge 规则和项目知识同步规范
- 文件：长期 Trust Model、威胁用例、端到端测试和迁移说明
- verification：威胁用例、全量 Verification、Strict Review 和知识同步检查
- artifacts：长期 Spec/ADR、端到端报告、Review 报告和归档记录
- 验收标准：
    - [ ] 明确参与者、可信基座、独立性、人工覆盖和不可证明边界。
    - [ ] 覆盖伪造报告、替换 Artifact、串 Run、重复副作用和 Harness 能力漂移。
    - [ ] P0/P1 全部通过 Verification、独立 Review 和知识同步后才归档。

## 当前验证记录

- 文档阶段不修改代码、Schema、配置、Skills、Commands 或 Agents。
- 代码实施前必须重新核对当前事实，并按 `workflow-code-generation` 执行。

## 交付前 intent 沉淀检查

- 不可逆或高影响架构决策：命中 → 已记录到 `design.md`，当前仍为 Proposed，尚未写入长期 Specs。
- 放弃重要方案：命中 → 已记录不增加 Workflow/Reviewer、不直接引入完整 Engine/SQLite、不使用巨型 Schema。
- 新增红线约束：命中 → 已记录证据绑定、失败关闭、单向状态派生和 Trust Model 边界。
- 已验证故障根因：未命中。
- 跨项目知识候选：未命中。
- 普通变更：未命中。
