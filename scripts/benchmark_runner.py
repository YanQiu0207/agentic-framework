"""Validate and summarize outcomes from real framework development tasks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

ROUTES = frozenset({"fast-path", "standard", "strict"})
FOLLOW_UP_STATUSES = frozenset({"pending", "no-rework", "reworked"})
TOKEN_FIELDS = ("input", "output", "cache_read", "cache_write")


class BenchmarkError(Exception):
    """Raised when a real-task benchmark record violates its contract."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BenchmarkError(f"cannot read JSON: {path}") from error
    if not isinstance(value, dict):
        raise BenchmarkError(f"JSON object required: {path}")
    return value


def _require_string(value: dict[str, Any], name: str) -> str:
    item = value.get(name)
    if not isinstance(item, str) or not item.strip():
        raise BenchmarkError(f"{name} must be a non-empty string")
    return item


def _require_nonnegative_int(value: dict[str, Any], name: str) -> int:
    item = value.get(name)
    if not isinstance(item, int) or isinstance(item, bool) or item < 0:
        raise BenchmarkError(f"{name} must be a non-negative integer")
    return item


def validate_case(case: dict[str, Any], outcome: dict[str, Any]) -> None:
    """Validate one manually curated task and its delivery outcome."""
    if case.get("schema_version") != 1 or outcome.get("schema_version") != 1:
        raise BenchmarkError("schema_version must be 1")
    task_id = _require_string(case, "task_id")
    if _require_string(outcome, "task_id") != task_id:
        raise BenchmarkError("outcome.task_id must match case.task_id")
    _require_string(case, "title")
    if case.get("route") not in ROUTES:
        raise BenchmarkError("case.route is invalid")
    if case.get("risk_level") not in {"low", "medium", "high"}:
        raise BenchmarkError("case.risk_level is invalid")
    criteria = case.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria or not all(
        isinstance(item, str) and item.strip() for item in criteria
    ):
        raise BenchmarkError("acceptance_criteria must contain non-empty strings")
    if outcome.get("final_verdict") not in {"accepted", "rejected", "manual"}:
        raise BenchmarkError("outcome.final_verdict is invalid")
    if not isinstance(outcome.get("first_acceptance"), bool):
        raise BenchmarkError("outcome.first_acceptance must be boolean")
    review = outcome.get("review")
    if not isinstance(review, dict):
        raise BenchmarkError("outcome.review must be an object")
    for name in ("p0_count", "p1_count", "rounds"):
        _require_nonnegative_int(review, name)
    follow_up = outcome.get("follow_up")
    if not isinstance(follow_up, dict):
        raise BenchmarkError("outcome.follow_up must be an object")
    if follow_up.get("status") not in FOLLOW_UP_STATUSES:
        raise BenchmarkError("outcome.follow_up.status is invalid")
    if follow_up.get("window_days") != 7:
        raise BenchmarkError("outcome.follow_up.window_days must be 7")
    refs = outcome.get("session_refs")
    if not isinstance(refs, list) or not refs:
        raise BenchmarkError("outcome.session_refs must be a non-empty array")
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict):
            raise BenchmarkError("session_refs items must be objects")
        identity = (_require_string(ref, "source"), _require_string(ref, "session"))
        if identity in seen:
            raise BenchmarkError("session_refs must not repeat one session")
        seen.add(identity)


def load_records(cases_root: Path) -> list[tuple[dict[str, Any], dict[str, Any], Path]]:
    """Load every completed record beneath the supplied case root."""
    records = []
    for case_path in sorted(cases_root.rglob("case.json")):
        outcome_path = case_path.with_name("outcome.json")
        if not outcome_path.is_file():
            continue
        case = _load_object(case_path)
        outcome = _load_object(outcome_path)
        validate_case(case, outcome)
        records.append((case, outcome, case_path.parent))
    if not records:
        raise BenchmarkError("no completed task records found")
    return records


