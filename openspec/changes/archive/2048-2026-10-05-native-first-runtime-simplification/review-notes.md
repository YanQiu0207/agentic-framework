# 方案文档审查记录

日期：2026-10-04。审核方：agmsg 团队 `agentic-framework` 的 `reviewer-1`；修订方：`codex-1`。范围为 proposal、design 与知识入口，仅审查方案，不代表代码已实现或用户已批准实施。

## 首轮意见与处理

| 意见 | 判断与处理 |
| --- | --- |
| P1-1：新独立性字段与旧白名单/禁止集的关系未明确 | 合理。核对 `check_delivery.py` 后，在 design §4.2.2 明确按类型、版本和档位分派；只开放 v2 strict Review 指定字段，保留 v1 与 Verify 结果禁止集，不全局豁免。 |
| P1-2：subject 的产物位置及交叉核验责任缺失 | 合理。在 §4.2.3 明确三份 v2 产物的顶层必填字段、生成方及交付门重算和相等检查，补充反例测试。 |
| P2-1：SVN 两种结果在旧 Verdict 中不可表达 | 合理。在 §4.3.2 明确 v2 结果枚举、必填证据和正式交付判定；内容改变后不能直接沿用提交前报告。 |
| P2-2：项目强制策略缺载体说明 | 合理。在 §4.2.1 明确由编排方读取已有约束，通过显式 audit_required 输入传递；不从 Profile 名称推断，不新增配置体系，不自动覆盖强制策略。 |
| P2-3：回归计划遗漏路由 fixture 与降级等价测试 | 合理。§7.1、§7.2 加入现有两份测试文件，保留 Runtime 保护场景。 |
| P2-4 / P3-1：Native strict、纯 SVN 初始化的现状描述不够准确 | 合理。proposal §1.2 与 design §4.2.2、§4.3.3 区分现有 Production strict 和纯 SVN 初始化能力，限定本次新增/调整范围。 |
| 建议：内容依赖识别可能过重 | 采纳保守覆盖建议。§4.2.3 使用项目工作区与明确排除项，不建设测试依赖推导系统；无法覆盖的输入明确报告。 |

## 复审

第 1 轮定向复审：**PASS**。reviewer-1 于 `2026-10-03T17:17:27Z` 通过 agmsg 返回结论：上述问题均已解决，修订未引入新的不自洽，处理记录完整。该结论仅覆盖文档，不代表用户已批准实施。

非阻塞提醒：P1 冻结实施清单时明确 Verdict 生成入口与写出位置。建议合理，保留为实施检查项；但“check_delivery 从纯校验器新增生成职责”的前提不准确：现有 `check_delivery.py` 已有 `write_native_delivery_verdict`（549 行），并在 896–903 行构建、写出 v1 Verdict。实施应沿用并升级现有入口与路径约束，不另建生成流程。

验证：proposal 的 `lint_spec --phase code` 与 design 的 `lint_spec --phase design-code` 均为 errors=0、warnings=0；本轮仅文档修改，未运行代码测试。消息定时器在收到复审结果后自动停止。

## 知识影响

- 高影响架构决策：命中，修订仅记录在本 Change 的 design.md，仍为 Draft。
- 放弃重要方案：沿用 design.md §5，本轮未新增长期决策。
- 新增红线约束：命中，v1 保护与 v2 证据要求记录在 design.md，尚未成为当前规则。
- 已验证故障根因：未命中，本轮为方案审查。
- 跨项目知识候选：未命中。
- 普通变更：本轮仅修改方案文档，不改长期事实、代码或安装配置。


## 实施期间记录（Task 11–17，reviewer-1）

- Task 11–16 每任务：定向测试 + 全量 `pytest scripts -q`（冻结 300s 内，最终 285.3s / 740 passed / count 697≥574）+ 全局 Verify（冻结基线 00355a9）PASS + 提交树主体 MATCH + 控制器状态机归档。证据：`.agentic-framework/verify/2048-task{11..16}-final.json`。
- 过程修复（如实）：Task 12 修正 `_svn_verify` 未版本化残留混入版本内容比对（Task 14 集成测试发现）；Task 14 集成测试自 scripts/ 迁至 skill 目录（冻结 300s 预算临界，先例 test_verify.py，场景零删减）；Task 16 readlink 前缀加固（P0 同类，主仓库旧树复现）。
- 一次 shell cwd 漂移导致主仓库测试误跑与两行误改，已还原并对照会话起点快照核验；无用户内容损失。
- 最终独立 strict 集成 Review（五维 + 独立 Judge，均未参与实现）：见下方终审记录与 `.agentic-framework/verify/2048-task17-delivery.txt`。
