# 实施任务清单

> 由 proposal.md（Quick Draft）生成
> 任务总数: 5
> 核心原则: 先建核心过滤层（Task 1），再在其上串行叠加基线差集（Task 2）与 config 字段（Task 3，因二者都改 cmd_verify），文档（Task 4）并行，测试（Task 5）兜底覆盖

## 依赖关系总览

```
Task 1 (glob 忽略过滤核心)     Task 4 (SKILL.md 文档)
   │                              （独立，W1 并行）
   └──> Task 2 (基线快照差集 S0)
          │
          └──> Task 3 (config ignore_paths)
                 │
                 └──> Task 5 (测试覆盖)
```

波次：W1 = {Task 1, Task 4} → W2 = {Task 2} → W3 = {Task 3} → W4 = {Task 5}

> Task 2 与 Task 3 都修改 `cmd_verify`，按 lint 规则同文件不能无依赖并行，故 Task 3 串在 Task 2 之后。

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
|------|------|---------|------|
| `skills/workflow-verification/scripts/verify.py` | 修改 | Task 1, 2, 3 | 新增忽略过滤、基线快照、config 字段、CLI 参数 |
| `skills/workflow-verification/scripts/test_verify.py` | 修改 | Task 5 | 新增忽略能力测试 |
| `skills/workflow-verification/SKILL.md` | 修改 | Task 4 | spec drift 章节补忽略机制、集成表更新 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
|------|---------|--------|---------|
| `verify.py --ignore` | 新增 CLI 参数 | workflow-code-generation / 用户 | Task 1 |
| `verify.config.json: ignore_paths` | 新增 config 字段 | verify.py | Task 3 |
| baseline `changed_files_snapshot` | 新增字段 | verify.py 读写 | Task 2 |
| report `spec_drift.value.ignored_files` | 新增字段 | workflow-code-review / 用户 | Task 1 |

### 构建系统变更

- 无（纯 Python 脚本，无构建配置）。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
|---|------|---------|----------|
| 1 | 门禁绕过面：忽略能力可能被滥用逃避 spec drift | Task 1 | 护栏：禁忽略 `openspec/` spec/tasks + 审计字段 + 只过滤归类不关 check |
| 2 | glob `**` 跨目录语义在不同库下不一致 | Task 1 | 用 `fnmatch` + 手动 `**` 展开，明确语义并加测试 |
| 3 | 旧 baseline 缺 `changed_files_snapshot` 字段 | Task 2 | fail-closed：要求重采基线，不静默放过 |
| 4 | `ignore_paths` 改动是否触发 rebaseline | Task 3 | 不纳入 `config_snapshot`（详见 proposal 2.5 权衡 2） |
| 5 | build/test 对 `M` 半成品的编译不受忽略影响 | 全部 | 非目标，proposal 1.非目标已声明硬约束 |

## 任务列表

