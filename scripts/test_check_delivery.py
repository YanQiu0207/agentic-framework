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

PASSING_LIGHTWEIGHT_REPORT = {
    "verdict": "PASS",
    "p0_count": 0,
    "p1_count": 0,
    "scope": "integration",
    "review_profile": "lightweight",
    "round": 0,
}

PASSING_NATIVE_REVIEW_REPORT = {
    "verdict": "PASS",
    "p0_count": 0,
    "p1_count": 0,
    "scope": "integration",
    "review_profile": "standard",
    "round": 0,
}

PASSING_VERIFY_REPORT = {
    "verdict": "PASS",
    "total": 1,
    "errors": 0,
    "violations": 0,
    "spec_drift": {
        "name": "Z-spec-drift",
        "type": "spec_drift",
        "status": "pass",
        "detail": "无代码文件变更",
        "value": None,
        "new_items": [],
    },
    "warnings": [],
    "results": [{"name": "test", "type": "test", "status": "pass", "detail": "ok", "value": None, "new_items": []}],
}


class CheckDeliveryTest(unittest.TestCase):
    """Cover terminal states, reason requirement, spec status, and git cleanliness."""

    def _clean_repo_with_ignore(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        subprocess.run(
            ["git", "init", "-q", str(repo)], check=True, capture_output=True
        )
        (repo / ".gitignore").write_text(".agentic-framework/\n", encoding="utf-8")
        (repo / "code.py").write_text("print('v1')\n", encoding="utf-8")
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
        return repo

    def _fast_path_inputs(
        self,
        repo: Path,
        *,
        review: dict | None = None,
        verify: dict | None = None,
    ) -> tuple[Path, Path]:
        runtime = repo / ".agentic-framework"
        runtime.mkdir(parents=True, exist_ok=True)
        review_path = runtime / "review.json"
        verify_path = runtime / "verify.json"
        review_path.write_text(
            json.dumps(review or PASSING_LIGHTWEIGHT_REPORT), encoding="utf-8"
        )
        verify_path.write_text(
            json.dumps(verify or PASSING_VERIFY_REPORT), encoding="utf-8"
        )
        return review_path, verify_path

    def _native_delivery_args(
        self,
        repo: Path,
        *,
        review: dict | None = None,
        verify: dict | None = None,
        knowledge_impact: str = "none",
    ) -> tuple[list[str], Path]:
        review, verify = self._fast_path_inputs(
            repo,
            review=(PASSING_NATIVE_REVIEW_REPORT if review is None else review),
            verify=verify,
        )
        tasks = repo / "tasks.md"
        spec = repo / "proposal.md"
        if not tasks.exists():
            tasks.write_text(TERMINAL_TASKS, encoding="utf-8")
            spec.write_text("**状态**: Archived\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(repo), "add", "tasks.md", "proposal.md"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "archive"],
                check=True,
                capture_output=True,
            )
        verdict = (
            repo
            / ".agentic-framework"
            / "native-delivery"
            / "native-delivery-verdict.json"
        )
        return (
            [
                "--repo",
                str(repo),
                "--tasks",
                str(tasks),
                "--spec",
                str(spec),
                "--native-delivery",
                "--native-delivery-verdict",
                str(verdict),
                "--review-report",
                str(review),
                "--verify-report",
                str(verify),
                "--knowledge-impact",
                knowledge_impact,
                "--knowledge-impact-reason",
                "local change has no lasting knowledge impact",
            ],
            verdict,
        )

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

    def test_main_fast_path_requires_knowledge_impact(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, verify = self._fast_path_inputs(repo)
        result = check_delivery.main(
            [
                "--repo",
                str(repo),
                "--review-report",
                str(review),
                "--verify-report",
                str(verify),
            ]
        )
        self.assertEqual(1, result)

    def test_main_fast_path_accepts_lightweight_delivery(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, verify = self._fast_path_inputs(repo)
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--review-report",
                    str(review),
                    "--verify-report",
                    str(verify),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "局部改动，无长期知识影响",
                ]
            )
        self.assertEqual(0, result)
        output = stdout.getvalue()
        self.assertIn("fast-path-pass", output)
        self.assertIn("知识影响：未命中；理由：局部改动", output)
        self.assertIn("unprovable_claims", output)
        self.assertIn("strict-independent-review", output)

    def test_fast_path_rejects_run_scope_even_with_lightweight_profile(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, verify = self._fast_path_inputs(
            repo,
            review=dict(PASSING_LIGHTWEIGHT_REPORT, scope="run"),
        )
        with redirect_stdout(StringIO()):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--review-report",
                    str(review),
                    "--verify-report",
                    str(verify),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "x",
                ]
            )
        self.assertEqual(1, result)

    def test_main_fast_path_rejects_standard_review_without_run_dir(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, verify = self._fast_path_inputs(repo, review=PASSING_RUN_REPORT)
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--review-report",
                    str(review),
                    "--verify-report",
                    str(verify),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "x",
                ]
            )
        self.assertEqual(1, result)
        self.assertIn("lightweight", stdout.getvalue())

    def test_main_fast_path_rejects_failed_verify(self) -> None:
        repo = self._clean_repo_with_ignore()
        failed = dict(PASSING_VERIFY_REPORT, verdict="FAIL", errors=2)
        review, verify = self._fast_path_inputs(repo, verify=failed)
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--review-report",
                    str(review),
                    "--verify-report",
                    str(verify),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "x",
                ]
            )
        self.assertEqual(1, result)
        self.assertIn("机器验证 verdict 非 PASS", stdout.getvalue())

    def test_main_fast_path_rejects_dirty_tree(self) -> None:
        repo = self._clean_repo_with_ignore()
        (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
        review, verify = self._fast_path_inputs(repo)
        result = check_delivery.main(
            [
                "--repo",
                str(repo),
                "--review-report",
                str(review),
                "--verify-report",
                str(verify),
                "--knowledge-impact",
                "none",
                "--knowledge-impact-reason",
                "x",
            ]
        )
        self.assertEqual(1, result)

    def test_native_delivery_writes_bounded_verdict_without_runtime_finalize(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict_path = self._native_delivery_args(repo)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(0, result)
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        self.assertEqual("native-delivery-pass", verdict["verdict"])
        self.assertNotIn("run_id", verdict)
        self.assertIn("runtime-trust-gate", verdict["unprovable_claims"])
        self.assertFalse((repo / ".agentic-framework" / "runs").exists())

    def test_native_delivery_rejects_forged_runtime_review_claim(self) -> None:
        repo = self._clean_repo_with_ignore()
        review = dict(PASSING_NATIVE_REVIEW_REPORT, run_id="forged-run")
        args, verdict_path = self._native_delivery_args(repo, review=review)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_unsafe_or_overlapping_output_path(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, _ = self._native_delivery_args(repo)
        verdict_index = args.index("--native-delivery-verdict") + 1
        args[verdict_index] = str(repo / "delivery.json")
        with redirect_stderr(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(2, result)

        args, _ = self._native_delivery_args(repo)
        verdict_index = args.index("--native-delivery-verdict") + 1
        review_index = args.index("--review-report") + 1
        args[verdict_index] = args[review_index]
        with redirect_stderr(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(2, result)

    def test_native_delivery_rejects_unprovable_review_or_verify_claims(self) -> None:
        cases = (
            ("review", {"harness_capability_probe": "PASS"}),
            ("review", {"judge_actor": "external"}),
            ("review", {"findings": [{"trust_gate": "PASS"}]}),
            ("verify", {"trust_gate": "PASS"}),
            ("verify", {"results": [{"trust_gate": "PASS"}]}),
            ("verify", {"results": [{"value": {"trust_gate": "PASS"}}]}),
            ("verify", {"spec_drift": {"value": {"trust_gate": "PASS"}}}),
        )
        for report_kind, injected in cases:
            with self.subTest(report_kind=report_kind, injected=injected):
                repo = self._clean_repo_with_ignore()
                review = None
                verify = None
                if report_kind == "review":
                    review = dict(PASSING_NATIVE_REVIEW_REPORT, **injected)
                else:
                    verify = dict(PASSING_VERIFY_REPORT, **injected)
                args, verdict_path = self._native_delivery_args(
                    repo, review=review, verify=verify
                )
                with redirect_stdout(StringIO()):
                    result = check_delivery.main(args)
                self.assertEqual(1, result)
                self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_forged_trust_claim(self) -> None:
        repo = self._clean_repo_with_ignore()
        review = dict(PASSING_NATIVE_REVIEW_REPORT, trust_gate="PASS")
        args, verdict_path = self._native_delivery_args(repo, review=review)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_empty_or_failed_verify_results(self) -> None:
        for verify in (
            dict(PASSING_VERIFY_REPORT, total=0, results=[]),
            dict(PASSING_VERIFY_REPORT, results=[dict(PASSING_VERIFY_REPORT["results"][0], status="fail")]),
        ):
            repo = self._clean_repo_with_ignore()
            args, verdict_path = self._native_delivery_args(repo, verify=verify)
            with redirect_stdout(StringIO()):
                result = check_delivery.main(args)
            self.assertEqual(1, result)
            self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_incomplete_verify_result(self) -> None:
        repo = self._clean_repo_with_ignore()
        verify = dict(
            PASSING_VERIFY_REPORT,
            results=[{"status": "pass"}],
        )
        args, verdict_path = self._native_delivery_args(repo, verify=verify)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_requires_passing_spec_drift_result(self) -> None:
        repo = self._clean_repo_with_ignore()
        verify = dict(PASSING_VERIFY_REPORT)
        del verify["spec_drift"]
        args, verdict_path = self._native_delivery_args(repo, verify=verify)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_failed_verify(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict_path = self._native_delivery_args(
            repo, verify=dict(PASSING_VERIFY_REPORT, verdict="FAIL", errors=1)
        )
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_review_findings(self) -> None:
        for field in ("p0_count", "p1_count"):
            with self.subTest(field=field):
                repo = self._clean_repo_with_ignore()
                args, verdict_path = self._native_delivery_args(
                    repo, review=dict(PASSING_NATIVE_REVIEW_REPORT, **{field: 1})
                )
                with redirect_stdout(StringIO()):
                    result = check_delivery.main(args)
                self.assertEqual(1, result)
                self.assertFalse(verdict_path.exists())

    def test_native_delivery_requires_knowledge_impact(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict_path = self._native_delivery_args(repo)
        del args[args.index("--knowledge-impact") : args.index("--knowledge-impact") + 4]
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_dirty_tree(self) -> None:
        repo = self._clean_repo_with_ignore()
        (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
        args, verdict_path = self._native_delivery_args(repo)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_accepts_terminal_tasks_and_archived_spec(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict_path = self._native_delivery_args(repo)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(0, result)
        self.assertTrue(verdict_path.is_file())

    def test_native_delivery_requires_tasks_and_spec(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict_path = self._native_delivery_args(repo)
        for option in ("--tasks", "--spec"):
            index = args.index(option)
            del args[index : index + 2]
        with redirect_stderr(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(2, result)
        self.assertFalse(verdict_path.exists())

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

    def test_review_profile_requirement_is_enforced(self) -> None:
        path = self._write(PASSING_RUN_REPORT)
        errors = check_delivery.check_review_report(path, expected_profile="strict")
        self.assertTrue(any("review_profile 必须为 strict" in error for error in errors))

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
