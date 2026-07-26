"""Tests for deterministic workflow control."""

import errno
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

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
import workflow_control

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_change


def passing_verify_result() -> dict[str, object]:
    """Return the minimum CheckResult serialization accepted by the gate."""
    return {
        "name": "test",
        "type": "test",
        "status": "pass",
        "detail": "ok",
        "value": None,
        "new_items": [],
    }


def runtime_verify_fixture(root: Path) -> tuple[Path, Path]:
    """Create the minimum initialized Run needed by the task quality gate."""
    run_dir = root / ".agentic-framework" / "runs" / "run-1"
    context = {
        "run_id": "run-1",
        "profile": "tooling",
        "harness": "codex",
        "commit_sha": "1" * 40,
        "base_commit_sha": "0" * 40,
        "config_digest": "sha256:" + "2" * 64,
        "created_at": "2026-07-19T12:00:00Z",
    }
    run_dir.mkdir(parents=True)
    (run_dir / "run-context.json").write_text(json.dumps(context), encoding="utf-8")
    report = workflow_control.runtime_workflow.envelope(
        context,
        "verify-report",
        "verify-1-1",
        {
            "verdict": "PASS",
            "total": 1,
            "errors": 0,
            "violations": 0,
            "spec_drift": passing_verify_result(),
            "warnings": [],
            "results": [passing_verify_result()],
        },
        "workflow-verification",
        task_id="1",
        attempt=1,
    )
    report_path = run_dir / "artifacts" / "verify-1-1.json"
    report_path.parent.mkdir()
    report_path.write_text(json.dumps(report), encoding="utf-8")
    journal = run_dir / "events.jsonl"
    workflow_control.runtime_workflow.run_journal.append_event(
        journal, workflow_control.runtime_workflow._event(context, 1, "run-started")
    )
    workflow_control.runtime_workflow.run_journal.write_checkpoint(run_dir, journal)
    return run_dir, report_path


def tasks_text(
    states: dict[int, str],
    dependencies: dict[int, list[int]],
    attempts: int = 0,
) -> str:
    """Build the minimum task document used by control-flow tests."""
    sections = []
    for task_id in states:
        deps = ", ".join(f"Task {dependency}" for dependency in dependencies[task_id])
        sections.append(
            f"### 任务 {task_id}：测试\n\n"
            f"- 状态：{states[task_id]}\n"
            f"- attempts：{attempts}\n"
            f"- depends_on：{deps or '[]'}\n"
        )
    return "\n".join(sections)


