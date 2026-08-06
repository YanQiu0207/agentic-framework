# 外部参考：AWS sample-codex-agent-team 多 Agent 协作样例分析

> 本文档是**外部开源样例的协议设计与对照分析**，不是当前框架的实现规格。作用是辅助理解多 Agent 协作协议的设计谱系，并对照当前框架的成熟度。补强点均为**候选并标注待核实**，未验证前不得当作当前框架的确定缺口。与代码冲突时以代码为准。

## 元信息

| 项 | 值 |
| --- | --- |
| 样例仓库 | github.com/aws-samples/sample-codex-agent-team |
| 分析基准 | 仓库 `main` 分支一手代码（2026-08-01 浅克隆逐文件精读）加文章《AWS 开源 Codex Agent Team：多 Agent 如何真正协作》 |
| 已读一手文件 | `AGENTS.md`、`team-spec-workflow`/`team-review-cycle`/`team-coordination` 三份 SKILL、`fullstack-agent.toml`、`review-agent.toml`、8 份 Spec 模板 |
| 仓库状态 | MIT-0 许可；约 16 commits、44 stars；无 Release/Tag；README 自声明「sample configuration, not a production-ready control plane」 |
| 核实范围 | 协议设计（Spec 模板、Spawn-Wait-Steer-Close、review-cycle）基于一手代码；文章所述行为测试与运行时缺口判断未由本项目复跑 |
| 底座依赖 | Codex（OpenAI）加 OpenAI 模型（`gpt-5.6-sol` / `gpt-5.6-terra`） |

## 一句话定性

它不是「多 Agent 调度框架」，而是一份「多 Agent 协作工程协议」的参考样例。它不跑 API、不存任务状态、不做 Agent 间文件隔离，而是把一支工程团队如何分工、共享事实、证明完成、失败收口写成 Codex 可反复读取的配置（5 个 Agent、9 个 Skill、3 个 Hook、命令护栏与 Spec 模板）。

## 适用场景

| 场景 | 适配度 | 说明 |
| --- | --- | --- |
| 借鉴多 Agent 协作的协议设计 | 高 | 文件所有权互斥、Spec 驱动共享记忆、独立评审门禁、三轮评审预算、沉默不等于失败 |
| Codex 加 OpenAI 技术栈 | 高 | 强依赖 Codex 平台能力与特定模型 ID，换底座需重写 |
| AWS 工程团队（含 IaC 与部署） | 高 | 内置 `sa-agent`（Well-Architected 六支柱）与 IaC MCP |

## 不适用或有保留的场景

- **直接上生产或高价值仓库**：README 自声明非生产级；所有纪律均为提示词协议，无运行时强制。
- **Windows 或跨平台**：Hook 硬编码 `/usr/bin/python3`、用 Unix 专有的 `fcntl`。
- **非 Codex 技术栈（含 Claude Code）**：配置格式是 Codex 专有（`.codex/`、`*.toml`、`hooks.json`）。

## 协议设计逐文件解读

### 1. Spec 模板层——共享记忆（`.codex/specs/<slug>/`）

8 份模板的分工：

| 文件 | 职责 | 关键设计 |
| --- | --- | --- |
| `requirements.md` | approved intent | 显式 Out of Scope 与 Open Questions，禁止规划阶段静默重设计 |
| `spec.md` | executable requirements | Interfaces And Contracts 独立成节，依赖任务前必须先冻结 |
| `design.md` | 架构 | 含 Alternatives、Rollout/Rollback，AWS 场景强制 Security Considerations |
| `tasks.md` | 波次化任务 | 任务契约见下 |
| `decisions.md` | 追加式轻量 ADR | Context、Decision、Alternatives、**Reversibility**、**Deviations from spec** |
| `review.md` | synthesizer 独占评审史 | 固定 7 节加 Verdict，承载全局 cycle 计数 |

三个最值得借鉴的机制：

