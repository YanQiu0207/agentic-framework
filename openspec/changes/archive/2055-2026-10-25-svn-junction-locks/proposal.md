# Proposal: SVN 与 Junction 任务根定位及共享写锁

**日期**：2026-10-25
**变更**：2055-svn-junction-locks
**状态**：Archived

## 1. 问题与目标

用户提供真实 SVN 项目的修复截图，并批准在新 worktree 内创建 Change 后立即实施。当前 `skills/workflow-code-generation/scripts/workflow_control.py` 的 `_repository_root()` 先解析真实路径且只识别 Git，导致 SVN 或外置 `openspec` Junction 的配置和运行锁定位错误。

目标：保持当前项目的逻辑根与配置作用域，同时确保多个项目入口指向同一真实任务文件时跨进程互斥写入。

## 2. 范围

- 修复 `_repository_root()`：逻辑祖先优先识别 `.git` 或 `.svn/wc.db`，真实祖先回退，非仓库保持原回退行为。
- 项目锁按逻辑根放置，新增基于真实任务路径的共享身份锁；保留旧锁兼容和统一超时。
- `scripts/test_workflow_control.py` 补 SVN、逻辑根、真实路径回退、跨进程竞争与锁释放回归测试。
- 同步 `openspec/specs/backend/framework/workflow-control/overview.md` 的锁机制说明。
- `init-run` 已使用根函数，不重复修改该调用。用户追加批准：一并修复 `route`／`recover` 及 `init-run` 的 VCS／能力检查作用域，并补回归测试。

## 3. 验收标准

1. SVN 根下的配置、项目锁定位到工作副本根。
2. Windows Junction 连接外置知识目录时，保留各项目逻辑根与配置位置；两个入口共享真实任务身份锁。
3. 持锁时另一个进程超时且任务正文不变，释放后可成功写入；旧锁兼容不退化。
4. 相关 pytest 测试与现有 Verify 配置通过，strict 集成审查由独立 Judge 裁决。

## 4. 知识影响与非目标

同步长期控制流概览；不修改安装配置，不启用 Runtime，不修改真实 SVN 项目或用户图片。临时目录身份锁仅协调相同系统临时目录下的进程，不声称提供跨主机或跨用户隔离。

## 5. 参考资料

- 用户图片：`E:/github/bak/picture/屏幕截图 2026-10-25 185250.png`、`185351.png`、`185412.png`（后两者沿用相同文件名前缀）。
- 当前实现：`skills/workflow-code-generation/scripts/workflow_control.py`。
- 回归测试：`scripts/test_workflow_control.py`。
