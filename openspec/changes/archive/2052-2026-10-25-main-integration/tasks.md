# Main 整合任务

### 任务 1：[x] 整合远程合同与本地能力
- 状态：完成
- depends_on: []
- review_profile: strict
- context_files: [proposal.md]
- verification: pytest scripts 与独立严格审核
- artifacts: workflow_control.py、合同测试、活跃知识和执行指南

### 任务 2：[x] 修复边界问题与补齐跨平台验证
- 状态：完成
- depends_on: [Task 1]
- review_profile: strict
- context_files: [proposal.md]
- verification: 嵌套目录负向回归、Linux 全量测试、信任链及需求符合度定向复审
- artifacts: 嵌套目录防护、跨平台测试 fixture、验证与审核报告

交付动作：备份并恢复用户本地改动、快进 main、正常推送及核对远程 SHA；执行状态由会话和 Git 记录单独报告。
