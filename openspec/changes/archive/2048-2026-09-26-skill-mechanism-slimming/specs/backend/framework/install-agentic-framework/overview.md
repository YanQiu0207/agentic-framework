# 安装能力选择 Delta

## ADDED

- `runtime` 与 `knowledge-advanced` 为可选能力标记，属于入口控制，不承诺物理文件隔离。
- `scripts/framework_packs.py` 提供能力查询；缺失或非法安装清单失败关闭。源码例外仅适用于当前执行模块的真实框架根，且不能绕过祖先非法清单。
- `--show-packs <project>` 只读返回能力，不执行目标 Manifest 的 `source`。

## MODIFIED

- 新安装默认核心；重装继承已选能力，`--with` 增量启用，`--without` 显式移除。
- 新清单写 `pack_selection_version: 1`；无该字段的旧清单保留此前默认拥有的 Runtime 和高级知识能力。

同步目标：`openspec/specs/backend/framework/install-agentic-framework/overview.md`。
