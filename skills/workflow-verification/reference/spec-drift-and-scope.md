# 规格关联与交付范围

处理 spec drift 失败、忽略路径、知识源新鲜度或 SVN 时读取相应章节；使用 Scoped Delivery 前读取残留快照规则。

## 内置 spec drift 检查

`verify.py` 总会检查本次改动文件列表，VCS 由 `verify.py` 自动探测：

- Git 工作副本 → `git diff --name-only <base>` + `git ls-files --others`。
- SVN 工作副本 → `svn status`（`A/M/D` 计为已纳入改动，`?` 计为未跟踪，`I` 跳过）。纯 SVN 模式按规则「只 `svn add`、不 `svn commit`」，一个 Change 期间无提交，工作副本本地改动即「本次改动」的全部，`--diff-base` 在 SVN 下不使用。
- 两端都探测不到 → spec drift 判 error，提示不在 Git 仓库或 SVN 工作副本内。
- **规格类文件判定**：活跃 Change 的 `proposal.md` / `design.md` / `spec.md` / `ui-spec.md` / `tasks.md` 与 `openspec/changes/` 下其余 `.md`（Delta 等）、长期 `openspec/specs|issues/` 下 `.md`、ADR 目录下 `.md`。

- 改了代码文件，且无法证明相关活跃 Change（`proposal.md` / `design.md` / `ui-spec.md` / `tasks.md` / `specs/` 下 Delta）或长期 `openspec/specs/`、`openspec/issues/`、ADR 已按知识影响更新 → FAIL。
- 相关性只做机械判定：规格类文件（含 ADR）正文出现改动代码路径；判不出相关时必须传 `--spec-drift-reason "<原因>"`。旧 `docs/design-docs/` 只作为迁移输入，不作为新改动的规格写入目标。
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
- **安全护栏**：`openspec/` 下的 `proposal.md` / `design.md` / `spec.md` / `ui-spec.md` / `tasks.md` / ADR 永不可忽略——忽略它们会让 spec drift 被静默绕过；命中忽略但仍属规格类的文件记入 report 的 `refused_ignores` 并照常归类。
- **审计**：被忽略文件写入 report 的 `spec_drift.value.ignored_files`，供 Review 核查。
- **硬约束**：`--ignore` 只作用于 spec drift 归类；build / test / lint 仍编译运行工作树全部文件，`M` 半成品仍需物理隔离（patch 往返 / 第二工作副本）。

示例：

```bash
python <skill-dir>/scripts/verify.py \
  --spec-drift-reason "仅修复脚本输出编码，不改变需求、任务拆解或架构决策"
```

## Scoped Delivery 残留快照（显式模式）

默认交付仍要求工作区绝对干净。只有存量工作区存在与本次任务无关、且可保持不变的残留时，才可在采基线时显式传入重复的 `--delivery-scope <路径>`：

- Verify 把冻结范围、Git／SVN 状态及残留内容指纹写入基线的 `workspace_residue_snapshot`。它与 `changed_files_snapshot` 完全独立；后者以及 `--ignore`／`ignore_paths` **仍只作用于 spec drift**。框架自身的 `.agentic-framework/` 本地运行产物不作为 SVN 残留，以避免基线和 Verdict 反向污染 S1。
- S0 残留与冻结的任务写入路径或生成目录重叠、状态不可解析、路径无法读取或树摘要失败时，采基线失败关闭且不覆盖既有基线。应切换干净 worktree 或工作副本，不得扩大 ignore 绕过。
- Git 交付必须提供等于当前 `HEAD` 的交付 commit；SVN 交付必须提供已提交 revision。`check_delivery.py --scoped-delivery` 仅在提交 Diff 均落入冻结范围且 S1 与 S0 完全一致时通过。
- 成功只能表述为「本次交付范围干净，预存残留未变化」，不得表述为「Git 工作区干净」。完整 Runtime Run 不使用此模式，仍应使用干净 worktree。
