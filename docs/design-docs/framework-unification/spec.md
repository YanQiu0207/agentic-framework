# Agentic Engineering Framework 单仓库双 Profile 最终方案

**状态**：Approved

**日期**：2026-07-19

## 1. 决策结论

将以下两个框架合并为一个独立仓库：

- `E:\github\agentic-engineering-framework`
- `E:\work\my-ai-resource\agentic-framework`

最终采用：

> **一个仓库、一个共享工程内核、两个长期独立的 Policy Profile。**

两个 Profile 分别服务不同场景：

| Profile | 场景 | 优化目标 |
| --- | --- | --- |
| `production` | 生产环境变更 | 正确性、审计、机器证据、风险控制 |
| `tooling` | 大型非生产工具或项目 | 自主执行、并行交付、减少等待、保留必要质量门 |

明确不采用：

- 把 Production 与 Tooling 强行合成一条工作流。
- 在目标项目中默认同时安装两套生命周期入口。
- 用双向同步、定期复制或 Git subtree 长期维护两个实现副本。
- 恢复 `openspec/specs/` 中央现行规范库。
- 把两套 Tasks 控制逻辑合成一个巨型状态机。
- 按「文件较新」直接覆盖同名共享文件。

## 2. 背景与证据

### 2.1 两个框架的真实关系

`E:\work\my-ai-resource\agentic-framework\README.md` 明确将自身定义为独立框架的特化分支：前期由人把关需求与设计，执行段由 AI 自主并行完成。

实机文件对比结果：

| 指标 | 数量 |
| --- | ---: |
| GitHub 框架文件 | 113 |
| Work 框架文件 | 130 |
| 相同相对路径 | 41 |
| 内容完全相同 | 30 |
| 同路径但内容不同 | 11 |
| GitHub 独有 | 72 |
| Work 独有 | 89 |

这说明共享底座仍然接近，但两个工作流家族、脚本和设计文档已经形成独立演进。

### 2.2 资料研究结论

本方案递归扫描了 Work 框架 `docs/` 下的 26 篇 Markdown，选择 20 篇最相关文档全文阅读。

资料中的稳定共识：

1. 应采用「共享内核 + 场景 Profile」，而不是复制两套工程底座。
2. 机器 Verification 与 LLM Review 是并列质量门，不能互相替代。
3. Tooling 的速度来自删除重复 Review、重复审批和重复编排，而不是删除 worktree、Verify 或失败隔离。
4. 确定性脚本应负责状态、依赖、恢复、锁和门禁，LLM 负责语义判断。
5. 代码是当前实现事实源；文档主要保存 intent、权衡和本次变更目标。

需要由最新决策覆盖的旧规则：

- Tooling 旧文中的「task 级 Review + 最终 Review」改为：全部任务和测试完成后，只执行一次首轮 Code Review。
- finding 修复后只执行定向 re-review，不重新启动完整首轮 Review。
- Tooling 的 Tasks 获批后，执行段不再逐 Task 等待人工批准；Production 保留逐 Task 推进和风险分档审核。

## 3. 设计原则

### 3.1 一个实现仓库

唯一主仓库为：

```text
E:\github\agentic-engineering-framework
```

`E:\work\my-ai-resource\agentic-framework` 完成迁移和等价验证后退役为指针说明，不再保存实现副本。

### 3.2 两个 Profile，不是一条流水线的两个开关

Production 与 Tooling 的差异不只是 Review 严格度，还包括：

- Artifact 模型。
- 人工介入点。
- 执行策略。
- 归档要求。
- Verification 失败策略。
- 默认风险偏好。

因此必须保留两个独立生命周期，只共享场景无关的工程能力。

### 3.3 代码事实源

| 信息 | 权威来源 |
| --- | --- |
| 当前模块、接口、数据流和运行行为 | 代码 |
| 本次变更的需求、设计和验收 | Change Artifacts 或 Tooling Spec |
| Production 当前执行状态 | 活跃 Change 的 `tasks.md`；校验器只读，不维护平行状态 |
| Tooling 当前执行状态 | `tasks.md`；`workflow_control.py` 负责校验和原子写回，不另建平行状态 |
| 重大长期决策和放弃方案 | ADR |
| 时效性导航材料 | 带 `vcs_ref` 的架构快照 |
| Review、Verify 和运行证据 | 绑定本次 change、commit 或 run 的报告 |
| 历史变更 | Archive |

