---
name: workflow-verification
description: 机器验证。代码改动前采集基线，任务合并及最终 Review 前运行检查，或响应用户的验证请求。用户要求初始化、刷新验证配置（/verify-config）时进入配置维护模式。
---

> 输出一行：`Using workflow-verification`

# 机器验证

**运行项目检查，记录实际结果。** 有配置时比较改动前后的基线；无配置时执行内置检查，并说明验证范围。

## 两种模式

- **有 `verify.config.json`（大多数项目）** → 配置驱动，`scripts/verify.py` 跑 + 基线对比。
- **没有** → 只跑内置门禁；其余检查跳过，并提示用户可运行 `/verify-config` 初始化配置（见下方配置维护模式）。

## 交付路径与 Verify 产物

| 交付路径 | Verify 产物 | 交付用途 | 禁止事项 |
| --- | --- | --- | --- |
| Native Delivery | 独立 `.agentic-framework/verify/report.json`，不传 `--run-dir` | `check_delivery.py --native-delivery` 消费 PASS 的 v2 独立 Verify 与 integration Review。 | 不得伪造 `run_id`、Harness、Trust Gate 或 Run Artifact。 |
| 完整 Runtime Run | 传 `--run-dir <run-dir>` 生成 Run-bound Verify Artifact。 | 完整 Runtime 的 Manifest、Journal、Capability 与 Trust Gate 证据链。 | 不得以独立报告替代 Run-bound Artifact。 |
| Fast-Path 兼容别名 | 与 Native Delivery 相同的独立 v2 Verify 报告。 | 只服务尚未迁移的低风险调用；不构成独立默认路径。 | 不得声明 Runtime 证据。 |

独立 Verify 是 Native v2 报告（change 2048）：顶层 `schema_version: 2` 与 `subject_id`，检查前后核对同一内容主体，检查期间输入变化或覆盖不完整时结果无效（不产生 PASS）。旧 v1 报告只按旧合同展示历史，不能作为新完成证据；交付门会用 `--subject-base` 重算当前内容并交叉核对 Review/Verify/当前三方一致。

独立 Verify 只证明已执行的机器检查及其结果。`scope: run` Review 的交付必须走完整 Runtime Run（显式启用）；strict Review 在 Native 与 Runtime 均可交付，Verify 本身不能把无 Run 任务升级为 Trust Gate PASS。

## 内置 spec drift 检查

`verify.py` 始终检查代码改动与规格的关联。相关规格正文须引用改动代码路径；确实无需更新时，传 `--spec-drift-reason "<具体原因>"` 后重跑。

- 规格包括 Change 的 proposal、design、tasks、Delta，长期 Specs、Issues 和 ADR。
- Git 标准或委派流程在改动前记录 `base_sha`，后续显式传 `--diff-base <base_sha>`；已提交后的 clean 工作区也使用该基准。
- SVN 直接检查工作副本，省略 `--diff-base`；两种版本控制都无法识别时返回 ERROR。
- 最终报告引用 `.agentic-framework/verify/report.json` 中的 `spec_drift` 结果。

遇到规格关联失败、忽略路径、来源版本问题或使用 SVN 时，读取 [规格关联与交付范围](reference/spec-drift-and-scope.md)。新 Change 写入 `openspec/changes/`，旧设计目录只作迁移输入。

## Scoped Delivery 残留快照（显式模式）

Native Delivery 若需保留预存的无关改动，必须在改动前用 `--save-baseline --delivery-scope <路径>` 冻结交付范围并采集残留快照。采集前读取 [残留快照规则](reference/spec-drift-and-scope.md#scoped-delivery-残留快照显式模式)。

`--ignore` 只影响规格漂移归类；独立的残留快照用于检查交付范围和预存内容。完整 Runtime Run 仍使用干净工作区。

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

用户要求初始化、刷新配置或运行 `/verify-config` 时，先读取 [配置写入规则](reference/config-write-policy.md) 和 [配置维护步骤](reference/config-maintenance.md)，再执行：

检查仓库证据 → 生成或刷新 → 校验结构 → 试运行 → 确认弱化类变更 → 写入版本控制。

实现期间冻结既有检查、`ignore_paths` 和基线。本次实现产生新检查入口时，追加前先读取 [配置写入规则](reference/config-write-policy.md)，确认入口已独立试运行，并使用唯一 `name`、非空 `_note` 和显式 `baseline_aware: false`。追加后使用原基线验证。

涉及外部 PR 或不可信分支时，先按信任边界确认配置，不自动进入维护模式。

## 执行规则

1. 改动所在 worktree 在实现和测试完成后运行，不等待 LLM Review。
2. 全过（exit 0）→ 允许 merge。
3. **exit 1**（检查失败：编译、测试或新增违规）→ 回实现改代码重跑，有限轮次仍 FAIL → 标 `需人工` + 附输出。**不停其他并行 task**。
4. **exit 2**（验证工具出错：工具缺失、正则非法或基线损坏）→ 标 `需人工`，排查配置或环境。
5. 无 config → 只跑内置门禁，汇报「未做项目自定义机器验证」，并提示可运行 `/verify-config` 初始化。
6. `spec_drift` FAIL → 更新对应 Change（`proposal.md` / `design.md` / Delta / `tasks.md`，正文引用改动代码路径）、长期 Specs、Issues 或 ADR，或补 `--spec-drift-reason` 后重跑。

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
| 配置保护 | 不得为过门删测试 / 放宽配置 |
| 写入受限 | 既有检查和 `ignore_paths` 在实现期冻结；只有已试运行、带非空 `_note` 的新入口可追加显式 `baseline_aware: false` 检查，验证失败后不得重采基线 |

## 信任边界

`command` 经 `shell=True` 执行，**仅自己信任的仓库自动跑**；审外部 PR / 不可信分支时先人工确认配置内容，不自动执行。