- **事实优先级**（`AGENTS.md` Source Of Truth）：current files/diffs 是实现状态权威，`.codex/specs/` 是需求与所有权权威，fresh command output 是验证权威，returned messages 只是 evidence。stale 摘要与 silence 不覆盖当前磁盘。
- **task 状态语义**：`[ ]` ready、`[-]` in-progress、`[x]` completed-with-evidence、`[!]` blocked-with-cause。硬规则：不能仅凭 worker 声明标 `[x]`，必须 reconcile 返回结果、当前文件与新鲜命令输出。
- **任务契约**（`tasks.md` 单行）：`- [ ] [coding|devops|sa] <verb> <outcome> | <exact files> | <acceptance>. Run: <command>`，角色、精确文件、验收、验证命令一行闭合。

### 2. Spawn-Wait-Steer-Close——协调循环

权威定义在 `team-coordination/SKILL.md` 与 `fullstack-agent.toml`。Codex 无共享 task store，协调是显式原语：

| 原语 | 行为 | 关键约束 |
| --- | --- | --- |
| Spawn | 并发批量启动（一次 parallel tool calls，不串行等待） | pool size 等于当前波次 file-disjoint 宽度，不是 cap；under-provision 优先 |
| Wait | 等所有被请求的 agent 才 consolidate | 首个返回不等于可推进；缺失结果记 evidence gap，禁止臆造 |
| Steer | 对活跃 worker 做最小纠正 | 仅限澄清契约、传达决策、纠 scope drift、请求验证、叫停到不安全边界前；不得 steer 成更宽文件 scope |
| Close | 收割结果后关闭 completed、failed、idle | 最终前必做 active-worker check，确认无 required worker 仍活跃 |

Liveness 与 Recovery 是这一层的精华：

- **Silence is not failure**：quiet agent 可能在跑长构建、plan 或 review，仅凭时间、无消息或无可见进程不是死亡证据。
- **Positive evidence before recovery**：只有明确终止错误、确认进程结束、输出损坏，或 acceptance 无法完成的持久证据，才允许恢复。
- 恢复时关闭失败 agent 并保留 partial evidence，只 respawn 未完成的精确 scope，不重做已完成，不在 coordinator 线程接管大规模实现。
- late output 当 stale result，与当前 ownership 和磁盘比对后再用，禁止用 stale same-file 覆盖 replacement 的新工作。
- Recovery 不授予破坏性、计费或部署批准。
- Resume Hygiene：恢复时不重放旧 spawn plan，重读 tasks、decisions、review、files 与 agent 状态，按 positive evidence 把历史 worker 分类为 completed、active、failed、unknown。

Handoff Contract 规定每个 spawn prompt 必含 12 项：role 与 instance、spec dir 与 task 或 wave ref、精确文件 scope 与 no-edit boundary、acceptance 与 spec ref、produced 与 consumed 接口、依赖与 peer outputs、验证命令、expected output、peer 并发警告、是否 wait-all、外部与破坏性操作的批准边界。

### 3. review-cycle——独立评审（`team-review-cycle/SKILL.md` 与 `review-agent.toml`）

角色分离是权限边界，不是角色扮演：

- **Synthesizer**（`review-1`，唯一）：`review.md` 唯一作者，审分配 slice 加全波 cross-slice 一致性，等所有 analyst 或记录缺失，去重归因，发唯一权威 verdict。
- **Analyst**（`review-2` 至 `review-4`，可选）：审一个 file-disjoint slice，不写任何文件，只返回结构化 findings 与 advisory slice result。
- **独立性**：Lead 与 implementer 不能写权威 PASS；self-review 只是 TODO marker；若 `review.md` 出现 lead 或 implementer 写的 PASS，当 TODO 重做。

三轮预算是最硬的停止规则：

