"""Read-only VCS facts for Native validation; no subject hash is computed here.

Public results are JSON-compatible dictionaries. ``base`` is a resolved immutable
Git commit or SVN ``svn:r<N>``, never a moving ref. Git identity uses its common
directory; SVN identity is repository UUID plus project relative URL. SVN nodes
retain their WC base revision, independently from their last-changed revision.
Queries are read-only, bounded to 30 seconds, with no hidden retries or updates.
Query failures raise VcsError, never empty facts.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional, Sequence
from urllib.parse import unquote


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
    if result.returncode and args[0] == "svn":
        codes = set(re.findall(rb"E([0-9]{6})", result.stderr))
        if codes.intersection({b"170013", b"175002", b"000111", b"730061"}):
            raise VcsError("network_error", "svn:" + args[1])
        if codes.intersection({b"160006", b"160013", b"195012", b"200009"}):
            raise VcsError("invalid_revision", "svn:" + args[1])
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


def _xml(root: Path, *args: str) -> ET.Element:
    try:
        return ET.fromstring(_run(root, ["svn", *args, "--non-interactive"]))
    except ET.ParseError:
        raise VcsError("parse_error", "svn_xml") from None


def _svn_revision(value: str) -> int:
    match = re.fullmatch(r"(?:svn:r)?([0-9]+)", str(value))
    if not match:
        raise VcsError("invalid_revision", "svn_revision")
    return int(match.group(1))


def _svn_path(root: Path, value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        raise VcsError("parse_error", "svn_path") from None


def _svn_status(root: Path) -> list[dict[str, Any]]:
    records = []
    tree = _xml(
        root,
        "status",
        "--xml",
        "--verbose",
        "--no-ignore",
        "--ignore-externals",
        ".",
    )
    for entry in tree.findall(".//entry"):
        status = entry.find("wc-status")
        if status is None or not entry.get("path"):
            raise VcsError("parse_error", "svn_status")
        item, props = status.get("item"), status.get("props")
        if item not in {
            "normal",
            "none",
            "added",
            "missing",
            "deleted",
            "replaced",
            "modified",
            "merged",
            "conflicted",
            "obstructed",
            "ignored",
            "unversioned",
            "external",
            "incomplete",
        }:
            raise VcsError("parse_error", "svn_status")
        revision = status.get("revision")
        records.append(
            {
                "path": _svn_path(root, entry.attrib["path"]),
                "status": item,
                "property_status": props,
                "revision": (
                    int(revision) if revision and revision.isdigit() else None
                ),
                "conflict": item == "conflicted"
                or props == "conflicted"
                or status.get("tree-conflicted") == "true",
                "switched": status.get("switched") == "true",
                "moved_from": status.get("moved-from"),
                "moved_to": status.get("moved-to"),
            }
        )
    return records


def _svn_properties(
    root: Path, target: str, revision: Optional[int] = None
) -> dict[str, dict[str, Any]]:
    args = ["proplist", "--xml", "--verbose", "--depth", "infinity"]
    if revision is not None:
        args += ["--revision", str(revision)]
    args.append(target)
    tree = _xml(root, *args)
    properties = {}
    for node in tree.findall("target"):
        location = node.get("path", "")
        if revision is None:
            path = _svn_path(root, location)
        else:
            prefix = unquote(target.rsplit("@", 1)[0]).rstrip("/")
            location = unquote(location).rstrip("/")
            if location != prefix and not location.startswith(prefix + "/"):
                raise VcsError("parse_error", "svn_properties")
            path = location[len(prefix) :].lstrip("/") or "."
        values = {}
        for prop in node.findall("property"):
            key = prop.get("name")
            if not key:
                raise VcsError("parse_error", "svn_properties")
            value = prop.text or ""
            if prop.get("encoding") == "base64":
                try:
                    value = {
                        "encoding": "base64",
                        "value": base64.b64encode(
                            base64.b64decode(
                                re.sub(r"[ \t\r\n]", "", value), validate=True
                            )
                        ).decode("ascii"),
                    }
                except ValueError:
                    raise VcsError("parse_error", "svn_properties") from None
            elif prop.get("encoding") is not None:
                raise VcsError("parse_error", "svn_properties")
            values[key] = value
        properties[path] = values
    return properties


def _svn_info(root: Path) -> dict[str, Any]:
    tree = _xml(root, "info", "--xml", ".")
    entry = tree.find("entry")
    if entry is None:
        raise VcsError("parse_error", "svn_info")
    wc_root = entry.findtext("wc-info/wcroot-abspath")
    uuid = entry.findtext("repository/uuid")
    relative_url = entry.findtext("relative-url")
    url = entry.findtext("url")
    if (
        not wc_root
        or not uuid
        or not re.fullmatch(
            r"[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}", uuid
        )
        or not relative_url
        or not relative_url.startswith("^/")
        or not url
    ):
        raise VcsError("parse_error", "svn_identity")
    query_root = root
    root = Path(wc_root).resolve()
    # The project is the WC root, including its own URL even when called below it.
    if query_root.resolve() != root:
        return _svn_info(root)
    nodes = []
    statuses = _svn_status(root)
    properties = _svn_properties(root, ".")
    limits = set()
    for node in _xml(root, "info", "--xml", "--depth", "infinity", ".").findall(
        "entry"
    ):
        try:
            path = _svn_path(root, node.attrib["path"])
            kind = node.attrib["kind"]
            if kind not in ("file", "dir"):
                raise ValueError
            raw_revision = node.get("revision")
            revision = (
                int(raw_revision)
                if raw_revision and raw_revision.isdigit()
                else None
            )
            schedule = node.findtext("wc-info/schedule")
            if revision is None and schedule != "add":
                raise ValueError
            if schedule == "add":
                revision = None
            depth = node.findtext("wc-info/depth")
            node_url = node.findtext("url")
            node_uuid = node.findtext("repository/uuid")
            if not node_url or node_uuid != uuid:
                limits.add("svn_node_repository_mismatch")
            expected = unquote(url).rstrip("/") + (
                "/" + path if path != "." else ""
            )
            switched = not node_url or unquote(node_url).rstrip("/") != expected
            if switched:
                limits.add("svn_switched_subtree")
            if kind == "dir" and depth != "infinity":
                limits.add("svn_sparse_working_copy")
            nodes.append(
                {
                    "path": path,
                    "kind": kind,
                    "revision": revision,
                    "url": node_url,
                    "depth": depth,
                    "schedule": schedule,
                    "switched": switched,
                }
            )
        except (KeyError, ValueError):
            raise VcsError("parse_error", "svn_nodes") from None
    revisions = {
        node["revision"] for node in nodes if node["revision"] is not None
    }
    if len(revisions) > 1:
        limits.add("svn_mixed_revisions")
    externals = any(
        "svn:externals" in values for values in properties.values()
    ) or any(item["status"] == "external" for item in statuses)
    if externals:
        limits.add("svn_externals_unsupported")
    for item in statuses:
        if item["status"] in ("obstructed", "incomplete", "missing"):
            limits.add("svn_incomplete_nodes")
    return {
        "backend": "svn",
        "root": str(root),
        "repository_identity": {
            "uuid": uuid.lower(),
            "relative_url": relative_url,
        },
        "url": url,
        "repository_root": entry.findtext("repository/root"),
        "base": "svn:r" + str(_svn_revision(entry.attrib["revision"])),
        "nodes": nodes,
        "statuses": statuses,
        "properties": properties,
        "conflicts": sorted(
            item["path"] for item in statuses if item["conflict"]
        ),
        "capabilities": [
            "inspect_workspace",
            "capture_subject",
            "collect_changes",
            "verify_delivery",
        ],
        "limitations": sorted(limits),
        "mixed_revisions": len(revisions) > 1,
        "switched": "svn_switched_subtree" in limits,
        "sparse": "svn_sparse_working_copy" in limits,
        "externals": externals,
    }


def _svn_tree(
    root: Path, facts: dict[str, Any], revision: int
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    target = facts["url"] + "@" + str(revision)
    remote = _xml(
        root, "info", "--xml", "--revision", str(revision), target
    ).find("entry")
    if (
        remote is None
        or remote.findtext("repository/uuid")
        != facts["repository_identity"]["uuid"]
        or remote.findtext("relative-url")
        != facts["repository_identity"]["relative_url"]
    ):
        raise VcsError("repository_mismatch", "svn_revision")
    entries = [{"path": ".", "kind": "dir", "mode": "dir"}]
    tree = _xml(
        root,
        "list",
        "--xml",
        "--recursive",
        "--revision",
        str(revision),
        target,
    )
    for node in tree.findall(".//entry"):
        name, kind = node.findtext("name"), node.get("kind")
        if (
            not name
            or kind not in ("file", "dir")
            or Path(name).is_absolute()
            or ".." in Path(name).parts
        ):
            raise VcsError("parse_error", "svn_tree")
        entries.append({"path": name.rstrip("/"), "kind": kind, "mode": kind})
    return entries, _svn_properties(root, target, revision)


def _svn_capture(
    facts: dict[str, Any],
    base: str,
    prefixes: Sequence[str],
    directory_names: Sequence[str],
) -> dict[str, Any]:
    root = Path(facts["root"])
    revision = _svn_revision(base)
    base_files, base_properties = _svn_tree(root, facts, revision)
    facts["base"] = "svn:r" + str(revision)
    if any(
        node["revision"] != revision
        for node in facts["nodes"]
        if node["revision"] is not None
    ):
        facts["limitations"] = sorted(
            set(facts["limitations"] + ["svn_node_base_mismatch"])
        )
    versioned = {
        node["path"]: {
            "path": node["path"],
            "mode": node["kind"],
            "kind": node["kind"],
            "revision": node["revision"],
            "stage": 0,
        }
        for node in facts["nodes"]
    }

    # XML status folds unversioned trees; expand them without following links,
    # excluding only the trusted generated policy and VCS administrative trees.
    def excluded(path: str) -> bool:
        return any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in prefixes
        ) or any(part in directory_names for part in Path(path).parts)

    def walk_error(error):
        raise VcsError("query_failed", "svn_filesystem") from error

    for directory, names, files in os.walk(
        root, followlinks=False, onerror=walk_error
    ):
        if Path(directory) != root and any(
            (Path(directory) / name).exists() for name in (".git", ".svn")
        ):
            facts["limitations"].append("svn_nested_repository_inputs")
        relative = Path(directory).relative_to(root).as_posix()
        names[:] = [
            name
            for name in names
            if name not in (".svn", ".git")
            and not excluded(
                (Path(directory) / name).relative_to(root).as_posix()
            )
        ]
        if relative != "." and relative not in versioned:
            versioned[relative] = {
                "path": relative,
                "mode": None,
                "kind": "dir",
                "stage": 0,
            }
        for name in files + [
            name for name in names if (Path(directory) / name).is_symlink()
        ]:
            path = (Path(directory) / name).relative_to(root).as_posix()
            if not excluded(path) and path not in versioned:
                versioned[path] = {
                    "path": path,
                    "mode": None,
                    "kind": "file",
                    "stage": 0,
                }
    if versioned.get(".agentic-framework", {}).get("mode") is None and not any(
        path.startswith(".agentic-framework/") for path in versioned
    ):
        versioned.pop(".agentic-framework", None)
    facts["files"] = list(versioned.values())
    facts["base_files"] = base_files
    facts["base_properties"] = base_properties
    facts["coverage"] = "tracked_and_untracked_including_ignored"
    return facts


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
    path: Path,
    base: str,
    backend: Optional[str] = None,
    facts: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Return Git working-tree changes against a fixed base, including untracked.

    Renames retain both paths; status U and index conflicts are never hidden.
    Git behavioral properties are captured separately by capture_subject.
    ``facts`` 复用同进程内已取得的 inspect_workspace 结果（终审 P1：每次
    verify 运行此前的 8 次全量探测是纯冗余）。
    """
    facts = facts if facts is not None else inspect_workspace(path, backend)
    if facts["backend"] == "svn":
        return _svn_changes(facts, base)
    root = Path(facts["root"])
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


