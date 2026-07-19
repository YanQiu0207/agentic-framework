# 实施任务清单

> 由 spec.md 生成
> 任务总数：3
> 核心原则：先建立链接与 Registry 契约，再更新使用文档，最后执行整体验证。

## 依赖关系总览

```text
Task 1（实现链接式安装器与自动化测试）
  ↓
Task 2（更新安装和功能文档）
  ↓
Task 3（执行整体质量验证）
```

## 变更影响概览

### 文件变更清单

| 文件 | 操作 | 涉及任务 | 说明 |
| --- | --- | --- | --- |
| `scripts/install_agentic_framework.py` | 修改 | Task 1 | 从文件复制改为软连接，增加 Registry 和 `--refresh-all` |
| `scripts/test_install_agentic_framework.py` | 修改 | Task 1 | 覆盖链接、登记、刷新、升级和卸载行为 |
| `README.md` | 修改 | Task 2 | 更新安装、刷新、限制和故障处理说明 |
| `docs/framework-features-status-and-comparison.md` | 修改 | Task 2 | 同步安装机制和成熟度说明 |
| `docs/design-docs/framework/link-based-installation/spec.md` | 修改 | Task 3 | 完成后归档设计 |
| `docs/design-docs/framework/link-based-installation/tasks.md` | 修改 | Task 1～3 | 记录任务执行状态和验证证据 |
| `docs/adr/001-use-symlink-based-installation.md` | 新建 | Task 3 | 沉淀从复制切换到软连接的架构决策与权衡 |

### 受影响接口

| 接口 | 变更类型 | 调用方 | 涉及任务 |
| --- | --- | --- | --- |
| `parse_args()` | CLI 扩展 | 命令行用户、测试 | Task 1 |
| `install()` | 行为和可选参数变更 | `main()`、测试 | Task 1 |
| `uninstall()` | Registry 清理扩展 | `main()`、测试 | Task 1 |
| `refresh_all()` | 新增 | `main()`、测试 | Task 1 |

### 构建系统变更

- 无构建系统变更；继续使用现有 Python 和 Pytest 验证入口。

## 风险与假设

| # | 描述 | 影响任务 | 假设/处理 |
| --- | --- | --- | --- |
| 1 | Windows 软连接权限可能不可用 | Task 1、2 | 预检后明确失败，不回退复制；文档说明开发人员模式或权限要求 |
| 2 | 旧版 Manifest 记录的是复制文件 | Task 1 | 保留 Schema 1 读取、校验、升级和卸载兼容逻辑 |
| 3 | Registry 可能包含已删除目标 | Task 1、2 | `--refresh-all` 逐项报告失败并返回非零，不静默删登记 |
| 4 | 仓库没有 `verify.config.json` | Task 3 | 使用 Pytest、Black 和 Skill 图脚本完成机器验证 |

## 任务列表

### 任务 1: [x] 实现链接式安装、全局登记和批量刷新

- 状态：完成
- 文件：`scripts/install_agentic_framework.py`（修改）、`scripts/test_install_agentic_framework.py`（修改）、`docs/design-docs/framework/link-based-installation/tasks.md`（修改）
- depends_on: []
- review_profile: standard
- spec 映射：1、2.1～2.5、3
- 说明：以测试驱动方式把受管资产改为软连接，增加用户级 Registry 和 `--refresh-all`，并保持旧 Manifest 的安全升级与卸载能力。
- context_files:
    - `scripts/install_agentic_framework.py:build_operations()` — 当前安装选择和复制操作生成逻辑
    - `scripts/install_agentic_framework.py:install()` — 当前安装事务、Manifest 和 Profile 隔离逻辑
    - `scripts/install_agentic_framework.py:uninstall()` — 当前安全卸载与回滚逻辑
    - `scripts/install_agentic_framework.py:main()` — CLI 路由入口
    - `scripts/test_install_agentic_framework.py:InstallTest` — 现有安装安全回归测试
- verification:
    - [x] `python -m pytest -q scripts/test_install_agentic_framework.py` 全部通过（Windows：9 项通过，14 项因当前未授予软连接权限而跳过；WSL：22 项通过，1 项 Windows Junction 专项跳过）
    - [x] 测试证明已有源文件内容更新可经链接立即读取
    - [x] 测试证明 `--refresh-all` 能刷新多个登记目标和清理退役链接
    - [x] 测试证明卸载不会删除源文件或项目自有文件
