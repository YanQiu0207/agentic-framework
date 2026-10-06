"""Cross-entry integration: real verify.py reports feeding the real gate.

change 2048 Task 14. These tests chain the actual CLIs in-process (verify.main,
check_delivery.main) instead of fabricating reports: Native Git serial/strict
delivery with worktree integration, and the pure-SVN lifecycle across two
working copies (pending → teammate race → exact-revision verification).
Fixtures are shared per class to respect the frozen B-tests-pass budget; no
scenario here re-tests unit logic already pinned elsewhere.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _path in (
    str(Path(__file__).resolve().parent),
    str(_REPO_ROOT / "scripts"),
    str(_REPO_ROOT / "skills" / "workflow-verification" / "scripts"),
):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import check_delivery
import verify
import workspace_residue

TASKS = """# 实施任务清单

### 任务 1：[x] 实现
- 状态: 完成
- 文件: `code.py`
- review_profile: strict
- verification:
  - [x] 集成验证通过
- 子任务:
  - [x] 1.1 实现完成
"""

_CONFIG = json.dumps(
    {
        "checks": [
            {
                "name": "ok",
                "type": "exit_code",
                "command": "python -c \"print('ok')\"",
            }
        ]
    }
)


@contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(
        list(args), cwd=str(cwd), check=True, capture_output=True, timeout=60
    )


def _git(cwd: Path, *args: str) -> None:
    _run(cwd, "git", *args)


def _svn(cwd: Path, *args: str) -> None:
    _run(cwd, "svn", *args, "--non-interactive")


def _verify_main(argv: list[str]) -> int:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return verify.main(argv)


def _review_report(subject: str) -> dict:
    return {
        "schema_version": 2,
        "subject_id": subject,
        "verdict": "PASS",
        "p0_count": 0,
        "p1_count": 0,
        "scope": "integration",
        "review_profile": "strict",
        "round": 0,
        "implementer_actor": "implementer-agent",
        "judge_actor": "independent-judge",
        "independence_basis": "Judge 未参与实现，独立审查全部产物",
    }


def _gate(argv: list[str]) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output), redirect_stderr(StringIO()):
        code = check_delivery.main(argv)
    return code, output.getvalue()


def _no_server_write_spy():
    """收集公共 VCS 查询命令，断言链路不执行任何 SVN 写命令。"""
    import vcs

    original = vcs._run
    commands: list[list[str]] = []

    def spy(root, args, data=None):
        commands.append(list(args))
        return original(root, args, data)

    return patch.object(vcs, "_run", side_effect=spy), commands


def _assert_no_svn_writes(testcase, commands: list[list[str]]) -> None:
    for command in commands:
        if command[0] == "svn":
            testcase.assertFalse(
                {"commit", "update", "revert", "switch"}.intersection(command[:2]),
                f"链路执行了写命令：{command}",
            )


class GitNativeIntegrationTest(unittest.TestCase):
    """真实 verify.py → 交付门 的 Git 跨入口链（默认零 Runtime 副作用）。"""

    repo: Path
    _tmp = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="int-git-")
        repo = Path(cls._tmp.name) / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", ".")
        _git(repo, "config", "user.email", "int@example.invalid")
        _git(repo, "config", "user.name", "Integration")
        (repo / ".gitignore").write_text(
            ".agentic-framework/\n", encoding="utf-8"
        )
        (repo / "code.py").write_text("print('v1')\n", encoding="utf-8")
        (repo / "verify.config.json").write_text(_CONFIG, encoding="utf-8")
        change = repo / "openspec" / "changes" / "1-int"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(TASKS, encoding="utf-8")
        (change / "proposal.md").write_text(
            "**状态**: Archived\n\n改动 `code.py`。\n", encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-qm", "base")
        cls.repo = repo

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._tmp is not None:
            cls._tmp.cleanup()

    def test_real_verify_report_feeds_strict_native_gate(self) -> None:
        repo = self.repo
        (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
        _git(repo, "add", "code.py")
        _git(repo, "commit", "-qm", "deliver")
        report = repo / ".agentic-framework" / "verify" / "report.json"
        with _chdir(repo):
            code = _verify_main(["--report", str(report)])
        self.assertEqual(0, code)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(2, payload["schema_version"])
        self.assertTrue(payload["subject_id"].startswith("sha256:"))
        review = repo / ".agentic-framework" / "review" / "review.json"
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text(
            json.dumps(_review_report(payload["subject_id"])), encoding="utf-8"
        )
        verdict = (
            repo / ".agentic-framework" / "native-delivery" / "verdict.json"
        )
        code, output = _gate(
            [
                "--repo", str(repo),
                "--tasks", str(repo / "openspec/changes/1-int/tasks.md"),
                "--spec", str(repo / "openspec/changes/1-int/proposal.md"),
                "--native-delivery",
                "--native-delivery-verdict", str(verdict),
                "--review-report", str(review),
                "--verify-report", str(report),
                "--knowledge-impact", "none",
                "--knowledge-impact-reason", "integration chain",
                "--governance-profile", "tooling",
            ]
        )
        self.assertEqual(0, code, output)
        result = json.loads(verdict.read_text(encoding="utf-8"))
        self.assertEqual("native-delivery-pass", result["verdict"])
        self.assertIn("implementer-agent", result["evidence"]["implementer_actor"])
        # 默认零 Runtime 副作用：无 Run 目录。
        self.assertFalse((repo / ".agentic-framework" / "runs").exists())

    def test_worktree_serial_integration_then_verify(self) -> None:
        repo = self.repo
        worktree = Path(self._tmp.name) / "wt"
        _git(repo, "worktree", "add", "-q", "-b", "feature", str(worktree))
        try:
            (worktree / "code.py").write_text("print('wt')\n", encoding="utf-8")
            _git(worktree, "add", "code.py")
            _git(worktree, "commit", "-qm", "feature")
            # 主编排方串行集成：单个 worktree 变更一次合并回主分支。
            _git(repo, "merge", "--ff-only", "feature")
        finally:
            _git(repo, "worktree", "remove", "--force", str(worktree))
        report = repo / ".agentic-framework" / "verify" / "report.json"
        with _chdir(repo):
            code = _verify_main(["--report", str(report)])
        self.assertEqual(0, code)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual("PASS", payload["verdict"])
        self.assertFalse((repo / ".agentic-framework" / "runs").exists())


class SvnLifecycleIntegrationTest(unittest.TestCase):
    """纯 SVN 两 WC 全生命周期：待提交 → 他人竞态 → 确切 revision 验证。"""

    server: Path
    _tmp = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="int-svn-")
        root = Path(cls._tmp.name)
        _run(root, "svnadmin", "create", str(root / "server"))
        staging = root / "staging"
        staging.mkdir()
        (staging / "code.py").write_text("print('v1')\n", encoding="utf-8")
        (staging / "verify.config.json").write_text(_CONFIG, encoding="utf-8")
        change = staging / "openspec" / "changes" / "1-int"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(TASKS, encoding="utf-8")
        (change / "proposal.md").write_text(
            "**状态**: Archived\n\n改动 `code.py`。\n", encoding="utf-8"
        )
        _run(
            root,
            "svn",
            "import",
            "--non-interactive",
            str(staging),
            (root / "server").as_uri(),
            "-m",
            "base",
            "--force-log",
        )
        cls.server = root / "server"

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._tmp is not None:
            cls._tmp.cleanup()

    def _checkout(self, name: str) -> Path:
        target = Path(self._tmp.name) / name
        _run(
            Path(self._tmp.name),
            "svn",
            "checkout",
            "--non-interactive",
            self.server.as_uri(),
            str(target),
        )
        return target

    def _gate_args(
        self, repo: Path, review: Path, verify: Path, verdict: Path,
        revision: str | None = None,
    ) -> list[str]:
        args = [
            "--repo", str(repo),
            "--tasks", str(repo / "openspec/changes/1-int/tasks.md"),
            "--spec", str(repo / "openspec/changes/1-int/proposal.md"),
            "--native-delivery",
            "--native-delivery-verdict", str(verdict),
            "--review-report", str(review),
            "--verify-report", str(verify),
            "--knowledge-impact", "none",
            "--knowledge-impact-reason", "integration chain",
            "--governance-profile", "tooling",
        ]
        if revision is not None:
            args += [
                "--scoped-delivery",
                "--workspace-residue-baseline",
                str(repo / ".agentic-framework/verify/baseline.json"),
                "--delivery-revision", revision,
            ]
        return args

    def test_pending_race_then_revision_verified_with_real_reports(self) -> None:
        repo = self._checkout("wc")
        teammate = self._checkout("wc2")
        review = repo / ".agentic-framework" / "review" / "review.json"
        verify_report = repo / ".agentic-framework" / "verify" / "report.json"
        verdict = (
            repo / ".agentic-framework" / "native-delivery" / "verdict.json"
        )
        # Scoped 基线在动代码前冻结（S0 无残留，范围只允许 code.py）。
        snapshot = workspace_residue.capture_workspace_residue(
            repo, "", ["code.py"], backend="svn"
        )
        baseline = repo / ".agentic-framework" / "verify" / "baseline.json"
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(
            json.dumps({"workspace_residue_snapshot": snapshot}),
            encoding="utf-8",
        )

        # 1) 本地改动 → 真实 v2 Verify（Task 11 的纯 SVN 主体绑定）。
        (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
        with _chdir(repo):
            code = _verify_main(
                [
                    "--report", str(verify_report),
                    "--spec-drift-reason", "集成链验证：规格正文已引用 code.py",
                ]
            )
        self.assertEqual(0, code)
        pending = json.loads(verify_report.read_text(encoding="utf-8"))
        self.assertEqual(2, pending["schema_version"])
        review.parent.mkdir(parents=True, exist_ok=True)
        review.write_text(
            json.dumps(_review_report(pending["subject_id"])), encoding="utf-8"
        )

        # 2) 无授权：交付门产出待提交，且链路不执行任何 SVN 写命令。
        spy, commands = _no_server_write_spy()
        with spy:
            code, output = _gate(
                self._gate_args(repo, review, verify_report, verdict)
            )
        self.assertEqual(0, code, output)
        result = json.loads(verdict.read_text(encoding="utf-8"))
        self.assertEqual("svn-pending-commit", result["verdict"])
        self.assertIn("不是正式交付 PASS", output)
        _assert_no_svn_writes(self, commands)
        verdict.unlink()

        # 3) 他人不同文件提交（竞态）+ 自有提交。提交前报告主体过旧——该拒收
        # 机制由 test_check_delivery 的 stale 场景定点覆盖，此处直接走重新取证。
        (teammate / "other.txt").write_text("teammate\n", encoding="utf-8")
        _svn(teammate, "add", "other.txt")
        _svn(teammate, "commit", "--force-log", "-m", "teammate")
        _svn(repo, "commit", "--force-log", "-m", "deliver")
        _svn(repo, "update")
        revision = subprocess.run(
            ["svn", "info", "--non-interactive", "--show-item", "revision"],
            cwd=str(repo), check=True, capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        ).stdout.strip()
        self.assertGreaterEqual(int(revision), 3)

        # 4) 对确切 revision 重新取证（真实 Verify）后正式交付。
        with _chdir(repo):
            code = _verify_main(
                [
                    "--report", str(verify_report),
                    "--spec-drift-reason", "集成链验证：规格正文已引用 code.py",
                ]
            )
        self.assertEqual(0, code)
        verified = json.loads(verify_report.read_text(encoding="utf-8"))
        self.assertNotEqual(pending["subject_id"], verified["subject_id"])
        review.write_text(
            json.dumps(_review_report(verified["subject_id"])),
            encoding="utf-8",
        )
        spy, commands = _no_server_write_spy()
        with spy:
            code, output = _gate(
                self._gate_args(
                    repo, review, verify_report, verdict, revision=revision
                )
            )
        self.assertEqual(0, code, output)
        result = json.loads(verdict.read_text(encoding="utf-8"))
        self.assertEqual("svn-revision-verified", result["verdict"])
        self.assertEqual(int(revision), result["evidence"]["revision"])
        self.assertEqual(
            result["subject_id"], result["evidence"]["revision_subject_id"]
        )
        self.assertIn(f"正式交付 revision：r{revision}", output)
        self.assertIn("本次交付范围干净，预存残留未变化", output)
        _assert_no_svn_writes(self, commands)


if __name__ == "__main__":
    unittest.main()
