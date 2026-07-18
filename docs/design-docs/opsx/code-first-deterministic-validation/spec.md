# OPSX 代码事实源与确定性校验方案

**状态**：Implemented（方案 A 已完成实施）

**日期**：2026-07-19

## 1. 决策结论

本框架继续采用纯 Skill 工作流，不把官方 OpenSpec CLI 作为运行地基。

确定采用：

> **代码作为当前实现的唯一事实源；变更文档记录本次 intent、需求、设计和任务；新增 Python 确定性校验器，为现有 OPSX 工作流补充机器门禁。**

明确不采用：

- `openspec/specs/` 中央规范库。
- Delta Spec 合并。
- 官方 OpenSpec CLI 的 Schema、Sync 和 Archive 闭环。
- 官方生成的 OPSX Skills/Commands。
- 与代码并行维护一份完整系统现状文档。

## 2. 背景

当前工作流已经在关键阶段重新读取代码：

- `opsx-requirements-clarification` 自主调研现有模块、接口、数据结构和技术约束。
- `opsx-system-design` 在设计前重新读取相关实现和调用链。
- `opsx-code-generation` 在任务拆解时重新分析修改面、依赖面、构建面以及上下游 context。
- `opsx-quick-design` 在已有系统上扩展时先读取代码，再提出轻量方案。

因此，「没有中央规范库」不是缺陷，而是与现有流程一致的设计选择。

官方 OpenSpec 的主要价值是中央 Specs、Delta 和 Archive 合并。永久禁用中央规范库后，CLI 剩余的 Change 状态、模板和依赖管理能力不足以覆盖实验性 Schema、版本锁定、入口竞争和迁移维护成本。

参考：[OpenSpec Concepts](https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md)。

## 3. 核心原则

### 3.1 代码是当前实现的唯一事实源

代码回答：

- 当前模块如何组织。
- 接口和数据结构是什么。
- 调用链和数据流如何运行。
- 当前真实存在什么约束。

需求澄清、设计和任务拆解不能依赖历史 Archive 推断当前实现。

### 3.2 文档记录变更 intent

文档回答：

- 为什么要改。
- 这次要改变什么。
- 明确不做什么。
- 选择了什么方案。
- 放弃了什么方案以及为什么。
- 完成后如何验收。

文档不得扩写成完整系统现状副本。

### 3.3 测试提供行为证据

代码只能说明「当前实际怎么做」，不一定说明「正确行为应该是什么」。因此：

- Requirements 记录本次变更的目标行为。
- 自动化测试验证目标行为。
- Code Review 检查实现、测试和文档是否一致。

### 3.4 机器校验与 LLM 评审分离

| 门禁 | 负责内容 |
|------|---------|
| Python 校验器 | 文件、字段、依赖、覆盖映射、状态和格式 |
| 构建与测试 | 代码能否编译运行、行为是否通过 |
| Code Review | 需求符合度、健壮性、性能、规范和契约风险 |

机器能确定的问题不得消耗 reviewer token；语义问题不得伪装成正则校验。

## 4. 目标架构

```text
用户
  ↓
OPSX Skills
  ├── 重新读取代码
  ├── 需求澄清 / Quick Design
  ├── 系统设计
  ├── Tasks 拆解
  ├── 实现与测试
  └── 全部任务完成后统一 Code Review
  ↓
validate_change.py
  ├── plan 门禁
  ├── delivery 门禁
  └── archive 门禁
  ↓
openspec/changes/
  ├── 活跃变更
  └── archive/
```

不创建：

```text
openspec/specs/
```

## 5. 事实源与知识载体

| 载体 | 记录内容 | 权威性 |
|------|---------|-------|
| 代码 | 当前模块、接口、数据流和运行逻辑 | 当前实现的唯一事实源 |
| 自动化测试 | 可执行的行为证据 | 与代码共同构成机器证据 |
| `proposal.md` | 问题、目标、非目标和约束 | 本次变更 intent |
| `specs/` 或后续 Requirements | 本次变更目标行为与验收条件 | 只对当前 change 有效 |
| `design.md` | 本次方案、接口决策和权衡 | 本次变更设计 intent |
| `tasks.md` | 实施步骤、代码 context 和验收动作 | 当前变更执行计划 |
| `docs/arch-snapshots/` | 带版本信息的结构和调用链快照 | 有时效性的导航材料 |
| `docs/adr/` | 重大决策、约束和放弃方案 | 长期 intent |
| `changes/archive/` | 已完成变更的历史上下文 | 审计材料，不是当前实现真相 |

## 6. 保留的变更目录

### 6.1 标准路径

