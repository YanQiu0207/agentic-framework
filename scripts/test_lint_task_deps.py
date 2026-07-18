"""Regression tests for task dependency parsing."""

import unittest
import tempfile
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "skills"
        / "workflow-code-generation"
        / "scripts"
    ),
)
import lint_task_deps


class TaskDependencyTest(unittest.TestCase):
    """Cover empty fields and duplicate identifiers."""

    def test_empty_depends_on_is_present(self) -> None:
        self.assertEqual(
            (set(), True), lint_task_deps.parse_deps("- depends_on:\n")
        )

    def test_missing_depends_on_is_absent(self) -> None:
        self.assertEqual(
            (set(), False), lint_task_deps.parse_deps("- 文件: `a.py`\n")
        )

    def test_duplicate_task_id_is_rejected(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n### 任务 1：B\n- depends_on: []\n"
        )
        with self.assertRaisesRegex(ValueError, "重复任务 ID: 1"):
            lint_task_deps.parse_tasks(text)

    def test_duplicate_task_id_returns_cli_error(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n### 任务 1：B\n- depends_on: []\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = Path(temp_dir) / "tasks.md"
            tasks_file.write_text(text, encoding="utf-8")
            self.assertEqual(2, lint_task_deps.main([str(tasks_file)]))

    def test_self_dependency_is_preserved_and_rejected(self) -> None:
        text = "### 任务 1：A\n- depends_on: [Task 1]\n"
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual({1}, tasks[1]["deps"])
        self.assertIn(1, lint_task_deps.reachable(tasks)[1])

    def test_missing_required_fields_are_errors(self) -> None:
        tasks = lint_task_deps.parse_tasks("### 任务 1：A\n- depends_on: []\n")
        errors = lint_task_deps.field_errors(tasks)
        for name in lint_task_deps.REQUIRED_FIELDS:
            self.assertTrue(any(f"缺少 {name} 字段" in e for e in errors), name)

    def test_invalid_profile_and_state_are_errors(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: heavy\n"
            "- context_files:\n- verification:\n- artifacts:\n- 状态: 已完结\n"
        )
        errors = lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))
        self.assertTrue(
            any("review_profile `heavy` 不合法" in e for e in errors)
        )
        self.assertTrue(any("状态 `已完结` 不含合法值" in e for e in errors))

    def test_valid_fields_pass(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: standard\n"
            "- context_files:\n- verification:\n- artifacts:\n"
            "- 状态: 未开始    （合法值：未开始 / 进行中 / 完成 / 需人工 / 阻塞）\n"
        )
        errors = lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))
        self.assertEqual([], errors)

    def test_main_parses_tasks_md_with_bom_prefix(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: standard\n"
            "- context_files:\n- verification:\n- artifacts:\n"
            "- 状态: 未开始\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = Path(temp_dir) / "tasks.md"
            tasks_file.write_bytes(text.encode("utf-8-sig"))
            self.assertEqual(0, lint_task_deps.main([str(tasks_file)]))


if __name__ == "__main__":
    unittest.main()
