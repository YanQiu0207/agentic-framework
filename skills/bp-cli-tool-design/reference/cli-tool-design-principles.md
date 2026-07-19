# CLI 工具设计原则（通用版）

本文是一份 CLI 工具设计参考，适用于系统运维、部署自动化、开发者工具、数据处理工具等场景。

目标不是规定某个项目应该怎么写，而是总结一组通用原则：让 CLI 在执行前可预期，在执行中可观察，在失败后可诊断，并且能被自动化测试稳定验证。

> 关于示例的说明：本文的**原则与语言无关**，但为了便于落地，代码模板与参考资料以 Python 为主。换成 Go、Rust、Shell 等语言时，原则不变，只需替换对应的实现手段。

## 什么时候该参考这份原则

如果一个 CLI 只是临时帮自己跑一条命令，可以不用把本文所有原则都套上去。真正需要认真设计的是下面这些情况：

- 这个工具会被别人使用，而不只是作者自己用；
- 这个工具会被脚本、CI、定时任务或部署流程调用；
- 这个工具一旦失败，可能留下半完成状态；
- 这个工具会改文件、改配置、改权限、改服务或操作远程机器；
- 这个工具需要长期维护，后续可能继续加子命令、参数或执行步骤。

如果只想抓重点，至少保留 4 条底线：**前置检查**、**失败即停**、**明确退出码**、**敏感信息脱敏**。

## 总体设计纲领

> 一个好的 CLI 不应该只是「能跑命令」，而应该让用户知道：现在要做什么、为什么可以做、失败时卡在哪里、下一步该查什么。

可以把 CLI 分成 4 层：

1. **参数层**：解析参数、校验参数格式、合并多来源配置。
2. **检查层**：检查权限、系统环境、依赖命令、远程连通性。
3. **执行层**：按固定步骤执行业务动作，保证可重复、可中断。
4. **反馈层**：区分人类输出与机器输出、记录详细日志、返回明确退出码。

下面的原则大致沿这 4 层展开。

## 1. CLI 入口和核心逻辑分离

**原则**：参数解析、流程编排、核心业务逻辑要分开。不要在核心函数里到处 `print()`、`sys.exit()` 或直接读写终端。

这样做有 3 个好处：

- 核心逻辑可以被其他模块复用；
- 测试时可以注入假的命令执行器、输入输出流、权限检查器；
- CLI 行为和业务逻辑可以独立演进。

**通用例子**：

一个用户管理 CLI 可以这样拆：

```text
parse_args()      -> 只解析 create/delete 等子命令
ensure_user()     -> 只负责创建或更新用户
delete_user()     -> 只负责删除用户
main()            -> 连接参数、业务函数和退出码
```

推荐结构：

