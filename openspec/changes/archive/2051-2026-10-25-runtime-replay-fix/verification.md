# 修复验证记录

## 已完成

- 基准：`4026684`；修复：`d4bfdbf`；首审 F-1 修复：`4f322a7`。
- 先复现红灯：Journal 非法 attempt 没有立即报错；重复 Finalization 报 `artifact_already_exists:task-1-state`。新增断言均曾失败后通过。
- 连续失败两次、第三轮 Verify 成功及保留失败轮次证据的端到端回归通过。
- Journal 已落盘、tasks.md 写入中断后重试，不重复消耗 attempts。
- strict 首审真实执行五维与 Critic，结论 NEEDS_CHANGES，唯一 F-1 为首次快照非原子发布。修复后仅健壮性定向复审，独立 Judge 第 1 轮 PASS，P0/P1 均为 0。
- 相关测试 112 passed；全量测试 648 passed、22 skipped。真实任务 Verify、全局 Verify 使用原配置与基线，均 PASS；知识来源过期警告未隐藏。
- CP936 环境下设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`，Runtime 重试 CLI 回归 1 passed。
- 实际交付与同参数重跑均 `checks=8 | errors=0`，重跑前后 25 份证据字节不变，见 `evidence/delivery-replay.json`。

## 证据与限制

真实 Run 为 `.agentic-framework/runs/2051-runtime-replay-fix-r1/`，代码绑定 `4f322a7`。Judge 原样机器报告、两轮报告及 Verify 已复制到 `evidence/`。旧错误 Run 和初审 Run 均保留，没有补造历史事件。

两轮 Judge Markdown 曾因编码写成问号；Judge 已核验原字节并保留 `.encoding-damaged.md`，从原始完整载荷恢复 UTF-8，裁决不变。没有用残片重写或由实现者代写裁决。

未做真实断电测试；使用文件发布、文档写入及下游门故障注入。未声称修复任意外部损坏的旧 Journal。远程 Native v2 与本地 Pack／Fast-Path／Runtime 路由存在合并冲突，当前分支验证不等于合并结果验证。
