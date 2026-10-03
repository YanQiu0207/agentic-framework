# 执行准备

加载扩展规范时读取“Overlay 规范发现”；委派任务前读取“任务执行”；完整 Runtime Run 另需执行其中的初始化和 Adapter 检查。

#### Overlay 规范发现

编码或测试前，从当前已加载的核心 workflow `SKILL.md` 真实路径（必须解析目录链接和文件链接）向上定位框架根，再运行 `python <framework-root>/scripts/install_agentic_framework.py --validate-extensions .`。

框架根以同时存在 `scripts/install_agentic_framework.py` 和 `skills/workflow-code-generation/SKILL.md` 为准；不得把链接入口（如 `~/.codex/skills/workflow-code-generation`）的父目录直接当作框架根。

无法确定该受信框架根时不得加载 Overlay，并报告失败。

只消费其 JSON 输出；目标文件后缀匹配 `skills[].files` 时，才加载当前 client 的对应 Skill。

不得直接读取 `.agentic-framework/extensions/*.json`，也不得从目标项目 Manifest 的 `source` 获得可执行路径。

Overlay 只补充规范，不自动执行、不覆盖核心 Skill，也不修改 workflow。

## 任务执行

`tasks.md` 经用户批准后，执行下放给 Agent：**主会话只编排，不亲自写代码、不逐 task 停等**，全部跑完一次性汇总。除非命中 Runtime 升级条件，标准流程默认使用 Native Delivery，不创建 Run Context。**先为每个 task 判定 review 档位**：

| 档位 | 适用 |
| --- | --- |
| `lightweight` | 小需求 / 低风险：局部改动，或不改变接口、契约、控制流与模块交互的跨文件机械重复改动；不碰数据 / 权限 / 并发 / 安全 / 性能关键路径 |
| `standard` | 默认档：普通功能、Bug 修复，或涉及多个模块之间的行为、契约、交互变化但风险可控 |
| `strict` | 高风险：生产关键路径、安全 / 权限 / 数据迁移 / 并发 / 分布式 / 性能敏感 / 公共 API / 大范围重构 |

无法判断风险时选 `standard`；命中高风险任一条件时选 `strict`。

各 task 的档位用于选择最终 Review；owner / implementer 禁止在 task 内启动 LLM Review。

无 `strict` 风险及 `--parallel-worktree-write`、`--long-task-recovery`、`--cross-host-capability-verification`、`--audit-required` 任一升级条件时，直接进入 Native Delivery，不运行恒为 `native-delivery` 的 `route` 步骤。

可能命中升级条件时，主编排方才在业务副作用前运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> route --review-profile <最高档位>` 并传入对应 flag；输出 `runtime-run` 时才进入完整 Runtime Run，输出 `native-delivery` 时不得创建或伪造 Run Context。

SVN 工作副本下 `route` 恒输出 `native-delivery`（见步骤 1）。**主会话只在并行分支、非线性依赖图或中断恢复时通过控制流内核构建波次（wave）数组**：先运行 `python <本 skill 目录>/scripts/workflow_control.py <tasks.md 路径> waves` 得到任务 ID 分层数组，按 [下放执行指南](delegated-execution-guide.md) 将当前一波的每个任务 ID 富化为 task 对象（从 `tasks.md` 取 `title`、`context_files`、`verification`、`artifacts`、`review_profile`）后再传入 Workflow 工具的 `args.waves`。

仅该路径在每波 dispatch 前运行 `dispatchable`。

单 task 或纯串行的小任务按 `tasks.md` 顺序直接执行 `event <id> start --write`；该命令仍校验前置依赖与 Verify 配置选择，不得绕过。

缺 `depends_on` 时先由 `lint_task_deps.py` 报错，修复前禁止全并行。**禁止另写一套手工分波或状态判断**。**先判定 CLI 嵌套能力**（派子 agent 试再派孙 agent；判定细则与 5 层上限见 reference 手册），选编排模式：
- **模式 A（默认，Claude Code 支持嵌套）**：每 task 派 owner 子 agent 执行实现、测试和机器验证。
- **模式 B（兜底，不支持嵌套）**：implementer 执行相同职责，由主 agent 负责状态编排。**详细操作（Phase 0 准备 / Phase 1 逐波执行 / 失败隔离 / 合并 / 阻塞）见 [下放执行指南](delegated-execution-guide.md)，按其执行。** 执行要求：每产物必须完成实现、测试和任务级机器检查后才合并；LLM Review 只在全部任务合并并完成全局验证后启动一次。

失败标 `需人工` 不阻塞其余；上游未合并则下游 `阻塞`；`tasks.md` 的 `状态:` 字段是恢复执行的状态依据。

当路由为 `runtime-run` 时，Phase 0 必须先调用 `workflow_control.py <tasks.md> init-run`，传入 `.agentic-framework/runs/<run-id>`、Spec、`AGENTS.md`、本 Skill、Harness 声明与 Adapter 命令。

该命令在业务副作用前冻结规则输入与完整 Task Plan、生成 Run Context、执行 Harness 启动能力门并创建 Journal；失败时禁止 dispatch。

此路径的每次 `quality_passed --write` 必须同时传 `--run-dir` 和该次执行生成的 Envelope Verify Artifact，旧式无 Run/Task/Attempt 绑定的顶层 `PASS` JSON 不得放行。

路由为 `native-delivery` 时，不调用 `init-run`；`quality_passed --write --verify-report <standalone-report.json>` 必须校验 `PASS` 顶层结论、零错误／违规，以及每项完整的 `CheckResult` 合同，不写入任何 Run Artifact。**定位内置 Harness Adapter**：Adapter 只负责 Runtime 启动时的能力探测，不负责启动或下放 Agent。

仅 `runtime-run` 执行本段；`native-delivery` 不要求 Adapter，不得因 Adapter 未探测而阻塞实现。

先对当前 Skill 路径执行等价于 Python `Path(skill_path).resolve()` 的解析，再逐级向上查找框架根；框架根必须同时包含 `scripts/codex_adapter.py`、`scripts/claude_code_adapter.py` 和 `harness/capabilities/`。

禁止只检查链接入口目录下是否存在 Adapter，因为 Adapter 位于框架根的 `scripts/`，不位于 Skill 自身的 `scripts/`。

| 宿主 | Harness 声明 | Adapter 命令 |
| --- | --- | --- |
| Codex | `<framework-root>/harness/capabilities/codex.json` | `python <framework-root>/scripts/codex_adapter.py` |
| Claude Code | `<framework-root>/harness/capabilities/claude-code.json` | `python <framework-root>/scripts/claude_code_adapter.py` |

`init-run` 的 `--required-capability` 只声明本次任务确实依赖的能力；不得因为 Adapter 将 `subagents` 或 `worktree_isolation` 报为 `unsupported`，就误判为「没有 Adapter」。

未被声明为 required 的能力按降级模式记录，不阻塞主宿主通过原生 Agent 工具执行。

只有按上述真实路径算法仍找不到内置 Adapter、Adapter 进程执行失败，或任务明确声明的必需能力确实不受支持时，才将 Harness 启动门报告为阻塞；不得用临时脚本伪造探测结果。

若框架根存在 Adapter，而当前宿主缺少某个可选能力，必须切换到已定义的降级模式继续执行，不能停在「尚未获准下放代码实现」。
