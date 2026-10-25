# Change 2053 验证记录

## 范围与状态

- 执行形态：Native，未创建 Runtime Run；用户已授权实现、提交与推送。
- 框架基准：计划提交 `1d7fb1d8df649ff8d3ab8a0130df3ce300890779`，其上游为 `914a2f826039ddbef22fd676bdb60e83a5eb3b66`。
- 当前状态：实现、有限行为回归及定向语义复审通过；用户已解决符号链接权限，真实安装、编码补验及原配置全量机器验证通过。归档后对最终提交内容再绑定 Verify 与定向 Review，实际交付裁决以忽略目录中的机器产物为准，不伪造 Runtime 或全工作区干净声明。
- 主工作区有预存修改，未覆盖或清理。已冻结本 Change 范围并保存残留摘要；验证另使用干净 worktree `E:/github/aef-2053-verification`，基线对照使用 `E:/github/aef-2053-baseline`。这些路径是本机证据位置，不是可移植依赖。

## 来源与许可

本地阅读包 README 标注上游提交 `5beb35b040e3de97e54fa9e386d7e42d15c295c2`。英文原文哈希与 `translation-manifest.json` 对应条目核对一致：

| 方法原文 | SHA-256 |
| --- | --- |
| `grilling/SKILL.md` | `befdff1e27a1dfe2a294d5871169ac1afe16d983911daa4f32627514a48c1e15` |
| `domain-modeling/SKILL.md` | `7b925d7b1e341a2eeae33ad68a8a8c0ab889a38ddd22a7598e4c240e5a7556a3` |

两个新方法技能各保留一份上游 MIT LICENSE，随技能目录发行。未联网复核 Git 提交，不把本地资料一致性扩大为远程版本证明。

## 确定性检查

| 检查 | 实际结果 |
| --- | --- |
| 安装选择与受管清单新增测试，修改前 | 2 failed，重现技能与命令未进入安装和管理集合 |
| 主工作区新安装测试及原安装回归 | 34 passed，22 skipped |
| 干净候选 worktree 安装与技能图测试 | `python -m pytest scripts/test_interview_installation.py scripts/test_install_agentic_framework.py scripts/test_lint_skill_graph.py -q`：35 passed，22 skipped |
| 技能引用图 | `skills=29 commands=16 agents=8`，errors=0，warnings=0 |
| 任务依赖与 Change plan | `tasks=3`，errors=0，warnings=0；`PASS: plan (standard)` |
| 编码 | CP936 父进程启动 UTF-8 子进程，显式 UTF-8 解码，4 份中文技能与命令源文件及中文往返通过 |
| Python 语法与格式 | 新安装测试 py_compile、black（80 列）通过 |
| 带 SVN 的干净基准全量测试 | 1 failed，808 passed，24 skipped；唯一失败为符号链接夹具 WinError 1314 |
| 带 SVN 的干净候选全量测试 | 1 failed，810 passed，25 skipped；与基准相同失败，新增测试为 2 passed、1 skipped |
| 干净候选配置驱动 Verify | FAIL；spec drift、测试数（755 / 基线 752）、技能图通过，B-tests-pass 因相同权限失败；Native 主体完整，无嵌套仓库覆盖错误 |
| 权限解决后的真实安装与技能图回归 | 相同安装与技能图测试命令：57 passed，无 skipped |
| 权限解决后的安装路径编码补验 | CP936 父进程 → UTF-8 子进程，两个 Profile × 两个客户端共 16 项已安装技能／命令中文读取、8 项 LICENSE 读取通过；卸载不改源文件，6 份源资产哈希不变 |
| 权限解决后的全量 Verify | 原配置、原基线及 300 秒预算不变，B-tests-pass exit 0（295.8 秒），spec drift、测试数和技能图均通过，verdict PASS；原样报告为 permission-report.json |

前期 Windows 无符号链接权限（WinError 1314）时，真实安装测试确实跳过，没有用复制冒充链接。用户处理后，主会话新探测符号链接创建及读取通过；真实 install/reinstall/uninstall 和安装路径编码均已重新执行通过，历史 skipped 结果保留不覆盖。完整编码命令和输出位于主仓 `.agentic-framework/verify/2053/installed-encoding-check.txt`。

## 有限行为前向试验

