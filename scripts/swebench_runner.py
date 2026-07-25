"""Plan or execute a bounded SWE-bench Verified evaluation.

The default mode only produces the official command plan.  It never imports
SWE-bench, contacts the network, or starts containers.  Container execution is
an explicit opt-in because the official SWE-bench evaluator builds and runs
repository images.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

DEFAULT_DATASET = "princeton-nlp/SWE-bench_Verified"
SWE_BENCH_VERSION = "4.1.0"
WSL_DOCKER_IMAGE = "python:3.11-slim"
REQUIRED_PREDICTION_FIELDS = (
    "instance_id",
    "model_name_or_path",
    "model_patch",
)


class SwebenchRunnerError(Exception):
    """Raised when a requested SWE-bench evaluation is unsafe or invalid."""


def _require_instance_ids(instance_ids: Sequence[str]) -> list[str]:
    values = list(instance_ids)
    if not values:
        raise SwebenchRunnerError("at least one --instance-id is required")
    if len(values) != len(set(values)):
        raise SwebenchRunnerError("--instance-id must not repeat")
    if any(not value.strip() for value in values):
        raise SwebenchRunnerError("--instance-id must not be empty")
    return values


def _validate_predictions(
    predictions_path: Path, instance_ids: Sequence[str]
) -> tuple[str, str]:
    """Validate selected predictions and return their digest and model name."""
    try:
        raw_content = predictions_path.read_bytes()
        lines = raw_content.decode("utf-8").splitlines()
    except OSError as error:
        raise SwebenchRunnerError(
            f"cannot read predictions file: {predictions_path}"
        ) from error
    except UnicodeDecodeError as error:
        raise SwebenchRunnerError(
            f"predictions file must use UTF-8: {predictions_path}"
        ) from error

    predicted_instance_ids: set[str] = set()
    selected_instance_ids = set(instance_ids)
    selected_model_names: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise SwebenchRunnerError(
                f"invalid JSONL prediction at line {line_number}"
            ) from error
        if not isinstance(record, dict):
            raise SwebenchRunnerError(
                f"prediction at line {line_number} must be a JSON object"
            )
        for field in REQUIRED_PREDICTION_FIELDS:
            if not isinstance(record.get(field), str):
                raise SwebenchRunnerError(
                    f"prediction at line {line_number} requires string field: {field}"
                )
        instance_id = record["instance_id"].strip()
        if not instance_id:
            raise SwebenchRunnerError(
                f"prediction at line {line_number} has an empty instance_id"
            )
        if instance_id in predicted_instance_ids:
            raise SwebenchRunnerError(
                f"prediction instance_id must not repeat: {instance_id}"
            )
        predicted_instance_ids.add(instance_id)
        if instance_id in selected_instance_ids:
            selected_model_names.add(record["model_name_or_path"])

    missing_instance_ids = set(instance_ids) - predicted_instance_ids
    if missing_instance_ids:
        missing = ", ".join(sorted(missing_instance_ids))
        raise SwebenchRunnerError(f"predictions missing selected instance_id: {missing}")
    unexpected_instance_ids = predicted_instance_ids - selected_instance_ids
    if unexpected_instance_ids:
        unexpected = ", ".join(sorted(unexpected_instance_ids))
        raise SwebenchRunnerError(
            f"predictions include unselected instance_id: {unexpected}"
        )
    if len(selected_model_names) != 1:
        raise SwebenchRunnerError(
            "selected predictions must use exactly one model_name_or_path"
        )
    return hashlib.sha256(raw_content).hexdigest(), selected_model_names.pop()


def build_official_command(
    predictions_path: Path,
    instance_ids: Sequence[str],
    run_id: str,
    max_workers: int,
    dataset_name: str = DEFAULT_DATASET,
) -> list[str]:
    """Build the official evaluator command without executing it."""
    instance_ids = _require_instance_ids(instance_ids)
    if not predictions_path.is_file():
        raise SwebenchRunnerError(f"predictions file does not exist: {predictions_path}")
    _validate_predictions(predictions_path, instance_ids)
    if not run_id.strip():
        raise SwebenchRunnerError("--run-id must not be empty")
    if max_workers < 1:
        raise SwebenchRunnerError("--max-workers must be at least 1")
    if dataset_name != DEFAULT_DATASET:
        raise SwebenchRunnerError("only SWE-bench Verified is supported")
    return [
        sys.executable,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        dataset_name,
        "--predictions_path",
        str(predictions_path.resolve()),
        "--max_workers",
        str(max_workers),
        "--run_id",
        run_id,
        "--instance_ids",
        *instance_ids,
    ]


def build_plan(
    predictions_path: Path,
    instance_ids: Sequence[str],
    run_id: str,
    max_workers: int,
    dataset_name: str = DEFAULT_DATASET,
) -> dict[str, Any]:
    """Return a machine-readable evaluation plan with explicit safety state."""
    command = build_official_command(
        predictions_path, instance_ids, run_id, max_workers, dataset_name
    )
    predictions_sha256, model_name_or_path = _validate_predictions(
        predictions_path, instance_ids
    )
    return {
        "schema_version": 1,
        "artifact_type": "swebench-evaluation-plan",
        "dataset": dataset_name,
        "instance_ids": list(instance_ids),
        "run_id": run_id,
        "predictions_path": str(predictions_path.resolve()),
        "predictions_sha256": predictions_sha256,
        "model_name_or_path": model_name_or_path,
        "command": command,
        "container_execution": "not-started",
    }


def _to_wsl_path(path: Path) -> str:
    """Convert an absolute Windows path to the default WSL mount convention."""
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if len(drive) != 1 or not resolved.is_absolute():
        raise SwebenchRunnerError(
            "--execution-host wsl-docker requires an absolute Windows path"
        )
    return "/mnt/" + drive + resolved.as_posix()[2:]


def build_wsl_docker_command(plan: dict[str, Any]) -> list[str]:
    """Build an isolated Linux evaluator command for Windows hosts with WSL."""
    predictions_path = Path(plan["predictions_path"])
    wsl_directory = _to_wsl_path(predictions_path.parent)
    evaluation_command = [
        "python",
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        plan["dataset"],
        "--predictions_path",
        f"/work/{predictions_path.name}",
        "--max_workers",
        str(plan["command"][plan["command"].index("--max_workers") + 1]),
        "--run_id",
        plan["run_id"],
        "--instance_ids",
        *plan["instance_ids"],
    ]
    container_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        "-v",
        f"{wsl_directory}:/work",
        "-w",
        "/work",
        WSL_DOCKER_IMAGE,
        "bash",
        "-lc",
        f"pip install --no-cache-dir -q swebench=={SWE_BENCH_VERSION} && "
        + shlex.join(evaluation_command),
    ]
    return ["wsl", "-e", "bash", "-lc", shlex.join(container_command)]


def _official_report_path(plan: dict[str, Any]) -> Path:
    """Return the official report location created beside the predictions."""
    return Path(plan["predictions_path"]).parent / (
        f"{plan['model_name_or_path'].replace('/', '__')}.{plan['run_id']}.json"
    )


def _summarize_official_report(plan: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless every selected instance resolved in the official report."""
    report_path = _official_report_path(plan)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise SwebenchRunnerError(
            f"official SWE-bench report is missing: {report_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise SwebenchRunnerError(
            f"official SWE-bench report is invalid JSON: {report_path}"
        ) from error
    if not isinstance(report, dict):
        raise SwebenchRunnerError("official SWE-bench report must be a JSON object")

    selected = set(plan["instance_ids"])
    summary: dict[str, list[str]] = {}
    for field in ("completed_ids", "resolved_ids", "error_ids", "incomplete_ids"):
        value = report.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise SwebenchRunnerError(f"official report field is invalid: {field}")
        summary[field] = sorted(selected.intersection(value))
    resolved = set(summary["resolved_ids"])
    completed = set(summary["completed_ids"])
    errors = set(summary["error_ids"])
    incomplete = set(summary["incomplete_ids"])
    if selected != resolved or selected != completed or errors or incomplete:
        raise SwebenchRunnerError(
            "official SWE-bench evaluation did not resolve every selected instance"
        )
    return {
        "verdict": "PASS",
        "report_path": str(report_path.resolve()),
        "selected_total": len(selected),
        **summary,
    }


