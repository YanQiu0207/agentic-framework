# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 3
> 核心原则: 单任务线性执行，实现与验证同批交付

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `scripts/lint_skill_graph.py` | 修改 | Task 1 | 新增 SKILL.md 体积红线检查（20000 字符，ERROR 级） |
| `scripts/test_lint_skill_graph.py` | 修改 | Task 2 | 补体积红线回归测试（超限 / 限内 / 边界值） |
| `docs/harness-alignment/08-host-update-2026-10.md` | 修改 | Task 3 | 恰 3 处：§2.3、§3.2 + 跟进 1 行、§6 证据说明的证据口径修正 |
| `openspec/specs/backend/engineering/tech/framework-unification.md` | 修改 | Task 3 | §16.4 补体积红线验收一条 |

### 受影响接口

无外部接口。`lint_skill_graph.py` 输出末行统计格式不变（`skills=N commands=N agents=N | errors=N warnings=N`）。

### 构建系统变更

- 无。

## 任务列表

### 任务 1: [x] lint_skill_graph.py 新增体积红线检查
- 状态：完成
- 文件：`scripts/lint_skill_graph.py`（修改）
- depends_on: []
- review_profile: lightweight
- 说明：新增模块级常量 `SKILL_BODY_CHAR_LIMIT = 20000` 与检查函数 `find_size_errors(skills)`：对每个 SKILL.md 全文字符数超限时报 ERROR，消息含实际字符数与「移入 reference/ 渐进加载」指引；在 `collect_nodes` 之后、`main` 汇总前接入，错误计入 errors 总数。头部 docstring 的检查清单补一行。
- context_files:
  - `scripts/lint_skill_graph.py` — 既有检查结构与错误汇报格式参照
  - `scripts/test_lint_skill_graph.py` — 测试调用方式参照
- artifacts:
  - `scripts/lint_skill_graph.py`
- verification:
  - [x] `python scripts/lint_skill_graph.py` 在当前仓库输出 `errors=0`（27 个 Skill 均达标）
  - [x] 临时构造超限 SKILL.md 时该文件被点名报 ERROR 且退出码 1
- 子任务:
  - [x] : 常量 + 检查函数 + main 接线
  - [x] : docstring 检查清单同步

### 任务 2: [x] 补体积红线回归测试
- 状态：完成
- 文件：`scripts/test_lint_skill_graph.py`（修改）
- depends_on: Task 1
- review_profile: lightweight
- 说明：新增测试方法（沿用 tempfile.TemporaryDirectory 风格）：① 超限 Skill 报 1 条 ERROR 且消息含路径；② 限内 Skill 无体积类 ERROR；③ 边界：正文恰 20000 字符通过、20001 拒绝。
- context_files:
  - `scripts/lint_skill_graph.py` — 被测常量与函数签名
  - `scripts/test_lint_skill_graph.py` — 既有测试风格
- artifacts:
  - `scripts/test_lint_skill_graph.py`
- verification:
  - [x] `python -m pytest scripts/test_lint_skill_graph.py -q` 全绿
  - [x] 全量 `python -m pytest scripts -q` 中本文件用例数净增 ≥ 2（test-count 门禁不降）
- 子任务:
  - [x] : 超限 / 限内用例
  - [x] : 边界值用例

### 任务 3: [x] 08 号文档证据口径修正 + spec 知识同步
- 状态：完成
- 文件：`docs/harness-alignment/08-host-update-2026-10.md`（修改）、`openspec/specs/backend/engineering/tech/framework-unification.md`（修改）
- depends_on: Task 1
- review_profile: standard
- 说明：08 号恰 3 处——① §2.3 「暴露于同一机制」句收窄为社区级并标注官方未载；② §3.2 与 §5 跟进 1 行去掉 `/skill-doctor` 悬空命令名，动作要点改为「体积审计（已完成）+ lint_skill_graph 体积红线门禁」，跟进 1 行补实施结论（change 2050）；③ §6 补「官方 CHANGELOG 未复核到 20000 字符条目」。spec §16.4 在 lint_skill_graph 验收行下补一条：每个 SKILL.md 字符数不超过 20000，超限须拆分至 reference/ 渐进加载。
- context_files:
  - `docs/harness-alignment/08-host-update-2026-10.md` — 待修正原文
  - `openspec/specs/backend/engineering/tech/framework-unification.md` — §16.4 现有验收行
  - `openspec/changes/2050-skill-compaction-survival-gate/proposal.md` — 修正依据
- artifacts:
  - `docs/harness-alignment/08-host-update-2026-10.md`
  - `openspec/specs/backend/engineering/tech/framework-unification.md`
