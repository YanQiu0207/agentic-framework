"""Tests for profile-isolated framework installation."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import install_agentic_framework as installer

REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    """Verify profile isolation, packs, and managed-file safety."""

    def test_production_contains_no_tooling_lifecycle_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            for client in installer.CLIENT_DIRS:
                self.assertTrue(
                    (target / client / "skills" / "opsx-code-generation").is_dir()
                )
                self.assertFalse(
                    (target / client / "skills" / "workflow-code-generation").exists()
                )
                self.assertFalse(
                    (target / client / "commands" / "code-generation.md").exists()
                )
                self.assertTrue(
                    (target / client / "scripts" / "validate_change.py").is_file()
                )
                self.assertTrue(
                    (target / client / "skills" / "workflow-verification").is_dir()
                )

    def test_tooling_contains_no_production_lifecycle_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "tooling", set())
            for client in installer.CLIENT_DIRS:
                self.assertTrue(
                    (target / client / "skills" / "workflow-code-generation").is_dir()
                )
                self.assertFalse(
                    (target / client / "skills" / "opsx-code-generation").exists()
                )
                self.assertFalse(
                    (target / client / "scripts" / "validate_change.py").exists()
                )

    def test_frontend_pack_is_explicit_and_tooling_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "tooling", {"frontend"})
            self.assertTrue(
                (target / ".codex" / "skills" / "workflow-frontend-design").is_dir()
            )
            with self.assertRaisesRegex(ValueError, "only available for tooling"):
                installer.build_operations(REPO_ROOT, "production", {"frontend"})

    def test_manifest_records_profile_packs_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "tooling", {"telemetry"})
            manifest = json.loads(
                (target / installer.MANIFEST_PATH).read_text(encoding="utf-8")
            )
            self.assertEqual("tooling", manifest["profile"])
            self.assertEqual(installer.FRAMEWORK_VERSION, manifest["framework_version"])
            self.assertEqual(["telemetry"], manifest["packs"])
            self.assertTrue(manifest["files"])
            self.assertTrue(
                all(len(item["sha256"]) == 64 for item in manifest["files"])
            )

    def test_profile_switch_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            with self.assertRaisesRegex(ValueError, "different profile"):
                installer.install(REPO_ROOT, target, "tooling", set())
            installer.install(REPO_ROOT, target, "tooling", set(), switch_profile=True)
            self.assertFalse(
                (target / ".codex" / "skills" / "opsx-code-generation").exists()
            )

    def test_modified_managed_file_blocks_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            managed = target / ".codex" / "commands" / "opsx-code-generation.md"
            managed.write_text("local edit", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "changed target file"):
                installer.install(REPO_ROOT, target, "production", set())

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set(), dry_run=True)
            self.assertEqual([], list(target.iterdir()))

    def test_build_operations_excludes_python_cache_files(self) -> None:
        operations = installer.build_operations(REPO_ROOT, "tooling", set())
        paths = [operation.source for operation in operations]
        self.assertFalse(any("__pycache__" in path.parts for path in paths))
        self.assertFalse(any(path.suffix == ".pyc" for path in paths))

    def test_forged_manifest_cannot_remove_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            project_file = target / "README.md"
            project_file.write_text("project", encoding="utf-8")
            manifest_path = target / installer.MANIFEST_PATH
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": installer.MANIFEST_SCHEMA_VERSION,
                        "framework_version": installer.FRAMEWORK_VERSION,
                        "profile": "production",
                        "packs": [],
                        "files": [
                            {
                                "path": "README.md",
                                "sha256": installer._hash(project_file),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "unmanaged path"):
                installer.install(REPO_ROOT, target, "production", set())
            self.assertEqual("project", project_file.read_text(encoding="utf-8"))

    def test_legacy_opposite_profile_entry_blocks_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            legacy = (
                target / ".codex" / "skills" / "workflow-code-generation" / "SKILL.md"
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("legacy", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "Opposite-profile"):
                installer.install(REPO_ROOT, target, "production", set())
            self.assertEqual("legacy", legacy.read_text(encoding="utf-8"))

    def test_copy_failure_restores_previous_installation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            manifest_path = target / installer.MANIFEST_PATH
            original_manifest = manifest_path.read_bytes()
            managed = target / ".codex" / "commands" / "opsx-code-generation.md"
            original_managed = managed.read_bytes()
            real_copy = installer._copy_operation
            calls = 0

            def fail_second_copy(operation, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated copy failure")
                real_copy(operation, destination)

            with mock.patch.object(
                installer, "_copy_operation", side_effect=fail_second_copy
            ):
                with self.assertRaisesRegex(OSError, "simulated copy failure"):
                    installer.install(REPO_ROOT, target, "production", set())

            self.assertEqual(original_manifest, manifest_path.read_bytes())
            self.assertEqual(original_managed, managed.read_bytes())

    def test_uninstall_removes_only_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "tooling", set())
            project_file = target / ".codex" / "commands" / "project-owned.md"
            project_file.write_text("keep", encoding="utf-8")
            installer.uninstall(REPO_ROOT, target)
            self.assertEqual("keep", project_file.read_text(encoding="utf-8"))
            self.assertFalse((target / installer.MANIFEST_PATH).exists())
            self.assertFalse(
                (target / ".codex" / "commands" / "code-generation.md").exists()
            )

    def test_install_rejects_managed_path_through_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            commands = target / ".codex" / "commands"
            commands.parent.mkdir(parents=True)
            try:
                commands.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "link or junction"):
                installer.install(REPO_ROOT, target, "production", set(), force=True)
            self.assertEqual([], list(outside.iterdir()))

    def test_install_rejects_manifest_directory_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            manifest_directory = target / ".agentic-framework"
            try:
                manifest_directory.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            with self.assertRaisesRegex(ValueError, "link or junction"):
                installer.install(REPO_ROOT, target, "production", set())
            self.assertEqual([], list(outside.iterdir()))

    def test_uninstall_does_not_depend_on_current_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            with mock.patch.object(
                installer,
                "build_operations",
                side_effect=AssertionError("uninstall read current sources"),
            ):
                installer.uninstall(Path("missing-source"), target)
            self.assertFalse((target / installer.MANIFEST_PATH).exists())

    def test_uninstall_accepts_manifest_for_retired_whole_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "production", set())
            without_skill = installer.CORE_SKILLS - {"bp-coding-best-practices"}
            with mock.patch.object(installer, "CORE_SKILLS", without_skill):
                installer.uninstall(REPO_ROOT, target)
            self.assertFalse((target / installer.MANIFEST_PATH).exists())

    def test_uninstall_accepts_manifest_for_retired_whole_pack(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            installer.install(REPO_ROOT, target, "tooling", {"open-code-review"})
            without_pack = dict(installer.PACK_SKILLS)
            without_pack.pop("open-code-review")
            with mock.patch.object(installer, "PACK_SKILLS", without_pack):
                installer.uninstall(REPO_ROOT, target)
            self.assertFalse((target / installer.MANIFEST_PATH).exists())

    def test_fixed_manifest_temporary_hardlink_is_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest_directory = target / installer.MANIFEST_PATH.parent
            manifest_directory.mkdir(parents=True)
            owned = target / "owned.txt"
            owned.write_text("project-owned", encoding="utf-8")
            predictable_temporary = (target / installer.MANIFEST_PATH).with_suffix(
                ".json.tmp"
            )
            try:
                os.link(owned, predictable_temporary)
            except OSError as error:
                self.skipTest(f"hardlink creation is unavailable: {error}")

            installer.install(REPO_ROOT, target, "production", set())
            self.assertEqual("project-owned", owned.read_text(encoding="utf-8"))
            self.assertEqual(
                "project-owned", predictable_temporary.read_text(encoding="utf-8")
            )
            self.assertEqual([], list(manifest_directory.glob(".manifest-*.tmp")))

    @unittest.skipUnless(os.name == "nt", "Windows Junction regression test")
    def test_install_rejects_managed_path_through_junction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            commands = target / ".codex" / "commands"
            commands.parent.mkdir(parents=True)
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(commands), str(outside)],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest(f"Junction creation failed: {result.stderr}")
            try:
                with self.assertRaisesRegex(ValueError, "link or junction"):
                    installer.install(
                        REPO_ROOT, target, "production", set(), force=True
                    )
                self.assertEqual([], list(outside.iterdir()))
            finally:
                commands.rmdir()

    @unittest.skipUnless(os.name == "nt", "Windows Junction regression test")
    def test_install_rejects_manifest_directory_junction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            manifest_directory = target / ".agentic-framework"
            result = subprocess.run(
                [
                    "cmd",
                    "/c",
                    "mklink",
                    "/J",
                    str(manifest_directory),
                    str(outside),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest(f"Junction creation failed: {result.stderr}")
            try:
                with self.assertRaisesRegex(ValueError, "link or junction"):
                    installer.install(REPO_ROOT, target, "production", set())
                self.assertEqual([], list(outside.iterdir()))
            finally:
                manifest_directory.rmdir()


if __name__ == "__main__":
    unittest.main()