def execute_plan(
    plan: dict[str, Any],
    allow_container_execution: bool,
    execution_host: str = "native",
) -> dict[str, Any]:
    """Run the official command only after the caller explicitly opts in."""
    if not allow_container_execution:
        raise SwebenchRunnerError("--allow-container-execution is required to execute")
    if execution_host == "native":
        if platform.system() == "Windows":
            raise SwebenchRunnerError(
                "native SWE-bench execution requires a POSIX Python host; "
                "use --execution-host wsl-docker on Windows"
            )
        execution_command = plan["command"]
    elif execution_host == "wsl-docker":
        if platform.system() != "Windows":
            raise SwebenchRunnerError(
                "--execution-host wsl-docker is available only on Windows"
            )
        execution_command = build_wsl_docker_command(plan)
    else:
        raise SwebenchRunnerError(f"unsupported execution host: {execution_host}")
    report_path = _official_report_path(plan)
    if report_path.exists():
        raise SwebenchRunnerError(
            f"refusing to overwrite existing official report: {report_path}"
        )
    completed = subprocess.run(
        execution_command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = {
        **plan,
        "container_execution": "completed",
        "execution_host": execution_host,
        "execution_command": execution_command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if completed.returncode == 0:
        result["official_result"] = _summarize_official_report(plan)
    return result


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    """Write an artifact atomically without silently replacing prior evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SwebenchRunnerError(f"refusing to overwrite existing artifact: {path}")
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
            raise SwebenchRunnerError(
                f"refusing to overwrite existing artifact: {path}"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or run SWE-bench Verified")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--instance-id", action="append", default=[])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--allow-container-execution", action="store_true")
    parser.add_argument(
        "--execution-host", choices=("native", "wsl-docker"), default="native"
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Print a no-network plan or run the official evaluator by explicit opt-in."""
    args = _parse_args(argv)
    try:
        plan = build_plan(
            args.predictions,
            args.instance_id,
            args.run_id,
            args.max_workers,
        )
        result = (
            execute_plan(plan, True, args.execution_host)
            if args.allow_container_execution
            else plan
        )
        if args.output is not None:
            _atomic_write(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=4))
        return 0 if result.get("exit_code", 0) == 0 else 1
    except (OSError, UnicodeError, SwebenchRunnerError) as error:
        print(f"swebench runner failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
