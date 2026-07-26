# 框架安装器概览

安装器根据 `production` 或 `tooling` Profile 选择 Shared Core 和生命周期资产，为 Codex、Claude Code 创建受管链接，并使用 Manifest 与用户级 Registry 跟踪安装关系。

当前两个 Profile 都安装 `project-init` 和 `project-knowledge`；Profile 只决定执行生命周期，不决定项目知识 Artifact 目录。

`project-init` 必须在项目根 `.gitignore` 中补充 `.agentic-framework/`，统一排除 `verify/`、`locks/`、`metrics/` 和 `runs/` 等本地运行产物；OpenSpec、Schema、代码、测试、`verify.config.json` 和正式文档仍由 Git 管理。

外部私有规范通过 Overlay 接入。Overlay 源根目录必须提供 `agentic-extension.json`，清单使用 `schema_version: 1`，声明唯一名称、Skill 的安全相对路径及适用文件后缀。安装器仅接受包含 `SKILL.md` 的目录，拒绝路径穿越、重复 Skill、核心或 Overlay 同名 Skill。

安装器为每个声明的 Overlay Skill 在 `.codex/skills/` 和 `.claude/skills/` 创建受管目录链接。目标项目的核心 Manifest 使用 schema v3，记录有序 Overlay 描述符（名称、来源、清单哈希、Skill 与链接快照）；每个 Overlay 的规则和链接独立记录在 `.agentic-framework/extensions/<name>.json`，并与描述符交叉校验。Registry 保存来源路径选择，供 `--refresh-all` 重新读取 Overlay。普通重装未传 `--extension` 时继承已登记选择；显式传入一个或多个 `--extension` 时替换选择。

旧 v2 链接式 Manifest 仍可读取，但 `--refresh-all` 要求先对目标项目显式重新安装，以升级为 v3。

刷新、重装和卸载都验证 Overlay 状态中的受管链接；链接被替换、清单无效、来源移动或与项目已有内容冲突时失败，不覆盖或删除项目自有文件。卸载只移除 Overlay 受管链接和状态，不删除 Overlay 源。Overlay 不能覆盖核心 Skill，也不能安装 Agent、Command、脚本或修改 workflow。

编码与测试 workflow 在开始前从当前已加载的核心 workflow `SKILL.md` 真实路径（解析链接后）向上定位受信框架根，运行 `python <framework-root>/scripts/install_agentic_framework.py --validate-extensions .`，并只消费其成功返回的 JSON。不得从目标项目 Manifest 的 `source` 获得可执行路径。只读校验严格核对 Manifest 描述符、Overlay 状态和实际客户端链接，并要求 Manifest 来源与当前安装器框架根一致；失败时 workflow 不加载 Overlay。成功后按 `skills[].files` 匹配目标文件后缀。该发现规则只补充规范，不自动执行 Overlay 内容，也不覆盖核心 workflow。

当前实现仍以 `scripts/install_agentic_framework.py` 和安装测试为准。本文件只用于定位。

## Manifest 的消费方（change 2041）

Manifest 的 `profile` 字段现被四个门禁脚本消费：`validate_change.py`、`check_delivery.py`、`lint_task_deps.py`（`workflow_control.py` 已接线参数，门层合并后消费）。读取由共享模块 `scripts/governance_profile.py` 承载：从被校验仓库根向上查找 `.agentic-framework/manifest.json`（祖先链上的安装会被继承），缺失或 `profile` 非法一律失败关闭，不静默回退默认值；`--governance-profile production|tooling` 显式覆盖优先。读取是惰性的——只在 `review_profile` 触及 Profile 下限时发生。框架实现仓库自身（本仓库）有 `.agentic-framework/` 运行目录但无 manifest，跑门禁经显式参数取得 Profile（见 `AGENTS.md`）。
