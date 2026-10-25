# Delta：决策依赖追问与领域建模适配候选

**状态**：Synced（适配已实施、验证并同步长期研究）
**动作**：MODIFIED
**长期目标**：`openspec/specs/backend/engineering/tech/external-reference-mattpocock-skills.md`

## 补充候选研究结论

- `/grill-me` 与 `/grill-with-docs` 是组合入口，实际能力来自 `grilling` 和 `domain-modeling`。引入需处理依赖链，不能只复制两个入口。
- 适配候选是两个薄命令与共享方法，工程侧继续由现有 workflow 管理需求、设计、实现及审批，不引入平行状态机。
- 决策依赖决定提问顺序，产物章节决定覆盖检查；需求与设计的阶段边界不变。提问节奏变化须经用户批准及行为评测。
- 领域模型包含术语、概念关系、规则与流程，保存在项目级长期 Specs，由多个 Change 共享；Agent 通过根索引定向读取，不依赖原会话或扫描历史 Change。
- 写入区分两类：既有知识澄清在证据与语义确认、明确写入授权后及时更新共享条目；未来业务变化先留 Change Delta，验证归档后同步。未决冲突或不明确分类不能覆盖共享模型，不另建 ADR 系统。
- 当前结论来自本地源码静态分析，未验证运行效果。本地资料包版本需单独固定，不能继承既有研究提交号。

## 同步条件

审核后按实际裁决更新候选结论；实施后补充采用版本、许可处理、行为评测证据和最终 Review 结果。没有实施证据的建议继续标记为候选。

长期文档已按实现与证据定向更新；最终验证及归档时按 `skills/project-knowledge/SKILL.md` 核对同步，不整篇覆盖。长期入口和路径未变化，不重复新增索引条目；机器和安装环境限制保留在 validation.md，不宣称已通过。

## 证据

- 当前 Change 的 `proposal.md` 第 1、4、5 节。
- 当前 Change 的 `design.md` 第 4、6、7、9 节。
- 上游本地英文 `grilling/SKILL.md:6–30` 与 `domain-modeling/SKILL.md:44–74`，完整路径见 `design.md` 第 9 节。
