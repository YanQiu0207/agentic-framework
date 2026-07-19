# 框架安装器接口

主要 CLI 输入：

- `target_dir`：目标项目目录。
- `--profile production|tooling`：选择唯一生命周期。
- `--with <pack>`：追加可选 Pack。
- `--switch-profile`、`--refresh-all`、`--uninstall`：切换、刷新和卸载受管资产。

详细参数、退出行为和安全检查必须回到 `scripts/install_agentic_framework.py:parse_args()` 核实。
