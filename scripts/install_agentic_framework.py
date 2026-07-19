"""Install one framework profile and optional packs into agent clients."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence

CLIENT_DIRS = (".codex", ".claude")
MANIFEST_PATH = Path(".agentic-framework/manifest.json")
DEFAULT_REGISTRY_PATH = Path.home() / ".agentic-framework" / "installations.json"
FRAMEWORK_VERSION = "2026.07.19"
MANIFEST_SCHEMA_VERSION = 2
REGISTRY_SCHEMA_VERSION = 1

CORE_SKILLS = {
    "bp-architecture-design",
    "bp-coding-best-practices",
    "bp-component-design",
    "bp-distributed-systems",
    "bp-performance-optimization",
    "bp-skill-authoring",
    "project-init",
    "project-knowledge",
    "self-refinement",
    "std-cpp",
    "std-go",
    "std-python",
    "troubleshooting",
    "workflow-code-review",
    "workflow-verification",
}
PRODUCTION_SKILLS = {
    "opsx-archive",
    "opsx-code-generation",
    "opsx-quick-design",
    "opsx-requirements-clarification",
    "opsx-system-design",
    "opsx-test-generation",
}
TOOLING_SKILLS = {
    "workflow-code-generation",
    "workflow-quick-design",
    "workflow-requirements-clarification",
    "workflow-system-design",
    "workflow-test-generation",
}
CORE_COMMANDS = {
    "code-review.md",
    "performance-optimization.md",
    "project-init.md",
    "reflect.md",
    "skill-authoring.md",
    "troubleshooting.md",
}
PRODUCTION_COMMANDS = {
    "opsx-archive.md",
    "opsx-code-generation.md",
    "opsx-quick-design.md",
    "opsx-requirements-clarification.md",
    "opsx-system-design.md",
    "opsx-test-generation.md",
}
TOOLING_COMMANDS = {
    "code-generation.md",
    "quick-design.md",
    "requirements-clarification.md",
    "system-design.md",
    "test-generation.md",
    "verification.md",
    "verify-config.md",
}
PACK_SKILLS = {
    "frontend": {
        "bp-frontend-layout",
        "bp-frontend-taste",
        "frontend-playwright-verification",
        "std-react",
        "workflow-frontend-design",
    },
    "project-init": {"project-init"},
    "open-code-review": {"open-code-review"},
    "telemetry": set(),
}
PACK_COMMANDS = {
    "frontend": {"frontend-design.md"},
    "project-init": {"project-init.md"},
    "open-code-review": set(),
    "telemetry": set(),
}
TOOLING_ONLY_PACKS = {"frontend"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
ACTIVE_AGENT_FILES = {
    "codebase-researcher.md",
    "comprehensive-reviewer.md",
    "magical-prompt-reviewer.md",
    "performance-reviewer.md",
    "review-critic.md",
    "robustness-reviewer.md",
    "spec-compliance-reviewer.md",
    "standards-reviewer.md",
}
# Append-only compatibility namespaces for previously installed manifests. When a
# source entry is retired, remove it from the install selection above but retain it
# here so an older installation can still be safely uninstalled.
MANAGED_AGENT_FILES = frozenset(
    {
        "codebase-researcher.md",
        "comprehensive-reviewer.md",
        "magical-prompt-reviewer.md",
        "performance-reviewer.md",
        "review-critic.md",
        "robustness-reviewer.md",
        "spec-compliance-reviewer.md",
        "standards-reviewer.md",
    }
)
MANAGED_PROFILE_SKILL_ROOTS = {
    "production": frozenset(
        {
            "bp-architecture-design",
            "bp-coding-best-practices",
            "bp-component-design",
            "bp-distributed-systems",
            "bp-performance-optimization",
            "bp-skill-authoring",
            "opsx-archive",
            "opsx-code-generation",
            "opsx-quick-design",
            "opsx-requirements-clarification",
            "opsx-system-design",
            "opsx-test-generation",
            "project-init",
            "project-knowledge",
            "self-refinement",
            "std-cpp",
            "std-go",
            "std-python",
            "troubleshooting",
            "workflow-code-review",
            "workflow-verification",
        }
    ),
    "tooling": frozenset(
        {
            "bp-architecture-design",
            "bp-coding-best-practices",
            "bp-component-design",
            "bp-distributed-systems",
            "bp-performance-optimization",
            "bp-skill-authoring",
            "project-init",
            "project-knowledge",
            "self-refinement",
            "std-cpp",
            "std-go",
            "std-python",
            "troubleshooting",
            "workflow-code-generation",
            "workflow-code-review",
            "workflow-quick-design",
            "workflow-requirements-clarification",
            "workflow-system-design",
            "workflow-test-generation",
            "workflow-verification",
        }
    ),
}
MANAGED_PROFILE_COMMAND_FILES = {
    "production": frozenset(
        {
            "code-review.md",
            "opsx-archive.md",
            "opsx-code-generation.md",
            "opsx-quick-design.md",
            "opsx-requirements-clarification.md",
            "opsx-system-design.md",
            "opsx-test-generation.md",
            "performance-optimization.md",
            "project-init.md",
            "reflect.md",
            "skill-authoring.md",
            "troubleshooting.md",
        }
    ),
    "tooling": frozenset(
        {
            "code-generation.md",
            "code-review.md",
            "performance-optimization.md",
            "project-init.md",
            "quick-design.md",
            "reflect.md",
            "requirements-clarification.md",
            "skill-authoring.md",
            "system-design.md",
            "test-generation.md",
            "troubleshooting.md",
            "verification.md",
            "verify-config.md",
        }
    ),
}
MANAGED_PACK_SKILL_ROOTS = {
    "frontend": frozenset(
        {
            "bp-frontend-layout",
            "bp-frontend-taste",
            "frontend-playwright-verification",
            "std-react",
            "workflow-frontend-design",
        }
    ),
    "project-init": frozenset({"project-init"}),
    "open-code-review": frozenset({"open-code-review"}),
    "telemetry": frozenset(),
}
MANAGED_PACK_COMMAND_FILES = {
    "frontend": frozenset({"frontend-design.md"}),
    "project-init": frozenset({"project-init.md"}),
    "open-code-review": frozenset(),
    "telemetry": frozenset(),
}


@dataclass(frozen=True)
class LinkOperation:
    """One source asset linked to a target-relative path."""

    source: Path
    relative_target: Path
    kind: str


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Install one Agentic Engineering Framework profile."
    )
    parser.add_argument("target_dir", type=Path, nargs="?")
    parser.add_argument("--profile", choices=("production", "tooling"))
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument(
        "--with",
        dest="packs",
        action="append",
        default=[],
        choices=tuple(PACK_SKILLS),
        help="Install an optional pack. Repeat for multiple packs.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--switch-profile", action="store_true")
    parser.add_argument("--refresh-all", action="store_true")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    return parser.parse_args(argv)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        raise FileNotFoundError(f"Missing source directory: {root}")
    for path in sorted(
        candidate for candidate in root.rglob("*") if candidate.is_file()
    ):
        relative = path.relative_to(root)
        if IGNORED_PARTS & set(relative.parts):
            continue
        if path.suffix.casefold() in IGNORED_SUFFIXES:
            continue
        yield path


def _selected_names(profile: str, packs: set[str]) -> tuple[set[str], set[str]]:
    invalid = packs & TOOLING_ONLY_PACKS if profile == "production" else set()
    if invalid:
        names = ", ".join(sorted(invalid))
        raise ValueError(f"Packs only available for tooling: {names}")

    skills = set(CORE_SKILLS)
    commands = set(CORE_COMMANDS)
    if profile == "production":
        skills.update(PRODUCTION_SKILLS)
        commands.update(PRODUCTION_COMMANDS)
    else:
        skills.update(TOOLING_SKILLS)
        commands.update(TOOLING_COMMANDS)
    for pack in packs:
        skills.update(PACK_SKILLS[pack])
        commands.update(PACK_COMMANDS[pack])
    return skills, commands


def build_operations(
    source: Path, profile: str, packs: set[str]
) -> list[LinkOperation]:
    """Return the explicit installation link list."""
    skills, commands = _selected_names(profile, packs)
    operations: list[LinkOperation] = []
    for client in CLIENT_DIRS:
        for skill in sorted(skills):
            skill_root = source / "skills" / skill
            if not skill_root.is_dir():
                raise FileNotFoundError(f"Missing source directory: {skill_root}")
            operations.append(
                LinkOperation(skill_root, Path(client, "skills", skill), "directory")
            )
        for name in sorted(ACTIVE_AGENT_FILES):
            path = source / "agents" / name
            if not path.is_file():
                raise FileNotFoundError(f"Missing source file: {path}")
            operations.append(
                LinkOperation(path, Path(client, "agents", path.name), "file")
            )
        for command in sorted(commands):
            path = source / "commands" / command
            if not path.is_file():
                raise FileNotFoundError(f"Missing source file: {path}")
            operations.append(
                LinkOperation(path, Path(client, "commands", command), "file")
            )
        if profile == "production":
            validator = source / "scripts" / "validate_change.py"
            if not validator.is_file():
                raise FileNotFoundError(f"Missing source file: {validator}")
            operations.append(
                LinkOperation(
                    validator,
                    Path(client, "scripts", "validate_change.py"),
                    "file",
                )
            )

    if "telemetry" in packs:
        path = source / "scripts" / "analyze_session_metrics.py"
        if not path.is_file():
            raise FileNotFoundError(f"Missing source file: {path}")
        operations.append(
            LinkOperation(
                path,
                Path(".agentic-framework", "packs", "telemetry", path.name),
                "file",
            )
        )
    return operations


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction and is_junction():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _safe_target(
    target: Path, relative: str | Path, *, allow_leaf_link: bool = False
) -> Path:
    root = target.absolute()
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Managed path escapes target: {relative}")
    current = root
    if _is_link_or_junction(current):
        raise ValueError(f"Installation target is a link or junction: {current}")
    for index, part in enumerate(relative_path.parts):
        current /= part
        is_leaf = index == len(relative_path.parts) - 1
        if (
            os.path.lexists(current)
            and _is_link_or_junction(current)
            and not (allow_leaf_link and is_leaf)
        ):
            raise ValueError(f"Managed path crosses a link or junction: {current}")
    return current


def _manifest_allowed_path(path_text: str, profile: str, packs: set[str]) -> bool:
    path = PurePosixPath(path_text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    if path.parts[:3] == (".agentic-framework", "packs", "telemetry"):
        return "telemetry" in packs and path.name == "analyze_session_metrics.py"
    if len(path.parts) < 3 or path.parts[0] not in CLIENT_DIRS:
        return False
    skills = set(MANAGED_PROFILE_SKILL_ROOTS[profile])
    commands = set(MANAGED_PROFILE_COMMAND_FILES[profile])
    for pack in packs:
        skills.update(MANAGED_PACK_SKILL_ROOTS[pack])
        commands.update(MANAGED_PACK_COMMAND_FILES[pack])
    area = path.parts[1]
    if area == "skills":
        return len(path.parts) >= 3 and path.parts[2] in skills
    if area == "agents":
        return len(path.parts) == 3 and path.parts[2] in MANAGED_AGENT_FILES
    if area == "commands":
        return len(path.parts) == 3 and path.parts[2] in commands
    if area == "scripts":
        return (
            profile == "production"
            and len(path.parts) == 3
            and path.parts[2] == "validate_change.py"
        )
    return False


def _load_manifest(target: Path) -> dict | None:
    """Load and validate a v1 copied-file or v2 linked-asset manifest."""
    path = _safe_target(target, MANIFEST_PATH)
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    schema = manifest.get("schema_version")
    if schema not in {1, MANIFEST_SCHEMA_VERSION}:
        raise ValueError("Unsupported manifest schema_version")
    if not isinstance(manifest.get("framework_version"), str):
        raise ValueError("Manifest is missing framework_version")
    profile = manifest.get("profile")
    if profile not in {"production", "tooling"}:
        raise ValueError("Manifest has an invalid profile")
    packs = manifest.get("packs")
    if not isinstance(packs, list) or any(
        pack not in MANAGED_PACK_SKILL_ROOTS for pack in packs
    ):
        raise ValueError("Manifest has invalid packs")

    entries_key = "files" if schema == 1 else "links"
    entries = manifest.get(entries_key)
    if not isinstance(entries, list):
        raise ValueError(f"Manifest {entries_key} must be a list")
    if schema == MANIFEST_SCHEMA_VERSION:
        source = manifest.get("source")
        if not isinstance(source, str) or not Path(source).is_absolute():
            raise ValueError("Manifest has an invalid source")

    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Manifest entry must be an object")
        relative = item.get("path")
        if (
            not isinstance(relative, str)
            or not _manifest_allowed_path(relative, profile, set(packs))
            or relative in seen
        ):
            raise ValueError(f"Manifest contains an unmanaged path: {relative}")
        if schema == 1:
            digest = item.get("sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"Manifest contains an invalid hash: {relative}")
        else:
            link_source = item.get("source")
            kind = item.get("type")
            if not isinstance(link_source, str) or not Path(link_source).is_absolute():
                raise ValueError(f"Manifest contains an invalid source: {relative}")
            if kind not in {"file", "directory"}:
                raise ValueError(f"Manifest contains an invalid link type: {relative}")
        _safe_target(target, relative, allow_leaf_link=schema == 2)
        seen.add(relative)
    return manifest


def _manifest_entries(manifest: dict | None) -> list[dict]:
    if not manifest:
        return []
    return manifest["files" if manifest["schema_version"] == 1 else "links"]


def _managed_paths(manifest: dict | None) -> set[str]:
    return {item["path"] for item in _manifest_entries(manifest)}


def _forbidden_entry_paths(profile: str) -> set[Path]:
    skills = TOOLING_SKILLS if profile == "production" else PRODUCTION_SKILLS
    commands = TOOLING_COMMANDS if profile == "production" else PRODUCTION_COMMANDS
    paths: set[Path] = set()
    for client in CLIENT_DIRS:
        paths.update(Path(client, "skills", skill) for skill in skills)
        paths.update(Path(client, "commands", command) for command in commands)
    return paths


def _cross_pollution_errors(
    target: Path, profile: str, removable_paths: set[str]
) -> list[str]:
    errors: list[str] = []
    for relative in _forbidden_entry_paths(profile):
        path = _safe_target(target, relative, allow_leaf_link=True)
        if not os.path.lexists(path):
            continue
        if relative.as_posix() not in removable_paths:
            errors.append(str(relative))
    return errors


def _normalized_link_path(path: str | Path) -> str:
    """Return a comparable absolute path, including Windows extended paths."""
    text = os.path.abspath(os.fspath(path))
    if os.name == "nt":
        text = text.replace("/", "\\")
        if text.casefold().startswith("\\\\?\\unc\\"):
            text = "\\\\" + text[8:]
        elif text.startswith("\\\\?\\"):
            text = text[4:]
    return os.path.normcase(os.path.normpath(text))


def _link_destination(path: Path) -> str:
    return _normalized_link_path(path.parent / os.readlink(path))


def _expected_link(path: Path, source: Path) -> bool:
    return path.is_symlink() and _link_destination(path) == _normalized_link_path(
        source
    )


def _verify_v2_links(target: Path, manifest: dict) -> None:
    for item in manifest["links"]:
        path = _safe_target(target, item["path"], allow_leaf_link=True)
        if not os.path.lexists(path):
            continue
        if not _expected_link(path, Path(item["source"])):
            raise FileExistsError(f"Managed link was changed or replaced: {path}")


def _preflight(
    target: Path,
    operations: list[LinkOperation],
    old_manifest: dict | None,
    force: bool,
) -> None:
    old_entries = {item["path"]: item for item in _manifest_entries(old_manifest)}
    if old_manifest and old_manifest["schema_version"] == 2:
        _verify_v2_links(target, old_manifest)
    for operation in operations:
        relative = operation.relative_target.as_posix()
        path = _safe_target(target, relative, allow_leaf_link=True)
        if not os.path.lexists(path):
            continue
        old = old_entries.get(relative)
        if (
            old is None
            and old_manifest
            and old_manifest["schema_version"] == 1
            and operation.kind == "directory"
            and path.is_dir()
        ):
            prefix = relative + "/"
            managed_children = {name for name in old_entries if name.startswith(prefix)}
            actual_children = {
                child.relative_to(target).as_posix() for child in _tree_files(path)
            }
            if managed_children and actual_children == managed_children:
                continue
        if old is None:
            raise FileExistsError(f"Refusing to replace unmanaged target: {path}")
        if old_manifest and old_manifest["schema_version"] == 1:
            if path.is_dir():
                raise IsADirectoryError(f"Managed file became a directory: {path}")
            if not force and _hash(path) != old["sha256"]:
                raise FileExistsError(
                    f"Refusing to overwrite changed target file: {path}"
                )


def _verify_removable(target: Path, manifest: dict, force: bool) -> None:
    if manifest["schema_version"] == 2:
        _verify_v2_links(target, manifest)
        return
    for item in manifest["files"]:
        path = _safe_target(target, item["path"])
        if not path.exists():
            continue
        if path.is_dir():
            raise IsADirectoryError(f"Managed file became a directory: {path}")
        if not force and _hash(path) != item["sha256"]:
            raise FileExistsError(f"Refusing to remove modified managed file: {path}")


def _prune_empty_parents(path: Path, target: Path) -> None:
    parent = path.parent
    root = target.absolute()
    while parent != root:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _remove_managed(target: Path, manifest: dict, dry_run: bool) -> None:
    allow_link = manifest["schema_version"] == 2
    for item in _manifest_entries(manifest):
        path = _safe_target(target, item["path"], allow_leaf_link=allow_link)
        if not os.path.lexists(path):
            continue
        if dry_run:
            print(f"[dry-run] remove {path}")
        else:
            path.unlink()
            _prune_empty_parents(path, target)


def _snapshot_entries(
    target: Path,
    relatives: set[str],
    backup: Path,
    link_type_hints: dict[str, str] | None = None,
) -> dict[str, tuple[str, str | None]]:
    link_type_hints = link_type_hints or {}
    snapshot: dict[str, tuple[str, str | None]] = {}
    for relative in sorted(relatives, key=lambda item: len(PurePosixPath(item).parts)):
        path = _safe_target(target, relative, allow_leaf_link=True)
        if not os.path.lexists(path):
            continue
        if path.is_symlink():
            link_type = link_type_hints.get(relative)
            if link_type is None:
                link_type = "directory" if path.is_dir() else "file"
            kind = f"{link_type}_link"
            snapshot[relative] = (kind, os.readlink(path))
        elif path.is_file():
            destination = backup / PurePosixPath(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            snapshot[relative] = ("file", None)
        elif not path.is_dir():
            raise IsADirectoryError(f"Cannot snapshot managed entry: {path}")
    return snapshot


def _restore_snapshot(
    target: Path,
    relatives: set[str],
    backup: Path,
    snapshot: dict[str, tuple[str, str | None]],
) -> None:
    for relative in sorted(relatives, key=lambda item: len(PurePosixPath(item).parts)):
        path = _safe_target(target, relative, allow_leaf_link=True)
        if os.path.lexists(path):
            if path.is_symlink() or path.is_file():
                path.unlink()
                _prune_empty_parents(path, target)
    for relative in sorted(snapshot, key=lambda item: len(PurePosixPath(item).parts)):
        kind, link_target = snapshot[relative]
        destination = _safe_target(target, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if kind.endswith("_link"):
            assert link_target is not None
            destination.symlink_to(
                link_target,
                target_is_directory=kind == "directory_link",
            )
        else:
            shutil.copy2(backup / PurePosixPath(relative), destination)


def _manifest_link_type_hints(manifest: dict | None) -> dict[str, str]:
    if not manifest or manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        return {}
    return {item["path"]: item["type"] for item in manifest["links"]}


def _create_link(operation: LinkOperation, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.symlink_to(
            operation.source.absolute(),
            target_is_directory=operation.kind == "directory",
        )
    except OSError as error:
        detail = str(error)
        if os.name == "nt" and getattr(error, "winerror", None) == 1314:
            detail = "enable Developer Mode or run with symbolic-link privilege"
        raise OSError(
            f"Unable to create symbolic link {destination}: {detail}. "
            "No files were copied."
        ) from error


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}-", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _write_manifest(target: Path, manifest: dict) -> None:
    _write_json(_safe_target(target, MANIFEST_PATH), manifest)


def _load_registry(registry_path: Path) -> dict:
    if not registry_path.exists():
        return {"schema_version": REGISTRY_SCHEMA_VERSION, "installations": []}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        raise ValueError("Unsupported registry schema_version")
    entries = registry.get("installations")
    if not isinstance(entries, list):
        raise ValueError("Registry installations must be a list")
    seen_targets: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Registry entry must be an object")
        source = entry.get("source")
        target = entry.get("target")
        profile = entry.get("profile")
        packs = entry.get("packs")
        if not all(isinstance(value, str) for value in (source, target)):
            raise ValueError("Registry entry has an invalid path")
        if not Path(source).is_absolute() or not Path(target).is_absolute():
            raise ValueError("Registry paths must be absolute")
        if profile not in {"production", "tooling"}:
            raise ValueError("Registry entry has an invalid profile")
        if not isinstance(packs, list) or any(
            pack not in MANAGED_PACK_SKILL_ROOTS for pack in packs
        ):
            raise ValueError("Registry entry has invalid packs")
        target_key = os.path.normcase(os.path.abspath(target))
        if target_key in seen_targets:
            raise ValueError("Registry contains duplicate installation")
        seen_targets.add(target_key)
    return registry


def _update_registry(
    registry_path: Path,
    source: Path,
    target: Path,
    profile: str | None,
    packs: set[str] | None,
) -> None:
    registry = _load_registry(registry_path)
    source_text = str(source.resolve())
    target_text = str(target.absolute())
    target_key = os.path.normcase(os.path.abspath(target_text))
    entries = [
        item
        for item in registry["installations"]
        if os.path.normcase(os.path.abspath(item["target"])) != target_key
    ]
    if profile is not None:
        entries.append(
            {
                "source": source_text,
                "target": target_text,
                "profile": profile,
                "packs": sorted(packs or set()),
            }
        )
    registry["installations"] = sorted(
        entries, key=lambda item: (item["source"], item["target"])
    )
    _write_json(registry_path, registry)


def install(
    source: Path,
    target: Path,
    profile: str,
    packs: set[str],
    force: bool = False,
    dry_run: bool = False,
    switch_profile: bool = False,
    registry_path: Path | None = None,
) -> None:
    """Install a profile using managed symbolic links and record it."""
    source = source.resolve()
    target = target.absolute()
    registry_path = (registry_path or DEFAULT_REGISTRY_PATH).absolute()
    operations = build_operations(source, profile, packs)
    old_manifest = _load_manifest(target)
    if old_manifest and old_manifest["profile"] != profile and not switch_profile:
        raise ValueError(
            "A different profile is installed; use --switch-profile explicitly"
        )
    old_paths = _managed_paths(old_manifest)
    pollution = _cross_pollution_errors(target, profile, old_paths)
    if pollution:
        raise FileExistsError(
            "Opposite-profile entries are not managed by this installer: "
            + ", ".join(pollution)
        )
    _preflight(target, operations, old_manifest, force)
    if old_manifest:
        _verify_removable(target, old_manifest, force)

    links = [
        {
            "path": operation.relative_target.as_posix(),
            "source": str(operation.source.absolute()),
            "type": operation.kind,
        }
        for operation in operations
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "framework_version": FRAMEWORK_VERSION,
        "source": str(source),
        "profile": profile,
        "packs": sorted(packs),
        "links": links,
    }
    if dry_run:
        if old_manifest:
            _remove_managed(target, old_manifest, True)
        for operation in operations:
            print(
                f"[dry-run] link {operation.source} -> "
                f"{_safe_target(target, operation.relative_target, allow_leaf_link=True)}"
            )
        print(f"[dry-run] write manifest {_safe_target(target, MANIFEST_PATH)}")
        return

    relative_paths = old_paths | {item["path"] for item in links}
    relative_paths.add(MANIFEST_PATH.as_posix())
    with tempfile.TemporaryDirectory() as temporary_directory:
        backup = Path(temporary_directory)
        snapshot = _snapshot_entries(
            target,
            relative_paths,
            backup,
            _manifest_link_type_hints(old_manifest),
        )
        try:
            if old_manifest:
                _remove_managed(target, old_manifest, False)
            for operation in operations:
                _create_link(
                    operation,
                    _safe_target(
                        target, operation.relative_target, allow_leaf_link=True
                    ),
                )
            post_pollution = _cross_pollution_errors(target, profile, set())
            if post_pollution:
                raise FileExistsError(
                    "Profile installation is contaminated: " + ", ".join(post_pollution)
                )
            _write_manifest(target, manifest)
            _update_registry(registry_path, source, target, profile, packs)
        except BaseException:
            _restore_snapshot(target, relative_paths, backup, snapshot)
            raise


def uninstall(
    source: Path,
    target: Path,
    force: bool = False,
    dry_run: bool = False,
    registry_path: Path | None = None,
) -> None:
    """Remove only entries owned by the validated installation manifest."""
    source = source.resolve()
    target = target.absolute()
    registry_path = (registry_path or DEFAULT_REGISTRY_PATH).absolute()
    manifest = _load_manifest(target)
    if manifest is None:
        raise FileNotFoundError(
            f"No installation manifest: {_safe_target(target, MANIFEST_PATH)}"
        )
    _verify_removable(target, manifest, force)
    registered_source = (
        Path(manifest["source"])
        if manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
        else source
    )
    if dry_run:
        _remove_managed(target, manifest, True)
        print(f"[dry-run] remove {_safe_target(target, MANIFEST_PATH)}")
        return
    relative_paths = _managed_paths(manifest) | {MANIFEST_PATH.as_posix()}
    with tempfile.TemporaryDirectory() as temporary_directory:
        backup = Path(temporary_directory)
        snapshot = _snapshot_entries(
            target,
            relative_paths,
            backup,
            _manifest_link_type_hints(manifest),
        )
        try:
            _remove_managed(target, manifest, False)
            manifest_path = _safe_target(target, MANIFEST_PATH)
            manifest_path.unlink()
            _prune_empty_parents(manifest_path, target)
            _update_registry(registry_path, registered_source, target, None, None)
        except BaseException:
            _restore_snapshot(target, relative_paths, backup, snapshot)
            raise


def refresh_all(
    source: Path,
    force: bool = False,
    dry_run: bool = False,
    registry_path: Path | None = None,
) -> None:
    """Refresh all registered targets for this source after manifest confirmation."""
    source = source.resolve()
    registry_path = (registry_path or DEFAULT_REGISTRY_PATH).absolute()
    registry = _load_registry(registry_path)
    source_key = os.path.normcase(os.path.abspath(str(source)))
    entries = [
        item
        for item in registry["installations"]
        if os.path.normcase(os.path.abspath(item["source"])) == source_key
    ]
    failures: list[str] = []
    for entry in entries:
        target = Path(entry["target"])
        try:
            manifest = _load_manifest(target)
            if (
                manifest is None
                or os.path.normcase(os.path.abspath(manifest.get("source", "")))
                != source_key
            ):
                raise ValueError(
                    "target manifest does not confirm the registered source"
                )
            if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
                raise ValueError(
                    "legacy manifest requires an explicit single-target upgrade"
                )
            if manifest["profile"] != entry["profile"] or sorted(
                manifest["packs"]
            ) != sorted(entry["packs"]):
                raise ValueError(
                    "target manifest does not confirm the registered selection"
                )
            install(
                source,
                target,
                entry["profile"],
                set(entry["packs"]),
                force=force,
                dry_run=dry_run,
                switch_profile=False,
                registry_path=registry_path,
            )
            print(f"refreshed: {target}")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            failures.append(f"{target}: {error}")
    if failures:
        raise RuntimeError("Refresh failed:\n" + "\n".join(failures))


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    if args.refresh_all:
        if (
            args.target_dir
            or args.profile
            or args.packs
            or args.uninstall
            or args.switch_profile
        ):
            raise ValueError(
                "--refresh-all cannot be combined with target_dir, --profile, "
                "--with, --uninstall, or --switch-profile"
            )
        refresh_all(
            args.source,
            force=args.force,
            dry_run=args.dry_run,
            registry_path=args.registry,
        )
        return 0
    if args.target_dir is None:
        raise ValueError("target_dir is required unless --refresh-all is used")
    if args.uninstall:
        if args.profile or args.packs or args.switch_profile:
            raise ValueError(
                "--uninstall cannot be combined with --profile, --with, "
                "or --switch-profile"
            )
        uninstall(
            args.source,
            args.target_dir,
            force=args.force,
            dry_run=args.dry_run,
            registry_path=args.registry,
        )
        return 0
    if not args.profile:
        raise ValueError("--profile is required unless --uninstall is used")
    install(
        args.source,
        args.target_dir,
        args.profile,
        set(args.packs),
        force=args.force,
        dry_run=args.dry_run,
        switch_profile=args.switch_profile,
        registry_path=args.registry,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