class WorkflowControlTest(unittest.TestCase):
    """Cover deterministic scheduling, transitions, persistence, and recovery."""

    def test_build_waves_is_stable(self) -> None:
        text = tasks_text(
            {3: "未开始", 1: "未开始", 2: "未开始"},
            {3: [1, 2], 1: [], 2: []},
        )
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([[1, 2], [3]], workflow_control.build_waves(tasks))

    def test_same_wave_failure_is_isolated_end_to_end(self) -> None:
        text = tasks_text({1: "进行中", 2: "进行中"}, {1: [], 2: []}, attempts=2)
        tasks = lint_task_deps.parse_tasks(text)
        failed = workflow_control.apply_event(tasks, 1, "failure")
        passed = workflow_control.apply_event(tasks, 2, "quality_passed")
        text = workflow_control.update_task_state(text, failed)
        text = workflow_control.update_task_state(text, passed)
        tasks = lint_task_deps.parse_tasks(text)
        merged = workflow_control.apply_event(tasks, 2, "merge_success")
        text = workflow_control.update_task_state(text, merged)
        states = workflow_control._states(lint_task_deps.parse_tasks(text))
        self.assertEqual({1: "需人工", 2: "完成"}, states)

    def test_quality_pass_does_not_complete_before_merge(self) -> None:
        text = tasks_text({1: "进行中"}, {1: []})
        tasks = lint_task_deps.parse_tasks(text)
        quality = workflow_control.apply_event(tasks, 1, "quality_passed")
        self.assertEqual(("进行中", "merge"), (quality.state, quality.action))
        text = workflow_control.update_task_state(text, quality)
        merged = workflow_control.apply_event(
            lint_task_deps.parse_tasks(text), 1, "merge_success"
        )
        self.assertEqual("完成", merged.state)

    def test_validate_verify_report_requires_pass_verdict(self) -> None:
        workflow_control._validate_verify_report(
            {
                "verdict": "PASS",
                "errors": 0,
                "violations": 0,
                "total": 1,
                "results": [passing_verify_result()],
                "spec_drift": passing_verify_result(),
            }
        )
        with self.assertRaisesRegex(ValueError, "PASS"):
            workflow_control._validate_verify_report({"verdict": "NEEDS_CHANGES"})
        with self.assertRaisesRegex(ValueError, "PASS"):
            workflow_control._validate_verify_report({})
        with self.assertRaisesRegex(ValueError, "JSON 对象"):
            workflow_control._validate_verify_report([])
        with self.assertRaisesRegex(ValueError, "errors"):
            workflow_control._validate_verify_report(
                {"verdict": "PASS", "errors": 1, "violations": 0}
            )
        with self.assertRaisesRegex(ValueError, "violations"):
            workflow_control._validate_verify_report(
                {"verdict": "PASS", "errors": 0, "violations": 1}
            )
        with self.assertRaisesRegex(ValueError, "缺少必填字段"):
            workflow_control._validate_verify_report(
                {
                    "verdict": "PASS",
                    "errors": 0,
                    "violations": 0,
                    "total": 1,
                    "results": [{"status": "pass"}],
                    "spec_drift": passing_verify_result(),
                }
            )

    def test_select_execution_route_defaults_to_native_delivery(self) -> None:
        self.assertEqual(
            workflow_control.ExecutionRoute("native-delivery", ()),
            workflow_control.select_execution_route("standard"),
        )

    def test_select_execution_route_upgrades_for_every_runtime_condition(self) -> None:
        conditions = (
            ("strict", {}, "strict-risk"),
            ("standard", {"parallel_worktree_write": True}, "parallel-worktree-write"),
            ("standard", {"long_task_recovery": True}, "long-task-recovery"),
            (
                "standard",
                {"cross_host_capability_verification": True},
                "cross-host-capability-verification",
            ),
            ("standard", {"audit_required": True}, "audit-required"),
        )
        for profile, kwargs, expected_reason in conditions:
            with self.subTest(expected_reason=expected_reason):
                route = workflow_control.select_execution_route(profile, **kwargs)
                self.assertEqual("runtime-run", route.path)
                self.assertIn(expected_reason, route.runtime_upgrade_reasons)

    def test_route_command_reports_native_and_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            path.write_text(tasks_text({1: "未开始"}, {1: []}), encoding="utf-8")
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(
                    0,
                    workflow_control.main(
                        [str(path), "route", "--review-profile", "standard"]
                    ),
                )
            self.assertIn('"path": "native-delivery"', stdout.getvalue())
            with mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(
                    0,
                    workflow_control.main(
                        [
                            str(path),
                            "route",
                            "--review-profile",
                            "standard",
                            "--audit-required",
                        ]
                    ),
                )
            self.assertIn('"path": "runtime-run"', stdout.getvalue())

    def test_quality_passed_without_verify_report_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            result = workflow_control.main(
                [str(path), "event", "1", "quality_passed", "--write"]
            )
            self.assertEqual(2, result)
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_quality_passed_with_missing_report_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            missing_report = Path(temp_dir) / "missing-report.json"
            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(missing_report),
                ]
            )
            self.assertEqual(2, result)
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_quality_passed_with_invalid_json_report_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            report_path = Path(temp_dir) / "report.json"
            report_path.write_text("{not valid json", encoding="utf-8")
            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(report_path),
                ]
            )
            self.assertEqual(2, result)
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_quality_passed_with_non_pass_verdict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            report_path = Path(temp_dir) / "report.json"
            report_path.write_text(
                json.dumps({"verdict": "NEEDS_CHANGES"}), encoding="utf-8"
            )
            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(report_path),
                ]
            )
            self.assertEqual(2, result)
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_native_quality_passed_accepts_standalone_pass_without_run_artifact(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "tasks.md"
            path.write_text(tasks_text({1: "进行中"}, {1: []}), encoding="utf-8")
            report_path = root / "verify-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "verdict": "PASS",
                        "errors": 0,
                        "violations": 0,
                        "total": 1,
                        "results": [passing_verify_result()],
                        "spec_drift": passing_verify_result(),
                    }
                ),
                encoding="utf-8",
            )

            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(report_path),
                ]
            )

            self.assertEqual(0, result)
            self.assertIn(
                "- control_stage：quality_passed", path.read_text(encoding="utf-8")
            )
            self.assertFalse((root / ".agentic-framework" / "runs").exists())

    def test_quality_passed_with_pass_verdict_writes_state_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            path.write_text(tasks_text({1: "进行中"}, {1: []}), encoding="utf-8")
            run_dir, report_path = runtime_verify_fixture(Path(temp_dir))
            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(report_path),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            self.assertEqual(0, result)
            persisted = path.read_text(encoding="utf-8")
            self.assertIn("- 状态：进行中", persisted)
            self.assertIn("- control_stage：quality_passed", persisted)

    def test_merge_requires_persisted_quality_passed_stage(self) -> None:
        running = lint_task_deps.parse_tasks(tasks_text({1: "进行中"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "不允许"):
            workflow_control.apply_event(running, 1, "merge_success")

    def test_failure_recursively_blocks_descendants(self) -> None:
        text = tasks_text(
            {1: "需人工", 2: "未开始", 3: "未开始"},
            {1: [], 2: [1], 3: [2]},
        )
        decisions = workflow_control.propagate_blocked(lint_task_deps.parse_tasks(text))
        self.assertEqual([2, 3], [decision.task_id for decision in decisions])

    def test_retry_count_persists_and_survives_reload(self) -> None:
        text = tasks_text({1: "进行中"}, {1: []})
        for expected in (1, 2, 3):
            tasks = lint_task_deps.parse_tasks(text)
            decision = workflow_control.apply_event(tasks, 1, "failure")
            text = workflow_control.update_task_state(text, decision)
            self.assertEqual(
                expected,
                workflow_control._attempts(lint_task_deps.parse_tasks(text)[1]),
            )
        self.assertEqual("需人工", decision.state)

    def test_recovery_skips_completed_and_reconciles_merged(self) -> None:
        text = tasks_text(
            {1: "完成", 2: "进行中", 3: "阻塞"},
            {1: [], 2: [1], 3: [2]},
        )
        actions = workflow_control.plan_recovery(lint_task_deps.parse_tasks(text), {2})
        self.assertEqual(
            ["skip", "complete", "unblock"], [item.action for item in actions]
        )

    def test_self_dependency_and_missing_field_fail_closed(self) -> None:
        self_dep = lint_task_deps.parse_tasks(tasks_text({1: "未开始"}, {1: [1]}))
        with self.assertRaisesRegex(ValueError, "循环"):
            workflow_control.build_waves(self_dep)
        missing = lint_task_deps.parse_tasks("### 任务 1：测试\n- 状态：未开始\n")
        with self.assertRaisesRegex(ValueError, "缺少 depends_on"):
            workflow_control.build_waves(missing)
        with self.assertRaisesRegex(ValueError, "缺少 depends_on"):
            workflow_control.apply_event(missing, 1, "start")

    def test_illegal_transition_and_reason_injection_fail(self) -> None:
        completed = lint_task_deps.parse_tasks(tasks_text({1: "完成"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "不允许"):
            workflow_control.apply_event(completed, 1, "merge_success")
        running = lint_task_deps.parse_tasks(tasks_text({1: "进行中"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "换行"):
            workflow_control.apply_event(running, 1, "failure", "x\n- 状态：完成")

    def test_unblock_requires_completed_dependencies(self) -> None:
        ready = lint_task_deps.parse_tasks(
            tasks_text({1: "完成", 2: "阻塞"}, {1: [], 2: [1]})
        )
        self.assertEqual(
            "未开始", workflow_control.apply_event(ready, 2, "unblock").state
        )
        waiting = lint_task_deps.parse_tasks(
            tasks_text({1: "需人工", 2: "阻塞"}, {1: [], 2: [1]})
        )
        with self.assertRaisesRegex(ValueError, "尚未全部完成"):
            workflow_control.apply_event(waiting, 2, "unblock")

    def test_start_requires_completed_dependencies(self) -> None:
        tasks = lint_task_deps.parse_tasks(
            tasks_text({1: "进行中", 2: "未开始"}, {1: [], 2: [1]})
        )
        with self.assertRaisesRegex(ValueError, "尚未全部完成"):
            workflow_control.apply_event(tasks, 2, "start")

    def test_missing_verify_config_blocks_all_dispatch_entry_points(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "未开始"}, {1: []})
            path.write_text(original, encoding="utf-8")

            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(2, workflow_control.main([str(path), "dispatchable"]))
            self.assertIn(
                str(Path(workflow_control.__file__).resolve()), stderr.getvalue()
            )
            self.assertEqual(
                2,
                workflow_control.main([str(path), "event", "1", "start", "--write"]),
            )
            self.assertEqual(
                2,
                workflow_control.main([str(path), "recover"]),
            )
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_skip_decision_allows_dispatch_without_verify_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            path.write_text(tasks_text({1: "未开始"}, {1: []}), encoding="utf-8")

            self.assertEqual(
                0,
                workflow_control.main(
                    [
                        str(path),
                        "verify-config-decision",
                        "--choice",
                        "skip",
                        "--write",
                    ]
                ),
            )
            self.assertIn(
                "- verify_config_decision: 跳过",
                path.read_text(encoding="utf-8"),
            )
            self.assertEqual(0, workflow_control.main([str(path), "dispatchable"]))
            self.assertEqual(
                0,
                workflow_control.main([str(path), "event", "1", "start", "--write"]),
            )

    def test_initialize_decision_requires_existing_verify_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "tasks.md"
            original = tasks_text({1: "未开始"}, {1: []})
            path.write_text(original, encoding="utf-8")

            self.assertEqual(
                2,
                workflow_control.main(
                    [
                        str(path),
                        "verify-config-decision",
                        "--choice",
                        "initialize",
                        "--write",
                    ]
                ),
            )
            self.assertEqual(original, path.read_text(encoding="utf-8"))

            (root / "verify.config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(
                0,
                workflow_control.main(
                    [
                        str(path),
                        "verify-config-decision",
                        "--choice",
                        "initialize",
                        "--write",
                    ]
                ),
            )
            self.assertIn(
                "- verify_config_decision: 初始化",
                path.read_text(encoding="utf-8"),
            )
            self.assertEqual(0, workflow_control.main([str(path), "dispatchable"]))

    def test_cli_uses_atomic_writer_and_persists_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            path.write_text(tasks_text({1: "进行中"}, {1: []}), encoding="utf-8")
            result = workflow_control.main(
                [str(path), "event", "1", "failure", "--write"]
            )
            self.assertEqual(0, result)
            persisted = path.read_text(encoding="utf-8")
            self.assertIn("- attempts：1", persisted)
            self.assertEqual([], list(path.parent.glob(".tasks.md.*")))

    def test_cli_writes_unified_change_tasks_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(temp_dir)
                / "openspec"
                / "changes"
                / "1-example-change"
                / "tasks.md"
            )
            path.parent.mkdir(parents=True)
            path.write_text(tasks_text({1: "进行中"}, {1: []}), encoding="utf-8")
            run_dir, report_path = runtime_verify_fixture(Path(temp_dir))
            result = workflow_control.main(
                [
                    str(path),
                    "event",
                    "1",
                    "quality_passed",
                    "--write",
                    "--verify-report",
                    str(report_path),
                    "--run-dir",
                    str(run_dir),
                ]
            )
            self.assertEqual(0, result)
            self.assertIn(
                "- control_stage：quality_passed",
                path.read_text(encoding="utf-8"),
            )

    def test_legacy_tasks_path_remains_readable_for_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(temp_dir)
                / "docs"
                / "design-docs"
                / "module"
                / "legacy-change"
                / "tasks.md"
            )
            path.parent.mkdir(parents=True)
            path.write_text(
                tasks_text({1: "完成", 2: "未开始"}, {1: [], 2: [1]}),
                encoding="utf-8",
            )
            (path.parent / "verify.config.json").write_text("{}", encoding="utf-8")
            self.assertEqual(0, workflow_control.main([str(path), "waves"]))
            self.assertEqual(
                0,
                workflow_control.main([str(path), "recover", "--merged", "1"]),
            )

    def test_rejects_nonstandard_task_document_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "work-items.md"
            path.write_text(tasks_text({1: "未开始"}, {1: []}), encoding="utf-8")
            self.assertEqual(2, workflow_control.main([str(path), "waves"]))

    def test_knowledge_sync_task_uses_normal_dag_and_recovery(self) -> None:
        text = tasks_text(
            {1: "完成", 2: "未开始", 3: "未开始"},
            {1: [], 2: [1], 3: [2]},
        ).replace("任务 2：测试", "任务 2：同步长期知识")
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([2], workflow_control.dispatchable_tasks(tasks))
        actions = workflow_control.plan_recovery(tasks, set())
        self.assertEqual(
            ["skip", "dispatch", "wait"],
            [action.action for action in actions],
        )

    def test_atomic_write_preserves_permissions_and_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []}).replace("\n", "\r\n")
            path.write_bytes(original.encode("utf-8"))
            path.chmod(0o640)
            original_mode = path.stat().st_mode & 0o777
            workflow_control.main([str(path), "event", "1", "failure", "--write"])
            data = path.read_bytes()
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
            self.assertEqual(original_mode, path.stat().st_mode & 0o777)

    def test_contending_writer_times_out_without_changing_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            (Path(temp_dir) / ".git").mkdir()
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            with workflow_control._task_write_lock(path, 0):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(workflow_control.__file__)),
                        str(path),
                        "event",
                        "1",
                        "failure",
                        "--write",
                        "--lock-timeout",
                        "0.1",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    check=False,
                    env={**os.environ, "PYTHONUTF8": "1"},
                )
            self.assertEqual(2, result.returncode)
            self.assertIn(str(workflow_control._task_lock_path(path)), result.stderr)
            self.assertIn("0.1 秒", result.stderr)
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_waiting_writer_succeeds_after_lock_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            (Path(temp_dir) / ".git").mkdir()
            path.write_text(tasks_text({1: "进行中"}, {1: []}), encoding="utf-8")
            with workflow_control._task_write_lock(path, 0):
                helper = (
                    "import os, sys\n"
                    f"sys.path.insert(0, {str(Path(workflow_control.__file__).parent)!r})\n"
                    "import workflow_control\n"
                    "path = workflow_control.Path(sys.argv[1])\n"
                    "lock_path = workflow_control._task_lock_path(path)\n"
                    "with lock_path.open('a+b') as stream:\n"
                    "    stream.seek(0)\n"
                    "    if workflow_control._try_lock(stream):\n"
                    "        workflow_control._unlock(stream)\n"
                    "        raise SystemExit('parent lock was not held')\n"
                    "print('contended', flush=True)\n"
                    "raise SystemExit(workflow_control.main([\n"
                    "    str(path), 'event', '1', 'failure', '--write',\n"
                    "    '--lock-timeout', '2']))\n"
                )
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        helper,
                        str(path),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env={**os.environ, "PYTHONUTF8": "1"},
                )
                self.assertEqual("contended\n", process.stdout.readline())
                self.assertIsNone(process.poll())
            _, stderr = process.communicate(timeout=3)
            self.assertEqual(0, process.returncode, stderr)
            self.assertIn("- attempts：1", path.read_text(encoding="utf-8"))

    def test_lock_path_uses_repository_runtime_directory_and_target_digest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            roots = [Path(first), Path(second)]
            paths = []
            for root in roots:
                (root / ".git").mkdir()
                path = root / "openspec" / "changes" / "same-name" / "tasks.md"
                path.parent.mkdir(parents=True)
                paths.append(path)

            first_lock = workflow_control._task_lock_path(paths[0])
            second_lock = workflow_control._task_lock_path(paths[1])
            self.assertEqual(
                roots[0] / ".agentic-framework" / "locks", first_lock.parent
            )
            self.assertRegex(first_lock.name, r"^[0-9a-f]{64}\.lock$")
            self.assertNotEqual(first_lock.name, second_lock.name)

            other_change = roots[0] / "openspec" / "changes" / "other" / "tasks.md"
            self.assertNotEqual(
                first_lock.name,
                workflow_control._task_lock_path(other_change).name,
            )

    def test_existing_legacy_lock_is_read_only_compatibility_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            path = root / "tasks.md"
            legacy = root / ".tasks.md.lock"
            legacy.write_bytes(b"legacy-lock")
            before = legacy.read_bytes()

            with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                with workflow_control._task_write_lock(path, 0):
                    pass

            self.assertEqual(before, legacy.read_bytes())
            self.assertIn("仅兼容加锁读取", stderr.getvalue())
            self.assertTrue(workflow_control._task_lock_path(path).is_file())

    def test_invalid_lock_timeout_fails_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            original = tasks_text({1: "进行中"}, {1: []})
            path.write_text(original, encoding="utf-8")
            for timeout in ("-1", "nan", "inf", "-inf"):
                with self.subTest(timeout=timeout):
                    result = workflow_control.main(
                        [
                            str(path),
                            "event",
                            "1",
                            "failure",
                            "--write",
                            f"--lock-timeout={timeout}",
                        ]
                    )
                    self.assertEqual(2, result)
                    self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_windows_try_lock_reraises_unexpected_os_error(self) -> None:
        stream = mock.Mock()
        locking = mock.Mock(side_effect=OSError(errno.EIO, "I/O error"))
        fake_msvcrt = types.SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
        with mock.patch.object(workflow_control.os, "name", "nt"), mock.patch.dict(
            sys.modules, {"msvcrt": fake_msvcrt}
        ):
            with self.assertRaisesRegex(OSError, "I/O error"):
                workflow_control._try_lock(stream)

    def test_windows_try_lock_treats_access_denied_as_contention(self) -> None:
        stream = mock.Mock()
        locking = mock.Mock(side_effect=OSError(errno.EACCES, "lock violation"))
        fake_msvcrt = types.SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=locking)
        with mock.patch.object(workflow_control.os, "name", "nt"), mock.patch.dict(
            sys.modules, {"msvcrt": fake_msvcrt}
        ):
            self.assertFalse(workflow_control._try_lock(stream))

    def test_reason_with_backslashes_does_not_corrupt_state_line(self) -> None:
        for reason in (r"C:\1foo", r"\g<0>", r"\1\2"):
            with self.subTest(reason=reason):
                text = tasks_text({1: "进行中"}, {1: []}, attempts=2)
                tasks = lint_task_deps.parse_tasks(text)
                decision = workflow_control.apply_event(tasks, 1, "failure", reason)
                updated = workflow_control.update_task_state(text, decision)
                self.assertIn(f"- 状态：需人工（{reason}）", updated)
                reparsed = lint_task_deps.parse_tasks(updated)
                self.assertEqual(
                    "需人工",
                    workflow_control._states(reparsed)[1],
                )

    def test_manual_event_requires_reason(self) -> None:
        tasks = lint_task_deps.parse_tasks(tasks_text({1: "进行中"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "原因"):
            workflow_control.apply_event(tasks, 1, "manual", "")

    def test_manual_event_moves_to_manual_without_consuming_attempts(
        self,
    ) -> None:
        tasks = lint_task_deps.parse_tasks(
            tasks_text({1: "进行中"}, {1: []}, attempts=1)
        )
        decision = workflow_control.apply_event(
            tasks, 1, "manual", "verify 门禁自身出错"
        )
        self.assertEqual("需人工", decision.state)
        self.assertEqual("manual", decision.control_stage)
        self.assertEqual(1, decision.attempts)

    def test_manual_resolved_event_completes_manual_task(self) -> None:
        text = tasks_text({1: "需人工"}, {1: []})
        text = text.replace("- attempts：0", "- attempts：0\n- control_stage：manual")
        tasks = lint_task_deps.parse_tasks(text)
        decision = workflow_control.apply_event(
            tasks, 1, "manual_resolved", "已人工修复并合并"
        )
        self.assertEqual("完成", decision.state)
        self.assertEqual("completed", decision.control_stage)

    def test_plan_recovery_manual_and_merged_completes(self) -> None:
        tasks = lint_task_deps.parse_tasks(tasks_text({1: "需人工"}, {1: []}))
        actions = workflow_control.plan_recovery(tasks, {1})
        self.assertEqual(
            ("complete", "任务已人工解决并合并"),
            (actions[0].action, actions[0].reason),
        )

    def test_plan_recovery_manual_and_unmerged_returns_manual_action(
        self,
    ) -> None:
        tasks = lint_task_deps.parse_tasks(tasks_text({1: "需人工"}, {1: []}))
        actions = workflow_control.plan_recovery(tasks, set())
        self.assertEqual(
            ("manual", "等待人工处理，处理并合并后重跑 recover"),
            (actions[0].action, actions[0].reason),
        )

    def test_plan_recovery_rejects_contradicting_merge_facts(self) -> None:
        pending = lint_task_deps.parse_tasks(tasks_text({1: "未开始"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "矛盾"):
            workflow_control.plan_recovery(pending, {1})
        blocked = lint_task_deps.parse_tasks(tasks_text({1: "阻塞"}, {1: []}))
        with self.assertRaisesRegex(ValueError, "矛盾"):
            workflow_control.plan_recovery(blocked, {1})

    def test_dispatchable_and_recovery_fail_closed_on_cycle(self) -> None:
        cyclic = lint_task_deps.parse_tasks(
            tasks_text({1: "未开始", 2: "未开始"}, {1: [2], 2: [1]})
        )
        with self.assertRaisesRegex(ValueError, "循环"):
            workflow_control.dispatchable_tasks(cyclic)
        with self.assertRaisesRegex(ValueError, "循环"):
            workflow_control.plan_recovery(cyclic, set())

    def test_missing_status_field_fails_closed(self) -> None:
        text = "### 任务 1：测试\n- depends_on：[]\n"
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "缺少合法状态"):
            workflow_control._states(tasks)

    def test_build_waves_scales_to_hundred_tasks(self) -> None:
        states = {task_id: "未开始" for task_id in range(1, 101)}
        dependencies = {1: []}
        for task_id in range(2, 101):
            dependencies[task_id] = [task_id - 1]
        tasks = lint_task_deps.parse_tasks(tasks_text(states, dependencies))
        waves = workflow_control.build_waves(tasks)
        self.assertEqual([[task_id] for task_id in range(1, 101)], waves)

    def test_update_task_state_preserves_existing_indentation(self) -> None:
        text = (
            "### 任务 1：测试\n\n"
            "  - 状态：进行中\n"
            "  - attempts：2\n"
            "  - depends_on：[]\n"
        )
        tasks = lint_task_deps.parse_tasks(text)
        decision = workflow_control.apply_event(tasks, 1, "failure")
        updated = workflow_control.update_task_state(text, decision)
        self.assertIn("  - 状态：需人工", updated)
        self.assertIn("  - attempts：3", updated)

    def test_update_task_state_preserves_existing_control_stage_indentation(
        self,
    ) -> None:
        text = (
            "### 任务 1：测试\n\n"
            "  - 状态：进行中\n"
            "  - attempts：2\n"
            "  - control_stage：running\n"
            "  - depends_on：[]\n"
        )
        tasks = lint_task_deps.parse_tasks(text)
        decision = workflow_control.apply_event(tasks, 1, "quality_passed")
        updated = workflow_control.update_task_state(text, decision)
        self.assertIn("  - control_stage：quality_passed", updated)

    def test_load_strips_bom_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tasks.md"
            path.write_bytes(tasks_text({1: "未开始"}, {1: []}).encode("utf-8-sig"))
            text, tasks = workflow_control._load(path)
            self.assertFalse(text.startswith("﻿"))
            self.assertIn(1, tasks)

    def test_attempts_rejects_non_decimal_digit_characters(self) -> None:
        text = tasks_text({1: "进行中"}, {1: []}).replace(
            "- attempts：0", "- attempts：¹"
        )
        tasks = lint_task_deps.parse_tasks(text)
        self.assertTrue("¹".isdigit())
        self.assertFalse("¹".isdecimal())
        with self.assertRaisesRegex(ValueError, "非法 attempts"):
            workflow_control._attempts(tasks[1])


class ApprovalGateVocabularyTest(unittest.TestCase):
    """change 2039：词表与 Production 逐项一致，不新建第二套。"""

    def test_escalation_conditions_equal_production(self) -> None:
        self.assertEqual(
            validate_change.ESCALATION_CONDITIONS,
            workflow_control.ESCALATION_CONDITIONS,
        )

    def test_approval_modes_equal_production(self) -> None:
        self.assertEqual(
            validate_change.APPROVAL_MODES, workflow_control.APPROVAL_MODES
        )

    def test_field_regexes_match_identically(self) -> None:
        samples = [
            "- Escalation: scope-change, irreversible\n",
            "- Approval: granted (scope-change)\n",
            "> 批准模式: per-task\n",
        ]
        for tooling_re, production_re in (
            (workflow_control.ESCALATION_RE, validate_change.ESCALATION_RE),
            (workflow_control.APPROVAL_RE, validate_change.APPROVAL_RE),
            (workflow_control.APPROVAL_MODE_RE, validate_change.APPROVAL_MODE_RE),
        ):
            for sample in samples:
                self.assertEqual(
                    bool(production_re.search(sample)),
                    bool(tooling_re.search(sample)),
                    (production_re.pattern, sample),
                )


def escalated_tasks_text(
    escalation: str = "- Escalation: scope-change",
    approval: str = "",
    mode: str = "",
) -> str:
    """构造带升级声明的两任务文档：任务 1 完成，任务 2 进行中。"""
    header = "# 实施任务清单\n\n"
    if mode:
        header += f"> 批准模式: {mode}\n\n"
    return (
        header
        + "### 任务 1：甲\n- 状态：完成\n- attempts：0\n- depends_on：[]\n"
        + "### 任务 2：乙\n- 状态：进行中\n- attempts：0\n- depends_on：Task 1\n"
        + (escalation + "\n" if escalation else "")
        + (approval + "\n" if approval else "")
    )


class EscalateTransitionTest(unittest.TestCase):
    """进入与恢复转移：语义与 manual 系明确区分，读侧恒 5 态。"""

    def test_escalate_enters_awaiting_approval_via_canonical_state(self) -> None:
        tasks = lint_task_deps.parse_tasks(escalated_tasks_text())
        decision = workflow_control.apply_event(tasks, 2, "escalate")
        # 持久化映射：状态写回规范态「需人工」，待批准经 control_stage 区分
        self.assertEqual("需人工", decision.state)
        self.assertEqual("awaiting_approval", decision.control_stage)
        self.assertIn("待批准 scope-change", decision.reason)

    def test_escalate_requires_declared_condition(self) -> None:
        tasks = lint_task_deps.parse_tasks(escalated_tasks_text(escalation=""))
        with self.assertRaisesRegex(ValueError, "未声明升级条件"):
            workflow_control.apply_event(tasks, 2, "escalate")

    def test_escalate_rejects_illegal_condition(self) -> None:
        tasks = lint_task_deps.parse_tasks(
            escalated_tasks_text(escalation="- Escalation: bogus-id")
        )
        with self.assertRaisesRegex(ValueError, "非法条件"):
            workflow_control.apply_event(tasks, 2, "escalate")

    def test_approval_granted_resumes_with_consistent_evidence(self) -> None:
        text = escalated_tasks_text(approval="- Approval: granted (scope-change)")
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        decision = workflow_control.apply_event(tasks, 2, "approval_granted")
        self.assertEqual("进行中", decision.state)
        self.assertEqual("running", decision.control_stage)

    def test_approval_granted_fails_closed_on_pending(self) -> None:
        text = escalated_tasks_text(approval="- Approval: pending (scope-change)")
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "尚未获批准"):
            workflow_control.apply_event(tasks, 2, "approval_granted")

    def test_approval_granted_fails_closed_on_missing_evidence(self) -> None:
        text = escalated_tasks_text()
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "缺少已批准的 Approval"):
            workflow_control.apply_event(tasks, 2, "approval_granted")

    def test_approval_granted_fails_closed_on_condition_mismatch(self) -> None:
        text = escalated_tasks_text(approval="- Approval: granted (irreversible)")
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "不一致"):
            workflow_control.apply_event(tasks, 2, "approval_granted")

    def test_approval_granted_fails_closed_on_misplaced_declaration(self) -> None:
        text = escalated_tasks_text(approval="  - Approval: granted (scope-change)")
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "格式错位"):
            workflow_control.apply_event(tasks, 2, "approval_granted")

    def test_recovery_distinguishes_awaiting_approval_from_manual(self) -> None:
        text = escalated_tasks_text()
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        actions = {a.task_id: a for a in workflow_control.plan_recovery(tasks, set())}
        self.assertEqual("await_approval", actions[2].action)

    def test_awaiting_approval_blocks_descendants(self) -> None:
        text = escalated_tasks_text() + "### 任务 3：丙\n- 状态：未开始\n- attempts：0\n- depends_on：Task 2\n"
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        decisions = workflow_control.propagate_blocked(tasks)
        self.assertIn(3, [d.task_id for d in decisions])

    def test_awaiting_approval_is_not_dispatchable(self) -> None:
        text = escalated_tasks_text()
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([], workflow_control.dispatchable_tasks(tasks))

    def test_read_side_states_stay_five(self) -> None:
        self.assertEqual(5, len(lint_task_deps.TASK_STATES))
        self.assertNotIn("待批准", lint_task_deps.TASK_STATES)
        self.assertIsNone(lint_task_deps.parse_state("待批准"))
        # 持久化后的文本读侧仍解析为「需人工」
        text = escalated_tasks_text()
        tasks = lint_task_deps.parse_tasks(text)
        paused = workflow_control.apply_event(tasks, 2, "escalate")
        text = workflow_control.update_task_state(text, paused)
        self.assertEqual("需人工", lint_task_deps.parse_state(
            lint_task_deps.field(lint_task_deps.parse_tasks(text)[2]["body"], "状态")
        ))