def load_history(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Index valid telemetry ledger records by their stable source/session key."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise BenchmarkError(f"cannot read telemetry history: {path}") from error
    history = {}
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(item, dict):
            continue
        source, session = item.get("source"), item.get("session")
        if isinstance(source, str) and isinstance(session, str):
            history[(source, session)] = item
    return history


def _empty_summary() -> dict[str, Any]:
    return {
        "tasks": 0,
        "accepted": 0,
        "first_acceptance": 0,
        "review_p0": 0,
        "review_p1": 0,
        "review_rounds": 0,
        "follow_up_observed": 0,
        "reworked": 0,
        "active_seconds": 0.0,
        "tokens": {name: 0 for name in TOKEN_FIELDS},
    }


def _add_session(summary: dict[str, Any], session: dict[str, Any]) -> None:
    wall_seconds = session.get("wall_seconds", 0)
    idle_seconds = session.get("idle_seconds", 0)
    if (
        isinstance(wall_seconds, (int, float))
        and not isinstance(wall_seconds, bool)
        and isinstance(idle_seconds, (int, float))
        and not isinstance(idle_seconds, bool)
    ):
        summary["active_seconds"] += max(wall_seconds - idle_seconds, 0)
    model_tokens = session.get("model_tokens")
    if not isinstance(model_tokens, dict):
        return
    for values in model_tokens.values():
        if not isinstance(values, dict):
            continue
        for name in TOKEN_FIELDS:
            amount = values.get(name, 0)
            if isinstance(amount, int) and not isinstance(amount, bool):
                if amount < 0:
                    raise BenchmarkError(
                        f"model_tokens.{name} must be a non-negative integer"
                    )
                summary["tokens"][name] += amount


def _rates(summary: dict[str, Any]) -> dict[str, Any]:
    total = summary["tasks"]
    follow_up_total = summary["follow_up_observed"]
    return {
        **summary,
        "acceptance_rate": summary["accepted"] / total if total else None,
        "first_acceptance_rate": summary["first_acceptance"] / total if total else None,
        "rework_rate": summary["reworked"] / follow_up_total if follow_up_total else None,
    }


def build_report(
    records: list[tuple[dict[str, Any], dict[str, Any], Path]],
    history: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Join task outcomes to telemetry and summarize each workflow route."""
    groups = {route: _empty_summary() for route in sorted(ROUTES)}
    seen_sessions: set[tuple[str, str]] = set()
    for case, outcome, path in records:
        summary = groups[case["route"]]
        summary["tasks"] += 1
        summary["accepted"] += outcome["final_verdict"] == "accepted"
        summary["first_acceptance"] += outcome["first_acceptance"]
        summary["review_p0"] += outcome["review"]["p0_count"]
        summary["review_p1"] += outcome["review"]["p1_count"]
        summary["review_rounds"] += outcome["review"]["rounds"]
        follow_up = outcome["follow_up"]
        if follow_up["status"] != "pending":
            summary["follow_up_observed"] += 1
            summary["reworked"] += follow_up["status"] == "reworked"
        for ref in outcome["session_refs"]:
            identity = (ref["source"], ref["session"])
            if identity in seen_sessions:
                raise BenchmarkError(f"session is assigned to multiple tasks: {identity}")
            session = history.get(identity)
            if session is None:
                raise BenchmarkError(f"telemetry session not found for {path}: {identity}")
            seen_sessions.add(identity)
            _add_session(summary, session)
    overall = _empty_summary()
    for summary in groups.values():
        for name in (
            "tasks", "accepted", "first_acceptance", "review_p0", "review_p1",
            "review_rounds", "follow_up_observed", "reworked",
        ):
            overall[name] += summary[name]
        overall["active_seconds"] += summary["active_seconds"]
        for name in TOKEN_FIELDS:
            overall["tokens"][name] += summary["tokens"][name]
    return {
        "schema_version": 1,
        "artifact_type": "real-task-benchmark-report",
        "total": _rates(overall),
        "routes": {route: _rates(summary) for route, summary in groups.items()},
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="real-task benchmark collector")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate one completed task")
    validate.add_argument("--case-dir", required=True, type=Path)
    report = commands.add_parser("report", help="write a route comparison report")
    report.add_argument("--cases-root", required=True, type=Path)
    report.add_argument("--history", required=True, type=Path)
    report.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "validate":
            case_dir = args.case_dir
            validate_case(
                _load_object(case_dir / "case.json"),
                _load_object(case_dir / "outcome.json"),
            )
            print("PASS")
            return 0
        report = build_report(load_records(args.cases_root), load_history(args.history))
        write_report(args.output, report)
        print(f"report written: {args.output}")
        return 0
    except BenchmarkError as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
