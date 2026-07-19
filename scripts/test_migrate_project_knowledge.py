"""Tests for the read-only project knowledge migration planner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import migrate_project_knowledge


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
        self.assertIsNone(
            mappings["docs/arch-snapshots/order/structure.md"]["proposed_target"]
        )
        self.assertEqual(
            "classification-required",
            mappings["docs/arch-snapshots/order/structure.md"]["status"],
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
