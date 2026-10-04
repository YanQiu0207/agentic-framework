"""Regression tests for the delivery gate."""

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from unittest.mock import patch

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import native_subject

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

# v2 载荷模板：版本与内容主体由 _native_review / _native_verify 按仓库补齐。
REVIEW_PAYLOAD = {
    "verdict": "PASS",
    "p0_count": 0,
    "p1_count": 0,
    "scope": "integration",
    "review_profile": "standard",
    "round": 0,
}

VERIFY_SPEC_DRIFT = {
    "name": "Z-spec-drift",
    "type": "spec_drift",
    "status": "pass",
    "detail": "无代码文件变更",
    "value": None,
    "new_items": [],
}

STRICT_INDEPENDENCE = {
    "implementer_actor": "codex-1",
    "judge_actor": "reviewer-1",
    "independence_basis": "Judge 未参与实现，独立审查 change 全部产物",
}


def _repo_subject(repo: Path, base: str = "HEAD") -> str:
    """用公共内容标识 API 取当前主体，与交付门三方核对同源。"""
    capture = native_subject.capture_subject(repo, base)
    assert capture["complete"], capture["limitations"]
    return capture["subject_id"]


def _native_review(
    repo: Path, profile: str = "standard", base: str = "HEAD", **overrides
) -> dict:
    report = {
        "schema_version": 2,
        "subject_id": _repo_subject(repo, base),
        **REVIEW_PAYLOAD,
        "review_profile": profile,
    }
    report.update(overrides)
    return report


