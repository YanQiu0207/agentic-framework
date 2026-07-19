# 框架安装器概览

安装器根据 `production` 或 `tooling` Profile 选择 Shared Core 和生命周期资产，为 Codex、Claude Code 创建受管链接，并使用 Manifest 与用户级 Registry 跟踪安装关系。

当前两个 Profile 都安装 `project-init` 和 `project-knowledge`；Profile 只决定执行生命周期，不决定项目知识 Artifact 目录。

`project-init` 必须在项目根 `.gitignore` 中补充 `.agentic-framework/`，统一排除 `verify/`、`locks/`、`metrics/` 和 `runs/` 等本地运行产物；OpenSpec、Schema、代码、测试、`verify.config.json` 和正式文档仍由 Git 管理。

当前实现仍以 `scripts/install_agentic_framework.py` 和安装测试为准。本文件只用于定位。