禁止创建：

```text
openspec/specs/
```

Production 的 `specs/` 只能存在于单次 Change 目录中，不是当前实现真相。

### 3.4 删除重复成本，不删除质量门

两个 Profile 均保留机器 Verification，并只删除重复审核：

- Production 普通 Task 做一次综合审核，高风险 Task 做一次五维审核，最终再做一次五维集成审核。
- Tooling 不做每个 Task 一次的 LLM Review，全部任务和测试完成后只做一次首轮 Code Review。
- finding 修复后只做定向 re-review。
- Tooling 的中高风险并行任务保留 worktree 和失败隔离；Production 是否使用 worktree 由其独立执行策略决定。
- 文档、Review 和 Verify 必须能留下可审计证据。

## 4. 目标架构

```text
agentic-engineering-framework/
├── agents/                    # Shared Core
├── skills/
│   ├── bp-* / std-*          # Shared Core
│   ├── workflow-code-review/ # Shared Core
│   ├── workflow-verification/ # Shared Core
│   ├── opsx-*                # Production
│   ├── workflow-*            # Tooling
│   └── frontend / init / OCR # Optional Packs
├── commands/                  # 由安装器按 Profile / Pack 白名单选择
├── scripts/
│   ├── install_agentic_framework.py
│   ├── validate_change.py
│   └── tests
├── metrics/                   # 本地遥测账本不入库
└── docs/
```

源码保持平铺，Core、Profile 和 Pack 是由安装白名单与测试强制的逻辑边界，不构成第三条工作流。

## 5. Production Profile

### 5.1 定位

面向进入生产环境的功能、修复和架构变更，默认选择审计性和风险控制，而不是最少步骤。

### 5.2 生命周期

```text
Requirements Clarification
    → Change-local Specs
    → Design
    → Tasks
    → Plan 门禁
    → 逐 Task 实现、测试和风险分档 Review
    → Machine Verification
    → Delivery 门禁
    → 一次五维 Strict 集成 Review
    → 必要时定向 Re-review
    → Archive 门禁
```

### 5.3 强制规则

- Standard 为默认路径；明确低风险且范围稳定时才允许 Quick。
- `validate_change.py` 负责 Plan、Delivery 和 Archive 三阶段的确定性检查。
- `verify.config.json` 必须存在且有效；缺失、失效或被实现阶段弱化时失败关闭。
- 普通 Task 完成实现和测试后，由独立 `comprehensive-reviewer` 执行一次 `standard` 审核。
- 高风险 Task 完成实现和测试后，由 5 个专项 Reviewer 执行一次 `strict` 审核，并由未参与实现的独立 Judge 裁决。
- 每个 Task 的 finding 修复后只定向 re-review，不重新全量扫描。
- 所有 Task、Verification 和 Delivery 门禁完成后，再执行一次五维 `strict` 集成审核。
- 首轮存在 P0/P1 才进入修复循环。
- 修复后重跑受影响的构建、测试和 Delivery，再执行定向 re-review。
- 定向 re-review 最多两轮，仍未通过则转人工。
- Archive 只移动本次 Change，不生成或同步中央 Specs。
- 发布、回滚、灰度、数据迁移、安全、兼容性和容量检查按风险条件启用，不在首轮合并中建设完整发布平台。

### 5.4 变更目录

Standard：

```text
openspec/changes/<change-name>/
├── proposal.md
├── specs/
│   └── <capability>/spec.md
├── design.md
└── tasks.md
```

Quick：

```text
openspec/changes/<change-name>/
├── proposal.md
└── tasks.md
```

## 6. Tooling Profile

### 6.1 定位

面向大型非生产工具或项目，前期由人把关需求和设计，Tasks 获批后由 AI 自主执行。

### 6.2 生命周期

```text
需求明确
    ├── Fast-Path
    ├── Quick Design
    └── 完整 Spec / Tasks
            ↓
Tasks 获批
    → DAG 分波
    → worktree 隔离与并行执行
    → 每个任务实现、测试和机器检查
    → 合并到集成分支
    → 全局 Machine Verification
    → 一次风险分级 Code Review
    → 必要时定向 Re-review
    → 交付和 intent 检查
```

