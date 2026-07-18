# 会话遥测本地账本

`session-history.jsonl` 由 `scripts/analyze_session_metrics.py` 在本地生成，可能包含工作目录、会话 ID 和 Token 使用数据，因此不会提交到仓库。

需要遥测时显式安装 `telemetry` Pack；安装器只分发分析脚本，不分发任何现有会话数据。
