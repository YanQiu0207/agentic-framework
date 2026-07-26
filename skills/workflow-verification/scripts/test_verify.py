"""Regression tests for spec drift evaluation."""

import contextlib
import io
import json
import os
import shlex
import signal
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


def _force_kill_process_group(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _cleanup_runner(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    _force_kill_process_group(process.pid)
    try:
        process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        process.kill()


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
        raise subprocess.TimeoutExpired(
            "fake-command", timeout, output=self.stdout, stderr=self.stderr
        )


class CommandDiagnosticsTest(unittest.TestCase):
    """Verify bounded command diagnostics without slowing normal checks."""

    def test_evaluate_check_uses_default_timeout_with_headroom(self) -> None:
        with mock.patch.object(
            verify, "run_command", return_value=(0, "", "")
        ) as run_command:
            result = verify.evaluate_check(
                {
                    "name": "default-timeout",
                    "type": "forbid_pattern",
                    "command": "scan",
                },
                baseline=None,
            )

        self.assertEqual("pass", result.status)
        run_command.assert_called_once_with(
            "scan", timeout=120, check_name="default-timeout"
        )

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

    def test_timeout_cleanup_has_hard_deadline_and_closes_stuck_pipes(self) -> None:
        source = f"""
import json
import subprocess
import sys
import time
from unittest import mock
sys.path.insert(0, {str(Path(verify.__file__).parent)!r})
import verify

class Pipe:
    def __init__(self):
        self.closed = False
    def close(self):
        self.closed = True

class Process:
    pid = 4321
    returncode = None
    def __init__(self):
        self.stdout = Pipe()
        self.stderr = Pipe()
        self.killed = False
    def communicate(self, timeout=None):
        if timeout is None:
            time.sleep(60)
            return "", ""
        time.sleep(timeout)
        raise subprocess.TimeoutExpired(
            "fake-command", timeout, output="partial-out", stderr="partial-err"
        )
    def kill(self):
        self.killed = True
    def wait(self, timeout=None):
        raise subprocess.TimeoutExpired("fake-command", timeout)

process = Process()
verify._PROCESS_CLEANUP_TIMEOUT_SECONDS = 0.2
with mock.patch.object(
    verify.subprocess, "Popen", return_value=process
), mock.patch.object(verify, "_kill_process_tree", return_value=False):
    try:
        verify.run_command(
            "stuck-cleanup", timeout=0.05, check_name="stuck-cleanup",
            heartbeat_seconds=0.05
        )
    except verify.CommandTimeout as error:
        print(json.dumps({{
            "cleanup_complete": error.cleanup_complete,
            "stdout_closed": process.stdout.closed,
            "stderr_closed": process.stderr.closed,
            "killed": process.killed,
            "message": str(error),
        }}))
"""
        process_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "encoding": "utf-8",
            "env": {
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        }
        if os.name == "nt":
            process_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            process_kwargs["start_new_session"] = True
        runner = subprocess.Popen([sys.executable, "-c", source], **process_kwargs)
        try:
            try:
                stdout, stderr = runner.communicate(timeout=3)
            except subprocess.TimeoutExpired as error:
                self.fail(f"verification cleanup exceeded outer hard deadline: {error}")
            self.assertEqual(0, runner.returncode, stderr)
            result = json.loads(stdout)
            self.assertFalse(result["cleanup_complete"])
            self.assertTrue(result["stdout_closed"])
            self.assertTrue(result["stderr_closed"])
            self.assertTrue(result["killed"])
            self.assertIn("清理不完整", result["message"])
        finally:
            _cleanup_runner(runner)

    def test_windows_taskkill_failure_falls_back_to_direct_kill(self) -> None:
        process = mock.Mock(pid=4321)
        process.poll.return_value = None
        completed = subprocess.CompletedProcess([], returncode=1)
        with mock.patch.object(verify.sys, "platform", "win32"), mock.patch.object(
            verify.subprocess, "run", return_value=completed
        ) as run:
            tree_terminated = verify._kill_process_tree(process, timeout=0.25)

        self.assertFalse(tree_terminated)
        process.kill.assert_called_once_with()
        run.assert_called_once_with(
            ["taskkill", "/F", "/T", "/PID", "4321"],
            capture_output=True,
            timeout=0.25,
            check=False,
        )

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

    def test_glob_match_supports_star_question_and_double_star(self) -> None:
        self.assertTrue(verify._glob_match("src/tool.py", ["*.py"]))
        self.assertTrue(verify._glob_match("a/b/c.py", ["a/*"]))
        self.assertTrue(verify._glob_match("a/b/c.py", ["**/c.py"]))
        self.assertTrue(verify._glob_match("x.py", ["x?py"]))
        self.assertFalse(verify._glob_match("src/tool.txt", ["*.py"]))
        self.assertFalse(verify._glob_match("any", []))

    def test_glob_match_directory_prefix_covers_beneath(self) -> None:
        self.assertTrue(verify._glob_match("local/debug.py", ["local/"]))
        self.assertTrue(verify._glob_match("local/debug.py", ["local"]))
        self.assertFalse(verify._glob_match("localism/debug.py", ["local/"]))

    def test_evaluate_spec_drift_records_ignore_sources(self) -> None:
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=(["local/a.py", "local/b.py"], [], None),
        ):
            result = verify.evaluate_spec_drift(
                "HEAD",
                "",
                ["local/a.py"],  # cli
                ["local/b*"],  # config
                ["local/c.py"],  # baseline (not in changes)
            )
        self.assertEqual(
            ["local/a.py", "local/b.py"], result.value["ignored_files"]
        )
        self.assertEqual(["cli"], result.value["ignore_sources"]["local/a.py"])
        self.assertEqual(["config"], result.value["ignore_sources"]["local/b.py"])

    def test_evaluate_spec_drift_ignores_matched_code_file(self) -> None:
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=(["local/debug.py"], [], None),
        ):
            result = verify.evaluate_spec_drift("HEAD", "", ["local/"])
        self.assertEqual("pass", result.status)
        self.assertEqual(["local/debug.py"], result.value["ignored_files"])
        self.assertEqual([], result.value["code_files"])

    def test_evaluate_spec_drift_refuses_ignoring_spec_file(self) -> None:
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=(["openspec/changes/x/tasks.md"], [], None),
        ):
            result = verify.evaluate_spec_drift(
                "HEAD", "", ["openspec/changes/x/tasks.md"]
            )
        self.assertEqual(
            ["openspec/changes/x/tasks.md"], result.value["refused_ignores"]
        )
        self.assertEqual(
            ["openspec/changes/x/tasks.md"], result.value["spec_files"]
        )

    def test_cmd_verify_fails_closed_when_baseline_missing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            baseline.write_text(
                json.dumps({"checks": {}, "config_snapshot": [], "ignore_paths_snapshot": []}),
                encoding="utf-8",
            )
            with mock.patch.object(
                verify, "load_config", return_value={"checks": []}
            ), mock.patch("builtins.print"):
                rc = verify.cmd_verify(
                    {"checks": []},
                    baseline,
                    Path(temp_dir) / "report.json",
                    "HEAD",
                    "",
                )
        self.assertEqual(2, rc)

    def test_baseline_paths_match_literally_not_as_glob(self) -> None:
        # P2-1: baseline paths are exact set membership, NOT glob — a filename
        # containing glob metacharacters must match itself and not be interpreted.
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=(["docs/v1.0[draft].md"], [], None),
        ):
            result = verify.evaluate_spec_drift(
                "HEAD", "", [], [], ["docs/v1.0[draft].md"]
            )
        self.assertEqual(
            ["docs/v1.0[draft].md"], result.value["ignored_files"]
        )

    def test_cmd_verify_forwards_three_ignore_sources(self) -> None:
        # P2-4: cmd_verify wires CLI, config and baseline sources through to
        # evaluate_spec_drift end-to-end.
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": [],
                        "ignore_paths_snapshot": ["cfg/*.py"],
                        "changed_files_snapshot": ["pre-existing.py"],
                    }
                ),
                encoding="utf-8",
            )
            config = {"checks": [], "ignore_paths": ["cfg/*.py"]}
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult("Z", "spec_drift", "pass", ""),
            ) as spy, mock.patch.object(
                verify, "evaluate_check"
            ), mock.patch("builtins.print"):
                verify.cmd_verify(
                    config,
                    baseline,
                    Path(temp_dir) / "report.json",
                    "HEAD",
                    "",
                    cli_ignore_patterns=["cli.py"],
                )
        positional = spy.call_args.args
        # diff_base, reason, cli_patterns, config_patterns, baseline_paths
        self.assertEqual(["cli.py"], positional[2])
        self.assertEqual(["cfg/*.py"], positional[3])
        self.assertEqual(["pre-existing.py"], positional[4])

    def test_changing_ignore_paths_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config_v1 = {"checks": [], "ignore_paths": ["a/*.py"]}
            config_v2 = {"checks": [], "ignore_paths": ["b/*.py"]}
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": verify._config_snapshot(config_v1),
                        "ignore_paths_snapshot": ["a/*.py"],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with mock.patch.object(
                verify, "evaluate_check"
            ) as evaluate_check, contextlib.redirect_stderr(stderr):
                rc = verify.cmd_verify(
                    config_v2,
                    baseline,
                    Path(temp_dir) / "report.json",
                    "HEAD",
                    "",
                )

        self.assertEqual(2, rc)
        evaluate_check.assert_not_called()
        self.assertIn("ignore_paths 配置已变更", stderr.getvalue())


