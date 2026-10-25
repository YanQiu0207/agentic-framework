# Proposal: Task 级 Agent 隔离与手动技能（Quick Draft）

**日期**：2026-10-25
**状态**：Quick Draft，用户已批准设计与实施范围

## 1. 问题与目标

标准流程的串行例外允许主会话实现，与主会话只编排的上下文约束不一致。改为每个 Task 使用新 Agent，Git Task 使用独立 Worktree；轻量任务保持宿主直接执行。

同时复制上游 handoff 和 prototype 完整技能目录，仅手动调用，不接入现有流程。

## 2. 设计与裁决

- 单 Task、串行链、并行分支均按 Task 分配新实现 Agent；不同 Task 不复用 Agent。并发仍由依赖和文件冲突决定。
- 每个 Git Task 使用独立分支和 Worktree。前序验证并合并后，才能启动依赖它的新 Task；主会话只编排和串行集成。
- 同一 Task 的修复优先延续原 Agent、原 Worktree；Agent 无法恢复时，新 Agent 读取该 Task 现场接手，不丢弃证据。
- 无子 Agent 或 Git Worktree 能力时停止，只有用户明确批准后才可例外执行。
- 经用户追加确认，SVN 为正常支持的串行后端：每 Change 一个工作副本，每 Task 新 Agent，不因缺少 worktree 另行申请例外；不构造 Git 镜像。任务失败先停止该工作副本的所有后续写入，修复并验证或经用户确认隔离失败改动后再继续，不自动回滚或删除现场。既有更新、提交授权与交付语义不变；不宣称具备 Git 任务级工作区隔离能力。
- 对 change 2048 的裁决：替换串行不要求子 Agent 的执行者例外；默认 Native、显式 Runtime、Verify、最终 Review 与交付门不变。不新增 Runtime 能力探测。
- 原样复制技能正文与参考文件，仅补 prototype 的手动调用声明和 Codex policy，并新增手动命令入口。
- 安装器是静态白名单，必要接线仅向四个受管集合加入两个技能与命令，沿用现有安装生命周期测试。

## 3. 验收标准

- 执行入口、准备指南、下放指南和 R-7 行为用例一致；不再保留串行不派 Agent 的规则。
- 两个技能的相对引用完整，Claude 与 Codex 均禁止隐式调用。
- 技能图 lint、技能合同测试、安装生命周期测试通过；安装清单包含新增入口。

## 4. 影响范围与知识

修改 skills/workflow-code-generation/SKILL.md、reference/execution-setup.md、reference/delegated-execution-guide.md、evaluation/trigger-cases.md；新增 skills/handoff/、skills/prototype/ 和 commands/ 两个入口；修改 scripts/install_agentic_framework.py 与 scripts/test_interview_installation.py。长期合同同步 openspec/specs/backend/framework/workflow-control/overview.md。

## 5. 权衡

接受新 Agent 启动、上下文重读与 Worktree 管理成本，换取任务隔离和既有合并证据语义。不引入新控制器、Runtime 或自动原型路由。
