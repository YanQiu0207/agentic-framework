---
name: workflow-verification
description: 研发后机器验证门。有 verify.config.json 时配置驱动跑 build / test / lint 等客观检查 + 改动前后基线对比、只追新增违规；内置 spec drift 检查：改了代码但相关 spec.md / ui-spec.md / tasks.md / ADR 未更新时，必须提供无需更新原因。Task 合并前、Native Delivery 最终 Review 前和完整 Runtime Run 最终 Review 前执行。workflow-code-generation 实现后判定「是否真做完」，或用户要求跑验证时使用；用户显式要求「初始化 / 刷新 verify 配置」（/verify-config）时进入配置维护模式——这是常规写入路径；实现产生已试运行的新入口时可受限追加非基线检查。
---

> 输出一行：`Using workflow-verification`

# 研发后机器验证门

把「完成」从 LLM 说了算变成机器绿灯。机器能验的不靠 LLM 背书。

## 两种模式

- **有 `verify.config.json`（大多数项目）** → 配置驱动，`scripts/verify.py` 跑 + 基线对比。
- **没有** → 只跑内置门禁；其余检查跳过，并提示用户可运行 `/verify-config` 初始化配置（见下方配置维护模式）。

## 交付路径与 Verify 产物

| 交付路径 | Verify 产物 | 交付用途 | 禁止事项 |
| --- | --- | --- | --- |
| Native Delivery | 独立 `.agentic-framework/verify/report.json`，不传 `--run-dir` | `check_delivery.py --native-delivery` 消费 PASS 的独立 Verify 与标准 integration Review。 | 不得伪造 `run_id`、Harness、Trust Gate 或 Run Artifact。 |
| 完整 Runtime Run | 传 `--run-dir <run-dir>` 生成 Run-bound Verify Artifact。 | 完整 Runtime 的 Manifest、Journal、Capability 与 Trust Gate 证据链。 | 不得以独立报告替代 Run-bound Artifact。 |
| Fast-Path 兼容别名 | 与 Native Delivery 相同的独立 Verify 报告。 | 只服务尚未迁移的低风险调用；不构成独立默认路径。 | 不得声明 Runtime 证据。 |

独立 Verify 只证明已执行的机器检查及其结果。`scope: run` 或 `strict` Review 的交付，必须走完整 Runtime Run；Verify 本身不能把无 Run 任务升级为 Trust Gate PASS。

## 内置 spec drift 检查

`verify.py` 总会检查本次改动文件列表，VCS 由 `verify.py` 自动探测：

- Git 工作副本 → `git diff --name-only <base>` + `git ls-files --others`。
- SVN 工作副本 → `svn status`（`A/M/D` 计为已纳入改动，`?` 计为未跟踪，`I` 跳过）。纯 SVN 模式按规则「只 `svn add`、不 `svn commit`」，一个 Change 期间无提交，工作副本本地改动即「本次改动」的全部，`--diff-base` 在 SVN 下不使用。
- 两端都探测不到 → spec drift 判 error，提示不在 Git 仓库或 SVN 工作副本内。

- 改了代码文件，且无法证明相关活跃 Change（`spec.md` / `ui-spec.md` / `tasks.md`）或长期 `openspec/specs/`、`openspec/issues/` 已按知识影响更新 → FAIL。
- 相关性只做机械判定：`tasks.md` 中出现代码路径，或代码文件位于同一规格目录下；判不出相关时必须传 `--spec-drift-reason "<原因>"`。旧 `docs/design-docs/` 只作为迁移输入，不作为新改动的规格写入目标。
- 标准 / 下放流程（Git 模式）必须在 Phase 0 记录 `base_sha`，后续验证显式传 `--diff-base <base_sha>`；禁止在已提交 / 已合并后的 clean 工作区裸用默认 `HEAD` 作为基准。SVN 模式无此要求，spec drift 直接读工作副本本地改动。
- 知识源新鲜度：`meta.yaml` 的 `source_ref` 校验 `git:<sha>`（commit 存在且来源路径最后提交是其祖先）与 `svn:<rev>`（revision 存在且来源路径最后修订号 `<= ref rev`，需 SVN 1.9+ 的 `--show-item`）两种形式，其余前缀报「不可解析」。
- 报告写入 `.agentic-framework/verify/report.json` 的 `spec_drift` 字段，交付报告必须引用。

### 忽略指定路径（不卷入 spec drift）

