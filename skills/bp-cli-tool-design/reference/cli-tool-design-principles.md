# CLI 工具设计原则

这份参考适用于长期维护、被他人或自动化调用、会改变状态，或者失败后可能留下半完成状态的 CLI。一次性、只读且低风险的内部命令可只采用「最小设计」与交付检查清单。

## 最小设计

将 CLI 分成 4 个职责，避免把参数解析、状态变更和终端输出揉在一个函数中。

| 职责 | 必须明确 |
| --- | --- |
| 参数 | 参数校验、配置来源与覆盖顺序 |
| 检查 | 权限、平台、依赖、输入、目标和连通性 |
| 执行 | 步骤顺序、失败边界、重复执行语义 |
| 反馈 | `stdout`、`stderr`、日志、结构化输出与退出码 |

入口负责解析参数、编排流程和映射退出码；核心逻辑返回结构化结果或抛出有意义的异常。外部命令执行器、输入输出流、时间和权限检查应可注入，避免测试真实修改系统。

配置有多个来源时，必须声明并测试覆盖顺序。推荐默认顺序为：命令行参数、环境变量、项目配置、用户配置、系统配置、内置默认值。凭据不采用普通命令行参数，参见「敏感信息与日志」。

## 状态变更安全

### 先检查，再修改

在首个状态变更前，一次性完成可预判的检查：

- 权限和目标平台；
- 必需命令、输入文件和目标路径；
- 远程解析、端口、认证方式和连通性；
- 操作对象白名单及通配符展开结果。

检查失败时指出失败对象和可执行的下一步，但不得继续执行。

### 显式步骤与失败即停

把关键流程表示为有序步骤，每步只做一件事。步骤失败后保留已完成步骤的记录，停止后续动作，返回非零退出码。不要在配置写入失败后继续重启服务，也不要用后续错误掩盖首个失败点。

### 幂等与恢复

将动作设计成「确保达到目标状态」：

- 已存在且状态一致：成功或跳过；
- 已存在但状态冲突：明确失败；
- 写文件：先比较内容，再写临时文件并原子替换；
- 中断或失败：允许下次运行识别并处理残留。

重复执行可能造成额外副作用时，必须在文档和帮助信息中说明。

### 破坏性操作

根据风险提供至少一种保护：

- `--dry-run` 展示准确的操作对象和步骤；
- 修改已有配置前备份，并输出备份位置；
- 交互环境要求确认，非交互环境要求显式 `--yes`；
- 风险绕过使用具体的 `--force-*`，不把 `--force` 设为默认值。

删除、上传或迁移多个对象时默认使用白名单。支持通配符时，先展示展开结果；不得默认包含缓存、临时文件和密钥文件。

### 中断

长任务收到 `Ctrl-C` 后，应尽快告知用户并停止在安全边界。中断返回非零退出码；清理可能失败时，应让下次启动也能处理未完成状态，而不是假设退出清理必然成功。

## 输出、错误与退出码

- 主结果写入 `stdout`。
- 进度、提示和固定错误摘要写入 `stderr`。
- 机器消费场景提供 `--json` 或等价格式；结构化结果中不得混入进度文本。
- 默认输出只保留关键进度；详细命令结果仅在字段已分类且经过专用过滤器时进入日志或显式 `--verbose` 通道。
- 未知异常不得以 `print(exc)`、`traceback.print_exc()` 等形式直接写入终端。
- 终端错误只说明失败对象、固定摘要、日志位置和安全的排查动作。

退出码至少保持以下契约：

| 退出码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `1` | 通用执行失败 |
| `2` | 参数使用错误 |
| `130` | 被 `SIGINT` 中断 |

包装外部命令时，可以保留有业务意义的子进程退出码；必须在接口文档中固定映射，不能失败后返回 `0`。

## 敏感信息与日志

敏感信息包括密码、令牌、私钥、会话 Cookie、连接串和含凭据的 URL。

- 不通过 `--password value` 等参数接收凭据；优先读取权限受控文件或 `stdin`。
- 环境变量可能被子进程继承，不作为凭据的默认首选来源。
- 未知异常只记录异常类型、步骤名和人工构造的安全上下文；不得读取或序列化其消息、`args`、异常链或 traceback。
- 已分类异常只允许记录明确列入白名单的结构化字段，并使用该异常类型专属的过滤器；不得用通用正则处理任意异常字符串。
- 日志只写入受控文件，不把详细异常日志同时传播到控制台 handler。
- 字段无法证明安全时宁可省略，不记录原值。
- 测试使用显眼的假凭据，并断言 `stdout`、`stderr` 和日志均无明文。

