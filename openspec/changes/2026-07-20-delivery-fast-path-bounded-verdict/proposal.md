# 交付门支持 Fast-Path 有界裁决

- **状态**：Quick Draft
- **日期**：2026-07-20
- **作者**：主会话

## 1. 背景

`workflow-code-generation` 的 Fast-Path 定义为「请求即计划的局部低风险修改」，使用 `review_profile: lightweight` 单 reviewer，第 8 步要求过 `check_delivery.py`。

但 `check_delivery.py` 当前实现与该定义矛盾：

- 无 `--run-dir` 时直接报错「缺少 --run-dir，旧无绑定 Review PASS 不得放行」；
- 有 `--run-dir` 时走 `finalize_run` → `runtime_trust.validate_run`，Trust Gate 强制 `review_profile: strict` + 独立 judge。

结果：Fast-Path 按定义**永远过不了交付门**。trivial 改动要么被迫跑完整 strict 独立 Run（不成比例），要么无法机器放行。

证据：`skills/workflow-code-generation/scripts/check_delivery.py:228-283`、`skills/workflow-code-generation/SKILL.md` 第 8 步、`openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` §4.2。

## 2. 目标

为 `check_delivery.py` 增加 Fast-Path 有界裁决路径：

- 无 `--run-dir` 时进入 Fast-Path 模式：校验 lightweight Review、机器验证报告、工作区干净、知识影响结论；
- 输出裁决 `fast-path-pass`，并显式列出 `unprovable_claims`（strict 独立审查、Run 证据图、Harness 能力探测）；
- strict Run 路径（`--run-dir`）**保持不变**，仍走完整 Trust Gate。

## 3. 方案

- 新增 `--verify-report` 参数，默认 `.agentic-framework/verify/report.json`。
- Fast-Path 模式（`--run-dir` 缺省）：
  - `check_fast_path_review`：复用 `check_review_report`（verdict=PASS、P0/P1=0、scope=run、round≥0），并强制 `review_profile == lightweight`；strict/standard 无 Run 拒绝。
  - `check_verify_report`：机器验证报告 verdict=PASS、errors=0、violations=0。
  - 复用 `check_git_clean` 与 `check_knowledge_impact`。
  - 不调用 `finalize_run` / Trust Gate。
  - 输出 `fast-path-pass` + `verified_claims` + `unprovable_claims`。
- strict 模式（`--run-dir` 给定）：逻辑不变。

## 4. 非目标

- 不改 Trust Gate 本体（`runtime_trust`）。
- 不新增 JSON Schema（Fast-Path 摘要仅为终端输出 + 知识影响结论，非 Run Artifact）。
- 不削弱 strict Run 路径。
- 不让 Fast-Path 声明 strict 独立审查已通过。

## 5. 成功标准

- Fast-Path 合法输入（lightweight PASS review + 机器验证 PASS + 工作区干净 + 知识影响已声明）→ exit 0，输出 `fast-path-pass`。
- Fast-Path 拒绝：strict/standard review 无 Run、机器验证 FAIL、Review P0/P1≠0、工作区脏、知识影响缺声明。
- strict Run 路径回归通过（既有端到端测试不退化）。
- spec.md 新增 Fast-Path 有界裁决 Scenario。

## 6. 知识影响

- 命中：交付门 Fast-Path 语义、Trust Model 边界澄清。
- 直接写入活跃长期 spec.md（`machine-verifiable-agent-runtime`）与 Trust Model 文档；不新建 ADR。
- 不修改跨项目公共知识库。