- 整个 user objective 共享最多 3 个 cycle，non-resetting。
- cycle 在 synthesizer spawn 时消耗（结果未知前），不是返回时。
- 计入 initial review、targeted re-review、replacement synthesizer、interrupted retry。
- 不因新 wave、fix、reviewer、file、process 或 resumed session 重置。
- Cycle 1 广谱对抗，Cycle 2 验修复加回归，Cycle 3 终局验证。
- 只有 Cycle 1 或 2 的 FAIL 可产生一个 scoped fix wave；Cycle 3 若 non-PASS，停止所有自动 fix 与 review，关闭 agent，保留证据，报告 BLOCKED，永不自动 spawn Cycle 4。

Evidence Discipline 要求引用 `file:line` 前重读当前文件，Critical 主张能执行就实证，不能执行降 Warning 并标 `requires live validation`，每条 finding 标 evidence class（static-verifiable、empirically reproduced、requires live validation），并 Verify the verifier（green 命令不够，要查 scope、CI-pinned 检查、acceptance 覆盖、断言完整、静态是否替代运行时）。

Live-Validation Gate：静态检查（lint、validate、synth、plan、unit test）证明不了 runtime account、region、backend、kube-context、config precedence、真实退出码、smoke target、destroy residue；需 deploy、smoke、teardown 或最接近的安全等价物；不能跑就标 static-validated only，记录 open gate，不暗示 runtime PASS。

## 与当前框架的维度级对比

两者设计哲学高度共振（Spec 驱动、文件所有权、独立评审、失败隔离、事实优先级、停止规则）。差异在于实现强度——AWS 样例多数停留在「提示词协议」，当前框架已落成「机器可验证或运行时强制」。

| 维度 | AWS 样例 | 当前框架（基于 framework-unification §3.3、§5.3、§6.3、§9 与 machine-verifiable spec） | 差距判断 |
| --- | --- | --- | --- |
| 事实优先级 | AGENTS.md 散文 | §3.3 代码事实源表加 project-knowledge 合同化加冲突显式报告 | 当前更强 |
| 文件所有权与并行隔离 | 提示词 scope 声明 | worktree 物理隔离加写锁加 DAG waves | 当前更强 |
| task 状态机器解析 | 自由文本加人工 reconcile | `scripts/task_ast.py` 公共 AST 加 OPSX 强制 | 当前更强 |
| 独立评审与角色分离 | synthesizer 加 analyst 提示词 | review_profile 分档加独立 Judge 加门禁失败关闭 | 当前更强 |
| Verify the verifier | 提示词 | machine-verifiable 核心行为可回归加 evidence-skipping 用例加配置弱化失败关闭 | 当前更强 |
| Recovery（沉默不等于失败） | 提示词 | 事件驱动恢复（Event Journal 加 Checkpoint）加状态源冲突失败关闭 | 当前更强 |
| 停止规则 | 三轮全局 non-resetting 预算 | 每 Scope 首轮加最多 2 轮复审，仍 `NEEDS_CHANGES` 标「需人工」终止（workflow-code-review 循环语义） | 当前等价（多 Scope 各自封顶），模型不同非缺口，见核实结论 |
| 静态与运行时验证 | Live-Validation Gate 显式区分 | verify.py 跑 exit_code、forbid_pattern、count 机器检查，无静态/运行时分级，验不了的检查不入配置 | 场景相关：云与部署扩展时值得引入证据分级，见核实结论 |
| 中途决策落点 | `decisions.md` 追加式 ADR | 决策在 design.md 备选加 custom/decisions.md 长期 | 见补强点 3 |
| Steer（纠进行中 scope drift） | 显式原语 | 有 escalate 与 approval（暂停与恢复），无显式最小纠正原语 | 见补强点 4 |
| 高风险命令护栏 | `.codex/rules/` 拦 `git push --force`、`terraform apply` | 门禁对象是 Change 生命周期（Plan、Delivery、Archive），非终端命令执行 | 场景不同，非缺口 |

## 补强点核实结论

补强点 1 与 2 已核实（读 `workflow-code-review` 与 `workflow-verification` 的 SKILL 实现）；3 与 4 仍待核实。

### 补强点 1：whole-change 全局 Review 预算——核实后判定非缺口

