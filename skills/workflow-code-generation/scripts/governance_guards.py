"""Production 治理守卫（change 2043）：挂在 `workflow_control` 转移上的前置条件。

守卫只在 `profile=production` 时生效；`tooling` 下全部关闭，状态机行为
与纯 Tooling 一致（降级等价）。守卫不新增转移，只增前置条件；每条守卫
在缺失证据时失败关闭。挂载映射见
`openspec/changes/2043-governance-overlay-merge/s53_mount_mapping.md`。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import lint_task_deps

_FRAMEWORK_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_FRAMEWORK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_SCRIPTS))
import task_ast
import validate_change

_REVIEW_PROFILE_NAMES = ("review_profile", "Review Profile")


def plan_gate_errors(repo: Path, change: Path, profile: str) -> list[str]:
    """合同二：Plan 总门。production 下进入执行前跑 `validate_change` plan 阶段。

    保留为独立的整体守卫，不拆散到各转移：总门失败时没有任何任务能进入
    执行状态机；执行期的逐转移守卫是总门之外的增量，不是替代。
    """
    if profile != "production":
        return []
    result = validate_change.validate_change(repo, change, "plan", profile_override=profile)
    if result.ok:
        return []
    first = result.findings[0] if result.findings else None
    detail = f"（首项 [{first.rule_id}] {first.message}）" if first else ""
    return [f"Plan 总门未通过：{len(result.findings)} 项确定性违规{detail}"]


def task_review_guard_errors(
    repo: Path, task_body: str, task_id: int, profile: str
) -> list[str]:
    """合同一：`merge_success` 前按 `review_profile` 校验逐任务 Review 证据。

    `standard` 要求一次综合审核证据；`strict` 要求报告档位为 `strict`。
    证据缺失、不合规或报告档位与声明不一致时，转移不发生（失败关闭）。
    逐任务触发，不存在「全部完成后统一收尾」的路径。
    """
    if profile != "production":
        return []
    body_lines = task_body.splitlines()
    profile_fields = task_ast.find_fields(body_lines, _REVIEW_PROFILE_NAMES)
    if not profile_fields:
        return [f"任务 {task_id} 缺少 review_profile 声明，无法判定 Review 档位"]
    declared = profile_fields[0][1]
    if declared not in {"standard", "strict"}:
        return [
            f"任务 {task_id} 的 review_profile 为 `{declared}`，"
            f"低于 production 下限 standard"
        ]
    task_review = task_ast.find_field(body_lines, ("Task Review",))
    if task_review is None or task_review[1].casefold() != "pass":
        return [f"任务 {task_id} 的 Task Review 未 PASS，完成转移不发生"]
    report_field = task_ast.find_field(body_lines, ("Review Report",))
    if report_field is None or not report_field[1]:
        return [f"任务 {task_id} 缺少 Review Report 字段"]
    report_errors = validate_change._validate_review_report(
        report_field[1], repo, "task"
    )
    if report_errors:
        return [f"任务 {task_id} 的 Review Report 无效：{report_errors[0]}"]
    report_path = repo / report_field[1].strip()
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"任务 {task_id} 的 Review Report 无法解析：{error}"]
    payload = report.get("payload")
    fields = payload if isinstance(payload, dict) else report
    if fields.get("review_profile") != declared:
        return [
            f"任务 {task_id} 声明 `{declared}` 但 Review Report 档位为 "
            f"`{fields.get('review_profile')}`，审核粒度与声明不一致"
        ]
    return []


def integration_review_guard_errors(review_fields: dict, profile: str) -> list[str]:
    """Delivery 前的五维 `strict` 集成审核守卫。

    production 下集成 Review 报告档位必须为 `strict`；`tooling` 下不启用
    （Native Delivery 的 `standard` 集成 Review 保持）。
    """
    if profile != "production":
        return []
    if review_fields.get("review_profile") != "strict":
        return [
            f"集成 Review 档位为 `{review_fields.get('review_profile')}`，"
            f"production 要求 strict 五维集成审核"
        ]
    return []


def guard_errors(
    tasks: dict[int, dict],
    task_id: int,
    event: str,
    profile: str,
    repo: Path,
    change: Path,
) -> list[str]:
    """转移守卫的统一入口：按事件分发到对应守卫。

    只增前置条件，不新增转移：`profile != "production"` 时全部返回空，
    与纯 Tooling 行为一致。
    """
    if profile != "production":
        return []
    if event == "start":
        return plan_gate_errors(repo, change, profile)
    if event == "merge_success":
        return task_review_guard_errors(repo, tasks[task_id]["body"], task_id, profile)
    return []
