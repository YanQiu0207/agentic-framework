# Proposal：新鲜度权威文档与 07 号对齐文档追平仓库现状（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-09-12
**变更**：freshness-doc-resync
**状态**：Active

---

## 1. 问题与目标

### 问题

一次全仓一致性审查（2026-09-12，本 change 的直接来源）发现两份文档与仓库现状脱节：

1. **`docs/framework-features-status-and-comparison.md`（更新时间 2026-07-19）落后于 7-19 之后的多个已归档变更**：
   - §4.1/§4.2/§6.1 仍描述「两族 Lifecycle Skills」与 `/opsx-*` 五个入口，而 change 2045（`6513ddc`）已退役全部 `opsx-*`，统一为 `workflow-*` 入口 + `governance_guards.py` 执行期守卫；README:90 与 `openspec/index.md` 均已更新，本文没有。
   - §4.2 引用 `skills/opsx-code-generation/SKILL.md:84-103`——该目录已在 2045 中删除，证据指针失效（`verify.config.json` 要求本身仍成立，现接在 `workflow-code-generation/SKILL.md` 与 `workflow_control.py`）。
   - §5 实测快照数字（155 passed / 32 Skills / 20 Commands）与当前实测（547 passed、21 skipped；skills=27 commands=14 agents=8）严重漂移，且 §11 自称「以第 5 节实测为准」形成自指失效。
   - 完全未覆盖 7-19 后落地的能力：`governance_guards.py` 治理守卫、`harness/` Capability Matrix 与 Adapter 探测合同、`evaluation/swebench` 与 Native Delivery 试点、`machine-verifiable-agent-runtime` spec、SVN 工作副本强制 native-delivery（`9b46152`）、风险触发批准（`2029`/`2030`）。
   - §3.1/§3.3/§4.2 仍以「Production 与 Tooling 生命周期入口相互隔离」「两族入口」描述架构，与 2045 后「共用统一入口、差异由 manifest 与治理守卫承载」的现实相反。
2. **`docs/harness-alignment/07-host-capability-alignment.md`（更新日期 2026-09-12）存在两类过时**：
   - 行号漂移：「治理 Profile 守卫（:1090-1118）」——该区间现为 argparse 注册代码，守卫实际在 `workflow_control.py:1125`（`_event_governance_errors`）；「约 1254 行」→ 实际 1302 行；「1400+ 行」→ 实际 1478 行（漂移源于 07 写成当天的 change 2046 refactor）。其余 40 余处行号引用经逐条核验仍然命中。
   - P1 的「未核实项」已可解除：本 change 当天联网核验确认 Codex CLI 已有 hooks 体系（`hooks.json`、PreToolUse/PostToolUse/Stop/SessionStart 等 lifecycle 事件，`/hooks` 命令；0.150.1 起强制信任审核）。P1 门禁 hooks 化的最大障碍消除。

### 目标

- 状态文档 §1/§3/§4/§5/§6 追平 change 2045/2046、2028-2030、2041-2046 与 SVN 降级后的现状；§5 更新为本次实测快照。
- 状态文档 §7 补记 2026-09-12 联网核验增量（Spec Kit 定位升级、Codex hooks、Claude Code 2.1.269 的 `/skill-doctor`、`claude plugin eval`、Workflow 并发上限），保持「历史基线 + 增量核验」分层。
- 07 文档修正 3 处漂移引用，并把行号引用改为「函数名 + 行号」格式（降低下次漂移损失）；解除 P1 未核实项。
- 07 文档补记 `harness/capabilities/codex.json` 的 `lifecycle_hooks: unsupported` 静态默认值与已核验事实的关系（静态声明按自身合同待运行时探测覆盖，本次不改 json）。

### 非目标

- 不改任何 Python 代码、Skill、Command、Agent、schema 与测试（唯一例外：`openspec/specs/backend/framework/meta.yaml` 的 quality-gates 来源指针修复——它自身是知识元数据，见 §2.1 第 3 条）。
- 不改 `harness/capabilities/*.json` 的静态默认值（其自身合同要求由运行时 Adapter 探测覆盖，凭联网核验手改 `supported` 违反其证据约定）。
- 不做 P1 门禁 hooks 化、P2 Workflow 波次深化、P3 plugin 双通道的实施（07 文档仅解除未核实项，实施仍走 `docs/design-docs/` 流程）。
- 不重写 §10 资料研究快照（它自我声明为 2026-06-28 的历史快照，语义自洽）。
- 不重跑对外竞品全量对比（§7 历史基线保留，仅补增量小节）。
- 不重生成 meta.yaml 各条目的 `source_ref`（freshness 类 WARN 为既有维护项，需要逐条目重跑知识派生，超出本次文档追平范围）。

### 验收标准

1. 状态文档中不再出现「两族 Lifecycle Skills」、`/opsx-requirements-clarification` 等 5 个已退役入口、以及 `skills/opsx-code-generation` 引用； Production 流程描述与 README「双 Profile 路由」一致。
2. 状态文档 §5 数字与 `python -m pytest scripts -q`、`python scripts/lint_skill_graph.py` 本次实测输出一致，并标注实测日期。
3. 07 文档的守卫引用指向 `workflow_control.py:1125` `_event_governance_errors`；行数引用与当前文件一致；P1 节「未核实项」改写为已核验结论并附来源。
4. `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json` 总判定 PASS（纯 `.md` 改动不触发 spec drift；测试计数不减）。
5. `python scripts/lint_skill_graph.py` 退出码 0。