def _base_files(root: Path, base: str) -> list[dict[str, Any]]:
    entries = []
    for record in _records(_git(root, "ls-tree", "-rz", "--full-tree", base)):
        try:
            metadata, path = record.split(b"\t", 1)
            mode, kind, oid = metadata.split(b" ")
            if mode not in (b"100644", b"100755", b"120000", b"160000"):
                raise ValueError
            if kind not in (b"blob", b"commit") or not path:
                raise ValueError
            if not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", oid):
                raise ValueError
            entries.append(
                {
                    "path": _text(path),
                    "mode": _text(mode),
                    "object_id": _text(oid),
                    "kind": _text(kind),
                }
            )
        except ValueError:
            raise VcsError("parse_error", "git_base_tree") from None
    return entries


def capture_subject(
    path: Path,
    base: str,
    backend: Optional[str] = None,
    *,
    excluded_prefixes: Sequence[str] = (),
    excluded_directory_names: Sequence[str] = (),
    additional_paths: Sequence[str] = (),
    facts: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Capture fixed VCS facts without choosing the subject digest algorithm.

    Args:
        path: Directory inside a working copy.
        base: Fixed commit, resolved before collecting files.
        backend: Explicit backend for dual-VCS workspaces.
        excluded_prefixes: Trusted generated directories excluded at query time
            from untracked enumeration only. Tracked/base files always survive.
        excluded_directory_names: Trusted cache directory names, no wildcards.
        additional_paths: Explicit inputs needing attributes despite exclusions.
        facts: Reuse an in-process inspect_workspace result (final-review P1:
            repeated full probes per run are pure overhead; Git branch only —
            the SVN branch derives its own facts before delegating).

    Returns:
        Repository identity, resolved base, current files, base_files and effective
        attributes. Ignored untracked inputs survive unless explicitly classified.

    Raises:
        VcsError: Invalid filters, unsupported backends or failed queries.
    """
    prefixes = _scope(excluded_prefixes) if excluded_prefixes else []
    if any(any(char in item for char in "*?[]()") for item in prefixes):
        raise VcsError("invalid_scope", "subject_exclusions")
    if any(
        not re.fullmatch(r"[a-zA-Z0-9_.-]+", name) or name in (".", "..")
        for name in excluded_directory_names
    ):
        raise VcsError("invalid_scope", "subject_exclusions")
    facts = dict(facts) if facts is not None else inspect_workspace(path, backend)
    if facts["backend"] == "svn":
        return _svn_capture(facts, base, prefixes, excluded_directory_names)
    root = Path(facts["root"])
    facts["base"] = _commit(root, base)
    files = _index(root)
    base_files = _base_files(root, facts["base"])
    tracked = {item["path"] for item in files}
    pathspecs = ["."]
    for prefix in prefixes:
        pathspecs.extend(
            [f":(literal,exclude){prefix}", f":(glob,exclude){prefix}/**"]
        )
    pathspecs.extend(
        f":(glob,exclude)**/{name}/**" for name in excluded_directory_names
    )
    # Filter inside Git so an installed tool environment or Worktree forest is
    # never traversed and materialized before Python can discard it.
    others = _records(
        _run(root, ["git", "ls-files", "--others", "-z", "--", *pathspecs])
    )
    files.extend(
        {"path": _text(item), "mode": None, "object_id": None, "stage": 0}
        for item in others
        if _text(item) not in tracked
    )
    all_paths = {item["path"] for item in files + base_files}
    all_paths.update(_scope(additional_paths) if additional_paths else [])
    attribute_input = b"".join(
        item.encode("utf-8", "surrogateescape") + b"\0"
        for item in sorted(all_paths)
    )
    attributes = (
        _records(
            _run(
                root,
                ["git", "check-attr", "--all", "-z", "--stdin"],
                attribute_input,
            )
        )
        if all_paths
        else []
    )
    if len(attributes) % 3:
        raise VcsError("parse_error", "git_attributes")
    properties: dict[str, dict[str, str]] = {}
    for offset in range(0, len(attributes), 3):
        file_path, key, value = map(_text, attributes[offset : offset + 3])
        if file_path not in all_paths or not key:
            raise VcsError("parse_error", "git_attributes")
        properties.setdefault(file_path, {})[key] = value
    facts["files"] = files
    facts["base_files"] = base_files
    facts["properties"] = properties
    facts["coverage"] = "tracked_and_untracked_including_ignored"
    facts["untracked_exclusions"] = {
        "prefixes": sorted(set(prefixes)),
        "directory_names": sorted(set(excluded_directory_names)),
    }
    if any(item["mode"] == "160000" for item in files + base_files):
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
            or item.root
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
    not test/review success. SVN uses exact revision bytes and properties.
    """
    facts = inspect_workspace(path, backend)
    if facts["backend"] == "svn":
        return _svn_verify(facts, commit, base, scope, repository_identity)
    root = Path(facts["root"])
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


def _svn_changes(facts: dict[str, Any], base: str) -> list[dict[str, Any]]:
    root = Path(facts["root"])
    revision = _svn_revision(base)
    _, base_properties = _svn_tree(root, facts, revision)
    tree = _xml(
        root, "diff", "--summarize", "--xml", "--revision", str(revision), "."
    )
    changes = []
    by_path = {item["path"]: item for item in facts["statuses"]}
    for node in tree.findall(".//path"):
        path = _svn_path(root, node.text or "")
        item, props = node.get("item"), node.get("props")
        if item not in {"added", "deleted", "modified", "none"}:
            raise VcsError("parse_error", "svn_diff")
        if props == "modified" and facts["properties"].get(
            path, {}
        ) == base_properties.get(path, {}):
            props = "none"
        if item == "none" and props == "none":
            continue
        status = by_path.get(path, {})
        old_path = status.get("moved_from")
        changes.append(
            {
                "path": path,
                "status": (
                    "R"
                    if old_path
                    else {
                        "added": "A",
                        "deleted": "D",
                        "modified": "M",
                        "none": "M",
                    }[item]
                ),
                "old_path": _svn_path(root, old_path) if old_path else None,
                "property_changes": ["modified"] if props == "modified" else [],
            }
        )
    present = {item["path"] for item in changes}
    for item in facts["statuses"]:
        if (
            item["status"]
            in ("unversioned", "ignored", "conflicted", "obstructed", "missing")
            and item["path"] not in present
        ):
            changes.append(
                {
                    "path": item["path"],
                    "status": (
                        "U"
                        if item["conflict"]
                        else (
                            "?"
                            if item["status"] in ("unversioned", "ignored")
                            else "!"
                        )
                    ),
                    "old_path": None,
                    "property_changes": (
                        ["conflicted"]
                        if item["property_status"] == "conflicted"
                        else []
                    ),
                }
            )
    return changes


def _svn_verify(
    facts: dict[str, Any],
    revision_value: str,
    base: str,
    scope: Optional[Sequence[str]],
    identity: Optional[dict[str, str]],
) -> dict[str, Any]:
    """Read exact revision facts and compare their canonical bytes/properties.

    This is a VCS content check, never a Verify/Review or authorization claim.
    No checkout/export/update/commit is hidden inside the adapter.
    """
    try:
        from . import native_subject
    except ImportError:
        import native_subject
    revision, first = _svn_revision(revision_value), _svn_revision(base)
    if revision == 0 or revision < first:
        raise VcsError("invalid_revision", "svn_revision_range")
    if identity is not None and identity != facts["repository_identity"]:
        raise VcsError("repository_mismatch", "svn_delivery")
    if facts["conflicts"]:
        raise VcsError("conflicts", "svn_delivery")
    if facts["limitations"]:
        raise VcsError("coverage_incomplete", "svn_delivery")
    if any(node["revision"] != revision for node in facts["nodes"]):
        raise VcsError("revision_mismatch", "svn_delivery")
    root = Path(facts["root"])
    paths = _scope(scope)
    target = facts["url"] + "@" + str(revision)
    logs = (
        _xml(
            root,
            "log",
            "--xml",
            "--verbose",
            "--revision",
            f"{first + 1}:{revision}",
            target,
        )
        if first < revision
        else ET.Element("log")
    )
    relative_prefix = unquote(
        facts["repository_identity"]["relative_url"][1:]
    ).rstrip("/")
    changed = set()
    for node in logs.findall(".//path"):
        remote_path = node.text or ""
        if (
            relative_prefix
            and remote_path != relative_prefix
            and not remote_path.startswith(relative_prefix + "/")
        ):
            continue
        local = remote_path[len(relative_prefix) :].lstrip("/") or "."
        changed.add(local)
        copied = node.get("copyfrom-path")
        if copied and (
            not relative_prefix or copied.startswith(relative_prefix + "/")
        ):
            changed.add(copied[len(relative_prefix) :].lstrip("/"))
    if paths and any(
        not any(item == p or item.startswith(p + "/") for p in paths)
        for item in changed
    ):
        raise VcsError("scope_mismatch", "svn_delivery")
    remote_files, properties = _svn_tree(root, facts, revision)
    capture = native_subject.capture_subject(
        root, "svn:r" + str(revision), backend="svn"
    )
    if not capture["complete"]:
        raise VcsError("coverage_incomplete", "svn_delivery")
    # 终审修复（两轮）：逐文件 `svn cat` 是 N+1 远程子进程；改用
    # `svn diff --summarize` 又继承了 SVN 的 mtime+size 捷径——伪造 stat
    # 即绕过内容比对（复审实测确认）。最终方案：一次 `svn export` 把确切
    # revision 的真实字节导出到系统临时目录（O(1) 子进程、不触碰用户工作
    # 副本），在 Python 侧与工作副本真实读取字节逐文件比对；EOL/keywords
    # 两侧都过 normalize_svn_content 规范化，语义与原 cat 实现一致。
    with tempfile.TemporaryDirectory(prefix="agentic-svn-verify-") as scratch:
        export_root = Path(scratch) / "tree"
        target = facts["url"].rstrip("/") + "@" + str(revision)
        _run(
            root,
            [
                "svn",
                "export",
                "--non-interactive",
                "--revision",
                str(revision),
                "--force",
                "--depth",
                "infinity",
                target,
                str(export_root),
            ],
        )
        # Unversioned paths are Scoped Delivery residue, not revision content:
        # the residue channel (S0/S1 snapshot compare at the delivery gate)
        # protects them separately, so the tree comparison stays on versioned
        # nodes only.
        versioned = {node["path"] for node in facts["nodes"]}
        current = {
            entry["path"]: entry
            for entry in capture["entries"]
            if entry["type"] != "missing" and entry["path"] in versioned
        }
        expected = {}
        for item in remote_files:
            path = item["path"]
            if path != "." and native_subject._classify(path) in ("vcs", "report"):
                raise VcsError("coverage_incomplete", "svn_delivery")
            if item["kind"] == "dir":
                expected[path] = {
                    "path": path,
                    "type": "directory",
                    "properties": properties.get(path, {}),
                }
                continue
            exported = export_root / path
            try:
                content = exported.read_bytes()
            except OSError:
                raise VcsError("content_mismatch", "svn_delivery") from None
            limits: set[str] = set()
            content = native_subject.normalize_svn_content(
                content, properties.get(path, {}), limits
            )
            if limits:
                raise VcsError("coverage_incomplete", "svn_delivery")
            if native_subject._is_tasks(path):
                content = native_subject._task_bytes(content)
            expected[path] = {
                "path": path,
                "type": "file",
                "properties": properties.get(path, {}),
                "executable": "svn:executable" in properties.get(path, {}),
                "content_sha256": hashlib.sha256(content).hexdigest(),
            }
    # Default absent Verify config is an input sentinel, not repository content.
    if current != expected:
        raise VcsError("content_mismatch", "svn_delivery")
    return {
        "backend": "svn",
        "repository_identity": facts["repository_identity"],
        "revision": revision,
        "base": "svn:r" + str(first),
        "scope": paths,
        "verified": True,
        "changes": sorted(changed),
        "subject_id": capture["subject_id"],
    }