```python
def parse_args(argv=None):
    ...

def run(args, *, command_runner, output):
    ...

def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        run(args, command_runner=run_command, output=sys.stdout)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**开发建议**：

- `main()` 返回整数退出码。
- 核心函数返回结构化结果，或抛出有意义的异常。
- 外部命令执行封装成函数，方便测试时替换。
- 输入输出流作为参数传入，避免测试依赖真实终端。

## 2. 明确配置来源与优先级

**原则**：当一个工具同时支持命令行参数、环境变量、配置文件和内置默认值时，应该定义清晰的优先级，并在文档中写明，避免「为什么我改了配置文件却不生效」这类困惑。

推荐的优先级，从高到低：

```text
1. 命令行参数（flags）
2. 环境变量
3. 项目级配置文件（如 ./config.toml、.env）
4. 用户级配置（如 ~/.config/tool/config.toml）
5. 系统级配置（如 /etc/tool/config.toml）
6. 内置默认值
```

这一顺序与业界常见约定一致：命令行参数最具体、最临时，应当能覆盖一切；默认值最通用，兜底使用。

**开发建议**：

- 高优先级来源覆盖低优先级，而不是互相忽略。
- 在 `--help` 或文档中说明优先级，并说明配置文件的查找路径。
- 解析后可在 `--verbose` 下打印「最终生效配置 + 各项来源」，方便排查。
- 密钥类配置不要默认从环境变量读取，原因见第 11 条。

## 3. 先做前置检查，再做高风险动作

**原则**：只要 CLI 会修改系统、调用远程服务、安装软件、删除资源或改配置，就应该先检查执行前提。

常见前置检查包括：

- 当前用户是否有足够权限；
- 当前操作系统是否符合预期；
- 必需的外部命令是否存在；
- 配置文件或输入文件是否存在；
- 远程主机是否可达；
- 端口、认证方式、目标路径是否可用。

**通用例子**：

远程部署 CLI 在上传文件和执行远程命令前，可以先做：

```text
1. 检查 ssh/scp 是否存在
2. 检查目标主机是否可解析
3. 检查目标端口是否可连接
4. 检查要上传的文件是否齐全
5. 检查当前用户是否允许执行该部署
```

**开发建议**：

- 前置检查失败时，不要继续执行后续动作。
- 错误信息应指出失败的检查项。
- 高风险绕过应该显式命名，例如 `--force-non-linux`、`--skip-checks`，并在帮助文档中说明风险。

## 4. 固定关键流程，失败即停

**原则**：关键流程应该有明确顺序，任一步失败后默认停止，不要静默跳过失败步骤。

**通用例子**：

一个服务器初始化 CLI 可以把流程设计成：

```text
Step 1: check_os
Step 2: check_permission
Step 3: create_deploy_user
Step 4: write_config
Step 5: restart_service
Step 6: verify_service
```

如果 `write_config` 失败，就不应该继续 `restart_service`。否则用户看到的最终失败点可能是服务启动失败，但真正原因是配置根本没写成功。

**开发建议**：

- 把流程定义成显式步骤列表。
- 每个步骤只做一件事。
- 每个步骤有清晰的成功 / 失败输出。
- 失败时保留已经执行过的步骤记录。

## 5. 让重复执行变得安全（幂等性）

**原则**：会被 CI、定时任务或部署流程反复调用的工具，重复执行应当是安全的——第二次运行要么检测到目标状态已满足而跳过，要么把状态收敛到一致，而不是报错或重复创建资源。

**一句话理解**：把命令从「做这个动作」改成「确保达到这个状态」，重跑就安全了。

| 动作式（易出错） | 状态式（幂等） |
|----------------|--------------|
| 创建用户 | 确保用户存在 |
| `mkdir data` | `mkdir -p data`（已存在不报错） |
| 往配置末尾追加一行 | 整体写入目标配置（已一致就不动） |
| 计数器 `+1` | 计数器设为目标值 |

这一点和第 4 条互补：失败即停保证「出错时不往下走」，幂等保证「重跑时能安全恢复」。clig.dev 把它描述为「可恢复（recoverable）」：如果程序因为临时原因失败，用户应该能直接重跑一次就接着完成。

**通用例子**：

创建部署用户的步骤应该是「确保存在（ensure）」而非「无条件创建（create）」：

```text
bad:  useradd deploy            # 第二次运行直接报 "user already exists"
good: id deploy || useradd deploy   # 已存在则跳过，再校正其属组/权限
```

写配置文件时，先比对目标内容，若已一致则不重写、不重启服务，避免无谓的副作用。

**开发建议**：

- 关键步骤优先用「检查 - 收敛」而不是「无条件执行」。
- 区分「资源已存在且状态一致」（视为成功）与「资源已存在但状态冲突」（应报错）。
- 配合第 6 条的 `--dry-run`，让用户能预看一次重跑会改动什么。
- 尽量让清理工作可推迟到下次运行，这样程序在失败或被中断时可以立即退出。

## 6. 为系统修改提供预演、备份或安全开关

**原则**：会改变系统状态的 CLI，应该让用户有机会先看清影响范围，并提供回退线索。

常用机制：

- `--dry-run`：只展示将执行的动作，不实际修改；
- 自动备份：修改已有配置前保存旧文件；
- 二次确认：删除用户、清空目录、覆盖数据前要求确认；
- `--yes`：在自动化场景中跳过交互确认；
- `--force-*`：对危险绕过做显式 opt-in。

**通用例子**：

配置修改工具可以这样设计：

```text
tool config apply --file new.conf --dry-run
tool config apply --file new.conf
```

`--dry-run` 输出：

```text
[dry-run] would write: /etc/example/app.conf
[dry-run] would backup: /etc/example/app.conf.bak-20260613120000
[dry-run] would restart: example.service
```

**开发建议**：

- 默认行为偏保守。
- 破坏性操作需要明确确认：交互时提示用户输入 `y`/`yes`，非交互时要求传 `--force` 或 `--yes`。
- 备份路径要打印出来。
- `--force` 不要成为默认值。

## 7. 优雅处理中断与清理

**原则**：长时间运行、会改系统状态的 CLI 应当正确响应中断信号（如用户按 `Ctrl-C` 触发的 `SIGINT`），而不是留下不可预期的半完成状态。

**一种省心的思路（crash-only）**：与其在退出时努力清理（清理可能很慢、可能再次失败、被强杀或断电时根本来不及跑），不如退出时直接走人，把清理挪到**下次启动时**做——下次启动先收拾上次的残留，再干正事。这样无论上次是失败、被中断还是断电，下次跑都能恢复干净。比如下载工具失败后留着 `download.tmp` 不管，下次启动时再删除或断点续传（前提是最终文件用原子 `rename()` 产生，否则会留下损坏文件）。

**通用例子**：

```text
^C
Interrupting... will stop after the current step.
Press Ctrl-C again to force quit (may leave a partial deploy).
```

**开发建议**：

- 收到中断信号后尽快响应，并**先告知用户**「正在中断」，再开始清理。
- 如果清理本身耗时，允许用户再次按 `Ctrl-C` 跳过清理，并提前说明跳过的后果。
- 不要假设上一次运行的清理一定执行过；程序应能在「清理未完成」的前提下被重新启动（与第 5 条幂等性呼应）。
- 中断导致的退出也要返回非零退出码（见第 13 条）。

## 8. 使用白名单控制作用域

**原则**：涉及上传、删除、迁移、修改多个对象时，默认使用白名单或明确作用域，不要粗放地处理整个目录或所有匹配项。

**通用例子**：

部署工具不要默认上传当前目录下所有文件：

```text
bad:  upload *
good: upload app.py config.yaml requirements.txt
```

如果确实支持通配符，应先展示匹配结果：

```text
Matched files:
- app.py
- config.yaml
- requirements.txt

