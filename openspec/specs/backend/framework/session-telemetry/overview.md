# 会话 Telemetry 概览

## 定位

Telemetry 是显式安装的可选 Pack。当前只实现 transcript 后处理：读取 Claude Code 或 Codex 已落盘的 JSONL 会话，不注入运行时 Hook，也不主动采集新数据。

安装器只把 `scripts/analyze_session_metrics.py` 链接到目标的 `.agentic-framework/packs/telemetry/`；它不增加 Skill 或 Command（`scripts/install_agentic_framework.py:82-99,352-363`）。

## 输入与识别

- Claude Code：读取项目会话 JSONL，并可补充伴生的 Subagent 转录。
- Codex：递归读取 `rollout-*.jsonl`，使用累计 Token 事件的相邻差分。
- 数据源根据合法 JSON 对象结构识别，不按文件名猜测（`scripts/analyze_session_metrics.py:384-403`）。
- `--cwd` 使用会话元数据做项目过滤；缺少早期元数据时先保留，再在完整解析后复核（`scripts/analyze_session_metrics.py:406-434,817-851`）。

## 指标合同

脚本输出：

- 阶段活跃时长与请求数。
- Input、Output、Cache Read 和 Cache Write Token。
- Claude Code Subagent 类型和成本归因。
- Review 轨迹、修复循环、复审新增 P0/P1、需人工和未收敛循环。
- Feature、Task、Review/Verify 重试和人工介入归因。

阶段边界依赖独占行的 `Using <skill-name>` 标记；Review 指标依赖 `workflow-code-review` 的标题、结论、轮次和 Finding 编号格式（`scripts/analyze_session_metrics.py:51-72`）。这些 Markdown 字段属于机器接口，修改时必须同步解析器和测试。

## 输出与恢复

- 默认打印人类可读报告。
- `--json` 写机器可读结果。
- `--history` 按 `(source, session)` Upsert JSONL 账本。
- 历史账本通过临时文件、`fsync` 和 `os.replace` 原子替换；无法解析的旧行原样保留（`scripts/analyze_session_metrics.py:720-778`）。
- 单个损坏会话会被隔离并跳过，不终止整批；全部无匹配结果时返回非 0（`scripts/analyze_session_metrics.py:832-872`）。

## 限制

- CLI 会话格式不是本框架控制的稳定 API，客户端升级可能要求适配。
- Codex 没有独立 Subagent 转录时，无法精确拆分 Subagent 成本。
- 阶段标记缺失会归入「未标记」，指标不能反向证明工作流一定未执行。
- 成本费率由外部 JSON 提供，脚本不内置可能过期的价格。

主要回归证据位于 `scripts/test_analyze_session_metrics.py`，覆盖数据源健壮性、CWD 过滤、Review 循环、任务归因和账本原子更新。
