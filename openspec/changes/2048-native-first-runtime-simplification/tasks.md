# 实施任务清单

> 由 proposal.md / design.md / review-notes.md 生成
> 任务总数：17
> 状态：执行中；隔离 Worktree 内本文件是执行状态来源，主工作区副本在集成时同步。
> 核心原则：先建合同与公共接口，再迁移消费者和路由，最后补齐 SVN、回归与交付；P1/P2 同批发布。

用户已通过“开始处理”授权执行本清单。设计的文档复审 PASS 不等于代码 Review PASS。执行期间冻结既有 Verify 配置和基线；规则随对应任务的实现与验证同步更新。

## 依赖关系总览

```text
P0   Task 1：回归与基线
               ├── Task 2：Native v2 合同 ──┐
               └── Task 3：Git VCS 接口 ────┤  2、3 文件不重叠，可并行
P1                                         ↓
          Task 4：内容标识 → Task 5：Verify → Task 6：Review/交付门
P2                                         ↓
          Task 7：显式路由 → Task 8：恢复 → Task 9：核心 Skill
P3                                         ↓
          Task 10：SVN Adapter → Task 11：Verify/残留 → Task 12：SVN 交付
                                         → Task 13：SVN 工作流/初始化
P4                                         ↓
          Task 14：集成回归 → Task 15：文档/知识 → Task 16：安装/真实任务
                                         → Task 17：最终验证、审查与交付
```

实现与本任务的关键路径测试同批交付；Task 14 补跨模块验证，不替代前序任务测试。Task 2–9 可逐步合入内部开发分支，但 P1/P2 不拆开发布；Task 10–13 的 SVN 能力另作完整发布批次，不等待 SVN Runtime。

## 变更影响概览

### 文件变更清单

