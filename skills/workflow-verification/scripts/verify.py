#!/usr/bin/env python3
"""研发后验证门禁（框架参考实现）。

读取 verify.config.json，执行其中定义的检查，产出结构化报告。
支持改动前后的基线对比：只把「相对基线新增」的违规判为失败，
从而把「是不是这次引入的」从口头辩解变成两份报告的差集。

用法：
    # 改动前：采集基线
    python verify.py --save-baseline .verify/baseline.json

    # 改动后：验证并与基线对比
    python verify.py --baseline .verify/baseline.json

    # 不带基线：所有检查按绝对标准判定
    python verify.py

退出码：
    0 = 全部通过 / 无配置 / 采集基线成功
    1 = 存在（新增）违规
    2 = 配置或运行错误
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """单个检查的结果。"""

    name: str
    type: str
    status: str  # "pass" | "fail"
    detail: str = ""
    value: Any = None  # 本次测得的值：count 为数字，forbid_pattern 为命中行列表
    new_items: list[str] = field(default_factory=list)  # 相对基线的新增违规行


def run_command(command: str) -> tuple[int, str, str]:
    """执行 shell 命令，返回 (returncode, stdout, stderr)。"""
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _measure_count(check: dict, stdout: str) -> int:
    """按 metric 把命令输出折算成一个整数。"""
    metric = check.get("metric", "line_count")
    if metric == "stdout_int":
        try:
            return int(stdout.strip())
        except ValueError:
            return len(_nonempty_lines(stdout))
    return len(_nonempty_lines(stdout))


def evaluate_check(check: dict, baseline: dict | None) -> CheckResult:
    """执行并判定一个检查。baseline 为该检查的基线条目（{type, value}）或 None。"""
    name = check.get("name", "<unnamed>")
    ctype = check.get("type")
    command = check.get("command", "")
    if not ctype or not command:
        return CheckResult(name, ctype or "?", "fail", "check 缺少 type 或 command")

    returncode, out, err = run_command(command)

    # 非 exit_code 检查只看 stdout；若命令本身执行失败（returncode 非 0 且有
    # stderr，如工具缺失、路径错误、正则非法），不能当成「无命中 / 0」放过——
    # 那会让门禁形同虚设。grep 类「无匹配返回 1 且无 stderr」不算执行失败。
    if ctype in ("forbid_pattern", "count") and returncode != 0 and err.strip():
        tail = " | ".join(err.strip().splitlines()[-3:])
        return CheckResult(name, ctype, "fail", f"命令执行失败 exit={returncode}：{tail}")

    if ctype == "exit_code":
        expect = check.get("expect_code", 0)
        if returncode == expect:
            return CheckResult(name, ctype, "pass", f"exit={returncode}")
        tail = (err or out).strip().splitlines()[-5:]
        return CheckResult(
            name, ctype, "fail",
            f"exit={returncode} 期望 {expect}；末尾输出：" + " | ".join(tail),
        )

    if ctype == "forbid_pattern":
        items = _nonempty_lines(out)
        if baseline is not None:
            base_items = set(baseline.get("value") or [])
            new = [it for it in items if it not in base_items]
            if new:
                return CheckResult(
                    name, ctype, "fail", f"新增 {len(new)} 处违规",
                    value=items, new_items=new,
                )
            return CheckResult(
                name, ctype, "pass", f"命中 {len(items)} 处，均在基线内", value=items,
            )
        if items:
            return CheckResult(
                name, ctype, "fail", f"命中 {len(items)} 处违规",
                value=items, new_items=items,
            )
        return CheckResult(name, ctype, "pass", "无命中", value=items)

    if ctype == "count":
        current = _measure_count(check, out)
        direction = check.get("direction", "not_decrease")
        if baseline is not None and isinstance(baseline.get("value"), int):
            base_val = baseline["value"]
            if direction == "not_decrease" and current < base_val:
                return CheckResult(name, ctype, "fail", f"{current} < 基线 {base_val}", value=current)
            if direction == "not_increase" and current > base_val:
                return CheckResult(name, ctype, "fail", f"{current} > 基线 {base_val}", value=current)
            return CheckResult(name, ctype, "pass", f"{current}（基线 {base_val}）", value=current)
        threshold = check.get("threshold")
        if isinstance(threshold, int) and current < threshold:
            return CheckResult(name, ctype, "fail", f"{current} < 阈值 {threshold}", value=current)
        return CheckResult(name, ctype, "pass", f"{current}", value=current)

    return CheckResult(name, ctype, "fail", f"未知 check 类型：{ctype}")


def load_config(path: Path) -> dict:
    """读配置；不存在则静默跳过门禁（对存量项目无侵入）。"""
    if not path.exists():
        print(f"[verify] 未找到配置 {path}，跳过门禁（对存量项目无侵入）。")
        sys.exit(0)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[verify] 配置解析失败：{exc}", file=sys.stderr)
        sys.exit(2)


def cmd_save_baseline(config: dict, out_path: Path) -> int:
    """采集基线：只记录 baseline_aware 检查的当前"值"。"""
    baseline: dict[str, Any] = {"checks": {}}
    for check in config.get("checks", []):
        if not check.get("baseline_aware"):
            continue
        res = evaluate_check(check, baseline=None)
        baseline["checks"][res.name] = {"type": res.type, "value": res.value}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[verify] 基线已保存到 {out_path}（{len(baseline['checks'])} 项 baseline-aware 检查）")
    return 0


def cmd_verify(config: dict, baseline_path: Path | None, report_path: Path) -> int:
    """跑全部检查，对 baseline_aware 项做基线对比，产出报告。"""
    baseline_data: dict[str, Any] = {}
    if baseline_path and baseline_path.exists():
        try:
            baseline_data = json.loads(baseline_path.read_text(encoding="utf-8")).get("checks", {})
        except json.JSONDecodeError as exc:
            print(f"[verify] 基线解析失败：{exc}", file=sys.stderr)
            return 2

    results: list[CheckResult] = []
    for check in config.get("checks", []):
        base_entry = None
        if check.get("baseline_aware") and check.get("name") in baseline_data:
            base_entry = baseline_data[check["name"]]
        results.append(evaluate_check(check, base_entry))

    failed = [r for r in results if r.status == "fail"]
    report = {
        "verdict": "FAIL" if failed else "PASS",
        "total": len(results),
        "failed": len(failed),
        "results": [asdict(r) for r in results],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(results, report["verdict"], report_path)
    return 1 if failed else 0


def _print_summary(results: list[CheckResult], verdict: str, report_path: Path) -> None:
    print("\n==== verify 门禁结果 ====")
    for r in results:
        mark = {"pass": "[PASS]", "fail": "[FAIL]"}.get(r.status, "[????]")
        print(f"{mark} {r.name} [{r.type}] {r.detail}")
        for item in r.new_items[:10]:
            print(f"        新增违规：{item}")
    print(f"\n总判定：{verdict}（报告：{report_path}）")


def main(argv: list[str] | None = None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")  # 避免 Windows 控制台中文乱码
    parser = argparse.ArgumentParser(description="研发后验证门禁（配置驱动 + 基线对比）")
    parser.add_argument("--config", default="verify.config.json", help="配置文件路径")
    parser.add_argument("--save-baseline", metavar="PATH", help="采集基线并写入该路径")
    parser.add_argument("--baseline", metavar="PATH", help="对比用的基线路径")
    parser.add_argument("--report", default=".verify/report.json", help="结构化报告输出路径")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))

    if args.save_baseline:
        return cmd_save_baseline(config, Path(args.save_baseline))

    baseline_path = Path(args.baseline) if args.baseline else None
    return cmd_verify(config, baseline_path, Path(args.report))


if __name__ == "__main__":
    sys.exit(main())