`workflow-code-review` 的循环语义已规定：仅 keep 的 P0/P1 触发「修复 → 复审」循环，**修复-复审最多 2 轮**，第 2 轮仍 `NEEDS_CHANGES` 标「需人工」终止，禁止继续循环；且每个 Scope 只有一次首轮，同一 Scope 的修复只能进 re-review。这是 per Scope 的硬上限（task、integration、run 各自首轮加最多 2 轮复审）。AWS 的「全局 3 cycle」是单一 integrated scope 模型下的设计；当前框架用「多 Scope 加每 Scope 2 轮加需人工终止」达到等价的停止效果——单一 Scope 不会无限自转。残留差异仅是「跨 Scope 的 change 级总轮数无上界」，属规模成本而非无限自转风险，不构成缺口。

### 补强点 2：静态/运行时验证分级——场景相关补强点（部分成立）

`workflow-verification` 的 `verify.py` 跑 `exit_code`、`forbid_pattern`、`count` 三类机器检查，按退出码判定；配置维护模式要求检查「不访问真实外部资源、不需要凭证」，即验不了的检查不写入配置。当前框架**无**「static-verified、runtime-verified、open-live-gate」的显式分级，也不显式记录「已静态证明 X、运行时行为 Y 仍 open」。`machine-verifiable` 的「语义结论边界」有「不超 claim」精神，但非静态/运行时分级。此补强点**仅在当前框架向云、IaC、部署场景扩展时**有价值（静态 `terraform validate` 与真实部署差距大，需显式 open gate）；纯软件代码场景下 `exit_code=0` 的测试已证明行为，当前模型够用。

### 补强点 3：mid-flight 追加式决策日志——待核实

判断基于 framework-unification，未核实 Change 目录与 archive 流程的实际落点。当前框架决策落点是 design.md（备选方案，规划期）与 custom/decisions.md（长期有效，archive 后同步），可能缺一个开发中临时决策、阻塞与偏离的轻量追加日志。AWS `decisions.md` 的 Reversibility 与 Deviations from spec 对中断恢复与多 Agent 交接实用。待核实 Change 目录是否已有等价机制。

### 补强点 4：Steer 原语——待核实

当前框架执行控制偏状态转移（route、escalate、approval_granted、merge_success）与暂停恢复。AWS 的 Steer 是对活跃 worker 做最小 scope 纠正但不扩宽文件 scope。待核实 `workflow_control.py` 是否有等价的进行中纠偏原语；worktree 隔离可能已隐式降低此需求。

## 结论

作为「协议设计参考」值得精读，不值得移植。当前框架在绝大多数维度已用机器化方式覆盖且更强。核实后，原 4 个补强点候选中：补强点 1（全局 Review 预算）判定非缺口，当前 per-Scope 复审上限已等价；补强点 2（静态/运行时验证分级）为场景相关补强点，仅在向云与部署扩展时值得引入；补强点 3 与 4 仍待核实。

## 信息来源与不确定性

- **已读一手代码**：`AGENTS.md`、三份核心 SKILL（team-spec-workflow、team-review-cycle、team-coordination）、`fullstack-agent.toml`、`review-agent.toml`、8 份 Spec 模板。协议设计解读以此为准。
- **来自文章、未复跑**：行为测试结果、`.gitignore` 缺失、MCP `@latest`、跨平台限制、Execpolicy 命令匹配等运行时判断。
- **对照部分**基于当前框架 `framework-unification.md`（§3.3、§5.3、§6.3、§9）、`machine-verifiable-agent-runtime/spec.md`，以及 `workflow-code-review`、`workflow-verification` 两份 SKILL 实现。补强点 1 与 2 已核实；补强点 3 与 4 仍需核实 Change 目录与 `workflow_control.py` 实现。

## 相关条目

- 通用协议设计与选型权衡（去项目化版）已晋升公共库：`multi-agent-collaboration-protocol.md`（`E:/work/shared-knowledge-base/domains/agentic-engineering/`）。本文档保留项目私有的维度对照与补强点核实。