以下为任务冻结的预期修改面。新增文件名是本计划选择的组织方式；执行前确认调用和安装关系。发现必要新增路径时，先更新对应任务和依赖，再修改，不以此扩展到 Runtime 全量重构。

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/test_workflow_control.py`、`scripts/test_check_delivery.py` | 修改 | 1、5–8、12、14 | 路由、状态、报告与交付守卫 |
| `scripts/test_runtime_schema.py`、`scripts/test_runtime_workflow.py`、`scripts/test_runtime_trust.py` | 修改 | 1、2、14 | 历史合同与显式 Runtime 保护 |
| `scripts/test_profile_contracts.py` | 修改 | 1、6、9、13、14 | Tooling/Production 边界及 Skill 合同 |
| `scripts/test_delivery_route_fixture_runner.py`、`scripts/test_downgrade_equivalence.py` | 修改 | 1、7、14 | 路由、兼容与降级反例 |
| `schemas/native/verify-report.schema.json`、`schemas/native/review-report.schema.json`、`schemas/native/native-delivery-verdict.schema.json` | 新建 | 2、12 | 独立 Native v2；不修改 Runtime v1 字段语义 |
| `scripts/native_delivery.py`、`scripts/test_native_delivery.py` | 新建/修改 | 2、6、12 | v2 分派、裁决合同与构造 |
| `scripts/runtime_schema.py` | 修改 | 2、6 | 保留 v1 入口与 Runtime 校验；明确版本分派边界 |
| `scripts/vcs.py`、`scripts/test_vcs.py` | 新建/修改 | 3、10、12 | 小型 Git/SVN Adapter，无隐式服务器写入 |
| `scripts/native_subject.py`、`scripts/test_native_subject.py` | 新建/修改 | 4、10、12 | 公共内容标识、覆盖与表示转换 |
| `skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/scripts/test_verify.py` | 修改 | 5、11 | v2 Verify、输入前后核对、SVN 识别 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 修改 | 6、12 | 档位、内容绑定、Git/SVN 最终结果 |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 修改 | 5、7、8、11 | 报告消费、显式路由、恢复与本地集成 |
| `scripts/delivery_route_fixture_runner.py`、`evaluation/delivery-route-fixtures.json` | 修改 | 7 | 新矩阵、旧 flag 兼容输入 |
| `scripts/downgrade_equivalence.py` | 按需修改 | 7 | 仅修正受新路由影响的比较，保留治理等价保护 |
| `skills/workflow-code-generation/SKILL.md`、`reference/execution-setup.md`、`reference/delivery-guide.md`、`reference/delegated-execution-guide.md` | 修改 | 9、13 | 上述 reference 均位于该 Skill 目录；默认核心与高级路径分离 |
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 修改 | 9 | 档位用于最终 Review，不再隐含 Run |
| `skills/workflow-code-review/SKILL.md`、`reference/report-format.md`、`reference/reviewer-prompts.md` | 修改 | 9 | reference 位于该 Skill 目录；v2 报告与复审主体规则 |
| `skills/workflow-verification/SKILL.md`、`reference/spec-drift-and-scope.md` | 修改 | 9、13 | reference 位于该 Skill 目录；内容绑定与 VCS 约束 |
| 三个核心 workflow 的 `evaluation/trigger-cases.md` | 修改 | 9、13 | 路由、审查、恢复和 SVN 触发场景 |
| `scripts/workspace_residue.py`、`scripts/test_workspace_residue.py` | 修改 | 11、12 | 保留旧快照合同，复用 VCS 查询 |
| `scripts/validate_change.py`、`scripts/tests/test_validate_change.py` | 修改 | 6、11、12 | Production 报告、VCS 和正式交付守卫 |
| `skills/project-init/SKILL.md`、`scripts/test_install_agentic_framework.py` | 修改 | 13、16 | 推荐/探测、安装刷新与原内容保护 |
| `scripts/test_native_delivery_integration.py` | 新建 | 14 | 真实 Git/SVN 两工作副本集成场景 |
| `README.md`、`schemas/runtime/README.md` | 修改 | 15 | 默认模式、版本边界与使用说明 |
| `docs/tooling/11-session-telemetry.md`、`docs/framework-features-status-and-comparison.md`、`docs/harness-alignment/07-host-capability-alignment.md` | 修改 | 15 | 受本次行为变化影响的现状说明，保留历史快照 |
| `evaluation/native-delivery-pilot.md`、`evaluation/real-task-cases/README.md` | 修改 | 16 | 实际效果与测量方法 |
| `evaluation/real-task-cases/2048-native-first-results.md` | 新建 | 16 | 可复核的真实任务记录与 Runtime 对照 |
| 本 Change 的 `specs/` Delta | 新建 | 2、7、12、13 | 路径见知识同步表；未实施结论不提前覆盖长期知识 |
| 知识同步表列出的长期 Specs、相应索引与 `openspec/specs/backend/framework/meta.yaml` | 修改 | 15 | 仅同步已验证行为与来源元数据 |
| 本 Change 的 `tasks.md`、`review-notes.md` | 修改 | 执行期间、17 | 真实状态、定向复审与最终证据 |

### 受影响接口

| 接口 | 变更类型 | 调用方/消费者 | 涉及任务 |
| --- | --- | --- | --- |
| `select_execution_route` / `route` CLI | 新增显式模式，旧 flag 兼容，拒绝不支持/策略冲突 | route fixture、编排 Skill | 7 |
| `inspect_workspace` / `capture_subject` / `collect_changes` / `verify_delivery` | 新建小型公共 VCS 接口 | Verify、控制器、残留检查、交付门 | 3、10–12 |
| 公共 `subject_id` 计算 | 新建；固定算法、基准和覆盖 | Verify、Review 取证、交付门 | 4–6、10、12 |
| `cmd_verify` / `quality_passed` 报告消费 | v1/v2 显式分派，新完成门要求 v2 | 控制器、Native 交付 | 5 |
| `check_native_delivery_review` / `check_native_delivery_verify` | 分版本、类型、档位校验 | Tooling/Production 交付 | 6、12 |
| `build_native_delivery_verdict` / `write_native_delivery_verdict` | 保留现有写出入口与路径保护，新增 v2 | `check_delivery` CLI | 2、6、12 |
| `recover` / `merge_success` | 依据事实恢复；成功集成不等于远程提交 | Native Git/SVN 编排 | 8 |
| `validate_change` 的 Review / Delivery 校验 | 消费新合同但不放宽 Production 守卫 | Production 三阶段门禁 | 6、11、12 |

### 构建系统变更

- 无编译系统或第三方运行依赖新增。新增 Python 模块使用标准库，测试沿用 pytest/unittest。
- Native v2 新 Schema 需要接入加载、校验和安装后访问路径（Tasks 2、16），不能只在框架源码目录可用。
- 不改既有 `verify.config.json`、检查命令、ignore_paths 或基线来迁就失败。新增测试进入既有发现路径；若环境缺工具，先报告缺失并按既有配置维护规则处理。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | 设计将摘要算法与路径分类留给实施 | 4、10、12 | 在 Task 4 冻结算法、基准、排除/覆盖规则；SVN 表示在 Task 10 补齐。报告自引用、提交/归档造成的内容变化均需场景验证，不用“相同 revision”替代内容证明。 |
| 2 | 未指定模式默认 Native，显式审计兼容输入又要求 Runtime | 7 | 区分未指定与显式 native：未指定且有明确 Runtime 要求时选 Runtime，显式 native 与硬要求冲突则拒绝；通过测试固定优先级，未知能力不静默降级。 |
| 3 | 旧任务可能未记录模式，但已有 Run | 7、8、16 | 优先依据真实 Run Context 保持旧路径；无模式且不能判断时报告需核对，不伪造历史或按新版默认重写。沿用 tasks 元数据记录，无第二状态源。 |
| 4 | 全工作区摘要可能把生成文件排除成漏洞 | 4、5 | 明确分类，不沿用通用 ignore 隐藏代码；纳入未跟踪构建输入、配置、文件类型/行为属性，不能证明覆盖时不发完整 PASS。 |
| 5 | 本仓库有无关预存/未跟踪内容，且无 manifest | 1、17 | 保存范围与残留快照；门禁显式 `--governance-profile tooling`。不得清理或提交 `.claude/`、`.codex/`、`mycodex.ps1` 等无关内容。 |
| 6 | SVN 的 mixed revisions、sparse、switched、externals 超出首期保证 | 10–14 | 检测并给出限制，完整交付拒绝不确定；普通人工开发可继续，不能伪称完整验证。 |
| 7 | SVN update 与 commit 间存在竞态、响应可能丢失 | 12–14 | 提交授权独立；写入不藏在查询接口，核对日志/内容解决未知结果，不盲目重提；确切 revision 隔离验证后才声明正式交付。 |
| 8 | 提交后的 subject 含基准而可能变化 | 12 | 明确映射与取证条件；变化时补相应 Verify/Review，不能把提交前 ID 改填成提交后 ID。 |
| 9 | 新报告字段可能通过全局放宽破坏 v1 | 2、5、6、14 | 类型/版本/档位白名单分派；Verify 结果与 v1 禁止集保留，Runtime v1 不迁移。 |
| 10 | 真实任务环境可能没有 SVN 或缺少历史耗时数据 | 14、16 | 要求交付环境具备 `svn`、`svnadmin`；关键 SVN 验收不能以 skip 算完成。不可获取的 token/历史指标写明缺失，不编造基线。 |
| 11 | tasks 执行元数据写入可能改变被检查内容 | 4–6、8、17 | 冻结执行元数据分类，测试记录状态/提交/归档前后的主体核对；不能为稳定摘要排除真实构建依赖或更改旧报告 ID。 |

## 任务列表

### 任务 1：[x] P0：固定现行回归、实施范围与验证基线
- 状态：完成
- attempts：0
- control_stage：completed
- 文件：`scripts/test_workflow_control.py`、`scripts/test_check_delivery.py`、`scripts/test_runtime_schema.py`、`scripts/test_runtime_workflow.py`、`scripts/test_runtime_trust.py`、`scripts/test_profile_contracts.py`、`scripts/test_delivery_route_fixture_runner.py`、`scripts/test_downgrade_equivalence.py`（修改）
- depends_on: []
- review_profile: standard
- 文档映射：design §7.1 P0、§7.2、§8；proposal A6–A7
- 说明：运行现行回归并记录旧语义，补齐缺少的行为保护；保存本次可写范围与预存残留，采改动前基线。新预期先记为迁移用例，不提交永远失败的测试，也不先放宽路由。
- context_files:
  - `verify.config.json` — 既有完整检查入口
  - `skills/workflow-code-generation/scripts/workflow_control.py:select_execution_route` — 现行路由
  - `skills/workflow-code-generation/scripts/check_delivery.py:main` — 原交付分派
  - `scripts/runtime_workflow.py:initialize_run` — 旧 Run 保护
  - `scripts/delivery_route_fixture_runner.py:run_fixtures`、`scripts/downgrade_equivalence.py:compare` — 现行评测消费者
- verification:
  - [x] `python -m pytest scripts/test_workflow_control.py scripts/test_check_delivery.py scripts/test_runtime_schema.py scripts/test_runtime_workflow.py scripts/test_runtime_trust.py scripts/test_profile_contracts.py scripts/test_delivery_route_fixture_runner.py scripts/test_downgrade_equivalence.py -q` 通过；记录旧行为与缺工具项。
  - [x] 按 workflow-verification 采基线；核对 `git status --short` 与范围快照，基线生成成功且用户内容未改。
  - [x] `python -m compileall -q scripts skills/workflow-code-generation/scripts skills/workflow-verification/scripts` 退出 0。
- artifacts:
  - 上述回归测试
  - `.agentic-framework/verify/2048-baseline.json`（本地验证证据，不作为产品新增状态源）
  - 本 Change 实施记录中的范围、基线命令及实际结果
- 子任务：
  - [x] 1.1：固定范围与既有合同，核对宿主、Git、SVN、pytest 工具可用性。
  - [x] 1.2：按 workflow-test-generation 补旧合同保护，运行回归并采基线。

### 任务 2：[ ] P1：建立独立 Native v2 报告合同与兼容分派
- 状态：进行中
- attempts：0
- control_stage：running
- 文件：`schemas/native/verify-report.schema.json`、`schemas/native/review-report.schema.json`、`schemas/native/native-delivery-verdict.schema.json`、`scripts/native_delivery.py`、`scripts/test_native_delivery.py`（新建），`scripts/runtime_schema.py`、`scripts/test_runtime_schema.py`（修改），本 Change `specs/backend/framework/quality-gates/overview.md`（新建）
- depends_on: Task 1
- review_profile: strict
- 文档映射：design §4.2.2–§4.2.3、§4.3.2、§8；proposal A2、A7
- 说明：先建完整 v2 合同和纯校验/构造入口，不切换现行路由。定义 schema_version、subject_id、档位、strict 三项独立性字段与三种 Verdict 的条件证据；保留 Runtime/v1 Schema 和读路径。沿用 check_delivery 的最终写出与路径保护，不另建生成流程。
- context_files:
  - `scripts/runtime_schema.py:validate_document`、`:build_native_delivery_verdict` — 旧校验与构造
  - `schemas/runtime/native-delivery-verdict.schema.json`、`review-report.schema.json`、`verify-report.schema.json` — 历史合同
  - `skills/workflow-code-generation/scripts/check_delivery.py:write_native_delivery_verdict` — 下游写出
  - `scripts/test_runtime_schema.py` — 兼容保护
- verification:
  - [ ] `python -m pytest scripts/test_native_delivery.py scripts/test_runtime_schema.py -q` 通过；缺字段、未知版本、非法状态、证据错配均拒绝。
  - [ ] 测试证明合法 v1 仍可读，v1 不接受伪造独立性/subject 保证，Runtime v1 字段与摘要不变。
  - [ ] `python -m compileall -q scripts` 退出 0；三个新 Schema 以合法与非法 fixtures 实际校验。
- artifacts:
  - 三个 `schemas/native/` Schema 与 `scripts/native_delivery.py`
  - `scripts/test_native_delivery.py`、兼容测试、quality-gates Delta
- 子任务：
  - [ ] 2.1：冻结 v2 字段、状态、保证边界与版本分派，建立质量门 Delta。
  - [ ] 2.2：按 workflow-test-generation 生成各版本与禁止字段反例，先建接口后迁移。

### 任务 3：[ ] P1：建立小型 VCS 接口和 Git 实现
- 状态：进行中
- attempts：0
- control_stage：running
- 文件：`scripts/vcs.py`、`scripts/test_vcs.py`（新建）
- depends_on: Task 1
- review_profile: strict
- 文档映射：design §4.2.4、§4.3.1；proposal R6–R8
- 说明：定义 inspect_workspace、capture_subject、collect_changes、verify_delivery 的结果与错误合同；实现现有 Git 所需的只读操作，SVN 未实现接口明确 unsupported。检测双 VCS/父 Git 包围 SVN，支持显式后端确认，不默认掩盖歧义。此步不迁移 Runtime 全部 Git 操作。
- context_files:
  - `scripts/workspace_residue.py:detect_vcs`、`:git_commit_paths` — 已有查询
  - `skills/workflow-verification/scripts/verify.py:_detect_vcs`、`:_changed_files` — 上游识别
  - `skills/workflow-code-generation/scripts/workflow_control.py` 的 VCS 查询 — 未来调用方
  - `skills/workflow-code-generation/scripts/check_delivery.py:check_git_clean` — 下游消费
- verification:
  - [ ] `python -m pytest scripts/test_vcs.py -q` 通过：真实 Git 根、Worktree、未跟踪、重命名、冲突、错误 commit、双 VCS 探测。
  - [ ] subprocess spy 断言只读查询不执行 update/commit/revert，工具失败不是空变更。
  - [ ] `python -m compileall -q scripts` 退出 0；已有消费者行为尚未切换。
- artifacts:
  - `scripts/vcs.py`、`scripts/test_vcs.py`
- 子任务：
  - [ ] 3.1：固定数据/错误合同和 GitAdapter，未支持能力失败关闭。
  - [ ] 3.2：按 workflow-test-generation 建临时 Git 仓库测试公共接口。

### 任务 4：[ ] P1：冻结公共内容标识与输入覆盖规则
- 状态：未开始
- 文件：`scripts/native_subject.py`、`scripts/test_native_subject.py`（新建），`scripts/vcs.py`、`scripts/test_vcs.py`（修改）
- depends_on: Task 2, Task 3
- review_profile: strict
- 文档映射：design §4.2.3–§4.2.4；proposal R6、A2、A7
- 说明：统一版本库身份、固定检查基准、规范化路径/类型/内容/行为属性、Verify 配置与覆盖分类的摘要；Verify、审查取证、交付共用。保守覆盖工作区与参与构建的未跟踪输入，明确生成/报告/VCS 元数据排除，禁止报告自引用和通用 ignore 隐藏代码。固定基准及提交前后取证规则，无法覆盖返回不确定。
- context_files:
  - `scripts/vcs.py:capture_subject` — 仓库身份与基准
  - `scripts/workspace_residue.py:_hash_path`、`:_canonical_digest` — 可复用算法，残留摘要不是项目内容摘要
  - `skills/workflow-verification/scripts/verify.py:_config_snapshot` — 配置消费
  - `scripts/native_delivery.py` — v2 subject 合同
- verification:
  - [ ] `python -m pytest scripts/test_native_subject.py scripts/test_vcs.py -q` 通过。
  - [ ] 用 fixtures 证明代码/配置/未跟踪构建输入/路径/文件类型/行为属性变化导致 ID 改变，报告输出与纯 VCS 元数据不造成自引用。
  - [ ] 测试前后输入改变、排除项包含构建输入、外部输入不明均不能产生完整已验证声明；算法排序与同基准结果可重复。
  - [ ] `python -m compileall -q scripts` 退出 0。
- artifacts:
  - 公共内容标识实现与测试
  - 本 Change 的算法、基准和分类实施记录
- 子任务：
  - [ ] 4.1：冻结算法与边界，不建设依赖自动推导或新的状态存储。
  - [ ] 4.2：按 workflow-test-generation 测输入覆盖、变化与取证稳定性。

### 任务 5：[ ] P1：Verify 生成 v2 并校验输入前后一致
- 状态：未开始
- 文件：`skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/scripts/test_verify.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/test_workflow_control.py`（修改）
- depends_on: Task 4
- review_profile: strict
- 文档映射：design §4.2.3、§4.2.5；proposal A2、A7
- 说明：standalone 新流程输出顶层 schema_version=2 和 subject_id，检查前后核对同一输入；改动中结果无效。quality_passed 消费合法版本与完整 CheckResult，保持 results/spec_drift 字段与独立性禁止集。保留 Runtime Envelope 路径，不为 Native 初始化 Run。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:cmd_verify`、`:resolve_verify_write_path` — 生成与路径约束
  - `scripts/native_subject.py`、`scripts/native_delivery.py` — 公共计算与合同
  - `skills/workflow-code-generation/scripts/workflow_control.py:_validate_verify_report` — 状态消费者
  - `scripts/runtime_workflow.py` — 历史 Runtime 输出保护
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py scripts/test_workflow_control.py scripts/test_native_delivery.py -q` 通过。
  - [ ] 测试证明检查期间编辑不能 PASS；缺 subject、未知版本、嵌套独立性字段拒绝；合法 v1 历史读取不升级为新证据。
  - [ ] spy 断言 Native 不调用 initialize_run、能力探测或 Journal 写入；已有基线指纹/配置守卫保持。
  - [ ] `python -m compileall -q scripts skills/workflow-verification/scripts skills/workflow-code-generation/scripts` 退出 0。
- artifacts:
  - v2 Verify 输出与控制器消费实现、对应测试
- 子任务：
  - [ ] 5.1：迁移 standalone 生成与消费，保留 Runtime 分支及路径保护。
  - [ ] 5.2：按 workflow-test-generation 测输入竞态、报告污染和新旧版本。

### 任务 6：[ ] P1：Native strict Review 与当前内容交付门
- 状态：未开始
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/native_delivery.py`、`scripts/runtime_schema.py`、`scripts/validate_change.py`、`scripts/test_check_delivery.py`、`scripts/test_native_delivery.py`、`scripts/test_runtime_schema.py`、`scripts/test_profile_contracts.py`、`scripts/tests/test_validate_change.py`（修改）
- depends_on: Task 5
- review_profile: strict
- 文档映射：design §4.2.2–§4.2.3、§4.3.1、§8；proposal A2、A7
- 说明：按 Profile 与实际风险档位接收 Native 三档，新 strict 必须有独立 Judge 证据且与实现者分离。限定 v2 strict Review 顶层三项独立性字段；不放宽 v1 或 Verify 递归禁止集。门重算并交叉核对 Review/Verify/current subject；沿用现有 Verdict 写出与路径约束。Production 最低档位、task Review、strict 集成与批准门保留。
- context_files:
  - `skills/workflow-code-generation/scripts/check_delivery.py:check_native_delivery_review`、`:check_native_delivery_verify`、`:check_native_delivery_verdict_path` — 直接修改
  - `scripts/validate_change.py:_validate_review_report`、`:_validate_delivery_evidence` — Production 消费
  - `scripts/governance_profile.py:review_profile_floor`、`skills/workflow-code-generation/scripts/governance_guards.py` — 守卫
  - `scripts/native_subject.py`、`scripts/native_delivery.py` — 新证据
