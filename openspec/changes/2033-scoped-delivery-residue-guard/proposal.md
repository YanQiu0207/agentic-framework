# Proposal: Scoped Delivery 遗留工作区防护（Quick Draft）

**作者**：主会话
**日期**：2026-07-26
**变更**：scoped-delivery-residue-guard
**工单号**：2033
**状态**：Quick Draft

---

## 1. 问题与目标

### 问题

现有交付门把 Git `status --porcelain` 为空作为唯一工作区条件；而 Verify 基线只把采集时已有的变更路径 S0 从 `spec_drift` 归类中排除。两者没有共同的完整性合同：合法的预存残留会阻止交付，但基线快照也不能证明残留在执行期间未变化。

### 目标

- 提供显式启用的 Scoped Delivery：允许预存残留存在，但只在「本次交付范围干净，预存残留未变化」可验证时放行。
- 采基线时记录 Git 或 SVN 的遗留工作区快照 S0，包含状态、路径与内容指纹；交付时重算 S1 并要求一致。
- 在采基线前冻结本次允许修改路径与生成目录；S0 与该写入范围重叠或无法判定时失败关闭，提示切换干净 worktree 或工作副本。
- Git 校验从 `base_sha` 到声明提交的 Diff 均属于冻结范围；SVN 仅接受明确提供的提交 revision，并校验该 revision 的 Diff 属于冻结范围。
- 保持 `--ignore`、`ignore_paths`、`changed_files_snapshot` 只用于 `spec_drift`，不得成为 Scoped Delivery 的豁免来源。

### 非目标

- 不为未知构建或测试命令推断读取范围；只检查任务允许修改路径与声明的生成输出目录。
- 不把 Scoped Delivery 等同于完整 Runtime、Trust Gate 或独立严格评审。
- 不允许未提交的 SVN 本地改动声明 Scoped Delivery；缺少提交 revision 时应失败关闭。
- 不修改现有绝对干净交付路径；Scoped Delivery 必须显式选择。

### 验收标准

- Git 与 SVN 都能采集版本化残留和未跟踪文件／目录的 S0 内容快照。
- S0 与冻结写入范围重叠、状态不可解析或快照无法读取时，基线采集失败且不覆盖已有基线。
- Git Scoped Delivery 仅在声明提交从 `base_sha` 的 Diff 全部位于范围内，且 S1 与 S0 内容和状态完全一致时通过。
- SVN Scoped Delivery 仅在提供提交 revision、该 revision Diff 位于范围内，且 S1 与 S0 内容和状态完全一致时通过。
- S1 中新增、删除、改写或状态变化的预存残留均失败；报告列出差异。
- 默认交付门仍要求绝对干净；Scoped Delivery 成功输出只可表述为「本次交付范围干净，预存残留未变化」。
- `--ignore`、基线的 `changed_files_snapshot` 不影响 Scoped Delivery 判定。
- 新增 Git、SVN、快照变化、范围冲突、缺少 SVN revision 与报告措辞的自动化测试。

## 2. 设计方案

### 2.1 整体方案

将 Scoped Delivery 实现为独立且显式的交付模式。Verify 在 `--save-baseline` 时，接收已冻结的范围声明，写入独立的 `workspace_residue_snapshot`；`check_delivery.py --scoped-delivery` 读取该快照、复算当前状态，并按 VCS 执行提交范围校验。默认模式继续使用绝对干净检查。

### 2.2 核心组件

| 组件 | 职责 |
| --- | --- |
| `verify.py` | 校验范围声明，采集 S0 残留状态与内容指纹，拒绝范围重叠并原子写入基线。 |
| `workspace_residue_snapshot` | 记录 VCS、基准、冻结范围、S0 条目和规范化摘要；与 `spec_drift` 的路径快照语义隔离。 |
| `check_delivery.py` | 新增 Scoped Delivery CLI，校验 Git commit 或 SVN revision 的 Diff、比较 S0/S1，并输出受限结论。 |
| VCS 适配层 | Git 区分暂存区与工作树变更；SVN 读取 `svn status` 与 revision Diff；未跟踪目录按稳定文件树摘要。 |

### 2.3 主要接口

- Verify：新增显式范围声明输入与 Scoped S0 写入；不得由 `--ignore` 或 `ignore_paths` 推导范围。
- Delivery：新增 `--scoped-delivery`、S0 基线路径及 Git commit／SVN revision 证据输入；与普通绝对干净模式互斥。
- 报告：Scoped 成功输出固定措辞「本次交付范围干净，预存残留未变化」，并列出 VCS、范围摘要与 S0/S1 比较结果。

### 2.4 数据模型

S0 条目至少包含路径、VCS 状态、内容指纹和条目类型。已跟踪 Git 文件分别记录暂存区与工作树的 Diff 指纹；未跟踪文件和目录使用按相对路径、类型与内容摘要排序的树指纹。快照还绑定 `base_sha`（Git）或基准 revision（SVN）、冻结范围与摘要。

### 2.5 关键权衡

1. 选择显式 Scoped 模式，而非自动从 dirty 工作区推断，避免放宽既有默认门。
2. 选择内容和状态比较，而非仅路径比较，防止预存残留在执行中被改写。
3. 将测试「扫描范围」缩小为可声明的写入和生成输出范围；通用静态读取范围推断不可靠。
4. SVN 没有 Git 本地提交等价物，因此 Scoped Delivery 要求可查询的提交 revision；无法提供时切换干净工作副本。
5. Scope 与 `spec_drift` ignore 分离，防止质量检查的归类规则绕过交付完整性。

## 3. 知识影响

- 更新 `workflow-verification` 与 `workflow-code-generation` 的交付和基线契约。
- 更新长期质量门与 Native Delivery 边界 Spec。
- 不修改跨项目公共知识库。

## 4. 运维

- 默认仍使用绝对干净交付；仅存量残留且已冻结范围的任务显式启用 Scoped Delivery。
- Scoped 检查失败时保留快照和工作区，报告冲突路径，不删除或重写任何预存残留。

## 5. 参考资料

- `skills/workflow-verification/scripts/verify.py`
- `skills/workflow-verification/SKILL.md`
- `skills/workflow-code-generation/scripts/check_delivery.py`
- `scripts/test_check_delivery.py`
- `openspec/specs/backend/framework/quality-gates/overview.md`
- `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md`
