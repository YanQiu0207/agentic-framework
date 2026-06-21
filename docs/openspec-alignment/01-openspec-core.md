# OpenSpec 核心机制总结

> 对象：官方 OpenSpec（Fission-AI/OpenSpec），一个面向 AI 编码助手的轻量级 Spec-Driven Development 工具。
> 本文只记录与 `workflow-*` 对照相关的机制；所有事实附 `来源` 锚点，可直接核对。

## 1. 一句话本质

OpenSpec 把规范分成两半，并用「归档」把它们缝合：`specs/` 是**当前真相**，`changes/` 是**对真相的增量提案**，`archive` 时把增量**合并回**真相。规范由此成为一份持续保鲜、可机器校验的活文档，而非一次性设计稿。

## 2. 解决了什么问题

OpenSpec 针对的痛点是「AI 编码助手在需求只存在于聊天记录里时，强大但不可预测」：

- **意图漂移 / 返工**：需求散落在会话中，AI 凭模糊提示猜意图，常在对齐前就把错的东西做出来。OpenSpec 的主张是「Agree before you build」——人和 AI 先在规范上达成一致，再写代码。
- **上下文流失**：聊天会话结束、成员离开后知识就消失。OpenSpec 把规范作为「living documentation」存在仓库里，让「系统应该做什么」始终可查。
- **评审低效**：变更以规范增量表达，评审者「review intent, not just code」，能在数秒内看懂改了什么、在实现前就抓住错位。