- verification:
  - [ ] `python -m pytest scripts/test_check_delivery.py scripts/test_native_delivery.py scripts/test_runtime_schema.py scripts/test_profile_contracts.py scripts/tests/test_validate_change.py -q` 通过。
  - [ ] strict 同 actor、缺分离依据、实现者代写声明、P0/P1 非零、三方 subject 错配/交付前编辑均拒绝；合法 strict v2 通过。
  - [ ] v1/Verify 同名与嵌套字段仍拒绝；Production lightweight 被拒绝；缺批准/逐任务报告仍阻断。
  - [ ] 产物路径越界/链接保护与 Runtime Trust 门回归通过；`python -m compileall -q scripts skills/workflow-code-generation/scripts` 退出 0。
- artifacts:
  - Native/Production 报告消费与交付实现、测试、v2 Git Verdict fixture
- 子任务：
  - [ ] 6.1：迁移档位/版本/独立性与内容交叉检查，保留旧保证边界。
  - [ ] 6.2：按 workflow-test-generation 覆盖字段豁免反例、陈旧报告和 Profile 下限。

### 任务 7：[ ] P2：显式 Runtime 路由与兼容评测
- 状态：未开始
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/delivery_route_fixture_runner.py`、`evaluation/delivery-route-fixtures.json`、`scripts/downgrade_equivalence.py`、`scripts/test_workflow_control.py`、`scripts/test_delivery_route_fixture_runner.py`、`scripts/test_downgrade_equivalence.py`（修改），本 Change `specs/backend/framework/workflow-control/overview.md`、`specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md`、`specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md`（新建）
- depends_on: Task 6
- review_profile: strict
- 文档映射：design §4.2.1、§4.3.4、§7.1 P2、§8；proposal A1、A6
- 说明：新增 execution_mode/--execution-mode，strict、并行、普通恢复不自动升级。旧审计/跨宿主 flags 保留明确 Runtime 含义；旧并行/恢复 flags 接受并解释新语义。硬要求冲突、SVN/必需能力不支持明确报错，不降级。已有 Run 优先保持原模式，不从风险或 Profile 名推断审计。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py:select_execution_route`、`:main` — 路由与 CLI
  - `scripts/delivery_route_fixture_runner.py:evaluate_fixture` — 输入/结果合同
  - `scripts/downgrade_equivalence.py:compare` — 治理等价比较
  - `scripts/runtime_workflow.py:load_context` — 已有模式证据