工作目录里常有不想提交的本地改动（公司 SVN 项目的本地调试文件、已跟踪文件的临时修改、未跟踪的本地脚本），会被 spec drift 误算入「本次改动」。`--ignore` 按指定路径把它们剔除出 code/spec 归类。

- **三种指定渠道**（取并集，可叠加）：
  - 命令行 `--ignore <glob>`（可重复）。
  - `verify.config.json` 顶层 `ignore_paths: [glob, ...]`（项目级长期忽略）。
  - 基线快照差集：`--save-baseline` 时自动记录当时的 changed files（S0），`verify` 时本次改动 = S1 − S0（动代码前已存在的本地改动自动排除）。旧基线缺 `changed_files_snapshot` 字段时 fail-closed，要求重采基线。
- **glob 语义**：`fnmatchcase`（大小写敏感、跨 OS 一致），`*` / `**` 跨目录、`?` 单字符；目录模式（`dir/` 或 `dir`）覆盖其下全部文件。被忽略文件在 report 中按来源标注（`ignore_sources`：cli / config / baseline）。
- **安全护栏**：`openspec/` 下的 `spec.md` / `ui-spec.md` / `tasks.md` / ADR 永不可忽略——忽略它们会让 spec drift 被静默绕过；命中忽略但仍属规格类的文件记入 report 的 `refused_ignores` 并照常归类。
- **审计**：被忽略文件写入 report 的 `spec_drift.value.ignored_files`，供 Review 核查。
- **硬约束**：`--ignore` 只作用于 spec drift 归类；build / test / lint 仍编译运行工作树全部文件，`M` 半成品仍需物理隔离（patch 往返 / 第二工作副本）。

示例：

```bash
python <skill-dir>/scripts/verify.py \
  --spec-drift-reason "仅修复脚本输出编码，不改变需求、任务拆解或架构决策"
```

## 配置驱动

三类检查（config 的 `type` 字段）：

| type | 判定 | 用途 |
| --- | --- | --- |
| `exit_code` | 退出码 == `expect_code` | 编译必过、测试必过、自定义校验脚本 |
| `forbid_pattern` | 命中的每行算一处违规 | 静态规范：禁用 API / 语法 / 硬编码 |
| `count` | stdout 解析为数字按方向比 | 测试数不减少、文件不超长 |

`baseline_aware: true` 的检查参与基线对比，**只判超出基线的新增违规**（历史遗留不阻塞）。`forbid_pattern` 命令用 `-H` 保留文件路径、不带行号。

用法（`<skill-dir>` = 本 skill 安装目录）：

```bash
# 改动前采基线
python <skill-dir>/scripts/verify.py --save-baseline .agentic-framework/verify/baseline.json
# 改动后验证并对比
python <skill-dir>/scripts/verify.py --baseline .agentic-framework/verify/baseline.json
```

退出码：`0` 全过；`1` 有新增违规或 spec drift（进修复循环）；`2` 门禁自身出错（先排查配置）。

配置项目：`cp <skill-dir>/reference/verify.config.example.json verify.config.json`，按技术栈改 `command`；`.agentic-framework/` 加进忽略配置（Git → `.gitignore`，SVN → `svn:ignore`）。**怎么写配置、怎么接入自己的脚本见 [reference/config-guide.md](reference/config-guide.md)。**

## 配置维护模式（用户触发）

用户显式要求「初始化 / 刷新 verify 配置」或运行 `/verify-config` 时进入。这是 `verify.config.json` 的**常规写入路径**；代码任务冻结既有检查，只有下方「实现产生新入口」的受限例外可以追加新检查。

流程：检查仓库证据 → 生成或刷新 → 校验结构 → 试运行 → 弱化类变更经用户确认 → 写入并纳入版本控制。

### 实现产生新入口的受限例外

若已在改动前采集基线，且实现本身产生新的、安全且可在当前工作区试运行的构建、测试或 Lint 入口，允许在实现期**仅追加**一个或多个新检查，条件必须同时满足：

- 现有 `verify.config.json` 和改动前基线均存在；缺配置或用户已选择跳过时，不得借此创建配置。
- 新入口来自本次实现的仓库证据；命令在写入前已独立试运行成功，且不访问真实外部资源、不需要凭证、不修改外部状态。
- 追加的检查使用唯一 `name`，显式设为 `baseline_aware: false`，并提供非空 `_note` 说明新入口及试运行证据；Verify 在执行前校验这两项。
- 不得修改或删除既有检查、`ignore_paths`，不得重采基线，也不得把任何既有检查改为非基线模式。