class ConfigSnapshotTest(unittest.TestCase):
    """Protect the implementation-period append-only configuration exception."""

    def test_cmd_save_baseline_snapshots_ignore_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config = {"checks": [], "ignore_paths": ["generated/**"]}
            with mock.patch.object(
                verify, "_changed_files", return_value=([], [], None)
            ), mock.patch("builtins.print"):
                rc = verify.cmd_save_baseline(config, baseline)

            payload = json.loads(baseline.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual(["generated/**"], payload["ignore_paths_snapshot"])

    def test_cmd_verify_rejects_baseline_without_ignore_paths_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": [],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = verify.cmd_verify(
                    {"checks": []},
                    baseline,
                    Path(temp_dir) / "report.json",
                    "HEAD",
                    "",
                )

        self.assertEqual(2, rc)
        self.assertIn("ignore_paths_snapshot", stderr.getvalue())

    def test_cmd_verify_rejects_changed_existing_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config_v1 = {
                "checks": [
                    {
                        "name": "existing-test-entry",
                        "type": "exit_code",
                        "command": _python_command("print('existing')"),
                        "baseline_aware": False,
                    }
                ]
            }
            config_v2 = {
                "checks": [
                    {
                        "name": "existing-test-entry",
                        "type": "exit_code",
                        "command": _python_command("print('changed')"),
                        "baseline_aware": False,
                    }
                ]
            }
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": verify._config_snapshot(config_v1),
                        "ignore_paths_snapshot": [],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with mock.patch.object(verify, "evaluate_check") as evaluate_check, contextlib.redirect_stderr(
                stderr
            ):
                rc = verify.cmd_verify(
                    config_v2, baseline, Path(temp_dir) / "report.json", "HEAD", ""
                )

        self.assertEqual(2, rc)
        evaluate_check.assert_not_called()
        self.assertIn("配置已变更", stderr.getvalue())

    def test_cmd_verify_allows_new_nonbaseline_check_without_rebaseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config_v1 = {"checks": []}
            config_v2 = {
                "checks": [
                    {
                        "name": "new-test-entry",
                        "type": "exit_code",
                        "command": _python_command("print('new entry')"),
                        "baseline_aware": False,
                        "_note": "本次实现新增测试入口；已在当前工作区试运行成功。",
                    }
                ]
            }
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": verify._config_snapshot(config_v1),
                        "ignore_paths_snapshot": [],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            report = Path(temp_dir) / "report.json"
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult("Z", "spec_drift", "pass", ""),
            ), mock.patch.object(verify, "knowledge_source_warnings", return_value=[]):
                rc = verify.cmd_verify(config_v2, baseline, report, "HEAD", "")

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual("PASS", payload["verdict"])
        self.assertEqual("new-test-entry", payload["results"][1]["name"])
        self.assertEqual("pass", payload["results"][1]["status"])

    def test_cmd_verify_rejects_new_baseline_aware_check_without_rebaseline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config_v1 = {"checks": []}
            config_v2 = {
                "checks": [
                    {
                        "name": "new-baseline-entry",
                        "type": "exit_code",
                        "command": _python_command("raise SystemExit(99)"),
                        "baseline_aware": True,
                    }
                ]
            }
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": verify._config_snapshot(config_v1),
                        "ignore_paths_snapshot": [],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with mock.patch.object(
                verify, "evaluate_check"
            ) as evaluate_check, contextlib.redirect_stderr(stderr):
                rc = verify.cmd_verify(
                    config_v2, baseline, Path(temp_dir) / "report.json", "HEAD", ""
                )

        self.assertEqual(2, rc)
        evaluate_check.assert_not_called()
        self.assertIn("必须显式设置 baseline_aware: false", stderr.getvalue())

    def test_cmd_verify_requires_explicit_nonbaseline_flag_and_note_for_new_check(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            config_v1 = {"checks": []}
            baseline.write_text(
                json.dumps(
                    {
                        "checks": {},
                        "config_snapshot": verify._config_snapshot(config_v1),
                        "ignore_paths_snapshot": [],
                        "changed_files_snapshot": [],
                    }
                ),
                encoding="utf-8",
            )
            cases = [
                (
                    {
                        "name": "missing-nonbaseline-flag",
                        "type": "exit_code",
                        "command": _python_command("raise SystemExit(99)"),
                        "_note": "有试运行记录，但缺少显式非基线标记。",
                    },
                    "必须显式设置 baseline_aware: false",
                ),
                (
                    {
                        "name": "missing-new-entry-note",
                        "type": "exit_code",
                        "command": _python_command("raise SystemExit(99)"),
                        "baseline_aware": False,
                    },
                    "缺少非空 _note",
                ),
            ]
            for check, expected in cases:
                with self.subTest(name=check["name"]):
                    stderr = io.StringIO()
                    with mock.patch.object(
                        verify, "evaluate_check"
                    ) as evaluate_check, contextlib.redirect_stderr(stderr):
                        rc = verify.cmd_verify(
                            {"checks": [check]},
                            baseline,
                            Path(temp_dir) / f"{check['name']}.json",
                            "HEAD",
                            "",
                        )

                    self.assertEqual(2, rc)
                    evaluate_check.assert_not_called()
                    self.assertIn(expected, stderr.getvalue())


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

    def test_verify_paths_write_new_and_read_legacy_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / ".verify" / "baseline.json"
            legacy.parent.mkdir()
            legacy.write_text('{"legacy": true}\n', encoding="utf-8")
            before = legacy.read_text(encoding="utf-8")

            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                read_path = verify.resolve_verify_read_path(
                    Path(".agentic-framework/verify/baseline.json"), root
                )
                write_path = verify.resolve_verify_write_path(
                    Path(".verify/report.json"), root
                )

            self.assertEqual(legacy, read_path)
            self.assertEqual(
                root / ".agentic-framework" / "verify" / "report.json",
                write_path,
            )
            self.assertEqual(before, legacy.read_text(encoding="utf-8"))
            self.assertIn("仅兼容读取", stderr.getvalue())

    def test_main_defaults_report_to_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch.object(verify, "load_config", return_value={}), mock.patch.object(
                    verify, "cmd_verify", return_value=0
                ) as cmd_verify:
                    self.assertEqual(0, verify.main([]))
            finally:
                os.chdir(old_cwd)

            self.assertEqual(
                root / ".agentic-framework" / "verify" / "report.json",
                cmd_verify.call_args.args[2],
            )

    def test_cmd_verify_emits_bound_runtime_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "verify-1-1.json"
            context = {
                "run_id": "run-1",
                "profile": "tooling",
                "harness": "codex",
                "commit_sha": "1" * 40,
                "config_digest": "sha256:" + "2" * 64,
            }
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult(
                    "spec-drift", "spec_drift", "pass", "ok"
                ),
            ), mock.patch.object(
                verify, "knowledge_source_warnings", return_value=[]
            ), mock.patch("builtins.print"):
                result = verify.cmd_verify(
                    {}, None, report, "HEAD", "", context, "1", 1
                )
            value = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual("verify-report", value["artifact_type"])
        self.assertEqual("run-1", value["run_id"])
        self.assertEqual("1", value["task_id"])
        self.assertEqual("PASS", value["payload"]["verdict"])
        self.assertNotIn("verdict", value)

    def test_cmd_verify_emits_bound_run_level_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "verify-run.json"
            context = {
                "run_id": "run-1",
                "profile": "tooling",
                "harness": "codex",
                "commit_sha": "1" * 40,
                "config_digest": "sha256:" + "2" * 64,
            }
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult(
                    "spec-drift", "spec_drift", "pass", "ok"
                ),
            ), mock.patch.object(
                verify, "knowledge_source_warnings", return_value=[]
            ), mock.patch("builtins.print"):
                result = verify.cmd_verify(
                    {}, None, report, "HEAD", "", context
                )
            value = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual("verify-run", value["artifact_id"])
        self.assertIsNone(value["task_id"])
        self.assertIsNone(value["attempt"])


