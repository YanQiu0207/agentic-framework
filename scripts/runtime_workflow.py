"""Minimal glue that binds runtime protocol artifacts to the real workflow."""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

import harness_runtime
import run_journal
import run_manifest
import runtime_schema
import runtime_trust


class RuntimeWorkflowError(Exception):
    """Raised when workflow evidence cannot be created or bound safely."""


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def load_context(run_dir: Path) -> dict[str, Any]:
    """Load the immutable context established before workflow side effects."""
    try:
        value = json.loads((run_dir / "run-context.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeWorkflowError("missing_or_invalid_run_context") from error
    required = {
        "run_id",
        "profile",
        "harness",
        "commit_sha",
        "base_commit_sha",
        "config_digest",
        "created_at",
    }
    if not isinstance(value, dict) or required - value.keys():
        raise RuntimeWorkflowError("incomplete_run_context")
    return value


def envelope(
    context: dict[str, Any],
    artifact_type: str,
    artifact_id: str,
    payload: dict[str, Any],
    producer: str,
    *,
    task_id: str | None = None,
    attempt: int | None = None,
) -> dict[str, Any]:
    """Build and validate one artifact bound to the immutable Run context."""
    value = {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "run_id": context["run_id"],
        "task_id": task_id,
        "attempt": attempt,
        "profile": context["profile"],
        "harness": context["harness"],
        "producer": producer,
        "commit_sha": context["commit_sha"],
        "config_digest": context["config_digest"],
        "created_at": _now(),
        "payload": payload,
    }
    runtime_schema.validate_document(value)
    return value


def _write_artifact(run_dir: Path, value: dict[str, Any]) -> Path:
    path = run_dir / "artifacts" / f"{value['artifact_id']}.json"
    if path.exists():
        raise RuntimeWorkflowError(f"artifact_already_exists:{value['artifact_id']}")
    _write_json(path, value)
    return path


def _snapshot_input(
    run_dir: Path,
    context: dict[str, Any],
    source: Path,
    input_type: str,
    artifact_id: str,
    task_ids: Sequence[str] = (),
) -> dict[str, Any]:
    if not source.is_file():
        raise RuntimeWorkflowError(f"missing_runtime_input:{source}")
    suffix = source.suffix or ".txt"
    snapshot = run_dir / "snapshots" / f"{artifact_id}{suffix}"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, snapshot)
    payload: dict[str, Any] = {
        "input_type": input_type,
        "path": snapshot.relative_to(run_dir).as_posix(),
        "content_digest": run_manifest.file_digest(snapshot),
    }
    if input_type == "task-plan":
        payload["task_ids"] = list(task_ids)
    value = envelope(
        context, "input-artifact", artifact_id, payload, "runtime-workflow"
    )
    _write_artifact(run_dir, value)
    return value


def _event(
    context: dict[str, Any],
    sequence: int,
    event_type: str,
    inputs: Sequence[str] = (),
    outputs: Sequence[str] = (),
    details: dict[str, Any] | None = None,
    task_id: str | None = None,
    attempt: int | None = None,
) -> dict[str, Any]:
    artifact_id = f"event-{sequence}"
    payload: dict[str, Any] = {
        "event_id": artifact_id,
        "sequence": sequence,
        "event_type": event_type,
        "actor": "runtime-workflow",
        "occurred_at": _now(),
        "input_artifact_ids": list(inputs),
        "output_artifact_ids": list(outputs),
    }
    if details:
        payload["details"] = details
    return envelope(
        context,
        "event",
        artifact_id,
        payload,
        "runtime-workflow",
        task_id=task_id,
        attempt=attempt,
    )


def initialize_run(
    repo: Path,
    run_dir: Path,
    *,
    run_id: str,
    profile: str,
    harness: str,
    commit_sha: str,
    base_commit_sha: str,
    max_attempts: int,
    verify_config: Path | None,
    tasks_path: Path,
    task_ids: Sequence[str],
    spec_path: Path,
    agents_path: Path,
    skill_path: Path,
    declaration_path: Path,
    adapter_command: Sequence[str],
    required_capabilities: Sequence[str],
    optional_capabilities: Sequence[str],
) -> dict[str, Any]:
    """Create immutable inputs and run the Harness capability gate at startup."""
    for label, commit_sha_value in (
        ("base", base_commit_sha),
        ("target", commit_sha),
    ):
        resolved = subprocess_result(
            [
                "git",
                "-C",
                str(repo),
                "rev-parse",
                "--verify",
                f"{commit_sha_value}^{{commit}}",
            ]
        ).decode("ascii", errors="strict").strip()
        if resolved != commit_sha_value:
            raise RuntimeWorkflowError(f"{label}_commit_mismatch")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise RuntimeWorkflowError("run_directory_not_empty")
    run_dir.mkdir(parents=True, exist_ok=True)
    run_config = runtime_schema.build_run_config(
        profile, harness, "workflow-code-generation", max_attempts, verify_config
    )
    _write_json(run_dir / "run-config.json", run_config)
    context = {
        "run_id": run_id,
        "profile": profile,
        "harness": harness,
        "commit_sha": commit_sha,
        "base_commit_sha": base_commit_sha,
        "config_digest": runtime_schema.config_digest(run_config),
        "created_at": _now(),
    }
    _write_json(run_dir / "run-context.json", context)
    inputs = [
        _snapshot_input(run_dir, context, agents_path, "agents", "input-agents"),
        _snapshot_input(run_dir, context, skill_path, "skill", "input-skill"),
        _snapshot_input(run_dir, context, spec_path, "spec", "input-spec"),
        _snapshot_input(
            run_dir,
            context,
            tasks_path,
            "task-plan",
            "input-task-plan",
            task_ids,
        ),
    ]
    declaration = harness_runtime.load_declaration(declaration_path)
    report = harness_runtime.startup_probe(
        declaration,
        harness_runtime.SubprocessHarnessAdapter(adapter_command),
        required_capabilities,
        optional_capabilities,
        run_id,
    )
    if report["verdict"] != "PASS":
        raise RuntimeWorkflowError("harness_capability_gate_failed")
    snapshot = run_dir / "snapshots" / "capability-probe.json"
    _write_json(snapshot, report)
    capability = envelope(
        context,
        "input-artifact",
        "input-capability",
        {
            "input_type": "capability-matrix",
            "path": snapshot.relative_to(run_dir).as_posix(),
            "content_digest": run_manifest.file_digest(snapshot),
        },
        "runtime-workflow",
    )
    _write_artifact(run_dir, capability)
    inputs.append(capability)
    journal = run_dir / "events.jsonl"
    run_journal.append_event(
        journal,
        _event(
            context,
            1,
            "run-started",
            outputs=[item["artifact_id"] for item in inputs],
        ),
    )
    for degradation in report["degradations"]:
        events = run_journal.read_events(journal)
        run_journal.append_event(
            journal,
            _event(
                context,
                len(events) + 1,
                "capability-degraded",
                inputs=["input-capability"],
                details=degradation,
            ),
        )
    run_journal.write_checkpoint(run_dir, journal)
    return context


def validate_verify_artifact(
    run_dir: Path, report_path: Path, task_id: str, attempt: int
) -> dict[str, Any]:
    """Reject legacy PASS JSON and require exact Run/Task/Attempt bindings."""
    context = load_context(run_dir)
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runtime_schema.validate_document(report, "verify-report")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        runtime_schema.RuntimeSchemaError,
    ) as error:
        raise RuntimeWorkflowError("invalid_or_legacy_verify_report") from error
    expected = {
        "run_id": context["run_id"],
        "task_id": task_id,
        "attempt": attempt,
        "commit_sha": context["commit_sha"],
        "config_digest": context["config_digest"],
    }
    for field, value in expected.items():
        if report[field] != value:
            raise RuntimeWorkflowError(f"verify_binding_mismatch:{field}")
    payload = report["payload"]
    if (
        payload["verdict"] != "PASS"
        or payload["errors"] != 0
        or payload["violations"] != 0
    ):
        raise RuntimeWorkflowError("verify_gate_failed")
    return report