- artifacts:
    - `scripts/install_agentic_framework.py`
    - `scripts/test_install_agentic_framework.py`
    - `docs/design-docs/framework/link-based-installation/tasks.md`
- 子任务:
    - [x] 1.1：先补链接、Registry、刷新和兼容性失败测试
    - [x] 1.2：实现最小链接事务、Manifest Schema 和 Registry 接口
    - [x] 1.3：实现 `--refresh-all` CLI 路由和逐目标错误汇总
    - [x] 1.4：运行安装器测试并修复回归

### 任务 2: [x] 更新安装与功能文档

- 状态：完成
- 文件：`README.md`（修改）、`docs/framework-features-status-and-comparison.md`（修改）、`docs/design-docs/framework/link-based-installation/tasks.md`（修改）
- depends_on: [Task 1]
- review_profile: lightweight
- spec 映射：1、2.3～2.5、3
- 说明：让快速开始、更新、卸载、Windows 权限和自动生效边界与真实实现一致。
- context_files:
    - `README.md:快速开始` — 用户安装主入口
    - `docs/framework-features-status-and-comparison.md` — 框架特性与成熟度总览
    - `scripts/install_agentic_framework.py:parse_args()` — 文档命令的真实 CLI 契约
- verification:
    - [x] `Select-String -Path README.md,docs/framework-features-status-and-comparison.md -Pattern '文件复制'` 无过时结论
    - [x] README 同时说明即时内容更新与需要 `--refresh-all` 的拓扑更新
    - [x] 中文 Markdown 按 `md-zh` 规则自检
- artifacts:
    - `README.md`
    - `docs/framework-features-status-and-comparison.md`
    - `docs/design-docs/framework/link-based-installation/tasks.md`
- 子任务:
    - [x] 2.1：更新 README 安装、更新、刷新和卸载说明
    - [x] 2.2：更新功能成熟度文档中的安装机制与限制
    - [x] 2.3：执行过时措辞扫描和 Markdown 自检

### 任务 3: [x] 执行整体质量验证并归档设计

- 状态：完成
- 文件：`docs/design-docs/framework/link-based-installation/spec.md`（修改）、`docs/design-docs/framework/link-based-installation/tasks.md`（修改）、`docs/adr/001-use-symlink-based-installation.md`（新建）
- depends_on: [Task 2]
- review_profile: standard
- spec 映射：1 验收标准、3
- 说明：执行完整机器验证、Skill 图检查和最终代码审查，记录结果后归档 Quick Draft。
- context_files:
    - `scripts/install_agentic_framework.py` — 最终实现
    - `scripts/test_install_agentic_framework.py` — 安装器专项测试
    - `scripts/lint_skill_graph.py` — Skill 图验证入口
    - `docs/design-docs/framework/link-based-installation/spec.md` — 归档目标
- verification:
    - [x] `black --check scripts/` 通过
    - [x] `python -m pytest -q` 全部通过（124 项通过，15 项因当前 Windows 环境未授予软连接权限而跳过，另有 28 项子测试通过）
    - [x] `python scripts/lint_skill_graph.py` 无悬挂节点或环
    - [x] `git diff --check` 通过
- artifacts:
    - `docs/design-docs/framework/link-based-installation/spec.md`
    - `docs/design-docs/framework/link-based-installation/tasks.md`
    - `docs/adr/001-use-symlink-based-installation.md`
    - 终端验证记录
- 子任务:
    - [x] 3.1：运行 Black、Pytest、Skill 图和 diff 检查
    - [x] 3.2：执行一次最终代码审查，仅修复本次范围内问题；复审第 1 轮结论为 PASS
    - [x] 3.3：完成 intent 沉淀检查，把决策写入 ADR，并将 Spec 状态改为 Archived

## Spec 覆盖映射

| Spec 章节 | 任务 | 说明 |
| --- | --- | --- |
| 1. 问题与目标 | Task 1、2、3 | 实现功能、说明边界并验证验收标准 |
| 2.1～2.4 方案与数据模型 | Task 1 | 实现链接事务、Manifest、Registry 和刷新接口 |
| 2.5 关键权衡 | Task 1、2 | 在实现和文档中保留隔离、安全与更新边界 |
| 3. 运维 | Task 1、2、3 | 提供命令、错误报告和最终验证证据 |
