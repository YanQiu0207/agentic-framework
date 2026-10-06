# 交付指南

轻量任务进入执行前读取“轻量交付”；标准任务收尾时读取“标准交付”。所有路径都读取“交付前沉淀检查”和“统一交付证据格式”。采用 Scoped Delivery 时，在采基线前读取对应章节。

本指南中的步骤 1、1.5、3、4 指主 Skill 的同名步骤；步骤 6 指本指南的标准交付。

## 轻量交付（Fast-Path 兼容）

轻量任务由当前宿主执行；中等任务可下放 Agent 并按需使用 DAG。

两者都属于 Native Delivery，不创建或伪造 Run Context。**Fast-Path 只是旧调用方的兼容别名，不再按「主会话直接修改」定义另一条默认路径。**兼容别名保留 lightweight integration Review；新的低／中风险标准交付使用 standard integration Review。

两者都不增加完整 Runtime 的声明。

1. 加载编码规范（同步骤 4）。
2. 实现改动（步骤 1.5 已完成配置选择；有 `verify.config.json` 时，动代码前先 `workflow-verification` 采基线；选择跳过时只跑内置门禁并在交付报告标注）。发现外溢（超出步骤 1 路由判据）→ **立即退出**，转标准流程。
3. **机器验证**：加载 `workflow-verification`（有 config 比基线；无 config 也跑内置 spec drift 检查），通过后继续；失败回第 2 步修复，若只是无法证明相关规格已更新且确实无需更新，则补 `--spec-drift-reason` 后重跑。
4. **前端验证**：若涉及 UI / 样式 / `.tsx` / 用户操作路径，加载 `bp-frontend-taste` 后再用 `frontend-playwright-verification` 做浏览器验证；产生代码改动时回到第 3 步重验。
5. **统一 Code Review**：实现、测试和机器验证全部完成后，加载一次 `workflow-code-review`（Fast-Path 兼容别名使用 `review_profile: lightweight`；新的 Native Delivery 使用 `standard`；均为 `scope: integration`，`mode: initial`）。

   Review Artifact 必须由审查流程生成，implementer 只能原样保存，不得依据对话手写 JSON。

   结论为 `NEEDS_CHANGES`（存在 keep 的 P0 / P1）→ 自行修复、重跑受影响的机器验证，再按 `mode: re-review` 定向复核，最多 10 轮；禁止启动第二次全量首审。