## 2. 方案

### 2.1 实现

纯文档修改，共 2 个文件：

1. `docs/framework-features-status-and-comparison.md`：
   - 头部「更新时间」改为 2026-09-12 并注明本次追平范围。
   - §1 结论第 1/2 条改写：OPSX 三阶段校验 → `validate_change.py` 三阶段门禁；补 governance guards、harness 能力矩阵。
   - §3.1 表格与说明对齐 2045 后的统一入口模型（差异由 manifest `profile` 字段与 `governance_guards.py` 守卫承载；`validate_change.py` 仅 Production 安装）。
   - §3.3 证据指针从已迁移的 `docs/design-docs/opsx/...`（保留为历史快照路径不变）补充现行代码入口。
   - §4.1 表格第一、二行改写（统一 `workflow-*` 入口；「Production OPSX」行改为「Production 三阶段门禁」并指向 `scripts/validate_change.py` 与 governance guards）。
   - §4.2 标题改为「Production 门禁（原 OPSX）」；流程图与 README「双 Profile 路由」一致；失效证据指针 `skills/opsx-code-generation/SKILL.md:84-103` 改为 `skills/workflow-code-generation/SKILL.md` 与 `scripts/validate_change.py`；保留「不是官方 OpenSpec CLI 兼容层」边界表述。
   - §4.10 之后新增 §4.12「Harness 能力矩阵与运行协议」小节：`harness/capabilities/*.json` 三态静态声明 + 运行时探测覆盖、`machine-verifiable-agent-runtime` spec（Run Envelope / run_id / task_id 绑定）、Native Delivery 与 Runtime Run 双路由、SVN 工作副本强制 native-delivery。
   - §4.11 评测体系补一行：`evaluation/swebench` 与 Native Delivery 三任务试点（2026-07-25，合同级回归完成、Run 级审计证据缺失）。
   - §5 实测快照更新为本次数字与日期。
   - §6.1 入口改为 `workflow-*` 统一路径，与 README §6 一致。
   - §7 在历史基线声明后新增「2026-09-12 增量核验」小表：Spec Kit（2026-08-21 官方文档站，自我定位升级为「extensible, intent-driven harness」）、Codex hooks、Claude Code 2.1.261-2.1.269 相关能力（`/skill-doctor`、`claude plugin eval`、`CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS`）。
2. `docs/harness-alignment/07-host-capability-alignment.md`：
   - 「治理 Profile 守卫（:1090-1118）」→「治理守卫 `:1125` `_event_governance_errors` + `governance_guards.py`」。
   - 「约 1254 行」→ 1302 行；「1400+ 行」→ 1478 行；installer 行号引用改为「函数名 + 行号」。
   - §5 P1 的「未核实项」改写：Codex hooks 已核验（`hooks.json` + lifecycle 事件 + `/hooks` 命令；0.150.1 起信任审核），来源标注官方文档 learn.chatgpt.com/docs/hooks 与社区核验记录；结论更新为「双宿主 hooks 化路径已通，实施前仍需用 harness/ Adapter 探测确认目标版本能力」。
   - §4.6 与观察项补一句：`harness/capabilities/codex.json` 静态声明 `lifecycle_hooks: unsupported` 为待探测默认值，与本节已核验事实的差异由运行时探测覆盖。
3. `openspec/specs/backend/framework/meta.yaml`（实施中由 verify 门禁 WARN 发现的同类缺口）：`quality-gates` 条目仍引用 change 2045 已删除的 `skills/opsx-code-generation/SKILL.md` 与 `skills/opsx-archive/SKILL.md`，替换为现行事实源（`workflow-code-generation/SKILL.md`、`governance_guards.py`、`check_delivery.py`）。

### 2.2 权衡

- **为什么不把状态文档 §7 全量重写**：§7 明确自我声明为「历史比较基线」，全量重写需要逐框架重新安装/核验，超出本次追平范围；增量小节已把「过时」风险显式化。
- **为什么不改 `codex.json`**：该文件头部合同要求「静态声明不凭文档断言产品支持；运行时探测覆盖静态默认值」。联网核验属文档证据，不满足其「可执行证据」门槛；改为 `supported` 会破坏合同。
- **为什么 §10 不动**：它自我声明为 2026-06-28 首次编写时的资料研究快照，语义自洽，不属于「与现状矛盾」。
- **行号引用改为「函数名 + 行号」**：07 文档当天写成、当天就被 2046 refactor 漂移了 3 处；函数名在重构后仍可 `grep` 定位，是防漂移的最低成本方案。

## 3. 知识影响

- 长期规格不受影响：本次只改 `docs/` 下两份叙述性文档，不改任何被 `openspec/specs/` 描述的行为。
- `docs/harness-alignment/README.md` 索引行的描述仍准确（07 的条目摘要未涉及本次修正的细节），不改。
- 无 Delta（Quick Draft），由任务直接落盘。

## 4. 实施记录

- 2026-09-12：Task 1（状态文档 §1/§3/§4/§5/§6/§7 追平）、Task 2（07 文档行号修正 + P1 未核实项解除）、Task 3（meta.yaml quality-gates 失效指针修复）全部完成。三道门禁全绿：pytest 547 passed / 21 skipped、verify 总判定 PASS（spec drift PASS）、skill 图 lint 0 错误。独立 Reviewer 两批均未回报（详见 tasks.md 实际 Diff 核对节），Review 以机械核验 + 门禁替代，语义 Review 留待补审。
