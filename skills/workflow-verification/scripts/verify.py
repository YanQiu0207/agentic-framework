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
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """单个检查的结果。"""

    name: str
    type: str
    status: str  # "pass"（通过）| "fail"（违规）| "error"（命令/配置执行错误）
    detail: str = ""
    value: Any = None  # 本次测得的值：count 为数字，forbid_pattern 为命中行列表
    new_items: list[str] = field(default_factory=list)  # 相对基线的新增违规行


_DEFAULT_TIMEOUT = 60  # 秒；防止卡死命令永久阻塞验证流程


def run_command(command: str, timeout: int = _DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """执行 shell 命令，返回 (returncode, stdout, stderr)。超时视为执行错误。"""
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"命令超时（>{timeout}s）"


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


_VALID_DIRECTIONS = {"not_decrease", "not_increase"}


def _check_fingerprint(check: dict) -> dict:
    """提取决定 check 行为的字段，用于检测配置在基线采集后是否被改弱/改变。"""
    ctype = check.get("type", "")
    fp: dict[str, Any] = {"type": ctype, "command": check.get("command", "")}
    if ctype == "count":
        fp["metric"] = check.get("metric", "line_count")
        fp["direction"] = check.get("direction", "not_decrease")
    elif ctype == "exit_code":
        fp["expect_code"] = check.get("expect_code", 0)
    return fp


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
        return CheckResult(name, ctype or "?", "error", "check 缺少 type 或 command")

    timeout = int(check.get("timeout_seconds", _DEFAULT_TIMEOUT))
    returncode, out, err = run_command(command, timeout=timeout)

    # 非 exit_code 检查只看 stdout；若命令本身执行失败（returncode 非 0 且有
    # stderr，如工具缺失、路径错误、正则非法），不能当成「无命中 / 0」放过——
    # 那会让门禁形同虚设。grep 类「无匹配返回 1 且无 stderr」不算执行失败。
    # 判为 error（区别于「有违规」的 fail）：采基线时遇 error 必须中止，不能写入伪基线。
    if ctype in ("forbid_pattern", "count") and returncode != 0 and err.strip():
        tail = " | ".join(err.strip().splitlines()[-3:])
        return CheckResult(name, ctype, "error", f"命令执行失败 exit={returncode}：{tail}")

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
            # 按出现次数比对，而非集合：grep -o 类命令对每处命中只输出相同文本，
            # 用 set 会把「新增的同名违规」误判为已在基线内而放过。
            base_counter = Counter(baseline.get("value") or [])
            new: list[str] = []
            for item, count in Counter(items).items():
                extra = count - base_counter.get(item, 0)
                if extra > 0:
                    new.extend([item] * extra)
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
        direction = check.get("direction", "not_decrease")
        if direction not in _VALID_DIRECTIONS:
            return CheckResult(name, ctype, "error",
                               f"count.direction 值「{direction}」无效，必须为 {sorted(_VALID_DIRECTIONS)}")
        current = _measure_count(check, out)
        if baseline is not None:
            if not isinstance(baseline.get("value"), int):
                return CheckResult(name, ctype, "error",
                                   f"基线 value 类型错误（期望 int，实际 {type(baseline.get('value')).__name__}），需重新采集基线")
            base_val = baseline["value"]
            if direction == "not_decrease" and current < base_val:
                return CheckResult(name, ctype, "fail", f"{current} < 基线 {base_val}", value=current)
            if direction == "not_increase" and current > base_val:
                return CheckResult(name, ctype, "fail", f"{current} > 基线 {base_val}", value=current)
            return CheckResult(name, ctype, "pass", f"{current}（基线 {base_val}）", value=current)
        threshold = check.get("threshold")
        if isinstance(threshold, int):
            # not_decrease → threshold 为下限，current 不得低于它
            # not_increase → threshold 为上限，current 不得高于它
            if direction == "not_decrease" and current < threshold:
                return CheckResult(name, ctype, "fail", f"{current} < 下限阈值 {threshold}", value=current)
            if direction == "not_increase" and current > threshold:
                return CheckResult(name, ctype, "fail", f"{current} > 上限阈值 {threshold}", value=current)
        return CheckResult(name, ctype, "pass", f"{current}", value=current)

    return CheckResult(name, ctype, "error", f"未知 check 类型：{ctype}")


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
    """采集基线：只记录 baseline_aware 检查的当前"值"。

    注意：forbid_pattern 检查在采基线阶段返回 status="fail"（记录"已存在的违规"）
    是正常用途，照常写入其值；只有 status="error"（命令/配置执行错误，如工具缺失、
    正则非法、缺字段）才中止——否则会写入 value=None 的伪基线，让后续对比失真。
    """
    baseline: dict[str, Any] = {"checks": {}}
    errors: list[CheckResult] = []
    for check in config.get("checks", []):
        if not check.get("baseline_aware"):
            continue
        res = evaluate_check(check, baseline=None)
        if res.status == "error":
            errors.append(res)
            continue
        baseline["checks"][res.name] = {
            "type": res.type,
            "value": res.value,
            "fingerprint": _check_fingerprint(check),
        }
    if errors:
        print("[verify] 基线采集失败：以下 baseline-aware 检查无法产出可用基线，已中止。", file=sys.stderr)
        for r in errors:
            print(f"  [ERROR] {r.name} [{r.type}] {r.detail}", file=sys.stderr)
        return 2
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[verify] 基线已保存到 {out_path}（{len(baseline['checks'])} 项 baseline-aware 检查）")
    return 0


def cmd_verify(config: dict, baseline_path: Path | None, report_path: Path) -> int:
    """跑全部检查，对 baseline_aware 项做基线对比，产出报告。"""
    # 显式传了 --baseline 但文件不存在 → fail-closed，不能静默降级为无基线模式
    if baseline_path is not None and not baseline_path.exists():
        print(f"[verify] 指定了 --baseline 但文件不存在：{baseline_path}，需先运行 --save-baseline 采集基线。", file=sys.stderr)
        return 2

    baseline_data: dict[str, Any] = {}
    if baseline_path and baseline_path.exists():
        try:
            baseline_data = json.loads(baseline_path.read_text(encoding="utf-8")).get("checks", {})
        except json.JSONDecodeError as exc:
            print(f"[verify] 基线解析失败：{exc}", file=sys.stderr)
            return 2

    results: list[CheckResult] = []
    for check in config.get("checks", []):
        name = check.get("name", "<unnamed>")
        base_entry = None
        if check.get("baseline_aware"):
            if baseline_path is not None:
                # baseline 显式指定：baseline_aware 检查必须在基线中；
                # 缺失条目不降级为无基线模式（count 无基线会静默 pass，门禁形同虚设）
                if name not in baseline_data:
                    results.append(CheckResult(
                        name, check.get("type", "?"), "error",
                        "baseline_aware 检查在基线文件中无对应条目，需重新运行 --save-baseline 更新基线",
                    ))
                    continue
                base_entry = baseline_data[name]
                # 校验 check 指纹：如果 command/direction 等关键字段在采集基线后被改变，
                # 已存储的基线值不再对应当前检查的语义，继续对比会产生错误结论。
                stored_fp = base_entry.get("fingerprint")
                if stored_fp is not None:
                    current_fp = _check_fingerprint(check)
                    if current_fp != stored_fp:
                        results.append(CheckResult(
                            name, check.get("type", "?"), "error",
                            f"check 配置与采集基线时不一致，需重新运行 --save-baseline 更新基线"
                            f"（存储：{stored_fp}，当前：{current_fp}）",
                        ))
                        continue
            # baseline_path 为 None → 不带基线运行，对存量项目无侵入
        results.append(evaluate_check(check, base_entry))

    failed = [r for r in results if r.status != "pass"]  # fail（违规）与 error（执行错误）都不放过
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
        mark = {"pass": "[PASS]", "fail": "[FAIL]", "error": "[ERR ]"}.get(r.status, "[????]")
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
