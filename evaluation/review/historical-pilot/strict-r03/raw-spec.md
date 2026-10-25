# spec-compliance 原始审查报告

- Agent ID：`/root/strict_r03_judge/spec`
- 角色：`spec-compliance-reviewer`
- Review Profile：`strict`
- 当前 Task：任务 1
- 审查文件：`r03/src/_pytest/logging.py`（来自 `input.files` 的完整源码）
- 依据：`scope.md`、`tasks.md` 及源码内接口契约；无外部设计。
- 只读工具调用数：5（含 1 次 `rtk --version`）。
- 候选数量：2。
- 未修改文件、执行被审源码、联网或读取其他 reviewer 意见。

## SPEC-1

- **title**：未配置全局日志级别时，`caplog.set_level()` 未恢复共享 handler 的级别，导致后续测试漏捕日志
- **file**：`r03/src/_pytest/logging.py`
- **line**：350–358（关联 433–437、676–684）
- **severity**：P1
- **trigger**：没有设置 `log_level`，测试 A 调用 `caplog.set_level(logging.ERROR)`；测试 B 不调整级别，产生正常应捕获的 WARNING 日志。
- **root_cause**：`set_level()` 同时修改 logger 和 capture handler 的级别，但 `_finalize()` 只恢复 logger，未保存或恢复 handler 的原级别。插件跨测试复用同一个 `caplog_handler`；全局级别为 `None` 时，`catching_logs.__enter__()` 不会重置其级别。
- **impact**：测试 A 结束后共享 handler 仍为 ERROR，测试 B 的 WARNING 日志被过滤，导致 `caplog.records`／`messages` 缺失记录，测试结果依赖前序测试，与承诺的测试结束恢复行为不符。
- **evidence**：
    - 422–431 行明确承诺捕获级别在测试结束恢复。
    - 433–437 行保存 logger 原值后，分别执行 `logger_obj.setLevel(level)` 和 `self.handler.setLevel(level)`。
    - 350–358 行终结处理仅遍历 `_initial_logger_levels` 恢复 logger。
    - 525–527 行只在插件初始化时创建 capture handler。
    - 296–299 行仅在 `self.level is not None` 时设置 handler 级别。
    - 328–330、676–684 行表明每阶段复用该 handler，而 `reset()` 仅重置列表与输出流。
- **建议**：保存第一次 `set_level()` 前的 handler 级别，并在 fixture 终结时恢复。
- **历史边界**：这是当前完整源码中的契约不一致，不声称由某次改动引入。

## SPEC-2

- **title**：调用 `caplog.clear()` 后替换记录列表却未更新阶段存储，导致 `get_records()` 返回清空前旧记录并遗漏后续日志
- **file**：`r03/src/_pytest/logging.py`
- **line**：418–420（关联 328–330、379、683）
- **severity**：P1
- **trigger**：测试 call 阶段记录日志 A，调用 `caplog.clear()`，再记录日志 B，然后调用 `caplog.get_records("call")`；或在 teardown 中查询上述 call 阶段。
- **root_cause**：`_runtest_for()` 将阶段存储绑定到当前 `caplog_handler.records` 列表；`clear()` 调用 `reset()` 将 handler 的列表替换为新对象，但阶段存储仍引用旧列表。
- **impact**：`caplog.records` 反映日志 B，而 `get_records("call")` 仍返回日志 A、遗漏 B。公开的阶段记录查询不再反映该阶段当前捕获记录，影响阶段日志断言。
- **evidence**：
    - 367–379 行承诺并实现从阶段存储返回指定阶段捕获记录。
    - 418–420 行 `clear()` 契约为重置记录列表及文本，实际调用 `self.handler.reset()`。
    - 328–330 行 `reset()` 使用 `self.records = []`，并非原列表就地清空。
    - 683 行 `item._store[caplog_records_key][when] = caplog_handler.records` 仅在阶段开始绑定一次。
    - 323–326 行后续记录追加到 handler 当前的新列表。
    - 386–389 行 `records` 属性返回新列表，与阶段存储产生分歧。
- **建议**：使 `clear()` 保留阶段存储与当前记录列表的一致性，例如就地清空当前记录列表并单独重置文本流；阶段切换的 `reset()` 行为可保持独立。
- **历史边界**：这是当前完整源码中的接口自洽性问题，不声称属于回归。

## 审查限制

- 仅根据所提供完整源码进行静态推导，未运行复现。
- 无 diff、历史、调用方源码或测试，不能判断引入版本与外部兼容性。
- 未进行外部设计需求遗漏检测，也不提供整体集成放行结论。