def record_quality_passed(
    run_dir: Path, report_path: Path, task_id: str, attempt: int
) -> None:
    """Bind one successful task Verification to the append-only Journal."""
    report = validate_verify_artifact(run_dir, report_path, task_id, attempt)
    journal = run_dir / "events.jsonl"
    events = run_journal.read_events(journal)
    run_journal.append_event(
        journal,
        _event(
            load_context(run_dir),
            len(events) + 1,
            "task-quality-passed",
            inputs=[report["artifact_id"]],
            task_id=task_id,
            attempt=attempt,
        ),
    )
    run_journal.write_checkpoint(run_dir, journal)


def load_bound_report(
    run_dir: Path, path: Path, artifact_type: str
) -> dict[str, Any]:
    context = load_context(run_dir)
    try:
        relative = path.resolve().relative_to((run_dir / "artifacts").resolve())
        if not relative.parts:
            raise ValueError
        value = json.loads(path.read_text(encoding="utf-8"))
        runtime_schema.validate_document(value, artifact_type)
    except (
        OSError,
        ValueError,
        UnicodeError,
        json.JSONDecodeError,
        runtime_schema.RuntimeSchemaError,
    ) as error:
        raise RuntimeWorkflowError(f"invalid_or_legacy_{artifact_type}") from error
    for field in ("run_id", "profile", "harness", "commit_sha", "config_digest"):
        if value[field] != context[field]:
            raise RuntimeWorkflowError(f"{artifact_type}_binding_mismatch:{field}")
    return value