使用独立子 Agent、`fork_turns=none`、继承父会话模型设置；未显式指定模型版本或采样参数，因而不宣称固定模型的可重复基准。只提供技能、最小隔离项目与用户请求，不提供设计结论或预期答案。原样请求、回复及实际加载路径保存在 [evidence/](evidence/)，夹具初始内容与实测变化路径见 [fixtures.json](evidence/fixtures.json)。

| 场景 | 观察结果 | 证据 |
| --- | --- | --- |
| 工程入口实际加载 | 读取命令、知识合同、两个共享方法及项目索引和领域条目 | `interview-transcript.md`、`model-write-transcript.md` |
| 独立问题与依赖问题 | 初版曾夹带「选择联系人后谁担任」的条件式下游问题；补充不夹带条件式追问后复跑，通知对象与跨客户开放同轮，联系人角色和额外审批后置 | `interview-transcript.md` 中初次与复跑回复 |
| 含糊同意 | 用户仅说「可以」后，Agent 要求逐项确认，没有将整轮批准 | `interview-transcript.md` |
| 上游决定变化 | 从不开放跨客户改为开放后，明确旧决定失效，重新检查管理员身份与订单所属客户授权，不直接沿用旧结论 | `interview-transcript.md` |
| 暂停与禁止副作用 | 暂停后只总结已确认与未决项，未改 model-a；用户另行授权的评测记录不属于业务写入 | `interview-transcript.md`、夹具核对 |
| 既有知识及时沉淀 | 明确授权后只更新共享 glossary 一行，记录来源、日期、上下文；未创建功能 Change、未覆盖未来部分取消 Delta | `model-write-transcript.md` |
| 跨 Change、新会话复用 | 新 Agent 从 model-b 根索引理解客户管理员、客户及订单归属，不依赖写入会话；指出没有代码时不能证明实现状态 | `cross-change-transcript.md` |
| 未来变化伪装为澄清 | 将部分取消称为既有澄清时，识别为行为变化，拒绝直接覆盖主本 | `cross-change-transcript.md` 第二轮 |
| 同名概念及并行 Delta 冲突 | 区分订购与财务客户；对照代码、共享规则与两个相反 Delta 展示证据，停止共享写入且未断言单函数代表全系统 | `conflict-transcript.md` |
| 通用非代码与近邻解释 | 读书活动只讨论目标和约束，不创建工程产物；只解释共享模型时没有强制完整访谈 | `generic-transcript.md`、`cross-change-transcript.md` |
| 正式设计缺失需求 | 实际加载系统设计与需求澄清 workflow，读取不完整 Proposal 后阻断正式设计，不给实现建议、不写业务文件 | `stage-missing-transcript.md` |
| 常规需求入口与已确认答案 | 初次仅复用 Proposal，缺少本会话模型读取；明确复用确认不能省略尚未读取的共享模型后复跑，实际加载知识合同及模型，仅澄清失败对象；不宣布需求完整、不提前问依赖参数、不给方案 | `stage-requirements-transcript.md`，初次与重新执行均保留 |
| 常规设计入口与建议边界 | 实际加载系统设计、追问方法、知识模型及架构规范；复用确认，针对用户既有思路质疑结果依据及职责，不替用户生成方案或写入 | `stage-design-candidate-transcript.md` |

主会话实际核对：model-a 的 7 个原文件未变化；model-b 仍为 7 个文件，仅 glossary 改变；model-c 保留原始文件及专属冲突夹具，未发生业务写入。

阶段回归夹具各为 9 个原文件，共享模型保持原样，均未创建 design.md 或其他业务文件；初始内容保存于 fixtures.json。

这些是有限合成场景，不是普遍效果或强隔离证明。另用两个独立新 Agent 在相同夹具、相同用户请求下分别加载原系统设计入口正文与当前入口，原样证据见 `stage-design-original-transcript.md` 和 `stage-design-candidate-transcript.md`。两者均复用确认、没有给方案：原入口提出 3 个职责问题，候选提出 2 个就绪问题并明确下游细节后置。该样本未证明候选更优；未测 Token、耗时、返工或统计提升。

对照边界：原入口正文由 `git show 1d7fb1d:skills/workflow-system-design/SKILL.md` 固定；共享参考与规范仍使用当前版本，故这是有限入口对照，不是两套完整框架的因果实验。原始请求保留用户输入排版，不以排版修订篡改证据；其余新增中文 Markdown 按 md-zh 自检。

