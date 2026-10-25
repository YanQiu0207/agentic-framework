# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 3
> 核心原则: 单任务线性执行，实现与验证同批交付

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `docs/harness-alignment/08-host-update-2026-10.md` | 新建 | Task 1 | 2026-08-25 → 10-25 宿主/竞品/模型增量核验 + 6 条跟进清单 |
| `docs/harness-alignment/07-host-capability-alignment.md` | 修改 | Task 2 | §4.6 观察项措辞更正 + 头部更新日期 |
| `docs/harness-alignment/README.md` | 修改 | Task 3 | 索引新增「宿主增量核验（2026-10）」小节 |

### 受影响接口

无（纯文档）。

### 构建系统变更

- 无。

## 任务列表

### 任务 1: [x] 新建 08 号宿主增量核验文档
- 状态：完成
- 文件：`docs/harness-alignment/08-host-update-2026-10.md`（新建）
- depends_on: []
- review_profile: standard
- 文档映射：proposal.md §2.1 第 1 条
- 说明：按 proposal §2.1 第 1 条的结构落盘调研结论：§1 背景与调研口径、§2 宿主增量（Claude Code 版本线 + Codex）、§3 竞品动作、§4 模型层变量、§5 跟进清单 6 条、§6 来源与证据分级。全部事实标注来源（官方 changelog / GitHub API 实测 / 社区口径），社区口径标「未验证」。
- context_files:
  - `docs/harness-alignment/07-host-capability-alignment.md` — 07 的分层口径与证据分级格式参照
  - `docs/harness-alignment/README.md` — 索引结构（Task 3 要挂链接）
  - `openspec/specs/backend/engineering/tech/framework-unification.md` — 风险触发批准规则的 spec 事实源
- artifacts:
  - `docs/harness-alignment/08-host-update-2026-10.md`
- verification:
  - [x] 六节结构齐全，跟进清单恰 6 条且带分级
  - [x] 每个事实性条目带来源；社区口径明确标「未验证」
  - [x] 「逐 Task 批准」类过时表述不再出现（批准语义写为风险触发的暂停批准）
- 子任务:
  - [x] : §1-§2 背景与宿主增量
  - [x] : §3-§4 竞品动作与模型层
  - [x] : §5-§6 跟进清单与来源说明

