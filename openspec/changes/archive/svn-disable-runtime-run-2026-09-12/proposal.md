# Proposal: SVN 工作副本禁用完整 Runtime Run（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-09-12
**变更**：svn-disable-runtime-run
**状态**：Archived

---

## 1. 问题与目标

### 问题

完整 Runtime Run 的启动与交付门硬编码 Git 证据链：`runtime_workflow.py` 的 `initialize_run` 用 `git rev-parse --verify <sha>^{commit}` 校验 base/target commit（`scripts/runtime_workflow.py:190-204`），交付门用 `git status` 校验工作区干净（`check_delivery.py:438-454`）。SVN 工作副本没有 git commit，命中升级条件（如 `strict` 风险、审计要求）时 `init-run` 必然失败，且失败发生在业务副作用之前，`route` 输出层没有任何 VCS 层面的提前提示。

### 目标

- `workflow_control.py route` 在裁决前探测仓库 VCS：检测到 SVN 时恒输出 `native-delivery`，在 stderr 明示降级，升级原因保留在 `runtime_upgrade_reasons` 供下游核对。
- `SKILL.md` 步骤 1 / 步骤 5 与 `workflow-control/overview.md` 主链路节同步该契约。
- 补测试锁定降级行为与 `_detect_vcs` 探测逻辑。

### 非目标

- 不为 SVN 补齐完整 Runtime 支持（revision 证据链改造涉及 schema、Envelope 契约与交付门全链路，收益低）。
- 不改 Native Delivery 路径（其对 SVN 已有完整支持）。
- 不改 `runtime_workflow.py` / `check_delivery.py` 的 Git 校验本身。

### 验收标准

- `route --review-profile standard --audit-required` 在 SVN 工作副本输出 `"path": "native-delivery"` 且 stderr 含降级提示；Git 工作副本与非仓库场景行为不变。
- `python -m pytest scripts/test_workflow_control.py -q` 全部通过。
- `verify.py` 总判定 PASS。

## 2. 方案

### 2.1 实现

`workflow_control.py` 新增 `_detect_vcs(directory)`（Git 优先、二进制缺失降级探测下一后端、两者皆无返回 None，语义与 `verify.py:348-377` 一致，`git` 调用补 `-C` 更稳）；`route` 子命令在 `select_execution_route` 命中 `runtime-run` 且仓库为 SVN 时，stderr 提示并将 `path` 强制改为 `native-delivery`。

### 2.2 权衡

- **禁用而非补齐**：Runtime 的证据链（commit 校验、Envelope `commit_sha`、交付门 `git status`）逐层依赖 Git，补齐需改造 schema / 契约 / 交付门全链路；SVN 项目命中升级条件时走 Native Delivery 仍有 standard 集成 Review 与独立 Verify 兜底。
- **探测时机**：仅在命中 `runtime-run` 时探测（原生 Native 路径零子进程开销），语义等价于恒探测。

## 3. 知识影响

长期规格 `openspec/specs/backend/framework/workflow-control/overview.md` 主链路节补 SVN 禁用契约；`SKILL.md` 步骤 1 / 步骤 5 同步。无 Delta（Quick Draft），由任务直接落盘。
