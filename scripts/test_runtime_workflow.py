"""End-to-end tests for runtime protocol wiring into workflow delivery."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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
import check_delivery
import runtime_workflow


class RuntimeWorkflowTest(unittest.TestCase):
    """Prove startup, task quality, Manifest, and Trust Gate form one chain."""

    def _commit(self, repo: Path, message: str) -> str:
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
                message,
            ],
            check=True,
        )
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()

    def test_complete_workflow_produces_reachable_trusted_evidence(self) -> None:
        self._complete_workflow(0)

    def test_retried_workflow_retains_failed_attempt_evidence(self) -> None:
        self._complete_workflow(2)

    def _complete_workflow(self, failures: int) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / ".gitignore").write_text(".agentic-framework/\n", encoding="utf-8")
            (repo / "code.py").write_text("print('v1')\n", encoding="utf-8")
            base = self._commit(repo, "base")
            tasks = repo / "tasks.md"
            spec = repo / "spec.md"
            agents = repo / "AGENTS.md"
            skill = repo / "SKILL.md"
            tasks.write_text(
                "### 任务 1：实现\n"
                "- 状态：完成\n"
                f"- attempts：{failures}\n"
                "- depends_on：[]\n"
                "- review_profile：strict\n"
                "- context_files：`spec.md`\n"
                "- 文件：`code.py`\n"
                "- verification：unit\n"
                "- artifacts：report\n",
                encoding="utf-8",
            )
            spec.write_text("**状态**: Archived\n\n# Spec\n", encoding="utf-8")
            agents.write_text("# Rules\n", encoding="utf-8")
            skill.write_text("# Workflow\n", encoding="utf-8")
            (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
            head = self._commit(repo, "change")
            declaration = Path(__file__).resolve().parents[1] / "harness/capabilities/codex.json"
            adapter = (
                "import json,sys; request=json.load(sys.stdin); "
                "caps={name:{'status':'supported','evidence':'test'} "
                "for name in request['payload']['capabilities']}; "
                "json.dump({'contract_version':1,'harness':'codex','capabilities':caps},sys.stdout)"
            )
            run_dir = repo / ".agentic-framework" / "runs" / "run-1"
            context = runtime_workflow.initialize_run(
                repo,
                run_dir,
                run_id="run-1",
                profile="tooling",
                harness="codex",
                commit_sha=head,
                base_commit_sha=base,
                max_attempts=2,
                verify_config=None,
                tasks_path=tasks,
                task_ids=["1"],
                spec_path=spec,
                agents_path=agents,
                skill_path=skill,
                declaration_path=declaration,
                adapter_command=[sys.executable, "-c", adapter],
                required_capabilities=["subagents"],
                optional_capabilities=["lifecycle_hooks"],
            )
            verify = runtime_workflow.envelope(
                context,
                "verify-report",
                f"verify-1-{failures + 1}",
                {
                    "verdict": "PASS",
                    "total": 1,
                    "errors": 0,
                    "violations": 0,
                    "spec_drift": None,
                    "warnings": [],
                    "results": [],
                },
                "workflow-verification",
                task_id="1",
                attempt=failures + 1,
            )
            for attempt in range(1, failures + 1):
                runtime_workflow.record_task_control(run_dir, "1", attempt, "start", "", "running")
                failed = dict(verify, artifact_id=f"verify-1-{attempt}", attempt=attempt,
                              payload={**verify["payload"], "verdict": "FAIL", "errors": 1})
                runtime_workflow._write_artifact(run_dir, failed)
                runtime_workflow.record_task_control(run_dir, "1", attempt, "failure", "test failure", "running")
            verify_path = runtime_workflow._write_artifact(run_dir, verify)
            runtime_workflow.record_quality_passed(run_dir, verify_path, "1", failures + 1)
            run_verify = runtime_workflow.envelope(
                context,
                "verify-report",
                "verify-run",
                {
                    "verdict": "PASS",
                    "total": 1,
                    "errors": 0,
                    "violations": 0,
                    "spec_drift": None,
                    "warnings": [],
                    "results": [],
                },
                "workflow-verification",
            )
            runtime_workflow._write_artifact(run_dir, run_verify)
            review = runtime_workflow.envelope(
                context,
                "review-report",
                "review-run",
                {
                    "verdict": "PASS",
                    "p0_count": 0,
                    "p1_count": 0,
                    "scope": "run",
                    "review_profile": "strict",
                    "round": 0,
                    "implementer_actor": "owner-agent",
                    "judge_actor": "independent-judge",
                    "independence_basis": "process-separated-agent",
                },
                "workflow-code-review",
            )
            review_path = runtime_workflow._write_artifact(run_dir, review)

            original_replace = runtime_workflow.os.replace
            def interrupt_snapshot(source, destination):
                if Path(destination).name == "code.diff":
                    raise OSError("snapshot publish interrupted")
                return original_replace(source, destination)
            with mock.patch.object(runtime_workflow.os, "replace", side_effect=interrupt_snapshot):
                with self.assertRaisesRegex(OSError, "snapshot publish interrupted"):
                    runtime_workflow.finalize_run(repo, run_dir, review_path, [
                        {"task_id": "1", "state": "completed", "attempts": failures}
                    ])
            self.assertFalse((run_dir / "snapshots/code.diff").exists())

            result = check_delivery.main(
                [
                    "--repo",
                    str(repo),
                    "--run-dir",
                    str(run_dir),
                    "--tasks",
                    str(tasks),
                    "--spec",
                    str(spec),
                    "--review-report",
                    str(review_path),
                    "--knowledge-impact",
                    "none",
                    "--knowledge-impact-reason",
                    "test runtime has no lasting knowledge impact",
                ]
            )
            manifest = json.loads(
                (run_dir / "run-manifest.json").read_text(encoding="utf-8")
            )

            self.assertEqual(0, result)
            self.assertIn(
                "code-result",
                {item["artifact_type"] for item in manifest["payload"]["artifacts"]},
            )
            self.assertTrue((run_dir / "events.jsonl").is_file())

            states = [{"task_id": "1", "state": "completed", "attempts": failures}]
            artifacts_before = {
                path.name: path.read_bytes()
                for path in (run_dir / "artifacts").glob("*.json")
            }
            journal_before = (run_dir / "events.jsonl").read_bytes()
            # A failed downstream gate must not prevent retrying the same inputs.
            with mock.patch.object(
                runtime_workflow.runtime_trust, "validate_run",
                side_effect=RuntimeError("injected gate interruption"),
            ):
                with self.assertRaisesRegex(RuntimeError, "injected gate"):
                    runtime_workflow.finalize_run(repo, run_dir, review_path, states)
            self.assertEqual("PASS", runtime_workflow.finalize_run(
                repo, run_dir, review_path, states
            )["verdict"])
            self.assertEqual(journal_before, (run_dir / "events.jsonl").read_bytes())
            self.assertEqual(artifacts_before, {
                path.name: path.read_bytes()
                for path in (run_dir / "artifacts").glob("*.json")
            })
            with self.assertRaisesRegex(runtime_workflow.RuntimeWorkflowError, "conflict"):
                runtime_workflow.finalize_run(repo, run_dir, review_path, [
                    {"task_id": "1", "state": "manual", "attempts": failures}
                ])

    def test_finalize_rejects_non_terminal_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            context = {
                "run_id": "run-1",
                "profile": "tooling",
                "harness": "codex",
                "commit_sha": "1" * 40,
                "base_commit_sha": "0" * 40,
                "config_digest": "sha256:" + "2" * 64,
                "created_at": "2026-07-19T12:00:00Z",
            }
            (run_dir / "run-context.json").write_text(
                json.dumps(context), encoding="utf-8"
            )
            (run_dir / "snapshots").mkdir()
            spec_snapshot = run_dir / "snapshots" / "input-spec.md"
            spec_snapshot.write_text("# Spec\n", encoding="utf-8")
            spec_artifact = runtime_workflow.envelope(
                context,
                "input-artifact",
                "input-spec",
                {
                    "input_type": "spec",
                    "path": "snapshots/input-spec.md",
                    "content_digest": runtime_workflow.run_manifest.file_digest(
                        spec_snapshot
                    ),
                },
                "runtime-workflow",
            )
            runtime_workflow._write_artifact(run_dir, spec_artifact)
            verify = runtime_workflow.envelope(
                context,
                "verify-report",
                "verify-run",
                {
                    "verdict": "PASS",
                    "total": 1,
                    "errors": 0,
                    "violations": 0,
                    "spec_drift": None,
                    "warnings": [],
                    "results": [],
                },
                "workflow-verification",
            )
            runtime_workflow._write_artifact(run_dir, verify)
            review = runtime_workflow.envelope(
                context,
                "review-report",
                "review-run",
                {
                    "verdict": "PASS",
                    "p0_count": 0,
                    "p1_count": 0,
                    "scope": "run",
                    "review_profile": "strict",
                    "round": 0,
                    "implementer_actor": "owner-agent",
                    "judge_actor": "independent-judge",
                    "independence_basis": "process-separated-agent",
                },
                "workflow-code-review",
            )
            review_path = runtime_workflow._write_artifact(run_dir, review)
            with mock.patch.object(
                runtime_workflow, "subprocess_result", return_value=b""
            ):
                with self.assertRaisesRegex(
                    runtime_workflow.RuntimeWorkflowError,
                    "non_terminal_task_state:1:running",
                ):
                    runtime_workflow.finalize_run(
                        run_dir.parent,
                        run_dir,
                        review_path,
                        [{"task_id": "1", "state": "running", "attempts": 0}],
                    )

    def test_legacy_unbound_pass_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "run-context.json").write_text(
                json.dumps(
                    {
                        "run_id": "run-1",
                        "profile": "tooling",
                        "harness": "codex",
                        "commit_sha": "1" * 40,
                        "base_commit_sha": "0" * 40,
                        "config_digest": "sha256:" + "2" * 64,
                        "created_at": "2026-07-19T12:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            report = run_dir / "legacy.json"
            report.write_text('{"verdict":"PASS"}\n', encoding="utf-8")
            with self.assertRaisesRegex(
                runtime_workflow.RuntimeWorkflowError,
                "invalid_or_legacy_verify_report",
            ):
                runtime_workflow.validate_verify_artifact(
                    run_dir, report, "1", 1
                )


if __name__ == "__main__":
    unittest.main()