建议将用户终端消息与内部诊断分开：终端只输出固定摘要；未知异常日志只记录异常类型、固定步骤名和代码内定义的安全事件字段。异常对象自身不属于安全日志输入。

## Python 3.8+ 最小模板

模板展示入口边界，不规定业务框架。公开函数使用完整类型注解和 docstring；未知异常只向终端输出固定摘要，日志不读取异常消息，只记录异常类型和固定步骤名。

```python
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence


def build_file_logger(log_path: Path) -> logging.Logger:
    """Build a non-propagating file logger for sanitized diagnostics."""
    logger = logging.getLogger("tool")
    for existing_handler in logger.handlers[:]:
        existing_handler.close()
        logger.removeHandler(existing_handler)
    logger.propagate = False
    handler = logging.FileHandler(str(log_path), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Describe the tool.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def precheck(args: argparse.Namespace) -> None:
    """Validate all predictable prerequisites before state changes."""
    del args


def run(args: argparse.Namespace) -> None:
    """Execute the ordered operation after prechecks pass."""
    precheck(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return its process exit code."""
    args = parse_args(argv)
    log_path = Path("tool.log")
    logger: Optional[logging.Logger] = None
    try:
        logger = build_file_logger(log_path)
        run(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # Boundary converts unexpected failures to exit 1.
        if logger is not None:
            logger.error(
                "operation failed: step=run exception_type=%s",
                type(exc).__name__,
            )
        print(
            f"Error: operation failed. See {log_path} for details.",
            file=sys.stderr,
        )
        return 1
    finally:
        if logger is not None:
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

已分类异常若需要额外诊断字段，应为该异常定义结构化字段白名单和专用过滤器，并在独立的 `except` 分支记录；未知异常路径不得复用该分支，也不得记录 `str(exc)`。

## 测试重点

至少覆盖与本次改动有关的项目：

- 合法、非法和缺失参数；
- 前置检查失败时没有执行任何状态变更；
- 中间步骤失败时没有执行后续步骤；
- 重复执行收敛到同一状态；
- `stdout` 与 `stderr` 分流，`--json` 可稳定解析；
- 成功、参数错误、执行失败和中断的退出码；
- 假凭据不出现在输出和日志；
- 未知异常的 `stdout`、`stderr` 和日志不包含异常消息或凭据，仅日志保留异常类型、步骤名和安全事件字段。

测试中注入命令执行器、文件系统目录、时间和输出流，不调用真实远程主机，不修改真实系统状态。

## 交付检查清单

- [ ] 参数、检查、执行和反馈职责已分离。
- [ ] 配置来源与覆盖顺序已写明并测试。
- [ ] 首次状态变更前完成所有可预判检查。
- [ ] 步骤顺序固定，失败后停止，重复执行安全。
- [ ] 高风险操作具有预演、备份、确认或显式风险开关。
- [ ] 多资源操作使用白名单或展示通配符展开结果。
- [ ] `stdout`、`stderr`、结构化输出和退出码契约明确。
- [ ] 未知异常不记录消息、`args`、异常链或 traceback，只记录异常类型、步骤名和人工构造的安全上下文。
- [ ] 凭据输入、输出和日志均无明文泄漏。
- [ ] 关键成功路径、失败路径和中断路径有测试。

## 参考资料

- [Command Line Interface Guidelines](https://clig.dev/)：输出、配置、信号、幂等、确认和凭据处理。
- [Python `argparse` 文档](https://docs.python.org/3/library/argparse.html)：参数解析与参数错误退出行为。
- [Python `logging` 文档](https://docs.python.org/3/library/logging.html)：日志、handler 与传播机制。
- [Python `getpass` 文档](https://docs.python.org/3/library/getpass.html)：不回显的凭据输入。
- [Python `signal` 文档](https://docs.python.org/3/library/signal.html)：信号处理。
- [Python `os.replace` 文档](https://docs.python.org/3/library/os.html#os.replace)：原子替换接口与平台行为。
- [POSIX `rename` 规范](https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html)：`rename()` 原子性要求。