Continue? [y/N]
```

**开发建议**：

- 关键资源使用显式清单。
- 缺少必需资源时尽早失败。
- 对通配符结果进行展示和确认。
- 不要把临时文件、缓存目录、密钥文件纳入默认处理范围。

## 9. 区分 stdout 与 stderr，并提供机器可读输出

**原则**：CLI 的输出有两类受众——人和程序。要按 Unix 约定把两者分开：**主结果走 `stdout`，日志、进度、错误走 `stderr`**；当输出需要被程序消费时，提供结构化格式（如 `--json`）。

这样设计后，`tool list --json | jq ...` 这类管道才不会被进度信息污染，脚本也能稳定解析结果。

**通用例子**：

```text
# 进度与日志走 stderr，结构化结果走 stdout
$ tool users list --json 2>/dev/null | jq '.[].name'
"deploy"
"backup"
```

```text
stderr:  Step 1: query database succeeded in 0.03s.
stdout:  [{"name": "deploy", "uid": 1001}, {"name": "backup", "uid": 1002}]
```

**开发建议**：

- 主输出（尤其是机器可读内容）一律送 `stdout`；日志、提示、错误一律送 `stderr`。
- 提供 `--json`（或 `--output json`）输出结构化结果，便于脚本消费。
- 默认面向人类的文本输出，不要破坏可读性；机器可读格式作为可选项开启。
- 退出码（第 13 条）表达成败，结构化输出表达细节，两者配合使用。

## 10. 控制台输出克制，详细信息进入日志

**原则**：默认面向人类的控制台输出应该服务于阅读，展示关键进度和错误摘要；详细命令输出、堆栈、子进程完整输出应该进入日志，或只在 `--verbose` 模式下展示。

**推荐输出**：

```text
Step 1: check_config succeeded in 0.012s.
Step 2: upload_files succeeded in 1.284s.
Step 3: restart_service failed after 0.318s.
Error: service did not become active
Log: ./tool.log
```

**不推荐输出**：

```text
正在执行一堆命令……
大量 stdout……
大量 stderr……
最后只告诉用户失败了……
```

**开发建议**：

- 成功路径只输出必要进度。
- 失败路径输出错误摘要、日志位置和排查方向。
- 提供 `--verbose` 展示完整命令输出。
- 日志中记录命令、退出码、耗时和详细输出。

## 11. 敏感信息默认不落日志

**原则**：密码、令牌、私钥、连接串等敏感信息不能出现在日志、错误信息和普通控制台输出中，也不应通过容易泄漏的渠道传入。

**通用例子**：

命令实际收到：

```text
tool user create deploy --password Secret123!
```

日志中应该记录为：

```text
[run] tool user create deploy --password <redacted>
```

**开发建议**：

- 维护敏感参数名列表，例如 `--password`、`--token`、`--secret`、`--api-key`；打印命令、异常和调试信息前先脱敏。
- **不要直接从命令行参数读密钥**：`--password Secret123!` 会泄漏进 `ps` 输出和 Shell 历史。
- 优先支持 `--password-file` 或从 `stdin` 读取。环境变量虽比命令行明文好，但会被子进程继承、被日志或崩溃信息打印，仍有泄漏面，**不建议作为密钥的首选来源**。
- 测试日志中是否出现敏感样例值。

## 12. 错误信息要告诉用户下一步查什么

**原则**：错误信息不应只描述「失败了」，还要帮助用户定位下一步。

**弱错误信息**：

```text
Error: command failed
```

**强错误信息**：

```text
Error: cannot connect to example.com:2222.
Please check host, SSH port, firewall, cloud security group, and local proxy settings.
```

**开发建议**：

- 错误信息包含失败对象。
- 外部命令失败时保留退出码。
- 常见失败原因给出排查清单。
- 如果有日志文件，明确告诉用户日志路径。
- 如果用户可以用某条命令验证，直接给出命令。

## 13. 用退出码表达最终结果

**原则**：CLI 应该通过退出码表达整体成功或失败，方便 Shell、CI、定时任务或其他自动化工具判断结果。

常见约定：

```text
0    成功
1    通用失败
2    参数使用错误
```

其中退出码 `2` 表示参数使用错误，是 Python `argparse` 在参数非法时的默认行为，沿用它便于与生态保持一致。如果 CLI 是外部命令包装器，可以在子命令失败时保留原始退出码，方便调用方判断。

**通用例子**：

```bash
tool deploy production
if [ $? -ne 0 ]; then
    echo "deploy failed"
    exit 1
