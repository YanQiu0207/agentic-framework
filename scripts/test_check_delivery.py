"""Regression tests for the delivery gate."""

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
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

PASSING_RUN_REPORT = {
    "verdict": "PASS",
    "p0_count": 0,
    "p1_count": 0,
    "scope": "run",
    "review_profile": "standard",
    "round": 0,
}


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

    def test_fast_path_requires_knowledge_impact(self) -> None:
        self.assertTrue(check_delivery.check_knowledge_impact(None, ""))
        self.assertTrue(check_delivery.check_knowledge_impact("none", ""))
        self.assertEqual(
            [],
            check_delivery.check_knowledge_impact(
                "none", "只调整局部日志，不改变长期知识"
            ),
        )
        self.assertEqual([], check_delivery.check_knowledge_impact("hit", ""))

    def test_main_rejects_partial_standard_arguments(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            result = check_delivery.main(
                [
                    "--spec",
                    "proposal.md",
                    "--review-report",
                    "review-report.json",
                ]
            )
        self.assertEqual(2, result)
        self.assertIn("必须同时提供", stderr.getvalue())

    def test_main_fast_path_requires_and_reports_knowledge_impact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            report = repo / "review-report.json"
            report.write_text(json.dumps(PASSING_RUN_REPORT), encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
            )
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    1,
                    check_delivery.main(
                        [
                            "--repo",
                            str(repo),
                            "--review-report",
                            str(report),
                        ]
                    ),
                )
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = check_delivery.main(
                    [
                        "--repo",
                        str(repo),
                        "--knowledge-impact",
                        "none",
                        "--knowledge-impact-reason",
                        "只修改局部日志",
                        "--review-report",
                        str(report),
                    ]
                )
        self.assertEqual(1, result)
        self.assertIn("旧无绑定 Review PASS 不得放行", stdout.getvalue())
        self.assertIn("知识影响：未命中；理由：只修改局部日志", stdout.getvalue())

    def test_main_standard_pair_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            tasks = repo / "tasks.md"
            spec = repo / "proposal.md"
            report = repo / "review-report.json"
            tasks.write_text(TERMINAL_TASKS, encoding="utf-8")
            spec.write_text("**状态**: Archived\n", encoding="utf-8")
            report.write_text(json.dumps(PASSING_RUN_REPORT), encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-q",
                    "-m",
                    "fixture",
                ],
                check=True,
            )
            with redirect_stdout(StringIO()):
                result = check_delivery.main(
                    [
                        "--repo",
                        str(repo),
                        "--tasks",
                        str(tasks),
                        "--spec",
                        str(spec),
                        "--review-report",
                        str(report),
                    ]
                )
        self.assertEqual(1, result)


class CheckReviewReportTest(unittest.TestCase):
    """Cover the review-report evidence gate: existence, parsing, verdict, counts."""

    def _write(self, report: object) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "review-report.json"
        if isinstance(report, str):
            path.write_text(report, encoding="utf-8")
        else:
            path.write_text(json.dumps(report), encoding="utf-8")
        return path

    def test_passing_report(self) -> None:
        path = self._write(PASSING_RUN_REPORT)
        self.assertEqual([], check_delivery.check_review_report(path))

    def test_missing_file(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "absent.json"
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("找不到 Review 报告" in e for e in errors))

    def test_invalid_json(self) -> None:
        path = self._write("{not valid json")
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("解析失败" in e for e in errors))

    def test_verdict_not_pass(self) -> None:
        report = dict(PASSING_RUN_REPORT, verdict="NEEDS_CHANGES")
        path = self._write(report)
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("verdict 不是 PASS" in e for e in errors))

    def test_p0_count_nonzero(self) -> None:
        path = self._write(dict(PASSING_RUN_REPORT, p0_count=1))
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("p0_count 必须为整数 0" in e for e in errors))

    def test_p1_count_nonzero(self) -> None:
        path = self._write(dict(PASSING_RUN_REPORT, p1_count=2))
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("p1_count 必须为整数 0" in e for e in errors))

    def test_non_object_report_fails(self) -> None:
        path = self._write([])
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("JSON 对象" in error for error in errors))

    def test_count_types_must_be_integers(self) -> None:
        path = self._write(dict(PASSING_RUN_REPORT, p0_count=False, p1_count=0.0))
        errors = check_delivery.check_review_report(path)
        self.assertEqual(2, sum("必须为整数 0" in error for error in errors))

    def test_scope_must_be_run(self) -> None:
        path = self._write(dict(PASSING_RUN_REPORT, scope="task"))
        errors = check_delivery.check_review_report(path)
        self.assertTrue(any("scope 不是 run" in error for error in errors))

    def test_remaining_schema_fields_are_required(self) -> None:
        report = dict(PASSING_RUN_REPORT)
        del report["review_profile"]
        del report["round"]
        errors = check_delivery.check_review_report(self._write(report))
        self.assertTrue(any("review_profile 非法" in error for error in errors))
        self.assertTrue(any("round 必须为非负整数" in error for error in errors))


class MainReviewReportTest(unittest.TestCase):
    """--review-report is required, and it gates the overall exit code."""

    def _clean_repo(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        subprocess.run(
            ["git", "init", "-q", str(repo)], check=True, capture_output=True
        )
        return repo

    def test_missing_review_report_arg_exits_nonzero(self) -> None:
        repo = self._clean_repo()
        with self.assertRaises(SystemExit) as ctx:
            check_delivery.main(["--repo", str(repo)])
        self.assertNotEqual(0, ctx.exception.code)

    def test_fast_path_rejects_unbound_legacy_pass_report(self) -> None:
        repo = self._clean_repo()
        report = repo / "review-report.json"
        report.write_text(
            json.dumps(PASSING_RUN_REPORT),
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "commit",
                "-qm",
                "init",
            ],
            check=True,
            capture_output=True,
        )
        code = check_delivery.main(
            [
                "--repo",
                str(repo),
                "--review-report",
                str(report),
                "--knowledge-impact",
                "hit",
            ]
        )
        self.assertEqual(1, code)

    def test_bad_report_fails_overall(self) -> None:
        repo = self._clean_repo()
        report = repo / "review-report.json"
        report.write_text(
            json.dumps(dict(PASSING_RUN_REPORT, verdict="NEEDS_CHANGES", p0_count=3)),
            encoding="utf-8",
        )
        code = check_delivery.main(
            [
                "--repo",
                str(repo),
                "--review-report",
                str(report),
                "--knowledge-impact",
                "hit",
            ]
        )
        self.assertEqual(1, code)


if __name__ == "__main__":
    unittest.main()
