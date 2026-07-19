"""Tests for profile-isolated symbolic-link framework installation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import install_agentic_framework as installer

REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallTest(unittest.TestCase):
    """Verify link topology, registry behavior, and managed-entry safety."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.registry = self.root / "home" / "installations.json"
        probe_source = self.root / "probe-source"
        probe_target = self.root / "probe-target"
        probe_source.write_text("probe", encoding="utf-8")
        try:
            probe_target.symlink_to(probe_source)
        except OSError:
            self.symlinks_available = False
        else:
            self.symlinks_available = True
            probe_target.unlink()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _require_symlinks(self) -> None:
        if not self.symlinks_available:
            self.skipTest("symbolic-link creation is unavailable")

    def _install(
        self,
        target: Path,
        profile: str = "tooling",
        packs: set[str] | None = None,
        **kwargs,
    ) -> None:
        self._require_symlinks()
        installer.install(
            REPO_ROOT,
            target,
            profile,
            packs or set(),
            registry_path=self.registry,
            **kwargs,
        )

    def test_build_operations_uses_directory_links_for_skills(self) -> None:
        operations = installer.build_operations(REPO_ROOT, "tooling", set())
        skill = next(
            operation
            for operation in operations
            if operation.relative_target.as_posix()
            == ".codex/skills/workflow-code-generation"
        )
        command = next(
            operation
            for operation in operations
            if operation.relative_target.as_posix()
            == ".codex/commands/code-generation.md"
        )
        self.assertEqual("directory", skill.kind)
        self.assertEqual("file", command.kind)

    def test_unregistered_agent_file_is_not_installed(self) -> None:
        source = self.root / "source"
        shutil.copytree(REPO_ROOT, source)
        extra = source / "agents" / "unregistered-reviewer.md"
        extra.write_text("unregistered", encoding="utf-8")
        operations = installer.build_operations(source, "tooling", set())
        self.assertNotIn(extra, {operation.source for operation in operations})

    def test_missing_active_agent_fails_clearly(self) -> None:
        active = set(installer.ACTIVE_AGENT_FILES) | {"missing-reviewer.md"}
        with mock.patch.object(installer, "ACTIVE_AGENT_FILES", active):
            with self.assertRaisesRegex(FileNotFoundError, "missing-reviewer.md"):
                installer.build_operations(REPO_ROOT, "tooling", set())

    def test_missing_profile_and_pack_scripts_fail_clearly(self) -> None:
        source = self.root / "source"
        shutil.copytree(REPO_ROOT, source)
        validator = source / "scripts" / "validate_change.py"
        validator.unlink()
        with self.assertRaisesRegex(FileNotFoundError, "validate_change.py"):
            installer.build_operations(source, "production", set())
        shutil.copy2(REPO_ROOT / "scripts" / "validate_change.py", validator)
        telemetry = source / "scripts" / "analyze_session_metrics.py"
        telemetry.unlink()
        with self.assertRaisesRegex(FileNotFoundError, "analyze_session_metrics.py"):
            installer.build_operations(source, "tooling", {"telemetry"})

    @unittest.skipUnless(os.name == "nt", "Windows path normalization test")
    def test_windows_extended_link_paths_are_normalized(self) -> None:
        drive_path = r"C:\Framework\skills\example"
        extended_drive = r"\\?\C:\Framework\skills\example"
        unc_path = r"\\server\share\skills\example"
        extended_unc = r"\\?\UNC\server\share\skills\example"
        self.assertEqual(
            installer._normalized_link_path(drive_path),
            installer._normalized_link_path(extended_drive),
        )
        self.assertEqual(
            installer._normalized_link_path(unc_path),
            installer._normalized_link_path(extended_unc),
        )

    def test_production_links_only_production_lifecycle(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target, "production")
        production = target / ".codex" / "skills" / "opsx-code-generation"
        self.assertTrue(production.is_symlink())
        self.assertFalse(
            (target / ".codex" / "skills" / "workflow-code-generation").exists()
        )
        self.assertTrue(
            (target / ".codex" / "scripts" / "validate_change.py").is_symlink()
        )

    def test_shared_project_skills_are_installed_for_both_profiles(self) -> None:
        for profile in ("production", "tooling"):
            with self.subTest(profile=profile):
                operations = installer.build_operations(REPO_ROOT, profile, set())
                targets = {
                    operation.relative_target.as_posix() for operation in operations
                }
                for client in installer.CLIENT_DIRS:
                    self.assertIn(
                        f"{client}/skills/project-init",
                        targets,
                    )
                    self.assertIn(
                        f"{client}/skills/project-knowledge",
                        targets,
                    )
                    self.assertIn(
                        f"{client}/commands/project-init.md",
                        targets,
                    )

    def test_legacy_project_init_pack_is_safe_for_production(self) -> None:
        operations = installer.build_operations(
            REPO_ROOT,
            "production",
            {"project-init"},
        )
        targets = [operation.relative_target for operation in operations]
        self.assertEqual(len(targets), len(set(targets)))

    def test_source_content_change_is_immediately_visible(self) -> None:
        self._require_symlinks()
        source = self.root / "source"
        shutil.copytree(REPO_ROOT, source)
        target = self.root / "target"
        target.mkdir()
        installer.install(
            source,
            target,
            "tooling",
            set(),
            registry_path=self.registry,
        )
        source_file = source / "commands" / "code-generation.md"
        linked_file = target / ".codex" / "commands" / "code-generation.md"
        original = source_file.read_text(encoding="utf-8")
        source_file.write_text(original + "\nvisible-update\n", encoding="utf-8")
        self.assertIn("visible-update", linked_file.read_text(encoding="utf-8"))

    def test_manifest_v2_and_registry_record_selection(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target, packs={"telemetry"})
        manifest = json.loads(
            (target / installer.MANIFEST_PATH).read_text(encoding="utf-8")
        )
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(2, manifest["schema_version"])
        self.assertEqual(str(REPO_ROOT.resolve()), manifest["source"])
        self.assertEqual(["telemetry"], manifest["packs"])
        self.assertTrue(manifest["links"])
        self.assertEqual(str(target.absolute()), registry["installations"][0]["target"])

    def test_profile_switch_requires_explicit_flag(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target, "production")
        with self.assertRaisesRegex(ValueError, "different profile"):
            installer.install(
                REPO_ROOT,
                target,
                "tooling",
                set(),
                registry_path=self.registry,
            )
        self._install(target, "tooling", switch_profile=True)
        self.assertFalse(
            os.path.lexists(target / ".codex" / "skills" / "opsx-code-generation")
        )

    def test_tampered_link_blocks_reinstall_even_with_force(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target)
        managed = target / ".codex" / "commands" / "code-generation.md"
        managed.unlink()
        managed.symlink_to(REPO_ROOT / "README.md")
        with self.assertRaisesRegex(FileExistsError, "changed or replaced"):
            installer.install(
                REPO_ROOT,
                target,
                "tooling",
                set(),
                force=True,
                registry_path=self.registry,
            )

    def test_broken_managed_link_can_be_repaired(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target)
        managed = target / ".codex" / "commands" / "code-generation.md"
        source = REPO_ROOT / "commands" / "code-generation.md"
        managed.unlink()
        missing = self.root / "missing"
        managed.symlink_to(missing)
        with self.assertRaisesRegex(FileExistsError, "changed or replaced"):
            installer.install(
                REPO_ROOT,
                target,
                "tooling",
                set(),
                registry_path=self.registry,
            )
        managed.unlink()
        managed.symlink_to(source)
        self._install(target)
        self.assertTrue(managed.is_symlink())

    def test_unmanaged_leaf_link_is_refused_but_managed_leaf_is_allowed(self) -> None:
        target = self.root / "target"
        target.mkdir()
        command = target / ".codex" / "commands" / "code-generation.md"
        command.parent.mkdir(parents=True)
        self._require_symlinks()
        command.symlink_to(REPO_ROOT / "README.md")
        with self.assertRaisesRegex(FileExistsError, "unmanaged target"):
            installer.install(
                REPO_ROOT,
                target,
                "tooling",
                set(),
                registry_path=self.registry,
            )

    def test_ancestor_link_is_rejected(self) -> None:
        self._require_symlinks()
        target = self.root / "target"
        outside = self.root / "outside"
        target.mkdir()
        outside.mkdir()
        codex = target / ".codex"
        codex.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "link or junction"):
            installer.install(
                REPO_ROOT,
                target,
                "tooling",
                set(),
                registry_path=self.registry,
            )

    def test_link_permission_failure_is_explicit_and_does_not_copy(self) -> None:
        target = self.root / "target"
        target.mkdir()
        with mock.patch.object(Path, "symlink_to", side_effect=OSError("denied")):
            with self.assertRaisesRegex(OSError, "No files were copied"):
                installer.install(
                    REPO_ROOT,
                    target,
                    "tooling",
                    set(),
                    registry_path=self.registry,
                )
        self.assertFalse((target / installer.MANIFEST_PATH).exists())
        self.assertFalse(self.registry.exists())

    def test_create_failure_restores_previous_links_and_manifest(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target)
        manifest_path = target / installer.MANIFEST_PATH
        original_manifest = manifest_path.read_bytes()
        managed = target / ".codex" / "commands" / "code-generation.md"
        original_target = os.readlink(managed)
        real_create = installer._create_link
        calls = 0

        def fail_second_create(operation, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated link failure")
            real_create(operation, destination)

        with mock.patch.object(
            installer, "_create_link", side_effect=fail_second_create
        ):
            with self.assertRaisesRegex(OSError, "simulated link failure"):
                installer.install(
                    REPO_ROOT,
                    target,
                    "tooling",
                    set(),
                    registry_path=self.registry,
                )
        self.assertEqual(original_manifest, manifest_path.read_bytes())
        self.assertEqual(original_target, os.readlink(managed))

    def test_v1_skill_tree_create_failure_restores_copied_tree(self) -> None:
        self._require_symlinks()
        target = self.root / "target"
        skill_name = "bp-architecture-design"
        source_skill = REPO_ROOT / "skills" / skill_name
        copied_skill = target / ".codex" / "skills" / skill_name
        shutil.copytree(source_skill, copied_skill)
        files = [
            {
                "path": child.relative_to(target).as_posix(),
                "sha256": installer._hash(child),
            }
            for child in installer._tree_files(copied_skill)
        ]
        manifest_path = target / installer.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "framework_version": "legacy",
                    "profile": "tooling",
                    "packs": [],
                    "files": files,
                }
            ),
            encoding="utf-8",
        )
        original_manifest = manifest_path.read_bytes()
        original_files = {
            item["path"]: (target / item["path"]).read_bytes() for item in files
        }
        real_create = installer._create_link
        calls = 0

        def fail_second_create(operation, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated v1 upgrade failure")
            real_create(operation, destination)

        with mock.patch.object(
            installer, "_create_link", side_effect=fail_second_create
        ):
            with self.assertRaisesRegex(OSError, "simulated v1 upgrade failure"):
                installer.install(
                    REPO_ROOT,
                    target,
                    "tooling",
                    set(),
                    registry_path=self.registry,
                )
        self.assertFalse(copied_skill.is_symlink())
        self.assertEqual(original_manifest, manifest_path.read_bytes())
        for relative, content in original_files.items():
            self.assertEqual(content, (target / relative).read_bytes())

    def test_broken_directory_link_rollback_uses_manifest_type(self) -> None:
        self._require_symlinks()
        target = self.root / "target"
        target.mkdir()
        relative = ".codex/skills/bp-architecture-design"
        managed = target / Path(relative)
        managed.parent.mkdir(parents=True)
        missing_source = self.root / "missing-skill-directory"
        managed.symlink_to(missing_source, target_is_directory=True)
        manifest_path = target / installer.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True)
        manifest = {
            "schema_version": 2,
            "framework_version": installer.FRAMEWORK_VERSION,
            "source": str(REPO_ROOT.resolve()),
            "profile": "tooling",
            "packs": [],
            "links": [
                {
                    "path": relative,
                    "source": str(missing_source.absolute()),
                    "type": "directory",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        real_create = installer._create_link
        calls = 0

        def fail_second_create(operation, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated broken-directory rollback")
            real_create(operation, destination)

        with mock.patch.object(
            installer, "_create_link", side_effect=fail_second_create
        ):
            with self.assertRaisesRegex(OSError, "simulated broken-directory rollback"):
                installer.install(
                    REPO_ROOT,
                    target,
                    "tooling",
                    set(),
                    registry_path=self.registry,
                )
        self.assertTrue(managed.is_symlink())
        self.assertEqual(str(missing_source.absolute()), os.readlink(managed))

    def test_uninstall_removes_links_not_source_or_project_files(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target)
        project_file = target / ".codex" / "commands" / "project-owned.md"
        project_file.write_text("keep", encoding="utf-8")
        source_file = REPO_ROOT / "commands" / "code-generation.md"
        installer.uninstall(REPO_ROOT, target, registry_path=self.registry)
        self.assertTrue(source_file.exists())
        self.assertEqual("keep", project_file.read_text(encoding="utf-8"))
        self.assertFalse((target / installer.MANIFEST_PATH).exists())
        registry = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual([], registry["installations"])

    def test_v1_manifest_is_upgraded_to_links(self) -> None:
        self._require_symlinks()
        target = self.root / "target"
        copied = target / ".codex" / "commands" / "code-generation.md"
        copied.parent.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "commands" / "code-generation.md", copied)
        manifest_path = target / installer.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "framework_version": "legacy",
                    "profile": "tooling",
                    "packs": [],
                    "files": [
                        {
                            "path": ".codex/commands/code-generation.md",
                            "sha256": installer._hash(copied),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        installer.install(
            REPO_ROOT,
            target,
            "tooling",
            set(),
            registry_path=self.registry,
        )
        self.assertTrue(copied.is_symlink())
        upgraded = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(2, upgraded["schema_version"])

    def test_v1_manifest_can_be_uninstalled_without_source(self) -> None:
        target = self.root / "target"
        copied = target / ".codex" / "commands" / "code-generation.md"
        copied.parent.mkdir(parents=True)
        copied.write_text("legacy", encoding="utf-8")
        manifest_path = target / installer.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "framework_version": "legacy",
                    "profile": "tooling",
                    "packs": [],
                    "files": [
                        {
                            "path": ".codex/commands/code-generation.md",
                            "sha256": installer._hash(copied),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        installer.uninstall(
            self.root / "missing-source",
            target,
            registry_path=self.registry,
        )
        self.assertFalse(copied.exists())

    def test_forged_manifest_cannot_remove_project_readme(self) -> None:
        target = self.root / "target"
        target.mkdir()
        readme = target / "README.md"
        readme.write_text("project", encoding="utf-8")
        manifest_path = target / installer.MANIFEST_PATH
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "framework_version": installer.FRAMEWORK_VERSION,
                    "source": str(REPO_ROOT.resolve()),
                    "profile": "tooling",
                    "packs": [],
                    "links": [
                        {
                            "path": "README.md",
                            "source": str(readme.absolute()),
                            "type": "file",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "unmanaged path"):
            installer.uninstall(REPO_ROOT, target, registry_path=self.registry)
        self.assertEqual("project", readme.read_text(encoding="utf-8"))

    def test_registry_paths_are_case_normalized_for_matching(self) -> None:
        target = self.root / "target"
        target.mkdir()
        duplicate_registry = {
            "schema_version": 1,
            "installations": [
                {
                    "source": str(REPO_ROOT.resolve()),
                    "target": str(target.absolute()),
                    "profile": "tooling",
                    "packs": [],
                },
                {
                    "source": str(REPO_ROOT.resolve()),
                    "target": str(target.absolute()).upper(),
                    "profile": "tooling",
                    "packs": [],
                },
            ],
        }
        installer._write_json(self.registry, duplicate_registry)
        with mock.patch.object(
            installer.os.path,
            "normcase",
            side_effect=lambda value: value.casefold(),
        ):
            with self.assertRaisesRegex(ValueError, "duplicate installation"):
                installer._load_registry(self.registry)

        manifest = {
            "schema_version": 2,
            "framework_version": installer.FRAMEWORK_VERSION,
            "source": str(REPO_ROOT.resolve()).upper(),
            "profile": "tooling",
            "packs": [],
            "links": [],
        }
        installer._write_manifest(target, manifest)
        registry = {
            "schema_version": 1,
            "installations": [
                {
                    "source": str(REPO_ROOT.resolve()).upper(),
                    "target": str(target.absolute()),
                    "profile": "tooling",
                    "packs": [],
                }
            ],
        }
        installer._write_json(self.registry, registry)
        with mock.patch.object(
            installer.os.path,
            "normcase",
            side_effect=lambda value: value.casefold(),
        ), mock.patch.object(installer, "install") as install:
            installer.refresh_all(REPO_ROOT, registry_path=self.registry)
        install.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "Windows Junction regression test")
    def test_install_rejects_managed_path_through_junction(self) -> None:
        target = self.root / "target"
        outside = self.root / "outside"
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
                    REPO_ROOT,
                    target,
                    "tooling",
                    set(),
                    registry_path=self.registry,
                )
            self.assertEqual([], list(outside.iterdir()))
        finally:
            commands.rmdir()

    def test_refresh_all_refreshes_two_confirmed_targets(self) -> None:
        first = self.root / "first"
        second = self.root / "second"
        first.mkdir()
        second.mkdir()
        self._install(first)
        self._install(second, packs={"telemetry"})
        with mock.patch.object(installer, "install", wraps=installer.install) as call:
            installer.refresh_all(REPO_ROOT, registry_path=self.registry)
        self.assertEqual(2, call.call_count)
        self.assertTrue(
            (
                second
                / ".agentic-framework"
                / "packs"
                / "telemetry"
                / "analyze_session_metrics.py"
            ).is_symlink()
        )

    def test_refresh_all_removes_retired_link(self) -> None:
        target = self.root / "target"
        target.mkdir()
        self._install(target)
        retired = target / ".codex" / "skills" / "bp-coding-best-practices"
        self.assertTrue(retired.is_symlink())
        selected = installer.CORE_SKILLS - {"bp-coding-best-practices"}
        with mock.patch.object(installer, "CORE_SKILLS", selected):
            installer.refresh_all(REPO_ROOT, registry_path=self.registry)
        self.assertFalse(os.path.lexists(retired))

    def test_refresh_all_does_not_blindly_install_stale_target(self) -> None:
        target = self.root / "target"
        target.mkdir()
        registry = {
            "schema_version": 1,
            "installations": [
                {
                    "source": str(REPO_ROOT.resolve()),
                    "target": str(target.absolute()),
                    "profile": "tooling",
                    "packs": [],
                }
            ],
        }
        installer._write_json(self.registry, registry)
        with self.assertRaisesRegex(RuntimeError, "does not confirm"):
            installer.refresh_all(REPO_ROOT, registry_path=self.registry)
        self.assertEqual([], list(target.iterdir()))

    def test_dry_run_writes_nothing(self) -> None:
        target = self.root / "target"
        target.mkdir()
        installer.install(
            REPO_ROOT,
            target,
            "production",
            set(),
            dry_run=True,
            registry_path=self.registry,
        )
        self.assertEqual([], list(target.iterdir()))
        self.assertFalse(self.registry.exists())

    def test_parse_refresh_all_does_not_require_target(self) -> None:
        args = installer.parse_args(["--refresh-all"])
        self.assertTrue(args.refresh_all)
        self.assertIsNone(args.target_dir)


if __name__ == "__main__":
    unittest.main()