- verification:
  - [ ] `python -m pytest scripts/test_workflow_control.py scripts/test_delivery_route_fixture_runner.py scripts/test_downgrade_equivalence.py -q` 通过；fixture runner 实际运行 PASS。
  - [ ] 三档 × 并行/恢复 × 显式模式 × VCS 的矩阵覆盖；默认 Native，显式 Git Runtime 保留，SVN Runtime/策略冲突拒绝。
  - [ ] 旧 flag 优先级、未知 capability 与已有 Run 恢复有测试；保留旧返回字段的兼容语义，不删 Runtime 保护样本。
  - [ ] `python -m compileall -q scripts skills/workflow-code-generation/scripts` 退出 0。
- artifacts:
  - 路由实现、fixture 与兼容测试
  - workflow-control、Runtime spec/trust-model Delta
- 子任务：
  - [ ] 7.1：固定未指定/显式/硬要求优先级及旧返回字段迁移说明。
  - [ ] 7.2：按 workflow-test-generation 实现路由矩阵、fixture 和降级等价回归。

### 任务 8：[ ] P2：Native 恢复、失败隔离与本地集成语义
- 状态：未开始
- 文件：`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/test_workflow_control.py`（修改）
- depends_on: Task 7
- review_profile: strict
- 文档映射：design §4.2.5、§4.3.4、§8；proposal R3、A3、A6
- 说明：依据 tasks、工作区和真实验证/集成事实恢复 Native，不创建 Run 或补历史。merge_success 仅表示纳入本地集成，不等于 SVN 远程提交。保留状态集合与批准/依赖/失败传播；不确定结果标需核对，重复恢复不触发外部写入。Git Worktree 主方串行集成，SVN 串行写入限制可检查。
- context_files:
  - `skills/workflow-code-generation/scripts/workflow_control.py:plan_recovery`、`:apply_event`、`:_handle_merge_success` — 状态与恢复
  - `scripts/task_ast.py` — 唯一任务状态解析
  - `scripts/native_subject.py`、`scripts/vcs.py` — 当前内容与事实
  - `scripts/runtime_workflow.py` — 既有 Run 不迁移
