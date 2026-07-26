"""交付门：宣布交付前的确定性检查，替代「AI 自述已完成」。

- **任务终态**（`--tasks`）：tasks.md 每个任务的 `状态` 必须是
  完成 / 需人工 / 阻塞；`需人工` 与 `阻塞` 必须附原因
  （状态行内附注，或单独的 `- 原因:` 字段）。同时校验状态字段、任务头
  标记与任务块复选框三向一致——只改状态字段不勾选复选框视为矛盾。
- **spec 已归档**（`--spec`）：`**状态**:` 必须为 `Archived`。
- **工作区干净**（总是检查）：`git status --porcelain` 必须为空——
  代码与归档产物（spec / tasks / ADR / issues）都已提交本地 git。

Fast-Path 兼容别名（无 spec / tasks）还必须传 lightweight integration Review、
独立 Verify 报告与结构化知识影响结论；`none` 必须附理由。
Native Delivery 使用标准 integration Review 与独立 Verify；只有完整 Runtime Run 使用
scope=run、strict Review 与 Run-bound Artifact。
非 0 退出即禁止宣布交付；输出应原样贴进交付报告。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_spec
import lint_task_deps

_FRAMEWORK_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_FRAMEWORK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_SCRIPTS))
import runtime_workflow
import runtime_schema
import workspace_residue

TERMINAL_STATES = {"完成", "需人工", "阻塞"}
NEEDS_REASON = {"需人工", "阻塞"}


def check_tasks(text: str) -> list[str]:
    """所有任务须处于终态；需人工 / 阻塞 须附原因。"""
    try:
        tasks = lint_task_deps.parse_tasks(text)
    except ValueError as error:
        return [f"tasks.md 解析失败：{error}"]
    if not tasks:
        return ["tasks.md 未解析到任何任务（检查 `### 任务 N:` 格式）"]

    errors: list[str] = []
    for tid, info in sorted(tasks.items()):
        value = lint_task_deps.field(info["body"], "状态")
        state = lint_task_deps.parse_state(value)
        if state is None:
            errors.append(f"任务 {tid} 缺少合法的 状态 字段")
        elif state not in TERMINAL_STATES:
            errors.append(
                f"任务 {tid} 状态为 `{state}`，未到终态（完成 / 需人工 / 阻塞）"
            )
        elif state in NEEDS_REASON:
            note = value[len(state) :].strip(" \t:：，,()（）-")
            reason = lint_task_deps.field(info["body"], "原因")
            if not note and not reason:
                errors.append(
                    f"任务 {tid} 标 `{state}` 但未附原因"
                    f"（状态行内补说明，或加 `- 原因:` 字段）"
                )
    # 状态字段只是完成信号之一：任务头标记与验收 / 子任务复选框必须同向，
    # 否则归档记录自相矛盾（只改状态字段即可过门）。归档移动前应先跑
    # `lint_task_deps.py --state-consistency`，此处是兜底。
    errors.extend(lint_task_deps.state_consistency_errors(text))
    return errors


def check_spec(text: str) -> list[str]:
    """spec 状态必须为 Archived。"""
    status = lint_spec.parse_status(text)
    if status != "Archived":
        return [f"spec 状态为 `{status or '缺失'}`，交付前应改为 Archived"]
    return []


def check_review_report(
    path: Path,
    run_dir: Path | None = None,
    expected_scope: str = "run",
    expected_profile: str | None = None,
) -> list[str]:
    """Review 报告须符合当前交付路径要求的机器可读裁决字段。"""
    if not path.is_file():
        return [f"找不到 Review 报告 {path}"]
    try:
        if run_dir is None:
            report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            payload = report
        else:
            report = runtime_workflow.load_bound_report(
                run_dir, path, "review-report"
            )
            payload = report["payload"]
    except (OSError, ValueError, runtime_workflow.RuntimeWorkflowError) as error:
        return [f"Review 报告解析失败：{error}"]

    if not isinstance(report, dict):
        return ["Review 报告顶层结构必须是 JSON 对象"]

    errors: list[str] = []
    if payload.get("verdict") != "PASS":
        errors.append(f"Review 报告 verdict 不是 PASS：{payload.get('verdict')!r}")
    for field in ("p0_count", "p1_count"):
        count = payload.get(field)
        if not isinstance(count, int) or isinstance(count, bool) or count != 0:
            errors.append(f"Review 报告 {field} 必须为整数 0：{count!r}")
    if payload.get("scope") != expected_scope:
        errors.append(
            "Review 报告 scope 不是 "
            f"{expected_scope}：{payload.get('scope')!r}"
        )
    profile = payload.get("review_profile")
    if profile not in {"lightweight", "standard", "strict"}:
        errors.append("Review 报告 review_profile 非法：" f"{profile!r}")
    elif expected_profile is not None and profile != expected_profile:
        errors.append(
            "Review 报告 review_profile 必须为 "
            f"{expected_profile}：{profile!r}"
        )
    round_number = payload.get("round")
    if (
        not isinstance(round_number, int)
        or isinstance(round_number, bool)
        or round_number < 0
    ):
        errors.append(f"Review 报告 round 必须为非负整数：{round_number!r}")
    return errors


def check_fast_path_review(path: Path) -> list[str]:
    """Legacy Fast-Path is a Native Delivery alias with lightweight review."""
    found = check_review_report(
        path,
        run_dir=None,
        expected_scope="integration",
        expected_profile="lightweight",
    )
    if found:
        return found
    report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    unexpected = sorted(set(report) - NATIVE_DELIVERY_REVIEW_FIELDS)
    if unexpected:
        return ["Fast-Path Review 包含无 Run 合同外字段：" + ", ".join(unexpected)]
    return []


NATIVE_DELIVERY_REVIEW_FIELDS = {
    "verdict",
    "p0_count",
    "p1_count",
    "scope",
    "review_profile",
    "round",
}
NATIVE_DELIVERY_VERIFY_FIELDS = {
    "verdict",
    "total",
    "errors",
    "violations",
    "spec_drift",
    "warnings",
    "results",
}


def check_native_delivery_review(path: Path) -> list[str]:
    """Require an unbound standard integration review for Native Delivery."""
    found = check_review_report(
        path,
        expected_scope="integration",
        expected_profile="standard",
    )
    if found:
        return found
    try:
        report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"Native Delivery Review 报告解析失败：{error}"]
    unexpected = sorted(set(report) - NATIVE_DELIVERY_REVIEW_FIELDS)
    if unexpected:
        return [
            "Native Delivery Review 包含无 Run 合同外字段："
            + ", ".join(unexpected)
        ]
    return []


NATIVE_DELIVERY_VERIFY_RESULT_FIELDS = {
    "name",
    "type",
    "status",
    "detail",
    "value",
    "new_items",
}
NATIVE_DELIVERY_FORBIDDEN_CLAIM_FIELDS = {
    "run_id",
    "harness",
    "config_digest",
    "trust_gate",
    "harness_capability_probe",
    "run_manifest_evidence_graph",
    "implementer_actor",
    "judge_actor",
    "independence_basis",
    "strict_independent_review",
}


def _find_native_forbidden_claim_fields(value: object) -> list[str]:
    """Find Runtime, Trust, or strict-review fields at any nested evidence level."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in NATIVE_DELIVERY_FORBIDDEN_CLAIM_FIELDS:
                found.add(key)
            found.update(_find_native_forbidden_claim_fields(nested))
    elif isinstance(value, list):
        for nested in value:
            found.update(_find_native_forbidden_claim_fields(nested))
    return sorted(found)


