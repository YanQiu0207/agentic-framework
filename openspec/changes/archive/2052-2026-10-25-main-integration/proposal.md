# Main 整合与交付合同对齐

**状态**：Archived

## 目标与决策

按用户选择，以远程 `main` 的 `23d3473` 为行为基线，整合本地 `40b3e70` 的能力包门禁和 `4c856f1` 的 Review 评测、Runtime 重试及交付重跑修复。保留三条历史，不强推，不丢弃用户工作区改动。

## 合同取舍

- Native Delivery 默认使用 v2 内容主体绑定；strict 使用独立 Judge 及三项独立性声明，不因 strict、并行或恢复自动创建 Runtime Run。
- Runtime 仅显式选择、硬性审计或跨宿主验证时启用，并受 `runtime` 能力包门禁保护；SVN 不支持 Runtime，不静默降级。
- Fast-Path 仅保留兼容别名，不能绕过 v2 证据合同。原六字段报告仅作历史记录。
- 能力包查询与 VCS 探测从任务所在目录开始，不能先提升到外层 Git 根而跳过最近的 Manifest 或内层 SVN。已确认的 Runtime 执行仍使用 Git 仓库根。
- 活跃知识与执行指南同步上述合同；归档历史保留原结论，不将原 Runtime 修复验证冒充合并后验证。

## 实施与验收证据

- 整合提交：`36e0d46`、`7b62e28`；后续合同测试、嵌套目录防护及知识同步见本 Change 所在提交。
- 严格首审发现两项嵌套目录边界问题和一项活跃知识冲突；修复后信任链、需求符合度定向复审均无剩余 P0／P1。完整报告保留在整合工作区 `.agentic-framework/review/main-integration/`，原失败报告不覆盖。
- Windows 首轮全量：806 passed、24 skipped、2 failed。失败分别为测试 fixture 的 CRLF／LF 差异，以及符号链接权限不足（WinError 1314）。前者通过显式 LF fixture 修复并单独重测通过；后者不改为跳过、不弱化断言，转 Linux 验证真实符号链接。
- Linux（WSL Ubuntu 22.04）同一代码与测试快照：828 passed、5 skipped，23.63 秒；日志为 `.agentic-framework/verify/linux-full-tests-r1.txt`。两项 SWE-bench 测试改为跨平台路径 fixture，未改生产执行逻辑。
- 最终 v2 Verify、严格 Review 与交付门在 Linux 隔离仓库绑定同一内容主体。机器报告分轮保存在 `.agentic-framework/verify/`、`.agentic-framework/review/main-integration/`；最终门禁状态以实际报告为准，不由本文替代。

## 边界

- Windows 无符号链接权限场景未通过全量测试；后续具备权限环境的全量结果见下节，不据此宣称无权限环境也通过。
- 本次不重跑历史 Bug 的模型效果实验；评测结果沿用原证据，不将功能回归等同于效果提升。
- 本 Change 归档的是整合实现与验证决策；是否已推送以及用户工作区恢复状态须另查 Git 与恢复记录，不由归档状态推断。

## Windows 验证收尾（2026-10-25）

- 修复基线为 `7e4539e`。独立工作区为 `E:\github\.worktrees\windows-install-test-copy`，分支为 `fix/windows-install-test-copy`。
- `scripts/test_install_agentic_framework.py` 中三个无过滤的整仓复制统一复用已有 `_copy_source()`，保留全部测试断言和符号链接权限检查；未修改生产代码。其他 `copytree()` 调用仅复制测试 fixture 或单个 Skill，未扩大修改范围。
- Agent 在非管理员终端运行安装器专项：`rtk proxy python -m pytest scripts/test_install_agentic_framework.py -q --tb=short --durations=5`，结果为 31 passed、21 skipped，2.30 秒。权限相关跳过不作为完整验收。
- 用户在上述独立工作区完成 Windows 全量，命令为 `rtk proxy python -m pytest scripts -vv --tb=short --durations=20`；回传终端输出为 `833 passed in 275.13s (0:04:35)`，无失败、无跳过。来源是本次交接会话中用户提供的终端输出，不是 Agent 自行运行的管理员测试，也没有将该输出包装为内容主体绑定的机器 Verify 报告。
- 回传输出中，安装后的隔离项目验证测试耗时 3.06 秒；此前中断退出码 `0xC000013A` 仍仅代表被中断，没有运行堆栈证明旧停顿由整仓复制导致。
- 上述全量针对三处测试修复后的代码；随后仅补充本节知识记录。本轮增量审查不替代原整合的严格 Review 或交付门报告。