### 6.3 强制规则

- Fast-Path 只适用于请求即计划，且不触碰安全、权限、数据、并发、公共 API 和性能关键路径。
- 中等及以上变更使用 `workflow_control.py` 的 DAG、waves、状态、锁、失败隔离和恢复能力。
- 每个任务可以执行测试和机器检查，但禁止启动 LLM Review。
- 当前路径的全部实现、测试和机器检查完成后，只启动一次首轮 Review；Standard 路径还必须完成全部 Tasks 合并和全局 Verification。
- Review Profile：
  - 低风险：`lightweight`。
  - 普通风险：`standard`。
  - 高风险：自动升级为 `strict`。
- P0/P1 才触发修复；修复后只执行定向 re-review。
- 速度优化不得通过删除 Verification、worktree、失败接管或 intent 检查实现。

## 7. Shared Core

### 7.1 共享资产

以下内容只有一份：

- 通用 `bp-*` 和 `std-*`。
- Reviewer、Critic 和 Researcher Agents。
- `workflow-code-review`。
- Verification 执行器。
- `self-refinement`。
- `troubleshooting`。
- Skill 图和引用检查。
- 通用安装、Manifest 和卸载能力。

### 7.2 共享规则的准入条件

一项规则只有同时满足以下条件才进入 Core：

1. 与 Production、Tooling 的 Artifact 模型无关。
2. 不改变任一 Profile 的人工介入点。
3. 不依赖某个 Profile 独有的状态字段。
4. 两个 Profile 都能通过测试证明其价值。

否则放入对应 Profile 或 Pack。

### 7.3 明确不进入 Core

- `bp-cola-ddd`。
- 旧 `project-knowledge` 中与代码事实源冲突的机制。
- OPSX Artifact 和 Archive 规则。
- Tooling 的 waves、attempts、control stage 和写锁状态。
- Profile 专属的触发和路由规则。

## 8. Task 模型与控制引擎

### 8.1 不建设巨型统一引擎

Production 校验器是只读生命周期裁决器；Tooling 控制器是有状态执行引擎。二者不能合并为同一个状态机。

### 8.2 第一阶段不提取共享解析模型

Production Tasks 服务逐阶段人工批准、Task Review 和归档证据；Tooling Tasks 服务 DAG、waves、attempts、blocked、recovery 和写锁。当前没有证据表明提取公共 AST 能减少净复杂度，因此第一阶段保留两个确定性实现，只统一字段语义和测试术语。

只有同时出现以下信号才重新评估公共 AST：

1. 同一解析缺陷必须在两个实现重复修复。
2. 两边至少 3 个稳定字段具有相同语义和生命周期。
3. Adapter 不需要丢弃 Profile 专属状态。

### 8.3 后续提取顺序

1. 先冻结两边现有 Fixtures 和行为。
2. 建立公共 AST 和 Profile Adapter。
3. 先迁移只读调用方。
4. 最后迁移 Tooling 写状态路径。
5. 每迁移一个调用方都运行兼容性测试。

## 9. Code Review

保留唯一共享入口：

```text
workflow-code-review
```

调用契约：

```text
profile: production | tooling
review_profile: lightweight | standard | strict
mode: initial | re-review
scope: task | integration | run
```

固定规则：

- 每个 Review Scope 只有一次 `initial` Review。
- Production 普通 Task 使用 `standard`，高风险 Task 使用 `strict`，最终 `integration` 固定使用 `strict`。
- Tooling 默认按风险选择 `lightweight` 或 `standard`。
- Tooling 命中高风险信号时自动升为 `strict`。
- 只有 P0/P1 触发修复。
- re-review 只检查原 finding 和修复 diff，禁止重新全量扫描。
- re-review 最多两轮，仍未通过则转人工。

实现基线：

- 以 Work 侧的风险分档、`comprehensive-reviewer`、定向 re-review 和独立 Judge 约束为基础。
- Tooling 叠加「全部任务完成后只执行一次首轮 Review」；Production 使用风险分档 Task Review 加最终五维集成 Review。
- 不按文件更新时间直接覆盖，必须通过 Review 路由和报告格式测试裁决。

