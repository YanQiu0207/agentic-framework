# Matt Pocock Skills 的理念与框架适配研究

本文评估哪些工程方法适合吸收到本框架。结论：优先改进设计、拆解和反馈方法，保留现有 workflow 的执行与治理职责。下述适配均为候选建议，不是已经实现的框架合同。

## 研究基准

- 核查日期：2026-10-03。
- 上游仓库：[mattpocock/skills](https://github.com/mattpocock/skills)，核查提交 `d81f3a183412e71a5b1e84ca21bc1a35eea03a60`。
- 本仓库基准：`00355a9d26bdac2cdf27dfdced37854e18c4d617`，结合当前工作区文件读取。
- 方法：读取上游技能源码、作者文章、播客官方节目页；本地核对技能、脚本与知识文档。未安装或运行上游技能，未做效果对照实验。
- 上游采用 [MIT License](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/LICENSE)。复制或改编代码与技能文本时保留适用的版权及许可声明。

## 核心理念

作者把工程实践做成小而可修改、可组合的技能，强调人保留流程控制权。README 将常见失败归为意图不一致、语言不一致、缺少运行反馈、设计复杂度增长。它是一套工程工作方法；不能据此认定其效果已经通过本项目验证。[README](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/README.md)

几个可独立吸收的方法如下：

1. **按决策依赖追问。** 当前 grilling 每轮处理前提已明确的一组问题；事实由代理调查，取舍交给用户。作者承认这个 frontier 依赖模型判断，并非机器计算的图。[作者说明](https://www.aihero.dev/skills-grilling)
2. **设计深模块。** 用较小的接口承载较多行为，降低调用方需要理解的复杂度；接口还包括调用顺序、错误、不变量等约束。关注复杂度是否真正集中，而不是实现代码行数。[codebase-design 源码](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/codebase-design/SKILL.md)
3. **按纵向行为切任务。** 每个任务打通一条可验证的完整路径，并明确阻塞关系；大范围机械重构则允许扩展、分批迁移、收缩。[to-tickets 源码](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/to-tickets/SKILL.md)
4. **逐行为获得测试反馈。** 经公共接口验证行为，每轮一个失败测试和最小实现；避免先批量写完测试再批量实现，也避免断言复刻实现公式。[tdd 源码](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/tdd/SKILL.md)
5. **让指令产生可观察作用。** writing-for-agents 的 no-op 检验关注删除一条指令是否改变行为，不能把它简化为追求最短提示词。[作者说明](https://www.aihero.dev/skills-writing-for-agents)

版本细节：README 使用 red-green-refactor 概括 TDD，但核查版本的 tdd 技能明确把 refactor 放到 Review 阶段。不能用通用 TDD 印象覆盖源码。采用哪种重构节奏需本框架自行裁决。

## 如何使用

按上游 README，通用安装方式是：

```bash
npx skills@latest add mattpocock/skills
```

选择所需技能及宿主，并包含 `setup-matt-pocock-skills`。首次在项目中运行 `/setup-matt-pocock-skills`，配置工单系统、标签和文档位置。通常从 `grill-with-docs` 进入，形成共识后用 `to-spec` 整理规格，`to-tickets` 拆任务，再交给实现入口。它们可以分开使用，不要求每次完成整条链。[官方说明](https://www.aihero.dev/skills)

例如开发取消订单功能：先明确哪些订单可取消、付款和发货状态如何影响结果，再将首个任务定义为一条可验收的取消路径，随后补充其他行为。这个例子是本研究的说明，不是上游提供的领域设计。

当前会话可用目录已出现 `grilling`、`codebase-design`、`tdd` 等同名技能；这只证明它们在本会话可用，不证明安装来源、版本或已经纳入本仓库发行清单。

## 与当前框架的接点

以下现状来自当前文件；候选改动尚未实现。

| 借鉴项 | 已核查的框架现状 | 建议适配 |
| --- | --- | --- |
| 决策依赖追问 | `skills/workflow-requirements-clarification/SKILL.md` 已要求代理查事实、苏格拉底式提问；`workflow-system-design` 独立负责设计 | 提取共同的追问方法，保留需求与设计的职责边界；已有答案直接复用，避免增加重复确认 |
| 深模块与测试接口 | `skills/bp-component-design/SKILL.md` 已有最小接口、封装和设计原则 | 增加调用方认知成本、复杂度集中程度、从公共接口可验证性三个具体检查点 |
| 纵向切片 | `skills/workflow-code-generation/reference/task_planning_guide.md` 已有 DAG、独立验收、渐进编译和迁移策略 | 功能任务优先以可观察行为命名并携带测试；保留独立的最终集成验证，不强迫所有迁移都纵向切片 |
| 逐行为测试反馈 | `skills/workflow-test-generation/SKILL.md` 已有公共接口分析与 task 内嵌测试路径 | 将失败证据、最小实现、通过证据作为需要 TDD 的任务内循环；可复用已确认的设计测试边界 |
| 技能组合可靠性 | `scripts/lint_skill_graph.py` 校验引用存在及连通性，并明确不保证实际加载 | 结构检查之外，以执行轨迹验证依赖技能实际加载和行为是否发生 |
| 提示词精简 | 当前框架有独立的技能、参考文件和执行脚本 | 对重复指令做有无对照；确定性门禁规则不能仅凭字数删除 |

优先试点深模块、纵向切片与任务内测试循环：选一个有限功能，在相同任务和模型配置下比较原流程与改进流程，记录需求遗漏、回归缺陷、返工、人工轮次、Token 和时间。多次运行后再决定推广；单次成功不足以证明改进有效。这是研究建议，不是已经获得的效果数据。

## 不能直接照搬的部分

- 上游 [implement](https://github.com/mattpocock/skills/blob/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/implement/SKILL.md) 会调用 Review 并提交当前分支。作为本框架 task 的执行器直接使用，会与 Tooling 的统一最终 Review 和提交职责发生重叠；应复用内部方法，由现有 workflow 管理交付。
- 上游 to-tickets 的工单倾向不写具体路径；本地任务合同要求 `context_files`、`verification`、`artifacts` 等结构化字段。业务票据可以简洁，但不能用其替换本地可执行 tasks 合同。
- 上游 grilling 作者明确承认，文本中引用另一技能并不保证实际加载。其决策 frontier 也不能当作本地运行时 DAG、锁、恢复和失败隔离的替代物。[限制说明](https://www.aihero.dev/skills-grilling)
- 上游 tdd 要求事先与用户确认测试 seam。适配时应识别本地设计阶段已有的授权与测试计划，不能在无人值守 task 内重复强制等待。
- 领域词汇与 ADR 的方法可以采用，但知识继续通过 `openspec/index.md` 进入并由项目 Git 管理；研究候选不写入公共知识库。

## 访谈与演示

已由一手页面确认：[The Unhandled Exception Podcast EP.088 Agent Skills](https://unhandledexceptionpodcast.com/posts/0088-mattpocock/)，2026-07-31，主持 Dan Clarke。官方节目介绍列出 grill-me、wayfinder、战术编程、上下文窗口、个人软件等话题，并链接 OpenSpec。这里仅据节目说明概括，未核听完整音频，不提供逐字引述或时间戳。

另一个可能是 Andrew Warner 主持的 [Matt Pocock Built the Skills Repo Every AI Coder Is Using](https://www.youtube.com/watch?v=LMpMmOWTtVk)。已找到原始视频入口，但未获取可核对的一手完整字幕，因此不引用其具体发言或断言发布日期。

实操可看本人 [完整技能工作流演示](https://www.youtube.com/watch?v=M6mYodf0dJM)，该链接由上述官方播客节目页提供；这是教程，不是访谈。

## 本地知识与当前文件的冲突

发现既有复审轮数漂移，保留双方证据：

- 知识文档 `framework-unification.md:200`、`:399`、`:607`、`:681` 仍写最多两轮。
- 当前 `skills/workflow-code-review/SKILL.md:65` 写最多 10 轮；`skills/workflow-code-generation/SKILL.md:73` 同样引用 10 轮。
- 当前 `scripts/analyze_session_metrics.py:456` 定义 `MAX_REVIEW_RETRIES = 10`，其测试文件包含第 10 轮用例。这支持当前技能与遥测口径一致，不等于证明所有运行时门禁都强制该上限。

本次只记录冲突，不静默修改既有知识或规则；它不影响上述适配方向，但正式改造 Review 前需先裁决并同步。