### 任务 2: [x] 更正 07 号文档观察项措辞
- 状态：完成
- 文件：`docs/harness-alignment/07-host-capability-alignment.md`（修改）
- depends_on: Task 1
- review_profile: standard
- 文档映射：proposal.md §2.1 第 2 条
- 说明：§4.6 观察项「需留意对 Production 逐 Task 批准假设的影响」改为「需留意对 Production 风险触发的暂停批准（尤其 irreversible 任务）假设的影响」；头部「更新日期」追加 2026-10-25 修订注记。只动这两处，其余内容不碰。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py` — `approval_mode()` 缺省 risk-triggered 的事实源
  - `openspec/specs/backend/engineering/tech/framework-unification.md` — Change 2029 引入的风险触发批准规则
- artifacts:
  - `docs/harness-alignment/07-host-capability-alignment.md`
- verification:
  - [x] :84 观察项不再含「逐 Task 批准」
  - [x] 头部更新日期含 2026-10-25 修订注记
  - [x] `git diff` 确认仅 2 处改动（观察项 + 头部日期）
- 子任务:
  - [x] : 观察项措辞更正
  - [x] : 头部更新日期注记

### 任务 3: [x] 更新 harness-alignment README 索引
- 状态：完成
- 文件：`docs/harness-alignment/README.md`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 文档映射：proposal.md §2.1 第 3 条
- 说明：「文档索引」节在「宿主原生能力对齐（2026-09）」之后新增「宿主增量核验（2026-10）」小节：表格挂 08 文档链接、内容摘要与「何时读」。
- context_files:
  - `docs/harness-alignment/README.md` — 现有索引结构（来源一/来源二/宿主对齐三组）
- artifacts:
  - `docs/harness-alignment/README.md`
- verification:
  - [x] 索引含 08 链接且锚点路径正确（相对链接可点开）
  - [x] 其余索引条目未变动
- 子任务:
  - [x] : 新增小节与表格行

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal §1 问题 | Task 1, 2 | 增量未沉淀 + 07 措辞过时 |
| proposal §2.1 | Task 1, 2, 3 | 逐文件实现方案 |
| proposal §2.2 权衡 | Task 1 | 08 不并入 07、不实施跟进项、证据分级 |
| proposal §3 知识影响 | — | 无 Delta，无规格改动 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | 无长期规格改动 | — | — | — |

## 知识冲突

- 结论：无冲突。08 文档是新增调研沉淀，07 的措辞更正以 `workflow_control.py:52,550` 与 `framework-unification.md`（Change 2029）为事实源，文档向代码事实对齐，不引入新的行为断言。

## 实际 Diff 核对

- 核对状态：PASS（带一项如实披露，见下）。
- 改动文件（本次 change 范围）：`docs/harness-alignment/08-host-update-2026-10.md`（新建）、`docs/harness-alignment/07-host-capability-alignment.md`（恰 2 处：头部更新日期注记 + §4.6 观察项措辞）、`docs/harness-alignment/README.md`（恰 1 节：宿主增量核验（2026-10）索引）、新增 `openspec/changes/2049-host-update-2026-10/`。
- 核对命令与结论：
  - `python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2049-host-update-2026-10/tasks.md --governance-profile tooling` → tasks=3 | errors=0 warnings=0 legacy=0（首次运行暴露 5 处格式问题：depends_on 写法 `[1]` → `Task 1`、缺 artifacts 字段，已修正后复跑归零）。
  - `python scripts/lint_skill_graph.py` → exit 0（skills=27 commands=14 agents=8）。
  - `python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base HEAD --spec-drift-reason ...` → Z-spec-drift PASS（提供的 reason 被接受：spec-drift 初跑判定的 7 个 code_files 全部位于 `.artifacts/skill-slimming-20260926/`，系 change 2048 遗留的未跟踪候选目录，非本次改动）；B-test-count-not-decrease PASS（609 ≥ 基线 565）；C-skill-graph-lint PASS。
  - **B-tests-pass FAIL（如实披露，非本次引入）**：`python -m pytest scripts -q` → 2 failed, 600 passed, 21 skipped。失败为 `test_skip_decision_allows_dispatch_without_verify_config` 与 `test_tooling_standard_uses_unified_artifact_and_controller`，stderr 均为「无法取得治理 Profile：缺少 .agentic-framework/manifest.json 且未传 --governance-profile」。已在 HEAD 7441ecc 的干净临时 worktree（`git worktree add` 后无任何改动）复跑同两个测试，**原样失败**，确证为既存失败（首跑另触发 300s 超时，直跑实测 242s 完成为环境速度问题，非挂死）。本 change 纯 .md 改动，无代码路径可影响这两个测试。
  - Z-knowledge-source 2 条 WARN 为既有维护项（meta.yaml source_freshness），与 2047 时相同，不属本次范围。
- 机械核验：`git diff` 确认 07 恰 2 处、README 恰 1 节；「逐 Task 批准」在 07 文档 grep 计数为 0；08 文档 md-zh 粗扫 0 候选违例。
- Review 说明（如实记录）：本 change 为纯文档落地，Review 以机械核验 + 门禁结果替代；语义 Review 建议人工抽查 08 文档 §5 跟进清单的分级措辞与 §3.2 事故转述的准确性。
- 交付门尝试（2026-10-25，如实记录）：Native Delivery 路径首跑 errors=5，其中 3 项属本次已修（tasks.md 遗留 1 个未勾选复选框已补、spec 状态改 Archived、知识影响理由补齐），2 项结构性受阻非本次改动可解：① verify 报告 B-tests-pass FAIL（既存测试失败，见上）；② 工作区含并行会话未提交改动（用户已知悉并示忽略）。门禁无法给出干净交付裁决，按契约如实标注，不声明「交付门 PASS」。
