"""交付门：宣布交付前的确定性检查，替代「AI 自述已完成」。

- **任务终态**（`--tasks`）：tasks.md 每个任务的 `状态` 必须是
  完成 / 需人工 / 阻塞；`需人工` 与 `阻塞` 必须附原因
  （状态行内附注，或单独的 `- 原因:` 字段）。同时校验状态字段、任务头
  标记与任务块复选框三向一致——只改状态字段不勾选复选框视为矛盾。
- **spec 已归档**（`--spec`）：`**状态**:` 必须为 `Archived`。
- **工作区状态**（总是检查，按后端分派）：Git 要求 `git status --porcelain`
  为空；原生 SVN 的预期本地改动不走 Git clean，输出 `svn-pending-commit`
  （本地已验证待提交，不是正式交付 PASS）。

Fast-Path 兼容别名（无 spec / tasks）还必须传 lightweight integration Review、
独立 Verify 报告与结构化知识影响结论；`none` 必须附理由。
Native Delivery 使用标准 integration Review 与独立 Verify；只有完整 Runtime Run 使用
scope=run、strict Review 与 Run-bound Artifact。
Native 证据为 v2 合同（顶层 schema_version=2 与 subject_id）：交付门重算当前
内容主体并交叉核对 Review/Verify/当前三方一致（`--subject-base` 须与 Verify 的
--diff-base 一致）；旧 v1 报告只按旧合同展示历史，不能作为新交付证据。
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
import native_delivery
import native_subject
import runtime_workflow
import vcs
import workspace_residue
import knowledge_sync
import governance_profile

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
            # 按原始匹配前缀切片：归一后 state 是规范值而 value 是原始值，
            # 长度不再对应（如 `blocked 依赖外部审批` → `阻塞`）。
            prefix = lint_task_deps.state_prefix(value) or ""
            note = value[len(prefix) :].strip(" \t:：，,()（）-")
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


def _load_native_report(path: Path, label: str) -> tuple[dict | None, list[str]]:
    """Parse one Native v2 report file with directed errors."""
    if not path.is_file():
        return None, [f"找不到{label}报告 {path}"]
    try:
        report = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [f"{label}报告解析失败：{error}"]
    if not isinstance(report, dict):
        return None, [f"{label}报告顶层结构必须是 JSON 对象"]
    return report, []


def check_fast_path_review(path: Path) -> list[str]:
    """Legacy Fast-Path is a Native Delivery alias with lightweight review.

    新证据为 v2 合同（含内容主体绑定）；旧六字段报告只按旧合同展示
    历史，不能作为新的交付证据。
    """
    report, errors = _load_native_report(path, "Fast-Path Review")
    if report is None:
        return errors
    if report.get("schema_version") != 2:
        return [
            "Fast-Path Review 必须为 schema_version 2 的 Native 报告，实际为 "
            f"{report.get('schema_version')!r}；旧六字段报告不能作为新交付证据"
        ]
    try:
        native_delivery.validate_review_report(report, "lightweight")
    except native_delivery.NativeDeliveryError as error:
        return [f"Fast-Path Review 未通过 Native v2 合同：{error}"]
    if report.get("scope") != "integration":
        return [f"Fast-Path Review scope 必须为 integration：{report.get('scope')!r}"]
    if report.get("verdict") != "PASS":
        return [f"Fast-Path Review verdict 不是 PASS：{report.get('verdict')!r}"]
    return []


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


def check_native_delivery_review(
    path: Path, expected_profile: str = "standard"
) -> list[str]:
    """Require a subject-bound v2 integration review at the expected profile.

    v2 strict 顶层三项独立性字段（implementer_actor / judge_actor /
    independence_basis）由 Native 合同按档位强制；standard / lightweight
    携带独立性字段即拒绝。旧六字段报告只按旧合同展示历史，不能作为新
    交付证据。
    """
    report, errors = _load_native_report(path, "Native Delivery Review")
    if report is None:
        return errors
    if report.get("schema_version") != 2:
        return [
            "Native Delivery Review 必须为 schema_version 2 的 Native 报告，"
            f"实际为 {report.get('schema_version')!r}；"
            "旧六字段报告不能作为新交付证据"
        ]
    errors = []
    try:
        native_delivery.validate_review_report(report, expected_profile)
    except native_delivery.NativeDeliveryError as error:
        errors.append(f"Native Delivery Review 未通过 Native v2 合同：{error}")
    if report.get("scope") != "integration":
        errors.append(
            "Native Delivery Review scope 必须为 integration："
            f"{report.get('scope')!r}"
        )
    if report.get("verdict") != "PASS":
        errors.append(
            f"Native Delivery Review verdict 不是 PASS：{report.get('verdict')!r}"
        )
    for field in ("p0_count", "p1_count"):
        count = report.get(field)
        if not isinstance(count, int) or isinstance(count, bool) or count != 0:
            errors.append(
                f"Native Delivery Review {field} 必须为整数 0：{count!r}"
            )
    return errors


def check_native_delivery_verify(path: Path) -> list[str]:
    """Require a subject-bound Native v2 verify report.

    v2 合同校验结构、汇总一致性、spec_drift==results[0] 与递归独立性
    禁止集；本门额外要求 verdict=PASS 且所有结果 pass。旧 v1 扁平报告
    无内容绑定，不能作为新交付证据。
    """
    report, errors = _load_native_report(path, "Native Delivery Verify")
    if report is None:
        return errors
    if report.get("schema_version") != 2:
        return [
            "Native Delivery Verify 必须为 schema_version 2 的 Native 报告，"
            f"实际为 {report.get('schema_version')!r}；"
            "旧 v1 报告无内容绑定，请重跑 workflow-verification 取得新证据"
        ]
    try:
        native_delivery.validate_verify_report(report)
    except native_delivery.NativeDeliveryError as error:
        return [f"Native Delivery Verify 未通过 Native v2 合同：{error}"]
    errors = []
    if report.get("verdict") != "PASS":
        errors.append(
            f"Native Delivery Verify verdict 非 PASS：{report.get('verdict')!r}"
        )
    for index, result in enumerate(report["results"]):
        if result.get("status") != "pass":
            errors.append(
                f"Native Delivery Verify results[{index}].status 必须为 pass"
            )
    if report["spec_drift"].get("status") != "pass":
        errors.append("Native Delivery Verify spec_drift.status 必须为 pass")
    forbidden = _find_native_forbidden_claim_fields(report)
    if forbidden:
        errors.append(
            "Native Delivery Verify 包含 Runtime、Trust 或严格独立性字段："
            + ", ".join(forbidden)
        )
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


def check_review_profile_floor(
    repo: Path, tasks_path: Path, override: str | None
) -> list[str]:
    """review_profile 的 Profile 下限（change 2041）。

    惰性读取：只在有任务声明 lightweight 时才读取 Profile；读取失败
    （无 manifest 且未传 --governance-profile）失败关闭。
    """
    text = tasks_path.read_text(encoding="utf-8", errors="replace")
    tasks = lint_task_deps.parse_tasks(text)
    lightweight_ids = [
        tid
        for tid, info in sorted(tasks.items())
        for _name, value, _offset in info["review_profile_fields"]
        if value == "lightweight"
    ]
    if not lightweight_ids:
        return []
    profile = governance_profile.read_profile(repo, override)
    if not governance_profile.below_floor("lightweight", profile):
        return []
    return [
        f"任务 {lightweight_ids[0]} 的 review_profile 为 lightweight，"
        f"低于 {profile} 下限 {governance_profile.review_profile_floor(profile)}"
    ]


def _declared_review_profiles(tasks_path: Path) -> set[str]:
    """Collect the review_profile values declared by the tasks."""
    tasks = lint_task_deps.parse_tasks(
        tasks_path.read_text(encoding="utf-8", errors="replace")
    )
    return {
        value
        for _tid, info in tasks.items()
        for _name, value, _offset in info["review_profile_fields"]
    }


def _current_subject(repo: Path, base: str) -> tuple[dict | None, list[str]]:
    """Recompute the current Native subject for delivery-time binding.

    Git 用 --subject-base（与 Verify 的 --diff-base 一致）；纯 SVN 的固定
    基准取工作副本根的 WC revision（与 Verify 的主体捕获同源），CLI 的
    --subject-base 在 SVN 下不参与。
    """
    try:
        facts = vcs.inspect_workspace(repo)
    except vcs.VcsError as error:
        return None, [
            "无法判定交付工作区后端（"
            f"{error.code}: {error.operation}），"
            "Native Delivery 需要单一后端；双 VCS 工作副本请先确认开发后端"
        ]
    subject_base = facts["base"] if facts["backend"] == "svn" else base
    try:
        subject = native_subject.capture_subject(
            repo, subject_base, backend=facts["backend"]
        )
    except (native_subject.SubjectError, vcs.VcsError) as error:
        return None, [
            "无法重算当前内容主体（"
            f"{getattr(error, 'code', None) or type(error).__name__}: {error}），"
            "Native Delivery 需要可绑定的内容标识"
        ]
    if not subject["complete"]:
        shown = "; ".join(subject["limitations"][:5])
        return None, [f"当前内容主体覆盖不完整：{shown}"]
    return subject, []


def check_svn_pending_workspace(repo: Path) -> list[str]:
    """SVN 待提交状态检查：本地预期改动不适用 Git clean，只核可判定性。

    本地改动是 svn-pending-commit 的交付内容本身，由三方主体一致性绑定；
    此处只确认公共接口能完整判定该工作副本（冲突、混合版本、switched 等
    限制会在主体覆盖不完整处失败关闭）。
    """
    try:
        facts = vcs.inspect_workspace(repo, "svn")
    except vcs.VcsError as error:
        return [
            "无法判定 SVN 待提交工作副本（"
            f"{error.code}: {error.operation}）；"
            "原生 SVN 预期改动不走 Git clean，但工作副本必须可完整判定"
        ]
    if facts["conflicts"]:
        return [
            "SVN 工作副本存在未解决冲突："
            + ", ".join(facts["conflicts"][:10])
        ]
    return []


def check_knowledge_impact(impact: str | None, reason: str) -> list[str]:
    """Every delivery path must declare its knowledge impact."""
    if impact is None:
        return ["缺少 --knowledge-impact hit|none"]
    if impact == "none" and not reason.strip():
        return ["--knowledge-impact none 必须提供 --knowledge-impact-reason"]
    return []


def check_knowledge_sync(repo: Path, tasks_path: Path, impact: str | None) -> list[str]:
    """反自证交叉核对（change 2040）：从 Delta 反推应同步目标，与声明比对。

    只在声明 `hit` 时执行五类核对——漏报、误报、路径不匹配、同步状态
    未完成、知识冲突节为空或占位；声明 `none` 时只做矛盾核对（有 Delta
    却称无影响）。无 `specs/` 目录时退回同步目标存在性核对，证据强度低
    于 Delta 反推（报告行会体现该区分）。
    """
    if impact is None:
        return []  # 声明缺失由 check_knowledge_impact 负责
    change_dir = tasks_path.parent
    lines = tasks_path.read_text(encoding="utf-8", errors="replace").splitlines()
    mappings, invalid = knowledge_sync.delta_map(change_dir)
    errors: list[str] = []
    for delta in invalid:
        errors.append(
            f"Delta 路径不能映射到受控长期 Specs：{delta.relative_to(change_dir).as_posix()}"
        )
    if impact == "none":
        if mappings:
            errors.append("声明无长期知识影响，但 Change 包含 Delta")
        return errors
    row_targets: dict[str, str] = {}
    for _line_number, cells in knowledge_sync.sync_rows(lines):
        source, target, _action, status = cells[0], cells[1], cells[2], cells[3]
        row_targets[source] = target
        if status.casefold() not in knowledge_sync.COMPLETED_SYNC_STATUSES:
            errors.append(f"知识 {source} 的同步尚未完成（当前 `{status}`）")
    for source, expected in mappings.items():
        target = row_targets.get(source)
        if target is None:
            errors.append(f"Delta {source} 缺少知识同步记录（漏报）")
        elif target != expected:
            errors.append(
                f"Delta {source} 的目标路径不匹配：声明 `{target}`，应为 `{expected}`"
            )
    for source in row_targets:
        if source.startswith("specs/") and source not in mappings:
            errors.append(f"声明了 Delta {source} 但该文件不存在（误报）")
    conflict_body, _conflict_line = knowledge_sync.section_lines(lines, "知识冲突")
    conflict_text = "\n".join(conflict_body).strip()
    if not conflict_text or "待交付时填写" in conflict_text:
        errors.append("知识冲突检查缺失或仍是占位文字")
    if not mappings and not row_targets:
        errors.append("声明知识影响命中，但无 Delta 且无知识同步记录")
    if not mappings:
        # 无 specs/ 时的替代反向证据：目标真实存在。只能证明「声明的同步
        # 目标存在」，不能证明「该同步的都同步了」——强度低于 Delta 反推。
        for source, target in row_targets.items():
            if source.startswith("specs/"):
                continue
            if not (repo / target).exists():
                errors.append(f"知识同步目标不存在：{target}")
    return errors


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
    parser.add_argument(
        "--governance-profile",
        choices=("production", "tooling"),
        help="显式指定治理 Profile（覆盖 manifest 读取）",
    )
    parser.add_argument(
        "--subject-base",
        default="HEAD",
        help="重算当前内容主体的固定基准；须与 Verify 运行时的 --diff-base 一致",
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

    if args.tasks is not None:
        checks += 1
        found = check_knowledge_sync(args.repo, args.tasks, args.knowledge_impact)
        errors.extend(found)
        if args.knowledge_impact == "hit":
            sync_mode = (
                "Delta 反推"
                if (args.tasks.parent / "specs").is_dir()
                else "同步目标存在性（无 specs/，证据强度较低）"
            )
        else:
            sync_mode = "矛盾核对"
        print(
            ("ERROR  " + "；".join(found))
            if found
            else f"PASS   知识同步交叉核对（{sync_mode}）"
        )

        checks += 1
        try:
            found = check_review_profile_floor(
                args.repo, args.tasks, args.governance_profile
            )
        except governance_profile.GovernanceProfileError as error:
            found = [f"无法取得治理 Profile：{error}"]
        errors.extend(found)
        print(
            ("ERROR  " + "；".join(found))
            if found
            else "PASS   review_profile 满足 Profile 下限"
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
        try:
            delivery_backend = workspace_residue.detect_vcs(args.repo)
        except workspace_residue.WorkspaceResidueError as error:
            delivery_backend = None
            found = [f"无法判定交付工作区后端：{error}"]
        if delivery_backend == "git":
            found = check_git_clean(args.repo)
            success = "PASS   工作区干净（代码与归档产物已提交）"
        elif delivery_backend == "svn":
            # 原生 SVN 预期改动不走 Git clean：本地改动即待提交交付内容。
            found = check_svn_pending_workspace(args.repo)
            success = (
                "PASS   SVN 工作副本待提交状态（预期本地改动，不适用 Git clean）"
            )
        else:
            found = found or ["无法判定交付工作区后端"]
            success = ""
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
        try:
            delivery_profile = governance_profile.read_profile(
                args.repo, args.governance_profile
            )
        except governance_profile.GovernanceProfileError as error:
            delivery_profile = None
            errors.append(f"无法取得治理 Profile：{error}")
        # Production 下限 strict；Tooling 默认 standard，但任务自身声明
        # strict 时按实际风险档位要求 strict（独立 Judge 证据随之强制）。
        declared_profiles = _declared_review_profiles(args.tasks)
        expected_integration_profile = (
            "strict"
            if delivery_profile == "production" or "strict" in declared_profiles
            else "standard"
        )
        found = check_native_delivery_review(
            args.review_report, expected_integration_profile
        )
        errors.extend(found)
        print(
            ("ERROR  " + "；".join(found))
            if found
            else f"PASS   Native Delivery {expected_integration_profile} Review：verdict=PASS 且 P0/P1=0"
        )
        checks += 1
        verify_errors = check_native_delivery_verify(args.verify_report)
        errors.extend(verify_errors)
        print(
            ("ERROR  " + "；".join(verify_errors))
            if verify_errors
            else "PASS   Native Delivery 机器验证报告 verdict=PASS"
        )
        # 三方内容一致性（change 2048）：交付门重算当前 subject，与两份
        # v2 报告交叉核对；交付前编辑或检查基准不同都会被拒绝。
        checks += 1
        native_subject_capture: dict | None = None
        native_verify_report: dict | None = None
        native_review_report: dict | None = None
        if not found and not verify_errors:
            native_subject_capture, subject_errors = _current_subject(
                args.repo, args.subject_base
            )
            if subject_errors:
                errors.extend(subject_errors)
                print("ERROR  " + "；".join(subject_errors))
            else:
                native_verify_report, _ = _load_native_report(
                    args.verify_report, "Native Delivery Verify"
                )
                native_review_report, _ = _load_native_report(
                    args.review_report, "Native Delivery Review"
                )
                subject_mismatches = []
                for label, report in (
                    ("Verify", native_verify_report),
                    ("Review", native_review_report),
                ):
                    if report["subject_id"] != native_subject_capture["subject_id"]:
                        subject_mismatches.append(
                            f"{label} 报告与当前内容不一致"
                            f"（报告 {report['subject_id'][:19]}…，"
                            f"当前 {native_subject_capture['subject_id'][:19]}…）；"
                            "交付前内容变化或检查基准不同，"
                            "请对当前内容重跑受影响的 Verify/Review"
                        )
                if subject_mismatches:
                    errors.extend(subject_mismatches)
                    print("ERROR  " + "；".join(subject_mismatches))
                else:
                    print("PASS   Review/Verify/当前内容三方 subject 一致")
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
        if args.scoped_delivery:
            # Scoped Delivery 统一到 v2 合同（change 2048 Task 12）：Git 输出
            # git-scoped-delivery-pass（冻结范围 + 残留不变，不用虚假
            # git_clean 包装脏工作区）；SVN 只在接受确切 revision 隔离核验后
            # 输出 svn-revision-verified，查询门不代执行 commit/update。
            try:
                reason = args.knowledge_impact_reason.strip()
                if args.knowledge_impact == "hit" and not reason:
                    raise native_delivery.NativeDeliveryError(
                        "--knowledge-impact hit 生成 v2 Verdict 需要非空"
                        " --knowledge-impact-reason（说明更新了哪条知识）"
                    )
                baseline_payload = json.loads(
                    args.workspace_residue_baseline.read_text(encoding="utf-8")
                )
                stored = workspace_residue.validate_workspace_residue_snapshot(
                    baseline_payload["workspace_residue_snapshot"]
                )
                if stored["vcs"] == "git":
                    head_result = subprocess.run(
                        ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if head_result.returncode != 0:
                        raise native_delivery.NativeDeliveryError(
                            f"无法读取交付提交 HEAD：{head_result.stderr.strip()}"
                        )
                    verdict = native_delivery.build_verdict(
                        native_verify_report,
                        native_review_report,
                        subject_id=native_subject_capture["subject_id"],
                        vcs="git",
                        scoped=True,
                        delivery_evidence={
                            "commit_sha": head_result.stdout.strip(),
                            "scope_paths": stored["scope_paths"],
                            "residue_snapshot_digest": stored["snapshot_digest"],
                        },
                        verify_report_path=str(args.verify_report.resolve()),
                        review_report_path=str(args.review_report.resolve()),
                        knowledge_impact=(
                            "updated"
                            if args.knowledge_impact == "hit"
                            else "none"
                        ),
                        knowledge_impact_reason=reason,
                    )
                else:
                    svn_facts = vcs.inspect_workspace(args.repo, "svn")
                    # 确切 revision 隔离核验：节点基准、范围、内容与属性逐项
                    # 比对（公共只读接口，不 update/commit/revert）。SVN 可能
                    # 接纳他人不同文件的提交——验证只绑定核验过的 revision。
                    delivery = vcs.verify_delivery(
                        args.repo,
                        args.delivery_revision,
                        f"svn:r{stored['base_ref']}",
                        backend="svn",
                    )
                    if (
                        delivery["subject_id"]
                        != native_subject_capture["subject_id"]
                    ):
                        raise native_delivery.NativeDeliveryError(
                            "当前工作副本主体与确切 revision 主体不一致；"
                            "请更新到交付 revision 并对当前内容重跑受影响的"
                            " Verify/Review"
                        )
                    verdict = native_delivery.build_verdict(
                        native_verify_report,
                        native_review_report,
                        subject_id=native_subject_capture["subject_id"],
                        vcs="svn",
                        delivery_evidence={
                            "repository_uuid": svn_facts["repository_identity"][
                                "uuid"
                            ],
                            "repository_relative_url": svn_facts[
                                "repository_identity"
                            ]["relative_url"],
                            "revision": delivery["revision"],
                            "revision_subject_id": delivery["subject_id"],
                        },
                        verify_report_path=str(args.verify_report.resolve()),
                        review_report_path=str(args.review_report.resolve()),
                        knowledge_impact=(
                            "updated"
                            if args.knowledge_impact == "hit"
                            else "none"
                        ),
                        knowledge_impact_reason=reason,
                    )
                write_native_delivery_verdict(args.native_delivery_verdict, verdict)
                post_write_errors = check_scoped_delivery(
                    args.repo,
                    args.workspace_residue_baseline,
                    args.delivery_commit,
                    args.delivery_revision,
                )
                if post_write_errors:
                    checks += 1
                    errors.extend(post_write_errors)
                    print("ERROR  " + "；".join(post_write_errors))
                else:
                    checks += 1
                    print(f"PASS   Native Delivery 裁决：{verdict['verdict']}")
                    if verdict["verdict"] == "svn-revision-verified":
                        print(
                            "       正式交付 revision：r"
                            f"{verdict['evidence']['revision']}"
                            "（工作副本、Verify/Review 与该版本内容三方一致）"
                        )
                    print(
                        "       verified_claims: "
                        + ", ".join(verdict["verified_claims"])
                    )
                    print(
                        "       unprovable_claims: "
                        + ", ".join(verdict["unprovable_claims"])
                    )
            except (
                OSError,
                ValueError,
                vcs.VcsError,
                native_delivery.NativeDeliveryError,
            ) as error:
                checks += 1
                errors.append(f"Native Delivery Verdict 写入失败：{error}")
                print(f"ERROR  Native Delivery Verdict 写入失败：{error}")
        else:
            try:
                reason = args.knowledge_impact_reason.strip()
                if args.knowledge_impact == "hit" and not reason:
                    raise native_delivery.NativeDeliveryError(
                        "--knowledge-impact hit 生成 v2 Verdict 需要非空"
                        " --knowledge-impact-reason（说明更新了哪条知识）"
                    )
                try:
                    backend = workspace_residue.detect_vcs(args.repo)
                except workspace_residue.WorkspaceResidueError as error:
                    raise native_delivery.NativeDeliveryError(
                        f"无法判定交付后端：{error}"
                    ) from error
                if backend == "svn":
                    # 本地已验证、待 SVN 提交：完成报告状态，不是正式交付 PASS。
                    svn_facts = vcs.inspect_workspace(args.repo, "svn")
                    verdict = native_delivery.build_verdict(
                        native_verify_report,
                        native_review_report,
                        subject_id=native_subject_capture["subject_id"],
                        vcs="svn",
                        delivery_evidence={
                            "repository_uuid": svn_facts["repository_identity"][
                                "uuid"
                            ],
                            "repository_relative_url": svn_facts[
                                "repository_identity"
                            ]["relative_url"],
                        },
                        verify_report_path=str(args.verify_report.resolve()),
                        review_report_path=str(args.review_report.resolve()),
                        knowledge_impact=(
                            "updated"
                            if args.knowledge_impact == "hit"
                            else "none"
                        ),
                        knowledge_impact_reason=reason,
                    )
                    write_native_delivery_verdict(
                        args.native_delivery_verdict, verdict
                    )
                    post_write_errors = check_svn_pending_workspace(args.repo)
                    if post_write_errors:
                        checks += 1
                        errors.extend(post_write_errors)
                        print("ERROR  " + "；".join(post_write_errors))
                    else:
                        checks += 1
                        print(
                            "PASS   Native Delivery 裁决：svn-pending-commit"
                        )
                        print(
                            "       本地已验证，待 SVN 提交：这不是正式交付"
                            " PASS；正式交付需提交后以 --scoped-delivery "
                            "--delivery-revision 按确切 revision 核验"
                        )
                        print(
                            "       verified_claims: "
                            + ", ".join(verdict["verified_claims"])
                        )
                        print(
                            "       unprovable_claims: "
                            + ", ".join(verdict["unprovable_claims"])
                        )
                else:
                    head_result = subprocess.run(
                        ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    if head_result.returncode != 0:
                        raise native_delivery.NativeDeliveryError(
                            f"无法读取交付提交 HEAD：{head_result.stderr.strip()}"
                        )
                    verdict = native_delivery.build_verdict(
                        native_verify_report,
                        native_review_report,
                        subject_id=native_subject_capture["subject_id"],
                        vcs="git",
                        delivery_evidence={
                            "git_clean": True,
                            "commit_sha": head_result.stdout.strip(),
                        },
                        verify_report_path=str(args.verify_report.resolve()),
                        review_report_path=str(args.review_report.resolve()),
                        knowledge_impact=(
                            "updated" if args.knowledge_impact == "hit" else "none"
                        ),
                        knowledge_impact_reason=reason,
                    )
                    write_native_delivery_verdict(
                        args.native_delivery_verdict, verdict
                    )
                    post_write_errors = check_git_clean(args.repo)
                    if post_write_errors:
                        checks += 1
                        errors.extend(post_write_errors)
                        print("ERROR  " + "；".join(post_write_errors))
                    else:
                        checks += 1
                        print(f"PASS   Native Delivery 裁决：{verdict['verdict']}")
                        print(
                            "       verified_claims: "
                            + ", ".join(verdict["verified_claims"])
                        )
                        print(
                            "       unprovable_claims: "
                            + ", ".join(verdict["unprovable_claims"])
                        )
            except (
                OSError,
                vcs.VcsError,
                native_delivery.NativeDeliveryError,
            ) as error:
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
