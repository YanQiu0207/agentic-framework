# Proposal：修复交付门知识影响检查的风险反转（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：knowledge-gate-risk-inversion
**状态**：Archived

---

## 1. 问题与目标

### 问题

`check_delivery.py` 仅在 Native Delivery 与 Fast-Path 执行知识影响检查。Runtime Run 传入 `--tasks` 与 `--spec` 且不传 `--native-delivery`，会跳过该检查。Scoped Delivery 必须同时传入 `--native-delivery`，因此已受既有检查覆盖；原 Proposal 对其遗漏的判断与当前代码冲突。

### 目标

- 四条交付路径都显式声明知识影响结论。
- Runtime Run 缺少 `--knowledge-impact`，或 `none` 缺少非空理由时失败关闭。
- Scoped Delivery 保持既有失败关闭行为，并输出可区分的路径名。
- 同步 Tooling 调用示例与长期 Specs。

### 非目标

- 不引入 Delta 与磁盘文件的交叉核对。
- 不改变 `hit`／`none` 的参数语义或自证边界。
- 不回填已归档 Change。

### 验收标准

- Runtime Run 缺少 `--knowledge-impact` 时以非 0 退出，并输出通用缺参错误。
- 四条路径在 `none` 缺少理由或提供非法取值时均失败关闭。
- 四条路径成功输出各自路径名与知识影响结论；`none` 时保留理由原文。
- `python -m pytest scripts -q`、Skill 图 Lint 与 Verification 通过。

## 2. 设计方案

### 2.1 整体方案

无条件调用既有 `check_knowledge_impact()`，删除只覆盖部分路径的条件变量。参数合同保持不变，仅把缺参错误改为通用表述，并按 Fast-Path、Native Delivery、Runtime Run 与 Scoped Delivery 选择成功输出的路径名。

### 2.2 核心组件

- `check_delivery.py`：统一知识影响检查与路径名输出。
- `test_check_delivery.py`：覆盖四条路径的成功与失败形态。
- `workflow-code-generation/SKILL.md` 与长期 Specs：同步参数合同和路径覆盖语义。

### 2.3 关键权衡

直接失败关闭会使历史 Runtime Run 调用缺参时转为失败，但不引入过渡开关，避免形成新的绕过入口。Scoped Delivery 只做回归覆盖和文案区分，不重复实现已有检查。

## 3. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。
- 索引无需更新：均为既有索引条目。

## 4. 运维

无新增服务、配置项、日志或指标。交付门命令新增的必填参数会通过现有非 0 退出码暴露遗漏调用。

## 5. 参考资料

- `skills/workflow-code-generation/scripts/check_delivery.py`
- `scripts/test_check_delivery.py`
- `skills/workflow-code-generation/SKILL.md`