def finalize_run(
    repo: Path,
    run_dir: Path,
    review_path: Path,
    task_states: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Create final evidence, validate the Manifest, then execute the Trust Gate."""
    context = load_context(run_dir)
    review = load_bound_report(run_dir, review_path, "review-report")
    payload = review["payload"]
    if (
        payload["verdict"] != "PASS"
        or payload["p0_count"] != 0
        or payload["p1_count"] != 0
        or payload["scope"] != "run"
    ):
        raise RuntimeWorkflowError("review_gate_failed")
    documents = []
    for path in (run_dir / "artifacts").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("artifact_type") == "verify-report":
            load_bound_report(run_dir, path, "verify-report")
            documents.append(value)
    if not documents:
        raise RuntimeWorkflowError("missing_verify_report")
    for state in task_states:
        artifact_id = f"task-{state['task_id']}-state"
        value = envelope(
            context,
            "task-state",
            artifact_id,
            {"state": state["state"], "attempts": state["attempts"]},
            "workflow-control",
            task_id=state["task_id"],
            attempt=runtime_schema.attempt_for_attempts(state["attempts"]),
        )
        _write_artifact(run_dir, value)
    diff = subprocess_result(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--binary",
            context["base_commit_sha"],
            context["commit_sha"],
        ]
    )
    changed = subprocess_result(
        [
            "git",
            "-C",
            str(repo),
            "diff",
            "--name-only",
            context["base_commit_sha"],
            context["commit_sha"],
        ]
    ).decode("utf-8", errors="replace").splitlines()
    code_path = run_dir / "snapshots" / "code.diff"
    code_path.write_bytes(diff)
    code = envelope(
        context,
        "code-result",
        "code-result",
        {
            "base_commit_sha": context["base_commit_sha"],
            "head_commit_sha": context["commit_sha"],
            "path": code_path.relative_to(run_dir).as_posix(),
            "content_digest": run_manifest.file_digest(code_path),
            "changed_paths": sorted(set(changed)),
        },
        "runtime-workflow",
    )
    _write_artifact(run_dir, code)
    final = envelope(
        context,
        "final-report",
        "final-report",
        {"verdict": "PASS", "summary": "Evidence is present and context-bound."},
        "runtime-trust",
    )
    _write_artifact(run_dir, final)
    all_documents = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (run_dir / "artifacts").glob("*.json")
    ]
    spec_ids = [
        item["artifact_id"]
        for item in all_documents
        if item["artifact_type"] == "input-artifact"
        and item["payload"]["input_type"] == "spec"
    ]
    relations = [
        {
            "relation_type": "concludes",
            "source_artifact_id": "final-report",
            "target_artifact_id": item["artifact_id"],
        }
        for item in all_documents
        if item["artifact_id"] != "final-report"
    ]
    for item in all_documents:
        relation_type = {
            "verify-report": "verifies",
            "review-report": "reviews",
        }.get(item["artifact_type"])
        if relation_type:
            relations.append(
                {
                    "relation_type": relation_type,
                    "source_artifact_id": item["artifact_id"],
                    "target_artifact_id": spec_ids[0],
                }
            )
    journal = run_dir / "events.jsonl"
    state_events = {
        "completed": "task-merged",
        "manual": "task-manual",
        "blocked": "task-blocked",
    }
    for state in task_states:
        events = run_journal.read_events(journal)
        run_journal.append_event(
            journal,
            _event(
                context,
                len(events) + 1,
                state_events[state["state"]],
                task_id=state["task_id"],
                attempt=runtime_schema.attempt_for_attempts(state["attempts"]),
            ),
        )
    events = run_journal.read_events(journal)
    run_journal.append_event(
        journal,
        _event(
            context,
            len(events) + 1,
            "run-finalized",
            inputs=[item["artifact_id"] for item in all_documents if item != final],
            outputs=["final-report"],
        ),
    )
    run_journal.write_checkpoint(run_dir, journal)
    run_manifest.generate_manifest(
        run_dir,
        {
            **context,
            "schema_version": 1,
            "artifact_id": "run-manifest",
            "producer": "runtime-workflow",
            "relations": relations,
        },
    )
    return runtime_trust.validate_run(run_dir)


def subprocess_result(command: Sequence[str]) -> bytes:
    """Run a bounded Git evidence command and return exact stdout bytes."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeWorkflowError("git_evidence_command_failed") from error
    if completed.returncode != 0:
        raise RuntimeWorkflowError("git_evidence_command_failed")
    return completed.stdout
