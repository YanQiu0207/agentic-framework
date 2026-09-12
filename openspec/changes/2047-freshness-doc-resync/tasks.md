# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 3
> 核心原则: 单任务线性执行，实现与验证同批交付

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `docs/framework-features-status-and-comparison.md` | 修改 | Task 1 | §1/§3/§4/§5/§6/§7 追平 2045 后现状 |
| `docs/harness-alignment/07-host-capability-alignment.md` | 修改 | Task 2 | 行号修正 + P1 未核实项解除 |
| `openspec/specs/backend/framework/meta.yaml` | 修改 | Task 3 | quality-gates 条目清除 2045 已删除的 opsx 指针 |

### 受影响接口

无（纯文档）。

### 构建系统变更

- 无。

## 任务列表

### 任务 1: [x] 状态文档追平仓库现状
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `docs/framework-features-status-and-comparison.md`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md §2.1 第 1 条
- 说明: 按 proposal §2.1 第 1 条逐节修改；§5 快照数字来自本次实测（547 passed、21 skipped、132 subtests；skills=27 commands=14 agents=8 errors=0 warnings=0）。
- context_files:
  - `README.md:86-115` — 双 Profile 路由现行表述
  - `openspec/index.md` — 现行任务路由
  - `docs/harness-alignment/07-host-capability-alignment.md` — 宿主对齐结论
- verification:
  - [x] 全文不再含 `opsx-requirements-clarification` 等 5 个已退役入口与 `skills/opsx-code-generation` 引用
  - [x] §5 数字与本次实测一致并标注日期
  - [x] Production 流程与 README「双 Profile 路由」一致
- 子任务:
  - [x] 1.1: 头部更新时间与 §1 结论
  - [x] 1.2: §3 架构两处
  - [x] 1.3: §4.1/§4.2 核心工作流
  - [x] 1.4: 新增 §4.12 harness/运行协议 + §4.11 补评测现状
  - [x] 1.5: §5 实测快照
  - [x] 1.6: §6.1 入口
  - [x] 1.7: §7 增量核验小节

### 任务 2: [x] 07 文档修正漂移并解除 P1 未核实项
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `docs/harness-alignment/07-host-capability-alignment.md`（修改）
- depends_on: [1]
- review_profile: standard
- 文档映射: proposal.md §2.1 第 2 条
- 说明: 守卫引用改 `:1125` `_event_governance_errors`；行数 1302/1478；installer 关键引用补函数名；P1 未核实项改写为已核验（Codex hooks，0.150.1+ 信任审核，来源 learn.chatgpt.com/docs/hooks）；§4.6 补 codex.json 静态默认值说明。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py` — `_event_governance_errors` 位置
  - `scripts/install_agentic_framework.py` — 行数与函数名
  - `harness/capabilities/codex.json` — 静态声明合同
- verification:
  - [x] 3 处漂移引用全部修正
  - [x] P1 节不再含「未核实项」，含来源
  - [x] `codex.json` 未被修改（保持待探测默认值）
- 子任务:
  - [x] 2.1: 行号/行数修正
  - [x] 2.2: P1 未核实项解除
  - [x] 2.3: §4.6 静态声明补注

### 任务 3: [x] meta.yaml quality-gates 来源指针修复
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `openspec/specs/backend/framework/meta.yaml`（修改）
- depends_on: []
- review_profile: standard
- 文档映射: proposal.md §1 问题 1（同类知识同步缺口）
- 说明: verify 门禁 WARN 暴露 `quality-gates` 条目仍引用 change 2045 已删除的 `skills/opsx-code-generation/SKILL.md` 与 `skills/opsx-archive/SKILL.md`（「来源路径不可用」WARN，改动前 19 条中含 2 条）。替换为现行事实源：`workflow-code-generation/SKILL.md`、`governance_guards.py`、`check_delivery.py`。复跑后「不可用」类 WARN 清零；剩余均为 `source_ref 停在 2026-07-20` 的 freshness 类非阻塞提示（既有维护项，超出本 change 范围，不在 Quick 内扩修 source_ref 重生成）。
- verification:
  - [x] `verify.py` 总判定 PASS，`来源路径不可用` WARN 为 0
  - [x] `harness/capabilities/*.json` 未被修改
- 子任务:
  - [x] 3.1: 替换两条失效指针为现行事实源

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal §1 问题 | Task 1, 2 | 两份文档的脱节清单 |
| proposal §2.1 | Task 1, 2 | 逐节修改方案 |
| proposal §2.2 权衡 | Task 1, 2 | §7 保留历史基线、codex.json 不改、§10 不动 |
| proposal §3 知识影响 | — | 无 Delta，无规格改动 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | 无长期规格改动 | — | — | — |

## 知识冲突

- 结论：无冲突。本次只把两份 `docs/` 叙述文档追平到代码与既有归档变更（2045/2046、2028-2030）已经描述过的现状，不引入新行为断言。

## 实际 Diff 核对

- 核对状态：PASS。
- 改动文件（本次 change 范围）：`docs/framework-features-status-and-comparison.md`、`docs/harness-alignment/07-host-capability-alignment.md`、`openspec/specs/backend/framework/meta.yaml`、新增 `openspec/changes/2047-freshness-doc-resync/`。
- 核对命令与结论：
  - `python -m pytest scripts -q` → 547 passed, 21 skipped, 132 subtests（verify B-tests-pass exit=0）
  - `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base HEAD` → 总判定 PASS（Z-spec-drift PASS：无代码文件变更；「来源路径不可用」WARN 由 2 条降为 0）
  - `python scripts/lint_skill_graph.py` → exit 0（skills=27 commands=14 agents=8）
  - 机械核验（脚本断言，非口头）：07 文档新增的 10 处「函数名 + 行号」引用全部命中；meta.yaml 三个新指针文件全部存在；两份文档的退役残留字样 grep 计数为 0；`harness/capabilities/*.json` 不在 diff 中。
- Review 说明（如实记录）：独立 Reviewer 子代理先后派出两批（general-purpose ×2），分别运行约 17 分钟与 12 分钟均未回报任何 finding，已停止；本 change 的 Review 结论以**机械核验脚本断言 + 三道门禁全绿**替代，未由被审方主观断言语义质量。建议下次会话或人工抽查时补一轮语义 Review（重点：状态文档 §4.12 新增小节的表述准确性、§7.0 表格措辞）。
