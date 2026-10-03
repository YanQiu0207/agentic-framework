"""Canonical Native subject identity and conservative project-input coverage.

Algorithm v1 hashes canonical JSON (ASCII escapes, sorted keys, compact
separators) with SHA256. Input records use fixed-base/current path union, actual
file bytes/type and effective attributes. HEAD, staging and event history are
not content. Trusted callers supply additional inputs; reports cannot choose
exclusions. Limitations always prevent a complete validation claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence

try:
    from . import vcs
except ImportError:
    import vcs


ALGORITHM = "native-subject-v1"
REPORT_PREFIXES = (
    ".agentic-framework/verify",
    ".agentic-framework/review",
    ".agentic-framework/native-delivery",
)
GENERATED_PREFIXES = (
    ".agentic-framework/runs",
    ".agentic-framework/locks",
    ".agentic-framework/metrics",
    ".agentic-framework/worktrees",
    ".agentic-framework/tools",
)
CACHE_DIRECTORY_NAMES = ("__pycache__", ".pytest_cache")
VCS_DIRECTORY_NAMES = (".git", ".svn")
TASK_METADATA_FIELDS = ("状态", "attempts", "control_stage")


class SubjectError(Exception):
    """A safe, classified failure to obtain or compare complete input evidence."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if (
        not value
        or "\0" in value
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() == "."
        or ":" in value
    ):
        raise SubjectError("invalid_input_path")
    return path.as_posix()


def _under(value: str, prefix: str) -> bool:
    return value == prefix or value.startswith(prefix + "/")


def _classify(value: str) -> str:
    parts = PurePosixPath(value).parts
    if any(part in VCS_DIRECTORY_NAMES for part in parts):
        return "vcs"
    if any(_under(value, prefix) for prefix in REPORT_PREFIXES):
        return "report"
    if any(_under(value, prefix) for prefix in GENERATED_PREFIXES) or any(
        part in CACHE_DIRECTORY_NAMES for part in parts
    ):
        return "generated"
    return "input"


def _task_bytes(value: bytes) -> bytes:
    # Preserve all task requirements and fenced examples. Only real task block
    # execution fields and completion marks are normalized, not arbitrary prose.
    try:
        text = value.decode("utf-8-sig")
    except UnicodeError:
        raise SubjectError("task_encoding_invalid") from None
    lines = []
    fence = None
    in_task = False
    seen_fields: set[str] = set()
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = (marker.group(1)[0], len(marker.group(1)))
            elif (
                marker.group(1)[0] == fence[0]
                and len(marker.group(1)) >= fence[1]
            ):
                fence = None
            lines.append(line)
            continue
        if fence is not None:
            lines.append(line)
            continue
        header = re.match(
            r"^(###\s*任务\s*\d+\s*[:：]\s*)(?:\[[^]]*\])?(.*)$", line
        )
        if header:
            in_task = True
            seen_fields = set()
            line = (
                header.group(1).rstrip()
                + " [state] "
                + header.group(2).lstrip()
            )
        elif re.match(r"^#{1,3}\s", line):
            in_task = False
        if in_task:
            field = re.match(
                r"^-\s*(状态|attempts|control_stage)\s*[:：].*$", line
            )
            if (
                field
                and field.group(1) not in seen_fields
                and _valid_metadata(
                    field.group(1),
                    (
                        line.split("：", 1)[-1]
                        if "：" in line
                        else line.split(":", 1)[-1]
                    ),
                )
            ):
                seen_fields.add(field.group(1))
                # Omit presence as well as value: the controller may insert
                # optional attempts/control_stage on its first transition.
                continue
            line = re.sub(r"^(\s*-\s*)\[[ xX]\]", r"\1[state]", line)
        lines.append(line)
    return (
        "\n".join(lines) + ("\n" if text.endswith(("\n", "\r")) else "")
    ).encode("utf-8")


def _valid_metadata(name: str, value: str) -> bool:
    value = value.strip()
    if name == "attempts":
        return bool(re.fullmatch(r"[0-9]+", value))
    if name == "control_stage":
        return value in {
            "pending",
            "running",
            "quality_passed",
            "completed",
            "manual",
            "blocked",
            "awaiting_approval",
        }
    return any(
        value.casefold().startswith(state)
        for state in (
            "未开始",
            "进行中",
            "完成",
            "需人工",
            "阻塞",
            "已完成",
            "completed",
            "complete",
            "done",
            "x",
            "pending",
            "in progress",
            "in-progress",
            "blocked",
        )
    )


def _is_tasks(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        len(path.parts) >= 4
        and path.parts[:2] == ("openspec", "changes")
        and path.name == "tasks.md"
    )


def _signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_mode, info.st_size, info.st_mtime_ns, info.st_ino