class SvnSupportTest(unittest.TestCase):
    """SVN spec-drift file list and source_ref freshness."""

    def test_svn_status_splits_tracked_and_untracked(self) -> None:
        lines = [
            "M       src/tool.py",
            "A       src/new.py",
            "?       untracked.txt",
            "I       ignored.log",
        ]

        def svn_lines(args: list[str]) -> tuple[int, list[str], str]:
            return 0, lines, ""

        with mock.patch.object(verify, "_svn_lines", side_effect=svn_lines):
            tracked, untracked, err = verify._svn_status_changes()

        self.assertIsNone(err)
        self.assertEqual(["src/new.py", "src/tool.py"], tracked)
        self.assertEqual(["untracked.txt"], untracked)

    def test_svn_status_preserves_paths_with_spaces(self) -> None:
        """Regression for P1-1：含空格路径不得被分词截断。"""
        lines = [
            "M       src/my module/tool.py",
            "?       untracked dir/note.md",
        ]

        def svn_lines(args: list[str]) -> tuple[int, list[str], str]:
            return 0, lines, ""

        with mock.patch.object(verify, "_svn_lines", side_effect=svn_lines):
            tracked, untracked, err = verify._svn_status_changes()

        self.assertIsNone(err)
        self.assertEqual(["src/my module/tool.py"], tracked)
        self.assertEqual(["untracked dir/note.md"], untracked)

    def test_svn_status_skips_noise_and_property_rows(self) -> None:
        """externals 提示行 / X / ! / ~ / 属性行不计入 tracked（白名单）。

        在 subprocess.run 层打桩，让真实 `_svn_lines`（含前导空白保留逻辑）参与执行，
        防止属性行 ` M file` 被 strip 成 `M file` 后误计入 tracked（NF-1 回归）。
        """
        stdout = (
            "M       src/real.py\n"
            "Performing status on external at 'vendor':\n"
            "X       vendor\n"
            "!       src/missing.py\n"
            "~       src/obstructed.py\n"
            " M      src/prop-only.py\n"
            "I       ignored.log\n"
        )
        completed = subprocess.CompletedProcess(
            args=["svn", "status"], returncode=0, stdout=stdout, stderr=""
        )
        with mock.patch.object(verify.subprocess, "run", return_value=completed):
            tracked, untracked, err = verify._svn_status_changes()

        self.assertIsNone(err)
        self.assertEqual(["src/real.py"], tracked)
        self.assertEqual([], untracked)

    def test_changed_files_dispatches_to_svn_when_svn_working_copy(self) -> None:
        with mock.patch.object(verify, "_detect_vcs", return_value="svn"), mock.patch.object(
            verify,
            "_svn_status_changes",
            return_value=(["src/a.py"], ["b.txt"], None),
        ):
            tracked, untracked, err = verify._changed_files("HEAD")
        self.assertIsNone(err)
        self.assertEqual(["src/a.py"], tracked)
        self.assertEqual(["b.txt"], untracked)

    def test_svn_source_ref_fresh_has_no_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "src" / "tool.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('v1')\n", encoding="utf-8")
            responses = {
                ("info", "--show-item", "revision", "-r", "10"): (0, "10"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "src/tool.py",
                ): (0, "5"),
            }

            def svn_result(_repo: Path, args: list[str]) -> tuple[int, str]:
                return responses[tuple(args)]

            with mock.patch.object(verify, "_svn_result", side_effect=svn_result):
                warnings = verify._svn_source_warnings(
                    "meta.yaml", "svn:10", ["src/tool.py"], repo, {}, {}, {}
                )
        self.assertEqual([], warnings)

    def test_svn_source_ref_stale_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "src" / "tool.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('v1')\n", encoding="utf-8")
            responses = {
                ("info", "--show-item", "revision", "-r", "10"): (0, "10"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "src/tool.py",
                ): (0, "15"),
            }

            def svn_result(_repo: Path, args: list[str]) -> tuple[int, str]:
                return responses[tuple(args)]

            with mock.patch.object(verify, "_svn_result", side_effect=svn_result):
                warnings = verify._svn_source_warnings(
                    "meta.yaml", "svn:10", ["src/tool.py"], repo, {}, {}, {}
                )
        self.assertEqual(1, len(warnings))
        self.assertIn("来源已晚于", warnings[0])

    def test_svn_source_ref_missing_rev_warns(self) -> None:
        with mock.patch.object(verify, "_svn_result", return_value=(1, "")):
            warnings = verify._svn_source_warnings(
                "meta.yaml",
                "svn:999",
                ["src/tool.py"],
                Path("/fake/repo"),
                {},
                {},
                {},
            )
        self.assertEqual(1, len(warnings))
        self.assertIn("不存在", warnings[0])

    def test_knowledge_source_warnings_routes_svn_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "scripts" / "tool.py"
            source.parent.mkdir()
            source.write_text("print('v1')\n", encoding="utf-8")
            meta = repo / "openspec" / "specs" / "tool" / "meta.yaml"
            meta.parent.mkdir(parents=True)
            meta.write_text(
                "service:\n"
                "    source_ref: svn:10\n"
                "    source_paths:\n"
                "        - scripts/tool.py\n",
                encoding="utf-8",
            )
            responses = {
                ("info", "--show-item", "revision", "-r", "10"): (0, "10"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "scripts/tool.py",
                ): (0, "5"),
            }

            def svn_result(_repo: Path, args: list[str]) -> tuple[int, str]:
                return responses[tuple(args)]

            with mock.patch.object(verify, "_svn_result", side_effect=svn_result):
                warnings = verify.knowledge_source_warnings(repo)
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()


