"""Regression tests for the delivery gate."""

import json
import subprocess
import tempfile
import unittest
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


class CheckReviewReportTest(unittest.TestCase):
    """Cover the review-report evidence gate: existence, parsing, verdict, counts."""

    def _write(self, report: object) -> Path:
        temp = Path(tempfile.mkdtemp())
        path = temp / "review-report.json"
        if isinstance(report, str):
            path.write_text(report, encoding="utf-8")
        else:
            path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def test_passing_report(self) -> None:
        path = self._write({"verdict": "PASS", "p0_count": 0, "p1_count": 0})
        self.assertEqual([], check_delivery.check_review_report(path))

    def test_missing_file(self) -> None:
        path = Path(tempfile.mkdtemp()) / "absent.json"
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("找不到 Review 报告" in e for e in errors))

    def test_invalid_json(self) -> None:
        path = self._write("{not valid json")
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("解析失败" in e for e in errors))

    def test_verdict_not_pass(self) -> None:
        path = self._write(
            {"verdict": "NEEDS_CHANGES", "p0_count": 0, "p1_count": 0}
        )
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("verdict 不是 PASS" in e for e in errors))

    def test_p0_count_nonzero(self) -> None:
        path = self._write({"verdict": "PASS", "p0_count": 1, "p1_count": 0})
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("p0_count 不为 0" in e for e in errors))

    def test_p1_count_nonzero(self) -> None:
        path = self._write({"verdict": "PASS", "p0_count": 0, "p1_count": 2})
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("p1_count 不为 0" in e for e in errors))


class MainReviewReportTest(unittest.TestCase):
    """--review-report is required, and it gates the overall exit code."""

    def _clean_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp())
        subprocess.run(
            ["git", "init", "-q", str(repo)], check=True, capture_output=True
        )
        return repo

    def test_missing_review_report_arg_exits_nonzero(self) -> None:
        repo = self._clean_repo()
        with self.assertRaises(SystemExit) as ctx:
            check_delivery.main(["--repo", str(repo)])
        self.assertNotEqual(0, ctx.exception.code)

    def test_fast_path_passes_with_valid_report(self) -> None:
        repo = self._clean_repo()
        report = repo / "review-report.json"
        report.write_text(
            json.dumps({"verdict": "PASS", "p0_count": 0, "p1_count": 0}),
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "-qm", "init"],
            check=True,
            capture_output=True,
        )
        code = check_delivery.main(
            ["--repo", str(repo), "--review-report", str(report)]
        )
        self.assertEqual(0, code)

    def test_bad_report_fails_overall(self) -> None:
        repo = self._clean_repo()
        report = repo / "review-report.json"
        report.write_text(
            json.dumps({"verdict": "NEEDS_CHANGES", "p0_count": 3, "p1_count": 0}),
            encoding="utf-8",
        )
        code = check_delivery.main(
            ["--repo", str(repo), "--review-report", str(report)]
        )
        self.assertEqual(1, code)


if __name__ == "__main__":
    unittest.main()