## 10. Verification

两个 Profile 共享 Verification 执行器，但策略不同：

| 行为 | Production | Tooling |
| --- | --- | --- |
| `verify.config.json` | 必须存在且有效 | 推荐；缺失时必须显式降级并报告 |
| 配置弱化 | 失败关闭 | 失败关闭 |
| 基线比较 | 必须 | Standard 及以上必须 |
| Spec Drift | 必须 | 代码改动必须说明 |
| 生产资源测试 | 默认排除，受控执行 | 默认排除 |
| 失败处理 | 阻止 Delivery | 阻止交付或转人工 |

AI 可以根据仓库事实生成或维护 Verify 配置，但必须：

- 先探测真实构建和测试入口。
- 写入前试运行。
- 实现阶段冻结基线配置。
- 禁止通过删除检查项解决失败。

## 11. Packs

| Pack | 默认 Profile | 内容 |
| --- | --- | --- |
| `frontend` | Tooling | Frontend Design、Layout、Taste、React、Playwright |
| `project-init` | Tooling | 项目初始化 |
| `open-code-review` | 可选 | 外部独立审查工具 |
| `telemetry` | Tooling 推荐、Production 可选，均需显式安装 | transcript 后处理、成本和收敛分析 |

Pack 不能定义第二条生命周期，也不能覆盖 Profile 的门禁规则。

## 12. 安装与隔离

### 12.1 命令

Production：

```bash
python scripts/install_agentic_framework.py . --profile production
```

Tooling：

```bash
python scripts/install_agentic_framework.py . --profile tooling
```

可选 Pack：

```bash
python scripts/install_agentic_framework.py . \
    --profile tooling \
    --with frontend \
    --with telemetry
```

### 12.2 安装约束

- 必须显式选择一个 Profile。
- 第一版不提供 `--profile all`。
- 同一目标项目默认禁止同时安装两个生命周期 Profile。
- 安装器写入 Manifest，记录版本、Profile、Packs 和受管文件哈希。
- 重装和升级根据 Manifest 精确覆盖受管文件。
- 卸载不得删除项目自有文件。
- Production 安装结果不得出现 Tooling 生命周期入口。
- Tooling 安装结果不得出现 OPSX 生命周期入口。
- Core 文件只安装一份。
- 禁止原地隐式切换 Profile；必须先卸载旧 Profile，或显式使用 `--switch-profile`。
- Profile 切换只能删除 Manifest 中记录的旧 Profile 受管文件，并在完成后执行交叉污染检查。

建议 Manifest：

```text
<target>/.agentic-framework/manifest.json
```

## 13. 遥测与评测

### 13.1 遥测字段

统一报告至少记录：

```text
profile
workflow
review_profile
review_retries
verify_retries
manual_intervention
change
task
```

报告格式属于机器接口，修改模板时必须同步解析器和兼容测试。

### 13.2 评测层级

1. Tier 0：Skill 图、引用、Tasks、Change、Delivery 和安装 Manifest 的确定性检查。
2. Tier 1：Production/Tooling 的 should-trigger、should-not-trigger 和边界路由测试。
3. Tier 2：只对 Review、Profile 路由和门禁高风险修改做 A/B。
4. 第一版不建设自动自进化系统。

## 14. 迁移范围

### 14.1 Shared Core 候选

- 两边完全相同或语义等价的 `bp-*`、`std-*`。
- 现有 6 个共同 Reviewer/Critic Agent。
- `codebase-researcher`，人工裁决 Work 侧新增内容。
- `self-refinement` 和 `troubleshooting`，按职责而不是时间戳裁决。
- Work 侧 `comprehensive-reviewer`。
- Work 侧 Review 评测集。

### 14.2 Production

- 全部 `opsx-*`。
- `validate_change.py` 及 Fixtures。
- OPSX Commands。
- 无中央规范库和代码事实源方案文档。

### 14.3 Tooling

- `workflow-requirements-clarification`。
- `workflow-system-design`。
- `workflow-quick-design`。
- `workflow-code-generation`。
- `workflow-test-generation`。
- Tooling 的 Verification 接线。
- `workflow_control.py`、`lint_task_deps.py`、`check_delivery.py`。
- worktree、waves、写锁、中断恢复和失败接管规则。