fi
```

**开发建议**：

- 成功统一返回 `0`，失败返回非零。
- 失败不要只打印错误后继续返回 `0`。
- 子命令失败时尽量保留原始退出码。
- `main()` 统一决定最终退出码。

## 14. 关键路径必须可测试

**原则**：CLI 测试不应只覆盖 happy path，还要覆盖参数校验、前置检查、失败中断、退出码、日志和敏感信息处理。

建议至少覆盖：

- 参数解析是否正确；
- 非法参数是否被拒绝；
- 缺少依赖命令时是否停止；
- 权限不足时是否停止；
- 某个步骤失败后是否不再执行后续步骤；
- 重复执行是否安全（幂等）；
- 失败时退出码是否非 `0`；
- 日志中是否包含必要诊断信息；
- 日志中是否没有敏感明文。

**通用例子**：

```python
def test_stops_when_precheck_fails():
    fake_runner = FakeRunner()
    result = main(["deploy", "prod"], runner=fake_runner, check_network=lambda: False)
    assert result != 0
    assert fake_runner.commands == []
```

**开发建议**：

- 将外部命令、当前时间、输入输出流、权限检查封装成可注入依赖。
- 不要在测试中真实修改系统。
- 用临时目录模拟文件系统输入输出。
- 对失败路径写测试。

## 开发新 CLI 时的检查清单

开发或评审一个新 CLI 时，可以逐项检查：

- 是否有清晰的 `main()` 入口，并返回退出码？
- 参数解析、前置检查、业务执行、输出反馈是否分层？
- 多来源配置是否定义了清晰的优先级，并写进文档？
- 修改系统或远程主机前，是否检查了权限、环境、依赖和连通性？
- 关键流程是否有固定顺序？任一步失败后是否默认停止？
- 重复执行是否安全（幂等）？
- 是否正确响应 `Ctrl-C` 等中断信号，并避免留下半完成状态？
- 主结果是否走 `stdout`、日志与进度是否走 `stderr`？
- 是否提供 `--json` 等机器可读输出？
- 默认面向人类的控制台输出是否简洁？是否有日志、`--verbose` 或其他排障机制？
- 失败信息是否说明下一步该查什么？
- 高风险修改是否支持 `--dry-run`、备份、确认或显式 `--force-*`？
- 敏感参数是否会被脱敏？是否避免从命令行参数直接读密钥？
- 多文件、多资源操作是否有白名单或明确作用域？
- 是否有覆盖失败路径的测试？

## 推荐最小模板

下面是一个适合多数 Python CLI 的最小结构：

```python
import argparse
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Describe what this tool does.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def precheck(args):
    ...


