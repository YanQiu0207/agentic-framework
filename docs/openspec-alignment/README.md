# OpenSpec 对齐专题（openspec-alignment）

> 本目录沉淀对官方 OpenSpec（Fission-AI/OpenSpec）的机制研究、它与本框架 `workflow-*` 工作流的差距分析与补齐建议，以及本仓库 `opsx-*` 复刻与官方的对照。属于「调研 + 规划」专题，不是 feature spec。

## 为什么有这个专题

本仓库同时提供两套设计工作流：默认的 `workflow-*` 技能族，以及作为 OpenSpec 本地复刻的 `opsx-*` 技能族（见 `README.md` 的安装章节）。日常中意 `workflow-*` 的流程，但相比官方 OpenSpec 总感觉「缺了点东西」。

把两者对照的价值在于：它能精确指出 `workflow-*` 缺的到底是哪一层。

> **结论经历过一次修正**（见 [02 第 7 节](02-gap-analysis.md) / [03 修订说明](03-roadmap.md)）：最初以为缺的是 OpenSpec 式「中央行为规范库」；深究后推翻——`workflow-*` 信奉「代码 = 现状的唯一真相、每次重新调研」，硬建行为库会和代码争真相、漂移，与其哲学冲突。**真正缺的是 intent 沉淀**：代码读不出的「为什么/约束/放弃的方案/权衡」，做完就散落在睡着的 spec 里，无汇总、不可检索。补法是 ADR + 交付前沉淀检查，而非行为规范库。

## 文档索引

| 文档 | 内容 | 何时读 |
| --- | --- | --- |
| [01-openspec-core.md](01-openspec-core.md) | 官方 OpenSpec 核心机制总结（带来源 URL） | 想知道 OpenSpec 到底怎么运作 |
| [02-gap-analysis.md](02-gap-analysis.md) | OpenSpec × `workflow-*` 对照（已对抗核验，带证据与诚实降级） | 想知道我们缺什么、强在哪 |
| [03-roadmap.md](03-roadmap.md) | 据 gap 制定的补齐建议（含落地方案） | 准备动手补齐时 |
| [04-opsx-fork-vs-openspec.md](04-opsx-fork-vs-openspec.md) | 本仓库 `opsx-*` 复刻 × 标准 OpenSpec 的对照（公司约束下的有意取舍） | 想知道 opsx-* 和官方差在哪、为什么 |

## 一句话结论

`workflow-*` 是一条优秀的**单次变更执行流水线**（澄清 → 设计 → 编码 → 评审 → 验证），产物是「一次性的、面向单个 feature 的设计文档」，做完即沉睡；OpenSpec 的产物是**持续演进的系统真相**（`specs/` 中央规范库 + 归档即合并）。差异非对称：`workflow-*` 强在执行层（设计深度、对抗式评审、客观门禁），OpenSpec 强在规范层（行为规范长期保鲜）。而 `workflow-*` 该补的不是照搬 OpenSpec 的行为规范库，是补自己缺的那半边——**intent 沉淀**（详见 02 第 7 节）。

## 核验方法说明

本专题关于 OpenSpec 的事实均来自官方 main 分支的实际抓取（README、`docs/`、`src/core/validation/validator.ts`、openspec.dev），并对每条「缺失」候选做过对抗性核验（尽力证伪）。核验过程中纠正了三处常见误记，已在 [02-gap-analysis.md](02-gap-analysis.md) 第 5 节标注：

- 官方 CLI **不存在** `openspec diff` 命令。
- 项目级配置文件是可选的 `config.yaml`，**不是** `project.md`（官方文档无 `project.md`）。
- 场景格式是 **Given/When/Then** 三段式，且校验为**分级**（delta 缺场景报 ERROR，主 spec 缺场景仅 WARNING，`--strict` 下才失败）。

## 来源

- 官方仓库：<https://github.com/Fission-AI/OpenSpec>
- 关键文档：[docs/cli.md](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)、[docs/concepts.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md)、[docs/getting-started.md](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/getting-started.md)、[validator.ts](https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/src/core/validation/validator.ts)、[openspec.dev](https://openspec.dev/)
- 对照的 `workflow-*` 证据：见各文档中的 `file:line` 引用。

## 后续约定

本专题只负责「分析 + 规划」。每个补齐项真正实施时，按 `project-knowledge` 约定在 `docs/design-docs/<module>/<feature>/` 下建正式 `spec.md` 与 `tasks.md`；本目录的 [03-roadmap.md](03-roadmap.md) 作为它们的输入。