### 14.4 Packs

- 前端 Skills 与 `std-react`。
- `project-init`。
- `open-code-review`。
- telemetry 脚本和指标账本模板。

### 14.5 Delete 或不迁移

- `bp-cola-ddd`。
- 重复或冲突的 `project-knowledge` 现状真相机制。
- Tooling 旧 Task 级 LLM Review 规则。
- 已被新校验器替代的重复结构规则。
- 双向同步和复制脚本。

## 15. 分阶段实施

### 阶段 0：冻结合同和基线

- 记录两个目录的文件清单、哈希、Git 状态、测试入口和 Skill 图。
- 固定 Profile、事实源、Review、Verify、Tasks 和安装隔离决策。
- 产出逐文件归类表：Core、Production、Tooling、Pack、Delete。
- 不搬文件，不改变行为。

**验收**：两个现有框架的基线测试均可重复通过。

### 阶段 1：白名单迁入 Work 独有资产

- 以 GitHub 仓库为目标。
- 迁入 Tooling 独有 Skills、Agents、脚本、测试和必要文档。
- 暂时保持原路径和行为，避免同时搬迁与重构。
- 禁止整个目录覆盖。

**验收**：迁入资产来源和 diff 可追踪，不覆盖 Production 已修改内容。

### 阶段 2：归一 Shared Core

- 逐文件裁决 `bp-*`、`std-*`、Agents、`self-refinement` 和 `troubleshooting`。
- 以 Work Review 为基线合并风险分档、独立 Judge 和定向 re-review。
- 接入「只执行一次首轮 Review」规则。
- 固定 Review 报告格式。

**验收**：共享文件只有一份；两个 Profile 的 Review 路由测试通过。

### 阶段 3：建立 Profile 安装隔离

- 引入 Profile Manifest。
- 安装器支持 `production`、`tooling` 和 Packs。
- 禁止默认双 Profile 安装。
- 增加安装、重装、升级、卸载和交叉污染测试。

**验收**：两个临时项目分别只出现自身生命周期入口，Core 文件一致且无重复。

### 阶段 4：提取最小 Task 解析层

- 冻结两边 Tasks Fixtures。
- 记录重复缺陷和字段稳定性证据。
- 未满足第 8.2 节触发条件时不提取公共 AST。
- 满足条件后，先迁移只读调用方，最后才考虑 Tooling 写状态路径。

**验收**：两个实现的 Fixtures、DAG、非法状态、写锁和恢复测试全部通过；没有为了形式复用新增无证据抽象。

### 阶段 5：统一质量门执行合同

- Tooling 删除 task 级 LLM Review，仅保留任务测试和机器检查。
- Tooling 的 task 级 `quality_passed` 重新定义为「实现、测试和任务级机器检查通过」；LLM Review 不参与单任务状态转换。
- 最终全局 Review 是 Run/Change 级门禁，不回写每个 task 的 `control_stage`。
- Production 接入普通 Task 单综合审核、高风险 Task 五维审核和最终五维集成审核。
- 统一 P0/P1 修复、定向 re-review 和两轮上限。
- Archive 校验 Review、Verify 和实际目标路径证据。

**验收**：Production 每个 Task 和最终集成 Scope 各只有一次 `initial` Review；Tooling 每个 Run 只有一次。Tooling 的状态迁移、合并、阻塞和恢复测试均使用新的 `quality_passed` 定义。

### 阶段 6：迁移文档、评测和遥测

- README 增加场景路由表。
- 更新架构文档和 ADR。
- 遥测增加 `profile` 字段。
- 增加两个 Profile 的触发评测和端到端样例。

**验收**：能够分别统计两个 Profile 的时间、Token、Review、Verify 和人工介入数据。

### 阶段 7：退役旧目录

仅在功能和测试达到等价后，将：

```text
E:\work\my-ai-resource\agentic-framework
```

增加迁移说明，指向唯一主仓库和 Tooling 安装命令，并明确停止独立演进。第一阶段不物理删除旧实现，保留为可回退证据；观察期后只有在仓库所有者显式确认时才删除。

不得保留双向同步；旧目录不得再接受功能改动。

## 16. 总体验收标准

### 16.1 仓库

