"""Scoped Delivery 的 Git/SVN 残留工作区快照辅助函数。"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable, Sequence


class WorkspaceResidueError(ValueError):
    """工作区残留快照无法可靠采集或校验。"""


_RUNTIME_ARTIFACT_DIRECTORIES = frozenset(
    {"locks", "metrics", "native-delivery", "review", "runs", "verify"}
)


def _run_bytes(root: Path, args: Sequence[str]) -> bytes:
    try:
        result = subprocess.run(
            list(args),
            cwd=str(root),
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise WorkspaceResidueError(f"无法执行 {' '.join(args[:2])}：{error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise WorkspaceResidueError(
            f"命令失败（exit={result.returncode}）：{' '.join(args[:3])}"
            + (f"；{detail}" if detail else "")
        )
    return result.stdout


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256(payload)


def _decode_path(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape").replace("\\", "/")


def _normalize_scope_path(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise WorkspaceResidueError(f"Scoped Delivery 范围路径非法：{value!r}")
    normalized = path.as_posix().rstrip("/")
    if not normalized or normalized == ".":
        raise WorkspaceResidueError(f"Scoped Delivery 范围路径非法：{value!r}")
    return normalized


def normalize_scope_paths(paths: Iterable[str]) -> list[str]:
    """规范化并去重冻结的可写路径。"""
    normalized = sorted({_normalize_scope_path(path) for path in paths})
    if not normalized:
        raise WorkspaceResidueError("Scoped Delivery 至少需要一个冻结的范围路径")
    return normalized


def _path_in_scope(path: str, scope: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/").rstrip("/")
    return any(normalized == item or normalized.startswith(item + "/") for item in scope)


def _hash_path(path: Path) -> str:
    """为未跟踪文件或目录生成稳定的类型和内容树摘要。"""
    try:
        info = path.lstat()
    except OSError as error:
        raise WorkspaceResidueError(f"无法读取未跟踪路径 {path}：{error}") from error
    if path.is_symlink():
        return _canonical_digest({"type": "symlink", "target": os.readlink(path)})
    if path.is_file():
        try:
            return _sha256(path.read_bytes())
        except OSError as error:
            raise WorkspaceResidueError(f"无法读取未跟踪文件 {path}：{error}") from error
    if path.is_dir():
        entries: list[dict[str, str]] = []
        try:
            children = sorted(path.rglob("*"), key=lambda child: child.as_posix())
        except OSError as error:
            raise WorkspaceResidueError(f"无法遍历未跟踪目录 {path}：{error}") from error
        for child in children:
            relative = child.relative_to(path).as_posix()
            if child.is_dir() and not child.is_symlink():
                entries.append({"path": relative, "type": "directory"})
            else:
                entries.append(
                    {"path": relative, "type": "entry", "hash": _hash_path(child)}
                )
        return _canonical_digest({"type": "directory", "entries": entries})
    return _canonical_digest({"type": "other", "mode": info.st_mode})


def detect_vcs(root: Path) -> str:
    """返回 Git 或 SVN；无法确认时失败关闭。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip() == b"true":
            return "git"
    except OSError:
        pass
    try:
        result = subprocess.run(
            ["svn", "info", "--show-item", "revision"],
            cwd=str(root),
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return "svn"
    except OSError:
        pass
    raise WorkspaceResidueError("当前目录不在 Git 仓库或 SVN 工作副本内")


def _git_base(root: Path, diff_base: str) -> str:
    return _run_bytes(root, ["git", "rev-parse", "--verify", f"{diff_base}^{{commit}}"]).decode(
        "utf-8", errors="replace"
    ).strip()


def _git_entries(root: Path) -> list[dict[str, Any]]:
    raw = _run_bytes(
        root, ["git", "status", "--porcelain=v1", "-z", "--untracked-files=normal"]
    )
    records = raw.split(b"\0")
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise WorkspaceResidueError("无法解析 git status --porcelain 输出")
        status = record[:2].decode("ascii", errors="replace")
        path = _decode_path(record[3:])
        if status == "!!":
            continue
        entry: dict[str, Any] = {"path": path, "status": status}
        if status == "??":
            entry["kind"] = "untracked"
            entry["fingerprint"] = _hash_path(root / path)
        else:
            entry["kind"] = "tracked"
            if "R" in status or "C" in status:
                if index >= len(records) or not records[index]:
                    raise WorkspaceResidueError("无法解析 git rename/copy 的原路径")
                entry["old_path"] = _decode_path(records[index])
                index += 1
            index_diff = _run_bytes(root, ["git", "diff", "--cached", "--binary", "--", path])
            worktree_diff = _run_bytes(root, ["git", "diff", "--binary", "--", path])
            entry["fingerprint"] = _canonical_digest(
                {
                    "index": _sha256(index_diff),
                    "worktree": _sha256(worktree_diff),
                }
            )
        entries.append(entry)
    return sorted(entries, key=lambda entry: (entry["path"], entry["status"]))


def _svn_base(root: Path) -> str:
    return _run_bytes(root, ["svn", "info", "--show-item", "revision"]).decode(
        "utf-8", errors="replace"
    ).strip()


def _is_unversioned_runtime_artifact(root: Path, path_text: str, status: str) -> bool:
    """只排除未版本化且位于保留运行产物目录的框架自身文件。"""
    if status[0] != "?":
        return False
    runtime_root = root / ".agentic-framework"
    candidate = root / path_text
    try:
        relative = candidate.relative_to(runtime_root)
    except ValueError:
        return False
    if relative.parts:
        return relative.parts[0] in _RUNTIME_ARTIFACT_DIRECTORIES
    if not candidate.is_dir():
        return False
    try:
        return all(
            child.name in _RUNTIME_ARTIFACT_DIRECTORIES
            for child in candidate.iterdir()
        )
    except OSError:
        return False


def _svn_entries(root: Path) -> list[dict[str, Any]]:
    raw = _run_bytes(root, ["svn", "status", "--ignore-externals"])
    entries: list[dict[str, Any]] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if len(line) < 8:
            continue
        status = line[:7]
        path = line[7:].strip().replace("\\", "/")
        if (
            not path
            or status[0] in {"I", "X"}
            or _is_unversioned_runtime_artifact(root, path, status)
        ):
            continue
        if not any(char != " " for char in status):
            continue
        entry: dict[str, Any] = {"path": path, "status": status}
        if status[0] == "?":
            entry["kind"] = "untracked"
            entry["fingerprint"] = _hash_path(root / path)
        else:
            entry["kind"] = "tracked"
            diff = _run_bytes(root, ["svn", "diff", "--git", "--", path])
            entry["fingerprint"] = _sha256(diff)
        entries.append(entry)
    return sorted(entries, key=lambda entry: (entry["path"], entry["status"]))


def capture_workspace_residue(
    root: Path, diff_base: str, scope_paths: Iterable[str]
) -> dict[str, Any]:
    """采集冻结范围之外的工作区残留；重叠即失败关闭。"""
    root = root.resolve()
    scope = normalize_scope_paths(scope_paths)
    vcs = detect_vcs(root)
    if vcs == "git":
        base_ref = _git_base(root, diff_base)
        entries = _git_entries(root)
    else:
        base_ref = _svn_base(root)
        entries = _svn_entries(root)
    conflicts = sorted(
        {
            path
            for entry in entries
            for path in (entry["path"], entry.get("old_path"))
            if path and _path_in_scope(path, scope)
        }
    )
    if conflicts:
        raise WorkspaceResidueError(
            "预存残留与 Scoped Delivery 写入范围重叠：" + ", ".join(conflicts)
        )
    payload: dict[str, Any] = {
        "version": 1,
        "vcs": vcs,
        "base_ref": base_ref,
        "scope_paths": scope,
        "entries": entries,
        "residue_digest": _canonical_digest(entries),
    }
    payload["snapshot_digest"] = _canonical_digest(payload)
    return payload


def validate_workspace_residue_snapshot(snapshot: object) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise WorkspaceResidueError("Scoped Delivery 基线缺少 workspace_residue_snapshot 对象")
    required = {"version", "vcs", "base_ref", "scope_paths", "entries", "residue_digest", "snapshot_digest"}
    if set(snapshot) != required:
        raise WorkspaceResidueError("workspace_residue_snapshot 字段不完整或包含未知字段")
    if snapshot["version"] != 1 or snapshot["vcs"] not in {"git", "svn"}:
        raise WorkspaceResidueError("workspace_residue_snapshot 版本或 VCS 非法")
    if not isinstance(snapshot["scope_paths"], list) or not all(
        isinstance(item, str) for item in snapshot["scope_paths"]
    ):
        raise WorkspaceResidueError("workspace_residue_snapshot.scope_paths 非法")
    normalize_scope_paths(snapshot["scope_paths"])
    if not isinstance(snapshot["entries"], list):
        raise WorkspaceResidueError("workspace_residue_snapshot.entries 非法")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
    if snapshot["snapshot_digest"] != _canonical_digest(payload):
        raise WorkspaceResidueError("workspace_residue_snapshot 摘要不匹配")
    if snapshot["residue_digest"] != _canonical_digest(snapshot["entries"]):
        raise WorkspaceResidueError("workspace_residue_snapshot 残留摘要不匹配")
    return snapshot


def compare_workspace_residue(root: Path, snapshot: object) -> list[str]:
    """比较 S1 与经过完整性校验的 S0，并返回可审计差异。"""
    stored = validate_workspace_residue_snapshot(snapshot)
    root = root.resolve()
    if detect_vcs(root) != stored["vcs"]:
        return ["当前 VCS 与 S0 快照不一致"]
    if stored["vcs"] == "git":
        current_entries = _git_entries(root)
    else:
        current_entries = _svn_entries(root)
    if _canonical_digest(current_entries) == stored["residue_digest"]:
        return []
    old_by_path = {entry["path"]: entry for entry in stored["entries"]}
    new_by_path = {entry["path"]: entry for entry in current_entries}
    differences: list[str] = []
    for path in sorted(set(old_by_path) | set(new_by_path)):
        if old_by_path.get(path) != new_by_path.get(path):
            differences.append(path)
    return differences or ["残留摘要变化但无法定位路径"]


def git_commit_paths(root: Path, base_ref: str, commit: str) -> list[str]:
    """返回 Git 基准到交付提交的变更路径，并验证交付提交就是 HEAD。"""
    head = _run_bytes(root, ["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    resolved = _run_bytes(root, ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"]).decode("utf-8").strip()
    if head != resolved:
        raise WorkspaceResidueError("Scoped Delivery 的 Git 交付提交必须是当前 HEAD")
    _run_bytes(root, ["git", "merge-base", "--is-ancestor", base_ref, resolved])
    raw = _run_bytes(
        root,
        [
            "git",
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            f"{base_ref}..{resolved}",
            "--",
        ],
    )
    records = raw.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(records):
        status = records[index]
        index += 1
        if not status:
            continue
        if index >= len(records) or not records[index]:
            raise WorkspaceResidueError("无法解析 Git 交付提交的变更路径")
        paths.add(_decode_path(records[index]))
        index += 1
        if status.startswith((b"R", b"C")):
            if index >= len(records) or not records[index]:
                raise WorkspaceResidueError("无法解析 Git rename/copy 的另一条路径")
            paths.add(_decode_path(records[index]))
            index += 1
    return sorted(paths)


def svn_revision_paths(root: Path, revision: str) -> list[str]:
    """返回 SVN 单个交付 revision 的摘要路径。"""
    if not revision.isdigit() or int(revision) <= 0:
        raise WorkspaceResidueError("Scoped Delivery 的 SVN revision 必须为正整数")
    raw = _run_bytes(root, ["svn", "diff", "--summarize", "-c", revision])
    paths: list[str] = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if len(line) >= 2 and line[0] in {"A", "D", "M", "R"}:
            path = line[1:].strip().replace("\\", "/")
            if path:
                paths.append(path)
    if not paths:
        raise WorkspaceResidueError(f"SVN revision {revision} 未解析到变更路径")
    return sorted(set(paths))


def validate_delivery_paths(paths: Iterable[str], scope_paths: Sequence[str]) -> list[str]:
    """返回交付 Diff 中超出冻结范围的路径。"""
    scope = normalize_scope_paths(scope_paths)
    return sorted({path for path in paths if not _path_in_scope(path, scope)})
