"""Regression tests for spec drift evaluation."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify


class EvaluateSpecDriftTest(unittest.TestCase):
    """Verify tracked and untracked specification matching."""

    def test_untracked_tasks_file_can_be_related(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tasks = root / "docs" / "tasks.md"
            tasks.parent.mkdir()
            tasks.write_text("`src/tool.py`\n", encoding="utf-8")
            with mock.patch.object(
                verify,
                "_changed_files",
                return_value=([], ["src/tool.py", "docs/tasks.md"], None),
            ):
                old_cwd = Path.cwd()
                try:
                    import os

                    os.chdir(root)
                    result = verify.evaluate_spec_drift("HEAD", "")
                finally:
                    os.chdir(old_cwd)
        self.assertEqual("pass", result.status)
        self.assertEqual(["docs/tasks.md"], result.value["related_spec_files"])

    def test_unrelated_untracked_spec_still_fails(self) -> None:
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=([], ["src/tool.py", "other/spec.md"], None),
        ):
            result = verify.evaluate_spec_drift("HEAD", "")
        self.assertEqual("fail", result.status)

    def test_change_tasks_can_prove_related_update(self) -> None:
        """An active Change tasks file can map a changed code path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tasks = root / "openspec/changes/add-tool/tasks.md"
            tasks.parent.mkdir(parents=True)
            tasks.write_text("- artifacts: `src/tool.py`\n", encoding="utf-8")
            with mock.patch.object(
                verify,
                "_changed_files",
                return_value=(
                    ["src/tool.py", "openspec/changes/add-tool/tasks.md"],
                    [],
                    None,
                ),
            ):
                old_cwd = Path.cwd()
                try:
                    import os

                    os.chdir(root)
                    result = verify.evaluate_spec_drift("HEAD", "")
                finally:
                    os.chdir(old_cwd)
        self.assertEqual("pass", result.status)

    def test_long_term_knowledge_with_source_path_can_prove_update(self) -> None:
        """Long-term Specs participate when they name the changed code path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            knowledge = root / "openspec/specs/backend/tool/overview.md"
            knowledge.parent.mkdir(parents=True)
            knowledge.write_text("source_paths:\n- src/tool.py\n", encoding="utf-8")
            with mock.patch.object(
                verify,
                "_changed_files",
                return_value=(
                    ["src/tool.py", "openspec/specs/backend/tool/overview.md"],
                    [],
                    None,
                ),
            ):
                old_cwd = Path.cwd()
                try:
                    import os

                    os.chdir(root)
                    result = verify.evaluate_spec_drift("HEAD", "")
                finally:
                    os.chdir(old_cwd)
        self.assertEqual("pass", result.status)
        self.assertEqual(
            ["openspec/specs/backend/tool/overview.md"],
            result.value["related_spec_files"],
        )

    def test_explicit_no_update_reason_still_passes(self) -> None:
        """A scoped reason is the escape hatch when no document maps mechanically."""
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=(["src/tool.py"], [], None),
        ):
            result = verify.evaluate_spec_drift(
                "HEAD", "只调整日志文字，不改变 Change 或长期知识"
            )
        self.assertEqual("pass", result.status)
        self.assertIn("无需更新原因", result.detail)


if __name__ == "__main__":
    unittest.main()
