"""Generate and validate an agent runtime manifest and evidence graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import runtime_schema

_REPARSE_POINT = 0x400
_BINDING_FIELDS = (
    "schema_version",
    "run_id",
    "profile",
    "harness",
    "commit_sha",
    "config_digest",
)
_REQUIRED_EVIDENCE_TYPES = frozenset(
    {
        "code-result",
        "final-report",
        "input-artifact",
        "review-report",
        "task-state",
        "verify-report",
    }
)
_REQUIRED_INPUT_TYPES = frozenset(
    {"agents", "skill", "spec", "task-plan", "run-config", "capability-matrix"}
)


class ManifestError(Exception):
    """Raised when manifest generation or evidence validation fails."""

    def __init__(self, issues: Sequence[str]):
        super().__init__("; ".join(issues))
        self.issues = tuple(issues)


def file_digest(path: Path) -> str:
    """Return a streaming SHA-256 digest for one evidence file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _is_link_or_reparse(path: Path) -> bool:
    """Return whether a path is a symbolic link or Windows reparse point."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & _REPARSE_POINT)


def secure_run_path(run_dir: Path, relative_path: str) -> Path:
    """Resolve a Run-relative path without following links or reparse points."""
    relative = Path(relative_path)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise ManifestError([f"path_escape:{relative_path}"])
    if not relative.parts or any(part in {"", "."} for part in relative.parts):
        raise ManifestError([f"invalid_path:{relative_path}"])
    root = run_dir.absolute()
    if _is_link_or_reparse(root):
        raise ManifestError(["run_root_reparse_point"])
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if _is_link_or_reparse(candidate):
            raise ManifestError([f"reparse_point:{relative_path}"])
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ManifestError([f"path_escape:{relative_path}"]) from error
    return candidate


def _read_artifact(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestError([f"invalid_artifact_json:{path.name}"]) from error
    try:
        runtime_schema.validate_document(document)
    except runtime_schema.RuntimeSchemaError as error:
        raise ManifestError([f"invalid_artifact_schema:{path.name}:{error}"]) from error
    return document


def _artifact_files(run_dir: Path) -> dict[str, Path]:
    """Return artifact-envelope files found in the Run artifact directory."""
    artifact_dir = run_dir / "artifacts"
    if not artifact_dir.is_dir():
        return {}
    found = {}
    directories = [artifact_dir]
    while directories:
        directory = directories.pop()
        for path in directory.iterdir():
            relative_path = path.relative_to(run_dir).as_posix()
            if _is_link_or_reparse(path):
                raise ManifestError([f"reparse_point:{relative_path}"])
            if path.is_dir():
                directories.append(path)
                continue
            if path.suffix != ".json":
                continue
            secure_run_path(run_dir, relative_path)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and "artifact_type" in value:
                found[relative_path] = path
    return found


def _validate_input_snapshot(
    run_dir: Path, artifact: dict[str, Any], issues: list[str]
) -> None:
    if artifact["artifact_type"] != "input-artifact":
        return
    snapshot_path = artifact["payload"]["path"]
    try:
        snapshot = secure_run_path(run_dir, snapshot_path)
    except ManifestError as error:
        issues.extend(f"input_{issue}" for issue in error.issues)
        return
    if not snapshot.is_file():
        issues.append(f"missing_input_snapshot:{snapshot_path}")
        return
    if file_digest(snapshot) != artifact["payload"]["content_digest"]:
        issues.append(f"input_digest_mismatch:{snapshot_path}")


def _validate_code_snapshot(
    run_dir: Path, artifact: dict[str, Any], issues: list[str]
) -> None:
    if artifact["artifact_type"] != "code-result":
        return
    snapshot_path = artifact["payload"]["path"]
    try:
        snapshot = secure_run_path(run_dir, snapshot_path)
    except ManifestError as error:
        issues.extend(f"code_{issue}" for issue in error.issues)
        return
    if not snapshot.is_file():
        issues.append(f"missing_code_snapshot:{snapshot_path}")
    elif file_digest(snapshot) != artifact["payload"]["content_digest"]:
        issues.append(f"code_digest_mismatch:{snapshot_path}")


def _validate_relations(
    artifacts: dict[str, dict[str, Any]], relations: list[dict[str, str]]
) -> list[str]:
    issues = []
    relation_keys = set()
    for relation in relations:
        source = relation["source_artifact_id"]
        target = relation["target_artifact_id"]
        relation_type = relation["relation_type"]
        key = (relation_type, source, target)
        if key in relation_keys:
            issues.append(f"duplicate_relation:{relation_type}:{source}:{target}")
        relation_keys.add(key)
        if source not in artifacts:
            issues.append(f"missing_relation_source:{source}")
        if target not in artifacts:
            issues.append(f"missing_relation_target:{target}")
    spec_ids = {
        artifact_id
        for artifact_id, artifact in artifacts.items()
        if artifact["artifact_type"] == "input-artifact"
        and artifact["payload"]["input_type"] == "spec"
    }
    if not spec_ids:
        issues.append("missing_spec_artifact")
    for artifact_id, artifact in artifacts.items():
        expected_relation = {
            "review-report": "reviews",
            "verify-report": "verifies",
        }.get(artifact["artifact_type"])
        if expected_relation is None:
            continue
        if not any(
            (expected_relation, artifact_id, spec_id) in relation_keys
            for spec_id in spec_ids
        ):
            issues.append(f"missing_spec_binding:{artifact_id}")
    return issues


def _validate_complete_evidence(
    artifacts: dict[str, dict[str, Any]], relations: list[dict[str, str]]
) -> list[str]:
    """Require rule inputs, the complete task plan, and final-report reachability."""
    issues: list[str] = []
    inputs = {
        artifact["payload"]["input_type"]: artifact
        for artifact in artifacts.values()
        if artifact["artifact_type"] == "input-artifact"
    }
    for input_type in sorted(_REQUIRED_INPUT_TYPES - inputs.keys()):
        issues.append(f"missing_input_type:{input_type}")

    task_plan = inputs.get("task-plan")
    if task_plan is not None:
        planned = set(task_plan["payload"].get("task_ids", []))
        actual = {
            artifact["task_id"]
            for artifact in artifacts.values()
            if artifact["artifact_type"] == "task-state"
        }
        if not planned:
            issues.append("task_plan_missing_task_ids")
        for task_id in sorted(planned - actual):
            issues.append(f"missing_planned_task:{task_id}")
        for task_id in sorted(actual - planned):
            issues.append(f"unplanned_task:{task_id}")

    finals = [
        artifact
        for artifact in artifacts.values()
        if artifact["artifact_type"] == "final-report"
    ]
    if len(finals) != 1:
        issues.append(f"final_report_count:{len(finals)}")
        return issues
    adjacency: dict[str, set[str]] = {}
    for relation in relations:
        adjacency.setdefault(relation["source_artifact_id"], set()).add(
            relation["target_artifact_id"]
        )
    reachable: set[str] = set()
    pending = [finals[0]["artifact_id"]]
    while pending:
        source = pending.pop()
        for target in adjacency.get(source, set()):
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    required_ids = {
        artifact_id
        for artifact_id, artifact in artifacts.items()
        if artifact["artifact_type"]
        in {
            "code-result",
            "input-artifact",
            "review-report",
            "task-state",
            "verify-report",
        }
    }
    for artifact_id in sorted(required_ids - reachable):
        issues.append(f"final_evidence_unreachable:{artifact_id}")
    return issues


def _validate_task_bindings(
    artifacts: dict[str, dict[str, Any]], tasks: list[dict[str, Any]]
) -> list[str]:
    issues = []
    task_artifacts: dict[tuple[str, int], set[str]] = {}
    for task in tasks:
        key = (task["task_id"], task["attempt"])
        if key in task_artifacts:
            issues.append(f"duplicate_task:{key[0]}:{key[1]}")
        task_artifacts[key] = set(task["artifact_ids"])
        state_artifacts = []
        for artifact_id in task["artifact_ids"]:
            artifact = artifacts.get(artifact_id)
            if artifact is None:
                issues.append(f"missing_task_artifact:{artifact_id}")
                continue
            if (artifact["task_id"], artifact["attempt"]) != key:
                issues.append(f"task_binding_mismatch:{artifact_id}")
            if artifact["artifact_type"] == "task-state":
                state_artifacts.append(artifact)
        if len(state_artifacts) != 1:
            issues.append(f"task_state_count:{key[0]}:{key[1]}")
        elif state_artifacts[0]["payload"]["state"] != task["state"]:
            issues.append(f"task_state_mismatch:{key[0]}:{key[1]}")
    for artifact_id, artifact in artifacts.items():
        if artifact["task_id"] is None:
            continue
        key = (artifact["task_id"], artifact["attempt"])
        if key not in task_artifacts:
            issues.append(f"unregistered_task_binding:{artifact_id}")
        elif artifact_id not in task_artifacts[key]:
            issues.append(f"task_artifact_omitted:{artifact_id}")
    return issues


def validate_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Validate manifest structure, files, digests, bindings, and evidence graph."""
    try:
        runtime_schema.validate_document(manifest)
    except runtime_schema.RuntimeSchemaError as error:
        raise ManifestError([f"invalid_manifest_schema:{error}"]) from error
    issues: list[str] = []
    entries = manifest["payload"]["artifacts"]
    entry_ids = [entry["artifact_id"] for entry in entries]
    entry_paths = [entry["path"] for entry in entries]
    if len(entry_ids) != len(set(entry_ids)):
        issues.append("duplicate_artifact_id")
    if len(entry_paths) != len(set(entry_paths)):
        issues.append("duplicate_artifact_path")
    documents: dict[str, dict[str, Any]] = {}
    for entry in entries:
        relative_path = entry["path"]
        if not relative_path.startswith("artifacts/"):
            issues.append(f"artifact_outside_artifacts:{relative_path}")
            continue
        try:
            path = secure_run_path(run_dir, relative_path)
        except ManifestError as error:
            issues.extend(error.issues)
            continue
        if not path.is_file():
            issues.append(f"missing_artifact:{relative_path}")
            continue
        if file_digest(path) != entry["content_digest"]:
            issues.append(f"digest_mismatch:{relative_path}")
            continue
        try:
            artifact = _read_artifact(path)
        except ManifestError as error:
            issues.extend(error.issues)
            continue
        artifact_id = artifact["artifact_id"]
        if artifact_id != entry["artifact_id"]:
            issues.append(f"artifact_id_mismatch:{relative_path}")
            continue
        for field in ("artifact_type", "producer", "schema_version"):
            if artifact[field] != entry[field]:
                issues.append(f"entry_{field}_mismatch:{artifact_id}")
        for field in _BINDING_FIELDS:
            if artifact[field] != manifest[field]:
                issues.append(f"binding_{field}_mismatch:{artifact_id}")
        documents[artifact_id] = artifact
        _validate_input_snapshot(run_dir, artifact, issues)
        _validate_code_snapshot(run_dir, artifact, issues)
    found_paths = set(_artifact_files(run_dir))
    for orphan_path in sorted(found_paths - set(entry_paths)):
        issues.append(f"orphan_artifact:{orphan_path}")
    present_types = {item["artifact_type"] for item in documents.values()}
    for missing_type in sorted(_REQUIRED_EVIDENCE_TYPES - present_types):
        issues.append(f"missing_evidence_type:{missing_type}")
    issues.extend(_validate_task_bindings(documents, manifest["payload"]["tasks"]))
    issues.extend(_validate_relations(documents, manifest["payload"]["relations"]))
    issues.extend(
        _validate_complete_evidence(documents, manifest["payload"]["relations"])
    )
    if issues:
        raise ManifestError(issues)


