# Proposal：宿主与竞品 2026-10 增量核验落地为 08 号文档 + 07 号措辞更正（Quick Draft）

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-10-25
**变更**：host-update-2026-10
**状态**：Archived

---

## 1. 问题与目标

### 问题

2026-08-25 → 2026-10-25 两个月的宿主与竞品增量调研（本次 change 的直接来源，调研在主会话完成）产出了两组脱节：

1. **`docs/harness-alignment/` 缺一次「宿主增量核验」**：上一份 07 号对齐文档停在 2026-09-12。近两月 Claude Code 与 Codex 的原生能力演进（Claude Mods、Code Review GA、idle compaction、hooks `onFailure:"block"`、AGENTS.md 支持等）、竞品版本动作（Comet 0.5.0、superpowers compaction 存活事故、Taskmaster 停滞）、模型层变量（Fable/Opus/Sonnet/Haiku 5.5、GPT-6.x、Gemini 4、DeepSeek V4.1）均未沉淀。
2. **07 文档 :84 观察项措辞过时**：「需留意对 Production 逐 Task 批准假设的影响」——框架自 change 2029 起默认 `risk-triggered` 批准模式（`workflow_control.py:52` `APPROVAL_MODES = {"risk-triggered", "per-task"}`，:550 缺省返回 `risk-triggered`），语义是「批准 tasks.md 后自主连跑、仅风险触发时暂停批准（scope-change / irreversible / gate-failure / assumption-broken / user-requested）」，其中 irreversible 升级正是 auto mode 时代的关键把关点。「逐 Task 批准」措辞会误导后续读者对框架批准语义的理解（与 07 写作当天即被 change 2046 漂移行号属同一类「文档措辞落后于代码事实」）。

### 目标

- 新建 `docs/harness-alignment/08-host-update-2026-10.md`：2026-08-25 → 10-25 宿主/竞品/模型增量核验 + 6 条跟进清单，标注来源与证据分级（官方确认 / 社区未验证），保持 07 号「历史基线 + 增量核验」的分层口径。
- 更正 `docs/harness-alignment/07-host-capability-alignment.md` :84 观察项措辞：「Production 逐 Task 批准假设」→「Production 风险触发的暂停批准（尤其 irreversible 任务）假设」，并更新其头部更新日期注明本次修订。
- 更新 `docs/harness-alignment/README.md` 索引：新增「宿主增量核验（2026-10）」一节挂 08 链接。

### 非目标

- 不改任何 Python 代码、Skill、Command、Agent、schema、`harness/capabilities/*.json` 与测试。
- 不按跟进清单实施任何跟进项（Skill 压缩改造、行为级评测、门禁 hooks 化等只作为 08 文档的建议，实施另走 `docs/design-docs/` 流程）。
- 不重写 07 文档其余部分：其余 40 余处行号引用在 change 2047 时已逐条核验命中，本次只动 :84 一处措辞 + 头部日期；若执行时复查发现其它漂移，列出来告知用户，不默默改。
- 不把 Comet 0.5.0 增量（SDK/Dashboard/Eval）补进 `openspec/specs/backend/engineering/tech/external-reference-comet.md`：该文件工作区含另一会话的未提交重写（md5 与 HEAD 不同），本次不触碰，避免混入；需要时另开 Change。
- 不把 08 文档内容同步进 `docs/framework-features-status-and-comparison.md`：该文档 §7 是「历史基线 + 增量核验」分层，本次增量按同一分层口径落在 08 号专题文档，不触碰状态文档。
- 不清理工作区无关改动（`.gitignore` 的 CAO 实验改动、`external-reference-comet.md` 未提交重写、`.artifacts/`、`.codex/`）——与本次改动分离，交付后交由用户拍板。

### 验收标准

1. `docs/harness-alignment/08-host-update-2026-10.md` 落盘且内容与本次调研证据一致：宿主增量覆盖 Claude Code 2.1.257→2.1.310 版本线与 Codex（GPT-5.5 退役、daemon 0.157.0、hooks 体系不变），竞品覆盖 Comet 0.5.0 / Spec Kit / OpenSpec / superpowers / BMAD / Taskmaster，模型层覆盖 5.5 系列与 GPT-6.x / Gemini 4 / DeepSeek V4.1，跟进清单 6 条齐全且分级（P0 / P1 / 低成本 / 观察）。
2. 07 文档 :84 观察项不再含「逐 Task 批准」，改为「风险触发的暂停批准（尤其 irreversible 任务）」；头部更新日期更新为 2026-10-25 并注明修订内容。
3. README 索引含「宿主增量核验（2026-10）」一节与 08 文档链接。
4. 全部新增/修改中文内容按 md-zh 规则自检（中英文空格、中文与数字空格、全角标点、专有名词大小写）。
5. `verify.py --baseline .agentic-framework/verify/baseline.json --diff-base HEAD` 总判定 PASS（纯 `.md` 改动不触发 spec drift）。
6. `lint_skill_graph.py` 退出码 0（确认纯文档改动未破坏 Skill 图）。

## 2. 方案

### 2.1 实现

纯文档修改，共 3 个文件（1 新建 + 2 修改）：

