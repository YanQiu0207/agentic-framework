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
FRAMEWORK_VERSION = "2026.07.19"
MANIFEST_SCHEMA_VERSION = 1

CORE_SKILLS = {
    "bp-architecture-design",
    "bp-coding-best-practices",
    "bp-component-design",
    "bp-distributed-systems",
    "bp-performance-optimization",
    "bp-skill-authoring",
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
TOOLING_ONLY_PACKS = {"frontend", "project-init"}
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
MANAGED_AGENT_FILES = {
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
class CopyOperation:
    """One source file copied to a target-relative path."""

    source: Path
    relative_target: Path


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Install one Agentic Engineering Framework profile."
    )
    parser.add_argument("target_dir", type=Path)
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
) -> list[CopyOperation]:
    """Return the explicit installation file list."""
    skills, commands = _selected_names(profile, packs)
    operations: list[CopyOperation] = []
    for client in CLIENT_DIRS:
        for skill in sorted(skills):
            skill_root = source / "skills" / skill
            for path in _tree_files(skill_root):
                relative = path.relative_to(skill_root)
                operations.append(
                    CopyOperation(path, Path(client, "skills", skill) / relative)
                )
        for path in _tree_files(source / "agents"):
            operations.append(CopyOperation(path, Path(client, "agents", path.name)))
        for command in sorted(commands):
            path = source / "commands" / command
            if not path.is_file():
                raise FileNotFoundError(f"Missing source file: {path}")
            operations.append(CopyOperation(path, Path(client, "commands", command)))
        if profile == "production":
            validator = source / "scripts" / "validate_change.py"
            operations.append(
                CopyOperation(validator, Path(client, "scripts", "validate_change.py"))
            )

    if "telemetry" in packs:
        path = source / "scripts" / "analyze_session_metrics.py"
        operations.append(
            CopyOperation(
                path,
                Path(".agentic-framework", "packs", "telemetry", path.name),
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


def _safe_target(target: Path, relative: str | Path) -> Path:
    root = target.absolute()
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Managed path escapes target: {relative}")
    current = root
    if _is_link_or_junction(current):
        raise ValueError(f"Installation target is a link or junction: {current}")
    for part in relative_path.parts:
        current /= part
        if os.path.lexists(current) and _is_link_or_junction(current):
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
        return len(path.parts) >= 4 and path.parts[2] in skills
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
    path = _safe_target(target, MANIFEST_PATH)
    if not path.is_file():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
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
    files = manifest.get("files")
    if not isinstance(files, list):
        raise ValueError("Manifest files must be a list")

    seen: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Manifest file entry must be an object")
        relative = item.get("path")
        digest = item.get("sha256")
        if (
            not isinstance(relative, str)
            or not _manifest_allowed_path(relative, profile, set(packs))
            or relative in seen
        ):
            raise ValueError(f"Manifest contains an unmanaged path: {relative}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Manifest contains an invalid hash: {relative}")
        _safe_target(target, relative)
        seen.add(relative)
    return manifest


def _managed_paths(manifest: dict | None) -> set[str]:
    return {item["path"] for item in (manifest or {}).get("files", [])}


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
        path = _safe_target(target, relative)
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else list(_tree_files(path))
        unmanaged = [
            candidate
            for candidate in candidates
            if candidate.relative_to(target).as_posix() not in removable_paths
        ]
        if unmanaged:
            errors.append(str(relative))
    return errors


def _preflight(
    target: Path,
    operations: list[CopyOperation],
    old_manifest: dict | None,
    force: bool,
) -> None:
    old_paths = {
        item["path"]: item["sha256"] for item in (old_manifest or {}).get("files", [])
    }
    for operation in operations:
        relative = operation.relative_target.as_posix()
        path = _safe_target(target, relative)
        if not path.exists():
            continue
        if path.is_dir():
            raise IsADirectoryError(f"Target file is a directory: {path}")
        expected_old = old_paths.get(relative)
        is_unchanged_managed = expected_old is not None and _hash(path) == expected_old
        if (
            not force
            and not is_unchanged_managed
            and _hash(path) != _hash(operation.source)
        ):
            raise FileExistsError(f"Refusing to overwrite changed target file: {path}")


def _verify_removable(target: Path, manifest: dict, force: bool) -> None:
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
    for item in manifest["files"]:
        path = _safe_target(target, item["path"])
        if not path.exists():
            continue
        if dry_run:
            print(f"[dry-run] remove {path}")
        else:
            path.unlink()
            _prune_empty_parents(path, target)


def _snapshot_files(target: Path, relatives: set[str], backup: Path) -> set[str]:
    existing: set[str] = set()
    for relative in relatives:
        path = _safe_target(target, relative)
        if not path.is_file():
            continue
        destination = backup / PurePosixPath(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        existing.add(relative)
    return existing


def _restore_snapshot(
    target: Path, relatives: set[str], backup: Path, existing: set[str]
) -> None:
    for relative in relatives:
        path = _safe_target(target, relative)
        if path.is_file():
            path.unlink()
            _prune_empty_parents(path, target)
    for relative in existing:
        source = backup / PurePosixPath(relative)
        destination = _safe_target(target, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _copy_operation(operation: CopyOperation, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(operation.source, destination)


def _write_manifest(target: Path, manifest: dict) -> None:
    path = _safe_target(target, MANIFEST_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=".manifest-", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def install(
    source: Path,
    target: Path,
    profile: str,
    packs: set[str],
    force: bool = False,
    dry_run: bool = False,
    switch_profile: bool = False,
) -> None:
    """Install a profile, writing a validated managed-file manifest."""
    source = source.resolve()
    target = target.absolute()
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

    files = [
        {
            "path": operation.relative_target.as_posix(),
            "sha256": _hash(operation.source),
        }
        for operation in operations
    ]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "framework_version": FRAMEWORK_VERSION,
        "profile": profile,
        "packs": sorted(packs),
        "files": files,
    }
    if dry_run:
        if old_manifest:
            _remove_managed(target, old_manifest, True)
        for operation in operations:
            print(
                f"[dry-run] copy {operation.source} -> "
                f"{_safe_target(target, operation.relative_target)}"
            )
        print(f"[dry-run] write manifest {_safe_target(target, MANIFEST_PATH)}")
        return

    relative_paths = old_paths | {item["path"] for item in files}
    relative_paths.add(MANIFEST_PATH.as_posix())
    with tempfile.TemporaryDirectory() as temporary_directory:
        backup = Path(temporary_directory)
        existing = _snapshot_files(target, relative_paths, backup)
        try:
            if old_manifest:
                _remove_managed(target, old_manifest, False)
            for operation in operations:
                _copy_operation(
                    operation, _safe_target(target, operation.relative_target)
                )
            post_pollution = _cross_pollution_errors(target, profile, set())
            if post_pollution:
                raise FileExistsError(
                    "Profile installation is contaminated: " + ", ".join(post_pollution)
                )
            _write_manifest(target, manifest)
        except BaseException:
            _restore_snapshot(target, relative_paths, backup, existing)
            raise


def uninstall(
    source: Path,
    target: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Remove only files owned by the validated installation manifest."""
    del source  # Uninstall is intentionally independent of the current source tree.
    target = target.absolute()
    manifest = _load_manifest(target)
    if manifest is None:
        raise FileNotFoundError(
            f"No installation manifest: {_safe_target(target, MANIFEST_PATH)}"
        )
    _verify_removable(target, manifest, force)
    if dry_run:
        _remove_managed(target, manifest, True)
        print(f"[dry-run] remove {_safe_target(target, MANIFEST_PATH)}")
        return
    relative_paths = _managed_paths(manifest) | {MANIFEST_PATH.as_posix()}
    with tempfile.TemporaryDirectory() as temporary_directory:
        backup = Path(temporary_directory)
        existing = _snapshot_files(target, relative_paths, backup)
        try:
            _remove_managed(target, manifest, False)
            manifest_path = _safe_target(target, MANIFEST_PATH)
            manifest_path.unlink()
            _prune_empty_parents(manifest_path, target)
        except BaseException:
            _restore_snapshot(target, relative_paths, backup, existing)
            raise


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
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
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
