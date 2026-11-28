# Delta：§11 公共库证据等级增加 superseded

**状态**：Pending
**动作**：MODIFIED
**长期目标**：`openspec/specs/backend/engineering/tech/knowledge-management.md`

## 变更内容

### 1. §11 证据等级列表

在 `deprecated` 之后增加一项，并调整 `deprecated` 的释义，使两者互斥：

- `deprecated`：已失效，且没有指定的替代条目。
- `superseded`：已被指定的新条目取代，必须在 frontmatter 填写非空 `superseded_by` 指向替代条目。

列表后的「只有 `verified` 可以默认作为建议；其他状态必须同时说明限制」保持不变。

## 同步说明

- 机器校验同步：`scripts/validate_shared_knowledge.py` 的 `ALLOWED_STATUSES` 增加 `superseded`，并校验 `superseded_by`。
