# 审查派发与中间报告

派发 Reviewer 前读取 Reviewer 提示模板；输出意见汇总时读取汇总模板；strict 首审有问题或复审新增 P0/P1 时读取 Critic 部分。

## Reviewer 提示模板

每个 reviewer 的 prompt 按以下模板构建：

```
审查以下代码变更，在你的维度内产出候选 finding。

[Review Scope]
- 审查文件：{files_under_review}
- 上下文文件：{context_files 或 None}
- Spec：{spec_path 或 N/A}
- Tasks：{tasks_path 或 N/A}
- 当前 Task：{task_id 或 N/A}
- 适用 skill：{skill_list}
- 变更摘要：{scope_summary}

[Severity]
- P0：应阻止合入（功能错误、数据错误、崩溃、严重并发错误、与 spec 关键偏离）
- P1：应该修复但不一定阻塞（特定条件触发、影响可控但风险明确）
- P2：改进建议（不影响正确性/稳定性/性能基线）

只报你的维度内的问题。其他维度的线索可以用一行 handoff note 提示。

当 `review_profile` 为 `lightweight` 或 `standard` 时，`comprehensive-reviewer` 还必须在回复末尾输出本轮完整、可直接保存的 6 字段 JSON Artifact（`verdict`、`p0_count`、`p1_count`、`scope`、`review_profile`、`round`）。编排方只能字节级原样保存该 JSON，不得手写、补全或改写字段。
```


## Reviewer 意见汇总

完成去重后，**立即向用户输出 Reviewer 意见汇总**（让用户看到各维度的原始审查视角）：

```markdown
---

## 📋 Reviewer 意见汇总

> 只列本档位实际调用的 reviewer 分节。`lightweight` / `standard` 档仅 `comprehensive-reviewer` 一节，显式追加 reviewer 时再增加对应分节。

### 综合审查 (comprehensive-reviewer，lightweight / standard 档)

- **F-1** [P1 · 需求符合度]
  - **位置**: `file:line`
  - **问题**: [一句话问题摘要]
  - **证据**: [支撑该问题的关键代码片段/数据/逻辑推理]
- 💡 **Handoff notes**: [发现的超出轻量档的高风险线索 + 是否建议升档，无则省略此行]

### 性能审查 (performance-reviewer)

- **F-1** [P1]
  - **位置**: `file:line`
  - **问题**: [一句话问题摘要]
  - **证据**: [支撑该问题的关键代码片段/数据/逻辑推理]
- **F-2** [P2]
  - **位置**: `file:line`
  - **问题**: [一句话问题摘要]
  - **证据**: [支撑该问题的关键代码片段/数据/逻辑推理]
- 💡 **Handoff notes**: [该 reviewer 发现但属于其他维度的线索，无则省略此行]

### 健壮性审查 (robustness-reviewer)

- **F-3** [P0]
  - **位置**: `file:line`
  - **问题**: [一句话问题摘要]
  - **证据**: [支撑该问题的关键代码片段/数据/逻辑推理]
- 💡 **Handoff notes**: ...

### 工程规范审查 (standards-reviewer)

（同上格式，无 finding 则显示"✅ 无发现"）

### 契约与信任链审查 (magical-prompt-reviewer，如本档位调用)

（同上格式）

### 需求/设计符合度审查 (spec-compliance-reviewer)

（同上格式）

---
```


## Critic 提示与结果

```
[Issue 列表]
（逐条列出 F-{seq}、claim、evidence、location、severity、assumptions）

[Review 上下文]
- 相关文件：{files}
- Spec：{spec_path 或 N/A}
- Tasks：{tasks_path 或 N/A}
- 当前 Task：{task_id 或 N/A}
```

收到 critic 结果后，**立即向用户输出 Critic 意见**：

```markdown
---

## 🔍 Critic 对抗性验证

- **F-1** ✅ 成立
  - **问题**: [reviewer 发现的问题简述]
  - **理由**: [为什么同意 reviewer，补充验证证据]
- **F-2** ❌ 驳回
  - **问题**: [reviewer 发现的问题简述]
  - **理由**: [反证摘要：为什么不成立]
- **F-3** ⚠️ 降级
  - **问题**: [reviewer 发现的问题简述]
  - **理由**: [部分成立但严重度应降低的理由]

---
```

> Critic 结论类型：✅ 成立（同意 reviewer）、❌ 驳回（提供反证）、⚠️ 降级（部分成立但建议降低 severity）。
