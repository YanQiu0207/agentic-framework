"""Verify shared interview assets in both framework profiles and clients."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import install_agentic_framework as installer

REPO_ROOT = Path(__file__).resolve().parents[1]
INTERVIEW_SKILLS = ("bp-decision-interview", "bp-domain-modeling")
INTERVIEW_COMMANDS = ("grill-me.md", "grill-with-docs.md")


class InterviewInstallationTest(unittest.TestCase):
    """Check selection, managed manifests, and real linked installations."""

    def test_both_profiles_select_interview_assets_for_both_clients(
        self,
    ) -> None:
        for profile in ("production", "tooling"):
            operations = {
                operation.relative_target.as_posix(): operation
                for operation in installer.build_operations(
                    REPO_ROOT, profile, set()
                )
            }
            for client in installer.CLIENT_DIRS:
                with self.subTest(profile=profile, client=client):
                    for name in INTERVIEW_SKILLS:
                        path = f"{client}/skills/{name}"
                        self.assertIn(path, operations)
                        self.assertEqual("directory", operations[path].kind)
                        self.assertEqual(
                            REPO_ROOT / "skills" / name,
                            operations[path].source,
                        )
                    for name in INTERVIEW_COMMANDS:
                        path = f"{client}/commands/{name}"
                        self.assertIn(path, operations)
                        self.assertEqual("file", operations[path].kind)

    def test_managed_namespace_accepts_new_assets(self) -> None:
        for profile in ("production", "tooling"):
            for client in installer.CLIENT_DIRS:
                for name in INTERVIEW_SKILLS:
                    self.assertTrue(
                        installer._manifest_allowed_path(
                            f"{client}/skills/{name}", profile, set()
                        )
                    )
                for name in INTERVIEW_COMMANDS:
                    self.assertTrue(
                        installer._manifest_allowed_path(
                            f"{client}/commands/{name}", profile, set()
                        )
                    )

    def test_real_install_reinstall_and_uninstall_preserve_sources(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            probe_source = root / "probe-source"
            probe_source.write_text("probe", encoding="utf-8")
            probe_link = root / "probe-link"
            try:
                probe_link.symlink_to(probe_source)
            except OSError:
                self.skipTest("symbolic-link creation is unavailable")
            self.assertTrue(probe_link.is_symlink())
            self.assertTrue(probe_link.is_file())
            for profile in ("production", "tooling"):
                with self.subTest(profile=profile):
                    target = root / profile
                    target.mkdir()
                    registry = root / "registry.json"
                    installer.install(
                        REPO_ROOT,
                        target,
                        profile,
                        set(),
                        registry_path=registry,
                    )
                    manifest = installer._load_manifest(target)
                    self.assertIsNotNone(manifest)
                    self.assertEqual(profile, manifest["profile"])
                    paths = {item["path"] for item in manifest["links"]}
                    for client in installer.CLIENT_DIRS:
                        for name in INTERVIEW_SKILLS:
                            relative = f"{client}/skills/{name}"
                            self.assertIn(relative, paths)
                            skill = target / relative
                            self.assertTrue(skill.is_symlink())
                            self.assertEqual(
                                REPO_ROOT / "skills" / name, skill.resolve()
                            )
                            self.assertIn(
                                "Copyright (c) 2026 Matt Pocock",
                                (skill / "LICENSE").read_text(encoding="utf-8"),
                            )
                        for name in INTERVIEW_COMMANDS:
                            relative = f"{client}/commands/{name}"
                            self.assertIn(relative, paths)
                            command = target / relative
                            self.assertTrue(command.is_symlink())
                            self.assertEqual(
                                REPO_ROOT / "commands" / name, command.resolve()
                            )
                    installer.install(
                        REPO_ROOT,
                        target,
                        profile,
                        set(),
                        registry_path=registry,
                    )
                    installer.uninstall(
                        REPO_ROOT, target, registry_path=registry
                    )
                    for client in installer.CLIENT_DIRS:
                        for name in INTERVIEW_SKILLS:
                            self.assertFalse(
                                (target / client / "skills" / name).exists()
                            )
                            self.assertTrue(
                                (
                                    REPO_ROOT / "skills" / name / "LICENSE"
                                ).is_file()
                            )


if __name__ == "__main__":
    unittest.main()
