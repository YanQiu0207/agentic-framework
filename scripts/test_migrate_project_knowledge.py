"""Tests for the read-only project knowledge migration planner."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import migrate_project_knowledge
from markdown_links import resolve_local_link


class ProjectKnowledgeMigrationTest(unittest.TestCase):
    """Cover mapping, references, safety, and the command interface."""

    def _repo(self, base: str) -> Path:
        repo = Path(base)
        files = {
            "docs/design-docs/orders/cancel/spec.md": "# Cancel\n",
            "docs/adr/001-storage.md": "# Storage\n",
            "docs/incidents/outage.md": "# Outage\n",
            "docs/issues/windows.md": "# Windows\n",
            "docs/arch-snapshots/order/structure.md": "# Structure\n",
            "README.md": "[ADR](docs/adr/001-storage.md)\n",
        }
        for name, content in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return repo

    def test_build_plan_is_read_only_and_maps_known_areas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            before = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file()
            }
            plan = migrate_project_knowledge.build_plan(repo)
            after = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file()
            }

        self.assertEqual(before, after)
        self.assertEqual("plan-only", plan["mode"])
        self.assertFalse(plan["safety"]["apply_supported"])
        mappings = {item["source"]: item for item in plan["mappings"]}
        self.assertEqual(
            "openspec/changes/archive/legacy-orders-cancel/spec.md",
            mappings["docs/design-docs/orders/cancel/spec.md"]["proposed_target"],
        )
        self.assertEqual(
            "openspec/issues/incidents/outage.md",
            mappings["docs/incidents/outage.md"]["proposed_target"],
        )
        self.assertEqual(
            "openspec/specs/backend/engineering/tech/adr/001-storage.md",
            mappings["docs/adr/001-storage.md"]["proposed_target"],
        )
        self.assertEqual(
            "openspec/issues/windows.md",
            mappings["docs/issues/windows.md"]["proposed_target"],
        )
        self.assertIsNone(
            mappings["docs/arch-snapshots/order/structure.md"]["proposed_target"]
        )
        self.assertEqual(
            "classification-required",
            mappings["docs/arch-snapshots/order/structure.md"]["status"],
        )
        self.assertTrue(
            all(
                "来源目录 README.md" in mapping["superseded_marker"]
                for mapping in mappings.values()
            )
        )

    def test_collects_resolved_markdown_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            plan = migrate_project_knowledge.build_plan(repo)

        mapping = next(
            item
            for item in plan["mappings"]
            if item["source"] == "docs/adr/001-storage.md"
        )
        self.assertEqual("README.md", mapping["references"][0]["path"])
        self.assertEqual(1, mapping["references"][0]["line"])

    def test_directory_superseded_marker_is_not_migrated_as_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            marker = repo / "docs" / "incidents" / "README.md"
            marker.write_text(
                "# 旧目录\n\n**状态**：Superseded\n",
                encoding="utf-8",
            )

            plan = migrate_project_knowledge.build_plan(repo)

        mapping = next(
            item
            for item in plan["mappings"]
            if item["source"] == "docs/incidents/README.md"
        )
        self.assertIsNone(mapping["proposed_target"])
        self.assertEqual("marker-only", mapping["status"])

    def test_reference_scan_precomputes_legacy_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            readme = repo / "README.md"
            readme.write_text(
                "docs/adr/001-storage.md\n" * 10,
                encoding="utf-8",
            )
            legacy = {
                repo / "docs/adr/001-storage.md",
                repo / "docs/issues/windows.md",
            }
            original = migrate_project_knowledge._as_posix
            with mock.patch.object(
                migrate_project_knowledge, "_as_posix", wraps=original
            ) as as_posix:
                references = migrate_project_knowledge._reference_index(repo, legacy)

        legacy_calls = [
            call
            for call in as_posix.call_args_list
            if call.args[0] in legacy
        ]
        self.assertEqual(len(legacy), len(legacy_calls))
        storage = next(path.resolve() for path in legacy if path.name == "001-storage.md")
        self.assertEqual(10, len(references[storage]))

    def test_shared_link_helper_handles_file_and_external_schemes(self) -> None:
        source = Path("repo/docs/index.md").resolve()
        expected = (source.parent / "adr/001.md").resolve()

        self.assertEqual(
            expected,
            resolve_local_link(source, "file:adr/001.md#decision"),
        )
        self.assertIsNone(resolve_local_link(source, "https://example.com/a.md"))

    @unittest.skipUnless(os.name == "nt", "Windows file URI semantics")
    def test_shared_link_helper_handles_windows_file_uris(self) -> None:
        source = Path("E:/shared/index.md")

        self.assertEqual(
            Path("E:/private/project.md"),
            resolve_local_link(source, "file:///E:/private/project.md"),
        )
        self.assertEqual(
            Path("//server/share/a.md"),
            resolve_local_link(source, "file://server/share/a.md"),
        )

    def test_markdown_scan_prunes_ignored_and_linked_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            ignored = repo / "node_modules" / "package.md"
            ignored.parent.mkdir()
            ignored.write_text("ignored", encoding="utf-8")
            linked = repo / "linked-docs"
            linked.mkdir()
            (linked / "linked.md").write_text("linked", encoding="utf-8")
            original = Path.is_symlink
            with mock.patch.object(
                Path,
                "is_symlink",
                autospec=True,
                side_effect=lambda path: path == linked or original(path),
            ):
                files = {
                    path.relative_to(repo).as_posix()
                    for path in migrate_project_knowledge._markdown_files(repo)
                }

        self.assertNotIn("node_modules/package.md", files)
        self.assertNotIn("linked-docs/linked.md", files)

    def test_rejects_legacy_path_without_file_component(self) -> None:
        with self.assertRaisesRegex(ValueError, "至少需要"):
            migrate_project_knowledge._proposed_target("docs/adr")

    def test_cli_writes_only_the_requested_plan_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            output = Path(temp_dir).parent / f"{Path(temp_dir).name}-plan.json"
            try:
                result = migrate_project_knowledge.main(
                    ["--repo", str(repo), "--output", str(output)]
                )
                plan = json.loads(output.read_text(encoding="utf-8"))
            finally:
                if output.exists():
                    output.unlink()

        self.assertEqual(0, result)
        self.assertEqual(5, plan["summary"]["files"])

    def test_invalid_repository_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            self.assertEqual(
                2, migrate_project_knowledge.main(["--repo", str(missing)])
            )


if __name__ == "__main__":
    unittest.main()