1. **新建 `docs/harness-alignment/08-host-update-2026-10.md`**，结构：
   - §1 背景与调研口径（窗口 2026-08-25 → 10-25；方法：官方 changelog/docs 页 + GitHub API 实测 + 社区信号；社区口径标注「未验证」）。
   - §2 宿主增量：Claude Code 版本线（2.1.257 Fable 5.1、2.1.280 Opus 5.5 + Pro/Team 默认升 Opus、2.1.284 Sonnet 5.5 + 交互会话默认 auto mode + ultracode 独立开关、2.1.287 Claude Mods、2.1.293 Haiku 5.5、2.1.302 `claude -p` 默认 Manual + fork 子代理全端默认、2.1.304 Code Review GA、2.1.299 idle compaction，及 2.1.277/281 AGENTS.md、2.1.295 hooks `onFailure:"block"` 等次要项）；Codex（GPT-5.5 于 10-14 从 ChatGPT 登录退役、daemon 自启 0.157.0、hooks 体系沿用 9 月核验结论）。Code Review GA 与 idle compaction 单独立小节——与框架 Review 分档、Skill compaction 存活直接相关。
   - §3 竞品动作（GitHub API 2026-10-25 实测：Comet 3,230★ v0.5.0 新增 Comet Any/SDK/Dashboard/Eval；spec-kit 142,737★ v1.2.3；OpenSpec 72,913★ v1.15.0；superpowers v7.0.1 的 compaction 只回挂 Skill 前 20,000 字符致多轮上限丢失的事故与重构应对——star 数异常值标注待复核；BMAD 54,519★ v7.0.0；Taskmaster 28,271★ 停滞于 2026-04-28）。
   - §4 模型层变量（Fable/Opus/Sonnet/Haiku 5.5 定位与 Sonnet 5.5 价格 $2/$10；GPT-6 Sol/Luna（Sol ~1M 上下文为社区口径未官方确认）、GPT-6.1 Sol 降价、GPT-6.1 Astra 因对齐回归撤回；Gemini 4 Argon；DeepSeek V4.1 Flash；`sonnet-4-5` 2026-11-30 退役；Claude API 2026-10-21 破坏性变更；Agent SDK 订阅计费变动）。
   - §5 跟进清单 6 条：①【新增 P0】Skill 压缩与 compaction 存活改造（体积审计 + references/ 渐进加载 + 体积红线测试）；②【P0 升级】行为级评测（`claude --restricted` + `claude plugin eval`，约 20 确定性场景）；③【P1 修订】门禁 hooks 化→hooks+Mods 双通道（Codex 无 Mods，hooks 为双宿主公约数）；④低成本立即做（/doctor prompt-audit、清旧模型 ID、评估 AGENTS.md 收敛）；⑤观察项升级（auto mode 默认化 × 风险触发暂停批准（尤其 irreversible）、宿主 Code Review GA × 框架 Review 分档边界）；⑥维持 native-first。
   - §6 来源与证据分级说明。
2. **修改 `docs/harness-alignment/07-host-capability-alignment.md`**：§4.6 观察项一句改写为「需留意对 Production 风险触发的暂停批准（尤其 irreversible 任务）假设的影响」；头部「更新日期」追加 2026-10-25 修订注记（批准语义以 `workflow_control.py` `approval_mode()` 缺省 `risk-triggered` 为准）。
3. **修改 `docs/harness-alignment/README.md`**：「文档索引」新增「宿主增量核验（2026-10）」小节，表格挂 08 文档链接与「何时读」说明。

### 2.2 权衡

- **为什么 08 文档不并入 07**：07 是「宿主原生能力 × 框架现状」的深对齐（吸收/保留建议 + P1/P2/P3 动作），本次是「两月窗口的增量核验 + 跟进清单」，粒度和用途不同；README 已按来源/窗口分组索引，分文档更清晰。
- **为什么不实施跟进清单**：本次是调研落地，各实施项需要各自的 design 文档（如 Skill 压缩改造、评测闭环），Quick Draft 一并实施会失焦；08 文档作为 design 流程的输入。
- **为什么 07 只动一处措辞**：其余引用在 2047 时逐条核验命中；精准修改原则——只碰必须碰的。
- **为什么不触碰 external-reference-comet.md**：工作区版本含另一会话的未提交重写，本次改动不得混入；需补 Comet 0.5.0 增量时另开 Change（该文件已在 Git 管理下，未提交改动不会丢失）。
- **为什么 08 的证据分级口径为「官方确认 / 社区未验证」**：结论须分开「来源已写明」与「自行推断」，未知标待确认，不以来源偏好升级结论强度——与团队作业原则一致。

## 3. 知识影响

- 长期规格不受影响：本次只改 `docs/harness-alignment/` 下文档，不改任何被 `openspec/specs/` 描述的行为。
- 无 Delta（Quick Draft），由任务直接落盘。

## 4. 实施记录

- 2026-10-25：Task 1（08 文档落盘）、Task 2（07 文档 :84 措辞更正 + 头部日期注记）、Task 3（README 索引新增小节）全部完成。门禁：lint_task_deps 0 错误（修正 5 处格式后）、lint_skill_graph exit 0、verify 的 Z-spec-drift PASS（reason：初跑判定的 7 个 code_files 均为 change 2048 遗留的 `.artifacts/skill-slimming-20260926/` 未跟踪候选目录，非本次改动）、B-test-count-not-decrease PASS（609 ≥ 565）。**如实披露**：B-tests-pass FAIL——2 个失败测试（test_skip_decision_allows_dispatch_without_verify_config、test_tooling_standard_uses_unified_artifact_and_controller）已在 HEAD 7441ecc 干净 worktree 复现确证为既存失败（测试环境缺 manifest.json 且未传 --governance-profile），与本纯 .md change 无关；详记 tasks.md「实际 Diff 核对」。
