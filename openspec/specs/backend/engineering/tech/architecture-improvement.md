# 深模块与存量架构改善

## 定位与事实来源

框架以既有设计、测试与交付流程承载架构改善，不建立平行生命周期。方法唯一来源为 `skills/bp-component-design/reference/deep-modules.md`；当前执行合同以对应 Skill、安装器和测试为准。

source_ref: change-2054

source_paths:
- `skills/bp-component-design/SKILL.md`
- `skills/bp-component-design/reference/deep-modules.md`
- `skills/workflow-system-design/SKILL.md`
- `skills/workflow-quick-design/SKILL.md`
- `skills/workflow-test-generation/SKILL.md`
- `skills/workflow-architecture-improvement/SKILL.md`
- `commands/architecture-improvement.md`
- `scripts/install_agentic_framework.py`
- `scripts/test_architecture_improvement_installation.py`

## 使用方式

- 新增或重组模块：设计流程加载组件设计方法，分析调用方认知成本、局部性、删除检验与接口可验证性；不按行数或文件数量判定质量。
- 测试计划：记录负责行为的模块、验证接口和需替换的依赖；已有适用批准直接复用。范围变化与契约冲突不能被旧批准覆盖，内嵌任务向编排方报告而非等待重复审批。
- 存量体检：调用 `/architecture-improvement`。用户痛点优先，否则从版本历史识别热点；无历史且无范围时先圈定范围。报告有证据的候选，允许无候选。
- 用户选择后只讨论；明确要求实施后才交回代码生成路由，沿用原有设计、任务批准与最终 Review。

## 维护决策

- 方法归入组件设计并由设计、测试和 Review 复用，不另建架构规范 Skill。
- 调查默认不写文件或更新知识；不因扫描建议自动创建 Change、重构、提交或增加 Runtime。
- 两个 Profile 共用新入口，不新建 Pack；新增安装资产后由用户按既有机制刷新，不在开发中自动刷新真实项目。
- 首版不提供 HTML 报告或 CDN；Markdown／Mermaid 足以表达候选前后结构。
- 不复刻上游根目录术语表、ADR 目录或自动写入方式；继续使用 `project-knowledge` 的唯一位置与授权规则。

## 证据边界

安装与结构测试不证明架构建议质量。行为案例位于 `skills/workflow-architecture-improvement/evaluation/trigger-cases.md`；独立演练结果记录于对应 Change。没有跨模型、多次对照实验，不宣称降低缺陷率或维护成本的实证效果。
