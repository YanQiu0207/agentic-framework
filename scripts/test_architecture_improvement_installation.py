"""Verify architecture-improvement installation and managed-link safety."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import install_agentic_framework as installer

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = "workflow-architecture-improvement"
COMMAND = "architecture-improvement.md"


class ArchitectureImprovementInstallationTest(unittest.TestCase):
    """Cover shared selection, refresh, uninstall, and user-owned files."""

    def test_both_profiles_and_clients_select_managed_entry_points(
        self,
    ) -> None:
        for profile in ("production", "tooling"):
            with self.subTest(profile=profile):
                operations = {
                    item.relative_target.as_posix(): item
                    for item in installer.build_operations(
                        REPO_ROOT, profile, set()
                    )
                }
                for client in installer.CLIENT_DIRS:
                    for area, name, kind in (
                        ("skills", SKILL, "directory"),
                        ("commands", COMMAND, "file"),
                    ):
                        relative = f"{client}/{area}/{name}"
                        self.assertIn(relative, operations)
                        operation = operations[relative]
                        self.assertEqual(kind, operation.kind)
                        self.assertEqual(
                            REPO_ROOT / area / name, operation.source
                        )
                        self.assertTrue(
                            installer._manifest_allowed_path(
                                relative, profile, set()
                            )
                        )
                        self.assertFalse(
                            installer._manifest_allowed_path(
                                f"{client}/{area}/unmanaged-entry",
                                profile,
                                set(),
                            )
                        )

    def _require_symlinks(self, root: Path) -> None:
        source = root / "probe-source"
        source.write_text("probe", encoding="utf-8")
        link = root / "probe-link"
        try:
            link.symlink_to(source)
        except OSError:
            self.skipTest("symbolic-link creation is unavailable")
        self.assertTrue(link.is_symlink())

    def test_install_refresh_uninstall_preserve_user_files_and_source(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._require_symlinks(root)
            registry = root / "registry.json"
            targets = []
            for profile in ("production", "tooling"):
                target = root / profile
                target.mkdir()
                installer.install(
                    REPO_ROOT, target, profile, set(), registry_path=registry
                )
                targets.append(target)
                for client in installer.CLIENT_DIRS:
                    user_file = (
                        target / client / "commands" / "project-owned.md"
                    )
                    user_file.write_text("用户内容", encoding="utf-8")

            installer.refresh_all(REPO_ROOT, registry_path=registry)
            for target in targets:
                for client in installer.CLIENT_DIRS:
                    for area, name in (
                        ("skills", SKILL),
                        ("commands", COMMAND),
                    ):
                        link = target / client / area / name
                        self.assertTrue(link.is_symlink())
                        self.assertEqual(
                            (REPO_ROOT / area / name).resolve(), link.resolve()
                        )
                installer.uninstall(REPO_ROOT, target, registry_path=registry)
                for client in installer.CLIENT_DIRS:
                    self.assertFalse(
                        (target / client / "skills" / SKILL).is_symlink()
                    )
                    self.assertFalse(
                        (target / client / "commands" / COMMAND).is_symlink()
                    )
                    user_file = (
                        target / client / "commands" / "project-owned.md"
                    )
                    self.assertEqual(
                        "用户内容", user_file.read_text(encoding="utf-8")
                    )
            self.assertTrue(
                (REPO_ROOT / "skills" / SKILL / "SKILL.md").is_file()
            )
            self.assertTrue((REPO_ROOT / "commands" / COMMAND).is_file())
            self.assertEqual(
                [],
                json.loads(registry.read_text(encoding="utf-8"))[
                    "installations"
                ],
            )

    def test_existing_user_command_blocks_install_without_overwrite(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            user_file = target / ".codex" / "commands" / COMMAND
            user_file.parent.mkdir(parents=True)
            user_file.write_text("用户命令", encoding="utf-8")
            registry = root / "registry.json"
            with self.assertRaises(FileExistsError):
                installer.install(
                    REPO_ROOT, target, "tooling", set(), registry_path=registry
                )
            self.assertEqual("用户命令", user_file.read_text(encoding="utf-8"))
            self.assertFalse((target / installer.MANIFEST_PATH).exists())
            self.assertFalse(registry.exists())


if __name__ == "__main__":
    unittest.main()