def _check_native_verify_result(value: object, label: str) -> list[str]:
    """Validate the flat check-result shape emitted by workflow-verification."""
    if not isinstance(value, dict):
        return [f"Native Delivery Verify {label} 必须为对象"]
    missing = sorted(NATIVE_DELIVERY_VERIFY_RESULT_FIELDS - set(value))
    if missing:
        return [
            f"Native Delivery Verify {label} 缺少必填字段："
            + ", ".join(missing)
        ]
    unexpected = sorted(set(value) - NATIVE_DELIVERY_VERIFY_RESULT_FIELDS)
    if unexpected:
        return [
            f"Native Delivery Verify {label} 包含合同外字段："
            + ", ".join(unexpected)
        ]
    forbidden = _find_native_forbidden_claim_fields(value)
    if forbidden:
        return [
            f"Native Delivery Verify {label} 包含 Runtime、Trust 或严格独立性字段："
            + ", ".join(forbidden)
        ]
    for field in ("name", "type", "detail"):
        if not isinstance(value[field], str):
            return [f"Native Delivery Verify {label}.{field} 必须为字符串"]
    if not isinstance(value["new_items"], list) or any(
        not isinstance(item, str) for item in value["new_items"]
    ):
        return [f"Native Delivery Verify {label}.new_items 必须为字符串数组"]
    return []


