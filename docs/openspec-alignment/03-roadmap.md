# 补齐路线图

> 据 [02-gap-analysis.md](02-gap-analysis.md) 及后续讨论修订。
> 目标：在不破坏 `workflow-*`「代码即现状真相」哲学的前提下，补上它真正缺的那一半——**intent 沉淀**。

## 修订说明（重要：原方案已被推翻）

本文件早期版本的 P0 设想过「OpenSpec 式中央行为规范库」（方案 A：升级 `docs/architecture/`；方案 B：新开 `docs/specs/<capability>/`，归档时合并行为需求）。**该方向已被推翻**，理由：

- `workflow-*` 的既定动作是**每次变更重新分析代码提取现状**（`skills/workflow-requirements-clarification/SKILL.md:31`、`:104`；`skills/workflow-system-design/SKILL.md:208`）。它信奉「代码 = 现状的唯一真相」。
- 因此任何手写的「行为现状规范库」都会**和代码争真相、漂移、腐烂**——这恰恰是 `workflow-*` 当初不做归档的原因。OpenSpec 能让 `specs/` 不漂移，靠的是「所有行为变更必经 `changes/` + validate/CI 强制」，`workflow-*` 没有这套纪律。
- 真正缺的不是「现状归档」（代码能重生现状），而是 **intent**（为什么/约束/放弃的方案/权衡）——代码读不出，不沉淀就永久丢失。

详见 [02-gap-analysis.md](02-gap-analysis.md) 第 7 节。

## 价值排序

| 优先级 | 补齐项 | 解决的 gap | 状态 |
| --- | --- | --- | --- |
| P0 | 交付前 intent 沉淀检查 + 盘活 ADR | intent 缺乏沉淀与检索（核心闭环） | 规范已落地，待接入触发点 |
| P1 | 需求挂 Scenario / 验收标准 | 给 test/review 提供验收锚点 | 正交、可选 |
| — | ~~OpenSpec 式行为规范库 + delta + 归档合并~~ | — | **已放弃**（见修订说明） |
| — | ~~spec-lint 结构门禁~~ | — | 降级（见下） |

## P0：intent 沉淀（闭环的关键）

**问题**：每份 feature spec 里那些代码读不出的「为什么 / 约束 / 放弃的方案 / 权衡」，做完就散落在一堆睡着的 spec 里，没汇总、不可检索；而现状不需要归档（代码是真相）。

**方案**（三步，已部分落地）：

1. **强制「交付前沉淀检查」**：开发完 / 归档前，必须显式判定本次变更有没有值得沉淀的 intent——有则写 / 更新 ADR，无则显式判「无需沉淀」。沉默 = 未完成。
2. **盘活 `docs/adr/`**：作为 intent 沉淀的主载体（代码读不出的决策/约束/权衡都进这里）。
3. **已归档 spec 原地保留、可检索**：靠 `<module>/<feature>` 目录结构 + spec 头部元数据按需检索，不新建中央库。

**落地点**：

- ✅ **`project-knowledge`（本轮已改）**：新增「交付前沉淀检查（强制）」节；取消 `architecture/` 现状散文目录；把 ADR 提升为 intent 沉淀主载体；同步原则表改为「现状不写文档、intent 进 ADR」。
- ⏳ **`workflow-code-generation`（待做，需确认）**：在交付环节（Phase 3 汇报 / Task 完成）接入「交付前沉淀检查」的**触发点**——这是让规范真正被执行的一步。否则规则只写在 `project-knowledge` 里，没有流程强制它发生。

**明确放弃**：不建行为规范库（理由见修订说明）。现状的事，交给代码和每次重新调研。

## P1：需求挂 Scenario / 验收标准（正交、可选）

**问题**：`spec.md` 的 `3.1` 功能性需求是自由 bullet（`skills/workflow-requirements-clarification/reference/spec_template.md:24`），无验收锚点。

**方案**：给 `3.1` 每条功能需求挂一个轻量 `Scenario`（可借鉴 OpenSpec 的 Given/When/Then，但不引入 delta 全套）。它既是需求也是验收标准，给 `workflow-test-generation` 和 `workflow-code-review` 的 spec-compliance 一个可对齐的锚点。只改模板与引导话术，不动流程骨架。

> 与 P0 正交：这是「需求表达」的改进，和「intent 沉淀」是两件事，可独立推进或暂缓。

## 降级 / 不做（是取舍，不是缺陷）

- **OpenSpec 式 `specs/` 行为规范库 + delta + 归档合并**：和代码争真相、会漂移、与 `workflow-*` 哲学冲突。放弃。
- **`spec-lint` 结构门禁**：原本是为校验行为规范库的结构。行为库取消后意义减弱——「intent 是否真的沉淀了」很难机械判定（不像「有没有场景」那样可正则统计）。若仍想要，最多做到「校验交付前沉淀检查是否给出了显式结论」这种弱门禁，价值有限，暂不列入。
- **`architecture/overview.md` 现状散文**：取消。现状靠代码，不靠人工保鲜的散文。

## 后续约定

intent 沉淀的**规范**已落在 `project-knowledge`。真正的**执行触发点**（在 `workflow-code-generation` 交付环节接入沉淀检查）是下一步——建议作为独立变更，按 `project-knowledge` 约定在 `docs/design-docs/` 下建正式 `spec.md` 与 `tasks.md` 推进。