def _entry(run_dir: Path, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact["artifact_id"],
        "path": path.relative_to(run_dir).as_posix(),
        "artifact_type": artifact["artifact_type"],
        "content_digest": file_digest(path),
        "producer": artifact["producer"],
        "schema_version": artifact["schema_version"],
    }


def generate_manifest(run_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Scan artifact envelopes, build a manifest, validate it, and write atomically."""
    manifest_path = run_dir / "run-manifest.json"
    if manifest_path.exists():
        raise ManifestError(["manifest_already_exists"])
    documents = []
    for path in _artifact_files(run_dir).values():
        documents.append((path, _read_artifact(path)))
    task_groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for _, artifact in documents:
        if artifact["task_id"] is not None:
            task_groups.setdefault(
                (artifact["task_id"], artifact["attempt"]), []
            ).append(artifact)
    tasks = []
    for (task_id, attempt), artifacts in sorted(task_groups.items()):
        states = [item for item in artifacts if item["artifact_type"] == "task-state"]
        if len(states) != 1:
            raise ManifestError([f"task_state_count:{task_id}:{attempt}"])
        tasks.append(
            {
                "task_id": task_id,
                "attempt": attempt,
                "state": states[0]["payload"]["state"],
                "artifact_ids": sorted(item["artifact_id"] for item in artifacts),
            }
        )
    required = {
        "schema_version",
        "artifact_id",
        "run_id",
        "profile",
        "harness",
        "producer",
        "commit_sha",
        "config_digest",
        "created_at",
        "base_commit_sha",
        "relations",
    }
    missing = required - metadata.keys()
    if missing:
        raise ManifestError([f"missing_metadata:{min(missing)}"])
    manifest = {
        **{
            field: metadata[field]
            for field in required - {"base_commit_sha", "relations"}
        },
        "artifact_type": "run-manifest",
        "task_id": None,
        "attempt": None,
        "payload": {
            "base_commit_sha": metadata["base_commit_sha"],
            "artifacts": sorted(
                (_entry(run_dir, path, artifact) for path, artifact in documents),
                key=lambda item: item["artifact_id"],
            ),
            "tasks": tasks,
            "relations": metadata["relations"],
        },
    }
    validate_manifest(run_dir, manifest)
    _atomic_write_json(manifest_path, manifest)
    return manifest


def _atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or validate a Run manifest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("run_dir", type=Path)
    generate_parser.add_argument("--metadata", required=True, type=Path)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("run_dir", type=Path)
    validate_parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the manifest generator or validator CLI."""
    args = _parse_args(argv)
    try:
        if args.command == "generate":
            metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
            generate_manifest(args.run_dir, metadata)
        else:
            path = args.manifest or args.run_dir / "run-manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            validate_manifest(args.run_dir, manifest)
        print("PASS")
        return 0
    except ManifestError as error:
        for issue in error.issues:
            print(issue, file=sys.stderr)
        return 1
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("run manifest operation failed", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("run manifest operation interrupted", file=sys.stderr)
        return 130
    except Exception:
        print("run manifest operation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
