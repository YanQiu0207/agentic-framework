# Runtime Schema 合同

本目录保存 Workflow、Verification、Review、Evaluation 与 Harness Adapter 共用的版本化 JSON Schema。它是受 Git 管理的仓库顶层合同目录；本机运行产物写入已忽略的 `.agentic-framework/`。

## 版本与迁移

- 第一版 `schema_version` 固定为 `1`，未知版本失败关闭。
- 兼容性新增字段应先在对应 Payload Schema 中声明为可选字段。
- 删除、改名、改变字段语义或收紧现有取值时，必须新增 Schema 版本和迁移器；不得原地改写历史 Artifact。
- 同一 Task 重试必须生成新的 `artifact_id`；不得覆盖旧 Artifact。

## `config_digest`

`config_digest` 是完整 `run-config.json` 的规范化 UTF-8 JSON 字节的 SHA-256，格式为 `sha256:<64 位小写十六进制>`。规范化序列化固定使用按键名字典序、无多余空白且不转义非 ASCII 字符的 JSON。

`run-config.json` 只包含以下字段：

- `profile`
- `harness`
- `workflow`
- `max_attempts`
- 解析后的仓库根 `verify.config.json`；文件不存在时固定为 `{"checks": []}`

`AGENTS.md`、Skill、输入 Spec、Task 计划和 Capability Matrix 快照是独立输入 Artifact，各自记录内容摘要，不并入 `config_digest`。
这些输入使用 `input-artifact.schema.json`，由 `input_type`、仓库相对路径和 `content_digest` 明确区分。

## Attempt 映射

Envelope 的 `attempt` 是从 `1` 开始的执行序号；`workflow_control.py` 的 `attempts` 是从 `0` 开始的已消费失败重试次数。映射固定为 `attempt = attempts + 1`。只有 `failure` 消费重试预算；`manual` 等其他控制事件不改变任一计数。

## 校验入口

```text
python scripts/runtime_schema.py validate <artifact.json>
python scripts/runtime_schema.py config-digest --profile tooling --harness codex --workflow workflow-code-generation --max-attempts 2 --verify-config verify.config.json
```

校验成功时输出 `PASS` 或摘要并返回 `0`；输入、版本或关联非法时失败关闭并返回 `1`。