- verification:
  - [ ] `python -m pytest scripts/test_workflow_control.py scripts/test_task_ast.py scripts/test_task_ast_equivalence.py -q` 通过。
  - [ ] 模拟失败/阻塞/合并冲突/恢复/外部编辑，状态与事实一致；Native 不初始化 Runtime，已有 Run 不换路径。
  - [ ] 重跑只读核验无重复 commit/update；单任务可直接执行但依赖和批准仍拦截；`python -m compileall -q scripts skills/workflow-code-generation/scripts` 退出 0。
- artifacts:
  - 恢复与本地集成语义实现、对应测试
- 子任务：
  - [ ] 8.1：更新事实核对和模式恢复，保持唯一状态源。
  - [ ] 8.2：按 workflow-test-generation 测中断、未知结果、重复执行与失败传播。

### 任务 9：[ ] P2：核心 Skill 与报告规则同步简化
- 状态：未开始
- 文件：`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-generation/reference/execution-setup.md`、`skills/workflow-code-generation/reference/delivery-guide.md`、`skills/workflow-code-generation/reference/delegated-execution-guide.md`、`skills/workflow-code-generation/reference/task_planning_guide.md`，`skills/workflow-code-review/SKILL.md`、`skills/workflow-code-review/reference/report-format.md`、`skills/workflow-code-review/reference/reviewer-prompts.md`，`skills/workflow-verification/SKILL.md`、`skills/workflow-verification/reference/spec-drift-and-scope.md`（修改，各 reference 归属前述 Skill）；`skills/workflow-code-generation/evaluation/trigger-cases.md`、`skills/workflow-code-review/evaluation/trigger-cases.md`、`skills/workflow-verification/evaluation/trigger-cases.md`、`scripts/test_profile_contracts.py`（修改）
- depends_on: Task 8
- review_profile: strict
- 文档映射：design §4.1、§4.2.1–§4.2.3、§4.2.5、§4.3.1、§4.3.4；proposal A3、A8
- 说明：主 Skill 只承载默认核心和必需决策；完整 Runtime 细节渐进读取。允许串行直接执行与按需 DAG/委派，不为探测嵌套能力常规派 Agent。同步三档 Native/v2 取证、独立 Judge、十轮复审；修复延续轮次，上游范围改变建立新主体但保留旧报告。保留 Production 逐任务守卫、审批、知识检查与固定输出字段。
- context_files:
  - `skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-review/reference/report-format.md`、`skills/workflow-verification/SKILL.md` — 直接修改入口与输出合同
  - `skills/workflow-code-generation/scripts/workflow_control.py`、`check_delivery.py` — 已迁移行为
  - `scripts/test_profile_contracts.py` — 机器文案合同
  - `scripts/lint_skill_graph.py` — 引用图消费者
- verification:
  - [ ] `python -m pytest scripts/test_profile_contracts.py scripts/test_lint_skill_graph.py -q` 通过；`python scripts/lint_skill_graph.py` 无错误。
  - [ ] 逐条运行更新后的触发场景，串行 Native 无子 Agent/波次/探测必需步骤；strict 仍独立裁决。
  - [ ] 用定位检查确认活跃规则不再含“strict 必定升级”、恢复必 init-run、最终复审最多两轮，保留任务自身机器修复次数与历史说明的区别。
- artifacts:
  - 核心 Skill/reference、触发场景与 Profile 文案测试
- 子任务：
  - [ ] 9.1：依现有语言风格更新默认流程、进阶读指针和示例。
  - [ ] 9.2：运行引用/触发/档位校验，确认 P1/P2 同批发布可完整使用。
### 任务 10：[ ] P3：SVN Adapter、工作副本限制与内容表示
- 状态：未开始
- 文件：`scripts/vcs.py`、`scripts/test_vcs.py`、`scripts/native_subject.py`、`scripts/test_native_subject.py`（修改）
- depends_on: Task 9
- review_profile: strict
- 文档映射：design §4.2.3–§4.2.4、§4.3.2；proposal R5–R7、A4–A6
- 说明：实现 SVN XML info/status/log/diff 摘要查询，UUID+relative URL 身份、每节点基准与范围；检测冲突、mixed revision、switched/sparse/externals。实现文件/目录/属性/二进制/EOL/keywords 的明确内容表示与比较；不能确定时不返回完整通过。只读 Adapter 不隐藏 update/commit。
- context_files:
  - `scripts/vcs.py`、`scripts/native_subject.py` — 公共入口
  - `scripts/workspace_residue.py:_svn_entries`、`:svn_revision_paths` — 已有 XML 操作
  - `skills/workflow-verification/scripts/verify.py:_svn_status_changes` — 未来消费者
  - `scripts/test_workspace_residue.py` — 已有 SVN 测试经验
- verification:
  - [ ] `python -m pytest scripts/test_vcs.py scripts/test_native_subject.py -q` 通过；本地 svnadmin 仓库真实运行，不以缺工具 skip 完成。
  - [ ] 两 WC 测正常/混合版本/冲突/属性/二进制/空目录/重命名删除、EOL/keywords；异常 UUID/URL/网络/解析返回具体错误。
  - [ ] switched/sparse/externals 检出被明确限制；spy 断言查询无 SVN 写入；`python -m compileall -q scripts` 退出 0。
- artifacts:
  - SvnAdapter、内容表示与真实 fixtures/tests
- 子任务：
  - [ ] 10.1：实现身份、节点状态、支持范围和表示转换。
  - [ ] 10.2：按 workflow-test-generation 测真实 SVN 正常与限制场景。

### 任务 11：[ ] P3：SVN Verify、状态与预存残留整合
- 状态：未开始
- 文件：`skills/workflow-verification/scripts/verify.py`、`skills/workflow-verification/scripts/test_verify.py`、`scripts/workspace_residue.py`、`scripts/test_workspace_residue.py`、`skills/workflow-code-generation/scripts/workflow_control.py`、`scripts/test_workflow_control.py`、`scripts/validate_change.py`、`scripts/tests/test_validate_change.py`（修改）
- depends_on: Task 10
- review_profile: strict
- 文档映射：design §4.2.4–§4.2.5、§4.3.2；proposal R5–R8、A4、A7
- 说明：将已有两种 VCS 查询迁入公共接口，纯 SVN 产生可绑定的 v2 Verify 并运行实际配置检查；不再 Git 优先吞掉 SVN。保留残留快照与作用域合同，覆盖属性和未跟踪输入，工具错误不算无改动。Production Spec Drift 与任务状态门均可在 SVN 工作副本工作。
- context_files:
  - `skills/workflow-verification/scripts/verify.py:_changed_files`、`:cmd_save_baseline`、`:cmd_verify` — 查询与报告
  - `scripts/workspace_residue.py:capture_workspace_residue`、`:compare_workspace_residue` — 残留
  - `skills/workflow-code-generation/scripts/workflow_control.py` 的 VCS 检测 — 调用方
  - `scripts/validate_change.py:validate_change` — Production 消费者
