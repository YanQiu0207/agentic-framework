# 外部参考：Comet 流程编排状态机及与当前框架的对照

> 本文档是 `rpamis/comet` 的外部项目研究与迁移对照分析，不是当前框架的实现规格。项目自述（README）、随包 SKILL.md、可读源码确认、推断与缺失证据分别标注；所有借鉴与迁移项在进入设计或实现前，仍须回到当前框架的代码、配置、测试和运行证据核实。

## 元信息

| 项 | 值 |
| --- | --- |
| 项目 | `rpamis/comet` |
| 定位 | AI 编码的流程编排状态机（Agent Skill Harness）：Native/Classic 双工作流 |
| 代码仓库 | <https://github.com/rpamis/comet> |
| 代码分析基准 | master `899d1fb05cd4`（2026-09-22） |
| 版本与许可 | v0.4.0 stable，MIT，Node.js（22.16+/24+），~3.1k stars |
| 核实范围 | README、`assets/skills/*/SKILL.md`（comet/comet-any/comet-classic/comet-native）、`comet-resume-probe.mjs` 可读源码、`eval/README.md`、`docs/architecture/ARCHITECTURE.md`、`app/commands/` 源码目录 |
| 核实边界 | guard/state/hook 脚本为 esbuild 打包产物（单文件 200–700 KB），内部校验逻辑未逐行反读；未本地安装实测；`/comet-any` 扩展管线未实跑 |
| 公共知识库条目 | `E:/work/shared-knowledge-base/domains/agentic-engineering/comet-workflow-harness.md`（跨项目通用版） |

## 一句话定性

Comet 把「想法 → 验证 → 归档」固化成状态机：阶段推进不依赖 Agent 口头声称完成（*"phase exits do not rely on an agent saying 'done'"*），由脚本门禁强制；状态外置到每个 change 的 `.comet.yaml`，中断可确定性续跑；自评闭环（Rubric + Pass@k + 独立 LLM Judge）驱动 Skill 人工迭代。与当前框架属**同类竞品**（同为「状态机 + 阶段门禁 + 评测」路线）。

## 双工作流的设计动机（README 原文）

分界线是**模型能力**，不是任务大小：

- Native：*"for strong models that can plan and verify autonomously"*——plan/implement/test/review 由模型自选，Comet 只管状态检查、验收、可恢复归档；
- Classic：*"for scenarios that benefit from a complete phased methodology and stronger constraints"*——OpenSpec + Superpowers 合成五阶段（Open → Design → Build → Verify → Archive）；
- 不合流的原因：①代价不对称（自报评测：Native 比 Classic 总 token 少 76.8%、轮次少 57.4%）；②作者拒绝「猜」：`/comet` 只按 `.comet/config.yaml` 确定性转发，*"does not guess from task size"*；
- *"Native and Classic are not lightweight and heavyweight tiers, and neither upgrades into the other"*——平行独立，仅共享 config/状态/Dashboard/Eval 底座。

## 机制要点（SKILL.md + resume-probe 源码确认）

**可恢复**：`.comet.yaml` 记 `workflow`/`phase`/`verifyResult`/`buildPause`/`archived`；未知字段判 invalid；归档区目录名 `YYYY-MM-DD-<name>` 可解析，「已归档但交付未完成」会捞回待恢复列表。恢复判定是四选一确定性分类器（`auto_resume | ask_user | out_of_scope | none` + confidence + reason + evidence），素材三路：磁盘状态（phase→命令硬编码映射）、`git status --short`（脏工作区一律 ask_user：「uncommitted worktree changes require attribution」）、话语关键词表（恢复词/疑问词/拒绝词）。策略偏保守：多 active change、决策点一律 ask_user；只有 `auto_resume` 才自动进入。

**门禁**：门禁点在 phase 推进——过脚本校验（任务完成、状态字段齐、验证证据在）才写 state 并返回下一条 `continuation`；Native 的 Agent 「works only on the phase specified by Runtime」。口头越级三重堵死：SKILL.md 明文对话不得授权改 phase；`.comet` 目录 Hook 保护不可豁免（`hook.allow_paths` 默认空）；坏 state 报错不猜（*"Report malformed state rather than guessing a phase"*）。并发安全：Native 命令带 `--expected-state-version` / `--expected-action` 乐观锁。

**评测**：pytest + Rubric（通用 7 维 / 工作流 9 维 / 生成包 11 维）+ LLM-as-judge（Judge 独立模型独立凭据 `BENCH_JUDGE_*`，不继承主任务配置）；被测 Agent 跑在 Docker（预装 Claude Code/Codex/Qoder/CodeBuddy），可接 LangSmith/LangFuse。**是评测驱动的人工迭代，非自进化**——无「eval 结果自动回写 Skill」闭环。

**扩展模型**（comet-any/SKILL.md + ARCHITECTURE.md）：三层扩展面，编译为 `workflow-protocol.json`（runtime source of truth，Factory/Eval/review/readiness 共用）：
1. **Required Skill Call**（最轻）：节点绑「必调依赖」，官方例：execute 必调 `elementui`、review 必调 `whitebox-code-standard`；
2. **Overlay**：`comet-five-phase-overlay` 保五阶段控制流与 `.comet.yaml` 语义；节点分权——control 节点（open/execute/verify/archive）不可覆写，producer 节点（design/plan）可覆但须满足原 Output Schema，handoff/guardrail 可增强；
3. **Workflow Kernel**：自建状态模型 + Output Schema + Guardrail；Native 本身即 kernel 成品示范。

扩展物同样过门禁：绑定/Schema 标强制级别（guarded/handoff-guarded/evidence-only/advisory）；*"failed eval, skipped eval, or stale-hash evidence cannot become ready"*；publish 须人工批准、install 先 preview 确认零写入。

