# Proposal: 为 verify.py 的 spec drift 增加文件忽略能力（Quick Draft）

**作者**：主会话
**日期**：2026-07-22
**变更**：add-verify-ignore
**工单号**：2
**状态**：Quick Draft

---

## 1. 问题与目标

### 问题

`workflow-verification` 的 `verify.py` 在判定 spec drift 时，把工作副本的全部本地改动当作「本次 change」：SVN 模式读 `svn status` 的 `A/D/M/R/C` 与 `?`，Git 模式读 `git diff --name-only <base>` 加 `git ls-files --others`（未跟踪文件也算）。

当工作目录长期挂着**不想提交**的本地改动（公司 SVN 项目常见：本地调试脚本、本地配置、对已跟踪文件的临时修改）时，这些改动被误卷入 spec drift 判定，即便与当前 change 无关也会触发 FAIL，并可能被 build/test 误编译。

根本原因：verify.py 无法区分「本次 change 的改动」与「不想提交的其他本地改动」。SVN 缺乏 stash/worktree 式的轻量隔离，框架在 SVN 模式下也未提供工作副本隔离，需在 verify.py 层面增加「按指定路径忽略」的能力。

现状关键点（行号见参考资料）：`_changed_files` 无过滤参数；`evaluate_spec_drift` 合并 tracked + untracked 算 code_files；`cmd_save_baseline` 不记录当时改动文件；`_config_snapshot` 只覆盖 `config.checks[]` 不覆盖内置 spec drift；CLI 无忽略参数。

### 目标

- 按指定路径（文件/目录，glob 匹配）忽略文件，被忽略文件不进入 spec drift 的 `code_files` / `spec_files` 归类。
- 提供三种指定忽略的方式：命令行参数、配置文件字段、基线时刻改动文件快照差集。
- 保持可审计：被忽略文件写入验证报告。

### 非目标

- 不解决 build/test 对已跟踪 `M` 半成品的物理编译——半成品仍会让 build 挂，需 patch 往返或第二工作副本等物理隔离。
- 不修改 `validate_change.py`（它不读工作目录改动，无此问题）。
- 忽略只作用于 spec drift 归类，不关闭、不弱化任何 check。
- 不为 SVN 增加工作副本隔离机制。

### 验收标准

- 给定忽略路径时，spec drift 不再把这些文件算入 `code_files` / `spec_files`。
- 三种指定渠道（命令行、配置、基线快照差集）各自可用且可叠加。
- glob 匹配支持 `*`、`?`、`**`（跨目录）。
- 尝试忽略 `openspec/` 下 spec/tasks 文件时被拒绝并明确提示。
- 被忽略文件出现在验证报告的 spec drift 字段。
- 现有 `test_verify.py` 测试不回归，新增覆盖忽略能力的测试。
- 基线快照差集：S0 不得在验证失败后通过重采基线被篡改。

## 2. 设计方案

### 2.1 整体方案

在 verify.py 的 spec drift 判定路径插入一层「忽略过滤」：合并三个来源的忽略集（命令行 `--ignore`、config `ignore_paths`、baseline 的 S0 快照），用 glob 从 changed files 中剔除被忽略项，再算 `code_files` / `spec_files`。忽略**只作用于 spec drift 归类**，不触碰任何 check 的执行。被忽略文件写入 report 供审计。

### 2.2 核心组件

| 位置 | 改动 |
|------|------|
| 新增 `_collect_ignores(cli_patterns, config_paths, baseline_s0)` | 合并三来源忽略集 |
| 新增 `_glob_match(path, patterns)` | glob 匹配（`fnmatch` + 手动 `**`） |
| `evaluate_spec_drift`（`:457-515`） | changed files 算出后过滤、记 `ignored_files`、禁忽略 spec/tasks 护栏 |
| `cmd_save_baseline`（`:1103-1137`） | 多存 `changed_files_snapshot`（= S0） |
| `cmd_verify`（`:1188-1264`） | 读 baseline S0，与 config + CLI 合并后传给 spec drift |
| config schema（`_validate_config` / `load_config`） | 加 `ignore_paths` 字段（list），**不纳入** `_config_snapshot` |
| CLI（`main:1389-1410`） | 加 `--ignore`（可重复） |

### 2.3 主要接口或 API

- CLI：新增 `--ignore <glob>`，可重复；与既有 `--spec-drift-reason` 正交。
- config：`verify.config.json` 新增顶层 `ignore_paths: ["pattern1", "dir/**"]`，可选。
- baseline：新增 `changed_files_snapshot: [...]` 字段（采基线时的 changed files 列表）。
- report：`spec_drift.value` 新增 `ignored_files: [...]` 与 `ignore_sources`（标注 cli / config / baseline）。

### 2.4 数据模型

忽略集合并语义：`ignored = set(cli --ignore) ∪ set(config ignore_paths) ∪ set(baseline S0)`；对每个 changed file，若被忽略集中任一 pattern 命中（glob）则剔除出 code_files/spec_files，并加入 `ignored_files`。`openspec/` 下 spec/tasks 文件（`_is_spec_file` 命中）即便命中忽略 pattern 也拒绝剔除，并在 report 标注「拒绝忽略」。

### 2.5 关键权衡

1. **glob 选 `fnmatch` + 手动 `**`**，不用 `pathlib.PurePath.match`——后者 `**` 需 Python 3.13，verify.py 要广泛兼容。
2. **`ignore_paths` 不纳入 `config_snapshot`**：它只影响内置 spec drift，而 spec drift 不在 `config.checks[]` 覆盖范围；纳入会让「改忽略触发 rebaseline」错位保护 build/test 基线，保护对象与被保护对象不匹配。
3. **三来源取并集**，不冲突可叠加；S0 是「动代码前已存在的本地改动」，CLI/config 是「显式声明忽略」。
4. **安全护栏**：禁忽略 `openspec/` spec/tasks；只过滤归类不关 check；审计写 report；S0 受既有「不得验证后重采基线」保护。
5. **硬约束不变**：`--ignore` 救不了 build/test 对 `M` 半成品的物理编译。

## 3. 知识影响

命中：

- `workflow-verification` 的 spec drift 契约（SKILL.md 第 17-30 行）：补忽略机制说明。
- `verify.py` 的 CLI 参数表、baseline schema、config schema：新增 `--ignore`、baseline 改动文件快照字段、config `ignore_paths`。
- 长期 specs：`openspec/specs/backend/framework/quality-gates/` 下与 verification 相关章节（实现完成后同步）。

不修改跨项目公共知识库。

## 4. 参考资料

- `skills/workflow-verification/scripts/verify.py`：`_changed_files:407-422`、`_svn_status_changes:371-404`、`evaluate_spec_drift:457-515`、`_related_spec_files:518-545`、`_is_code_file:425-435`、`_is_spec_file:438-454`、`cmd_save_baseline:1103-1137`、`cmd_verify:1188-1264`、`_check_fingerprint:781-791`、`_config_snapshot:794-806`、CLI argparse `:1389-1410`。
- `skills/workflow-verification/SKILL.md`：spec drift 章节、与 workflow-code-generation 集成表。
- `skills/workflow-verification/scripts/test_verify.py`：现有测试。
- `openspec/changes/1-enforce-ticketed-change-naming/proposal.md`：工单号命名规范。
- 前序对话（本会话）：需求与方案的逐轮澄清。
