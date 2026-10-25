# Change 2054 验证记录

## 环境与范围

- 基线：`1d7fb1d`；独立分支 `codex/deep-module-architecture`，未带入主工作区未提交改动。
- Native Delivery，现有 `verify.config.json` 未修改。初次采基线缺少 `grep`／`true`；仅当前进程 PATH 加入 Git `usr/bin` 后成功采集原基线。
- Overlay 查询返回 `Overlay validation requires a v3 installation manifest`：框架源码 worktree 无安装 Manifest，未加载 Overlay，未按目标 Manifest 执行任何外部路径。

## 首次阶段的确定性检查（历史记录）

| 检查 | 实际结果 |
| --- | --- |
| 新增安装测试，修复前 | 缺安装选择，出现红灯 |
| 新增安装测试，接线后 | 2 passed、1 skipped |
| 安装器与引用图定向回归 | 35 passed、22 skipped |
| Skill 引用图 | 28 skills、15 commands、8 agents，0 errors、0 warnings |
| Black 新测试，80 列 | 通过 |
| tasks DAG 与必填字段 | 4 tasks，0 errors、0 warnings |
| CP936 父进程，显式 UTF-8 子进程与 UTF-8 捕获 | 新增测试 2 passed、1 skipped；用户中文内容断言通过 |
| 原配置全量 Verify | FAIL；787 passed、25 skipped、7 failed、17 errors |
| spec drift | PASS；两处 Python 变更已由当前规格关联 |
| 测试数 | 755，原基线 752，未减少 |

实际命令：

```text
python -m pytest scripts/test_architecture_improvement_installation.py scripts/test_install_agentic_framework.py scripts/test_lint_skill_graph.py -q
python scripts/lint_skill_graph.py
python -m black --check --line-length 80 scripts/test_architecture_improvement_installation.py
python skills/workflow-code-generation/scripts/lint_task_deps.py openspec/changes/2054-deep-module-architecture/tasks.md
python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base 1d7fb1d
python -m pytest scripts -q --tb=short --lf
```

所有正常 Python 调用设置 `PYTHONUTF8=1`、`PYTHONIOENCODING=utf-8`；CP936 演练特意以 GBK 父进程启动，子进程恢复两项 UTF-8 设置，并以 `encoding="utf-8"` 捕获。

## 首次阶段的环境限制（历史记录）

- `where.exe svn`、`where.exe svnadmin` 均未找到命令。失败复跑中 SVN fixtures 调用 `svnadmin create` 报 `FileNotFoundError: [WinError 2]`。
- `scripts/test_native_subject.py::test_symlink_content_and_external_limitations` 报 `WinError 1314`，当前进程无符号链接创建权限。
- 新增真实安装—刷新—卸载测试因此跳过；选择、来源、受管路径及用户命令冲突保护不依赖该权限，已实际通过。不能据此声称真实生命周期已经验证。
- 原全量失败复跑结果仍为 7 failed、17 errors，均落在上述缺命令或缺权限路径。本次未修改这些既有测试源码，不安装 SVN、不改变系统权限、不降低配置。
- 原 Verify 另有既有框架知识来源版本滞后警告，未为通过本 Change 重写无关元数据。
- 机器报告位于 `.agentic-framework/verify/report.json`，失败复跑日志位于 `.agentic-framework/verify/last-failed.log`。最终 Review 位于 `.agentic-framework/review/`，只由独立审查方生成。
- 需在具备 SVN 工具和符号链接权限的环境重跑原配置；当前不归档、不宣称正式交付通过。
- 首次交付门还发现知识同步使用了散文，未被同步表解析器识别；已补标准同步表，并直接核对知识门。该修正不改变功能与测试范围，按修复 Diff 定向复审，不重新启动全量首审。

## 独立行为演练

独立子 Agent `/root/behavior` 读取实际 Skill 与参考方法，在无写入的模拟输入上执行，共 7 个场景；结论仅证明本次输出符合预期，不是跨模型稳定性评测。

| 输入 | 实际决策／回复摘要 | 副作用 |
| --- | --- | --- |
| 原样转发但承担旧客户端兼容的 OrderFacade | 保留并核实兼容职责，不机械删除包装 | 无 |
| 接口 40 行、实现 1000 行的单一订单用例 | 不凭行数拆分，需要接口知识与变化证据 | 无 |
| 一个 execute 混合权限、订单、邮件 | 优先调查职责混杂，按变化原因与所有权分解 | 无 |
| 用户选中候选并要求继续细聊 | 只讨论约束、迁移和测试，明确选择不等于实施授权 | 无 |
| 批准取消退款，而实现拒绝已付款订单 | 向编排方报告冲突，不把当前行为固化为测试预期，也不在无人值守任务中等待用户 | 无 |
| 无版本历史且无范围 | 说明不能可靠定位热点，请用户圈定范围，不全库扫描 | 无 |
| 六个调用者重复协调定价、库存、扣款与补偿 | 考虑收拢完整行为，保留内部职责，不继续盲目拆小 | 无 |
| 无任何隔离或兼容价值的原样包装 | 仅推演删除检验，先核实调用与迁移成本，不实际删除 | 无 |
| 已批准接点、范围及契约完全未变 | 复用批准推进内嵌测试，不重复确认，不另启动 task Review | 演练无写入；真实任务允许原授权范围内生成与运行测试 |

其中首轮订单检查包含三个模块判断，追加演练覆盖碎片化、无价值包装与批准复用。未使用完整生产仓库做效果对照；无热点历史演练、真实决策冲突和保存报告场景仍列在评估用例中，不能视为均已实际执行。

## 知识与决策

- 架构决策：未新增高影响运行时架构，未命中。
- 放弃方案：命中，未建立平行方法 Skill、HTML 报告与平行知识目录；理由已写入 proposal.md §2.2 及长期知识「维护决策」。
- 新增约束：命中，只读调查、选择不等于授权、不绕过既有批准与交付；已写入新 Skill 和长期知识。
- 长期知识已从根索引接线；历史 Matt 研究保留为候选记录，不伪装为当前实现。无已发现且未裁决的知识冲突。

## 恢复验证（2026-10-25）

- 用户授权补装现有 TortoiseSVN 的 CLI 组件，未升级原软件；`svn`、`svnadmin`、`svnserve` 实测均为 1.14.3。当前进程 PATH 显式加入 TortoiseSVN 和 Git 的工具目录。
- PowerShell 与 Python 符号链接探针均通过；新增安装回归 3 passed，真实安装—刷新—卸载不再跳过。初始环境失败保留为历史，不代表恢复后的现状。
- 使用原 300 秒配置的恢复 Verify 超时，报告为 ERROR，不能当作测试通过；日志还报告清理不完整，随后进程查询未发现仍在运行的 pytest／svnserve。未修改清理代码或隐藏该信号。
- 独立执行 `python -m pytest scripts -q --tb=short --durations=12`：836 passed in 257.36s，退出码为 0。此项是完整测试结果，不等于正式交付门结果。
- 用户明确批准配置维护：仅将全量测试 `timeout_seconds` 从 300 调为 600；其余配置保持不变。未删测试、改断言、扩大排除或重采基线。
- 原基线 SHA256 为 `343CA73E8994BBD28D02EAC5B3735F756BEBA3BBA10EB43E3412102803F5BFDD`，恢复期间继续使用该文件。
- 恢复日志：`.agentic-framework/verify/resume-verify.log`、`resume-full-pytest.log`。接下来以更新后的配置执行正式 Verify，未完成前不归档或宣称交付通过。
