# Proposal：Production 复用工作区与交付范围证据

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：production-delivery-evidence
**状态**：Draft

---

## 1. 问题

Tooling 有一套完整的交付范围与工作区残留证据能力，Production 一行都不读。

实测：

```
grep -c "workspace_residue\|scoped_delivery\|git " scripts/validate_change.py  →  0
```

`validate_change.py` 不导入 `workspace_residue`，不调用版本控制，不做任何交付范围核对。它只读 `openspec/changes/<change>/` 下的 Markdown 工件，判定这些文档之间是否自洽。

后果：Production 的 Delivery 门可以在以下情况下通过。

- 实现改动落在声明范围之外的文件。
- 工作区仍有未提交的残留改动。
- `tasks.md` 声明的 `文件` 字段与实际提交路径完全不符。

这些正是 Tooling 的 Scoped Delivery（change 2033）已经堵住的洞。Production 作为面向生产变更的 Profile，在这一维度上**弱于** Tooling，与 `framework-unification.md` §5.1「默认选择审计性和风险控制」直接相悖。

## 2. Tooling 侧已有的能力

`scripts/workspace_residue.py` 是共享模块，公共接口齐备：

| 函数 | 用途 | 行号 |
| --- | --- | ---: |
| `detect_vcs` | 识别 Git／SVN | 110 |
| `capture_workspace_residue` | 采集工作区基线快照 | 241 |
| `validate_workspace_residue_snapshot` | 校验快照结构 | 278 |
| `compare_workspace_residue` | 比对当前工作区与基线 | 301 |
| `git_commit_paths` | 取一次提交touch 的路径 | 322 |
| `svn_revision_paths` | 取一个修订号 touch 的路径 | 361 |
| `validate_delivery_paths` | 判定路径是否越出声明范围 | 377 |
| `normalize_scope_paths` | 范围路径归一 | 66 |

消费方是 `check_delivery.py:390` 的 `check_scoped_delivery`，通过 `--scoped-delivery` 启用，并强制要求 `--native-delivery` 与 `--workspace-residue-baseline`（`check_delivery.py:546-560`）。

模块已在 `scripts/` 下，跨 Profile 导入的机制已经存在（`check_delivery.py:31-37` 就是这么导入的）。**本 Change 不需要新建任何能力，只需要 Production 开始用它。**

## 3. 目标

1. `validate_change.py` 的 `delivery` 阶段读取工作区与交付范围证据。
2. 交付路径越出 `tasks.md` 声明范围时失败关闭，分配新的 OPSX 错误码。
3. 工作区存在未声明残留时失败关闭，分配新的 OPSX 错误码。
4. 新检查在无版本控制或无基线时的行为明确，不静默跳过。

## 4. 非目标

- **不改 `workspace_residue.py`**。本 Change 只增加消费方，不动共享模块。若发现需要改，先停下报告——那会同时影响 Tooling。
- **不改 Tooling 的 Scoped Delivery**。`check_delivery.py` 零改动。
- **不把 Production 改成有状态**。`validate_change.py` 仍是只读裁决器，读版本控制状态不等于维护平行状态。这条是 §8.1 的硬约束。
- **不引入 Production 专属的证据格式**。快照结构复用 Tooling 的既有格式，否则两轨证据无法互认。
- **不做基线采集**。Production 不负责生成 `workspace_residue` 基线，只负责校验；基线由谁生成见 §6.2。

## 5. 与目标模型的关系

这是「Tooling 底座能力被 Production 复用」的第一个实例，也是最便宜的一个——因为能力已经在共享模块里，不需要跨轨搬运代码。

它同时是 `framework-unification.md` §3.2 条件 1 的部分举证：交付证据这一项从「Tooling 独有」变为「两轨共用」，说明该维度可以被表达为可声明策略而非固有差异。

## 6. 设计方案

### 6.1 挂载阶段：`delivery`

Production 的三个阶段中：

- `plan`：`tasks.md` 刚获批，还没有实现，无交付路径可查。不挂。
- `delivery`：实现与测试完成，正是核对范围的时点。**挂这里**。
- `archive`：已过 Delivery 门，此时再查是补票。不挂。

### 6.2 基线来源：新增 CLI 参数，不自动采集

`validate_change.py` 是只读裁决器。自动采集基线意味着写文件，破坏只读性质，违反 §8.1。

因此基线通过新增参数传入，与 Tooling 的 `--workspace-residue-baseline` 同名同格式。谁生成基线由 Production 的 Skill 流程决定，不由校验器承担。

### 6.3 缺证据时的行为：失败关闭，可显式豁免

三种情况需要裁决：

| 情况 | 建议行为 |
| --- | --- |
| 未传基线参数 | 失败关闭，提示必须提供 |
| 仓库无版本控制（`detect_vcs` 抛错） | 失败关闭，提示 Production 要求版本控制证据 |
| 显式声明豁免 | 通过，但必须在 `tasks.md` 留下可审计的豁免记录 |

「静默跳过」不在选项里——那正是 change 2034 要修的那类风险反转。

### 6.4 未裁决项

**豁免记录的字段形式。** 需要一个类似 `Escalation`／`Approval` 的显式声明。是复用现有的 Escalation 机制（`validate_change.py:40-48`），还是新增独立字段，由实现方在 `design.md` 中裁决。倾向复用——新增第三套审批式字段会增加 `tasks.md` 的表面积。

**新增 OPSX 错误码的编号。** 现有已用到 OPSX056（`validate_change.py`）。新码从 OPSX057 起，具体分配由实现方定。

## 7. 验收标准

1. `validate_change.py --phase delivery` 读取交付范围与工作区残留证据。
2. 交付路径越出声明范围时失败关闭，错误码、消息与修复建议齐备。
3. 工作区存在未声明残留时失败关闭，同上。
4. 未传基线参数时失败关闭，不静默跳过。
5. 仓库无版本控制时失败关闭，错误消息说明 Production 的要求。
6. 显式豁免路径可用，且豁免必须留下可审计记录；无记录的豁免不生效。
7. `scripts/workspace_residue.py` 逐字节未改动。
8. `skills/workflow-code-generation/scripts/check_delivery.py` 逐字节未改动。
9. `validate_change.py` 未新增任何文件写入；只读性质有检索证明。
10. 快照格式与 Tooling 一致：同一份基线文件两轨都能校验，有用例证明。
11. 既有 OPSX002 至 OPSX056 的判定结果全部不变。
12. `python -m pytest scripts -q` 全量通过。
13. 按 md-zh 规范自检中文排版。

## 8. 知识影响

- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED。新增 Production Delivery 阶段的交付范围与工作区证据检查。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。§5.3 强制规则新增对应条目；记录这是 §3.2 条件 1 的部分举证。

## 9. 参考资料

- Production 无证据能力：`scripts/validate_change.py`，`workspace_residue` 出现 0 次
- 共享模块接口：`scripts/workspace_residue.py:66,110,241,278,301,322,361,377`
- Tooling 消费方：`skills/workflow-code-generation/scripts/check_delivery.py:390`（`check_scoped_delivery`）、`:512`（`--scoped-delivery`）、`:546-560`（参数强制关系）
- 跨 Profile 导入先例：`skills/workflow-code-generation/scripts/check_delivery.py:31-37`
- Production 定位：`openspec/specs/backend/engineering/tech/framework-unification.md:157`（§5.1）
- 只读约束：同文件 `:299`（§8.1）、`:103`（§3.3）
- Scoped Delivery 来源：`openspec/changes/archive/2033-2026-07-26-scoped-delivery-residue-guard/`
