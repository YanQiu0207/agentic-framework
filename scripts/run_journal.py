"""Persist and replay the append-only Run event journal."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import runtime_schema
import run_manifest

_WORKFLOW_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "workflow-code-generation"
    / "scripts"
)
sys.path.insert(0, str(_WORKFLOW_SCRIPTS))
import lint_task_deps  # noqa: E402
import workflow_control  # noqa: E402

_BINDING_FIELDS = (
    "schema_version",
    "run_id",
    "profile",
    "harness",
    "commit_sha",
    "config_digest",
)
_SIDE_EFFECT_EVENTS = frozenset(
    {"artifact-produced", "merge-completed", "external-side-effect"}
)
_EVENT_STATES = {
    "task-started": "running",
    "task-quality-passed": "quality_passed",
    "task-merged": "completed",
    "task-manual": "manual",
    "task-blocked": "blocked",
    "task-retried": "pending",
    "task-failed": "pending",
}


class JournalError(Exception):
    """Raised when journal evidence is invalid or contradictory."""


@dataclass(frozen=True)
class ReplayResult:
    """Deterministic state reconstructed from a validated journal."""

    sequence: int
    tasks: dict[str, dict[str, Any]]
    idempotency_keys: dict[str, dict[str, Any]]
    digest: str


def _canonical(value: object) -> bytes:
    return runtime_schema.canonical_json_bytes(value)


def _journal_digest(events: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for event in events:
        digest.update(_canonical(event) + b"\n")
    return f"sha256:{digest.hexdigest()}"


def _validate_event(event: dict[str, Any]) -> None:
    try:
        runtime_schema.validate_document(event, "event")
    except runtime_schema.RuntimeSchemaError as error:
        raise JournalError(f"invalid_event:{error}") from error
    payload = event["payload"]
    if payload["event_type"] in _SIDE_EFFECT_EVENTS and not payload.get(
        "idempotency_key"
    ):
        raise JournalError("missing_idempotency_key")


def read_events(path: Path) -> list[dict[str, Any]]:
    """Read JSONL without accepting a torn or malformed final record."""
    if not path.exists():
        return []
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise JournalError("journal_unreadable") from error
    if raw and not raw.endswith(b"\n"):
        raise JournalError("torn_journal_record")
    events = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise JournalError(f"invalid_json_line:{line_number}") from error
        if not isinstance(value, dict):
            raise JournalError(f"invalid_event_line:{line_number}")
        events.append(value)
    return events


def _same_effect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    ignored = {"event_id", "sequence", "occurred_at"}
    left_payload = {k: v for k, v in left["payload"].items() if k not in ignored}
    right_payload = {k: v for k, v in right["payload"].items() if k not in ignored}
    envelope = (
        "schema_version",
        "artifact_type",
        "run_id",
        "task_id",
        "attempt",
        "profile",
        "harness",
        "producer",
        "commit_sha",
        "config_digest",
    )
    return left_payload == right_payload and all(left[k] == right[k] for k in envelope)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def append_event(path: Path, event: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Atomically append one event; return ``(event, appended)``.

    Reusing an idempotency key for the same effect is a no-op. Reusing it for a
    different effect fails closed.
    """
    _validate_event(event)
    try:
        with workflow_control._task_write_lock(path, timeout=10.0):
            events = read_events(path)
            replay = replay_events(events)
            key = event["payload"].get("idempotency_key")
            if key and key in replay.idempotency_keys:
                existing = replay.idempotency_keys[key]
                if _same_effect(existing, event):
                    return existing, False
                raise JournalError(f"idempotency_conflict:{key}")
            expected = replay.sequence + 1
            if event["payload"]["sequence"] != expected:
                raise JournalError(f"sequence_mismatch:expected={expected}")
            existing_ids = {item["payload"]["event_id"] for item in events}
            if event["payload"]["event_id"] in existing_ids:
                raise JournalError("duplicate_event_id")
            previous = path.read_bytes() if path.exists() else b""
            _atomic_write(path, previous + _canonical(event) + b"\n")
            return event, True
    except TimeoutError as error:
        raise JournalError("journal_lock_timeout") from error


def replay_events(events: Sequence[dict[str, Any]]) -> ReplayResult:
    """Validate and replay events in stable sequence order."""
    tasks: dict[str, dict[str, Any]] = {}
    keys: dict[str, dict[str, Any]] = {}
    event_ids: set[str] = set()
    binding: dict[str, Any] | None = None
    for expected, event in enumerate(events, 1):
        _validate_event(event)
        payload = event["payload"]
        if payload["sequence"] != expected:
            raise JournalError(f"sequence_mismatch:expected={expected}")
        if payload["event_id"] in event_ids:
            raise JournalError("duplicate_event_id")
        event_ids.add(payload["event_id"])
        current_binding = {name: event[name] for name in _BINDING_FIELDS}
        if binding is None:
            binding = current_binding
        elif binding != current_binding:
            raise JournalError("event_binding_conflict")
        key = payload.get("idempotency_key")
        if key:
            if key in keys:
                raise JournalError(f"duplicate_idempotency_key:{key}")
            keys[key] = event
        task_id = event["task_id"]
        if task_id is None:
            continue
        current = tasks.setdefault(task_id, {"state": "pending", "attempts": 0})
        expected_attempt = runtime_schema.attempt_for_attempts(current["attempts"])
        if event["attempt"] != expected_attempt:
            raise JournalError(
                f"attempt_mismatch:{task_id}:expected={expected_attempt}"
            )
        event_type = payload["event_type"]
        if event_type == "task-failed":
            current["attempts"] += 1
        if event_type in _EVENT_STATES:
            current["state"] = _EVENT_STATES[event_type]
    return ReplayResult(len(events), tasks, keys, _journal_digest(events))