- verification:
  - [ ] `python -m pytest skills/workflow-verification/scripts/test_verify.py scripts/test_workspace_residue.py scripts/test_workflow_control.py scripts/tests/test_validate_change.py -q` 通过。
  - [ ] 真实纯 SVN 跑基线/Verify/Spec Drift，报告 subject 绑定完整；双 VCS 无显式后端拒绝，指定后端可核验。
  - [ ] 预存修改/未跟踪文件与属性变化被检测、未清理；旧 Git 与旧残留快照合法读取回归通过。
  - [ ] `python -m compileall -q scripts skills/workflow-verification/scripts skills/workflow-code-generation/scripts` 退出 0。
- artifacts:
  - 公共 VCS 查询迁移、SVN Verify/残留及 Production 回归测试
- 子任务：
  - [ ] 11.1：迁移查询而不改变无关 Runtime Git 操作。
  - [ ] 11.2：按 workflow-test-generation 覆盖残留保护、工具错误、报告变化与双 VCS。

### 任务 12：[ ] P3：SVN 待提交与确切 revision 交付门
- 状态：未开始
- 文件：`skills/workflow-code-generation/scripts/check_delivery.py`、`scripts/native_delivery.py`、`schemas/native/native-delivery-verdict.schema.json`、`scripts/vcs.py`、`scripts/native_subject.py`、`scripts/workspace_residue.py`、`scripts/validate_change.py`、`scripts/test_check_delivery.py`、`scripts/test_native_delivery.py`、`scripts/test_vcs.py`、`scripts/test_native_subject.py`、`scripts/test_workspace_residue.py`、`scripts/tests/test_validate_change.py`（修改），本 Change quality-gates Delta（修改）
- depends_on: Task 11
- review_profile: strict
- 文档映射：design §4.2.4、§4.3.2、§8；proposal A4–A5
- 说明：原生 SVN 预期改动不走 Git clean；完整本地证据输出 svn-pending-commit，正式交付只接受指定 revision 的 svn-revision-verified。校验 UUID/URL/revision、范围、内容、三方 subject 和确切版本隔离验证；变化时取得对应 Verify/Review。Production 正式门不把待提交视为 PASS。查询门不代执行 commit；提交未知/验证失败保留实际状态。
- context_files:
  - `skills/workflow-code-generation/scripts/check_delivery.py:check_scoped_delivery`、`:main`、`:write_native_delivery_verdict` — 既有分派与写出
  - `scripts/vcs.py:verify_delivery`、`scripts/native_subject.py` — revision 与内容取证
  - `scripts/validate_change.py:_validate_delivery_evidence` — 正式交付消费
  - `scripts/workspace_residue.py:svn_revision_paths` — 交付范围
- verification:
  - [ ] `python -m pytest scripts/test_check_delivery.py scripts/test_native_delivery.py scripts/test_vcs.py scripts/test_native_subject.py scripts/test_workspace_residue.py scripts/tests/test_validate_change.py -q` 通过。
  - [ ] 两 WC 注入不同文件竞态/同文件冲突，只有确切版本及对应证据通过才声明正式交付；待提交正式门拒绝。
  - [ ] 无效 revision、错误 UUID/URL、范围越界、旧 subject、响应不明/版本测试失败不误报，属性/EOL/keywords/目录内容实际核验。
  - [ ] 测试断言门无远程写入、无自动回退/重提；Git v2 与 Runtime 门回归通过，compileall 退出 0。
- artifacts:
  - SVN 两类 Verdict 与交付校验、隔离版本取证、测试和 Delta 更新
- 子任务：
  - [ ] 12.1：接入终态、条件证据、正式门和现有写出路径。
  - [ ] 12.2：按 workflow-test-generation 测确切版本、提交竞态与不确定结果。

### 任务 13：[ ] P3：SVN 工作流与已有项目初始化
- 状态：未开始
- 文件：`skills/project-init/SKILL.md`、`skills/workflow-code-generation/SKILL.md`、`skills/workflow-code-generation/reference/execution-setup.md`、`skills/workflow-code-generation/reference/delivery-guide.md`、`skills/workflow-code-generation/reference/delegated-execution-guide.md`、`skills/workflow-verification/SKILL.md`、`skills/workflow-verification/reference/spec-drift-and-scope.md`（修改，各 reference 归属前述 Skill），`skills/workflow-code-generation/evaluation/trigger-cases.md`、`skills/workflow-verification/evaluation/trigger-cases.md`、`scripts/test_profile_contracts.py`（修改），本 Change `specs/backend/framework/install-agentic-framework/overview.md`（新建）
- depends_on: Task 12
- review_profile: strict
- 文档映射：design §4.3.2–§4.3.3；proposal R5、R7、A4–A8
- 说明：规定保护预存改动→更新→开发/验证/审查→提交前上游核对→明确授权提交→确切版本验证的串行流程。无授权完成本地验证并报告待提交；响应丢失先查证，提交后失败如实报告，不自动 revert。已有 SVN 默认推荐原生，双 VCS 确认后端；不创建镜像/桥接，不删除元数据，沿用初始化 svn add 不自动 commit，修正 OPSX 入口。
- context_files:
  - `skills/project-init/SKILL.md` 的 VCS 选择与提交步骤 — 已有能力
  - 核心 Skill/reference 与 trigger cases — 工作流调用者
  - `scripts/vcs.py`、`skills/workflow-code-generation/scripts/check_delivery.py` — 已实现能力
  - `scripts/test_profile_contracts.py` — 合同验证
- verification:
  - [ ] `python -m pytest scripts/test_profile_contracts.py -q` 通过，`python scripts/lint_skill_graph.py` 退出 0。
  - [ ] 运行 SVN/双 VCS/父 Git/旧混合模式触发场景，未经授权不 commit、不创建 Git；已配置桥接不擅自转换。
  - [ ] 工具日志证明更新/提交只在明确工作流步骤；提交未知/失败报告不宣告成功；初始化仍逐路径 svn add。
- artifacts:
  - SVN/初始化规则、触发用例与 install Delta
- 子任务：
  - [ ] 13.1：同步原生 SVN 完整工作流与模式探测/确认。
  - [ ] 13.2：核验工具调用记录和 Skill 合同，保留 Profile 独立性。
### 任务 14：[ ] P4：真实 Git/SVN 集成与兼容回归
- 状态：未开始
- 文件：`scripts/test_native_delivery_integration.py`（新建），`scripts/test_workflow_control.py`、`scripts/test_check_delivery.py`、`scripts/test_runtime_schema.py`、`scripts/test_runtime_workflow.py`、`scripts/test_runtime_trust.py`、`scripts/test_profile_contracts.py`、`scripts/test_delivery_route_fixture_runner.py`、`scripts/test_downgrade_equivalence.py`（修改）
- depends_on: Task 13
- review_profile: strict
- 文档映射：design §7.2、§8；proposal A1–A7
- 说明：跨入口跑 Native Git 串行/strict/Worktree/恢复，纯 SVN 两 WC 更新/竞态/隔离版本与三种结果；回归旧 Runtime 与 Production，验证无多余副作用、不隐式降级、状态与内容一致。补前序未覆盖的集成断点，不重复实现单元逻辑。
- context_files:
  - `scripts/vcs.py`、`scripts/native_subject.py`、`scripts/native_delivery.py` — 新模块
  - `skills/workflow-code-generation/scripts/workflow_control.py`、`check_delivery.py`、`skills/workflow-verification/scripts/verify.py` — 真实 CLI 链
  - `scripts/runtime_workflow.py`、`scripts/runtime_trust.py`、`scripts/validate_change.py` — 保留路径
