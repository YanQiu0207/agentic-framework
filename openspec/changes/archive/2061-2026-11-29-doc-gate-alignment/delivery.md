# 交付说明：2061 文档模板与校验脚本对齐

## 提交文件清单

| 路径 | 状态 | 用途 |
| --- | --- | --- |
| `scripts/validate_change.py` | 修改 | 无长期知识影响时豁免 OPSX018；无 Delta 时 OPSX029 不要求映射 Delta |
| `scripts/tests/test_validate_change.py` | 修改 | 3 个复现测试 |
| `scripts/native_subject.py` | 修改 | 删除 `verify_config_missing` 覆盖限制 |
| `scripts/test_native_subject.py` | 修改 | 复现测试 + 1 个断言翻转 |
| `skills/workflow-verification/scripts/test_verify.py` | 修改 | 无配置 Verify 断言翻转为 PASS |
| `scripts/validate_shared_knowledge.py` | 修改 | 允许 `superseded`，校验 `superseded_by` |
| `scripts/test_validate_shared_knowledge.py` | 修改 | 复现测试 |
| `skills/project-knowledge/reference/knowledge-advanced.md` | 修改 | 写明五个状态合法值 |
| `skills/workflow-code-generation/reference/task_planning_guide.md` | 修改 | 新增「Production 追加字段」 |
| `skills/workflow-system-design/SKILL.md` | 修改 | 前置条件与设计完成前接入 `lint_spec` |
| `skills/workflow-code-generation/SKILL.md` | 修改 | 步骤 2 接入 `lint_spec` |
| `docs/tooling/08-evaluation-strategy.md` | 修改 | 挂点描述对齐 |
| `skills/workflow-verification/evaluation/trigger-cases.md` | 修改 | S-4 预期随新行为翻转 |
| `openspec/changes/2061-doc-gate-alignment/` | 新增 | proposal、tasks、Delta、本交付说明，随 Change 归档 |
| `E:/work/shared-knowledge-base/index.md` | 修改（外部仓库，未提交） | 写入规则补状态合法值 |

不应提交：根目录未跟踪文件 `1`（来源不明，不纳入）。

## QA 测试点

- Standard 无知识影响无 Delta → plan 门 PASS；有影响无 Delta → OPSX018。
- 无 Verify 配置 → 主体完整、Verify PASS；补配置 → `subject_id` 改变。
- `superseded` + `superseded_by` 通过；缺 `superseded_by` 报错。
- 指南 Production 样例 → `validate_change --phase plan --governance-profile production` PASS。

## 审核顺序

1. `validate_change.py`：`NO_KNOWLEDGE_IMPACT_RE`／`_declares_no_knowledge_impact` 与 OPSX043 共用判定、`_has_delta`、OPSX018／029 条件。
2. `native_subject.py`：只删限制分支，entries 与 `config_sha256` 不变。
3. `validate_shared_knowledge.py`：允许值与 `superseded_by` 校验。
4. 测试文件：复现测试先于实现失败。
5. 文档：指南新增小节、两个 SKILL.md 各一处新增、08 文档一句。