来源：[README](https://github.com/Fission-AI/OpenSpec)（"AI coding assistants are powerful but unpredictable when requirements live only in chat history"、"Agree before you build"）、[openspec.dev](https://openspec.dev/)（"Review intent, not just code"、"Context that persists"）。

## 3. 适用场景

**适合（openspec.dev 的定位）**：

- **成熟 / brownfield 代码库**：官方称最大的痛点是「figuring out how the current system works」，规范库正是用来沉淀「系统现在长什么样、当初为什么这么建」。
- **跨会话 / 团队协作的规划**：相对「单次聊天内规划」，规范持久化、可共享、可评审。
- **需要长期可见性**的项目：始终知道「代码应该做什么」。

**不适合 / 注意（官方明示的边界）**：

- **不是零投入的自动魔法**：官方原话「If you're looking for a magic tool that plans everything for you without any effort on your part, this isn't it」——规范需要人主动读、主动精炼才有效（"works best when you meet it halfway"）。
- **不影响规范的变更**：基础设施 / 工具 / 纯文档类改动不动规范——规范描述的是「系统对外的行为契约」（concepts.md："how your system currently behaves"），这类改动只改「系统怎么造、怎么跑」、不改对外行为，故没有 Requirement 增删改、无 delta 可合并；OpenSpec 为此提供 `archive --skip-specs` 跳过合并（见 [docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)）。*（"为什么"为基于 spec 定义的推断；`--skip-specs` 官方仅说明用于 infrastructure / tooling / doc-only，未展开 rationale。）*
- *（推断，非官方表述）*：纯一次性脚本、需求极简单时，走完整 spec/Scenario/归档流程的收益有限，更适合直接动手。

来源：[openspec.dev](https://openspec.dev/)（"mature codebases where the real struggle is figuring out how the current system works"、"meet it halfway"、"this isn't it"）。注：README 未展开 when-not-to-use。

## 4. 目录结构

```
openspec/
├── specs/                    # 中央真相库，按 capability/domain 组织
│   ├── auth-login/spec.md    # 描述系统【当前】行为（source of truth）
│   └── checkout-payment/spec.md
├── changes/                  # 提案，每个变更一个目录
│   └── add-dark-mode/
│       ├── proposal.md       # 为什么改、改什么
│       ├── design.md         # 怎么改（可选）
│       ├── tasks.md          # 实现清单
│       ├── .openspec.yaml    # 变更元数据（可选）
│       └── specs/ui/spec.md  # delta：## ADDED / MODIFIED / REMOVED Requirements
└── changes/archive/
    └── 2025-01-23-add-dark-mode/   # 归档：delta 已合并进上面的 specs/
config.yaml                   # 项目级配置（可选）
```

- `specs/` 与 `changes/` **分离**是关键：可以并行推进多个变更而不冲突，也可以在影响主规范前先评审一个变更。
- 项目级配置文件是可选的 `config.yaml`，位于 `openspec/` 根；**官方文档中不存在 `project.md`**。

来源：[docs/concepts.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md)、[docs/getting-started.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/getting-started.md)（specs/ 注释为 "Source of truth"）、[openspec.dev](https://openspec.dev/)（"organized by capability"）。

## 5. 三阶段生命周期

```
/opsx:propose  →  创建变更目录（proposal + delta specs + tasks）
/opsx:apply    →  实现任务
/opsx:archive  →  合并 delta 回 specs/，移入 archive/
```

扩展工作流（通过 `openspec config profile` 切换）还有 `/opsx:new`、`/opsx:continue`、`/opsx:ff`、`/opsx:verify`、`/opsx:bulk-archive`、`/opsx:onboard` 等。

设计哲学明确反对刚性门禁：README 逐字写「**Work fluidly — update any artifact anytime, no rigid phase gates**」，并列出「fluid not rigid / iterative not waterfall / easy not complex」。

来源：[README](https://github.com/Fission-AI/OpenSpec)。

## 6. Spec 格式：Requirement + Scenario

每条规范用固定的 Markdown 标题层级组织：

```markdown
## Purpose
<!-- 该 spec 领域的高层描述 -->

### Requirement: User login
The system SHALL authenticate users with valid credentials.

#### Scenario: Valid credentials
- GIVEN a user with valid credentials
- WHEN the user submits login form
- THEN a JWT token is returned
- AND the user is redirected to dashboard
```

- 需求级用 `### Requirement:`，含 RFC 2119 关键字（MUST / SHALL / SHOULD / MAY）。
- 场景级用 `#### Scenario:`，正文是 **Given/When/Then**（大写 GIVEN / WHEN / THEN，外加可选 AND）的要点列表。

来源：[docs/concepts.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md)、[docs/getting-started.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/getting-started.md)。

## 7. Delta 格式：增量表达变更

变更目录内的 `specs/<domain>/spec.md` 不是整篇规范，而是对既有能力的**增量**：

```markdown
## ADDED Requirements      <!-- 新增行为，归档时追加到主 spec -->
## MODIFIED Requirements   <!-- 替换既有需求 -->
## REMOVED Requirements    <!-- 删除已弃用需求 -->
```

每个增量条目内部仍用 `### Requirement:`。归档时这些增量被合并进 `openspec/specs/`。

来源：[docs/concepts.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md)。

## 8. 校验：validate（分级强制）

`openspec validate` 对 changes 与 specs 做结构校验，由 `src/core/validation/validator.ts` 实现。关键规则：

| 规则 | 严重级别 |
| --- | --- |
| delta 缺 `## ADDED Requirements` 等段落 | ERROR（"No delta sections found..."） |
| delta 中 ADDED/MODIFIED 需求**缺场景** | ERROR |
| ADDED 需求**不含 SHALL/MUST** | ERROR |
| 主 spec 中需求**缺场景** | WARNING（`--strict` 下才算失败） |

- 场景计数靠正则 `/^####\s+/gm` 统计 `####` 标题数量（即「有没有场景」），并不在校验层强校验 WHEN/THEN 关键字本身。
- `--strict` 语义：`valid = errors === 0 && warnings === 0`（非 strict 仅要求 `errors === 0`）。
- 标志：`--all`、`--changes`、`--specs`、`--type`、`--strict`、`--json`、`--concurrency`（默认 6）。

来源：[validator.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/validation/validator.ts)、[docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)。

## 9. CLI 工具链

围绕规范本身提供确定性的校验与浏览能力：

| 命令 | 作用 |
| --- | --- |
| `init` | 创建目录结构并配置 AI 工具集成 |
| `update` | 升级 CLI 后刷新指令文件 |
| `list` | 列出 changes 或 specs（`--specs` / `--changes`） |
| `show` | 显示某 change/spec 详情（`--requirements` / `--deltas-only` / `--no-scenarios`） |
| `validate` | 结构校验（`--strict`） |
| `status` | 显示某 change 的 artifact 完成状态 |
| `view` | 交互式终端 dashboard，浏览 specs 与 changes |
| `archive` | 归档并合并 delta 进主 specs |

> ⚠️ **纠正**：官方 CLI **不存在** `openspec diff` 命令（`docs/cli.md` 完整命令列表无 diff，README 与官网亦无）。

来源：[docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)。

## 10. archive：归档即合并（最关键的一步）

`openspec archive [change-name]` 的官方步骤：

1. 校验变更（除非 `--no-validate`）。
2. 请求确认（除非 `--yes`）。
3. **Merges delta specs into openspec/specs/**（把增量合并进中央真相库）。
4. 把变更目录移到 `openspec/changes/archive/YYYY-MM-DD-<name>/`。

`--skip-specs` 可跳过第 3 步（用于基础设施 / 工具 / 纯文档类变更）。README 示例的归档输出也印证：「Archived to ... 2025-01-23-add-dark-mode/ **Specs updated.**」

来源：[docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)、[README](https://github.com/Fission-AI/OpenSpec)。

## 11. 多工具分发

`init` / `update` 为 25+ AI 工具生成各自的 slash command（如 Claude Code 用 `/opsx:propose`，Cursor/Copilot 用 `/opsx-propose`），并在项目根维护一份托管的 `AGENTS.md` hand-off。无需 API key、无需 MCP。还支持把内置 workflow schema fork 到 `openspec/schemas/` 自定义（`openspec schema fork`）。

来源：[docs/supported-tools.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/supported-tools.md)、[docs/commands.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md)、[docs/customization.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/customization.md)、[openspec.dev](https://openspec.dev/)（"No API Keys / No MCP"）。
