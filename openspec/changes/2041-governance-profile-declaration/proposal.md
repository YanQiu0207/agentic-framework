# Proposal：治理 Profile 可声明化

**作者**：YanQiu0207（AI 辅助）
**日期**：2026-07-26
**变更**：governance-profile-declaration
**状态**：Draft

---

## 1. 问题

Profile 已经被机器记录，但没有任何门禁读它。

安装器把 Profile 写进安装清单：

```python
MANIFEST_PATH = Path(".agentic-framework/manifest.json")   # install_agentic_framework.py:19
MANIFEST_SCHEMA_VERSION = 3                                # :24
profile = manifest.get("profile")                          # :607
if profile not in {"production", "tooling"}:               # :608
    raise ValueError("Manifest has an invalid profile")    # :609
```

但四个门禁脚本一个都不读它：

| 脚本 | `manifest` 出现次数 | 说明 |
| --- | ---: | --- |
| `scripts/validate_change.py` | 0 | 不读 |
| `skills/workflow-code-generation/scripts/check_delivery.py` | 2 | 是 `run_manifest_evidence_graph`，Runtime 能力串，与安装清单无关 |
| `skills/workflow-code-generation/scripts/workflow_control.py` | 0 | 不读 |
| `skills/workflow-code-generation/scripts/lint_task_deps.py` | 0 | 不读 |

`AGENTS.md` 里的「本项目使用 Tooling Profile」是给人和 LLM 看的散文，没有脚本消费。

结果：Profile 目前只决定**装哪些文件**，不决定**门禁怎么判**。两轨的差异全部硬编码在两套脚本里，而不是由声明驱动。

## 2. 第二个问题：`review_profile` 没有下限

`REVIEW_PROFILES = {"lightweight", "standard", "strict"}`（`lint_task_deps.py:37`）只校验取值合法，不校验档位是否够。

也就是说，写 `tasks.md` 的 Agent 可以给自己的任务声明 `lightweight`，门禁照过。没有任何机制规定「这类项目／这类任务最低必须 standard」。

Production 侧有部分约束：OPSX055 要求 `irreversible` 与 `strict` 双向绑定（`framework-unification.md:188`）。但那是单点绑定，不是 Profile 级下限。

## 3. 目标

1. 门禁能读到当前项目的治理 Profile，来源机器可读。
2. `review_profile` 有 Profile 级下限，低于下限时失败关闭。
3. 声明缺失时的行为明确，不静默按宽松档处理。
4. 为 change 2042 的降级等价判据提供可切换的 Profile 开关。

## 4. 非目标

- **不改安装器的 Profile 语义**。`--profile` 的互斥安装、白名单、Registry 全部不动。
- **不改 manifest schema**。`profile` 字段已存在且已校验，本 Change 只增加消费方。若确需扩字段，须升 `MANIFEST_SCHEMA_VERSION` 并单独裁决。
- **不合并两轨门禁**。本 Change 只让门禁知道自己在哪个 Profile 下运行，不改变任何一轨的判定内容。
- **不实现降级路径**。`governance_profile` 的实际降级行为由 change 2042 建设。
- **不改 `AGENTS.md` 的声明**。散文声明保留，只是不再是唯一来源。

## 5. 设计方案

### 5.1 来源：安装 manifest，不是 AGENTS.md

`AGENTS.md` 是自然语言，解析它等于让门禁做语义判断。`manifest.json` 已经是结构化的、已校验的、由安装器写入的事实源。

读取路径：从被校验的仓库根向上找 `.agentic-framework/manifest.json`。

### 5.2 缺失时的行为：失败关闭，可显式覆盖

三种情况：

| 情况 | 行为 |
| --- | --- |
| manifest 存在且 `profile` 合法 | 采用 |
| manifest 不存在（例如开发框架仓库自身） | 失败关闭，除非显式传入 `--governance-profile` |
| manifest 存在但 `profile` 非法 | 失败关闭，不回退默认值 |

「静默默认为 tooling」不在选项里——那会让 Production 项目在 manifest 损坏时悄悄降到宽松档，正是最危险的失败方向。

注意本仓库自身没有 `.agentic-framework/`（它是框架实现仓库，不是安装目标）。因此 `--governance-profile` 参数不是边角情况，是本仓库跑门禁的常规路径。

### 5.3 `review_profile` 下限

下限由 Profile 决定：

| Profile | `review_profile` 下限 | 依据 |
| --- | --- | --- |
| `production` | `standard` | §5.3「Standard 为默认路径；明确低风险且范围稳定时才允许 Quick」 |
| `tooling` | `lightweight` | §6.3 允许低风险兼容调用用 `lightweight` |

Production 下不允许 `lightweight`；两轨都允许向上声明 `strict`。

**未裁决项：** Production 的 Quick 流程是否构成下限例外。§5.3 允许 Quick，但未说明 Quick 下的 Review 档位。需要实现方查证后裁决，不得默认 Quick 可用 `lightweight`。

### 5.4 与目标模型的关系

这是「Production 改成可声明策略」的第一步，也是 change 2042 降级等价判据的前置——没有可切换的 Profile 开关，就无从降级。

但它**只做读取与下限**，不做行为分派。让门禁知道 Profile 与让门禁按 Profile 改变判定，是两件事，后者属于 change 2043 的门层合并。

## 6. 验收标准

1. 四个门禁脚本都能获取当前治理 Profile，来源为 `.agentic-framework/manifest.json` 的 `profile` 字段。
2. manifest 缺失时失败关闭，除非显式传入 `--governance-profile`。
3. manifest 的 `profile` 非法时失败关闭，不回退默认值。
4. 不存在「静默默认为 tooling」的分支，用检索证明。
5. `review_profile` 下限按 Profile 生效：`production` 下 `lightweight` 失败关闭。
6. Quick 流程是否为下限例外，已查证并裁决，有用例。
7. 除下限检查外，两轨的既有判定结果全部不变——全部活跃与归档 Change 逐一比对。
8. `scripts/install_agentic_framework.py` 逐字节未改动。
9. `MANIFEST_SCHEMA_VERSION` 未变更。
10. 本仓库自身（无 `.agentic-framework/`）的门禁调用路径已文档化，CI 与本地用法一致。
11. `python -m pytest scripts -q` 全量通过。
12. 按 md-zh 规范自检中文排版。

## 7. 知识影响

- `openspec/specs/backend/framework/install-agentic-framework/overview.md`：MODIFIED。记录 manifest 的 `profile` 字段现被门禁消费。
- `openspec/specs/backend/framework/quality-gates/overview.md`：MODIFIED。记录 `review_profile` 下限规则。
- `openspec/specs/backend/engineering/tech/framework-unification.md`：MODIFIED。记录这是 §3.2 条件 1 的部分举证。

## 8. 参考资料

- manifest 已含 profile：`scripts/install_agentic_framework.py:19,24,598,607-609`
- 门禁不读 manifest：`validate_change.py`／`workflow_control.py`／`lint_task_deps.py` 中 `manifest` 出现 0 次；`check_delivery.py:211,795` 的两处是 `run_manifest_evidence_graph`
- Review Profile 取值集合：`skills/workflow-code-generation/scripts/lint_task_deps.py:37`
- Production Review 规则：`openspec/specs/backend/engineering/tech/framework-unification.md:179`、`:188`（§5.3）
- Tooling Review 规则：同文件 `:253-256`（§6.3）
- 收敛条件 1：change 2036 引入的 §3.2 重新评估条件
- 降级等价判据消费方：`openspec/changes/2042-downgrade-equivalence-harness/proposal.md`