def _entry(
    root: Path,
    value: str,
    properties: dict[str, str],
    index_mode: Optional[str],
    limitations: set[str],
) -> dict[str, Any]:
    path = root / value
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"path": value, "type": "missing", "properties": properties}
    except OSError:
        raise SubjectError("input_read_failed") from None
    entry: dict[str, Any] = {"path": value, "properties": properties}
    if stat.S_ISLNK(info.st_mode):
        try:
            target = os.readlink(path)
            resolved = path.resolve()
        except OSError:
            raise SubjectError("symlink_read_failed") from None
        entry.update(type="symlink", target=target)
        try:
            resolved.relative_to(root)
        except ValueError:
            limitations.add("external_symlink:" + value)
        else:
            if not resolved.exists():
                limitations.add("missing_symlink_target:" + value)
            elif _classify(resolved.relative_to(root).as_posix()) != "input":
                limitations.add("excluded_symlink_target:" + value)
    elif getattr(info, "st_file_attributes", 0) & 0x400:
        entry["type"] = "reparse-point"
        limitations.add("unsupported_reparse_point:" + value)
    elif stat.S_ISREG(info.st_mode):
        try:
            content = path.read_bytes()
            after = path.lstat()
        except OSError:
            raise SubjectError("input_read_failed") from None
        if _signature(info) != _signature(after):
            raise SubjectError("inputs_changed_during_capture")
        if _is_tasks(value):
            content = _task_bytes(content)
        # Windows does not represent Git executable bits in filesystem modes.
        executable = (
            (index_mode == "100755")
            if os.name == "nt"
            else bool(info.st_mode & 0o111)
        )
        entry.update(
            type="file",
            executable=executable,
            content_sha256=hashlib.sha256(content).hexdigest(),
        )
    elif stat.S_ISDIR(info.st_mode):
        entry["type"] = "directory"
    else:
        entry["type"] = "special"
        limitations.add("unsupported_file_type:" + value)
    try:
        if _signature(info) != _signature(path.lstat()):
            raise SubjectError("inputs_changed_during_capture")
    except OSError:
        raise SubjectError("inputs_changed_during_capture") from None
    return entry


def _walk_error(_: OSError) -> None:
    raise SubjectError("input_read_failed")


def _explicit_paths(root: Path, required: Sequence[str]) -> set[str]:
    result = set(required)
    for value in required:
        path = root / value
        if _classify(value) in ("vcs", "report"):
            continue
        # Never follow directory symlinks or recurse into VCS metadata.
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            for directory, names, files in os.walk(
                path,
                followlinks=False,
                onerror=_walk_error,
            ):
                names[:] = [
                    name for name in names if name not in VCS_DIRECTORY_NAMES
                ]
                relative = Path(directory).relative_to(root).as_posix()
                result.add(relative)
                result.update(
                    (Path(directory) / name).relative_to(root).as_posix()
                    for name in names + files
                )
        except OSError:
            raise SubjectError("input_read_failed") from None
    return result


