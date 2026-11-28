"""Regression tests for spec drift evaluation and standalone v2 binding."""

import contextlib
import io
import json
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

import verify

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from native_delivery import validate_verify_report as validate_native_report
from scripts.test_vcs import command, head, repository, svn_pair


def _python_command(source: str) -> str:
    arguments = [sys.executable, "-c", source]
    if os.name == "nt":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


_STABLE_CAPTURE = {
    "subject_id": "sha256:" + "1" * 64,
    "complete": True,
    "limitations": [],
    "entries": [],
}
_STABLE_COMPARISON = {
    "unchanged": True,
    "complete": True,
    "verified": True,
    "limitations": [],
}


def _stable_subject_patches():
    """Bypass real VCS capture for tests targeting unrelated guard logic."""
    return (
        mock.patch.object(
            verify, "_capture_verify_subject", return_value=dict(_STABLE_CAPTURE)
        ),
        mock.patch.object(
            verify,
            "compare_native_subjects",
            return_value=dict(_STABLE_COMPARISON),
        ),
        mock.patch.object(verify, "_config_matches_subject", return_value=True),
    )


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
                return_value=("git", [], ["src/tool.py", "docs/tasks.md"], None),
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
            return_value=("git", [], ["src/tool.py", "other/spec.md"], None),
        ):
            result = verify.evaluate_spec_drift("HEAD", "")
        self.assertEqual("fail", result.status)

    def test_proposal_and_design_files_classify_as_spec(self) -> None:
        """现行产物名 proposal.md / design.md 按文件名任意目录命中规格类。"""
        self.assertTrue(verify._is_spec_file("openspec/changes/add-tool/proposal.md"))
        self.assertTrue(verify._is_spec_file("openspec/changes/add-tool/design.md"))
        # 文件名命中不受目录限制（与 spec.md / tasks.md 口径一致）
        self.assertTrue(verify._is_spec_file("docs/notes/design.md"))
        self.assertFalse(verify._is_code_file("openspec/changes/add-tool/proposal.md"))

    def test_change_delta_markdown_classifies_as_spec(self) -> None:
        """openspec/changes/ 下其余 .md（Delta 等）必须被认作规格类文件。"""
        self.assertTrue(verify._is_spec_file("openspec/changes/add-tool/specs/api/tool.md"))
        self.assertTrue(verify._is_spec_file("openspec/changes/add-tool/notes.md"))
        self.assertFalse(verify._is_spec_file("openspec/other/specs/api/tool.md"))
        self.assertFalse(verify._is_spec_file("changes/add-tool/specs/api/tool.md"))

    def test_adr_with_code_path_proves_related_update(self) -> None:
        """ADR 正文引用改动代码路径时必须计入 related（修复前永不计入）。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adr = root / "docs/adr/0001-tool.md"
            adr.parent.mkdir(parents=True)
            adr.write_text("决策：src/tool.py 改用连接池。\n", encoding="utf-8")
            related = verify._related_spec_files(
                ["src/tool.py"], [str(adr)]
            )
        self.assertEqual([str(adr)], related)

    def test_proposal_with_code_path_can_prove_related_update(self) -> None:
        """proposal / design 正文引用改动代码路径即可通过 spec drift。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            change = root / "openspec/changes/add-tool"
            change.mkdir(parents=True)
            (change / "proposal.md").write_text(
                "## 1. 背景\n改动 src/tool.py\n", encoding="utf-8"
            )
            (change / "design.md").write_text(
                "## 4. 设计方案\n涉及 src/tool.py\n", encoding="utf-8"
            )
            with mock.patch.object(
                verify,
                "_changed_files",
                return_value=(
                    "git",
                    [
                        "src/tool.py",
                        "openspec/changes/add-tool/proposal.md",
                        "openspec/changes/add-tool/design.md",
                    ],
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
            [
                "openspec/changes/add-tool/design.md",
                "openspec/changes/add-tool/proposal.md",
            ],
            result.value["related_spec_files"],
        )

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
                    "git",
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
                    "git",
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
            return_value=("git", ["src/tool.py"], [], None),
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
            return_value=("git", ["local/a.py", "local/b.py"], [], None),
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
            return_value=("git", ["local/debug.py"], [], None),
        ):
            result = verify.evaluate_spec_drift("HEAD", "", ["local/"])
        self.assertEqual("pass", result.status)
        self.assertEqual(["local/debug.py"], result.value["ignored_files"])
        self.assertEqual([], result.value["code_files"])

    def test_evaluate_spec_drift_refuses_ignoring_spec_file(self) -> None:
        with mock.patch.object(
            verify,
            "_changed_files",
            return_value=("git", ["openspec/changes/x/tasks.md"], [], None),
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
            return_value=("git", ["docs/v1.0[draft].md"], [], None),
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
            subject_patch, comparison_patch, config_patch = _stable_subject_patches()
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult("Z", "spec_drift", "pass", ""),
            ) as spy, mock.patch.object(
                verify, "evaluate_check"
            ), subject_patch, comparison_patch, config_patch, mock.patch("builtins.print"):
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
                verify, "_changed_files", return_value=("git", [], [], None)
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
            subject_patch, comparison_patch, config_patch = _stable_subject_patches()
            with mock.patch.object(
                verify,
                "evaluate_spec_drift",
                return_value=verify.CheckResult("Z", "spec_drift", "pass", ""),
            ), mock.patch.object(
                verify, "knowledge_source_warnings", return_value=[]
            ), subject_patch, comparison_patch, config_patch:
                rc = verify.cmd_verify(config_v2, baseline, report, "HEAD", "")

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, rc)
        self.assertEqual(2, payload["schema_version"])
        self.assertTrue(payload["subject_id"].startswith("sha256:"))
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
            # v2 standalone 主体必须覆盖 Verify 配置；先入库再制造过期警告。
            (repo / "verify.config.json").write_text(
                '{"checks": []}', encoding="utf-8"
            )
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
                    result = verify.cmd_verify({"checks": []}, None, report, "HEAD", "")
            finally:
                os.chdir(old_cwd)

            payload = __import__("json").loads(report.read_text(encoding="utf-8"))

        self.assertEqual(0, result)
        self.assertEqual(2, payload["schema_version"])
        self.assertRegex(payload["subject_id"], r"^sha256:[0-9a-f]{64}$")
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