def run(args):
    precheck(args)
    ...


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        run(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

> 模板里 `KeyboardInterrupt` 返回 `130`，沿用 Shell 中「被信号 N 终止时退出码为 `128 + N`」的惯例（`SIGINT` 的信号编号为 `2`，故 `128 + 2 = 130`）。

## 参考资料

- [Command Line Interface Guidelines（clig.dev）](https://clig.dev/) —— stdout/stderr、`--json`、配置优先级、幂等、信号处理、确认与脱敏等约定的主要来源。
- [The Twelve-Factor App：Config](https://12factor.net/config) —— 配置与代码分离、环境变量管理。
- [Python `argparse` 官方文档](https://docs.python.org/3/library/argparse.html)
- [Python `subprocess` 官方文档](https://docs.python.org/3/library/subprocess.html)
- [Python `sys.exit()` 官方文档](https://docs.python.org/3/library/sys.html#sys.exit)
- [Python `signal` 官方文档](https://docs.python.org/3/library/signal.html)
- [Python `logging` 官方文档](https://docs.python.org/3/library/logging.html)
- [Python `getpass` 官方文档](https://docs.python.org/3/library/getpass.html)
- [Python `os.replace` / `os.rename` 官方文档](https://docs.python.org/3/library/os.html#os.replace) —— 第 7 条原子替换的依据：成功时重命名是原子操作（POSIX 要求）、覆盖已存在目标、跨文件系统可能失败、`os.rename` 在 Windows 上遇已存在目标抛 `FileExistsError`。
- [Python `os.fsync` 官方文档](https://docs.python.org/3/library/os.html#os.fsync) —— 强制把文件内容写入磁盘（Force write … to disk），配合原子替换防断电。
- [POSIX `rename` 规范（The Open Group）](https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html) —— rename 原子性的一手要求（RATIONALE：that this `rename()` be atomic）。
