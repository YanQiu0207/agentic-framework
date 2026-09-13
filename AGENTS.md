# 项目约定

## 版本管理

- 本项目使用纯 Git，Git 同时用于本地开发和正式提交。

## 框架 Profile

- 本项目使用 Tooling Profile，采用 DAG、Worktree、失败隔离和统一最终 Review。
- 机器来源（change 2041）：本仓库是框架实现仓库，存在 `.agentic-framework/` 运行目录但**没有** `manifest.json`；上面的「Tooling Profile」是散文声明，门禁不消费它。本仓库跑门禁时经 `--governance-profile tooling` 显式取得 Profile（无 CI 配置，本地与技能流程同一路径）；不传的调用只在没有任何 `lightweight` 声明时才不会触发 Profile 读取（惰性读取）。上级目录安装的 manifest 会被向上搜索继承——本仓库（E:\ 盘）不受 C:\ 用户目录安装影响，但嵌套项目应注意祖先链上的安装。

## 项目知识

- 项目知识存储在仓库内，由项目 Git 管理。
- 项目知识入口固定为 `openspec/index.md`。
- 项目知识和公共知识只用于辅助理解；代码、Schema、配置、测试和运行证据用于确认当前事实。
- 知识与当前事实冲突时，必须展示双方证据，不得静默选择或修改任意一方。

## 跨项目公共知识库

- 公共知识库入口为 `E:/work/shared-knowledge-base/index.md`。
- 公共知识库只保存经用户确认、脱敏和泛化后的跨项目知识。
- 项目专属知识不得写入公共知识库；未经用户确认的候选知识只能保留在当前项目。
- 公共知识只作通用参考；与项目代码、Schema、配置、测试或运行证据冲突时，必须报告冲突。

<!-- concord:start -->
## Concord — shared work-state for coding agents

<!-- concord:workflow-version=6 -->

This project uses Concord MCP. Keep coordination to the five workflow tools:

- **Before editing**, call `start_work` with the task, your agent kind, and
  expected files or modules. It registers presence, accepts assigned work when
  appropriate, claims the scope, and returns overlap warnings. Concord derives
  your `agent_id` from your session — omit it unless your client told you one.
- Use `inspect_work` to read the workspace, one task, one agent, or one message
  thread. Use `update_work` for durable progress and for live prompts/replies
  to another promptable workspace agent, including while that agent is busy.
- Use `transfer_work` for assignment, acceptance, decline, release,
  reassignment, evidence-bearing handoff offers, and reopening.
- **Before finishing**, call `finish_work` once with the outcome, changed
  files, tests, assumptions, decisions, risks, guardrails, and provenance. It
  records evidence and can mark work review-ready or terminal.

Keep each claim small and resolve reported overlaps before editing. Concord
regenerates human-readable review artifacts in `.concord/`.

Enforcement remains client-dependent. `concord doctor` reports setup and
workflow adoption; optional hooks can block exact-file collisions.

In Grok Build, keep this session reachable while idle by starting one persistent
monitor for `concord inbox watch --provider grok`. Do not start a duplicate when that monitor is active.

In Cursor, start exactly one Cursor background Shell task for `concord inbox watch --provider cursor --once`.
Leave it active when the turn ends. When Cursor resumes you with its completion,
answer the emitted peer message and immediately start a fresh background monitor.

In Gemini CLI, start the exact monitor command supplied by the SessionStart hook
(`concord inbox watch --agent <agent-id> --provider gemini --once`) with `run_shell_command` and `is_background: true`. Project
settings inject background completion into the agent. Answer the peer message,
then immediately start a fresh background monitor.
<!-- concord:end -->
