"""Read-only VCS facts for Native validation; no subject hash is computed here.

Public results are JSON-compatible dictionaries. ``base`` is a resolved immutable
commit, never a moving ref. Repository identity uses Git's common directory so
linked Worktrees share identity. Query failures raise VcsError, never empty facts.
"""

from __future__ import annotations

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Sequence


class VcsError(Exception):
    """A classified VCS failure with safe code and operation fields."""

    def __init__(self, code: str, operation: str) -> None:
        super().__init__(f"{code}: {operation}")
        self.code = code
        self.operation = operation


def _run(
    root: Path, args: Sequence[str], data: Optional[bytes] = None
) -> bytes:
    env = os.environ.copy()
    # Ambient Git overrides must not redirect a query to a different repository.
    for key in tuple(env):
        if key.startswith("GIT_"):
            env.pop(key)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        result = subprocess.run(
            list(args),
            cwd=str(root),
            env=env,
            capture_output=True,
            check=False,
            timeout=30,
            input=data,
        )
    except FileNotFoundError:
        raise VcsError("tool_missing", args[0]) from None
    except subprocess.TimeoutExpired:
        raise VcsError("query_timeout", args[0]) from None
    except OSError:
        raise VcsError("query_failed", args[0]) from None
    if result.returncode:
        raise VcsError("query_failed", args[0] + ":" + args[1])
    return result.stdout