def check_native_delivery_verify(path: Path) -> list[str]:
    """Require a flat verify report without Runtime or Trust declarations."""
    found = check_verify_report(path)
    if found:
        return found
    try:
        report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"Native Delivery Verify 报告解析失败：{error}"]
    unexpected = sorted(set(report) - NATIVE_DELIVERY_VERIFY_FIELDS)
    if unexpected:
        return [
            "Native Delivery Verify 包含无 Run 合同外字段："
            + ", ".join(unexpected)
        ]

    errors: list[str] = []
    results = report.get("results")
    total = report.get("total")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        errors.append("Native Delivery Verify total 必须为正整数")
    if not isinstance(results, list) or not results:
        errors.append("Native Delivery Verify results 必须为非空数组")
    else:
        if total != len(results):
            errors.append("Native Delivery Verify total 必须等于 results 数量")
        for index, result in enumerate(results):
            errors.extend(_check_native_verify_result(result, f"results[{index}]"))
            if isinstance(result, dict) and result.get("status") != "pass":
                errors.append(
                    f"Native Delivery Verify results[{index}].status 必须为 pass"
                )
    spec_drift = report.get("spec_drift")
    if spec_drift is None:
        errors.append("Native Delivery Verify spec_drift 必须为完整的 pass CheckResult")
    else:
        errors.extend(_check_native_verify_result(spec_drift, "spec_drift"))
        if isinstance(spec_drift, dict) and spec_drift.get("status") != "pass":
            errors.append("Native Delivery Verify spec_drift.status 必须为 pass")
    warnings = report.get("warnings")
    if not isinstance(warnings, list) or any(
        not isinstance(warning, str) for warning in warnings
    ):
        errors.append("Native Delivery Verify warnings 必须为字符串数组")
    return errors

def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path stays below parent, including resolved symlinks."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def check_native_delivery_verdict_path(
    repo: Path,
    verdict_path: Path,
    review_path: Path,
    verify_path: Path,
) -> list[str]:
    """Keep Native artifacts ignored, non-destructive, and outside Runtime runs."""
    resolved_verdict = verdict_path.resolve()
    resolved_inputs = {review_path.resolve(), verify_path.resolve()}
    if resolved_verdict in resolved_inputs:
        return ["--native-delivery-verdict 不得覆盖 Review 或 Verify 证据"]
    if resolved_verdict.exists():
        return ["--native-delivery-verdict 已存在；不得覆盖既有交付 Artifact"]

    native_dir = (repo.resolve() / ".agentic-framework" / "native-delivery").resolve()
    if not _is_relative_to(resolved_verdict, native_dir):
        return [
            "--native-delivery-verdict 必须位于 "
            "<repo>/.agentic-framework/native-delivery/"
        ]

    try:
        vcs = workspace_residue.detect_vcs(repo)
    except workspace_residue.WorkspaceResidueError as error:
        return [f"无法判定 Native Delivery 产物的 VCS：{error}"]
    if vcs == "svn":
        return []
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            str(resolved_verdict),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return []
    if result.returncode == 1:
        return ["--native-delivery-verdict 必须被 Git 忽略"]
    return [f"git check-ignore 执行失败：{result.stderr.strip()}"]


def check_verify_report(path: Path) -> list[str]:
    """Unbound delivery paths require a PASS machine verification report."""
    if not path.is_file():
        return [f"找不到机器验证报告 {path}（先跑 workflow-verification）"]
    try:
        report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"机器验证报告解析失败：{error}"]
    if not isinstance(report, dict):
        return ["机器验证报告顶层结构必须是 JSON 对象"]
    errors: list[str] = []
    if report.get("verdict") != "PASS":
        errors.append(f"机器验证 verdict 非 PASS：{report.get('verdict')!r}")
    for field in ("errors", "violations"):
        value = report.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            errors.append(f"机器验证 {field} 必须为整数 0：{value!r}")
    return errors


