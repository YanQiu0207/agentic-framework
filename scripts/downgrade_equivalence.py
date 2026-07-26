"""降级等价比对器（change 2042）。

判据（`framework-unification.md` §8.1，change 2036 引入）：把
`governance_profile` 从 `production` 降到 `tooling` 后，对同一输入的执行
结果必须与纯 Tooling 实现逐字节相同。

本脚本只做调用与比对，不含任何门禁判定逻辑：两条路径都是对外部命令的
子进程调用，判定由被调门禁自行完成。输出三种结论：

- 通过（退出码 0）：两路径的归一输出逐字节相同。
- 不通过（退出码 1）：两路径都跑出了可比结果但不一致。
- 无法执行（退出码 3）：开关不存在、开关无效果、基线缺失或输出格式
  不可比。「无法执行」与「不通过」同判越界，但原因分开标注；不存在
  按「暂不适用」放行的分支。

判据局限（每次报告都写入头部）：本判据只验「减去治理门后等于
Tooling」，不验治理强度；治理强度由 §3.2 条件 3 另行承担，判据通过
不得读成「收敛已证明」。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 判据局限声明，写入每份报告头部——不验治理强度，通过不等于收敛已证明。
CRITERION_LIMITATION = (
    "本判据只验「减去治理门后等于 Tooling」，不验治理强度；"
    "治理强度由 §3.2 条件 3 另行承担，判据通过不得读成「收敛已证明」。"
)

VERDICT_PASS = "通过"
VERDICT_FAIL = "不通过"
VERDICT_UNEXECUTABLE = "无法执行"

EXIT_CODES = {VERDICT_PASS: 0, VERDICT_FAIL: 1, VERDICT_UNEXECUTABLE: 3}

# 默认路径对：当前两轨输出格式不可比（Tooling lint 无错误编号体系），
# 比对器如实报告「无法执行」；change 2043 的合并引擎提供可比对的路径对。
DEFAULT_PATH_A = (
    "{python} {repo}/scripts/validate_change.py --repo {repo} "
    "--change {input} --phase plan --governance-profile tooling --json"
)
DEFAULT_EXTRACTOR_A = "validate-json"
DEFAULT_PATH_B = "{python} {repo}/skills/workflow-code-generation/scripts/lint_task_deps.py {input}/tasks.md --json"
DEFAULT_EXTRACTOR_B = "lint-json"


@dataclass(frozen=True)
class PathOutput:
    """一条路径的归一输出：退出码 + 排序后错误编号集合（集合语义，重复
    计数不参与比对——归一规则显式声明，不静默丢弃）。"""

    exit_code: int
    error_ids: tuple[str, ...]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=dict(os.environ, PYTHONUTF8="1"),
    )


def _extract(exit_code: int, stdout: str, extractor: str) -> PathOutput | None:
    """按提取器归一输出；无法提取时返回 None（输出格式不可比）。"""
    if extractor == "validate-json":
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        errors = payload.get("errors")
        if not isinstance(errors, list):
            return None
        ids = {item["rule_id"] for item in errors if isinstance(item, dict) and "rule_id" in item}
        return PathOutput(exit_code, tuple(sorted(ids)))
    if extractor == "lint-json":
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        # Tooling lint 的错误是消息字符串，没有编号体系——不可比。
        return None
    if extractor.startswith("regex:"):
        pattern = extractor[len("regex:") :]
        ids = {match.group(1) for match in re.finditer(pattern, stdout)}
        if not ids and exit_code != 0:
            return None
        return PathOutput(exit_code, tuple(sorted(ids)))
    return None


def _build(template: str, *, repo: Path, input_path: Path) -> list[str]:
    rendered = template.format(
        python=sys.executable, repo=repo.as_posix(), input=input_path.as_posix()
    )
    return rendered.split()


def _probe_switch(
    path_a: str, extractor_a: str, *, repo: Path
) -> str | None:
    """探测降级开关：不存在与无效果都判「无法执行」。

    开关不存在：路径 A 带 `--governance-profile` 运行即被 argparse 拒绝。
    开关无效果：对含 lightweight 声明的合成输入跑路径 A，仍出现
    production 下限判定（OPSX063）或读取失败（OPSX062）。
    """
    if "--governance-profile" not in path_a:
        return None
    with tempfile.TemporaryDirectory() as temp_dir:
        probe_dir = Path(temp_dir) / "openspec" / "changes" / "2099-probe"
        probe_dir.mkdir(parents=True)
        (probe_dir / "tasks.md").write_text(
            "# 实施任务清单\n\n### 任务 1：[pending] 探测\n"
            "- 依赖: 无\n- Review Profile: lightweight\n- 文件: `a.py`\n- 文档映射: `proposal.md` §1\n",
            encoding="utf-8",
        )
        probe_repo = Path(temp_dir)
        command = _build(path_a, repo=repo, input_path=probe_dir)
        try:
            completed = _run(command)
        except OSError as error:
            return f"开关不存在（路径 A 无法执行：{error}）"
        if "unrecognized arguments" in completed.stderr:
            return "开关不存在（--governance-profile 被 argparse 拒绝）"
        output = _extract(completed.returncode, completed.stdout, extractor_a)
        if output is not None and {"OPSX062", "OPSX063"} & set(output.error_ids):
            return "开关无效果（降级后仍出现 production 下限判定）"
    return None


def compare(
    *,
    path_a: str,
    extractor_a: str,
    path_b: str,
    extractor_b: str,
    input_path: Path,
    repo: Path = REPO_ROOT,
) -> dict:
    """执行两路径并给出三态结论。报告头部固定写入判据局限。"""
    report: dict = {
        "criterion_limitation": CRITERION_LIMITATION,
        "comparison_scope": "退出码 + 排序后错误编号集合（集合语义，重复计数不参与）",
        "input": input_path.as_posix(),
        "path_a": path_a,
        "path_b": path_b,
        "verdict": None,
        "reason": "",
    }
    if not input_path.exists():
        report["verdict"] = VERDICT_UNEXECUTABLE
        report["reason"] = f"基线缺失（输入不存在：{input_path}）"
        return report

    switch_problem = _probe_switch(path_a, extractor_a, repo=repo)
    if switch_problem is not None:
        report["verdict"] = VERDICT_UNEXECUTABLE
        report["reason"] = switch_problem
        return report

    outputs: dict[str, PathOutput | None] = {}
    for label, template, extractor in (
        ("a", path_a, extractor_a),
        ("b", path_b, extractor_b),
    ):
        command = _build(template, repo=repo, input_path=input_path)
        try:
            completed = _run(command)
        except OSError as error:
            report["verdict"] = VERDICT_UNEXECUTABLE
            report["reason"] = f"基线缺失（路径 {label.upper()} 无法执行：{error}）"
            return report
        outputs[label] = _extract(completed.returncode, completed.stdout, extractor)
        if outputs[label] is None:
            report["verdict"] = VERDICT_UNEXECUTABLE
            report["reason"] = f"输出格式不可比（路径 {label.upper()} 的提取器 {extractor} 无法归一输出）"
            return report

    output_a, output_b = outputs["a"], outputs["b"]
    assert output_a is not None and output_b is not None
    report["normalized_a"] = {
        "exit_code": output_a.exit_code,
        "error_ids": list(output_a.error_ids),
    }
    report["normalized_b"] = {
        "exit_code": output_b.exit_code,
        "error_ids": list(output_b.error_ids),
    }
    if output_a == output_b:
        report["verdict"] = VERDICT_PASS
        report["reason"] = "两路径归一输出逐字节相同"
        return report
    report["verdict"] = VERDICT_FAIL
    if output_a.exit_code != output_b.exit_code:
        report["reason"] = f"退出码不一致：A={output_a.exit_code} B={output_b.exit_code}"
    else:
        only_a = sorted(set(output_a.error_ids) - set(output_b.error_ids))
        only_b = sorted(set(output_b.error_ids) - set(output_a.error_ids))
        first = (only_a or only_b)[0]
        report["reason"] = (
            f"错误编号集合不一致，首个差异：{first}"
            f"（仅 A：{only_a}；仅 B：{only_b}）"
        )
    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="降级等价比对器：同一输入的「production 降级」与「纯 Tooling」两路径逐字节比对"
    )
    parser.add_argument("--input", type=Path, required=True, help="被比对输入（Change 目录）")
    parser.add_argument("--path-a", default=DEFAULT_PATH_A, help="路径 A 命令模板")
    parser.add_argument("--extractor-a", default=DEFAULT_EXTRACTOR_A)
    parser.add_argument("--path-b", default=DEFAULT_PATH_B, help="路径 B 命令模板")
    parser.add_argument("--extractor-b", default=DEFAULT_EXTRACTOR_B)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)

    report = compare(
        path_a=args.path_a,
        extractor_a=args.extractor_a,
        path_b=args.path_b,
        extractor_b=args.extractor_b,
        input_path=args.input,
        repo=args.repo,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return EXIT_CODES[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