def _native_verify(repo: Path, base: str = "HEAD", **overrides) -> dict:
    report = {
        "schema_version": 2,
        "subject_id": _repo_subject(repo, base),
        "verdict": "PASS",
        "total": 1,
        "errors": 0,
        "violations": 0,
        "spec_drift": dict(VERIFY_SPEC_DRIFT),
        "warnings": [],
        # v2 合同要求 spec_drift == results[0]。
        "results": [dict(VERIFY_SPEC_DRIFT)],
    }
    report.update(overrides)
    return report


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
        # v2 内容主体必须覆盖 Verify 配置（Task 4 冻结分类）。
        (repo / "verify.config.json").write_text(
            '{"checks": []}', encoding="utf-8"
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
        return repo

    def _fast_path_inputs(
        self,
        repo: Path,
        *,
        review: dict | None = None,
        verify: dict | None = None,
    ) -> tuple[Path, Path]:
        # 报告写入报告目录（主体排除项）：内容主体不得自引用报告输出。
        review_path = repo / ".agentic-framework" / "review" / "review.json"
        verify_path = repo / ".agentic-framework" / "verify" / "verify.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        verify_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(
            json.dumps(
                review if review is not None else _native_review(repo, "lightweight")
            ),
            encoding="utf-8",
        )
        verify_path.write_text(
            json.dumps(verify if verify is not None else _native_verify(repo)),
            encoding="utf-8",
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
        # tasks/spec 先落盘提交：报告主体须按交付门重算时的内容生成。
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
        review, verify = self._fast_path_inputs(
            repo,
            review=(review if review is not None else _native_review(repo)),
            verify=verify,
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
                "--governance-profile",
                "tooling",
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

    def test_blocked_alias_with_inline_reason_passes(self) -> None:
        """别名归一后，原因抽取按原始前缀切片（change 2035 Task 7）。"""
        text = "### 任务 1: [ ] 实现\n- 状态: blocked 依赖外部审批\n- depends_on: []\n"
        self.assertEqual([], check_delivery.check_tasks(text))

    def test_blocked_alias_without_reason_fails(self) -> None:
        text = "### 任务 1: [ ] 实现\n- 状态: blocked\n- depends_on: []\n"
        errors = check_delivery.check_tasks(text)
        self.assertTrue(any("未附原因" in e for e in errors), errors)

    def test_completed_alias_is_terminal(self) -> None:
        text = "### 任务 1: [x] 实现\n- 状态: 已完成\n- depends_on: []\n"
        self.assertEqual([], check_delivery.check_tasks(text))

    def test_completed_state_with_unchecked_boxes_fails_delivery(self) -> None:
        """只改状态字段、不勾选复选框的形态必须被交付门拦住。"""
        text = (
            "### 任务 1: [ ] 实现\n- 状态: 完成\n- depends_on: []\n"
            "- 验收标准:\n    - [ ] 测试通过\n"
        )
        errors = check_delivery.check_tasks(text)
        self.assertTrue(any("任务头标记为 `[ ]`" in e for e in errors), errors)
        self.assertTrue(any("未勾选复选框" in e for e in errors), errors)

    def test_completed_header_with_manual_state_fails_delivery(self) -> None:
        text = (
            "### 任务 1: [x] 实现\n- 状态: 需人工（合并冲突）\n- depends_on: []\n"
        )
        errors = check_delivery.check_tasks(text)
        self.assertTrue(any("但状态为 `需人工`" in e for e in errors), errors)

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

    def test_scoped_delivery_requires_native_delivery(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr):
            code = check_delivery.main(
                ["--review-report", "missing.json", "--scoped-delivery"]
            )
        self.assertEqual(2, code)
        self.assertIn("--native-delivery", stderr.getvalue())

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

    def test_runtime_run_requires_knowledge_impact(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, _ = self._fast_path_inputs(repo, review=PASSING_RUN_REPORT)
        tasks = repo / "tasks.md"
        spec = repo / "proposal.md"
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
        output = StringIO()
        with (
            patch.object(check_delivery, "check_review_report", return_value=[]),
            redirect_stdout(output),
        ):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--run-dir",
                    str(repo / ".agentic-framework" / "runs" / "run-1"),
                    "--tasks",
                    str(tasks),
                    "--spec",
                    str(spec),
                    "--review-report",
                    str(review),
                ]
            )
        self.assertEqual(1, result)
        self.assertIn("缺少 --knowledge-impact hit|none", output.getvalue())

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
            review=_native_review(repo, "lightweight", scope="run"),
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
        # Fast-Path 只接受 lightweight；v2 standard 报告按档位不匹配拒绝。
        review, verify = self._fast_path_inputs(
            repo, review=_native_review(repo, "standard")
        )
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
        self.assertIn("未通过 Native v2 合同", stdout.getvalue())

    def test_main_fast_path_rejects_failed_verify(self) -> None:
        repo = self._clean_repo_with_ignore()
        failed = _native_verify(
            repo,
            verdict="FAIL",
            violations=1,
            results=[{**VERIFY_SPEC_DRIFT, "status": "fail"}],
            spec_drift={**VERIFY_SPEC_DRIFT, "status": "fail"},
        )
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
        self.assertIn("verdict 非 PASS", stdout.getvalue())

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

    def test_scoped_delivery_reports_scoped_claim_not_git_clean(self) -> None:
        repo = self._clean_repo_with_ignore()
        args, verdict = self._native_delivery_args(repo)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import workspace_residue

        snapshot = workspace_residue.capture_workspace_residue(
            repo, "HEAD", ["tasks.md", "proposal.md"]
        )
        baseline = repo / ".agentic-framework" / "verify" / "baseline.json"
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(
            json.dumps({"workspace_residue_snapshot": snapshot}), encoding="utf-8"
        )
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        output = StringIO()
        with redirect_stdout(output):
            code = check_delivery.main(
                args
                + [
                    "--scoped-delivery",
                    "--workspace-residue-baseline",
                    str(baseline),
                    "--delivery-commit",
                    commit,
                ]
            )
        self.assertEqual(0, code)
        verdict_payload = json.loads(verdict.read_text(encoding="utf-8"))
        self.assertIn("本次交付范围干净，预存残留未变化", output.getvalue())
        self.assertIn("Scoped Delivery 知识影响：未命中", output.getvalue())
        self.assertNotIn("工作区干净", output.getvalue())
        self.assertNotIn("git-clean", output.getvalue())
        self.assertEqual(True, verdict_payload["evidence"]["scoped_delivery"])
        self.assertNotIn("git_clean", verdict_payload["evidence"])
        self.assertIn("scoped-delivery-clean", verdict_payload["verified_claims"])

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
        review = _native_review(repo, run_id="forged-run")
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
                    review = _native_review(repo, **injected)
                else:
                    verify = _native_verify(repo, **injected)
                args, verdict_path = self._native_delivery_args(
                    repo, review=review, verify=verify
                )
                with redirect_stdout(StringIO()):
                    result = check_delivery.main(args)
                self.assertEqual(1, result)
                self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_forged_trust_claim(self) -> None:
        repo = self._clean_repo_with_ignore()
        review = _native_review(repo, trust_gate="PASS")
        args, verdict_path = self._native_delivery_args(repo, review=review)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_empty_or_failed_verify_results(self) -> None:
        for empty in (True, False):
            with self.subTest(empty=empty):
                repo = self._clean_repo_with_ignore()
                if empty:
                    verify = _native_verify(repo, total=0, results=[])
                else:
                    failing = {**VERIFY_SPEC_DRIFT, "status": "fail"}
                    verify = _native_verify(
                        repo,
                        verdict="FAIL",
                        violations=1,
                        results=[failing],
                        spec_drift=dict(failing),
                    )
                args, verdict_path = self._native_delivery_args(
                    repo, verify=verify
                )
                with redirect_stdout(StringIO()):
                    result = check_delivery.main(args)
                self.assertEqual(1, result)
                self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_incomplete_verify_result(self) -> None:
        repo = self._clean_repo_with_ignore()
        verify = _native_verify(repo, results=[{"status": "pass"}])
        args, verdict_path = self._native_delivery_args(repo, verify=verify)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_requires_passing_spec_drift_result(self) -> None:
        repo = self._clean_repo_with_ignore()
        verify = _native_verify(repo)
        del verify["spec_drift"]
        args, verdict_path = self._native_delivery_args(repo, verify=verify)
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_native_delivery_rejects_failed_verify(self) -> None:
        repo = self._clean_repo_with_ignore()
        erroring = {**VERIFY_SPEC_DRIFT, "status": "error"}
        args, verdict_path = self._native_delivery_args(
            repo,
            verify=_native_verify(
                repo,
                verdict="ERROR",
                errors=1,
                results=[erroring],
                spec_drift=dict(erroring),
            ),
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
                    repo, review=_native_review(repo, **{field: 1})
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

    def test_runtime_run_reports_knowledge_impact(self) -> None:
        repo = self._clean_repo_with_ignore()
        review, _ = self._fast_path_inputs(repo, review=PASSING_RUN_REPORT)
        tasks = repo / "tasks.md"
        spec = repo / "proposal.md"
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
        output = StringIO()
        with (
            patch.object(check_delivery, "check_review_report", return_value=[]),
            patch.object(
                check_delivery.runtime_workflow,
                "finalize_run",
                return_value={"verdict": "PASS"},
            ),
            redirect_stdout(output),
        ):
            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--run-dir",
                    str(repo / ".agentic-framework" / "runs" / "run-1"),
                    "--tasks",
                    str(tasks),
                    "--spec",
                    str(spec),
                    "--review-report",
                    str(review),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "requires no lasting knowledge update",
                ]
            )
        self.assertEqual(0, result)
        self.assertIn("Runtime Run 知识影响：未命中", output.getvalue())

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