- verification:
  - [ ] `python -m pytest scripts skills/workflow-verification/scripts/test_verify.py -q` 全量通过，记录 count/skips 与基线比较；关键 SVN 场景实际执行。
  - [ ] `python scripts/delivery_route_fixture_runner.py` 返回 PASS；Production task/strict/批准门与 Runtime Journal/Manifest/Trust 全套回归通过。
  - [ ] 集成日志证明默认零 Runtime init/probe，SVN 串行写、Git 串行集成，旧 Run 保留；无授权服务器写入次数为 0。
  - [ ] `python -m compileall -q scripts skills/workflow-code-generation/scripts skills/workflow-verification/scripts` 退出 0。
- artifacts:
  - 集成测试、真实 Git/SVN fixtures 与测试证据
- 子任务：
  - [ ] 14.1：按 workflow-test-generation 建两 WC/Worktree/恢复/竞态集成测试。
  - [ ] 14.2：运行全量兼容与门禁矩阵，失败定向修复并重验。

### 任务 15：[ ] P4：文档、知识 Delta 与来源同步
- 状态：未开始
- 文件：`README.md`、`schemas/runtime/README.md`、`docs/tooling/11-session-telemetry.md`、`docs/framework-features-status-and-comparison.md`、`docs/harness-alignment/07-host-capability-alignment.md`、知识同步表列出的长期 Specs、相应索引、`openspec/specs/backend/framework/meta.yaml`（修改），本 Change `specs/backend/engineering/tech/framework-unification.md`（新建）
- depends_on: Task 14
- review_profile: standard
- 文档映射：proposal §4、A8；design §4.4、§5–§6、§7.1 P4、§8–§9
- 说明：以代码与实际验证合并 Delta，明确 Native 保证、显式 Runtime、v1/v2、旧 flags 和升级/回退行为。同步知识来源元数据与索引；现状文档更新，历史快照保留日期与范围。记录保留 Runtime/放弃双同步的权衡，不写未经验证或跨项目知识。遥测固定字段/十轮口径不变，更新结果状态解释。
- context_files:
  - 本 Change `specs/`、proposal/design — 待同步契约
  - `openspec/index.md`、相关长期 Specs — 目标与知识路由
  - 已实现代码、Schema、Task 14 结果 — 当前事实
  - `skills/project-knowledge/SKILL.md` — 同步、冲突与 intent 规范
- verification:
  - [ ] `python scripts/lint_skill_graph.py` 退出 0；`python -m pytest scripts/test_profile_contracts.py scripts/test_lint_skill_graph.py -q` 通过。
  - [ ] 对知识同步表逐行检查目标、Delta 动作、来源路径、版本与索引；列出的链接实际可解析。
  - [ ] 活跃入口与代码一致；历史冲突分别列证据并解决，未验证部分不写成当前事实。
- artifacts:
  - 使用/兼容文档、长期知识与索引、已核验知识同步表
- 子任务：
  - [ ] 15.1：更新使用与升级说明，合并已验证 Delta 并记录架构取舍。
  - [ ] 15.2：按 project-knowledge 核对来源、链接和冲突，公共知识只保留候选。

### 任务 16：[ ] P4：安装刷新与真实任务效果验证
- 状态：未开始
- 文件：`scripts/test_install_agentic_framework.py`、`evaluation/native-delivery-pilot.md`、`evaluation/real-task-cases/README.md`（修改），`evaluation/real-task-cases/2048-native-first-results.md`（新建）
- depends_on: Task 15
- review_profile: standard
- 文档映射：design §7.3、§8、§4.4；proposal A3、A6–A8
- 说明：在隔离测试项目安装/刷新 Tooling、Production 和既有 Run，验证新模块/Schema 可从安装入口真实访问，保留用户文件与原模式。必要安装器修改先以证据补入本任务范围，不能以源码直跑代替安装成功。实际执行小修复、普通功能、strict、并行 Git、SVN 串行任务，并保留 Git Runtime 对照；不只验证 fixture 合同。
- context_files:
  - `scripts/install_agentic_framework.py` 的 install/refresh 入口 — 安装实现
  - `scripts/test_install_agentic_framework.py` — 隔离项目测试
  - `evaluation/native-delivery-pilot.md`、`evaluation/real-task-cases/README.md` — 现有评测记录
  - 三个核心 Skill、`scripts/native_delivery.py`、`schemas/native/` — 安装后消费
- verification:
  - [ ] `python -m pytest scripts/test_install_agentic_framework.py scripts/test_profile_contracts.py -q` 通过；隔离安装后真实运行新 Verify/交付入口。
  - [ ] 真实任务五类各有命令、产物、验证/Review/返工结果；记录耗时、人工停顿、命令/产物数与可获取 token，标明缺数据。
  - [ ] 默认任务零 Runtime init/probe；显式 Git Runtime 对照按原门通过；刷新后已有 Run 未降级，预存文件未覆盖。
- artifacts:
  - 安装刷新测试与实际结果记录
  - `evaluation/real-task-cases/2048-native-first-results.md`
- 子任务：
  - [ ] 16.1：核验隔离安装、刷新与历史任务恢复。
  - [ ] 16.2：执行真实任务并比较实际成本/返工，不承诺无依据降幅。

### 任务 17：[ ] 最终验证、独立严格审查与交付收口
- 状态：未开始
- 文件：本 Change `tasks.md`、`review-notes.md`（修改）；依据保留/归档规则处理本 Change 和索引，不引入新实现功能
- depends_on: Task 16
- review_profile: strict
- 文档映射：proposal A1–A8、§4；design §7–§8；本次完整交付
- 说明：逐项审计需求、任务、实际 Diff 与运行证据；全局 Verify 后进行一次独立 strict 集成 Review，五维/必要 Critic/独立 Judge 保留。修复后重验并定向复审，最多十轮，不补写裁决。完成 intent、知识同步、状态一致性和所需归档，仅提交本次产物后运行交付门；不推送远程、不纳入用户无关内容。
- context_files:
  - 本 Change proposal/design/specs/tasks/review-notes — 完整契约
  - `skills/workflow-code-review/SKILL.md`、`skills/workflow-verification/SKILL.md`、`skills/project-knowledge/SKILL.md` — 最终审查/验证/沉淀
  - `skills/workflow-code-generation/scripts/check_delivery.py` — 实际交付门
  - 本次实际 Diff、Task 14–16 运行证据 — 完成证明