### 任务 1: [ ] glob 忽略过滤核心与 spec/tasks 护栏
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-verification/scripts/verify.py`（修改）
- depends_on: []
- review_profile: strict
- 文档映射: proposal.md 验收标准 / 2.1 整体方案 / 2.2 核心组件 / 2.4 数据模型 / 2.5 关键权衡 1,4
- 说明: 实现 spec drift 的忽略过滤核心。新增 `_glob_match(path, patterns)`（`fnmatch` + 手动 `**` 跨目录）、`_collect_ignores(cli_patterns, config_paths, baseline_s0)` 合并三来源。改造 `evaluate_spec_drift`：算出 changed files 后按忽略集过滤，剔除被忽略项出 code_files/spec_files 并记入 `ignored_files`；对 `_is_spec_file` 命中的 `openspec/` spec/tasks 文件即便命中忽略 pattern 也拒绝剔除，并在 report 标注。新增 CLI `--ignore`（可重复，append）。本任务先接 CLI 来源，config 与 baseline 来源以空列表占位（Task 2/3 填充）。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:evaluate_spec_drift` — 直接改造目标
  - `skills/workflow-verification/scripts/verify.py:_changed_files` — 上游，changed files 来源
  - `skills/workflow-verification/scripts/verify.py:_is_code_file` / `_is_spec_file` — 归类与护栏依据
  - `skills/workflow-verification/scripts/verify.py:main` — CLI argparse，新增 `--ignore`
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py -q` 全部通过（含新增的 glob/过滤/护栏用例）
  - [ ] `python skills/workflow-verification/scripts/verify.py --help` 输出含 `--ignore`
  - [ ] 手动：构造一个 untracked 代码文件，传 `--ignore` 后 spec drift 不把它算入 code_files；对 `openspec/` 下 tasks.md 传 `--ignore` 被拒绝
- artifacts:
  - `skills/workflow-verification/scripts/verify.py`（修改）
- 子任务:
  - [ ] 1.1: 实现 `_glob_match`（`fnmatch` + `**` 跨目录）与单元测试
  - [ ] 1.2: 实现 `_collect_ignores` 合并逻辑（CLI 来源先接，config/baseline 占位空）
  - [ ] 1.3: 改造 `evaluate_spec_drift` 注入忽略过滤与 `ignored_files` 审计
  - [ ] 1.4: 实现 spec/tasks 拒绝忽略护栏（`_is_spec_file` 命中不剔除）
  - [ ] 1.5: 新增 CLI `--ignore` 参数并接入
  - [ ] 1.6: 调用 `workflow-test-generation` 为本任务核心逻辑生成测试，运行通过

### 任务 2: [ ] 基线快照差集（S0）
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-verification/scripts/verify.py`（修改）
- depends_on: [Task 1]
- review_profile: strict
- 文档映射: proposal.md 验收标准（S0 防篡改）/ 2.2 核心组件 / 2.5 关键权衡 3,4
- 说明: `cmd_save_baseline` 采基线时额外记录 `changed_files_snapshot`（= 当时的 changed files，即 S0）。`cmd_verify` 读取 baseline 的 S0，传入 `_collect_ignores` 作为第三个来源；verify 时的 changed files（S1）扣除 S0 后再算 code_files（本次 = S1 − S0 的语义通过「S0 进忽略集」实现）。旧 baseline 缺 `changed_files_snapshot` 字段时 fail-closed（要求重采基线），不静默放过。S0 的不可篡改由既有「不得验证后重采基线」规则保护（不在代码层额外强制）。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:cmd_save_baseline` — 直接改造，存 S0
  - `skills/workflow-verification/scripts/verify.py:cmd_verify` — 直接改造，读 S0 并传给 `_collect_ignores`
  - `skills/workflow-verification/scripts/verify.py:_collect_ignores` — Task 1 产出，本任务填充 baseline 来源
  - `skills/workflow-verification/scripts/verify.py:_changed_files` — S0 / S1 数据来源
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py -q` 全部通过（含 S0 差集用例）
  - [ ] 手动：采基线（`--save-baseline`）后 baseline.json 含 `changed_files_snapshot`；用旧 baseline（缺字段）跑 verify 报 fail-closed 错误
- artifacts:
  - `skills/workflow-verification/scripts/verify.py`（修改）
- 子任务:
  - [ ] 2.1: `cmd_save_baseline` 记录 `changed_files_snapshot`
  - [ ] 2.2: `cmd_verify` 读 S0 并接入 `_collect_ignores`
  - [ ] 2.3: 旧 baseline 缺字段 fail-closed 校验
  - [ ] 2.4: 调用 `workflow-test-generation` 生成 S0 差集与 fail-closed 测试，运行通过

### 任务 3: [ ] config ignore_paths 字段
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-verification/scripts/verify.py`（修改）
- depends_on: [Task 1, Task 2]
- review_profile: strict
- 文档映射: proposal.md 2.2 核心组件 / 2.3 主要接口 / 2.5 关键权衡 2
- 说明: `verify.config.json` 新增顶层可选字段 `ignore_paths`（glob 字符串列表）。`_validate_config` / `load_config` 校验其类型为 `list[str]`（缺失允许）。`cmd_verify` 读取 config 的 `ignore_paths` 传入 `_collect_ignores` 的 config 来源。**不纳入** `_config_snapshot` / `_check_fingerprint`（只影响内置 spec drift，spec drift 不在 `config.checks` 覆盖范围；详见 proposal 2.5 权衡 2）。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:_validate_config` / `load_config` — schema 校验
  - `skills/workflow-verification/scripts/verify.py:cmd_verify` — 读 config `ignore_paths` 传给 `_collect_ignores`
  - `skills/workflow-verification/scripts/verify.py:_collect_ignores` — Task 1 产出，本任务填充 config 来源
  - `skills/workflow-verification/scripts/verify.py:_config_snapshot` — 确认 `ignore_paths` 不被纳入
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py -q` 全部通过（含 config `ignore_paths` 用例）
  - [ ] 手动：config 含 `ignore_paths` 时对应文件被忽略；不含字段时行为不变；改 `ignore_paths` 不触发 `config_snapshot` 不一致错误
- artifacts:
  - `skills/workflow-verification/scripts/verify.py`（修改）
- 子任务:
  - [ ] 3.1: `_validate_config` / `load_config` 加 `ignore_paths` 校验（`list[str]`，可选）
  - [ ] 3.2: `cmd_verify` 读 config `ignore_paths` 接入 `_collect_ignores`
  - [ ] 3.3: 确认 `_config_snapshot` 不含 `ignore_paths`，并加测试验证改 `ignore_paths` 不触发 rebaseline
  - [ ] 3.4: 调用 `workflow-test-generation` 生成 config `ignore_paths` 测试，运行通过

### 任务 4: [ ] SKILL.md 文档更新
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-verification/SKILL.md`（修改）
- depends_on: []
- review_profile: lightweight
- 文档映射: proposal.md 2.3 主要接口 / 3. 知识影响（spec drift 契约）
- 说明: 在 SKILL.md 的「内置 spec drift 检查」章节（第 17-30 行）补充忽略机制：三种指定渠道（`--ignore` / config `ignore_paths` / 基线 S0）、glob 语义、安全护栏（禁忽略 `openspec/` spec/tasks）、审计字段、硬约束（不救 build/test 的 `M` 半成品）。更新「与 workflow-code-generation 集成」表（第 89-92 行），说明采基线时同时快照 changed files、验证时可传 `--ignore`。文档基于已锁定的 proposal 设计先写，实现后由该任务 verification 人工核对一致性。
- context_files:
  - `skills/workflow-verification/SKILL.md` — 直接修改目标
  - `skills/workflow-verification/scripts/verify.py` — 文档需与实现一致（Task 1/2/3 产出）
