"""Regression tests for the delivery gate."""

import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "skills" / "workflow-code-generation" / "scripts"
    ),
)
import check_delivery

TERMINAL_TASKS = """### 任务 1: [x] 实现
- 状态: 完成
- depends_on: []

### 任务 2: [ ] 迁移
- 状态: 需人工（合并冲突，见 conflict.log）
- depends_on: [Task 1]
"""


class CheckDeliveryTest(unittest.TestCase):
    """Cover terminal states, reason requirement, spec status, and git cleanliness."""

    def test_terminal_tasks_with_reason_pass(self) -> None:
        self.assertEqual([], check_delivery.check_tasks(TERMINAL_TASKS))

    def test_in_progress_task_fails(self) -> None:
        text = "### 任务 1: [ ] 实现\n- 状态: 进行中\n- depends_on: []\n"
        errors = check_delivery.check_tasks(text)
        self.assertTrue(any("未到终态" in e for e in errors))

    def test_manual_state_without_reason_fails(self) -> None:
        text = "### 任务 1: [ ] 实现\n- 状态: 需人工\n- depends_on: []\n"
        errors = check_delivery.check_tasks(text)
        self.assertTrue(any("未附原因" in e for e in errors))

    def test_reason_field_satisfies_requirement(self) -> None:
        text = (
            "### 任务 1: [ ] 实现\n- 状态: 阻塞\n- 原因: 上游 Task 2 未合并\n"
            "- depends_on: []\n"
        )
        self.assertEqual([], check_delivery.check_tasks(text))

    def test_spec_must_be_archived(self) -> None:
        self.assertEqual([], check_delivery.check_spec("**状态**: Archived\n"))
        errors = check_delivery.check_spec("**状态**: Approved\n")
        self.assertTrue(any("Archived" in e for e in errors))

    def test_git_clean_and_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(
                ["git", "init", "-q", str(repo)], check=True, capture_output=True
            )
            self.assertEqual([], check_delivery.check_git_clean(repo))
            (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
            errors = check_delivery.check_git_clean(repo)
            self.assertTrue(any("工作区不干净" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