def check_scoped_delivery(
    repo: Path,
    baseline_path: Path,
    delivery_commit: str | None,
    delivery_revision: str | None,
) -> list[str]:
    """校验冻结范围内的提交，以及 S0/S1 预存残留不变。"""
    if not baseline_path.is_file():
        return [f"找不到 Scoped Delivery 基线 {baseline_path}"]
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        snapshot = baseline["workspace_residue_snapshot"]
        stored = workspace_residue.validate_workspace_residue_snapshot(snapshot)
        vcs = stored["vcs"]
        if vcs == "git":
            if not delivery_commit or delivery_revision:
                return ["Git Scoped Delivery 必须提供 --delivery-commit，且不得提供 --delivery-revision"]
            paths = workspace_residue.git_commit_paths(
                repo, stored["base_ref"], delivery_commit
            )
        else:
            if not delivery_revision or delivery_commit:
                return ["SVN Scoped Delivery 必须提供 --delivery-revision，且不得提供 --delivery-commit"]
            paths = workspace_residue.svn_revision_paths(repo, delivery_revision)
        outside = workspace_residue.validate_delivery_paths(
            paths, stored["scope_paths"]
        )
        if outside:
            return ["交付提交超出冻结范围：" + ", ".join(outside)]
        residue_changes = workspace_residue.compare_workspace_residue(repo, stored)
        if residue_changes:
            return ["预存残留与 S0 不一致：" + ", ".join(residue_changes)]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, workspace_residue.WorkspaceResidueError) as error:
        return [f"Scoped Delivery 校验失败：{error}"]
    return []


def check_git_clean(repo: Path) -> list[str]:
    """git 工作区（含未跟踪文件）必须干净。"""
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return [f"git status 执行失败：{result.stderr.strip()}"]
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        shown = "；".join(dirty[:10])
        suffix = f"（共 {len(dirty)} 项）" if len(dirty) > 10 else ""
        return [f"工作区不干净，未提交改动：{shown}{suffix}"]
    return []


def check_knowledge_impact(impact: str | None, reason: str) -> list[str]:
    """Every delivery path must declare its knowledge impact."""
    if impact is None:
        return ["缺少 --knowledge-impact hit|none"]
    if impact == "none" and not reason.strip():
        return ["--knowledge-impact none 必须提供 --knowledge-impact-reason"]
    return []


