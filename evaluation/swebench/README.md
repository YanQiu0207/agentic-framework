# SWE-bench Verified 自动评测

本目录通过 [`scripts/swebench_runner.py`](../../scripts/swebench_runner.py) 对接官方 SWE-bench Verified 评测器，用于补充框架本地路由测试，而不是替代它。

## 安全边界

默认命令只生成机器可读执行计划：不导入 `swebench`、不访问网络、不启动 Docker 或其他容器。只有显式传入 `--allow-container-execution` 时，Runner 才会调用官方 `swebench.harness.run_evaluation`；该步骤可能下载数据集、构建镜像并运行容器。

Runner 固定数据集为 `princeton-nlp/SWE-bench_Verified`，避免把不同 SWE-bench 变体混入同一轮对比。它不安装依赖；执行前由操作者在隔离环境安装官方 SWE-bench 及其运行前提。

每份 prediction JSONL 必须只包含本轮 `--instance-id` 指定的实例，且使用同一个 `model_name_or_path`。Runner 会记录 prediction 的 SHA-256；官方进程退出码为 0 后，仍要求每个选中实例在官方报告中同时是 completed 和 resolved，且没有 error／incomplete，否则失败关闭。

## 最小流程

先准备官方要求的 prediction JSONL，且只选择已审核的少量实例：

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
python scripts/swebench_runner.py `
    --predictions .agentic-framework/evaluation/predictions.jsonl `
    --instance-id sympy__sympy-20590 `
    --run-id native-first-pilot-001
```

上述命令只打印计划。确认实例、prediction 文件和隔离环境后，再显式允许容器执行：

```powershell
python scripts/swebench_runner.py `
    --predictions .agentic-framework/evaluation/predictions.jsonl `
    --instance-id sympy__sympy-20590 `
    --run-id native-first-pilot-001 `
    --allow-container-execution `
    --output .agentic-framework/evaluation/swebench-pilot-001.json
```

`--output` 拒绝覆盖既有 Artifact；每次运行应使用新的文件名。评测退出码、标准输出和错误输出会写入该 Artifact，供后续统计处理。

Windows 原生 Python 无法导入官方评测器依赖的 POSIX `resource` 模块。已启用 Docker Desktop 的 Windows 主机可显式传入 `--execution-host wsl-docker`：Runner 会通过 WSL 启动隔离的 Linux Python 容器，并将预测目录挂载为 `/work`。该模式仍需要 `--allow-container-execution`，会拉取 `python:3.11-slim`、安装固定的 `swebench==4.1.0`，并允许该容器经 Docker Socket 创建官方评测容器。

> **安全警告**：Docker Socket 等同 Docker 主机的高权限控制面。仅在专用评测机或隔离 Docker Daemon 上启用此模式；不要对不可信 prediction、镜像或网络环境授权。

```powershell
python scripts/swebench_runner.py `
    --predictions .agentic-framework/evaluation/predictions.jsonl `
    --instance-id sympy__sympy-20590 `
    --run-id native-first-pilot-001 `
    --allow-container-execution `
    --execution-host wsl-docker `
    --output .agentic-framework/evaluation/swebench-pilot-001.json
```

## 与本地 Fixture 的分工

- SWE-bench Verified：衡量真实 Issue 修复任务的端到端结果。
- [`evaluation/delivery-route-fixtures.json`](../delivery-route-fixtures.json)：在零网络、零容器条件下验证 Native Delivery 与 Runtime Run 的升级路由。

两类评测都不能单独证明所有结论。SWE-bench 不验证本框架的 Trust Gate 语义；路由 Fixture 也不衡量真实代码修复成功率。