追加后仍须带原基线运行 Verify。新检查按绝对模式再次执行；新增检查若不是显式 `baseline_aware: false`，或缺少非空 `_note`，Verify 会在执行前报 ERROR，不属于本例外。`ignore_paths` 同样被冻结；旧基线缺少其快照时，必须先在配置维护模式重建基线。

- 生成只依据仓库证据（CI、项目清单、构建入口、测试与 Lint 配置、`AGENTS.md` / Spec / ADR），无证据不更新，无变化保持字节级不变。
- 至少包含一项试运行成功的编译（构建）或测试检查；仓库没有可安全执行的入口 → 返回 ERROR，不生成占位命令。
- 弱化类变更（删检查、降 `threshold`、关 `baseline_aware`、扩大测试排除）必须展示「旧值、新值、证据、理由」并经用户确认。
- 涉及真实 API / 生产资源 / 凭证的检查用项目已有 marker、分组排除，并在 `_note` 说明。

**证据清单、生成与刷新规则、试运行步骤、输出模板见 [reference/config-maintenance.md](reference/config-maintenance.md)，按其执行。** 审外部 PR / 不可信分支时不进入本模式（生成的命令会被试运行，见信任边界）。

## 执行规则

1. 改动所在 worktree 在实现和测试完成后运行，不等待 LLM Review。
2. 全过（exit 0）→ 允许 merge。
3. **exit 1**（代码问题：编译错 / 测试挂 / 新增违规）→ 回实现改代码重跑，有限轮次仍 FAIL → 标 `需人工` + 附输出。**不停其他并行 task**。
4. **exit 2**（门禁自身坏了：工具缺失 / 正则非法 / 基线损坏）→ 改代码没用，直接标 `需人工` 排查配置 / 环境。
5. 无 config → 只跑内置门禁，汇报「未做项目自定义机器验证」，并提示可运行 `/verify-config` 初始化。
6. `spec_drift` FAIL → 更新对应 Change、长期 Specs、Issues 或知识同步任务，或补 `--spec-drift-reason` 后重跑。

## 与 workflow-code-generation 集成

| 时机 | 动作 |
| --- | --- |
| 动代码前（Native Delivery／Fast-Path 兼容别名／Phase 0） | 有 config → `--save-baseline` 采基线（同时快照当时的 changed files 作为 S0） |
| Task 合并前、Native Delivery 或 Runtime 最终 Review 前 | 有 config → `--baseline <repo-root>/.agentic-framework/verify/baseline.json --diff-base <base_sha>`；无 config → `--diff-base <base_sha>`。Native Delivery 不传 `--run-dir`；完整 Runtime Run 必须传。SVN 模式 spec drift 读 `svn status`，`--diff-base` 省略。有不想提交的本地改动 → 追加 `--ignore <glob>`（或 config `ignore_paths`） |

> 下放执行在 worktree 内，基线须用**主仓库根绝对路径** `--baseline <repo-root>/.agentic-framework/verify/baseline.json`（worktree 看不到未提交的基线）。
>
> **基线读多写一、并发安全**：`--save-baseline` 只在动代码前单点写一次，并行 task 验证时一律**只读对比**、不改基线；report 默认写各自 worktree 的 `.agentic-framework/verify/report.json`（相对 cwd）。worktree 隔离是为了隔离代码改动，不是为了基线。

## 强制规则

| 规则 | 说明 |
| --- | --- |
| 客观优先 | 能机器判定的，不接受口头「应该没问题」 |
| 只追新增 | 基线下历史违规不阻塞，本次不得新增 |
| 文档同步 | 改代码但不改规格 / 任务 / ADR 时，必须写明无需更新原因 |
| 无侵入 | 无 config 时仅运行内置门禁，不跑项目自定义命令 |
| 不偷改 | 不得为过门删测试 / 放宽配置 |
| 写入受限 | 既有检查和 `ignore_paths` 在实现期冻结；只有已试运行、带非空 `_note` 的新入口可追加显式 `baseline_aware: false` 检查，验证失败后不得重采基线 |

## 信任边界

`command` 经 `shell=True` 执行，**仅自己信任的仓库自动跑**；审外部 PR / 不可信分支时先人工确认配置内容，不自动执行。
