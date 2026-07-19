"""Regression tests for spec drift evaluation."""

import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify


def _python_command(source: str) -> str:
    arguments = [sys.executable, "-c", source]
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


class _FakeProcess:
    pid = 4321

    def __init__(
        self,
        clock: _FakeClock,
        finish_at: float,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.clock = clock
        self.finish_at = finish_at
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        if timeout is None:
            return self.stdout, self.stderr
        finish_in = self.finish_at - self.clock.now
        if finish_in <= timeout:
            self.clock.now += max(0.0, finish_in)
            return self.stdout, self.stderr
        self.clock.now += timeout
        raise subprocess.TimeoutExpired("fake-command", timeout)


class CommandDiagnosticsTest(unittest.TestCase):
    """Verify bounded command diagnostics without slowing normal checks."""

    def test_child_process_receives_forced_utf8_environment(self) -> None:
        command = _python_command(
            "import json,os; print(json.dumps({"
            "'PYTHONUTF8': os.environ.get('PYTHONUTF8'),"
            "'PYTHONIOENCODING': os.environ.get('PYTHONIOENCODING')}))"
        )
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics):
            returncode, stdout, stderr = verify.run_command(
                command,
                timeout=10,
                check_name="utf8-environment",
            )
        self.assertEqual(0, returncode)
        self.assertEqual("", stderr)
        self.assertEqual(
            {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            json.loads(stdout),
        )

    def test_short_command_logs_start_and_end_without_heartbeat(self) -> None:
        clock = _FakeClock()
        process = _FakeProcess(clock, finish_at=0.1, stdout="ok\n")
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics), mock.patch.object(
            verify.subprocess, "Popen", return_value=process
        ), mock.patch.object(verify.time, "monotonic", side_effect=clock.monotonic):
            returncode, stdout, stderr = verify.run_command(
                "short-command",
                timeout=5,
                check_name="short-check",
            )
        log = diagnostics.getvalue()
        self.assertEqual(0, returncode)
        self.assertEqual("ok", stdout.strip())
        self.assertEqual("", stderr)
        self.assertIn("start check='short-check' pid=", log)
        self.assertIn("command=", log)
        self.assertIn("end check='short-check'", log)
        self.assertIn("exit=0", log)
        self.assertIn("timeout=5s", log)
        self.assertNotIn("heartbeat", log)

    def test_long_command_emits_bounded_heartbeats(self) -> None:
        clock = _FakeClock()
        process = _FakeProcess(clock, finish_at=11.0)
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics), mock.patch.object(
            verify.subprocess, "Popen", return_value=process
        ), mock.patch.object(verify.time, "monotonic", side_effect=clock.monotonic):
            verify.run_command(
                "long-command",
                timeout=20,
                check_name="heartbeat-check",
                heartbeat_seconds=5,
            )
        heartbeats = [
            line
            for line in diagnostics.getvalue().splitlines()
            if " heartbeat check=" in line
        ]
        self.assertEqual(2, len(heartbeats))
        self.assertTrue(all("elapsed=" in line for line in heartbeats))

    def test_timeout_logs_and_preserves_stdout_stderr_summary(self) -> None:
        clock = _FakeClock()
        process = _FakeProcess(
            clock,
            finish_at=100.0,
            stdout="before-out\n",
            stderr="before-err\n",
        )
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics), mock.patch.object(
            verify.subprocess, "Popen", return_value=process
        ), mock.patch.object(
            verify.time, "monotonic", side_effect=clock.monotonic
        ), mock.patch.object(
            verify, "_kill_process_tree"
        ):
            with self.assertRaises(verify.CommandTimeout) as caught:
                verify.run_command(
                    "timeout-command",
                    timeout=10,
                    check_name="timeout-check",
                )
        log = diagnostics.getvalue()
        self.assertIn("exit=TIMEOUT", log)
        self.assertIn("elapsed=", log)
        self.assertIn("timeout=10s", log)
        self.assertIn("stdout=before-out", log)
        self.assertIn("stderr=before-err", log)
        self.assertIn("stdout=before-out", str(caught.exception))
        self.assertIn("stderr=before-err", str(caught.exception))

    def test_nonzero_exit_logs_stdout_stderr_summary(self) -> None:
        clock = _FakeClock()
        process = _FakeProcess(
            clock,
            finish_at=0.1,
            returncode=3,
            stdout="failed-out\n",
            stderr="failed-err\n",
        )
        diagnostics = io.StringIO()
        with contextlib.redirect_stderr(diagnostics), mock.patch.object(
            verify.subprocess, "Popen", return_value=process
        ), mock.patch.object(verify.time, "monotonic", side_effect=clock.monotonic):
            returncode, _, _ = verify.run_command(
                "failed-command",
                timeout=2,
                check_name="failed-check",
            )
        log = diagnostics.getvalue()
        self.assertEqual(3, returncode)
        self.assertIn("exit=3", log)
        self.assertIn("stdout=failed-out", log)
        self.assertIn("stderr=failed-err", log)


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