- verification:
  - [ ] SKILL.md 含忽略机制说明（`grep -n -- "--ignore\|ignore_paths" skills/workflow-verification/SKILL.md` 有命中）
  - [ ] 文档与实现接口一致（人工核对 CLI 参数、config 字段、report 字段）
- artifacts:
  - `skills/workflow-verification/SKILL.md`（修改）
- 子任务:
  - [ ] 4.1: spec drift 章节补忽略机制（三渠道 / glob / 护栏 / 审计 / 硬约束）
  - [ ] 4.2: 集成表更新（基线快照 changed files、`--ignore`）

### 任务 5: [ ] 测试覆盖与全量回归
- 状态：完成
- attempts：0
- control_stage：completed
- 文件: `skills/workflow-verification/scripts/test_verify.py`（修改）
- depends_on: [Task 1, Task 2, Task 3]
- review_profile: strict
- 文档映射: proposal.md 验收标准（全部）
- 说明: 在 `test_verify.py` 新增覆盖忽略能力的端到端测试：三种渠道各自可用且可叠加、glob（`*` / `?` / `**`）、安全护栏（`openspec/` spec/tasks 拒绝忽略）、审计字段（`ignored_files`）、S0 防篡改（旧 baseline fail-closed、改 `ignore_paths` 不触发 rebaseline）。运行全量回归确保现有测试不破坏。Task 1/2/3 内嵌的单元测试在此汇聚为完整覆盖。
- context_files:
  - `skills/workflow-verification/scripts/test_verify.py` — 直接修改目标
  - `skills/workflow-verification/scripts/verify.py` — 被测对象（Task 1/2/3 产出）
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py -q` 全部通过，无回归
  - [ ] 新增测试覆盖三渠道叠加、glob 三种通配、spec/tasks 护栏、审计字段、S0 防篡改
- artifacts:
  - `skills/workflow-verification/scripts/test_verify.py`（修改）
- 子任务:
  - [ ] 5.1: 新增三渠道叠加端到端测试
  - [ ] 5.2: 新增 glob（`*` / `?` / `**`）测试
  - [ ] 5.3: 新增 spec/tasks 拒绝忽略护栏测试
  - [ ] 5.4: 新增 `ignored_files` 审计字段测试
  - [ ] 5.5: 新增 S0 防篡改（fail-closed / rebaseline）测试
  - [ ] 5.6: 全量回归通过

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
|-----------|------|------|
| proposal 1.问题 | Task 1 | 根因在过滤层实现中体现 |
| proposal 1.验收标准 | Task 1, 2, 3, 5 | 忽略过滤 / 三渠道 / S0 / 测试全覆盖 |
| proposal 2.1 整体方案 | Task 1, 2, 3 | 过滤层 + 基线 + config |
| proposal 2.2 核心组件 | Task 1, 2, 3 | 各改动点对应 |
| proposal 2.3 主要接口 | Task 1, 3, 4 | CLI / config / report 接口 + 文档 |
| proposal 2.4 数据模型 | Task 1 | 忽略集合并集语义 |
| proposal 2.5 关键权衡 | Task 1, 2, 3 | glob / snapshot 不纳入 / 护栏 |
| proposal 3.知识影响（SKILL.md） | Task 4 | spec drift 契约文档 |

## 知识同步

| Delta | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| （Quick，无 Delta） | `openspec/specs/backend/framework/quality-gates/`（verification 相关章节） | MODIFIED | Pending | 归档时由 project-knowledge 按 proposal 3. 知识影响同步 |

> 本 Change 为 Quick Draft，未创建 `specs/` Delta。长期知识影响（quality-gates 下 verification 章节的新增 CLI / config / baseline 字段与忽略机制契约）在归档阶段由 `project-knowledge` 同步到长期 specs。

## 知识冲突

- 结论：待核对。归档前写「无冲突」，或记录双方证据并标记 `Resolved`。

## 实际 Diff 核对

- 核对状态：Pending。归档前记录实际 Diff、Change 和测试证据的核对命令与 PASS 结论。