```text
openspec/changes/<change-name>/
├── proposal.md
├── specs/
│   └── <capability>/
│       └── spec.md
├── design.md
└── tasks.md
```

适用于：

- 中高风险行为变更。
- 接口、数据模型或跨模块变更。
- 涉及并发、性能、兼容性、升级或回滚。

### 6.2 Quick Design 路径

```text
openspec/changes/<change-name>/
├── proposal.md
└── tasks.md
```

`specs/` 可选，`design.md` 不要求存在。

适用于：

- 低风险、范围明确的内部工具。
- 小型服务或局部功能。
- 不涉及复杂接口、并发和数据迁移。

如果实施过程中风险升级，必须转入标准路径并补齐 Requirements 和 Design。

### 6.3 非行为变更

纯文档、注释、格式或不改变程序行为的工具元数据变更，可以不创建 OpenSpec change。

## 7. 确定性校验器

### 7.1 文件位置

计划新增：

```text
scripts/
├── validate_change.py
└── tests/
    └── test_validate_change.py
```

如果仓库后续建立统一脚本测试目录，应遵循仓库最终约定，不单独发明第二套测试入口。

### 7.2 命令接口

```bash
python scripts/validate_change.py \
    --repo . \
    --change openspec/changes/<change-name> \
    --phase plan
```

Archive 阶段必须额外传入即将由归档 Skill 使用的实际目标路径：

```bash
python scripts/validate_change.py \
    --repo . \
    --change openspec/changes/<change-name> \
    --phase archive \
    --archive-target openspec/changes/archive/YYYY-MM-DD-<change-name>
```

支持阶段：

```text
plan
Delivery
archive
```

实际 CLI 参数统一使用小写：

```bash
--phase plan
--phase delivery
--phase archive
```

建议支持：

```bash
--json
```

供 Skill 和后续自动化读取结构化结果。

### 7.3 退出码

| 退出码 | 含义 |
|-------:|------|
| `0` | 校验通过 |
| `1` | 发现确定性违规 |
| `2` | 调用错误、路径错误或校验器自身异常 |

校验失败必须输出文件、行号、规则编号和修复提示。

## 8. 校验阶段

### 8.1 Plan 门禁

触发时机：

- Proposal、Requirements、Design 和 Tasks 均已完成时。
- Tasks 获得用户确认后、编码开始前。

检查：

#### 通用结构

- Change 目录位于 `openspec/changes/`。
- Change 名称符合动词-名词格式。
- `proposal.md` 存在且非空。
- `tasks.md` 存在且非空。
- 不存在 `openspec/specs/` 中央规范库。

#### Proposal

- 包含问题或背景。
- 包含目标。
- 包含非目标或明确的范围边界。
- 包含成功标准或验收标准。
- Quick Design 明确标记 `Quick Draft`。

#### 标准路径

- `specs/` 至少包含一个非空 Spec。
- `design.md` 存在且非空；无需独立设计的低风险变更应走 Quick Design 或直接编码路径。
- Requirements、Design 与 Tasks 有覆盖关系。

#### Quick Design

- Proposal 包含核心方案、关键权衡和验收标准。
- `design.md` 可以不存在。
- `specs/` 可以不存在。
- Tasks 必须覆盖 Proposal 的验收标准。

#### Tasks

- 每个任务有编号、状态和说明。
- 每个任务有明确依赖或标记为无依赖。
- 依赖引用的任务必须存在。
- 依赖图必须是 DAG。
- 每个任务有可机械执行的验收标准。
- 每个任务包含直接修改文件或明确说明无需修改代码。
- 标准路径必须包含文档到任务的覆盖映射。

### 8.2 Delivery 门禁

触发时机：

- 所有任务实现和测试完成后。
- 完整 Code Review 前。

检查：

- 所有任务状态为 Completed。
- 所有子任务复选框已完成。
- 测试任务已完成，或明确写明 `N/A：<理由>`。
- 构建和测试命令已有成功执行记录；机器记录统一包含「退出码 0」，不适用时使用 `N/A：<理由>`。
- 文档覆盖映射无遗漏。
- `Code Review` 状态为 `Pending`，防止跳过最终评审。
- 没有创建 `openspec/specs/`。

Delivery 校验通过后，才启动一次完整 Code Review。

### 8.3 Archive 门禁

触发时机：

- Code Review PASS 后。
- 移动 change 目录前。

检查：

- Delivery 门禁已通过。
- `Code Review` 状态为 `PASS`。
- 不存在未完成任务。
- Archive 目标目录不存在，防止覆盖。
- Archive 目录名符合 `YYYY-MM-DD-<change-name>`。
- 不存在 `openspec/specs/`。

Archive 校验器只裁决是否允许归档，不负责移动目录。目录移动仍由 `opsx-archive` Skill 执行。