def _svn_facts(statuses: list[dict]) -> dict:
    """公共接口 SVN facts 的最小可用形状（只填 _changed_files 消费的字段）。"""
    return {
        "backend": "svn",
        "root": ".",
        "statuses": statuses,
    }


class SvnSupportTest(unittest.TestCase):
    """SVN spec-drift file list and source_ref freshness."""

    def test_svn_status_splits_tracked_and_untracked(self) -> None:
        statuses = [
            {"path": "src/tool.py", "status": "modified", "property_status": "none"},
            {"path": "src/new.py", "status": "added", "property_status": None},
            {
                "path": "untracked.txt",
                "status": "unversioned",
                "property_status": None,
            },
            {"path": "ignored.log", "status": "ignored", "property_status": None},
        ]
        tracked, untracked = verify._svn_status_changes_from_facts(statuses)
        self.assertEqual(["src/new.py", "src/tool.py"], tracked)
        self.assertEqual(["untracked.txt"], untracked)

    def test_svn_status_preserves_paths_with_spaces(self) -> None:
        """Regression for P1-1：含空格路径不得被切分（XML 路径天然完整）。"""
        statuses = [
            {
                "path": "src/my module/tool.py",
                "status": "modified",
                "property_status": "none",
            },
            {
                "path": "untracked dir/note.md",
                "status": "unversioned",
                "property_status": None,
            },
        ]
        tracked, untracked = verify._svn_status_changes_from_facts(statuses)
        self.assertEqual(["src/my module/tool.py"], tracked)
        self.assertEqual(["untracked dir/note.md"], untracked)

    def test_svn_status_counts_property_rows_and_versioned_anomalies(self) -> None:
        """Task 11：纯属性行计入 tracked；external/normal 跳过；异常节点计入。

        旧文本解析跳过 ` M` 属性行——属性也是项目输入，公共接口迁移后必须覆盖。
        missing/obstructed/incomplete 是版本化节点的异常状态，计入 tracked 以便
        spec drift 可见；ignored/external/normal/none 仍不计入改动。
        """
        statuses = [
            {"path": "src/real.py", "status": "modified", "property_status": "none"},
            {"path": "vendor", "status": "external", "property_status": None},
            {"path": "src/normal.py", "status": "normal", "property_status": "none"},
            {
                "path": "src/prop-only.py",
                "status": "normal",
                "property_status": "modified",
            },
            {
                "path": "src/prop-conflict.py",
                "status": "normal",
                "property_status": "conflicted",
            },
            {"path": "src/missing.py", "status": "missing", "property_status": None},
            {"path": "ignored.log", "status": "ignored", "property_status": None},
        ]
        tracked, untracked = verify._svn_status_changes_from_facts(statuses)
        self.assertEqual(
            [
                "src/missing.py",
                "src/prop-conflict.py",
                "src/prop-only.py",
                "src/real.py",
            ],
            tracked,
        )
        self.assertEqual([], untracked)

    def test_changed_files_dispatches_to_svn_when_svn_working_copy(self) -> None:
        with mock.patch.object(
            verify,
            "inspect_workspace",
            return_value=_svn_facts(
                [
                    {
                        "path": "src/a.py",
                        "status": "modified",
                        "property_status": "none",
                    },
                    {
                        "path": "b.txt",
                        "status": "unversioned",
                        "property_status": None,
                    },
                ]
            ),
        ):
            backend, tracked, untracked, err = verify._changed_files("HEAD")
        self.assertIsNone(err)
        self.assertEqual("svn", backend)
        self.assertEqual(["src/a.py"], tracked)
        self.assertEqual(["b.txt"], untracked)

    def test_changed_files_reports_tool_and_query_errors_not_empty(self) -> None:
        """工具错误不算无改动：分类错误必须成为 error，不得静默空列表。"""
        for code, operation in (
            ("tool_missing", "svn"),
            ("query_timeout", "svn:status"),
        ):
            with self.subTest(code=code):
                with mock.patch.object(
                    verify,
                    "inspect_workspace",
                    side_effect=verify.VcsError(code, operation),
                ):
                    backend, tracked, untracked, err = verify._changed_files("HEAD")
                self.assertIsNone(backend)
                self.assertEqual([], tracked)
                self.assertEqual([], untracked)
                self.assertIn(code, err)

    def test_changed_files_rejects_dual_vcs_without_explicit_backend(self) -> None:
        calls = {}

        def inspect(path, backend=None):
            calls["backend"] = backend
            if backend is None:
                raise verify.VcsError("ambiguous_backend", "inspect_workspace")
            return _svn_facts([])

        with mock.patch.object(verify, "inspect_workspace", side_effect=inspect):
            _, _, _, err = verify._changed_files("HEAD")
        self.assertIn("--vcs-backend", err)
        with mock.patch.object(verify, "inspect_workspace", side_effect=inspect):
            backend, tracked, untracked, err = verify._changed_files("HEAD", "svn")
        self.assertIsNone(err)
        self.assertEqual("svn", backend)
        self.assertEqual("svn", calls["backend"])

    def test_changed_files_git_keeps_rename_old_path(self) -> None:
        with mock.patch.object(
            verify,
            "inspect_workspace",
            return_value={"backend": "git", "root": "."},
        ), mock.patch.object(
            verify,
            "collect_changes",
            return_value=[
                {
                    "path": "renamed.py",
                    "status": "R100",
                    "old_path": "old.py",
                    "property_changes": [],
                },
                {
                    "path": "new.py",
                    "status": "A",
                    "old_path": None,
                    "property_changes": [],
                },
                {
                    "path": "untracked.txt",
                    "status": "?",
                    "old_path": None,
                    "property_changes": [],
                },
            ],
        ) as collect:
            backend, tracked, untracked, err = verify._changed_files("00355a9")
        collect.assert_called_once_with(Path.cwd(), "00355a9", "git")
        self.assertIsNone(err)
        self.assertEqual("git", backend)
        self.assertEqual(["new.py", "old.py", "renamed.py"], tracked)
        self.assertEqual(["untracked.txt"], untracked)

    def test_svn_source_ref_fresh_has_no_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            source = repo / "src" / "tool.py"
            source.parent.mkdir(parents=True)
            source.write_text("print('v1')\n", encoding="utf-8")
            responses = {
                ("info", "--show-item", "revision", "--", ".@"): (0, "20"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "--",
                    str(source.resolve()) + "@",
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
                ("info", "--show-item", "revision", "--", ".@"): (0, "20"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "--",
                    str(source.resolve()) + "@",
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
        self.assertIn("无法在本地确认", warnings[0])

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
                ("info", "--show-item", "revision", "--", ".@"): (0, "20"),
                (
                    "info",
                    "--show-item",
                    "last-changed-revision",
                    "--",
                    str(source.resolve()) + "@",
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
                verify, "_changed_files", return_value=("git", [], [], None)
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
                verify, "_changed_files", return_value=("git", [], [], None)
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


class _RuntimeSentinel(types.ModuleType):
    """Fail loudly if the standalone flow touches runtime_workflow."""

    def __getattr__(self, name: str) -> object:
        raise AssertionError(
            "standalone verify must not touch runtime_workflow." + name
        )


def _run_in_repo(repo: Path, argv: list[str]) -> tuple[int, Path]:
    report = repo / ".agentic-framework" / "verify" / "report.json"
    old_cwd = Path.cwd()
    try:
        os.chdir(repo)
        with mock.patch("builtins.print"):
            code = verify.main(argv + ["--report", str(report)])
    finally:
        os.chdir(old_cwd)
    return code, report


def _minimal_config() -> str:
    """One passing exit_code check; config files must declare at least one."""
    return json.dumps(
        {
            "checks": [
                {
                    "name": "ok-check",
                    "type": "exit_code",
                    "command": _python_command("print('ok')"),
                }
            ]
        }
    )


@pytest.mark.parametrize(
    "value", [None, "cache", ["../cache"], ["cache/*"], ["."]]
)
def test_config_rejects_unsafe_local_exclude_dirs(value):
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = value
    with pytest.raises(SystemExit) as error:
        verify._validate_config(config, Path("verify.config.json"))
    assert error.value.code == 2


@pytest.mark.parametrize("revision", ["0", "-1", "HEAD", "BASE", "bad"])
def test_svn_source_invalid_revision_does_not_query(revision):
    with mock.patch.object(verify, "_svn_result") as query:
        warnings = verify._svn_source_warnings(
            "meta.yaml",
            "svn:" + revision,
            ["source.txt"],
            Path.cwd(),
            {},
            {},
            {},
        )
    query.assert_not_called()
    assert len(warnings) == 1 and "非正整数" in warnings[0]


def test_svn_source_future_revision_is_unknown_locally():
    with mock.patch.object(
        verify, "_svn_result", return_value=(0, "5")
    ) as query:
        warnings = verify._svn_source_warnings(
            "meta.yaml", "svn:10", ["source.txt"], Path.cwd(), {}, {}, {}
        )
    query.assert_called_once_with(
        Path.cwd(), ["info", "--show-item", "revision", "--", ".@"]
    )
    assert len(warnings) == 1 and "无法在本地确认" in warnings[0]


def test_standalone_verify_svn_and_knowledge_work_without_server(svn_pair):
    first, _, server = svn_pair
    (first / "verify.config.json").write_text(
        _minimal_config(), encoding="utf-8"
    )
    meta = first / "openspec" / "specs" / "demo" / "meta.yaml"
    meta.parent.mkdir(parents=True)
    meta.write_text(
        "service:\n    source_ref: svn:1\n    source_paths:\n        - source.txt\n",
        encoding="utf-8",
    )
    _svn_change_referencing(first, "source.txt")
    offline = server.with_name("server-offline")
    server.rename(offline)
    try:
        code, report = _run_in_repo(first, [])
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert code == 0, payload
        assert payload["verdict"] == "PASS"
        assert verify.knowledge_source_warnings(first) == []
    finally:
        offline.rename(server)


def test_svn_source_paths_are_literal_offline_targets(svn_pair):
    first, _, server = svn_pair
    names = ["-rHEAD", "source.txt@HEAD"]
    for name in names:
        (first / name).write_text("literal project input", encoding="utf-8")
    subprocess.run(
        [
            "svn",
            "add",
            "--non-interactive",
            "--",
            *(name + "@" for name in names),
        ],
        cwd=first,
        capture_output=True,
        check=True,
        timeout=30,
    )
    command(first, "svn", "commit", "-m", "literal names")
    command(first, "svn", "update")
    offline = server.with_name("server-offline")
    server.rename(offline)
    try:
        warnings = verify._svn_source_warnings(
            "meta.yaml", "svn:2", names, first, {}, {}, {}
        )
        assert warnings == []
    finally:
        offline.rename(server)


def test_svn_repository_relative_name_uses_verified_local_node(svn_pair):
    first, _, server = svn_pair
    target = first / "^" / "source.txt"
    target.parent.mkdir()
    target.write_text("local r2 node", encoding="utf-8")
    command(first, "svn", "add", "^")
    command(first, "svn", "commit", "-m", "local caret directory")
    command(first, "svn", "update")

    def warnings():
        return verify._svn_source_warnings(
            "meta.yaml", "svn:1", ["^/source.txt"], first, {}, {}, {}
        )

    online = warnings()
    assert len(online) == 1 and "最新 r2" in online[0]
    offline = server.with_name("server-offline")
    server.rename(offline)
    try:
        assert warnings() == online
    finally:
        offline.rename(server)


def _tracked_python_change(root):
    source = root / "source.py"
    source.write_text("print('v1')\n", encoding="utf-8")
    command(root, "git", "add", "source.py")
    command(root, "git", "commit", "-m", "source baseline")
    base = head(root)
    source.write_text("print('v2')\n", encoding="utf-8")
    return base


@pytest.mark.parametrize("directory", [".codex", "scratch"])
def test_unbound_local_spec_cannot_release_changed_code(repository, directory):
    base = _tracked_python_change(repository)
    relative = directory + "/proposal.md"
    spec = repository / relative
    spec.parent.mkdir()
    spec.write_text("source.py", encoding="utf-8")
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = [directory]
    config["checks"][0]["command"] = _python_command(
        f"from pathlib import Path; Path({relative!r}).write_text('unrelated', encoding='utf-8')"
    )
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    code, report = _run_in_repo(repository, ["--diff-base", base])
    payload = json.loads(report.read_text(encoding="utf-8"))
    drift = payload["spec_drift"]
    assert code == 2 and payload["verdict"] == "ERROR"
    assert drift["status"] == "error"
    assert drift["value"]["related_spec_files"] == [relative]
    assert drift["value"]["unbound_spec_files"] == [relative]
    assert relative in drift["value"]["refused_ignores"]
    assert spec.read_text(encoding="utf-8") == "unrelated"


@pytest.mark.parametrize("coverage", ["tracked", "explicit"])
def test_bound_local_spec_can_release_changed_code(
    repository, monkeypatch, coverage
):
    base = _tracked_python_change(repository)
    relative = ".codex/proposal.md"
    spec = repository / relative
    spec.parent.mkdir()
    spec.write_text("source.py", encoding="utf-8")
    (repository / "verify.config.json").write_text(
        _minimal_config(), encoding="utf-8"
    )
    if coverage == "tracked":
        command(repository, "git", "add", "-f", relative)
    else:

        def capture(base, config_path, vcs_backend=None):
            return verify.capture_native_subject(
                repository,
                base,
                config_path=config_path,
                backend=vcs_backend,
                required_inputs=[relative],
            )

        monkeypatch.setattr(verify, "_capture_verify_subject", capture)
    code, report = _run_in_repo(repository, ["--diff-base", base])
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 0 and payload["verdict"] == "PASS", payload
    assert payload["spec_drift"]["value"]["related_spec_files"] == [relative]


def test_unrelated_local_template_does_not_block_bound_specs(repository):
    base = _tracked_python_change(repository)
    local = repository / ".codex" / "proposal.md"
    local.parent.mkdir()
    local.write_text("unrelated local template", encoding="utf-8")
    relative = "openspec/changes/1-test/tasks.md"
    spec = repository / relative
    spec.parent.mkdir(parents=True)
    spec.write_text("source.py", encoding="utf-8")
    (repository / "verify.config.json").write_text(
        _minimal_config(), encoding="utf-8"
    )
    code, report = _run_in_repo(repository, ["--diff-base", base])
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 0 and payload["verdict"] == "PASS", payload
    assert payload["spec_drift"]["value"]["related_spec_files"] == [relative]
    assert (
        ".codex/proposal.md"
        in payload["spec_drift"]["value"]["refused_ignores"]
    )


def test_missing_spec_tombstone_does_not_bind_later_consumed_content(
    repository, monkeypatch
):
    source = repository / "source.py"
    source.write_text("v1", encoding="utf-8")
    spec = repository / ".codex" / "proposal.md"
    spec.parent.mkdir()
    spec.write_text("source.py baseline", encoding="utf-8")
    command(repository, "git", "add", "-f", "source.py", ".codex/proposal.md")
    command(repository, "git", "commit", "-m", "source and spec baseline")
    base = head(repository)
    source.write_text("v2", encoding="utf-8")
    spec.unlink()
    config = json.loads(_minimal_config())
    config["checks"][0]["command"] = _python_command(
        "from pathlib import Path; Path('.codex/proposal.md').unlink()"
    )
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    original = verify._capture_verify_subject
    calls = 0

    def capture(*args, **kwargs):
        nonlocal calls
        subject = original(*args, **kwargs)
        if calls == 0:
            spec.write_text(
                "source.py newly consumed content", encoding="utf-8"
            )
        calls += 1
        return subject

    monkeypatch.setattr(verify, "_capture_verify_subject", capture)
    code, report = _run_in_repo(repository, ["--diff-base", base])
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 2 and payload["verdict"] == "ERROR"
    assert payload["spec_drift"]["value"]["unbound_spec_files"] == [
        ".codex/proposal.md"
    ]
    assert not spec.exists()


@pytest.mark.parametrize("backend", ["git", "svn"])
def test_local_exclusions_skip_only_untracked_spec_drift(request, backend):
    if backend == "svn":
        root, _, _ = request.getfixturevalue("svn_pair")
        argv = []
    else:
        root = request.getfixturevalue("repository")
        argv = ["--diff-base", head(root)]
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = ["cache"]
    (root / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    for directory in (".codex", ".claude", "cache"):
        (root / directory).mkdir()
        (root / directory / "local.py").write_text(
            "local state", encoding="utf-8"
        )
    code, report = _run_in_repo(root, argv)
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 0, payload
    ignored = payload["spec_drift"]["value"]["ignore_sources"]
    for directory in (".codex", ".claude", "cache"):
        name = directory if backend == "svn" else directory + "/local.py"
        assert ignored[name] == ["local_exclude_dirs"]
    if backend == "svn":
        command(root, "svn", "add", ".codex")
    else:
        command(root, "git", "add", "-f", ".codex/local.py")
    code, report = _run_in_repo(root, argv)
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 1, payload
    assert ".codex/local.py" in payload["spec_drift"]["value"]["code_files"]
    assert (
        ".codex/local.py" not in payload["spec_drift"]["value"]["ignored_files"]
    )


def test_local_exclusions_keep_spec_drift_refusal(repository, monkeypatch):
    spec = repository / ".codex" / "proposal.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("preserve untracked spec", encoding="utf-8")
    monkeypatch.chdir(repository)
    result = verify.evaluate_spec_drift(head(repository), "")
    assert result.status == "pass"
    assert ".codex/proposal.md" in result.value["refused_ignores"]


@pytest.mark.parametrize(
    "directory", ["openspec", "OpenSpec/cache", "docs/ADR", "adrs"]
)
def test_local_exclusions_cannot_cover_project_specs(repository, directory):
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = [directory]
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    with pytest.raises(SystemExit) as error:
        _run_in_repo(repository, ["--diff-base", head(repository)])
    assert error.value.code == 2


def test_local_directory_exclusion_does_not_hide_regular_code_file(repository):
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = ["cache.py"]
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    (repository / "cache.py").write_text("project input", encoding="utf-8")
    code, report = _run_in_repo(repository, ["--diff-base", head(repository)])
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 1
    assert "cache.py" in payload["spec_drift"]["value"]["code_files"]
    assert "cache.py" not in payload["spec_drift"]["value"]["ignored_files"]


def test_standalone_verify_rejects_policy_edits_during_checks(repository):
    config = {
        "checks": [
            {
                "name": "mutate-policy",
                "type": "exit_code",
                "command": _python_command(
                    "import json; from pathlib import Path; "
                    "p=Path('verify.config.json'); "
                    "v=json.loads(p.read_text(encoding='utf-8')); "
                    "v['local_exclude_dirs']=['cache']; "
                    "p.write_text(json.dumps(v), encoding='utf-8')"
                ),
            }
        ],
    }
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    code, report = _run_in_repo(repository, ["--diff-base", head(repository)])
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 2 and payload["verdict"] == "ERROR"
    assert payload["results"][-1]["name"] == "native-subject"
    assert "发生变化" in payload["results"][-1]["detail"]


def test_config_loaded_before_policy_capture_must_match(
    repository, monkeypatch
):
    path = repository / "verify.config.json"
    path.write_text(_minimal_config(), encoding="utf-8")
    original = verify.load_config

    def changed_after_load(*args, **kwargs):
        loaded = original(*args, **kwargs)
        changed = {**loaded, "local_exclude_dirs": ["cache"]}
        path.write_text(json.dumps(changed), encoding="utf-8")
        return loaded

    monkeypatch.setattr(verify, "load_config", changed_after_load)
    with mock.patch.object(verify, "evaluate_check") as check:
        code, report = _run_in_repo(
            repository, ["--diff-base", head(repository)]
        )
    assert code == 2 and not report.exists()
    check.assert_not_called()


def test_config_bytes_must_still_match_initial_capture(repository, monkeypatch):
    path = repository / "verify.config.json"
    path.write_text(_minimal_config(), encoding="utf-8")
    original = verify._capture_verify_subject

    def changed_after_capture(*args, **kwargs):
        subject = original(*args, **kwargs)
        path.write_text(
            path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        return subject

    monkeypatch.setattr(
        verify, "_capture_verify_subject", changed_after_capture
    )
    with mock.patch.object(verify, "evaluate_check") as check:
        code, report = _run_in_repo(
            repository, ["--diff-base", head(repository)]
        )
    assert code == 2 and not report.exists()
    check.assert_not_called()


def test_local_exclusions_are_frozen_in_baseline(repository):
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = ["cache"]
    path = repository / "verify.config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    baseline = repository / ".agentic-framework" / "verify" / "baseline.json"
    code, _ = _run_in_repo(repository, ["--save-baseline", str(baseline)])
    assert code == 0
    saved = json.loads(baseline.read_text(encoding="utf-8"))
    assert saved["local_exclude_dirs_snapshot"] == ["cache"]
    config["local_exclude_dirs"].append("other")
    path.write_text(json.dumps(config), encoding="utf-8")
    code, _ = _run_in_repo(repository, ["--baseline", str(baseline)])
    assert code == 2


def test_old_baseline_means_no_custom_local_exclusions(repository):
    config = json.loads(_minimal_config())
    path = repository / "verify.config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    baseline = repository / ".agentic-framework" / "verify" / "baseline.json"
    code, _ = _run_in_repo(repository, ["--save-baseline", str(baseline)])
    assert code == 0
    saved = json.loads(baseline.read_text(encoding="utf-8"))
    saved.pop("local_exclude_dirs_snapshot")
    baseline.write_text(json.dumps(saved), encoding="utf-8")
    code, _ = _run_in_repo(repository, ["--baseline", str(baseline)])
    assert code == 0
    config["local_exclude_dirs"] = ["cache"]
    path.write_text(json.dumps(config), encoding="utf-8")
    code, _ = _run_in_repo(repository, ["--baseline", str(baseline)])
    assert code == 2


def test_local_exclude_error_utf8_child_under_cp936_parent(repository):
    config = json.loads(_minimal_config())
    config["local_exclude_dirs"] = ["../outside"]
    (repository / "verify.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    source = (
        "import os, subprocess, sys; "
        "assert sys.stdout.encoding.lower() in ('cp936', 'gbk'); "
        "env=os.environ.copy(); "
        "env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8'); "
        f"r=subprocess.run([sys.executable, {str(Path(verify.__file__).resolve())!r}], "
        "env=env, capture_output=True, encoding='utf-8', timeout=30); "
        "assert r.returncode == 2; "
        "assert 'local_exclude_dirs' in r.stderr and '\u9879\u76ee\u6839' in r.stderr"
    )
    env = {**os.environ, "PYTHONUTF8": "0", "PYTHONIOENCODING": "cp936"}
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=repository,
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=40,
    )
    assert result.returncode == 0, result.stderr


def test_standalone_verify_binds_v2_subject(repository):
    (repository / "verify.config.json").write_text(
        _minimal_config(), encoding="utf-8"
    )
    base = head(repository)
    code, report = _run_in_repo(repository, ["--diff-base", base])
    assert code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["subject_id"].startswith("sha256:")
    assert payload["verdict"] == "PASS"
    validate_native_report(payload)


def test_standalone_verify_rejects_input_edits_during_checks(repository):
    (repository / "verify.config.json").write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "name": "mutating-check",
                        "type": "exit_code",
                        "command": _python_command(
                            "open('原始 file.txt', 'a', encoding='utf-8')"
                            ".write('mid-run edit')"
                        ),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    base = head(repository)
    code, report = _run_in_repo(repository, ["--diff-base", base])
    assert code == 2
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["verdict"] == "ERROR"
    assert payload["results"][-1]["name"] == "native-subject"
    assert payload["results"][-1]["status"] == "error"
    assert "发生变化" in payload["results"][-1]["detail"]
    # 报告仍绑定检查前的内容主体，且整体满足 v2 合同（ERROR 可校验）。
    assert payload["subject_id"].startswith("sha256:")
    validate_native_report(payload)


def test_standalone_verify_without_config_is_complete(repository):
    # 无 Verify 配置只跑内置门禁，缺失配置不算主体覆盖限制。
    base = head(repository)
    code, report = _run_in_repo(repository, ["--diff-base", base])
    assert code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"


def test_standalone_without_vcs_writes_no_report(tmp_path):
    report = tmp_path / "report.json"
    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        with mock.patch("builtins.print"):
            code = verify.main(["--report", str(report)])
    finally:
        os.chdir(old_cwd)
    assert code == 2
    assert not report.exists()


def test_standalone_verify_never_touches_runtime_workflow(repository):
    (repository / "verify.config.json").write_text(
        _minimal_config(), encoding="utf-8"
    )
    base = head(repository)
    sentinel = _RuntimeSentinel("runtime_workflow")
    old_cwd = Path.cwd()
    try:
        os.chdir(repository)
        with mock.patch.dict(sys.modules, {"runtime_workflow": sentinel}):
            with mock.patch("builtins.print"):
                code = verify.main(["--diff-base", base])
    finally:
        os.chdir(old_cwd)
    assert code == 0
    assert not (repository / ".agentic-framework" / "runs").exists()


def _svn_change_referencing(first: Path, *code_paths: str) -> None:
    """活跃 Change 的 tasks.md，正文引用改动的代码路径以通过 spec drift。

    未版本化目录在 svn status 中折叠为单个 `?` 条目，tasks.md 不可见；先
    `svn add` 使节点逐项进入状态（只 add 不 commit，符合纯 SVN 规则）。
    """
    tasks = first / "openspec" / "changes" / "1-svn" / "tasks.md"
    tasks.parent.mkdir(parents=True)
    body = "- 文件：" + "、".join(f"`{item}`" for item in code_paths) + "\n"
    tasks.write_text(body, encoding="utf-8")
    command(first, "svn", "add", "openspec")


def test_standalone_verify_binds_svn_subject_and_covers_properties(svn_pair):
    """纯 SVN 产出可绑定的 v2 Verify：属性改动计入改动并进入内容主体。"""
    first, _, _ = svn_pair
    (first / "verify.config.json").write_text(_minimal_config(), encoding="utf-8")
    (first / "tool.py").write_text("print('v1')\n", encoding="utf-8")
    command(first, "svn", "add", "tool.py")
    command(first, "svn", "propset", "project:flag", "yes", "tool.py")
    _svn_change_referencing(first, "tool.py")
    code, report = _run_in_repo(first, [])
    assert code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["subject_id"].startswith("sha256:")
    assert payload["verdict"] == "PASS"
    spec_drift = payload["spec_drift"]["value"]
    # 属性改动（property_status=modified）计入 tracked，不再像旧文本解析那样跳过。
    assert "tool.py" in spec_drift["code_files"]
    assert spec_drift["diff_base"] is None
    validate_native_report(payload)


def test_standalone_verify_svn_requires_backend_when_git_added(svn_pair):
    """双 VCS 不再隐式 Git 优先：无显式后端拒绝，指定后端可核验。"""
    first, _, _ = svn_pair
    (first / "verify.config.json").write_text(_minimal_config(), encoding="utf-8")
    _svn_change_referencing(first, "source.txt")
    command(first, "git", "init")
    code, report = _run_in_repo(first, [])
    assert code == 2
    assert not report.exists()
    code, report = _run_in_repo(first, ["--vcs-backend", "svn"])
    assert code == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["verdict"] == "PASS"
    assert payload["spec_drift"]["value"]["diff_base"] is None


def test_standalone_verify_svn_mixed_revision_is_not_complete(svn_pair):
    """混合版本工作副本不能产生完整已验证声明（每节点基准不可互相替代）。"""
    first, second, _ = svn_pair
    (first / "verify.config.json").write_text(_minimal_config(), encoding="utf-8")
    (second / "source.txt").write_text("upstream\n", encoding="utf-8")
    command(second, "svn", "commit", "-m", "upstream")
    command(first, "svn", "update", "source.txt")
    code, report = _run_in_repo(first, [])
    assert code == 2
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["verdict"] == "ERROR"
    subject_result = payload["results"][-1]
    assert subject_result["name"] == "native-subject"
    assert subject_result["status"] == "error"
    assert "覆盖不完整" in subject_result["detail"]


def test_save_baseline_svn_snapshots_property_and_local_changes(svn_pair):
    """SVN 基线 S0 记录本地改动（含属性行）；不清理、不提交。"""
    first, _, _ = svn_pair
    (first / "verify.config.json").write_text(_minimal_config(), encoding="utf-8")
    command(first, "svn", "propset", "project:flag", "yes", "empty")
    (first / "untracked.py").write_text("local\n", encoding="utf-8")
    baseline = first / ".agentic-framework" / "verify" / "baseline.json"
    old_cwd = Path.cwd()
    try:
        os.chdir(first)
        with mock.patch("builtins.print"):
            code = verify.main(["--save-baseline", str(baseline)])
    finally:
        os.chdir(old_cwd)
    assert code == 0
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    snapshot = payload["changed_files_snapshot"]
    assert "empty" in snapshot
    assert "untracked.py" in snapshot
    # 预存改动保持原样：没有 revert，也没有 svn add/commit。
    assert (first / "untracked.py").exists()


def test_extract_executable_keeps_windows_absolute_paths():
    # POSIX 切词会吃掉反斜杠，使真实工具被误判缺失（虚假 error）。
    unquoted = r"E:\work\venv\Scripts\python.exe -c \"print(1)\""
    assert verify._extract_executable(unquoted) == r"E:\work\venv\Scripts\python.exe"
    quoted = r'"C:\Program Files\Python39\python.exe" -c "print(1)"'
    assert verify._extract_executable(quoted) == (
        r"C:\Program Files\Python39\python.exe"
    )
    assert verify._extract_executable("grep -rHo pattern x") == "grep"