class ApprovalGateTest(unittest.TestCase):
    """merge_success 批准门：零触发、risk-triggered 与 per-task 的失败关闭。"""

    def test_zero_trigger_merge_success_unchanged(self) -> None:
        text = escalated_tasks_text(escalation="")
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([], workflow_control.approval_gate_errors(text, tasks, 2))

    def test_escalated_task_requires_approval_to_merge(self) -> None:
        text = escalated_tasks_text()
        tasks = lint_task_deps.parse_tasks(text)
        self.assertTrue(workflow_control.approval_gate_errors(text, tasks, 2))

    def test_escalated_task_merges_with_granted_approval(self) -> None:
        text = escalated_tasks_text(approval="- Approval: granted (scope-change)")
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([], workflow_control.approval_gate_errors(text, tasks, 2))

    def test_per_task_mode_requires_approval_without_escalation(self) -> None:
        text = escalated_tasks_text(escalation="", mode="per-task")
        tasks = lint_task_deps.parse_tasks(text)
        errors = workflow_control.approval_gate_errors(text, tasks, 2)
        self.assertTrue(any("per-task-mode" in e for e in errors), errors)

    def test_per_task_mode_passes_with_per_task_approval(self) -> None:
        text = escalated_tasks_text(
            escalation="",
            approval="- Approval: granted (per-task-mode)",
            mode="per-task",
        )
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual([], workflow_control.approval_gate_errors(text, tasks, 2))

    def test_orphan_approval_record_fails_closed(self) -> None:
        text = escalated_tasks_text(
            escalation="", approval="- Approval: granted (无)"
        )
        tasks = lint_task_deps.parse_tasks(text)
        errors = workflow_control.approval_gate_errors(text, tasks, 2)
        self.assertTrue(any("未声明 Escalation" in e for e in errors), errors)

    def test_misplaced_mode_declaration_fails_closed(self) -> None:
        text = escalated_tasks_text(escalation="").replace(
            "### 任务 1", "- 批准模式: per-task\n\n### 任务 1"
        )
        tasks = lint_task_deps.parse_tasks(text)
        with self.assertRaisesRegex(ValueError, "批准模式"):
            workflow_control.approval_gate_errors(text, tasks, 2)

    def test_cross_track_read_consistency(self) -> None:
        """同一份 tasks.md，两轨对升级与批准字段的读取结果一致。"""
        cases = [
            escalated_tasks_text(),
            escalated_tasks_text(approval="- Approval: granted (scope-change)"),
            escalated_tasks_text(approval="- Approval: pending (scope-change)"),
            escalated_tasks_text(approval="- Approval: granted (irreversible)"),
        ]
        for text in cases:
            body = lint_task_deps.parse_tasks(text)[2]["body"]
            # 字段命中数一致
            self.assertEqual(
                len(list(validate_change.ESCALATION_RE.finditer(body))),
                len(list(workflow_control.ESCALATION_RE.finditer(body))),
                text,
            )
            self.assertEqual(
                len(list(validate_change.APPROVAL_RE.finditer(body))),
                len(list(workflow_control.APPROVAL_RE.finditer(body))),
                text,
            )
            # 条件集合解析一致
            production_esc_match = validate_change.ESCALATION_RE.search(body)
            tooling_esc_match = workflow_control.ESCALATION_RE.search(body)
            self.assertEqual(
                production_esc_match is None, tooling_esc_match is None, text
            )
            if production_esc_match is not None:
                self.assertEqual(
                    validate_change._condition_set(production_esc_match.group(1)),
                    workflow_control._condition_set(tooling_esc_match.group(1)),
                    text,
                )
            production_app_match = validate_change.APPROVAL_RE.search(body)
            tooling_app_match = workflow_control.APPROVAL_RE.search(body)
            self.assertEqual(
                production_app_match is None, tooling_app_match is None, text
            )
            if production_app_match is not None:
                self.assertEqual(
                    validate_change._approval_conditions(
                        production_app_match.group("status")
                    ),
                    workflow_control._approval_conditions(
                        tooling_app_match.group("status")
                    ),
                    text,
                )


if __name__ == "__main__":
    unittest.main()
