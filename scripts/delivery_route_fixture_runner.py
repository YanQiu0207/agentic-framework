"""Execute deterministic fixtures for Native Delivery and Runtime routing."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW_SCRIPTS = _REPO_ROOT / "skills" / "workflow-code-generation" / "scripts"
if str(_WORKFLOW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_WORKFLOW_SCRIPTS))

import workflow_control

_ROUTE_FLAGS = frozenset(
    {
        "parallel_worktree_write",
        "long_task_recovery",
        "cross_host_capability_verification",
        "audit_required",
    }
)


class DeliveryRouteFixtureError(Exception):
    """Raised when a route fixture violates the stable fixture contract."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeliveryRouteFixtureError(f"{field} must be a non-empty string")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise DeliveryRouteFixtureError(f"{field} must be boolean")
    return value


def load_fixtures(path: Path) -> list[dict[str, Any]]:
    """Load and validate route fixtures before any route is selected."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DeliveryRouteFixtureError(f"cannot read fixtures: {path}") from error
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise DeliveryRouteFixtureError("fixture schema_version must be 1")
    if document.get("artifact_type") != "delivery-route-fixtures":
        raise DeliveryRouteFixtureError("fixture artifact_type is invalid")
    fixtures = document.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise DeliveryRouteFixtureError("fixtures must be a non-empty array")
    return fixtures


def evaluate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one fixture using the production route selector."""
    if not isinstance(fixture, dict):
        raise DeliveryRouteFixtureError("fixture must be an object")
    fixture_id = _require_string(fixture.get("id"), "id")
    route_input = fixture.get("input")
    expected = fixture.get("expected")
    if not isinstance(route_input, dict) or not isinstance(expected, dict):
        raise DeliveryRouteFixtureError(f"fixture {fixture_id} requires input and expected")
    unexpected = set(route_input) - ({"review_profile"} | _ROUTE_FLAGS)
    if unexpected:
        raise DeliveryRouteFixtureError(f"fixture {fixture_id} has unsupported input")
    profile = _require_string(route_input.get("review_profile"), "review_profile")
    flags = {
        flag: _require_bool(route_input.get(flag, False), flag)
        for flag in _ROUTE_FLAGS
    }
    expected_path = _require_string(expected.get("path"), "expected.path")
    expected_reasons = expected.get("runtime_upgrade_reasons")
    if not isinstance(expected_reasons, list) or not all(
        isinstance(reason, str) for reason in expected_reasons
    ):
        raise DeliveryRouteFixtureError(
            f"fixture {fixture_id} expected.runtime_upgrade_reasons is invalid"
        )
    route = workflow_control.select_execution_route(profile, **flags)
    actual = {
        "path": route.path,
        "runtime_upgrade_reasons": list(route.runtime_upgrade_reasons),
    }
    expected_value = {
        "path": expected_path,
        "runtime_upgrade_reasons": expected_reasons,
    }
    return {
        "id": fixture_id,
        "verdict": "PASS" if actual == expected_value else "FAIL",
        "expected": expected_value,
        "actual": actual,
    }


def run_fixtures(fixtures: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate all fixtures and fail the aggregate verdict on any drift."""
    results = [evaluate_fixture(fixture) for fixture in fixtures]
    passed = sum(result["verdict"] == "PASS" for result in results)
    return {
        "schema_version": 1,
        "artifact_type": "delivery-route-fixture-result",
        "verdict": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "results": results,
    }


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    """Write a fixture result atomically without replacing prior evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise DeliveryRouteFixtureError(f"refusing to overwrite existing artifact: {path}")
    descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise DeliveryRouteFixtureError(
                f"refusing to overwrite existing artifact: {path}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run delivery route fixtures")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=_REPO_ROOT / "evaluation" / "delivery-route-fixtures.json",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run route fixtures without network, containers, or task side effects."""
    args = _parse_args(argv)
    try:
        summary = run_fixtures(load_fixtures(args.fixtures))
        if args.output is not None:
            _atomic_write(args.output, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=4))
        return 0 if summary["verdict"] == "PASS" else 1
    except (OSError, UnicodeError, DeliveryRouteFixtureError, ValueError) as error:
        print(f"delivery route fixtures failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