## 与当前框架的结构对照

| 能力 | 当前框架 | Comet | 差异要点 |
| --- | --- | --- | --- |
| 流程骨架 | workflow-* skills（散文编排） | control 节点锁死 + `.comet.yaml` | 两套机制占同一位置，**不可并存于同一项目** |
| 交付门禁 | `check_delivery.py`（Profile 档位、spec drift、残留快照、状态一致性、知识影响） | comet-guard.mjs（任务/字段/证据/归档条件） | 文档层面 Comet 未见 spec drift、残留快照、状态一致性、知识影响的等价描述 |
| 知识体系 | `openspec/`（proposal/design/tasks/归档）+ Delta/Issues/冲突检查 | `.comet.yaml` + `docs/comet/`，无独立知识库概念 | 框架的知识同步门禁在 Comet 中无处落地 |
| Skill 评测 | 无机器验收（skill 更新靠人工） | `comet eval`：Rubric + Pass@k + 独立 Judge | Comet 有、框架无 |
| 扩展门禁 | 无（skill 可任意改） | 扩展物强制过 eval/readiness 才可 publish | Comet 有、框架无 |

## 迁移对照（当前框架 27 个 skills → Comet）

前提扫描：`workflow-*` 系列 17 处引用绑死 `check_delivery.py`、`.agentic-framework/`、`openspec/`，为框架私有基础设施；`std-*`/`bp-*` 等零绑定。

### 直接可迁（零改动，12 个）

`std-cpp/go/python/react`、`bp-architecture-design`、`bp-coding-best-practices`、`bp-component-design`、`bp-distributed-systems`、`bp-frontend-layout`、`bp-frontend-taste`、`bp-performance-optimization`、`bp-cli-tool-design`、`bp-skill-authoring`、`troubleshooting`、`self-refinement`——纯规范知识，零框架绑定；接入点为 Required Skill Call（绑 execute 或 review 节点，恰是官方给的两个例子）。`frontend-playwright-verification` 内容可迁（绑前端工作流不绑框架设施），更适合改造成 Native Verifier subagent 策略。

### 无需迁移（能力等价，9 个）

`workflow-requirements-clarification`（≈ `comet-open` / Native Shape 八节简报）、`workflow-system-design`（≈ `comet-design`）、`workflow-quick-design`（≈ `comet-hotfix`/`comet-tweak`）、`workflow-code-generation`（≈ `comet-build` / Native implement）、`workflow-code-review`（≈ `comet-review` / Native review）、`workflow-test-generation`（≈ Classic 内置 Superpowers TDD）、`workflow-verification`（≈ `comet-verify` + guard，skill 本体不迁，残值见下）、`open-code-review`（ocr CLI 薄封装，零框架绑定，本来就独立可用）。前 6 个迁的实质是「用散文编排覆写 control 节点」——恰是 Comet 明令禁止的，强行做只会打架。

`workflow-frontend-design` 单列：Comet 无前端设计等价物，但该 skill 不绑框架设施，留作独立 skill 随取随用即可，无需迁移动作。

### 唯一决策点：check_delivery.py 检查项 → Guardrail

`comet-verify` gate 文档层面查「任务完成、状态字段、验证证据、归档条件」，以下 4 项未见等价描述（推断级——guard 脚本未反读，不排除有等价机制）：

| # | 检查项 | 防什么 | 建议 |
| --- | --- | --- | --- |
| 1 | spec drift（diff 落在冻结范围，S0/S1 一致） | 交付超出约定范围 | 多 Agent 并行（Supervisor Changes）时才值钱；单人小 Change 收益低 |
| 2 | workspace residue snapshot（残留指纹入基线） | 残留物混入交付 | 同上，视交付纪律定 |
| 3 | `lint_task_deps` 状态一致性（复选框/状态字段同向） | Agent 为过门批量勾选作弊 | **建议补**——防「为过门作弊」与本框架「不偷改门禁」原则直接对应；Comet gate 只查字段存在、不查字段与事实同向 |
| 4 | knowledge-impact 检查 | 知识不同步就归档 | Comet 无 `openspec/` 知识体系，补了无处落地；除非保留知识库并让归档前查它 |

### 建议不迁（绑定最深，2 个）

`project-init`、`project-knowledge`——绑定 `openspec/index.md`、`openspec/changes/`、归档流程，是其存在理由；Comet 有自己的变更工件体系，硬迁造成两套 Change 管理并存，Agent 每次都要判断「归档去 openspec 还是去 .comet」，正是 Comet 设计反对的不确定性来源。

### 共存策略建议（未实测）

1. 不整库切换：workflow-* 门禁链是自研资产，Comet control 节点会将其锁死，两边都有完整验证哲学，并存必打架。
2. 侵入最小的共存路径：只装 Comet **Native**（`comet init --workflow native`，不碰 Classic/OpenSpec 生态），std-*/bp-* 用 Required Skill Call 挂上。
3. 反哺候选（借鉴回框架）：①skill 更新加机器验收（参照 comet eval 的 with/without + Rubric + 独立 Judge）；②扩展物强制过验收才可生效（参照其扩展 readiness 门禁）。

## 缺失证据与后续动作

- guard/state/hook 打包脚本内部逻辑未反读；「Comet 无 4 项检查等价物」为文档层面推断。
- 未实际安装运行；迁移可行性基于静态分析，未在 sandbox 项目验证 `comet init --workflow native` + Required Skill Call 端到端。
- Overlay 对 Output Schema 的具体格式只读了 schema 描述，未实跑 `/comet-any` 管线。
- 若进入实施：先在 sandbox 项目跑 Native + 单个 std-python 绑定验证，再批量。