- verification:
  - [x] `grep -n "skill-doctor"` 在 08 号仅命中跟进 1 行的勘误记录（「查无出处、已废弃」），不再作为待办动作出现
  - [x] `git diff` 确认 08 号恰 3 处、spec 恰 1 条
  - [x] 中文 Markdown 排版自检（中英文空格、全角标点、直角引号）无新增违例
- 子任务:
  - [x] : 08 号 §2.3 / §3.2 / 跟进 1 / §6 修正
  - [x] : spec §16.4 补验收条目

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal §2.1 | Task 1 | 门禁红线 |
| proposal §2.2 | Task 2 | 回归测试 |
| proposal §2.3 | Task 3 | 08 号口径修正 |
| proposal §2.4 | Task 3 | spec 知识同步 |
| proposal §3 权衡 | Task 1 | 不迁移现有正文、红线取 20000 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| framework-unification.md §16.4 新增体积红线验收行 | `openspec/specs/backend/engineering/tech/framework-unification.md` | 补 1 条验收 | 完成 | 无需（既有文档内增补） |

## 知识冲突

- 结论：无冲突。红线数值 20000 的来源（社区事故口径 + 08 号跟进 1）与官方 CHANGELOG「未载此条目」的核验结论在 proposal §1 显式并列，文档向「机器门禁 + 证据分级」对齐，不引入与代码事实相悖的行为断言。

## 实际 Diff 核对

- 核对状态：PASS（带一项如实披露，见下）。
- 改动文件（本次 change 范围，恰 5 项）：`scripts/lint_skill_graph.py`（+21：docstring 1 行、`SKILL_BODY_CHAR_LIMIT` 常量、`find_size_errors`、main 接线 1 行）、`scripts/test_lint_skill_graph.py`（+44：3 个体积用例 + 1 个共享 helper）、`docs/harness-alignment/08-host-update-2026-10.md`（4 处：§2.3 一句、§3.2 两段、§5 跟进 1 行、§6 一条）、`openspec/specs/backend/engineering/tech/framework-unification.md`（§16.4 恰 1 条）、新增 `openspec/changes/2050-skill-compaction-survival-gate/`。
- 工作区中不属于本次的改动（并行会话现场，一律未碰）：`.gitignore`、`openspec/index.md`、`openspec/specs/index.md`、`external-reference-comet.md`、`external-reference-agentic-landscape-2026-10.md`、`.artifacts/`、`.codex/`、change 2049-agentic-landscape-knowledge。
- 门禁记录（2026-10-26）：
  - `lint_task_deps.py ... --governance-profile tooling` → `tasks=3 | errors=0 warnings=0 legacy=0`，exit 0（落盘前后各跑一次均绿）。
  - `lint_skill_graph.py` → `skills=27 commands=14 agents=8 | errors=0 warnings=0`，exit 0（含新体积检查，现有 Skill 全达标）。
  - 负向验证：临时 root 构造 20,100 字符 SKILL.md → 该文件被点名 ERROR、exit 1。
  - `python -m pytest scripts -q` → 2 failed, **603 passed**, 21 skipped（基线 600 passed，净增 3 = 新增体积用例数）。两个失败为 `test_skip_decision_allows_dispatch_without_verify_config` 与 `test_tooling_standard_uses_unified_artifact_and_controller`，已在干净 HEAD worktree（`git worktree add ../aef-head-check-2050 HEAD`，无任何改动）复跑，**原样失败**（`0 != 2` + 「无法取得治理 Profile」），确证为既存失败（与 2049 归档披露的同一对），非本次引入。
  - `verify.py --baseline ... --diff-base HEAD` → 总判定 **FAIL（violations=1，errors=0）**：`Z-spec-drift PASS`（代码变更 9 个、规格类文件已更新 2 个）、`B-test-count-not-decrease PASS`（612 ≥ 565）、`C-skill-graph-lint PASS`；`B-tests-pass FAIL` 由上述两个既存失败构成（直跑实测 242.8s，未触发 300s 超时）。按契约如实披露，不声明「质量门通过」；该失败修复属独立 change（与 2049 收尾同源问题）。
  - `Z-knowledge-source` 2 条 WARN 为既有维护项，与 2047/2049 时相同，不属本次范围。
- 中文排版：本次修改行 md-zh 粗扫 0 违例。
- Review 说明：本 change 为「门禁脚本 + 测试 + 纯文档」组合，语义 Review 建议人工抽查两处——① `find_size_errors` 计的是全文而非去 frontmatter 后正文（红线管回挂整体，报错文案已按「全文」表述）；② 08 号跟进 1 行的勘误记录措辞是否可接受。