## 9. 校验边界

### 9.1 应由脚本检查

- 文件是否存在。
- 必填章节是否存在。
- 任务引用是否合法。
- 任务依赖是否有环。
- 复选框状态。
- 覆盖映射是否为空。
- Review 状态。
- 目录和命名格式。
- 是否误建中央规范库。

### 9.2 不应由脚本判断

- 需求是否合理。
- 方案是否最优。
- 代码调研是否足够深入。
- Requirements 的语义是否正确。
- 代码是否真正满足需求。
- 性能、并发或契约是否存在风险。

这些问题分别由用户确认、代码调研、测试和 Code Review 处理。

### 9.3 禁止脆弱启发式

第一版不得使用以下方式假装完成语义校验：

- 用关键词数量判断设计质量。
- 用文档长度判断需求完整性。
- 用是否出现「测试」两个字判断测试充分性。
- 用文件数量判断任务粒度。
- 用 LLM 输出作为确定性校验器的内部依赖。

## 10. Skill 接入点

### 10.1 `opsx-requirements-clarification`

- 保持代码自主调研。
- Proposal 和 Requirements 完成后明确交接；此时不得越界创建 `tasks.md`。
- 由 `opsx-code-generation` 创建并确认 Tasks 后统一运行 Plan 门禁。
- Plan 校验失败时修正文档，不进入编码。

### 10.2 `opsx-quick-design`

- 保持一次收集 Brief 和 AI 主动设计。
- Proposal 和 Tasks 完成后运行 Quick Plan 门禁。
- 风险升级时转标准路径。

### 10.3 `opsx-system-design`

- 设计前重新读取代码。
- Design 完成后明确交接，由 `opsx-code-generation` 创建并确认 Tasks 后统一运行 Plan 门禁。
- 不用历史 Archive 替代当前代码调研。

### 10.4 `opsx-code-generation`

- Tasks 创建完成后运行 Plan 门禁。
- 全部实现和测试完成后运行 Delivery 门禁。
- Delivery 通过后只启动一次完整 Code Review。
- finding 修复后只执行定向 re-review。
- finding 修复后先重跑受影响的构建和测试、更新执行记录并再次通过 Delivery，不启动第二次完整 Code Review。
- PASS 后更新 `Code Review` 状态。

### 10.5 `opsx-test-generation`

- 测试作为 Tasks 的组成部分。
- 测试完成后返回 Code Generation。
- 不独立启动第二次 Code Review。

### 10.6 `opsx-archive`

- 移动目录前运行 Archive 门禁。
- 只移动 `openspec/changes/<name>`。
- 不合并或生成中央 Specs。

### 10.7 `opsx-project-knowledge`

继续明确：

- 代码是当前实现的唯一事实源。
- Change Artifacts 只描述本次变更。
- Archive 保存历史 intent。
- 不维护中央规范库。
- 需求、设计和任务拆解每次重新读取代码。

## 11. 配置方式

第一版不引入复杂 YAML Schema，优先从当前 Markdown 结构中读取信息。

如果不同项目的模板差异导致解析不稳定，再引入最小配置：

```json
{
    "proposal": {
        "required_sections": ["背景", "目标", "非目标"]
    },
    "tasks": {
        "review_status_pattern": "Code Review: (Pending|PASS)"
    }
}
```

配置必须满足：

- 可选。
- 有合理默认值。
- 不包含项目现状信息。
- 不把语义判断转移到复杂正则。

## 12. 测试策略

### 12.1 单元测试

覆盖：

- Change 路径校验。
- Proposal 章节识别。
- Quick/Standard 路径识别。
- Tasks 解析。
- 不存在的依赖。
- 自依赖。
- 多节点依赖环。
- 未完成复选框。
- Review 状态。
- 中央规范库禁止规则。
- JSON 输出。
- 退出码。

### 12.2 Fixture

至少准备：

```text
valid-standard/
valid-quick/
missing-proposal/
missing-tasks/
missing-specs-standard/
cyclic-tasks/
unfinished-delivery/
review-not-pass/
forbidden-central-specs/
```

### 12.3 集成测试

验证三条完整链路：

1. Standard：Plan → Delivery → Review PASS → Archive。
2. Quick：Quick Plan → Delivery → Review PASS → Archive。
3. 失败链路：任一门禁失败后不得进入下一阶段。

## 13. 分阶段实施计划

### 阶段 0：固化现有格式

- 收集现有 Proposal、Spec、Design 和 Tasks 样例。
- 明确 Standard 与 Quick 的最小合法结构。
- 建立正例和反例 Fixture。
- 不修改现有 Skills。

