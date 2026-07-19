# 安装器人工约束

- 禁止把 Production 与 Tooling 生命周期入口默认混装；切换必须显式执行。
- 不覆盖目标项目自有文件；卸载只处理 Manifest 中经过安全校验的受管链接。
- `project-init` 与 `project-knowledge` 属于 Shared Core，两种 Profile 都必须安装。
- 链接失效时明确失败，不静默复制为普通文件。
- 修改安装器时必须同时运行安装测试和 Profile 合同测试。