- verification:
  - [ ] 全量测试、graph lint 与 workflow-verification 总判定通过，基线/配置未经偷改；A1–A8 各自有覆盖其范围的实际证据。
  - [ ] `python skills/workflow-code-generation/scripts/lint_task_deps.py <最终tasks路径> --state-consistency` 退出 0；依赖 lint 显式 `--governance-profile tooling` 无错误/警告。
  - [ ] 独立 strict Review 报告 PASS、P0/P1=0，与最终 subject 一致；如有修复保存每轮报告与轮次。
  - [ ] 本地提交后按交付指南运行真实 check_delivery（显式 tooling；有预存内容用事先冻结的 scoped 证据），保存原始输出，不能以本次方案文档 PASS 代替。
- artifacts:
  - 最终 Verify/Review/Verdict、提交与交付门证据
  - 完成任务状态、知识同步/intent 检查、归档或保留记录
- 子任务：
  - [ ] 17.1：逐需求与任务核对完成证据，完成知识/状态检查。
  - [ ] 17.2：最终验证、独立 Review；修复定向复审至通过或如实报告阻断。
  - [ ] 17.3：范围提交、最终门与完整交付报告。

## 文档覆盖映射

| 文档章节 | 任务 | 说明 |
| --- | --- | --- |
| proposal §1、§2 / design §4.1 | 1、7、9、16 | 当前事实、范围、默认核心与效果 |
| proposal R1–R4 | 6–9 | 三档审查、按需辅助、显式模式 |
| proposal R5–R7 | 10–13 | SVN 本地/正式交付与初始化 |
| proposal R8、§3.2 | 1–8、10–14、16 | 版本兼容、副作用、错误与用户内容保护 |
| proposal A1 | 7、14、16 | 路由矩阵及真实任务 |
| proposal A2 | 2、4–6、14 | 独立性、档位与当前内容 |
| proposal A3 | 8–9、14、16 | 串行、依赖、批准与按需辅助 |
| proposal A4–A5 | 10–14、16 | 两 WC、待提交、确切 revision、失败语义 |
| proposal A6–A7 | 1–8、14、16 | 历史 Runtime、显式 unsupported、新合同兼容 |
| proposal A8、§4–§5 | 9、13、15、17 | 文案、知识与完整交付证据 |
| design §4.2.1 | 7 | 模式、策略、旧 CLI |
| design §4.2.2 | 2、6、9 | Native strict 与声明边界 |
| design §4.2.3 | 2、4–6、10、12 | 最小证据、摘要与变化 |
| design §4.2.4 | 3、10–12 | VCS 与消费迁移 |
| design §4.2.5 | 8–9、11、14 | 恢复、集成、失败与并发 |
| design §4.3.1–§4.3.4 | 6–9、10–13、16 | Git/SVN/初始化/显式 Runtime 实际闭环 |
| design §4.4、§5–§6、§9 | 15–16 | 取舍与参考保留；不额外实现桥接/调度服务 |
| design §7.1 P0/P1/P2/P3/P4 | 1 / 2–6 / 7–9 / 10–13 / 14–17 | 阶段与发布边界 |
| design §7.2–§7.3 | 14、16 | 全矩阵与真实效果，前序单元测试先行 |
| design §8 | 1–9、12、15–17 | 版本、状态、升级、回退与完成声明 |
| review-notes 首轮问题/复审提醒 | 2、4–7、9、12–13、16 | 按版本豁免、subject、SVN 终态、策略、已有能力与生成路径 |

## 知识同步

以下 Delta 在对应实施任务创建；当前只生成任务清单，不制造已存在或已验证的 Delta。路径从本 Change `specs/` 镜像长期目标；同步只在相应行为验证后执行。

| Delta（相对本 Change） | 长期目标 | 动作 | 状态 | 索引更新 |
| --- | --- | --- | --- | --- |
| `specs/backend/framework/workflow-control/overview.md` | `openspec/specs/backend/framework/workflow-control/overview.md` | MODIFIED | Pending（7 创建、15 同步） | 对应索引/来源元数据待核对 |
| `specs/backend/framework/quality-gates/overview.md` | `openspec/specs/backend/framework/quality-gates/overview.md` | MODIFIED | Pending（2/12 创建、15 同步） | 对应索引/来源元数据待核对 |
| `specs/backend/framework/install-agentic-framework/overview.md` | `openspec/specs/backend/framework/install-agentic-framework/overview.md` | MODIFIED | Pending（13 创建、15 同步） | 对应索引/来源元数据待核对 |
| `specs/backend/engineering/tech/framework-unification.md` | `openspec/specs/backend/engineering/tech/framework-unification.md` | MODIFIED | Pending（15 同步前创建核验） | engineering 索引待核对 |
| `specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/spec.md` | MODIFIED | Pending（7 创建、15 同步） | 技术索引待核对 |
| `specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | `openspec/specs/backend/engineering/tech/machine-verifiable-agent-runtime/trust-model.md` | MODIFIED | Pending（7 创建、15 同步） | 技术索引待核对 |

intent：高影响架构、放弃重度方案和兼容红线已记录在 design；Task 15 只同步经实现证实的长期约束。故障根因和跨项目候选按实际证据判断，公共库写入仍须另有明确确认。

## 知识冲突

- 当前 Draft 与代码有意不同，不冒充已落地；现状证据见 proposal §1.2、review-notes。
- 下放指南的两轮复审/strict 必 Runtime 与当前主 Review 十轮、Production Native strict 的差异，Task 9 同步。
- project-init 旧 OPSX 描述与统一 workflow 入口的差异，Task 13 同步。
- 归档前核对所有实际代码与长期知识冲突，记录双方证据和处理结果；当前状态：Pending。

## 实际 Diff 核对

- 核对状态：Pending (P0 complete; implementation continues)。
- 实施 Worktree：`.agentic-framework/worktrees/2048`，分支 `change/2048-native-first`，base SHA `00355a9d26bdac2cdf27dfdced37854e18c4d617`。原工作区无关内容保持不变。
- 2026-10-04 P0：独立 Python 3.12.15 环境、pytest 与 SVN 1.14.5 已就绪。源版本全量测试为 4 failed / 570 passed / 136 subtests；graph lint 为 0 errors / 0 warnings；compileall 通过。
- P0 既有失败为安装夹具的旧 manifest 版本、Windows 链接目标前缀和两处未声明 Profile 的调用。修正测试夹具以匹配当前合同，不改生产守卫、不删除测试；补充修改范围为 `scripts/test_install_agentic_framework.py`、`scripts/test_knowledge_management_e2e.py`（现有 `test_workflow_control.py` 已在 Task 1 范围）。
- 改码前基线已单点生成，`B-test-count-not-decrease=574`；后续只读，不因失败重采。
- 执行期按各任务记录实际文件、测试/机器门结果和必要范围变更；最终由 Task 17 对照全清单、proposal A1–A8 与 design 审计，不能仅以任务复选框证明完成。

### P0 verification record

- 2026-10-04: full Verify PASS; B-tests-pass exit=0, B-test-count-not-decrease=574 (baseline=574), graph lint PASS, spec drift PASS. Existing source freshness warnings are reserved for Task 15.