def capture_subject(
    path: Path,
    base: str,
    *,
    config_path: Optional[Path] = None,
    required_inputs: Sequence[str] = (),
    external_inputs: Sequence[str] = (),
    backend: Optional[str] = None,
) -> dict[str, Any]:
    """Capture one canonical subject and explicit coverage limitations.

    Args:
        path: Workspace directory; its VCS root defines the project boundary.
        base: Fixed commit/revision provided by trusted baseline/CLI input.
        config_path: Verify configuration path; default is verify.config.json.
        required_inputs: Trusted additional project-relative input files/trees.
        external_inputs: Known external dependency labels; unsupported for now.
        backend: Explicit VCS backend where detection is ambiguous.

    Returns:
        subject_id plus complete, limitations, identity/base, entries and policy.
        Incomplete captures may be inspected but must not justify a PASS.

    Raises:
        SubjectError: Invalid paths, unreadable inputs or capture-time changes.
        vcs.VcsError: Failed repository queries or unsupported backends.
    """
    required = sorted({_path(value) for value in required_inputs})
    workspace = vcs.inspect_workspace(path, backend)
    root = Path(workspace["root"])
    explicit = _explicit_paths(root, required)
    config = (
        Path(config_path)
        if config_path is not None
        else root / "verify.config.json"
    )
    if not config.is_absolute():
        config = root / config
    config_relative = None
    try:
        config_relative = _path(config.relative_to(root).as_posix())
    except ValueError:
        pass
    if config_relative:
        explicit.add(config_relative)
    facts = vcs.capture_subject(
        path,
        base,
        backend,
        excluded_prefixes=REPORT_PREFIXES + GENERATED_PREFIXES,
        excluded_directory_names=CACHE_DIRECTORY_NAMES + VCS_DIRECTORY_NAMES,
        additional_paths=sorted(explicit),
    )
    limitations = set(facts["limitations"])
    if facts["conflicts"]:
        limitations.add("unresolved_vcs_conflicts")
    if external_inputs:
        limitations.add("external_inputs_unknown")
    if config_relative is None:
        limitations.add("external_verify_config")
    paths = {item["path"] for item in facts["files"] + facts["base_files"]}
    base_paths = {item["path"] for item in facts["base_files"]}
    tracked = {
        item["path"]
        for item in facts["files"] + facts["base_files"]
        if item["mode"] is not None
    }
    paths.update(explicit)
    if config_relative:
        paths.add(config_relative)
        explicit.add(config_relative)
    modes = {item["path"]: item["mode"] for item in facts["base_files"]}
    modes.update(
        {
            item["path"]: item["mode"]
            for item in facts["files"]
            if item["mode"] is not None
        }
    )
    entries = []
    for value in sorted(paths):
        _path(value)
        classification = _classify(value)
        if classification in ("vcs", "report"):
            if value in explicit or value in tracked:
                limitations.add("excluded_input_unsupported:" + value)
            continue
        if (
            classification == "generated"
            and value not in tracked
            and value not in explicit
        ):
            continue
        # Any ancestor link can make an otherwise ordinary path an external input.
        try:
            (root / value).parent.resolve().relative_to(root)
        except ValueError:
            limitations.add("external_input_parent:" + value)
            continue
        entry = _entry(
            root,
            value,
            facts["properties"].get(value, {}),
            modes.get(value),
            limitations,
        )
        if entry["type"] == "directory" and value not in explicit:
            limitations.add("unexpanded_directory_inputs:" + value)
        if (
            entry["type"] == "missing"
            and value not in base_paths
            and value not in explicit
        ):
            # A file added after the fixed base and then removed is absent in
            # both representations, including before its index deletion.
            continue
        if entry["type"] == "missing" and value in required:
            limitations.add("required_input_missing:" + value)
        if (
            entry["type"] == "missing"
            and config_path is not None
            and value == config_relative
        ):
            limitations.add("verify_config_missing")
        entries.append(entry)
    # HEAD/index records are intentionally absent; base union keeps deletion
    # tombstones stable through git add/rm/commit under the same fixed base.
    policy = {
        "algorithm": ALGORITHM,
        "report_prefixes": list(REPORT_PREFIXES),
        "generated_prefixes": list(GENERATED_PREFIXES),
        "cache_directory_names": list(CACHE_DIRECTORY_NAMES),
        "vcs_directory_names": list(VCS_DIRECTORY_NAMES),
        "task_metadata_fields": list(TASK_METADATA_FIELDS),
        "required_inputs": required,
        "external_inputs": sorted(set(external_inputs)),
        "config_path": config_relative,
        "coverage": "conservative_project_inputs",
    }
    payload = {
        "algorithm": ALGORITHM,
        "backend": facts["backend"],
        "repository_identity": facts["repository_identity"],
        "base": facts["base"],
        "entries": entries,
        "coverage_policy": policy,
    }
    return {
        **payload,
        "subject_id": _digest(payload),
        "complete": not limitations,
        "limitations": sorted(limitations),
    }


def compute_subject_id(
    path: Path,
    base: str,
    *,
    config_path: Optional[Path] = None,
    required_inputs: Sequence[str] = (),
    external_inputs: Sequence[str] = (),
    backend: Optional[str] = None,
) -> str:
    """Return a complete subject ID, rejecting uncertain coverage."""
    capture = capture_subject(
        path,
        base,
        config_path=config_path,
        required_inputs=required_inputs,
        external_inputs=external_inputs,
        backend=backend,
    )
    if not capture["complete"]:
        raise SubjectError("subject_coverage_incomplete")
    return capture["subject_id"]


def _validate_capture(capture: dict[str, Any]) -> None:
    keys = (
        "algorithm",
        "backend",
        "repository_identity",
        "base",
        "entries",
        "coverage_policy",
    )
    try:
        payload = {key: capture[key] for key in keys}
        if (
            capture["algorithm"] != ALGORITHM
            or type(capture["complete"]) is not bool
            or not isinstance(capture["limitations"], list)
            or capture["subject_id"] != _digest(payload)
        ):
            raise SubjectError("invalid_subject_capture")
    except (KeyError, TypeError, ValueError):
        raise SubjectError("invalid_subject_capture") from None


def compare_subjects(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    """Compare two captures; incomplete or mismatched evidence never verifies."""
    for capture in (before, after):
        _validate_capture(capture)
    limitations = sorted(set(before["limitations"] + after["limitations"]))
    complete = before["complete"] and after["complete"] and not limitations
    unchanged = before["subject_id"] == after["subject_id"]
    return {
        "unchanged": unchanged,
        "complete": complete,
        "verified": complete and unchanged,
        "limitations": limitations,
    }


def require_same_subject(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Reject changed content or coverage rather than reusing a stale result."""
    comparison = compare_subjects(before, after)
    if not comparison["complete"]:
        raise SubjectError("subject_coverage_incomplete")
    if not comparison["unchanged"]:
        raise SubjectError("subject_changed")