### 阶段 1：实现只读校验器

- 实现路径和 Artifact 解析。
- 实现 Plan、Delivery、Archive 三阶段检查。
- 支持文本和 JSON 输出。
- 补齐单元测试。

### 阶段 2：接入 Plan 门禁

- 接入 Requirements Clarification。
- 接入 Quick Design。
- 接入 System Design。
- 接入 Tasks 创建完成节点。

Plan Fixture 和单元测试通过后，接入失败即停的强制门禁。

### 阶段 3：接入 Delivery 和 Archive

- Delivery 通过后才执行一次完整 Code Review。
- Archive 只接受 Review PASS。
- 添加不得创建中央规范库的检查。

### 阶段 4：清理重复文案

校验器稳定后，从 Skills 中删除已经由脚本确定性执行的重复规则，只保留：

- 何时调用校验器。
- 校验失败如何处理。
- 语义流程和用户交互规则。

避免脚本和 Skill 同时维护两套详细规则。

## 14. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Markdown 格式差异导致误报 | 正常变更被阻断 | 阶段 0 收集真实 Fixture，先观测后阻断 |
| 校验器承担语义判断 | 规则脆弱、误判 | 只检查确定性结构，语义交给 Review |
| Standard 与 Quick 边界不清 | 要求错误 Artifact | Proposal 明确 Quick Draft，测试两条路径 |
| Tasks 格式持续变化 | 解析器漂移 | 固化最小语法，格式变更必须更新测试 |
| 校验规则与 Skill 重复 | 双重维护 | 稳定后让脚本成为结构规则单一事实源 |
| 每个项目格式不同 | 通用性不足 | 先支持框架默认格式，后续只加最小配置 |
| 阻断上线过早 | 影响现有流程 | 先以正反例 Fixture 和单元测试验证规则，再接入失败即停的强制门禁 |

## 15. 回退策略

1. 每个阶段独立提交。
2. 阶段 1 校验器默认只读，不修改变更文档。
3. 门禁接入点保持独立，出现无法接受的误报时可单独回退对应接入点。
4. 接入点可以逐个回退，不影响其他 Skill。
5. 删除校验器后，现有纯 Skill 流程仍可正常运行。

## 16. 验收标准

### 16.1 代码事实源

- 需求、设计和 Tasks 阶段都有本次代码调研动作。
- 文档不维护完整系统现状。
- Archive 不被用于回答当前实现问题。
- 不存在 `openspec/specs/`。

### 16.2 校验器

- 三个阶段均有稳定退出码。
- 错误包含文件、行号、规则和修复提示。
- JSON 输出可供 Skill 解析。
- Tasks 环检测覆盖自依赖和多节点环。
- 正例 Fixture 全部通过。
- 反例 Fixture 命中预期规则。

### 16.3 工作流

- Standard 与 Quick 路径均可运行。
- 机器能检查的问题不再启动 reviewer。
- 每个任务完成后不执行 Code Review。
- 全部任务完成后只执行一次完整 Code Review。
- finding 修复后只执行定向 re-review。
- Archive 前必须 Review PASS。

### 16.4 兼容性

- 校验器只依赖 Python 3 标准库。
- Windows 和类 Unix 环境均可执行。
- 中文路径和 UTF-8 Markdown 可正确处理。
- 校验器不修改用户文档。

## 17. 放弃的方案

### 17.1 官方 OpenSpec CLI + 中央规范库

放弃原因：

- 与代码事实源原则冲突。
- 需要长期维护系统行为规范副本。
- Archive 合并会建立第二套当前事实。

### 17.2 官方 OpenSpec CLI + 永久 `--skip-specs`

放弃原因：

- 放弃了 OpenSpec 最核心的中央 Specs 和 Delta 合并价值。
- 剩余收益不足以覆盖实验性 Schema、版本锁定和入口竞争成本。
- 当前 Python 校验器能以更低复杂度覆盖主要确定性需求。

### 17.3 继续只靠 Skill 文案

放弃原因：

- Tasks 环、必填文件、状态和覆盖映射属于机器可判断问题。
- 仅靠提示词无法提供稳定退出码和自动化证据。
- 会浪费 Code Review token 处理结构性错误。

## 18. 推荐实施范围

已批准并连续实施：

1. 阶段 0：固化现有格式和 Fixture。
2. 阶段 1：实现只读校验器。
3. 阶段 2：接入 Plan 门禁。
4. 阶段 3：接入 Delivery 和 Archive 门禁。
5. 阶段 4：清理被校验器替代的重复结构规则。

本轮明确不实施：

- 自动修改文档。
- 自动归档。
- 多项目可配置格式。
- 与本次确定性校验无关的 Skill 重构。
