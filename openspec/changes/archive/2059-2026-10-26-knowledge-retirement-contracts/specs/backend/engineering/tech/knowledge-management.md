# Delta：共享条目退役语义与定位链补全

**状态**：Synced（已按实际 Diff 核对并同步长期方案，2026-10-26）
**动作**：MODIFIED
**长期目标**：`openspec/specs/backend/engineering/tech/knowledge-management.md`

## 变更内容

### 1. §4 目录树：`<domain>/` 内补 `research.md`（Change 树）

`changes/<ticket>-<change-name>/` 树补一行（与 §5.5 既有定义对齐）：

```text
│   ├── <ticket>-<change-name>/
│   │   ├── proposal.md
│   │   ├── specs/
│   │   ├── design.md
│   │   ├── tasks.md
│   │   └── research.md
```

### 2. §5.2 `specs/business/` 职责列表补 `index.md` 一行

在 §5.2 列表首行（`glossary.md` 之前）加入：

```markdown
- `index.md`：业务域清单与定位映射——每个 `<domain>/` 目录一行（名称、一句范围、指向 `overview.md`），以及 `glossary.md` 分节名与 domain 目录名的映射；新增、改名或退役 domain 时同轮更新。小项目不建该文件时，映射写在 `specs/index.md` 对应条目旁。
```

### 3. §9.1 双轨更新指针扩展

§9.1 中「具体前置条件和唯一写入位置统一见 `skills/project-knowledge/SKILL.md` §5、§7.1」改为「§5、§7.1、§7.3」，覆盖操作合同新增的共享条目退役语义（状态标记替代物理删除、直写路径作废写法表、自动流程禁物理删除）。

## 补充候选研究结论

- 退役语义收拢既有四种状态机制（adr-format Status 枚举、公共库证据等级 `deprecated`、`meta.yaml` status、Delta `REMOVED`），为「既有知识澄清」直写路径补作废 SOP；不新增机器校验，执行率低再立 change 加校验（2054 风险表第 3 条同一立场）。
- 定位链缺口（`business/index.md` 无职责、glossary 分节-目录映射无约定）由 `project-knowledge` §3.4 与 `glossary-format.md` 结构规则同轮补全，措辞与本 Delta §2 逐字对齐。

## 同步条件

实施后归档前：核对 `skills/project-knowledge/SKILL.md` 三处改动与本文档描述一致，将「状态」更新为 Synced 并补充最终 Review 结果。长期文件本体由归档合并动作修改，本 Delta 不直接改写。

## 证据

- 当前 Change 的 `proposal.md` §1.2、§3.1。
- 当前 Change 的 `design.md` §4.3 退役标记法表与定位链补全裁决。
- `skills/project-knowledge/SKILL.md` 实际改动（本 worktree Diff）。
