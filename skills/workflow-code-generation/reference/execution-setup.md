# 执行准备

由实现者加载扩展规范时读取「Overlay 规范发现」；委派任务前读取「任务执行」。

## Overlay 规范发现

实现者在编码或测试前，从当前已加载的核心 workflow `SKILL.md` 真实路径（必须解析目录链接和文件链接）向上定位框架根，再运行 `python <framework-root>/scripts/install_agentic_framework.py --validate-extensions .`。

框架根以同时存在 `scripts/install_agentic_framework.py` 和 `skills/workflow-code-generation/SKILL.md` 为准；不得把链接入口（如 `~/.codex/skills/workflow-code-generation`）的父目录直接当作框架根。

无法确定该受信框架根时不得加载 Overlay，并报告失败。

只消费其 JSON 输出；目标文件后缀匹配 `skills[].files` 时，才加载当前 client 的对应 Skill。

不得直接读取 `.agentic-framework/extensions/*.json`，也不得从目标项目 Manifest 的 `source` 获得可执行路径。

Overlay 只补充规范，不自动执行、不覆盖核心 Skill，也不修改 workflow。

## 任务执行

派发、路由、DAG、失败隔离、合并与恢复统一按 [下放执行指南](delegated-execution-guide.md) 执行；完整 Runtime Run 的启动、Adapter 定位与 `init-run` 按 [Runtime 指南](runtime-guide.md) 执行；Review 档位定义见 [任务拆解指南原则 8](task_planning_guide.md#原则-8为每个任务标注-review-档位)。SVN 工作副本串行写入，不创建 Git 镜像或桥接。
