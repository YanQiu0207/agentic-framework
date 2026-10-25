# Proposal：深模块与存量架构改善（Quick Draft）

**日期**：2026-10-25
**变更**：2054-deep-module-architecture
**状态**：Quick Draft
**批准依据**：用户确认使用 2054 及四项任务拆分。

## 1. 问题与目标

已有设计规范强调最小接口与封装，但缺少深模块判断法、测试接点选择规则及存量架构改善入口。

目标：补齐上述方法，复用现有设计、测试、知识与交付流程。

非目标：不自动重构，不增加 Runtime 或审批门，不引入平行术语表及 ADR 目录，不复制主工作区尚未提交的 Change 2053 实现。

验收标准：

1. 深模块方法覆盖认知成本、局部性、删除检验、接口测试，并能区分透传层、碎片化和 God Class。
2. 设计与测试复用已批准接点；新需求或契约冲突不能伪装成已有批准。
3. `/architecture-improvement` 只调查并呈现候选；用户选择不等于批准重构，允许无候选。
4. 两个 Profile 均可安装、刷新和卸载新入口；测试不依赖主工作区未合并改动。
5. 结构检查、安装回归与隔离行为演练完成；如有环境限制如实记录。

## 2. 设计方案

### 2.1 整体方案

- 在 `skills/bp-component-design/reference/deep-modules.md` 维护唯一方法源，由组件设计入口引用。
- 在 `skills/workflow-system-design/SKILL.md` 与 `skills/workflow-test-generation/SKILL.md` 接入模块责任、测试接点及授权复用；Quick Design 涉及接口时使用相同方法。
- 新建 `skills/workflow-architecture-improvement/SKILL.md` 和 `commands/architecture-improvement.md`，读项目知识及热点，报告证据、前后结构、收益、风险与不确定性，选中后回到现有流程。
- 在 `scripts/install_agentic_framework.py` 的交付与受管清单登记，不改变安装权限、安全校验及 Registry 语义。

### 2.2 关键权衡

复用组件设计而非新增平行设计规范；报告默认在对话中使用 Markdown 和 Mermaid，不增加 HTML、CDN 或自动写入。调查阶段只读，不把架构偏好变成 Review 阻塞项。方法独立表述，不复制上游文本。

## 3. 知识影响

新增长期说明 `openspec/specs/backend/engineering/tech/architecture-improvement.md`，由 `openspec/index.md` 接线。既有外部研究只作历史候选，不重写无关结论。

## 4. 验证与交付

Native Delivery，串行任务，一次 standard integration Review。使用现有 `verify.config.json`，不修改检查或基线。Windows 检查命令依赖 Git `usr/bin` 的 `grep` 和 `true`，仅为当前进程补充 PATH。行为演练与结构检查分别报告，前者不冒充确定性保证。

恢复阶段的配置维护例外：2026-10-25 用户明确批准仅将 `verify.config.json` 中全量测试的 `timeout_seconds` 从 300 改为 600。依据为原 Verify 的 300 秒超时与独立全量测试 836 项通过；不改测试范围、断言、其他检查或原基线。该修改与验证收口一并定向复审，不重新启动全量首审。

## 5. 参考资料

- 本次对话批准的三项补充方案与四项任务。
- `.learn-by-gpt/mattpocock-skills/zh-CN/skills/engineering/codebase-design/SKILL.md`。
- `.learn-by-gpt/mattpocock-skills/zh-CN/skills/engineering/improve-codebase-architecture/SKILL.md`。
