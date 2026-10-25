# Runtime 重试与交付重放修复

**状态**：Archived

## 范围

用户要求修复 `openspec/issues/runtime-retry-and-delivery-replay.md` 中的真实故障，完成后合并至 main 并推送。旧 Run 保留，不修改历史时间、插入缺失事件或覆盖既有证据。main 的已跟踪未提交修改经用户授权可备份、暂存并在合并后恢复，未跟踪文件留在原处。

## 验收合同

1. Journal 追加前验证完整新前缀。错误 attempt、Run 绑定或事件顺序不得污染原日志。
2. Runtime 的 start、failure 和 quality_passed 使用真实当前 attempt 记账；失败消耗次数与 tasks.md 一致。Journal 成功而 tasks.md 更新中断时，同请求重试不能重复消费失败次数。
3. 失败 attempt 的状态快照保留，用于关联该轮 Verify 报告；快照记录失败事件发生前的运行状态，失败事实由 Journal 记录，不伪造该轮通过。
4. 交付可重跑：相同 Artifact 仅允许忽略生成时间后的语义一致复用，原字节不变；绑定、状态、payload 或源码快照冲突拒绝。
5. Finalization 串行化，已有 Manifest 不覆盖，仍执行完整 Trust Gate。不得用缓存 PASS 跳过证据验证。
6. 通过现有全量测试及新回归，独立 strict Review 后真实运行交付检查。旧的已损坏 Journal 不自动修复，不能以新 Run 成功冒充旧 Run 历史完好。
