# 验证记录与证据边界

## 定向回归

- 实现前新增根定位、身份锁、CLI 作用域及链接嵌套边界回归出现预期失败，修复后通过。
- 首轮 `python -m pytest scripts/test_workflow_control.py -q`：113 passed，4.24 秒；严格审查新增两个边界回归先失败，修复后为 115 passed；原问题的多层链接回归再次先失败，最终定向为 116 passed，5.43 秒。
- `git diff --check`：退出码 0。
- 覆盖 `.git` 文件与目录、SVN 标记、无仓库回退、真实路径回退、中文空格 Junction、跨进程竞争、异常释放、CP936 父进程及 UTF-8 Python 子进程。复审新增整个项目根 Junction、知识目标本身受 Git／SVN 管理、多层知识链接及无所属项目回退矩阵。

## 真实 SVN 工作副本

- 命令：`python .agentic-framework/tools/2055/smoke_2055.py layered`。
- 结果：102 项断言通过，包含前轮 73 项重跑及 29 项多层链接断言。
- 真实本地仓库及工作副本：`E:/github/bak/2055-svn-junction-smoke-20261025/run-193732`，无 Git 祖先，使用 `svnadmin create` 与 `svn checkout` 创建。
- 完整记录：`.agentic-framework/verify/svn-smoke-2055-193732.json`，SHA-256 为 `f594969c1acfc8cca146f3e56bc2fa79ac0dadfef0235f194a757042dddd16f1`。
- 汇总：`.agentic-framework/verify/svn-smoke-2055-summary-193732.json`。
- 被测脚本 `skills/workflow-code-generation/scripts/workflow_control.py` 的 SHA-256 为 `204bb14fc916cc2c1fda2bf1b5efd0140b100f3d30634ad30873288bd2e8da74`，运行期间未变。
- 前轮 38／73 项及原快照记录保留在 `.agentic-framework/verify/svn-smoke-2055-192312.json` 和 `svn-smoke-2055-193425.json`，不替代最终快照证据。

已验证两工作副本各自配置与项目锁、共享真实身份锁、Native 路由、SVN 拒绝 Runtime、recover 只读、持锁超时正文逐字节不变、释放后写入成功，以及单独持有既有项目锁仍能阻止写入。Runtime 能力清单为合法结构 fixture，只验证检查作用域和拒绝发生在副作用之前，不冒充完整安装生命周期验收。

扩展场景将共享知识本身建为真实 SVN 工作副本，验证其 `.svn/wc.db` 不抢占所属项目作用域；再在知识目录内叠加任务目录 Junction，检查多层链接仍归属 owner，并重复跨进程互斥；另外验证整个 SVN 项目经根 Junction 别名访问。后者使用实际 `svn add/commit` 的正常受版本控制目录。初始未版本化目录触发既有 `svn info(task.parent)` 的 E200009，保留现场并修正测试 fixture，不声称支持未版本化任务父目录的全部命令。

## 未验证边界

- 本轮是本地 `file://` SVN，不是用户业务服务器；未验证远程认证、网络故障或业务项目完整交付。
- 本机 TortoiseSVN 1.14.3 对原生中文仓库路径创建出乱码目录；尝试多种 locale 后仍存在，因此仓库及工作副本采用 ASCII 路径。中文空格外置知识目录和逻辑任务路径已验证，不宣称中文工作副本路径已通过。失败现场与编码探针保留在隔离目录。
- 共享身份锁仅协调相同系统临时目录中的新版进程；不承诺跨用户、跨主机或新旧版混跑互斥。
- Windows Junction 已执行；本轮未额外运行 Linux 符号链接测试，不能用 Windows 结果替代该平台证据。

## 集成验证与审查

使用已有 `verify.config.json` 和实现前冻结的 `.agentic-framework/verify/baseline.json`。开发阶段运行定向测试；首轮正式验证与严格审查并行，审查发现边界问题后已主动中止旧快照的全量测试，原报告保留为 `.agentic-framework/verify/report-2055-initial-interrupted.json`，不将中止记为产品测试通过或失败。修复后先完成定向复审，再冻结最终快照集中运行配置驱动验证，命令如下，实际结果以机器报告为准：

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
python skills/workflow-verification/scripts/verify.py --baseline .agentic-framework/verify/baseline.json --diff-base ef57ed4821462c174819582dec90f1e0fc83f3bb
```

独立 v2 Verify 位于 `.agentic-framework/verify/report.json`；strict 集成 Review 位于 `.agentic-framework/review/2055/`，由未参与实现的 Judge 裁决；Native 最终裁决位于 `.agentic-framework/native-delivery/verdict.json`。不启用 Runtime，不声明 Harness 或 Trust Gate 证据。

首审两个 P1 为项目根 Junction 跳出作用域，以及知识目标仓库标记抢占所属项目根；经独立 Critic 确认后修复。第 1 轮定向复审确认首项关闭，但第二项多层链接仍未完全修复；第 2 轮需求与契约 Reviewer 独立验证最外侧链接修复及相邻边界，原问题已关闭。定向复审只核对原问题和修复 Diff，不重启首审。

## 交付前沉淀检查

- 架构决策命中：逻辑作用域与真实任务身份分离，已记录在 design.md 第 4～6、9 节及长期控制流概览。
- 放弃方案命中：只用项目锁不能协调共享真实任务；直接提升到外层仓库根会破坏嵌套 manifest，已记录在 design.md 第 5、9 节。
- 新增约束命中：固定锁序、统一超时、升级共享写入进程、明确临时目录协调边界，已同步长期概览。
