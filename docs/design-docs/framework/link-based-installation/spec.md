# Tool/Service: 链接式框架安装器

**作者**：Codex
**日期**：2026-07-19
**状态**：Archived

---

## 1. 问题与目标

### 问题

当前安装器把框架文件复制到目标项目。框架仓库更新后，已安装项目不会自动获得已有资产的内容更新，且需要逐项目重复执行安装命令。

### 目标

- 保留安装脚本作为唯一安装入口。
- 默认通过软连接安装选中的 Skill、Agent、Command 和脚本，不再复制框架内容。
- 在目标项目保留 Manifest，并在用户目录登记所有安装目标。
- 已有链接源的内容更新立即对目标项目生效。
- 通过 `--refresh-all` 一次刷新新增、删除、重命名资产及 Profile、Pack 安装拓扑。

### 非目标

- 不把整个 `.codex/` 或 `.claude/` 目录链接到框架仓库。
- 不让 Production 与 Tooling 绕过现有 Profile、Pack 隔离。
- 不在软连接创建失败时静默回退到文件复制。
- 不自动执行 `git pull`，框架仓库版本仍由用户控制。

### 验收标准

- 安装后的受管资产是指向框架仓库的软连接，修改已有源文件后目标项目立即可见。
- `%USERPROFILE%/.agentic-framework/installations.json` 记录源仓库、目标项目、Profile 和 Pack。
- `--refresh-all` 能刷新当前源仓库登记的全部目标，并清理不再选择的链接。
- 卸载只删除受管链接、目标 Manifest 和对应登记，不删除框架源文件或项目自有文件。
- 旧版复制式 Manifest 仍可安全升级或卸载。

---

## 2. 设计方案

### 2.1 整体方案

安装器把选中的 Skill 目录作为目录软连接安装，把 Agent、Command 和脚本作为文件软连接安装。目标 Manifest 记录链接路径、源路径和链接类型；用户级 Registry 记录安装位置和选择参数。普通源码内容更新沿链接直接生效，安装集合变化由 `--refresh-all` 重建链接拓扑。

### 2.2 核心组件

| 组件 | 职责 |
| --- | --- |
| 安装选择器 | 根据 Profile 和 Pack 生成明确的链接操作集合 |
| 链接事务 | 预检冲突，创建或替换受管链接，失败时恢复原安装 |
| 目标 Manifest | 记录受管链接及其预期源，支持安全重装和卸载 |
| 用户级 Registry | 记录源仓库与目标项目关系，为批量刷新提供输入 |
| 批量刷新器 | 读取 Registry，刷新当前源仓库登记的所有安装目标 |

### 2.3 主要接口/API

- `install(source, target, profile, packs, ..., registry_path=None)`：安装或更新一个目标并登记。
- `uninstall(source, target, ..., registry_path=None)`：安全卸载并移除登记。
- `refresh_all(source, ..., registry_path=None)`：刷新当前源仓库登记的全部目标。
- CLI 新增 `--refresh-all`；该模式不要求 `target_dir`，且不能与单目标安装参数混用。

### 2.4 数据模型

目标 Manifest 使用新 Schema 记录：

- `source`：框架仓库绝对路径。
- `profile`、`packs`：安装选择。
- `links[]`：目标相对路径、源绝对路径和 `file` / `directory` 类型。

用户级 Registry 记录：

- `source`：框架仓库绝对路径。
- `target`：目标项目绝对路径。
- `profile`、`packs`：刷新时复用的安装参数。

### 2.5 关键权衡

- 按资产创建链接而不是链接整个客户端目录，以保留 Profile、Pack 隔离和项目自有扩展空间。
- Skill 使用目录链接，使现有 Skill 内新增文件也能立即出现；新增 Skill、删除或重命名资产仍需 `--refresh-all`。
- 使用绝对链接，避免目标目录层级变化导致相对链接解析错误；代价是框架仓库移动后必须重新安装。
- 链接目标被本地编辑时等同于直接修改框架源文件，安装器无法把它识别为目标项目的独立副本；README 必须明确这一行为。
- Windows 无法创建软连接时明确失败，不静默复制，以避免用户误以为后续更新会自动生效。

---

## 3. 运维

| 项目 | 说明 |
| --- | --- |
| 部署方式 | 克隆框架仓库后，通过 Python 3 安装脚本为项目创建软连接 |
| 关键指标 | Registry 中的安装数量、刷新成功数和失败数 |
| 告警建议 | 链接权限不足、源仓库或目标项目缺失、链接被改指向时返回非零退出码 |
| 日志关键路径 | 单目标链接创建、Registry 更新、批量刷新逐目标结果 |

---

## 4. 参考资料

- `scripts/install_agentic_framework.py`
- `scripts/test_install_agentic_framework.py`
- `README.md`
- Microsoft Learn：CreateSymbolicLink API