class ScopedBaselineTest(unittest.TestCase):
    """Scoped Delivery 的 S0 必须独立、可写入且失败不覆盖。"""

    def test_save_baseline_stores_workspace_residue_snapshot(self) -> None:
        snapshot = {
            "version": 1,
            "vcs": "git",
            "base_ref": "a" * 40,
            "scope_paths": ["scripts"],
            "entries": [],
            "residue_digest": "sha256:" + "0" * 64,
            "snapshot_digest": "sha256:" + "1" * 64,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            with mock.patch.object(
                verify, "_changed_files", return_value=([], [], None)
            ), mock.patch.object(
                verify, "capture_workspace_residue", return_value=snapshot
            ):
                result = verify.cmd_save_baseline(
                    {"checks": []}, baseline, "HEAD", ["scripts"]
                )
            stored = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertEqual(0, result)
        self.assertEqual(snapshot, stored["workspace_residue_snapshot"])
        self.assertEqual([], stored["changed_files_snapshot"])

    def test_save_baseline_does_not_overwrite_on_scope_snapshot_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            baseline.write_text('{"preserve": true}', encoding="utf-8")
            with mock.patch.object(
                verify, "_changed_files", return_value=([], [], None)
            ), mock.patch.object(
                verify,
                "capture_workspace_residue",
                side_effect=verify.WorkspaceResidueError("范围重叠"),
            ), contextlib.redirect_stderr(io.StringIO()):
                result = verify.cmd_save_baseline(
                    {"checks": []}, baseline, "HEAD", ["scripts"]
                )
            content = baseline.read_text(encoding="utf-8")
        self.assertEqual(2, result)
        self.assertEqual('{"preserve": true}', content)
