# Robustness 原始报告

- Reviewer：`/root/strict_r03_judge/robustness`（当前可见的实际 Agent 标识；未提供 UUID）
- 只读调用数：4。
- 范围：`input.files` 中完整的 `r03/src/_pytest/logging.py`。
- 已读取内嵌 workflow、robustness 角色和 `bp-coding-best-practices`。
- 方法：静态源码审查；未执行源码、联网、读取其他 reviewer 候选或访问范围外项目文件。

## Finding R03_ROB_01

- **title**：未配置日志级别时，`caplog.set_level()` 修改的共享 handler 未恢复，导致后续测试漏捕日志
- **file**：`r03/src/_pytest/logging.py`
- **line**：437
- **severity**：P1
- **trigger**：未设置 `--log-level`／`log_level`，第一个测试调用 `caplog.set_level(logging.ERROR)`；后续测试记录 `WARNING` 并通过 `caplog` 检查。
- **root_cause**：`set_level()` 同时修改 logger 与 handler，但只保存 logger 原值；`_finalize()` 也只恢复 logger。会话共享的 `caplog_handler` 因此保留 `ERROR` 阈值。下一测试的 `catching_logs(..., level=None)` 不重置 handler 的级别。
- **impact**：后续测试的 `WARNING` 日志仍可进入 report handler，却被 caplog handler 丢弃，产生与测试顺序有关的捕获结果和断言失败。
- **evidence**：
    - 423–424 行承诺级别在测试结束时恢复。
    - 435–437 行仅保存 logger 原值，却修改两处级别。
    - 350–358 行 `_finalize()` 仅恢复 logger。
    - 525–529 行在插件实例上创建并复用两个 handler。
    - 298–299 行仅当 `level is not None` 时设置 handler 级别。
    - 676–684 行复用 handler；328–330 行 `reset()` 只重置记录与文本，不重置级别。
- **建议**：保存首次修改前的 handler 级别，并在 fixture finalize 时恢复。

## Finding R03_ROB_02

- **title**：并发日志跨两个 capture handler 共享可变 formatter，导致记录输出错误的级别名称
- **file**：`r03/src/_pytest/logging.py`
- **line**：88
- **severity**：P1
- **trigger**：启用包含 `%(levelname)s` 的彩色 formatter，测试中两个线程分别记录不同级别日志；两个 capture handler 使用同一 formatter。
- **root_cause**：`ColoredLevelFormatter.format()` 先按当前记录修改共享 `_style._fmt`，随后才调用基类格式化。两个 handler 各自的同步不能保护共同 formatter 的可变状态。
- **具体交错**：
    1. 线程 B 完成 `WARNING` 记录的 caplog handler 处理，进入 report handler。
    2. 线程 A 进入 caplog handler，处理 `ERROR`，在第 88 行写入 `ERROR` 格式后暂停。
    3. 线程 B 在 report handler 中将同一个 `_style._fmt` 写成 `WARNING` 格式。
    4. 线程 A 恢复，第 89 行及第 185 行读取已经覆盖的格式，将 `ERROR` 消息输出为 `WARNING`。
- **impact**：`caplog.text` 或失败报告中的日志级别名称和颜色可能不对应实际 `LogRecord.levelno`，并发测试的诊断内容不可靠。
- **evidence**：
    - 72–84 行把级别名称直接插入各级别格式字符串，而非保留记录动态取值。
    - 86–89 行修改共享格式后再格式化。
    - 185 行使用共享的 `self._fmt`。
    - 526–529 行明确让 `caplog_handler` 与 `report_handler` 共享 `self.formatter`。
    - 573–584 行展示彩色 formatter 的可达创建路径及 multiline style 安装。
- **建议**：避免格式化过程中修改共享 formatter 状态，或至少为两个 handler 创建独立 formatter。

## 限制

- 没有 diff／历史，以上仅认定当前源码缺陷，不声称由特定变更引入。
- 并发交错属于静态推导，未运行验证。
- 内嵌最佳实践所链接的额外 safety 文档不在允许读取范围内，未访问。
