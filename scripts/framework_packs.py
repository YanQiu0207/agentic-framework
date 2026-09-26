"""Read optional framework capabilities without executing project code."""

from __future__ import annotations

import os
from pathlib import Path

PACK_SELECTION_VERSION = 1
LEGACY_PACKS = frozenset({"runtime", "knowledge-advanced"})
KNOWN_PACKS = frozenset(
    {
        "runtime",
        "knowledge-advanced",
        "frontend",
        "open-code-review",
        "project-init",
        "telemetry",
    }
)
MANIFEST_PATH = Path(".agentic-framework/manifest.json")


class FrameworkPackError(ValueError):
    """An installation is invalid or a required capability is unavailable."""


def manifest_packs(manifest: dict) -> set[str]:
    """Validate selection metadata and preserve legacy default capabilities."""
    version = manifest.get("pack_selection_version")
    if "pack_selection_version" in manifest and (
        type(version) is not int or version != PACK_SELECTION_VERSION
    ):
        raise FrameworkPackError("Unsupported pack_selection_version")
    packs = manifest.get("packs")
    if (
        not isinstance(packs, list)
        or any(
            not isinstance(pack, str) or pack not in KNOWN_PACKS
            for pack in packs
        )
        or len(packs) != len(set(packs))
    ):
        raise FrameworkPackError("Invalid framework pack selection")
    return set(packs) | (LEGACY_PACKS if version is None else set())


def pack_status(repo: Path) -> dict:
    """Return enabled capabilities and the validated selection source."""
    # Import only our own installer, never a module named by manifest.source.
    import install_agentic_framework as installer

    start = repo.resolve()
    if not start.is_dir():
        raise FrameworkPackError(
            "Pack lookup requires an existing project directory"
        )
    for root in (start, *start.parents):
        path = root / MANIFEST_PATH
        if not os.path.lexists(path):
            continue
        try:
            manifest = installer._load_manifest(root)
            if manifest is None:
                raise FrameworkPackError(
                    "Framework manifest is not a regular file"
                )
            packs = manifest_packs(manifest)
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise FrameworkPackError(
                "Invalid framework installation manifest"
            ) from error
        return {
            "enabled": sorted(packs),
            "source": (
                "manifest"
                if "pack_selection_version" in manifest
                else "legacy-manifest"
            ),
            "path": str(path),
        }

    # Only this executing framework checkout qualifies; similarly named files
    # in an arbitrary project are not proof that it is framework source.
    source = Path(__file__).resolve().parents[1]
    markers = (
        "scripts/install_agentic_framework.py",
        "skills/workflow-code-generation/SKILL.md",
        "harness/capabilities/codex.json",
    )
    if (start == source or source in start.parents) and all(
        (source / marker).is_file() for marker in markers
    ):
        return {
            "enabled": sorted(KNOWN_PACKS),
            "source": "framework-source",
            "path": str(source),
        }
    raise FrameworkPackError(
        "No framework installation manifest; install the project with --with <pack>"
    )


def enabled_packs(repo: Path) -> set[str]:
    """Return optional capabilities enabled for a project or source checkout."""
    return set(pack_status(repo)["enabled"])


def require_pack(repo: Path, pack: str) -> None:
    """Raise FrameworkPackError unless the named capability is enabled."""
    if pack not in KNOWN_PACKS:
        raise FrameworkPackError("Unknown framework capability")
    if pack not in enabled_packs(repo):
        raise FrameworkPackError(
            f"Framework capability {pack} is disabled; enable it with --with {pack}"
        )