def _text(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def _records(value: bytes) -> list[bytes]:
    if not value:
        return []
    if not value.endswith(b"\0"):
        raise VcsError("parse_error", "nul_records")
    return value[:-1].split(b"\0")


def _markers(path: Path, name: str) -> list[Path]:
    return [
        parent for parent in (path, *path.parents) if (parent / name).exists()
    ]


def _root(path: Path) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_dir():
        raise VcsError("invalid_path", "workspace")
    return resolved


def _git(root: Path, *args: str) -> bytes:
    return _run(
        root,
        ["git", "--literal-pathspecs", "-c", "core.quotepath=false", *args],
    )


def _commit(root: Path, value: str) -> str:
    if not value or value.startswith("-") or "\0" in value:
        raise VcsError("invalid_revision", "git_commit")
    try:
        commit = _text(
            _git(root, "rev-parse", "--verify", value + "^{commit}")
        ).strip()
    except VcsError as error:
        if error.code == "query_failed":
            raise VcsError("invalid_revision", "git_commit") from None
        raise
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise VcsError("parse_error", "git_commit")
    return commit


def _svn_info(root: Path) -> dict[str, Any]:
    try:
        entry = ET.fromstring(_run(root, ["svn", "info", "--xml"])).find(
            "entry"
        )
        if entry is None:
            raise ValueError
        wc_root = entry.findtext("wc-info/wcroot-abspath")
        uuid = entry.findtext("repository/uuid")
        relative_url = entry.findtext("relative-url")
        if not wc_root or not uuid or not relative_url:
            raise ValueError
        return {
            "backend": "svn",
            "root": str(Path(wc_root).resolve()),
            "repository_identity": {"uuid": uuid, "relative_url": relative_url},
            "base": entry.attrib["revision"],
            "conflicts": [],
            "capabilities": ["inspect_workspace"],
            "limitations": ["svn_full_inspection_unsupported"],
            "mixed_revisions": None,
            "externals": None,
        }
    except (ET.ParseError, ValueError, KeyError):
        raise VcsError("parse_error", "svn_info") from None


def inspect_workspace(
    path: Path, backend: Optional[str] = None
) -> dict[str, Any]:
    """Identify the workspace without silently choosing between Git and SVN.

    Args:
        path: Directory inside the working copy.
        backend: Explicit ``git`` or ``svn`` to resolve a dual-VCS workspace.

    Returns:
        Root, identity, HEAD/base, conflicts, capabilities and limitations.

    Raises:
        VcsError: Missing tools, invalid workspaces, ambiguity or failed queries.
    """
    root = _root(path)
    if backend not in (None, "git", "svn"):
        raise VcsError("unsupported_backend", "inspect_workspace")
    detected = [
        name
        for name, marker in (("git", ".git"), ("svn", ".svn"))
        if _markers(root, marker)
    ]
    if len(detected) > 1 and backend is None:
        raise VcsError("ambiguous_backend", "inspect_workspace")
    selected = backend or (detected[0] if detected else None)
    if selected is None:
        raise VcsError("not_working_copy", "inspect_workspace")
    if selected not in detected:
        raise VcsError("not_working_copy", "inspect_workspace")
    if selected == "svn":
        facts = _svn_info(root)
    else:
        git_root = Path(
            _text(_git(root, "rev-parse", "--show-toplevel")).strip()
        ).resolve()
        common = Path(
            _text(_git(git_root, "rev-parse", "--git-common-dir")).strip()
        )
        if not common.is_absolute():
            common = git_root / common
        head = _commit(git_root, "HEAD")
        stages = _index(git_root)
        facts = {
            "backend": "git",
            "root": str(git_root),
            "repository_identity": {"common_dir": str(common.resolve())},
            "base": head,
            "head": head,
            "conflicts": sorted(
                {item["path"] for item in stages if item["stage"]}
            ),
            "capabilities": [
                "inspect_workspace",
                "capture_subject",
                "collect_changes",
                "verify_delivery",
            ],
            "limitations": [],
            "mixed_revisions": False,
            "externals": False,
        }
    facts["detected_backends"] = detected
    return facts


def _index(root: Path) -> list[dict[str, Any]]:
    entries = []
    for record in _records(_git(root, "ls-files", "--stage", "-z")):
        try:
            metadata, path = record.split(b"\t", 1)
            mode, oid, stage = metadata.split(b" ")
            if mode not in (
                b"100644",
                b"100755",
                b"120000",
                b"160000",
            ) or stage not in (b"0", b"1", b"2", b"3"):
                raise ValueError
            if not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", oid) or not path:
                raise ValueError
            entries.append(
                {
                    "path": _text(path),
                    "mode": _text(mode),
                    "object_id": _text(oid),
                    "stage": int(stage),
                }
            )
        except ValueError:
            raise VcsError("parse_error", "git_index") from None
    return entries


def _diff(
    root: Path, base: str, target: Optional[str] = None
) -> list[dict[str, Any]]:
    revisions = [base] + ([target] if target else [])
    records = iter(
        _records(
            _git(
                root,
                "diff",
                "--name-status",
                "-z",
                "--find-renames",
                *revisions,
                "--",
            )
        )
    )
    changes = []
    try:
        for status in records:
            if not re.fullmatch(rb"[ACDMRTUXB](?:[0-9]{1,3})?", status):
                raise ValueError
            old_path = None
            path = next(records)
            if status[:1] in (b"R", b"C"):
                old_path, path = path, next(records)
            if not path:
                raise ValueError
            changes.append(
                {
                    "path": _text(path),
                    "status": _text(status),
                    "old_path": _text(old_path) if old_path else None,
                    "property_changes": [],
                }
            )
    except (ValueError, StopIteration):
        raise VcsError("parse_error", "git_diff") from None
    return changes


def _unsupported(facts: dict[str, Any], operation: str) -> Path:
    if facts["backend"] != "git":
        raise VcsError("unsupported", "svn:" + operation)
    return Path(facts["root"])


def collect_changes(
    path: Path, base: str, backend: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return Git working-tree changes against a fixed base, including untracked.

    Renames retain both paths; status U and index conflicts are never hidden.
    Git behavioral properties are captured separately by capture_subject.
    """
    root = _unsupported(inspect_workspace(path, backend), "collect_changes")
    changes = _diff(root, _commit(root, base))
    changes.extend(
        {
            "path": _text(item),
            "status": "?",
            "old_path": None,
            "property_changes": [],
        }
        for item in _records(
            _git(root, "ls-files", "--others", "--exclude-standard", "-z")
        )
    )
    return changes


def capture_subject(
    path: Path, base: str, backend: Optional[str] = None
) -> dict[str, Any]:
    """Capture VCS identity/base/file facts; the caller computes one shared hash.

    Files include ignored/untracked paths to avoid hiding build inputs behind
    gitignore. No file-content digest is invented at this layer. Git attributes
    and index modes are facts for the public subject algorithm to consume.
    """
    facts = inspect_workspace(path, backend)
    root = _unsupported(facts, "capture_subject")
    facts["base"] = _commit(root, base)
    files = _index(root)
    tracked = {item["path"] for item in files}
    others = _records(_git(root, "ls-files", "--others", "-z"))
    files.extend(
        {"path": _text(item), "mode": None, "object_id": None, "stage": 0}
        for item in others
        if _text(item) not in tracked
    )
    attribute_input = b"".join(
        item.encode("utf-8", "surrogateescape") + b"\0"
        for item in sorted({item["path"] for item in files})
    )
    attributes = (
        _records(
            _run(
                root,
                ["git", "check-attr", "--all", "-z", "--stdin"],
                attribute_input,
            )
        )
        if files
        else []
    )
    if len(attributes) % 3:
        raise VcsError("parse_error", "git_attributes")
    properties: dict[str, dict[str, str]] = {}
    for offset in range(0, len(attributes), 3):
        file_path, key, value = map(_text, attributes[offset : offset + 3])
        properties.setdefault(file_path, {})[key] = value
    facts["files"] = files
    facts["properties"] = properties
    facts["coverage"] = "tracked_and_untracked_including_ignored"
    if any(item["mode"] == "160000" for item in files):
        facts["limitations"].append(
            "submodule_inputs_require_explicit_coverage"
        )
    return facts


def _scope(paths: Optional[Sequence[str]]) -> list[str]:
    if paths is None:
        return []
    if not paths:
        raise VcsError("invalid_scope", "verify_delivery")
    result = []
    for value in paths:
        item = Path(value)
        if (
            not value
            or item.is_absolute()
            or ".." in item.parts
            or value.startswith("-")
            or item.as_posix() == "."
            or "\0" in value
            or item.drive
        ):
            raise VcsError("invalid_scope", "verify_delivery")
        result.append(item.as_posix().rstrip("/"))
    return result


def verify_delivery(
    path: Path,
    commit: str,
    base: str,
    scope: Optional[Sequence[str]] = None,
    backend: Optional[str] = None,
    repository_identity: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Verify exact Git HEAD, ancestry, changed scope and working content.

    Raises VcsError for mismatches. A successful result proves these VCS facts,
    not test/review success. SVN revision verification is explicitly unsupported.
    """
    facts = inspect_workspace(path, backend)
    root = _unsupported(facts, "verify_delivery")
    target, fixed_base = _commit(root, commit), _commit(root, base)
    paths = _scope(scope)
    if (
        repository_identity is not None
        and facts["repository_identity"] != repository_identity
    ):
        raise VcsError("repository_mismatch", "verify_delivery")
    if facts["head"] != target:
        raise VcsError("head_mismatch", "verify_delivery")
    if facts["conflicts"]:
        raise VcsError("conflicts", "verify_delivery")
    try:
        _git(root, "merge-base", "--is-ancestor", fixed_base, target)
    except VcsError as error:
        if error.code == "query_failed":
            raise VcsError("base_not_ancestor", "verify_delivery") from None
        raise
    committed = _diff(root, fixed_base, target)
    changed_paths = {
        change[key]
        for change in committed
        for key in ("path", "old_path")
        if change[key]
    }
    if paths and any(
        not any(item == p or item.startswith(p + "/") for p in paths)
        for item in changed_paths
    ):
        raise VcsError("scope_mismatch", "verify_delivery")
    if _git(root, "diff", "--name-only", "-z", target, "--", *paths):
        raise VcsError("content_mismatch", "verify_delivery")
    untracked = _records(
        _git(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            *paths,
        )
    )
    if untracked:
        raise VcsError("untracked_content", "verify_delivery")
    return {
        "backend": "git",
        "repository_identity": facts["repository_identity"],
        "commit": target,
        "base": fixed_base,
        "scope": paths,
        "verified": True,
        "changes": committed,
    }
