"""Tests for the read-only shared knowledge validator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_shared_knowledge

VALID_FRONTMATTER = """\
---
status: verified
source: https://example.com/reference
source_version: 2026-07-19
applies_to: Python projects
excludes: browser-only applications
---
"""


class SharedKnowledgeValidatorTest(unittest.TestCase):
    """Cover public metadata, navigation, and candidate boundaries."""

    def _root(self, base: str) -> Path:
        root = Path(base)
        (root / "domains" / "testing").mkdir(parents=True)
        (root / "issues").mkdir()
        (root / "changes").mkdir()
        (root / "projects").mkdir()
        (root / "index.md").write_text(
            "# Public knowledge\n\n[Domains](domains/)\n[Issues](issues/)\n",
            encoding="utf-8",
        )
        (root / "domains" / "index.md").write_text(
            "# Domains\n\n[Testing](testing/index.md)\n", encoding="utf-8"
        )
        (root / "domains" / "testing" / "index.md").write_text(
            "# Testing\n\n[Entry](entry.md)\n", encoding="utf-8"
        )
        (root / "domains" / "testing" / "entry.md").write_text(
            VALID_FRONTMATTER + "\n# Entry\n", encoding="utf-8"
        )
        return root

    def test_valid_repository_passes_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            problems = validate_shared_knowledge.validate(root)
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
        self.assertEqual([], problems)
        self.assertEqual(before, after)

    def test_requires_public_entry_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            entry = root / "domains" / "testing" / "entry.md"
            entry.write_text(
                "---\nstatus: draft\nsource: local\n---\n# Entry\n",
                encoding="utf-8",
            )
            problems = validate_shared_knowledge.validate(root)
        joined = "\n".join(problems)
        self.assertIn("source_version, applies_to, excludes", joined)
        self.assertIn("status `draft`", joined)

    def test_rejects_projects_navigation_and_private_index_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            (root / "index.md").write_text(
                "[Projects](projects/)\n[Private](../private/spec.md)\n",
                encoding="utf-8",
            )
            problems = validate_shared_knowledge.validate(root)
        joined = "\n".join(problems)
        self.assertIn("projects/ 不得作为日常索引入口", joined)
        self.assertIn("公共索引不得链接 projects/", joined)
        self.assertIn("公共索引链接越出公共库", joined)

    def test_rejects_project_candidates_in_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            (root / "changes" / "candidate.md").write_text(
                "---\nscope: project\nkind: promotion-candidate\n---\n"
                "# 跨项目知识候选\n",
                encoding="utf-8",
            )
            problems = validate_shared_knowledge.validate(root)
        joined = "\n".join(problems)
        self.assertIn("禁止 scope: project", joined)
        self.assertIn("禁止项目知识候选类型", joined)
        self.assertIn("禁止保存项目知识候选", joined)

    def test_rejects_private_links_from_public_entry_bodies(self) -> None:
        """A compliant index cannot hide private links inside an entry body."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            entry = root / "domains" / "testing" / "entry.md"
            entry.write_text(
                VALID_FRONTMATTER
                + "\n# Entry\n\n[Project](../../projects/a/spec.md)\n"
                + "[Outside](../../../private/spec.md)\n",
                encoding="utf-8",
            )
            problems = validate_shared_knowledge.validate(root)
        joined = "\n".join(problems)
        self.assertIn("公共条目不得链接 projects/", joined)
        self.assertIn("公共条目链接越出公共库", joined)

    def test_rejects_project_scope_in_public_entries(self) -> None:
        """Public domains and issues cannot declare project scope."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            entry = root / "domains" / "testing" / "entry.md"
            entry.write_text(
                VALID_FRONTMATTER.replace(
                    "status: verified", "scope: project\nstatus: verified"
                )
                + "\n# Entry\n",
                encoding="utf-8",
            )
            problems = validate_shared_knowledge.validate(root)
        self.assertIn("公共条目禁止 scope: project", "\n".join(problems))

    def test_main_is_read_only_and_rejects_fix_option(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._root(temp_dir)
            self.assertEqual(0, validate_shared_knowledge.main(["--root", str(root)]))
            with self.assertRaises(SystemExit) as raised:
                validate_shared_knowledge.main(["--root", str(root), "--fix"])
        self.assertEqual(2, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