def replay_journal(path: Path) -> ReplayResult:
    """Replay a journal file."""
    return replay_events(read_events(path))


def write_checkpoint(run_dir: Path, journal_path: Path) -> Path:
    """Atomically persist the latest replay result as a journal-prefix checkpoint."""
    replay = replay_journal(journal_path)
    document = {
        "schema_version": 1,
        "sequence": replay.sequence,
        "journal_digest": replay.digest,
        "tasks": replay.tasks,
    }
    path = run_dir / "checkpoints" / f"checkpoint-{replay.sequence:08d}.json"
    _atomic_write(path, _canonical(document) + b"\n")
    return path


def validate_checkpoint(path: Path, events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Validate a checkpoint against its exact journal prefix."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        sequence = document["sequence"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as error:
        raise JournalError("invalid_checkpoint") from error
    if not isinstance(sequence, int) or sequence < 0 or sequence > len(events):
        raise JournalError("checkpoint_sequence_conflict")
    prefix = replay_events(events[:sequence])
    expected = {
        "schema_version": 1,
        "sequence": sequence,
        "journal_digest": prefix.digest,
        "tasks": prefix.tasks,
    }
    if document != expected:
        raise JournalError("checkpoint_content_conflict")
    return document


def recovery_plan(
    journal_path: Path,
    checkpoint_path: Path,
    tasks_text: str,
    manifest: dict[str, Any],
    merged_task_ids: set[int],
) -> list[workflow_control.RecoveryAction]:
    """Fail closed on source conflicts, then calculate deterministic recovery."""
    events = read_events(journal_path)
    replay = replay_events(events)
    validate_checkpoint(checkpoint_path, events)
    try:
        runtime_schema.validate_document(manifest, "run-manifest")
    except runtime_schema.RuntimeSchemaError as error:
        raise JournalError(f"invalid_manifest:{error}") from error
    try:
        run_manifest.validate_manifest(journal_path.parent, manifest)
    except run_manifest.ManifestError as error:
        raise JournalError(f"invalid_manifest_evidence:{error}") from error
    for event in events:
        if any(event[name] != manifest[name] for name in _BINDING_FIELDS):
            raise JournalError("event_manifest_binding_conflict")
    tasks = lint_task_deps.parse_tasks(tasks_text)
    errors = lint_task_deps.field_errors(tasks)
    if errors:
        raise JournalError(f"invalid_tasks:{errors[0]}")
    validate_task_sources(replay, tasks_text, manifest)
    try:
        return workflow_control.plan_recovery(tasks, merged_task_ids)
    except ValueError as error:
        raise JournalError(f"git_tasks_conflict:{error}") from error


def validate_task_sources(
    replay: ReplayResult,
    tasks_text: str,
    manifest: dict[str, Any],
) -> None:
    """Require Journal, task plan, and Manifest to describe the same tasks."""
    tasks = lint_task_deps.parse_tasks(tasks_text)
    errors = lint_task_deps.field_errors(tasks)
    if errors:
        raise JournalError(f"invalid_tasks:{errors[0]}")
    manifest_tasks = {item["task_id"]: item for item in manifest["payload"]["tasks"]}
    task_ids = set(replay.tasks) | set(manifest_tasks) | {str(item) for item in tasks}
    conflicts = []
    for task_id in sorted(task_ids, key=lambda value: (not value.isdigit(), value)):
        try:
            numeric_id = int(task_id)
        except ValueError as error:
            raise JournalError(f"invalid_task_id:{task_id}") from error
        state = replay.tasks.get(task_id)
        manifest_task = manifest_tasks.get(task_id)
        task = tasks.get(numeric_id)
        if state is None:
            conflicts.append(f"missing_task_event:{task_id}")
        if manifest_task is None:
            conflicts.append(f"missing_manifest_task:{task_id}")
        if task is None:
            conflicts.append(f"missing_task_plan_task:{task_id}")
        if state is None or manifest_task is None:
            continue
        # Compare state/attempts against the manifest leg only: manifest
        # payload.tasks is built from delivery-time task-state artifacts
        # (run_manifest.py:395-407), equivalent to journal vs delivery-time
        # tasks.md; the frozen plan snapshot guarantees plan completeness only.
        if manifest_task["state"] != state["state"] or manifest_task[
            "attempt"
        ] != runtime_schema.attempt_for_attempts(state["attempts"]):
            conflicts.append(f"event_manifest_task_conflict:{task_id}")
    if conflicts:
        raise JournalError(";".join(conflicts))


def make_user_action_event(
    envelope: dict[str, Any],
    *,
    event_id: str,
    sequence: int,
    action: str,
    reason: str,
    occurred_at: str,
) -> dict[str, Any]:
    """Build an explicit, auditable user decision event."""
    if action not in {"approve", "reject", "retry", "cancel", "override"}:
        raise JournalError(f"unsupported_user_action:{action}")
    if not reason.strip():
        raise JournalError("user_action_reason_required")
    event = dict(envelope)
    event.update(
        {
            "artifact_type": "event",
            "artifact_id": event_id,
            "producer": "user",
            "created_at": occurred_at,
            "payload": {
                "event_id": event_id,
                "sequence": sequence,
                "event_type": f"user-{action}",
                "actor": "user",
                "occurred_at": occurred_at,
                "input_artifact_ids": [],
                "output_artifact_ids": [],
                "details": {"reason": reason},
            },
        }
    )
    _validate_event(event)
    return event
