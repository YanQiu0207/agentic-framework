# Delta：Change 级调研结论落盘约定

**状态**：Pending（归档时按实际实施与验证结果更新）
**动作**：MODIFIED
**长期目标**：`openspec/specs/backend/engineering/tech/knowledge-management.md`

## 变更内容

长期文档 §5.5 `changes/` 职责列表新增一行：

```markdown
- `research.md`：本 Change 的代码调研结论（中间产物，追加式，随 Change 归档）。
```

长期文档 §7.2「编码实现」行更新为：

```markdown
| 编码实现 | 当前 Change（含 `research.md`，存在时）、相关模块 `custom/constraints.md` 和 `custom/pitfalls.md`，然后读取代码 |
```

## 补充候选研究结论

- `research.md` 是 change 级中间产物：由需求澄清与系统设计阶段在调研摘要获用户确认后追加写入，任务拆解时从中提取每任务的「实现参考」（接口级要点 + 章节指针），编码入口存在时强制通读。归档后即历史证据，不参与长期 Specs 的合并与新鲜度管理。
- 落盘写入方是调用方 skill 主会话，`codebase-researcher` 保持只读；与既有「实时更新 Proposal」同一写盘模式。
- 依据：RepoReuse（arXiv:2609.35357）interface memory 实验——需求中列已有函数的接口清单使 agent 复用率翻倍，粘贴完整源码无增益；Anthropic structured note-taking 与 long-running harnesses 的 progress 文件实践。

## 同步条件

实施后归档前：核对五个接线文件的实际改动与本文档描述一致，将「状态」更新为 Synced 并补充最终 Review 结果。长期文件本体由归档合并动作修改，本 Delta 不直接改写。

## 证据

- 当前 Change 的 `proposal.md` 第 1、2、3 节。
- 当前 Change 的 `design.md` 第 4、6 节。
- 五个接线文件改动：见当前 Change 的 tasks.md 与实际 Diff 核对结论。
