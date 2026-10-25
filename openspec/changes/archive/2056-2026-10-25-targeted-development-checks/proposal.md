# Proposal: 区分开发定向检查与正式完整 Verify

**作者**：Codex
**日期**：2026-10-25
**变更**：2056-targeted-development-checks
**状态**：Archived

---

## 1. 背景

### 1.1 问题描述

- 开发与修复循环需要快速反馈，但执行指引没有统一区分定向检查与正式完整 Verify，容易把每次修改都升级为完整验证。
- 本次只调整执行指引，减少可避免的重复验证，不降低正式质量门要求。

### 1.2 现状分析

- `skills/workflow-verification/SKILL.md` 定义配置驱动验证、基线及正式报告合同，尚未单独定义开发定向检查。
- `skills/workflow-code-generation/reference/delegated-execution-guide.md` 要求任务运行 verification 与 workflow-verification，并以正式报告推进 `quality_passed`。
- `skills/workflow-code-generation/reference/delivery-guide.md` 在完整机器验证之后仍有 Review、知识同步等步骤；应提前完成可确定的文档准备，但不能豁免后续主体变化引发的重验。

### 1.3 主要使用场景

- 主会话及子 Agent 的开发、失败修复、任务质量门和正式交付准备。

## 2. 目标

- 统一两类检查的用途、触发时机和证据效力。
- 开发循环优先运行已有相关测试，正式任务质量门及交付仍执行完整 Verify。
- 完整验证前先收口可确定的结构和文档内容。

### 2.1 非目标

- 不修改 `verify.py`、`verify.config.json`、测试用例、报告 Schema、内容指纹或交付门。
- 不新增缓存、自动测试选择器或局部 PASS 报告。
- 不处理 VCS 子进程开销，不承诺具体提速比例。

## 3. 需求概览

### 3.1 功能性需求

- 仅调整用户指定的 4 份执行指引，具体位置和动作见 `design.md`。
- 定向测试直接使用已有 pytest 文件路径或用例 nodeid，仅提供开发反馈。
- 定向检查不能替代任务质量门、`quality_passed` 或正式交付凭证。

### 3.2 非功能性需求

- 分类定义只在 workflow-verification 主入口维护，其余指引引用，不复制多套规则。
- 保留基线采集、配置冻结、失败停止、完整覆盖、主体绑定及报告有效性要求。
- 此次为执行行为调整，不是纯措辞精简，也不是验证降级。

### 3.3 验收标准

- 4 份指引不存在「每次修改都必须完整 Verify」或「定向结果可以正式放行」的歧义。
- 子 Agent 开发反馈和任务正式质量门明确分开。
- 正式验证前有快速结构检查与文档收口动作；验证后主体变化仍按原合同重验。
- `git diff --check` 和 Skill 图检查通过，禁改文件没有 Diff。
- 审批前仅准备文档；老板已于 2026-10-25 批准实施，并追加要求完成 Change、合并主分支、提交推送及刷新本地安装。正式交付执行完整 Verify 与 Review。

## 4. 知识影响

- 本次执行策略的唯一维护来源是指定的 Skill 与参考文档；不改变长期 Specs 中的机器门禁合同，因此不创建长期 Spec Delta。
- 不新增业务领域模型或跨项目公共知识；审批后在 Change 中保留执行与检查记录。

## 5. 参考资料

- 用户本轮指定的四文件方案与禁止修改范围。
- `skills/workflow-verification/SKILL.md`。
- `skills/workflow-code-generation/SKILL.md`。
- `skills/workflow-code-generation/reference/delegated-execution-guide.md`。
- `skills/workflow-code-generation/reference/delivery-guide.md`。
- `openspec/specs/backend/framework/quality-gates/overview.md`（现行质量门与 Verification 合同）。