def write_native_delivery_verdict(path: Path, verdict: dict) -> None:
    """Atomically write one validated Native Delivery Verdict artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(verdict, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        os.unlink(temporary)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    """Run the delivery gate and report per-check results."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8"
        )  # Windows 控制台默认非 UTF-8，避免中文乱码

    parser = argparse.ArgumentParser(description="交付前确定性门禁")
    parser.add_argument("--tasks", type=Path, help="tasks.md 路径（标准流程必传）")
    parser.add_argument("--spec", type=Path, help="spec.md 路径（标准流程必传）")
    parser.add_argument(
        "--repo", type=Path, default=Path("."), help="git 仓库根，默认当前目录"
    )
    parser.add_argument(
        "--run-dir", type=Path, help="已初始化的 Runtime Run 目录"
    )
    parser.add_argument(
        "--native-delivery",
        action="store_true",
        help="生成无 Runtime Run 的有界 Native Delivery Verdict",
    )
    parser.add_argument(
        "--native-delivery-verdict",
        type=Path,
        help="Native Delivery Verdict 的 JSON 输出路径",
    )
    parser.add_argument(
        "--knowledge-impact",
        choices=("hit", "none"),
        help="所有交付路径必填的长期知识影响结论",
    )
    parser.add_argument(
        "--knowledge-impact-reason",
        default="",
        help="知识无影响的理由；--knowledge-impact none 时必填",
    )
    parser.add_argument(
        "--scoped-delivery",
        action="store_true",
        help="显式启用 Scoped Delivery：校验冻结范围与预存残留 S0/S1 一致性",
    )
    parser.add_argument(
        "--workspace-residue-baseline",
        type=Path,
        help="Verify --save-baseline 写入的 Scoped Delivery 基线路径",
    )
    parser.add_argument(
        "--delivery-commit",
        help="Git Scoped Delivery 的交付提交；必须等于当前 HEAD",
    )
    parser.add_argument(
        "--delivery-revision",
        help="SVN Scoped Delivery 的已提交 revision",
    )
    parser.add_argument(
        "--review-report",
        type=Path,
        required=True,
        help="workflow-code-review 产出的 review-report.json 路径（Fast-Path 亦必传）",
    )
    parser.add_argument(
        "--verify-report",
        type=Path,
        default=Path(".agentic-framework/verify/report.json"),
        help="workflow-verification 产出的机器验证报告路径（Fast-Path 必传）",
    )
    args = parser.parse_args(argv)

    if args.run_dir is not None and args.native_delivery:
        print("error: --run-dir 与 --native-delivery 不能同时提供", file=sys.stderr)
        return 2
    if args.scoped_delivery and args.run_dir is not None:
        print("error: Scoped Delivery 不适用于完整 Runtime Run；请使用干净 worktree", file=sys.stderr)
        return 2
    if args.scoped_delivery and not args.native_delivery:
        print("error: --scoped-delivery 必须与 --native-delivery 一起使用", file=sys.stderr)
        return 2
    scoped_arguments = (
        args.workspace_residue_baseline,
        args.delivery_commit,
        args.delivery_revision,
    )
    if args.scoped_delivery and args.workspace_residue_baseline is None:
        print("error: --scoped-delivery 必须提供 --workspace-residue-baseline", file=sys.stderr)
        return 2
    if not args.scoped_delivery and any(value is not None for value in scoped_arguments):
        print("error: Scoped Delivery 参数必须与 --scoped-delivery 一起使用", file=sys.stderr)
        return 2
    if args.native_delivery and args.native_delivery_verdict is None:
        print(
            "error: --native-delivery 必须提供 --native-delivery-verdict",
            file=sys.stderr,
        )
        return 2
    if not args.native_delivery and args.native_delivery_verdict is not None:
        print(
            "error: --native-delivery-verdict 仅可与 --native-delivery 一起使用",
            file=sys.stderr,
        )
        return 2
    if args.native_delivery:
        found = check_native_delivery_verdict_path(
            args.repo,
            args.native_delivery_verdict,
            args.review_report,
            args.verify_report,
        )
        if found:
            print("error: " + "；".join(found), file=sys.stderr)
            return 2

    if (args.tasks is None) != (args.spec is None):
        print(
            "error: --tasks 与 --spec 必须同时提供（标准交付）或同时省略（Fast-Path 兼容别名）",
            file=sys.stderr,
        )
        return 2
    if args.native_delivery and args.tasks is None:
        print(
            "error: --native-delivery 必须提供 --tasks 与 --spec（标准交付）",
            file=sys.stderr,
        )
        return 2
    if args.scoped_delivery and args.tasks is None:
        print(
            "error: --scoped-delivery 必须提供 --tasks 与 --spec（标准交付）",
            file=sys.stderr,
        )
        return 2

    errors: list[str] = []
    checks = 0

    checks += 1
    found = check_knowledge_impact(
        args.knowledge_impact, args.knowledge_impact_reason
    )
    errors.extend(found)
    if args.scoped_delivery:
        path_name = "Scoped Delivery"
    elif args.run_dir is not None:
        path_name = "Runtime Run"
    elif args.native_delivery:
        path_name = "Native Delivery"
    else:
        path_name = "Fast-Path"
    print(
        ("ERROR  " + "；".join(found))
        if found
        else (
            f"PASS   {path_name} 知识影响：命中"
            if args.knowledge_impact == "hit"
            else f"PASS   {path_name} 知识影响：未命中；"
            f"理由：{args.knowledge_impact_reason.strip()}"
        )
    )

    for label, path, checker in (
        ("tasks.md 全部任务处于终态且附原因", args.tasks, check_tasks),
        ("spec 已归档（Archived）", args.spec, check_spec),
    ):
        if path is None:
            continue
        checks += 1
        if not path.is_file():
            print(f"error: 找不到 {path}", file=sys.stderr)
            return 2
        found = checker(path.read_text(encoding="utf-8", errors="replace"))
        errors.extend(found)
        print(("ERROR  " + "；".join(found)) if found else f"PASS   {label}")

    checks += 1
    if args.scoped_delivery:
        found = check_scoped_delivery(
            args.repo,
            args.workspace_residue_baseline,
            args.delivery_commit,
            args.delivery_revision,
        )
        success = "PASS   本次交付范围干净，预存残留未变化"
    else:
        found = check_git_clean(args.repo)
        success = "PASS   工作区干净（代码与归档产物已提交）"
    errors.extend(found)
    print(("ERROR  " + "；".join(found)) if found else success)

    checks += 1
    if args.run_dir is not None:
        found = check_review_report(
            args.review_report,
            args.run_dir,
            expected_scope="run",
            expected_profile="strict",
        )
        errors.extend(found)
        print(
            ("ERROR  " + "；".join(found))
            if found
            else "PASS   Review 报告 verdict=PASS 且 P0/P1=0"
        )
    elif args.native_delivery:
        found = check_native_delivery_review(args.review_report)
        errors.extend(found)
        print(
            ("ERROR  " + "；".join(found))
            if found
            else "PASS   Native Delivery standard Review：verdict=PASS 且 P0/P1=0"
        )
        checks += 1
        verify_errors = check_native_delivery_verify(args.verify_report)
        errors.extend(verify_errors)
        print(
            ("ERROR  " + "；".join(verify_errors))
            if verify_errors
            else "PASS   Native Delivery 机器验证报告 verdict=PASS"
        )
    else:
        found = check_fast_path_review(args.review_report)
        errors.extend(found)
        print(
            ("ERROR  " + "；".join(found))
            if found
            else "PASS   Fast-Path 兼容别名 lightweight integration Review：verdict=PASS 且 P0/P1=0"
        )
        checks += 1
        verify_errors = check_native_delivery_verify(args.verify_report)
        errors.extend(verify_errors)
        print(
            ("ERROR  " + "；".join(verify_errors))
            if verify_errors
            else "PASS   Fast-Path 机器验证报告 verdict=PASS"
        )

    if not errors and args.run_dir is not None:
        if args.tasks is None:
            task_states = [
                {"task_id": "fast-path", "state": "completed", "attempts": 0}
            ]
        else:
            parsed = lint_task_deps.parse_tasks(
                args.tasks.read_text(encoding="utf-8", errors="replace")
            )
            state_names = {
                "完成": "completed",
                "需人工": "manual",
                "阻塞": "blocked",
            }
            task_states = []
            for task_id, task in sorted(parsed.items()):
                state = lint_task_deps.parse_state(
                    lint_task_deps.field(task["body"], "状态")
                )
                attempts = lint_task_deps.field(task["body"], "attempts") or "0"
                task_states.append(
                    {
                        "task_id": str(task_id),
                        "state": state_names[state],
                        "attempts": int(attempts),
                    }
                )
        try:
            trust_report = runtime_workflow.finalize_run(
                args.repo.resolve(),
                args.run_dir.resolve(),
                args.review_report.resolve(),
                task_states,
            )
            checks += 1
            print(
                "PASS   Runtime Manifest、Journal、Harness 与 Trust Gate："
                f"{trust_report['verdict']}"
            )
        except Exception as error:
            checks += 1
            errors.append(str(error))
            print(f"ERROR  Runtime 证据链：{error}")
    elif not errors and args.native_delivery:
        try:
            verdict = runtime_schema.build_native_delivery_verdict(
                str(args.review_report.resolve()),
                str(args.verify_report.resolve()),
                args.knowledge_impact,
                args.knowledge_impact_reason.strip(),
                args.scoped_delivery,
            )
            write_native_delivery_verdict(args.native_delivery_verdict, verdict)
            if args.scoped_delivery:
                post_write_errors = check_scoped_delivery(
                    args.repo,
                    args.workspace_residue_baseline,
                    args.delivery_commit,
                    args.delivery_revision,
                )
            else:
                post_write_errors = check_git_clean(args.repo)
            if post_write_errors:
                checks += 1
                errors.extend(post_write_errors)
                print("ERROR  " + "；".join(post_write_errors))
            else:
                checks += 1
                print("PASS   Native Delivery 裁决：native-delivery-pass")
                print(
                    "       verified_claims: "
                    + ", ".join(verdict["verified_claims"])
                )
                print(
                    "       unprovable_claims: "
                    + ", ".join(verdict["unprovable_claims"])
                )
        except (OSError, runtime_schema.RuntimeSchemaError) as error:
            checks += 1
            errors.append(f"Native Delivery Verdict 写入失败：{error}")
            print(f"ERROR  Native Delivery Verdict 写入失败：{error}")
    elif not errors:
        checks += 1
        print("PASS   Fast-Path 兼容别名交付裁决：fast-path-pass")
        print(
            "       verified_claims: git-clean, machine-verify, "
            "lightweight-review, knowledge-impact"
        )
        print(
            "       unprovable_claims: strict-independent-review, "
            "run-manifest-evidence-graph, harness-capability-probe"
        )

    print(f"\nchecks={checks} | errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
