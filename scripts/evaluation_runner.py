"""Execute deterministic Tier 1 agent behavior evaluations."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import runtime_schema

DIMENSIONS = (
    "should-trigger",
    "should-not-trigger",
    "boundary",
    "profile-routing",
    "recovery",
    "conflicting-instructions",
    "evidence-skipping",
)
DEFAULT_CASE_PATHS = (
    "skills/workflow-code-generation/evaluation/trigger-cases.md",
    "skills/workflow-code-review/evaluation/trigger-cases.md",
    "skills/workflow-requirements-clarification/evaluation/trigger-cases.md",
    "skills/workflow-verification/evaluation/trigger-cases.md",
)
_SIGNAL_PATTERN = re.compile(r"signal:([a-z-]+)=([a-z0-9-]+)", re.IGNORECASE)


class EvaluationError(Exception):
    """Raised when cases, observations, or baselines violate the contract."""


@dataclass(frozen=True)
class EvalCase:
    """One compiled Markdown behavior case."""

    case_id: str
    local_id: str
    skill: str
    dimension: str
    prompt: str
    expected: str
    source_path: str


@dataclass(frozen=True)
class Observation:
    """Harness output consumed by deterministic assertions."""

    transcript: str
    signals: tuple[str, ...]
    error: str = ""


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_trigger_cases(path: Path, repo_root: Path) -> list[EvalCase]:
    """Compile supported Markdown table sections from one trigger-cases file."""
    text = path.read_bytes().decode("utf-8-sig")
    skill = path.parents[1].name
    relative_source = path.relative_to(repo_root).as_posix()
    dimension = ""
    cases = []
    for line in text.splitlines():
        heading = re.match(r"^##\s+([a-z-]+)", line)
        if heading:
            dimension = heading.group(1)
            continue
        if dimension not in DIMENSIONS or not line.startswith("|"):
            continue
        cells = _table_cells(line)
        if len(cells) < 3 or cells[0] in {"ID", "---"}:
            continue
        if set(cells[0]) == {"-"}:
            continue
        local_id, prompt, expected = cells[:3]
        cases.append(
            EvalCase(
                case_id=f"{skill}:{local_id}",
                local_id=local_id,
                skill=skill,
                dimension=dimension,
                prompt=prompt.strip("「」"),
                expected=expected,
                source_path=relative_source,
            )
        )
    return cases


def compile_core_cases(repo_root: Path) -> list[EvalCase]:
    """Compile and validate the four canonical trigger-case sources."""
    cases = []
    for relative_path in DEFAULT_CASE_PATHS:
        path = repo_root / relative_path
        if not path.is_file():
            raise EvaluationError(f"missing case source: {relative_path}")
        cases.extend(parse_trigger_cases(path, repo_root))
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationError("duplicate qualified case ID")
    missing = set(DIMENSIONS) - {case.dimension for case in cases}
    if missing:
        raise EvaluationError(f"missing evaluation dimension: {min(missing)}")
    return cases


class SubprocessAdapter:
    """Invoke one Harness adapter through a JSON stdin/stdout contract."""

    def __init__(self, command: Sequence[str], timeout_seconds: float = 120.0):
        if not command:
            raise EvaluationError("adapter command is required")
        if timeout_seconds <= 0:
            raise EvaluationError("adapter timeout must be positive")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds

    def __call__(self, case: EvalCase) -> Observation:
        request = json.dumps(asdict(case), ensure_ascii=False)
        try:
            completed = subprocess.run(
                self._command,
                input=request,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return Observation("", (), "adapter-execution-failed")
        if completed.returncode != 0:
            return Observation("", (), "adapter-returned-nonzero")
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return Observation("", (), "adapter-output-invalid-json")
        if not isinstance(value, dict):
            return Observation("", (), "adapter-output-not-object")
        transcript = value.get("transcript")
        signals = value.get("signals")
        if not isinstance(transcript, str) or not isinstance(signals, list):
            return Observation("", (), "adapter-output-fields-invalid")
        if not all(isinstance(signal, str) for signal in signals):
            return Observation("", (), "adapter-signals-invalid")
        return Observation(transcript, tuple(signals))


def _assertion(name: str, passed: bool, expected: str, actual: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "expected": expected, "actual": actual}


def _boundary_assertions(
    case: EvalCase, observation: Observation
) -> list[dict[str, Any]]:
    expected = case.expected
    if "workflow-quick-design" in expected:
        marker = "Using workflow-quick-design"
        return [
            _assertion(
                "boundary-route",
                marker in observation.transcript,
                marker,
                observation.transcript,
            )
        ]
    expected_signal = "action=context-dependent"
    if "先澄清" in expected:
        expected_signal = "action=clarify"
    elif "先定位" in expected:
        expected_signal = "route=troubleshooting"
    elif "Fast-Path" in expected:
        expected_signal = "route=fast-path"
    return [
        _assertion(
            "boundary-action",
            expected_signal in observation.signals,
            expected_signal,
            ",".join(observation.signals),
        )
    ]


def _profile_assertions(
    case: EvalCase, observation: Observation
) -> list[dict[str, Any]]:
    profiles = {"P-1": "lightweight", "P-2": "standard", "P-3": "strict"}
    reviewers = {
        "P-1": "comprehensive-reviewer",
        "P-2": "comprehensive-reviewer",
        "P-3": "full-5-reviewers",
    }
    expected_signals = (
        f"review-profile={profiles[case.local_id]}",
        f"reviewer={reviewers[case.local_id]}",
    )
    actual = ",".join(observation.signals)
    return [
        _assertion(name, signal in observation.signals, signal, actual)
        for name, signal in zip(("review-profile", "reviewer"), expected_signals)
    ]


def evaluate_case(
    case: EvalCase, observation: Observation
) -> tuple[str, list[dict[str, Any]]]:
    """Apply only deterministic Tier 1 assertions to one observation."""
    if observation.error:
        return "ERROR", [_assertion("adapter", False, "success", observation.error)]
    marker = f"Using {case.skill}"
    if case.dimension == "should-trigger":
        assertions = [
            _assertion(
                "skill-marker",
                marker in observation.transcript,
                marker,
                observation.transcript,
            )
        ]
    elif case.dimension == "should-not-trigger":
        assertions = [
            _assertion(
                "skill-marker-absent",
                marker not in observation.transcript,
                f"not {marker}",
                observation.transcript,
            )
        ]
    elif case.dimension == "boundary":
        assertions = _boundary_assertions(case, observation)
    elif case.dimension == "profile-routing":
        assertions = _profile_assertions(case, observation)
    else:
        expected_signals = [
            f"{key}={value}" for key, value in _SIGNAL_PATTERN.findall(case.expected)
        ]
        actual = ",".join(observation.signals)
        assertions = [
            _assertion("required-signal", signal in observation.signals, signal, actual)
            for signal in expected_signals
        ]
        if not assertions:
            raise EvaluationError(f"case lacks deterministic signals: {case.case_id}")
    verdict = "PASS" if all(item["passed"] for item in assertions) else "FAIL"
    return verdict, assertions


def _eval_artifact(
    case: EvalCase,
    verdict: str,
    assertions: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    artifact = {
        "schema_version": 1,
        "artifact_type": "eval-result",
        "artifact_id": f"eval:{case.case_id}",
        "run_id": metadata["run_id"],
        "task_id": None,
        "attempt": None,
        "profile": metadata["profile"],
        "harness": metadata["harness"],
        "producer": "evaluation-runner",
        "commit_sha": metadata["commit_sha"],
        "config_digest": metadata["config_digest"],
        "created_at": metadata["created_at"],
        "payload": {
            "case_id": case.case_id,
            "dimension": case.dimension,
            "verdict": verdict,
            "assertions": assertions,
            "model": metadata["model"],
            "evaluation_method": "deterministic-tier-1",
        },
    }
    runtime_schema.validate_document(artifact)
    return artifact


def compare_baseline(
    results: Sequence[dict[str, Any]], baseline: dict[str, Any]
) -> dict[str, Any]:
    """Apply an independent non-weighted gate to every baseline dimension."""
    if baseline.get("schema_version") != 1 or not isinstance(
        baseline.get("dimensions"), dict
    ):
        raise EvaluationError("invalid evaluation baseline")
    dimensions = {}
    overall_pass = True
    for dimension, threshold in baseline["dimensions"].items():
        dimension_results = [
            result for result in results if result["payload"]["dimension"] == dimension
        ]
        passed = sum(
            result["payload"]["verdict"] == "PASS" for result in dimension_results
        )
        total = len(dimension_results)
        pass_rate = passed / total if total else 0.0
        gate_passed = (
            total >= threshold["minimum_cases"]
            and pass_rate >= threshold["minimum_pass_rate"]
        )
        dimensions[dimension] = {
            "passed": passed,
            "total": total,
            "pass_rate": pass_rate,
            "minimum_cases": threshold["minimum_cases"],
            "minimum_pass_rate": threshold["minimum_pass_rate"],
            "verdict": "PASS" if gate_passed else "FAIL",
        }
        overall_pass = overall_pass and gate_passed
    unknown = {result["payload"]["dimension"] for result in results} - baseline[
        "dimensions"
    ].keys()
    if unknown:
        raise EvaluationError(f"dimension missing from baseline: {min(unknown)}")
    return {
        "schema_version": 1,
        "verdict": "PASS" if overall_pass else "FAIL",
        "dimensions": dimensions,
    }


def run_evaluation(
    cases: Sequence[EvalCase],
    executor: Callable[[EvalCase], Observation],
    metadata: dict[str, Any],
    baseline: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute all cases and return versioned artifacts plus regression summary."""
    required_metadata = {
        "run_id",
        "profile",
        "harness",
        "model",
        "commit_sha",
        "config_digest",
        "created_at",
    }
    missing = required_metadata - metadata.keys()
    if missing:
        raise EvaluationError(f"missing evaluation metadata: {min(missing)}")
    results = []
    for case in cases:
        verdict, assertions = evaluate_case(case, executor(case))
        results.append(_eval_artifact(case, verdict, assertions, metadata))
    return results, compare_baseline(results, baseline)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_outputs(
    output_dir: Path,
    results: Sequence[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    """Write machine JSONL/JSON and a concise human-readable summary atomically."""
    results_text = "".join(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
        for result in results
    )
    _atomic_write(output_dir / "eval-results.jsonl", results_text)
    _atomic_write(
        output_dir / "summary.json",
        json.dumps(summary, ensure_ascii=False, indent=4) + "\n",
    )
    lines = [
        "# Agent 行为评测摘要",
        "",
        f"- 总判定：{summary['verdict']}",
        "",
        "| 维度 | 通过 | 总数 | 判定 |",
        "| --- | ---: | ---: | --- |",
    ]
    for dimension, result in summary["dimensions"].items():
        lines.append(
            f"| `{dimension}` | {result['passed']} | {result['total']} | {result['verdict']} |"
        )
    _atomic_write(output_dir / "summary.md", "\n".join(lines) + "\n")


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic agent behavior evaluations"
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--adapter-arg", action="append", default=[])
    parser.add_argument("--adapter-timeout", type=float, default=120.0)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run Tier 1 evaluation and return nonzero on any dimension regression."""
    args = _parse_args(argv)
    try:
        cases = compile_core_cases(args.repo_root)
        baseline_path = (
            args.baseline
            or args.repo_root / "evaluation/baseline/core-agent-behavior.json"
        )
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
        executor = SubprocessAdapter(
            [args.adapter, *args.adapter_arg], args.adapter_timeout
        )
        results, summary = run_evaluation(cases, executor, metadata, baseline)
        write_outputs(args.output_dir, results, summary)
        print(summary["verdict"])
        return 0 if summary["verdict"] == "PASS" else 1
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        EvaluationError,
        runtime_schema.RuntimeSchemaError,
    ):
        print("agent behavior evaluation failed", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("agent behavior evaluation interrupted", file=sys.stderr)
        return 130
    except Exception:
        print("agent behavior evaluation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
