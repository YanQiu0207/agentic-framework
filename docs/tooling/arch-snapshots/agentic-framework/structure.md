---
module: agentic-framework
vcs_ref: git:78de137
generated_at: 2026-06-22
track: structure
expires_hint: "structure track 在版本库提交后自动失效；insights track 需人工判断"
---

# Agentic Framework — 结构快照

## 目录结构与各层职责

```
agentic-framework/
├── commands/           用户入口（/xxx slash command → 转发到对应 skill，极薄）
├── skills/
│   ├── workflow-*/     有状态工作流（需求澄清 / 系统设计 / 快速设计 / 代码生成 / 代码评审 / 测试生成）
│   ├── bp-*/           最佳实践参考手册（无状态，按需加载）
│   ├── std-*/          语言编码规范（C++ / Go / Python）
│   ├── project-knowledge/  文档目录约定 + 知识沉淀规范
│   ├── self-refinement/    经验反馈闭环（错误模式 → skill 更新）
│   └── troubleshooting/    问题排查专项
├── agents/             专项 subagent 定义
│   ├── codebase-researcher.md
│   ├── performance-reviewer.md
│   ├── robustness-reviewer.md
│   ├── standards-reviewer.md
│   ├── spec-compliance-reviewer.md
│   ├── magical-prompt-reviewer.md
│   └── review-critic.md
└── docs/               设计决策文档（为什么这样做）
    ├── adr/
    ├── arch-snapshots/
    └── design-docs/
```

## 工作流体系（workflow-*）

| Skill | 职责 | AI 角色 |
|---|---|---|
| `workflow-requirements-clarification` | 明确「要解决什么问题」，产出 spec 1-3 章 | 苏格拉底式追问，只问业务问题 |
| `workflow-system-design` | 将需求转化为设计，产出 spec 4-8 章 | 导师（只提问质疑），用户请求时才给方案 |
| `workflow-quick-design` | 轻量替代路径，适合内部工具 | 设计者（主动给方案，1-2 轮确认） |
| `workflow-code-generation` | 所有代码变更统一入口，复杂度路由 | 执行编排者 |
| `workflow-code-review` | 分级并行评审协调（Judge 角色） | 编排 + 最终裁决 |
| `workflow-test-generation` | 测试生成（可内嵌进代码生成流程） | 实现者 |
## 代码生成执行段的复杂度路由

```
输入 task
  ↓
极轻改动（单文件局部，可直接确定文件列表）？
  ├─ 是 → Fast-Path（主会话直改，无 agent 派发开销）
  │         → review → 交付前沉淀检查
  └─ 否 → 标准流程
           → tasks.md 用户批准（最后一道闸）
           → 为每 task 分配 review_profile
           → DAG 分波（按 depends_on 拓扑）
           → 波内并行 dispatch owner agent（各自跑 worktree）
             → 实现 → 内嵌测试 → review → [自修复] → 合并
           → 失败隔离（单 task 失败不停整体，依赖方标「阻塞」）
           → 全部完成 → 汇总报告 → 交付前沉淀检查
```

## Agents 调度关系

```
workflow-code-review（Judge）
  ├─ 并行调用 → performance-reviewer
  ├─ 并行调用 → robustness-reviewer
  ├─ 并行调用 → standards-reviewer
  ├─ 并行调用 → spec-compliance-reviewer
  ├─ 并行调用 → magical-prompt-reviewer（strict 档）
  └─ 串行调用 → review-critic（有 finding 时）

workflow-requirements-clarification / system-design / troubleshooting
  └─ 调用 → codebase-researcher（研究代码后返回报告）
```

## Review 档位映射

| 档位 | reviewer 组合 | 适用场景 |
|---|---|---|
| lightweight | comprehensive（一趟覆盖工程规范 + 需求符合度） | 配置/文档/极低风险改动 |
| standard | + robustness（性能敏感时另加 performance） | 常规功能开发 |
| strict | 全部 5 个 + critic | 核心逻辑/并发/安全/架构改动 |

## 知识沉淀文档结构

```
docs/
├── adr/NNN-<title>.md          # Intent 沉淀（不可逆决策）
├── arch-snapshots/<module>/    # 时效性快照（vcs_ref 标注）
│   ├── structure.md            # 边界/接口/数据流（本文件）
│   └── insights.md             # 设计模式/关键权衡
└── design-docs/<module>/<feature>/
    ├── spec.md                 # 需求 + 设计（Draft → Archived）
    └── tasks.md                # 任务拆分与进度（进度真相源）
```