class ReviewProfileFloorCheckTest(unittest.TestCase):
    """change 2041：交付门的 review_profile 下限检查。"""

    def _tasks(self, profile_line: str) -> tuple[Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        tasks = repo / "tasks.md"
        tasks.write_text(
            f"### 任务 1: [x] A\n- 状态: 完成\n{profile_line}",
            encoding="utf-8",
        )
        return repo, tasks

    def test_lightweight_below_production_floor_fails(self) -> None:
        repo, tasks = self._tasks("- review_profile: lightweight\n")
        errors = check_delivery.check_review_profile_floor(repo, tasks, "production")
        self.assertTrue(any("低于 production 下限" in e for e in errors), errors)

    def test_lightweight_passes_under_tooling(self) -> None:
        repo, tasks = self._tasks("- review_profile: lightweight\n")
        self.assertEqual(
            [], check_delivery.check_review_profile_floor(repo, tasks, "tooling")
        )

    def test_no_lightweight_means_profile_never_read(self) -> None:
        # 无 manifest、无 override、无 lightweight 声明：不触发读取，直接通过。
        repo, tasks = self._tasks("- review_profile: standard\n")
        self.assertEqual([], check_delivery.check_review_profile_floor(repo, tasks, None))


class KnowledgeSyncCrossCheckTest(unittest.TestCase):
    """change 2040：知识影响门从布尔计数升级为反自证交叉核对。"""

    def _change(self, *, sync_table: str = "", conflict: str = "- 状态: 无冲突\n",
                deltas: tuple[str, ...] = ()) -> tuple[Path, Path, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        change = repo / "openspec" / "changes" / "2099-x"
        change.mkdir(parents=True)
        tasks = (
            "# 实施任务清单\n\n### 任务 1: [x] 实现\n- 状态: 完成\n\n"
            "## 知识同步\n\n"
            "| Delta | 长期目标 | 动作 | 状态 | 索引更新 |\n"
            "| --- | --- | --- | --- | --- |\n"
            + sync_table
            + "\n## 知识冲突\n\n"
            + conflict
        )
        (change / "tasks.md").write_text(tasks, encoding="utf-8")
        for relative in deltas:
            delta = change / relative
            delta.parent.mkdir(parents=True, exist_ok=True)
            delta.write_text("# delta\n", encoding="utf-8")
        return repo, change, change / "tasks.md"

    def _check(self, repo, tasks, impact="hit"):
        return check_delivery.check_knowledge_sync(repo, tasks, impact)

    def test_valid_delta_sync_passes(self) -> None:
        repo, _change, tasks = self._change(
            sync_table="| `specs/backend/x.md` | `openspec/specs/backend/x.md` | MODIFIED | 已完成 | 既有条目 |\n",
            deltas=("specs/backend/x.md",),
        )
        self.assertEqual([], self._check(repo, tasks))

    def test_missing_declaration_fails(self) -> None:
        repo, _change, tasks = self._change(deltas=("specs/backend/x.md",))
        self.assertTrue(any("漏报" in e for e in self._check(repo, tasks)))

    def test_false_declaration_fails(self) -> None:
        repo, _change, tasks = self._change(
            sync_table="| `specs/backend/ghost.md` | `openspec/specs/backend/ghost.md` | ADDED | 已完成 | 无 |\n"
        )
        self.assertTrue(any("误报" in e for e in self._check(repo, tasks)))

    def test_target_mismatch_fails(self) -> None:
        repo, _change, tasks = self._change(
            sync_table="| `specs/backend/x.md` | `openspec/specs/backend/other.md` | MODIFIED | 已完成 | 无 |\n",
            deltas=("specs/backend/x.md",),
        )
        self.assertTrue(any("不匹配" in e for e in self._check(repo, tasks)))

    def test_incomplete_status_fails(self) -> None:
        repo, _change, tasks = self._change(
            sync_table="| `specs/backend/x.md` | `openspec/specs/backend/x.md` | MODIFIED | 未开始 | 无 |\n",
            deltas=("specs/backend/x.md",),
        )
        self.assertTrue(any("尚未完成" in e for e in self._check(repo, tasks)))

    def test_placeholder_conflict_section_fails(self) -> None:
        repo, _change, tasks = self._change(
            sync_table="| `specs/backend/x.md` | `openspec/specs/backend/x.md` | MODIFIED | 已完成 | 无 |\n",
            conflict="- 状态: 待交付时填写\n",
            deltas=("specs/backend/x.md",),
        )
        self.assertTrue(any("占位" in e for e in self._check(repo, tasks)))

    def test_none_impact_with_deltas_is_contradiction(self) -> None:
        repo, _change, tasks = self._change(deltas=("specs/backend/x.md",))
        self.assertTrue(any("无长期知识影响" in e for e in self._check(repo, tasks, impact="none")))

    def test_none_impact_without_deltas_passes(self) -> None:
        repo, _change, tasks = self._change()
        self.assertEqual([], self._check(repo, tasks, impact="none"))

    def test_hit_without_anything_fails(self) -> None:
        repo, _change, tasks = self._change()
        self.assertTrue(any("无 Delta 且无知识同步记录" in e for e in self._check(repo, tasks)))

    def test_no_specs_fallback_checks_target_existence(self) -> None:
        repo, change, tasks = self._change(
            sync_table="| `framework-x` | `openspec/specs/backend/framework/x/overview.md` | MODIFIED | 已完成 | 无 |\n"
        )
        # 目标不存在 → 失败（无 specs/ 的替代反向证据，不直接放行）
        self.assertTrue(any("目标不存在" in e for e in self._check(repo, tasks)))
        target = repo / "openspec" / "specs" / "backend" / "framework" / "x" / "overview.md"
        target.parent.mkdir(parents=True)
        target.write_text("# overview\n", encoding="utf-8")
        self.assertEqual([], self._check(repo, tasks))


if __name__ == "__main__":
    unittest.main()


STRICT_TERMINAL_TASKS = """### 任务 1: [x] 实现
- 状态: 完成
- depends_on: []
- review_profile: strict
"""


class NativeDeliveryV2GateTest(unittest.TestCase):
    """v2 报告合同、档位分派与三方主体核对（change 2048 Task 6）。"""

    # 复用 CheckDeliveryTest 的仓库与参数构造（self 提供 addCleanup）。
    _clean_repo = CheckDeliveryTest._clean_repo_with_ignore
    _delivery_args = CheckDeliveryTest._native_delivery_args
    _fast_path_inputs = CheckDeliveryTest._fast_path_inputs

    def test_tooling_strict_with_independent_judge_passes(self) -> None:
        repo = self._clean_repo()
        tasks = repo / "tasks.md"
        tasks.write_text(STRICT_TERMINAL_TASKS, encoding="utf-8")
        spec = repo / "proposal.md"
        spec.write_text("**状态**: Archived\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(repo), "add", "tasks.md", "proposal.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-qm", "strict-archive"],
            check=True,
            capture_output=True,
        )
        # 报告按交付门将重算的内容绑定主体（tasks/spec 已在基准内）。
        review_report = _native_review(repo, "strict", **STRICT_INDEPENDENCE)
        verify_report = _native_verify(repo)
        review, verify = CheckDeliveryTest._fast_path_inputs(
            self, repo, review=review_report, verify=verify_report
        )
        verdict = (
            repo / ".agentic-framework" / "native-delivery" / "verdict.json"
        )
        args = [
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
            "none",
            "--knowledge-impact-reason",
            "no lasting knowledge impact",
            "--governance-profile",
            "tooling",
        ]
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(args)
        self.assertEqual(0, result)
        self.assertIn("strict Review", stdout.getvalue())
        self.assertIn("三方 subject 一致", stdout.getvalue())
        payload = json.loads(verdict.read_text(encoding="utf-8"))
        self.assertEqual(2, payload["schema_version"])
        self.assertEqual("native-delivery-pass", payload["verdict"])
        self.assertEqual(
            "reviewer-1", payload["evidence"]["judge_actor"]
        )
        self.assertIn("strict-actor-separation-declared", payload["verified_claims"])
        self.assertTrue(payload["evidence"]["commit_sha"])

    def test_strict_same_actor_rejected(self) -> None:
        repo = self._clean_repo()
        forged = dict(STRICT_INDEPENDENCE, judge_actor="codex-1")
        args, verdict_path = self._delivery_args(
            repo, review=_native_review(repo, "strict", **forged)
        )
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_strict_missing_independence_rejected(self) -> None:
        repo = self._clean_repo()
        args, verdict_path = self._delivery_args(
            repo, review=_native_review(repo, "strict")
        )
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_standard_review_with_independence_fields_rejected(self) -> None:
        repo = self._clean_repo()
        args, verdict_path = self._delivery_args(
            repo, review=_native_review(repo, "standard", judge_actor="x")
        )
        with redirect_stdout(StringIO()):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())

    def test_production_profile_requires_strinct_review(self) -> None:
        repo = self._clean_repo()
        args, verdict_path = self._delivery_args(repo)
        index = args.index("--governance-profile")
        args[index + 1] = "production"
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())
        # Production 下限 strict：standard v2 Review 按档位不匹配拒绝。
        self.assertIn("未通过 Native v2 合同", stdout.getvalue())

    def test_subject_mismatch_between_reports_and_current_content(self) -> None:
        repo = self._clean_repo()
        other = "sha256:" + "a" * 64
        args, verdict_path = self._delivery_args(
            repo,
            review=_native_review(repo, subject_id=other),
        )
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())
        self.assertIn("与当前内容不一致", stdout.getvalue())

    def test_pre_delivery_edit_rejects_stale_reports(self) -> None:
        repo = self._clean_repo()
        args, verdict_path = self._delivery_args(repo)
        (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())
        self.assertIn("与当前内容不一致", stdout.getvalue())

    def test_legacy_v1_reports_rejected_as_new_evidence(self) -> None:
        repo = self._clean_repo()
        legacy_review = dict(REVIEW_PAYLOAD)
        legacy_verify = {
            "verdict": "PASS",
            "total": 1,
            "errors": 0,
            "violations": 0,
            "spec_drift": dict(VERIFY_SPEC_DRIFT),
            "warnings": [],
            "results": [dict(VERIFY_SPEC_DRIFT)],
        }
        for kind in ("review", "verify"):
            with self.subTest(kind=kind):
                current = self._clean_repo()
                review = legacy_review if kind == "review" else None
                verify = legacy_verify if kind == "verify" else None
                args, verdict_path = self._delivery_args(
                    current, review=review, verify=verify
                )
                stdout = StringIO()
                with redirect_stdout(stdout):
                    result = check_delivery.main(args)
                self.assertEqual(1, result)
                self.assertFalse(verdict_path.exists())
                self.assertIn("schema_version 2", stdout.getvalue())

    def test_knowledge_hit_requires_reason_for_v2_verdict(self) -> None:
        repo = self._clean_repo()
        args, verdict_path = self._delivery_args(
            repo, knowledge_impact="hit"
        )
        reason_index = args.index("--knowledge-impact-reason")
        del args[reason_index : reason_index + 2]
        stdout = StringIO()
        # 隔离知识同步核对，聚焦 v2 Verdict 对理由的显式要求。
        with patch.object(
            check_delivery, "check_knowledge_sync", return_value=[]
        ), redirect_stdout(stdout):
            result = check_delivery.main(args)
        self.assertEqual(1, result)
        self.assertFalse(verdict_path.exists())
        self.assertIn("非空 --knowledge-impact-reason", stdout.getvalue())