- 只有一个实现仓库。
- Shared Core 不存在重复副本。
- Work 旧目录不再演进代码。
- 所有迁移文件都有来源和裁决记录。

### 16.2 Production

- Standard 和 Quick 均通过 Plan、Delivery、Archive 门禁。
- 不生成或维护中央 `openspec/specs/`。
- 缺少或失效的 Verify 配置失败关闭。
- 普通 Task 使用单综合审核，高风险 Task 使用五维审核，每个 Task 首轮仅一次。
- 全部任务完成后执行一次五维 Strict 集成审核。
- Archive 有机器证据且不覆盖已有目标。

### 16.3 Tooling

- Fast-Path、Quick 和完整路径路由正常。
- DAG 分波、失败隔离、worktree、锁和恢复正常。
- task 级不启动 LLM Review。
- 全部任务完成后只执行一次分级首轮 Review。
- 高风险改动自动升为 Strict。

### 16.4 安装

- 两个 Profile 的安装结果相互隔离。
- Packs 可以独立选择。
- 重装幂等。
- 升级和卸载不损害项目自有文件。
- `lint_skill_graph.py` 输出 `errors=0 warnings=0`。

### 16.5 测试

至少覆盖：

- Production Standard 和 Quick 成功链路。
- Production 中央 Specs 拒绝链路。
- Production 缺失 Verify 配置失败链路。
- Tooling 并行成功链路。
- Tooling 上游失败、下游阻塞链路。
- Tooling 中断恢复和写锁超时。
- 只执行一次首轮 Review 的 Trace 断言。
- 定向 re-review 最多两轮。
- Profile 交叉安装拒绝。
- Manifest 重装和卸载安全性。
- Profile 显式切换及旧入口清理。

## 17. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 两个生命周期入口被同时安装 | Skill 触发竞争 | 强制单 Profile 安装，第一版不提供 `all` |
| 共享规则被某个场景污染 | 另一 Profile 行为改变 | Core 准入条件和双 Profile 测试 |
| Tasks 解析过度统一 | 丢失 Profile 语义 | 最小 AST + Profile Adapter |
| Review 合并后成本回升 | Tooling Token 增长 | 风险分档、一次首轮 Review、定向复审 |
| Production 只增加流程而无真实质量收益 | 交付变慢 | Verify 证据、Profile 遥测和端到端评测 |
| 搬迁与重构同时进行 | 难以定位回归 | 先白名单迁入，再归一和重构 |
| 旧目录继续修改 | 再次形成双头 | 等价验证后立即退役为指针 |

## 18. 回退策略

1. 每个迁移阶段独立提交。
2. 阶段 1 只做白名单迁入，不改变原行为。
3. Profile 安装器稳定前保留两个旧安装入口用于对照测试。
4. 公共 Task Parser 按调用方逐个迁移，可单独回退。
5. 旧目录只在全部验收通过后退役。
6. 任一阶段发现 Profile 语义被破坏，回退该阶段，不通过兼容层掩盖问题。

## 19. 放弃的方案

### 19.1 强行收敛为一条工作流

放弃原因：

- Production 和 Tooling 的 Artifact、人工介入和执行策略不同。
- 单一路由会持续积累条件分支，最终形成难以理解的巨型 Skill。

### 19.2 两套框架继续独立维护

放弃原因：

- 共享 `bp-*`、`std-*`、Agents 和 Review 持续漂移。
- 同一个修复需要重复迁移和验证。

### 19.3 把两个 Skill 目录直接合并

放弃原因：

- 文件冲突虽少，但生命周期触发和安装语义仍会竞争。
- 无法明确哪些规则属于共享 Core。

### 19.4 默认安装两个 Profile

放弃原因：

- 自然语言 Skill 触发不能只靠 Command 前缀隔离。
- 同一需求可能同时命中两个 code-generation 入口。

### 19.5 建设完整 Workflow Engine

放弃原因：

- 当前需要的是可执行、可测试的 Profile 编排，不是 Temporal 或 LangGraph 类平台。
- 完整 Engine 会显著增加持久化、调度、恢复和可观测复杂度。

## 20. 资料依据

本方案重点参考：