## 全量验证与环境限制

主工作区配置驱动验证实际返回 ERROR：

- 全量 pytest：7 failed、791 passed、25 skipped、17 errors。
- spec drift 通过；测试数 759 不低于基线 756；技能图通过。
- Native 主体不完整：本地 `.claude/worktrees/`、上游资料仓库及 `resource_downloads/` 下嵌套仓库无法展开，不能产生完整验证声明。未修改忽略规则绕过。
- 干净候选 worktree 的 `scripts/test_vcs.py`：1 failed、29 passed、11 errors；失败与错误均在调用 `svnadmin create` 时 WinError 2。当前机器只有 TortoiseSVN GUI，没有 svn/svnadmin 命令行工具。
- MSI 行政提取命令被策略拦截，没有运行安装器。随后改用现有 7-Zip 静态解包，并只读 MSI File 表恢复发布文件名，没有执行 MSI 动作或修改系统配置。
- 工具来自 winget 源记录的 Slik.Subversion 1.14.2001，下载地址为 `https://github.com/AmpScm/SharpSvn/releases/download/SlikSVN-1.14.2/Slik-Subversion-1.14.2-x64.msi`，SHA-256 为 `9ae3bede58b78952d92e3f59725ccbbb7b7c575743dc6eb95ee47bfee3cfe5df`，本地校验通过。`svn` 与 `svnadmin` 实测均返回 `1.14.2-SlikSvn`，仅前置测试进程 PATH，未修改全局 PATH。
- 补齐 SVN 后，干净基准和候选都仅在 `scripts/test_native_subject.py::test_symlink_content_and_external_limitations` 失败，均为 WinError 1314。已请求用户提供符号链接能力；未改测试、配置或忽略规则消除该失败。
- 定向复审前的又一次 Verify 达到冻结的 300 秒超时，输出 ERROR；未放宽超时或重采基线。该失败保留在 `rereview-report.json`。
- 用户确认处理后已重新探测符号链接 PASS，57 项真实安装与技能图检查通过，当前继续使用原配置和原基线进行最终全量验证。权限问题不再列作当前阻塞，但旧失败不改写为通过。
- 随后原配置全量 Verify 已返回 PASS；历史失败、超时与最终通过分别保留，不删除失败证据。最终归档内容的报告保存于干净交付 worktree 的 `.agentic-framework/verify/2053/final-report.json`，Review 的最终轮次与交付 Verdict 独立保存于 `.agentic-framework/review/2053/` 和 `.agentic-framework/native-delivery/`。

主工作区报告：`.agentic-framework/verify/2053/implementation-report.json`；候选工作树报告：`.agentic-framework/verify/2053/candidate-report.json`。主仓诊断目录另保存 `clean-vcs-diagnostic.txt`、`clean-baseline-pytest.txt`、`clean-baseline-with-svn.txt` 和 `clean-candidate-with-svn.txt`。这些是未通过及诊断证据，不是交付通过证据。

## 独立 Review

首审为 standard / integration / round 0，报告位于主仓 `.agentic-framework/review/2053/review-round-0.md` 与原样 JSON；结论 NEEDS_CHANGES，P0=0、P1=1、P2=1。F-1 的正式阶段回归已补原样轨迹，F-2 的研究状态歧义已最小修正。定向 round 1 由同一 Reviewer 裁决 PASS，两个问题均已修复、无新增 finding，原样 Markdown 与 JSON 保存在同目录 `review-round-1.*`。未重启全量首审；最终归档内容变化仍须绑定当前机器报告并定向核对，Review 结果不替代机器验证。

## 知识影响与最终核对

- 架构决策：命中，采用共享方法与项目级模型，不新增访谈状态机；记录于 design.md §4.1～4.3 及长期知识 Delta。
- 放弃方案：命中，不原样安装整套上游、不新建根目录术语表或平行 ADR 系统；记录于 design.md §5。
- 新增约束：命中，先读模型、双轨写入、授权分离与不夹带下游问题；规则维护在对应技能，长期知识同步保留唯一操作来源。
- 研究与知识管理长期文档已按本次实现定向更新，未生成本框架业务领域占位文件；三项任务经真实 PASS 报告通过质量与本地集成事件，状态一致性检查为零错误，再进行归档。