class KnowledgeSourceFreshnessTest(unittest.TestCase):
    """Verify generated knowledge source metadata without blocking delivery."""

    def _repo(self, temp_dir: str) -> Path:
        repo = Path(temp_dir)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", "Test"],
            check=True,
        )
        return repo

    def _commit(self, repo: Path, message: str) -> str:
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", message],
            check=True,
        )
        return subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_current_source_ref_has_no_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            source = repo / "scripts" / "tool.py"
            source.parent.mkdir()
            source.write_text("print('v1')\n", encoding="utf-8")
            generated_at = self._commit(repo, "source")
            meta = repo / "openspec" / "specs" / "tool" / "meta.yaml"
            meta.parent.mkdir(parents=True)
            meta.write_text(
                "service:\n"
                f"    source_ref: git:{generated_at}\n"
                "    source_paths:\n"
                "        - scripts/tool.py\n",
                encoding="utf-8",
            )

            self.assertEqual([], verify.knowledge_source_warnings(repo))

    def test_newer_source_change_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            source = repo / "scripts" / "tool.py"
            source.parent.mkdir()
            source.write_text("print('v1')\n", encoding="utf-8")
            generated_at = self._commit(repo, "source")
            meta = repo / "openspec" / "specs" / "tool" / "meta.yaml"
            meta.parent.mkdir(parents=True)
            meta.write_text(
                "service:\n"
                f"    source_ref: git:{generated_at}\n"
                "    source_paths:\n"
                "        - scripts/tool.py\n",
                encoding="utf-8",
            )
            self._commit(repo, "meta")
            source.write_text("print('v2')\n", encoding="utf-8")
            self._commit(repo, "source update")

            warnings = verify.knowledge_source_warnings(repo)

        self.assertEqual(1, len(warnings))
        self.assertIn("来源已晚于", warnings[0])

    def test_duplicate_metadata_reuses_git_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "scripts" / "tool.py"
            source.parent.mkdir()
            source.write_text("print('ok')\n", encoding="utf-8")
            for service in ("a", "b"):
                meta = repo / "openspec" / "specs" / service / "meta.yaml"
                meta.parent.mkdir(parents=True)
                meta.write_text(
                    "service:\n"
                    "    source_ref: git:abc1234\n"
                    "    source_paths:\n"
                    "        - scripts/tool.py\n",
                    encoding="utf-8",
                )
            responses = {
                "rev-parse": (0, "abc1234"),
                "log": (0, "abc1234"),
                "merge-base": (0, ""),
            }

            def git_result(_repo: Path, args: list[str]) -> tuple[int, str]:
                return responses[args[0]]

            with mock.patch.object(
                verify, "_git_result", side_effect=git_result
            ) as git_result_mock:
                self.assertEqual([], verify.knowledge_source_warnings(repo))

        self.assertEqual(3, git_result_mock.call_count)

    def test_cmd_verify_keeps_source_warning_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self._repo(temp_dir)
            source = repo / "scripts" / "tool.py"
            source.parent.mkdir()
            source.write_text("print('v1')\n", encoding="utf-8")
            generated_at = self._commit(repo, "source")
            meta = repo / "openspec" / "specs" / "tool" / "meta.yaml"
            meta.parent.mkdir(parents=True)
            meta.write_text(
                "service:\n"
                f"    source_ref: git:{generated_at}\n"
                "    source_paths:\n"
                "        - scripts/tool.py\n",
                encoding="utf-8",
            )
            self._commit(repo, "meta")
            source.write_text("print('v2')\n", encoding="utf-8")
            self._commit(repo, "source update")
            report = repo / "report.json"
            old_cwd = Path.cwd()
            try:
                import os

                os.chdir(repo)
                with mock.patch("builtins.print"):
                    result = verify.cmd_verify({}, None, report, "HEAD", "")
            finally:
                os.chdir(old_cwd)

            payload = __import__("json").loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual("PASS", payload["verdict"])
        self.assertEqual(1, len(payload["warnings"]))


if __name__ == "__main__":
    unittest.main()