| 文档 | 关键证据 |
| --- | --- |
| `01-why-and-methodology.md` | Tooling 的前重后自主、风险分级和脚本下沉，见第 3～26、84～99、186～206 行 |
| `03-parallel-execution-mode.md` | DAG、worktree、失败隔离和执行合同，见第 3～22、28～77 行 |
| `07-critical-review.md` | Review 不能替代编译、测试和 Lint，见第 18～28 行 |
| `08-evaluation-strategy.md` | Tier 0～3 和确定性门优先，见第 8～21、29～71 行 |
| `10-harness-engineering-practices.md` | 共享内核和场景 Profile，见第 83～100 行 |
| `11-session-telemetry.md` | 报告格式是机器接口，见第 48～67、80～89 行 |
| `12-development-workflow-absorption-audit.md` | 确定性内核与 Prompt 编排边界，见第 40～83、111～188 行 |
| `adr/001-machine-verification-gate.md` | Verify 与 Review 并列，见第 13～22 行 |
| `adr/002-retain-and-widen-fastpath.md` | Fast-Path 边界，见第 15～40 行 |
| `adr/003-review-fix-loop-convergence.md` | P0/P1 修复和定向复审，见第 13～17、33～42 行 |
| `adr/004-lighten-default-workflow.md` | 删除重复成本，不删除质量门，见第 7～39 行 |
| `design-docs/workflow-code-generation/deterministic-control-flow/spec.md` | 控制内核和副作用编排分层，见第 73～108 行 |
| `design-docs/workflow-code-generation/write-lock-timeout/spec.md` | Tooling 写状态的并发语义，见第 25～79 行 |
| `design-docs/workflow-verification/ai-maintained-config/spec.md` | Verify 配置探测、试运行和弱化保护，见第 25～31、91～179 行 |

上述路径均相对于：

```text
E:\work\my-ai-resource\agentic-framework\docs
```

## 21. 不确定性与实施边界

- 文档支持双 Profile 架构，但不能证明 Production OPSX 已经过真实生产项目验证。
- `arch-snapshots/` 带明确时效性，当前结构仍应以代码为准。
- Production 的发布、灰度、回滚和数据迁移目前只是条件门禁候选，不在首轮合并中建设完整平台。
- 迁移工作量不能仅凭文件数量可靠估算，不承诺固定完成时间。
- 第一轮实施前必须先生成逐文件归类表和两个仓库的可重复基线。

## 22. 方案对比与最终裁决

对比对象：`../framework/dual-track-merge/spec.md`。

| 维度 | 本方案 | `dual-track-merge` | 裁决 |
| --- | --- | --- | --- |
| 场景隔离 | 必须显式选择一个 Profile，禁止默认双装 | 支持 `opsx\|workflow\|all` | 采用本方案，避免入口竞争 |
| Review 次数 | Production 风险分档 Task Review + 最终五维集成 Review；Tooling 每个 Run 一次 | Tooling 仍写「每产物分级」 | 采用本方案，在生产质量与 Tooling Token 成本之间隔离策略 |
| 中央规范库 | 明确不建立，以代码为当前实现事实源 | 同样不建立 | 一致 |
| 资产边界 | Core、Profile、Pack、Delete 分类 | 主要按两轨直接搬入 | 采用本方案，防止 `project-knowledge`、`bp-cola-ddd` 回流 |
| 安装治理 | Manifest、受管文件哈希、切换约束 | 目录复制和三档安装 | 采用本方案 |
| 落地复杂度 | 原设计建议物理迁移到 `core/`、`profiles/` | 保持顶层平铺 | 第一阶段吸收平铺布局，先用安装清单形成逻辑边界，避免无价值的大规模路径搬迁 |
| 独立裁决 | Shared Review 中要求独立 Judge | 明确 Production 使用独立 Judge | 吸收并强化：Production Strict Review 必须由未参与实现的 Judge 执行 |
| 共享治理 | 规则需同时满足双 Profile 准入条件 | 「谁改谁证明两轨通用」 | 吸收后者作为贡献者检查项 |

**最终选择**：以本方案为准，但将第一阶段源码布局由物理 `core/` / `profiles/` 改为顶层平铺、逻辑分组。Profile 边界由安装器白名单、Manifest、测试和 Skill 图共同强制。只有当平铺布局出现真实命名冲突或测试隔离问题时，才执行物理迁移。
