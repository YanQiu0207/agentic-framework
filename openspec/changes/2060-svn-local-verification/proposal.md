# Proposal: SVN 本地验证与本地目录排除（Quick Draft）

**日期**：2026-10-31
**状态**：Quick Draft
**批准**：用户已确认本地验证方向、排除目录及工单号 2060。

## 1. 问题与目标

`scripts/vcs.py` 的 SVN 内容主体捕获查询远程基准目录树和属性；`skills/workflow-verification/scripts/verify.py` 的知识来源检查也会查询远程 revision。本地 Verify 不应依赖这些远程读取。默认扫描未版本化的 `.codex/`、`.claude/` 又引入无关成本。

目标：本地 Verify 仅依赖 SVN 工作副本，默认跳过上述本地目录，并允许补充目录；保持已版本化文件、显式必需输入、删除节点及检查前后真实内容指纹的覆盖。

非目标：不遍历 SVN 历史，不调整全局超时，不取消正式提交后的远程验收，不跳过项目配置的构建、测试、静态检查。

### 验收标准

- SVN 内容主体及知识来源检查不使用 URL、远程目录树、数字 revision 查询；远程不可用时仍能完成本地验证。
- 未版本化的默认目录和配置目录在枚举时剪枝；目录内已版本化文件与显式必需输入仍影响指纹。
- Spec Drift 的未跟踪项采用同一目录规则，并记录忽略来源；已跟踪项及受保护规格不因本地目录规则被忽略。
- `verify.config.json` 的 `local_exclude_dirs` 为项目根相对目录列表，不支持通配符或越界路径；与默认排除取并集，配置和生效策略纳入指纹。
- Verify、Review、交付门调用共享的 `scripts/native_subject.py`，不能由报告自选排除规则。
- 本地知识来源仅作本地新鲜度核对，无法本地确认时明确告警，不再声称已证明远程 revision 存在。
- `vcs.verify_delivery` 的确切 revision 远程内容核验不变；Git 固定基准语义、混合修订及不完整覆盖失败关闭不退化。
- 定向回归、完整 Verify 和最终集成 Review 留存实际证据。

## 2. 设计方案

在现有 `scripts/vcs.py` 的 SVN 捕获逻辑增加本地模式，供 Native 主体使用；根据本地节点的 revision、schedule 构造基准路径并保留删除节点，拒绝与工作副本基准不一致的请求。公共历史 revision 查询及正式提交验收仍保留原语义。

`scripts/native_subject.py` 从实际配置读取 `local_exclude_dirs`，与默认 `.codex`、`.claude` 根相对路径合并；枚举未版本化目录时剪枝，并保留 tracked、固定基准及显式输入。配置非法时失败关闭。生效策略进入主体，旧报告不能自动沿用新指纹。

`skills/workflow-verification/scripts/verify.py` 的 SVN 知识来源检查改用工作副本本地修订范围和来源节点最后修订号；不证明远程 revision 的存在。目录策略只接入 Spec Drift 的未跟踪项，保留已跟踪项和规格保护；不将目录策略并入可能影响已跟踪项的 `ignore_paths`。

测试接点为真实临时 Git／SVN 仓库和现有捕获／Verify 接口；拦截外部命令拒绝远程调用，观察目录遍历及主体变化。保留现有远程正式验收回归，不用 Mock 代替全部集成证据。

## 3. 任务与知识影响

1. 实现共享本地捕获、目录排除、知识来源本地核对及回归测试。
2. 集成验证、同步配置指南和质量门合同、最终审查与交付。

长期知识更新 `openspec/specs/backend/framework/quality-gates/overview.md`；操作说明更新 `skills/workflow-verification/reference/config-guide.md` 和 `spec-drift-and-scope.md`。不修改跨项目公共知识库。

## 4. 风险与边界

本地有效文件仍需读取；本次不承诺任意大仓库都在 30 秒内完成。已版本化输入不因目录排除而被跳过。本地验证不等于远程提交验收。未对所有点目录作一刀切排除。
