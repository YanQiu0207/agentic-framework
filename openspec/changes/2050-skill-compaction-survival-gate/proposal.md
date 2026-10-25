# Skill 压缩存活门禁：体积红线 + 08 号文档证据口径修正

## 1. 背景

`docs/harness-alignment/08-host-update-2026-10.md` 跟进 1（【新增 P0】）要求为 Skill 长会话 compaction 存活建防护。实施前实测发现三个前提与事实不符，须先修正再建设：

1. 「20k 截断是官方 CHANGELOG 行为」不成立。官方 CHANGELOG（2.1.287 → 2.1.310 近期全版本）无任何「compaction 后只回挂 Skill 前 20000 字符」条目；官方口径为 2.1.299 `/reload-skills`「re-sends the full skill list」、2.1.304「compaction 后重发 skill 清单」。08 号 §3.2 自身已标注该机制为〔社区〕级、数字待本地验证，但 §2.3 与跟进 1 的表述强度超过了这个分级。`/skill-doctor` 命令名查无出处（官方 CHANGELOG 无、superpowers 仓库无对应命令，其诊断类技能为 diagnosing-superpowers）。
2. 「框架 91 个 Skill」不成立。`skills/` 实测 27 个 SKILL.md（目录共 90 个文件，含 reference/scripts/evaluation）；「91」疑为文件数误记。
3. 「先跑 /skill-doctor + 体积审计」中的体积审计已完成：27 个 SKILL.md 无一超 20000 字符，最大 `workflow-code-generation` 15,259 字符（约红线 76%），合计约 10.3 万字符。

事故的合理内核保留：长 Skill 后半段约束在 compaction 后丢失是结构性风险（机制与数字属〔社区〕级，待本地验证），且 Skill 正文随演进只会变长。防护的正确形态是把「单文件体积红线」固化为机器门禁，而不是一次性人工瘦身。

## 2. 方案

### 2.1 门禁红线（核心交付）

`scripts/lint_skill_graph.py` 新增第 5 类检查：每个 `skills/*/SKILL.md` 正文字符数 ≤ 20000（超限报 ERROR，附带截断安全建议：把后半段移入 `reference/` 并在主文件留渐进加载指引）。红线数值 20000 定义为常量并在输出与测试中体现。

选择并入 `lint_skill_graph.py` 而非新建脚本的理由：该脚本已是 verify 门禁 `C-skill-graph-lint` 的执行体（`verify.config.json`），自动获得交付门与 verify 双通道强制；同构检查（description 非空）也在这里。

### 2.2 回归测试

`scripts/test_lint_skill_graph.py` 补体积检查用例：超限 Skill 被报 ERROR、限内 Skill 通过、边界值（恰 20000 通过 / 20001 拒绝）。

### 2.3 08 号文档口径修正（恰 3 处）

- §2.3：「暴露于同一机制」一句收窄为社区级机制描述，标注「官方 CHANGELOG 未载、待本地验证」。
- §3.2 与跟进 1 行：`/skill-doctor` 改为「体积审计脚本 / 并入 lint_skill_graph 的红线检查」，删除悬空命令名；跟进 1 动作要点同步为本次实际形态。
- §6 证据说明：20,000 字符一行的表述补「官方 CHANGELOG 未复核到对应条目」。

### 2.4 知识同步

`openspec/specs/backend/engineering/tech/framework-unification.md` §16.4 在 lint_skill_graph 验收行下补体积红线一条（规格随代码事实对齐，避免 spec drift）。

## 3. 权衡

- **不迁移现有正文**：当前无超标对象，唯一接近红线的 workflow-code-generation（76%）保持现状；拆分留待真实超限时按门禁提示执行，避免无对照收益的预重构。
- **红线取 20000**：对齐跟进 1 口径与社区事故数字；作为防线其价值在「变长前拦截」，绝对阈值精度影响有限，若本地验证推翻该数字，改常量一处即可。
- **ERROR 而非 WARN**：compaction 丢约束是静默失效，事后难归因，值得硬门禁。

## 4. 范围与边界

- 改动仅限：`scripts/lint_skill_graph.py`、`scripts/test_lint_skill_graph.py`、`docs/harness-alignment/08-host-update-2026-10.md`、`openspec/specs/backend/engineering/tech/framework-unification.md`、本 change 目录。
- 不触碰并行会话工作区现场：`.gitignore`、`openspec/index.md`、`openspec/specs/index.md`、`external-reference-comet.md`、`external-reference-agentic-landscape-2026-10.md`、`.artifacts/`、change 2049-agentic-landscape-knowledge。
- 纯 .md + 门禁脚本增强，不涉及运行时行为。