6. **交付前沉淀检查**：见下方[「交付前沉淀检查」](#交付前沉淀检查)（强制，Fast-Path 不豁免）。
7. **提交**：将本次改动提交本地 git（push / `svn commit` 由用户决定）；用户明确要求不提交时，在交付报告标注「未提交待用户处理」。
8. **交付门（机器判定）**：Fast-Path 兼容别名免传 spec / tasks 与 `--run-dir`，但必须传由审查流程生成的 lightweight integration Review、独立机器验证报告与长期知识影响结论：命中时运行 `python <本 skill 目录>/scripts/check_delivery.py --review-report <review-report.json> --verify-report <.agentic-framework/verify/report.json> --knowledge-impact hit`；未命中时运行 `python <本 skill 目录>/scripts/check_delivery.py --review-report <review-report.json> --verify-report <.agentic-framework/verify/report.json> --knowledge-impact none --knowledge-impact-reason "<具体理由>"`。

   门禁校验 `scope: integration` 的 lightweight Review（P0／P1 = 0）、机器验证 verdict = PASS、工作区干净与知识影响结论；通过则输出兼容裁决 `fast-path-pass`，不得声明 strict Review 或 Trust Gate PASS。

   交付报告只能逐字引用该命令的原始输出，并标为「Fast-Path 兼容裁决」；由于没有归档路径，不得把它概括为「交付门 PASS」。

   新的标准 Native Delivery 必须走下方标准流程的 `--native-delivery` 门。

   非 0 → 补齐 Review 报告、机器验证、知识影响结论或提交后重跑。
9. 按[「统一交付证据格式」](#统一交付证据格式)输出改动说明，**结束**。

## 标准交付

全部 wave 处理完、`tasks.md` 任务为 `完成` / `需人工` / `阻塞` 时，**禁止直接宣布交付**，先走：

1. **汇总报告**（一次性，不逐 task）：汇总每个 task 的实现、测试和机器检查结果，列出哪些 `需人工`、哪些 `阻塞`、哪些合并冲突。
2. **机器验证**：对合并结果整体跑 `workflow-verification`。

   `runtime-run` 传 `--run-dir <run-dir>` 生成 Run 级 Verify Artifact；`native-delivery` 生成独立 Verify 报告，不创建 Run Artifact。

   有 config 时必须传 `--baseline <repo-root>/.agentic-framework/verify/baseline.json --diff-base <base_sha>`；无 config 时必须传 `--diff-base <base_sha>` 触发内置 spec drift 检查。

   FAIL → 派 fix Agent 修复后重验；仍 FAIL 标 `需人工`。
3. **前端验证**：若涉及 UI / 样式 / `.tsx` / 用户操作路径，加载 `bp-frontend-taste` 后再用 `frontend-playwright-verification` 做浏览器验证。失败则修复并回到第 2 步重验。
4. **一次最终审核**：对本次全部变更调用一次 `workflow-code-review`（`mode: initial`）。

   `native-delivery` 固定产出无 Run 的 `scope: integration`、`review_profile: standard` 报告；`runtime-run` 固定产出绑定 Run Context 的 `scope: run`、`review_profile: strict` Envelope。

   Artifact 必须由审查流程生成：`standard` 可由 `comprehensive-reviewer` 自证，`strict` 必须由未参与实现的独立 Judge 裁决；implementer 不得手写或改写 Artifact。

   存在 keep 的 P0 / P1 时派 fix agent 修复、重跑受影响的验证，再按 `mode: re-review` 只复核 finding 和修复 diff；最多 10 轮，禁止启动第二次全量首审。
5. **交付前沉淀检查**：见下方[「交付前沉淀检查」](#交付前沉淀检查)，执行统一知识影响检查，并逐条核销步骤 3 / Phase 1 预留的「intent 沉淀」任务。命中长期知识影响时记录目标 `openspec/specs/` 或 `openspec/issues/` 及同步状态；Fast-Path 未创建 Change 时必须说明无长期知识影响的理由。
6. **知识同步与归档**：加载 `project-knowledge`，对照实际 Diff 和验证证据完成 Delta、索引、Issues 与冲突检查；知识同步任务未完成时禁止归档。**归档移动前必须先跑 `python <本 skill 目录>/scripts/lint_task_deps.py <tasks.md 路径> --state-consistency`**：`tasks.md` 的任务头复选框、`- 状态：` 字段与验收标准／子任务复选框必须同向。

   `状态：完成` 的任务，任务头须标 `[x]` 且验收项与子任务全部勾选——复选框由执行方按**真实完成情况**勾选，不得为过门而批量勾选；未达成的验收项应改状态为 `需人工` / `阻塞` 并附原因。

   非 0 → 修正后重跑，不得带着矛盾状态归档。

   通过后把 `proposal.md` 头部 `状态` 改为 `Archived`，并将整个 Change 移到 `openspec/changes/archive/<ticket>-YYYY-MM-DD-<change-name>/`。
7. **提交归档产物**：将工作区本次残留的全部改动（fix 修复、spec / tasks / ADR / issues 等文档）提交本地 git，提交信息关联 feature，交付时工作区必须干净；push / `svn commit` 仍由用户决定。
8. **交付门（机器判定）**：`runtime-run` 对归档后的路径运行 `python <本 skill 目录>/scripts/check_delivery.py --run-dir <run-dir> --tasks <archived-tasks.md> --spec <archived-proposal.md> --review-report <run-dir>/artifacts/review-run.json --knowledge-impact hit|none`；`none` 时追加 `--knowledge-impact-reason "<具体理由>"`。

   门禁校验完整 Manifest 可达性、Journal、Harness 启动证据、Trust Gate、任务终态（含状态字段与复选框一致性）、归档、Git 状态与知识影响结论。

   `native-delivery` 运行 `python <本 skill 目录>/scripts/check_delivery.py --native-delivery --native-delivery-verdict <repo>/.agentic-framework/native-delivery/verdict.json --tasks <archived-tasks.md> --spec <archived-proposal.md> --review-report <review-report.json> --verify-report <verify-report.json> --knowledge-impact hit|none`；`none` 时追加 `--knowledge-impact-reason "<具体理由>"`。

   该门只接受由审查流程生成的无 Run standard integration Review 与独立 Verify，只能生成有界 Verdict，不得声明 Trust Gate 或 Harness 能力。**交付报告只能逐字引用 `check_delivery.py` 成功执行的原始 stdout，不得自行归纳为「交付门 PASS」或等价措辞。** 缺少归档路径、干净 Git 状态或有效 Review / Verify Artifact，或命令非 0 时，禁止任何「交付门 PASS」类表述；必须改报实际缺失项或失败输出。

   非 0 → 回对应步骤修复后重跑。
9. 按[「统一交付证据格式」](#统一交付证据格式)交付，等用户验收 `需人工` / `阻塞` 项的处理。

## Scoped Delivery（显式例外）

默认交付门保持「工作区干净」（Git）；SVN 原生路径按下方「SVN 原生交付」处理预期本地改动。

只有本次任务已在动代码前冻结允许修改路径／生成目录，并由 `workflow-verification --save-baseline --delivery-scope <路径>` 写入 `workspace_residue_snapshot` 时，Native Delivery 才可显式传 `check_delivery.py --scoped-delivery --workspace-residue-baseline <baseline>`：

- Scoped Delivery 必须与 `--native-delivery` 一起使用，并声明 `--knowledge-impact hit|none`；`none` 时必须追加 `--knowledge-impact-reason "<具体理由>"`。Git 同时传 `--delivery-commit <HEAD>`，SVN 同时传 `--delivery-revision <已提交 revision>`。
- 交付门比较 S1 与 S0，并拒绝提交 Diff 超出冻结范围的路径；`--ignore`、`ignore_paths` 和 `changed_files_snapshot` 不参与此判定。
- Scoped Delivery 不适用于完整 Runtime Run；S0 与范围重叠、内容变化、提交证据缺失或无法判定时，切换干净 worktree／工作副本。
- Git Scoped 成功产出 v2 `git-scoped-delivery-pass`（提交 sha、冻结范围与 S0 残留摘要入证据，不用 `git_clean` 包装脏工作区）；SVN Scoped 按「SVN 原生交付」产出 `svn-revision-verified`。Scoped 成功报告只能逐字引用「本次交付范围干净，预存残留未变化」，不得声称「Git 工作区干净」。

## SVN 原生交付（串行工作流）

纯 SVN 工作副本的 Native Delivery 按固定串行顺序推进；`update` / `commit` 只发生在下述明确步骤，查询与门禁绝不代执行（change 2048）：

1. **保护预存改动**：开始前检查工作副本本地改动。干净副本可继续；有预存改动时先展示影响，需要 Scoped Delivery 的在动代码前冻结范围并采残留快照，不得自动 revert 或用更新覆盖未知状态。
2. **更新并记录基准**：完成必要更新后记录仓库身份（UUID + repository-relative URL）与节点基准。混合版本、switched、sparse、externals 等无法完整判定的状态不发完整 PASS，明确报告限制。
3. **串行开发、验证、审查**：工作副本是唯一开发内容，不创建 Git 镜像或桥接。并行只允许只读调研/审查；写入串行。
4. **提交前上游核对**：提交前查询上游（`svn status -u`）。相关上游有变化时更新、解决冲突，并按新主体重新验证／审查——一次 `svn status -u` 的结果不是「之后不会再变化」的保证；文本无冲突也不代表验证过他人改动与自己改动的组合。
5. **无授权 → 待提交**：没有提交授权时，本地完成验证与审查后运行 `check_delivery.py --native-delivery`（SVN 不适用 Git clean，本地预期改动即交付内容），产出 `svn-pending-commit`。这是完成报告状态，**不是正式交付 PASS**；交付报告逐字引用原始输出并注明待提交。
6. **有授权 → 明确提交**：展示范围与差异后执行 `svn commit`，记录实际返回 revision。超时或响应丢失导致结果不明时，先核对服务器日志与实际内容，不盲目重提、不推断成功；SVN 可能接纳他人不同文件的提交，正式声明只绑定核验过的 revision。
7. **确切版本验证**：更新到交付 revision，对当前内容重跑 Verify／Review（提交前的报告只保留为提交前证据），再以 `--scoped-delivery --delivery-revision <N>` 运行交付门，产出 `svn-revision-verified`。提交后验证失败时如实报告「已提交、版本验证失败」，不自动回滚共享版本；是否修复或回退由后续明确任务决定。

## 统一交付证据格式

最终报告必须包含：

```markdown
## 任务归因
- **Feature**: [feature 标识]
- **Task**: [Task ID/名称]
- **Review Profile**: lightweight / standard / strict
- **Review Retries**: [非负整数]
- **Verify Retries**: [非负整数]
- **Manual Intervention**: 无 / [介入阶段，多个位置用中文逗号分隔]
```

每个 task 输出一个完整区块；同一 task 再次交付时重新输出完整区块。字段名和标题是遥测解析接口，不得改写或省略，不得从对话推测未知值。

- **改动文件**：列出代码、规格、任务、ADR 和关键文档。
- **提交状态**：本地 commit hash（代码与归档产物），或「未提交待用户处理」及原因。
- **交付门**：完整粘贴 `check_delivery.py` 的原始 stdout，不增写 Verdict 摘要、PASS 结论或「交付门 PASS」类措辞。未运行、非 0、缺少归档路径、工作区不干净或 Artifact 无效时，只写实际状态和原始错误，不得声明交付通过。
- **测试命令**：列出实际运行命令、结果；未运行写原因。
- **review 结论**：列出 review_profile、通过 / finding / 需人工。
- **机器验证**：列出 `workflow-verification` 结果和 `.agentic-framework/verify/report.json` 路径；必须包含 `spec_drift` 结论；注明配置消费状态（使用现有 / 缺失已跳过 / 建议刷新及原因——如 exit 2 或配置引用的命令、路径失效，提示用户之后运行 `/verify-config`，不在任务内改配置）。
- **前端截图 / DOM 验证**：涉及 UI 时列截图路径、DOM / console / 交互检查；不涉及写「不涉及」。
- **未验证风险**：列出无法验证项、阻塞原因和建议补验方式。

---

## 交付前沉淀检查

Fast-Path 与标准交付都执行此检查。

逐条检查「架构决策」「放弃方案」「新增红线约束」三个信号，并逐行作答「命中 → 已沉淀到 <具体 ADR / spec 章节>」或「未命中」。命中则更新相关 `proposal.md`、`design.md` 或长期 Specs；当前无法完成时在 `tasks.md` 建「intent 沉淀」任务。

---
