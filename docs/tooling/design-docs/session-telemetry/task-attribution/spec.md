# 会话遥测任务级归因

**作者**：Codex  
**日期**：2026-07-12  
**状态**：Archived

## 1. 问题与目标

### 问题

会话账本只能统计 review 轮次和质量结果，无法判断返工属于哪个 feature、task、风险档位或流程阶段。

### 目标

- 固定任务归因报告格式，作为遥测解析接口。
- 记录 feature、task、风险档位、review 重试次数、verify 重试次数和人工介入位置。
- 旧报告继续可解析，缺少归因信息时返回空列表，不填推测值。
- 用真实 review 会话验证轮次模板遵从率，并更新账本。

### 非目标

- 不引入 hooks 或 OTel。
- 不从非结构化对话推测任务归因。
- 不建立复杂的人工介入枚举体系。

### 验收标准

- 新格式可被 `analyze_session_metrics.py` 解析为 `task_attributions`。
- 同一会话内重复出现相同 feature/task 时保留最后一份归因记录。
- 旧格式解析结果保持兼容。
- 单元测试通过，真实会话写入账本后 review 轨迹带明确轮次。

## 2. 设计方案

### 2.1 整体方案

在 `workflow-code-generation` 的固定交付证据中增加「任务归因」区块；`workflow-code-review` 补齐 feature、task 和风险档位字段。遥测脚本只解析固定字段，将归因数据写入会话账本顶层的 `task_attributions`。

### 2.2 数据模型

每条任务归因包含：

- `feature`
- `task`
- `review_profile`
- `review_retries`
- `verify_retries`
- `manual_intervention`

`manual_intervention` 使用字符串列表；无人工介入时为空列表。旧会话缺少固定区块时，`task_attributions` 为空列表。

### 2.3 关键权衡

- 选择固定 Markdown 字段而非自然语言推断，保证「格式即接口」可测试。
- 归因放在交付报告而非每份 review 报告中，因为 verify 重试和人工介入只有交付阶段拥有完整信息。
- 保留 review 报告中的 feature、task 和风险档位，便于单份报告定位，但账本以交付归因区块为准。
- 不回填旧账本的未知值，避免把缺失数据伪装成事实。

## 3. 参考资料

- `docs/11-session-telemetry.md`
- `skills/workflow-code-review/SKILL.md`
- `skills/workflow-code-generation/SKILL.md`
