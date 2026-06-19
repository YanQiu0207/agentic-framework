# Harness 工程对齐专题（harness-alignment）

> 本目录沉淀对一篇外部 Harness Engineering 实践文章的研究、它与本框架的差距分析，以及据此制定的改进路线图。属于「调研 + 规划」专题，不是 feature spec。

## 为什么有这个专题

本框架（agentic-engineering-framework）是从第一性原理**演绎**出的一套基于 Skill 的 Agentic Engineering 方法。而一篇来自工业实践的 Harness Engineering 文章，从相反路径（真实项目踩坑**归纳**）得到了高度重叠、但侧重不同的结论。

把两者对照的价值在于：它能暴露本框架「设计上已支持、但实践中未兑现」的盲点——尤其是可执行的客观门禁这一块。

## 文档索引

| 文档 | 内容 | 何时读 |
| --- | --- | --- |
| [01-source-summary.md](01-source-summary.md) | 文章的结构化总结 | 想快速了解文章讲了什么 |
| [02-gap-analysis.md](02-gap-analysis.md) | 文章实践 × 本框架现状对照（带证据） | 想知道我们缺什么、强在哪 |
| [03-roadmap.md](03-roadmap.md) | 据 gap 制定的改进计划（含实施方案） | 准备动手改进时 |

## 一句话结论

文章与本框架在「约束与流程、反馈、知识沉淀、进化」四个维度上高度同构；本框架在理论严谨性、复杂度路由、多维评审上更强，主要短板是**缺少可执行的客观门禁**（verify 脚本 + 基线对比）。

## 来源

- 文章：《万字干货！Harness Engineering 如何工程化落地？》，作者 白家杰，腾讯云开发者。
- 本地副本：`E:\html_2_md\万字干货！Harness_Engineering如何工程化落地？.md`
- 对照的本框架证据：见各文档中的 `file:line` 引用。

## 后续约定

本专题只负责「分析 + 规划」。每个改进项真正实施时，按 `project-knowledge` 约定在 `docs/design-docs/<module>/<feature>/` 下建正式 `spec.md` 与 `tasks.md`；本目录的 `03-roadmap.md` 作为它们的输入。
