# 旧项目知识迁移记录

**日期**：2026-07-19

## 结论

- 迁移前逐文件映射和引用清单保存在 [`migration-plan.json`](migration-plan.json)。
- 已把当前双 Profile 和知识管理合同复制到 `openspec/specs/`，旧位置保留历史跳转入口。
- 已把 5 组旧 `docs/design-docs/` 产物复制到 `openspec/changes/archive/`，保留原文件名和正文。
- 已把 ADR 001、ADR 002 复制到当前项目工程知识目录。
- 已把 1 条已验证 Incident 复制到 `openspec/issues/incidents/` 并加入索引。
- 未删除、移动或覆盖任何旧文件，也未处理未跟踪产物。

## 边界

- 迁移前后的副本暂时并存，当前入口以 `openspec/index.md` 为准。
- 旧目录是否最终删除，必须在引用核对完成后由用户另行授权。
- `docs/tooling/` 是合并前历史研究快照，不纳入本次项目知识迁移。
