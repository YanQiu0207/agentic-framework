"""End-to-end threat tests for the minimum runtime Trust Model."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness_runtime
import run_journal
import run_manifest
import runtime_schema
import runtime_trust
from test_run_manifest import CREATED_AT, RunFixture, envelope, write_json

CLI_TIMEOUT_SECONDS = 10


def run_cli(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a test CLI without allowing an unbounded test wait."""
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=CLI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            f"command {command!r} exceeded {CLI_TIMEOUT_SECONDS} seconds"
        ) from error


def probe_report(run_id: str, subagents: str = "supported") -> dict:
    capabilities = {
        capability: {
            "status": subagents if capability == "subagents" else "supported",
            "evidence": f"probe:{capability}",
        }
        for capability in harness_runtime.CAPABILITIES
    }
    report = harness_runtime.gate_capabilities(
        {"schema_version": 1, "harness": "codex", "capabilities": capabilities},
        ["subagents"],
        ["lifecycle_hooks"],
    )
    report.update(
        {
            "run_id": run_id,
            "evidence_source": "runtime-adapter-probe",
            "declaration_capabilities": copy.deepcopy(capabilities),
        }
    )
    return report


def journal_event(
    sequence: int,
    event_type: str,
    *,
    key: str | None = None,
    details: dict | None = None,
    task_id: str | None = None,
    config_digest: str | None = None,
) -> dict:
    payload = {
        "event_id": f"event-{sequence}",
        "sequence": sequence,
        "event_type": event_type,
        "actor": "user" if event_type.startswith("user-") else "runtime",
        "occurred_at": CREATED_AT,
        "input_artifact_ids": [],
        "output_artifact_ids": [],
    }
    if key:
        payload["idempotency_key"] = key
    if details is not None:
        payload["details"] = details
    value = envelope("event", f"event-{sequence}", payload, task_id)
    if config_digest is not None:
        value["config_digest"] = config_digest
    return value


class TrustRun:
    """Build one complete Run spanning Tasks 2 through 6 contracts."""

    def __init__(self, root: Path, include_override: bool = True):
        self.root = root
        self.fixture = RunFixture(root)
        snapshots = root / "snapshots"
        snapshots.mkdir()
        self.run_config = runtime_schema.build_run_config(
            "tooling",
            "codex",
            "workflow-code-generation",
            2,
            None,
            ["subagents"],
            ["lifecycle_hooks"],
        )
        self.config_digest = runtime_schema.config_digest(self.run_config)
        run_config_path = snapshots / "run-config.json"
        write_json(run_config_path, self.run_config)
        tasks_path = snapshots / "tasks.md"
        tasks_path.write_text(
            "### 任务 3：Trust Test\n\n"
            "- depends_on：[]\n"
            "- review_profile：strict\n"
            "- context_files：`proposal.md`\n"
            "- 文件：`scripts/runtime_trust.py`\n"
            "- verification：unit\n"
            "- artifacts：report\n"
            "- attempts：0\n"
            "- 状态：完成\n",
            encoding="utf-8",
        )
        review = self.fixture.documents["review"]
        review["task_id"] = None
        review["attempt"] = None
        verify = self.fixture.documents["verify"]
        verify["task_id"] = None
        verify["attempt"] = None
        review["payload"].update(
            {
                "scope": "run",
                "implementer_actor": "owner-agent",
                "judge_actor": "independent-judge-agent",
                "independence_basis": "process-separated-agent",
            }
        )
        self.fixture.documents["run-config"] = envelope(
            "input-artifact",
            "run-config",
            {
                "input_type": "run-config",
                "path": "snapshots/run-config.json",
                "content_digest": run_manifest.file_digest(run_config_path),
            },
            None,
        )
        self.fixture.documents["task-plan"] = envelope(
            "input-artifact",
            "task-plan",
            {
                "input_type": "task-plan",
                "path": "snapshots/tasks.md",
                "content_digest": run_manifest.file_digest(tasks_path),
                "task_ids": ["3"],
            },
            None,
        )

        self.capability_path = root / "artifacts/capability-probe.json"
        write_json(self.capability_path, probe_report("run-1"))
        capability = envelope(
            "input-artifact",
            "capability",
            {
                "input_type": "capability-matrix",
                "path": "artifacts/capability-probe.json",
                "content_digest": run_manifest.file_digest(self.capability_path),
            },
            None,
        )
        self.fixture.documents["capability"] = capability
        for name, document in self.fixture.documents.items():
            document["config_digest"] = self.config_digest
            write_json(root / f"artifacts/{name}.json", document)
        self.fixture.metadata["config_digest"] = self.config_digest
        self.manifest = self.fixture.generate()

        self.journal = root / "events.jsonl"
        run_journal.append_event(
            self.journal,
            journal_event(1, "run-started", config_digest=self.config_digest),
        )
        for sequence, event_type in enumerate(
            ("task-started", "task-quality-passed", "task-merged"), 2
        ):
            run_journal.append_event(
                self.journal,
                journal_event(
                    sequence,
                    event_type,
                    task_id="3",
                    config_digest=self.config_digest,
                ),
            )
        if include_override:
            run_journal.append_event(
                self.journal,
                journal_event(
                    5,
                    "user-override",
                    details={"reason": "用户承担风险并要求继续"},
                    config_digest=self.config_digest,
                ),
            )
        run_journal.write_checkpoint(root, self.journal)

    def persist_manifest(self) -> None:
        write_json(self.root / "run-manifest.json", self.manifest)

    def replace_artifact(self, name: str, document: dict) -> None:
        self.fixture.rewrite_artifact(self.manifest, name, document)
        self.persist_manifest()

    def replace_capability(self, report: dict) -> None:
        write_json(self.capability_path, report)
        capability = copy.deepcopy(self.fixture.documents["capability"])
        capability["payload"]["content_digest"] = run_manifest.file_digest(
            self.capability_path
        )
        self.replace_artifact("capability", capability)


class RuntimeTrustTest(unittest.TestCase):
    def test_complete_run_passes_with_explicit_unprovable_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            report = runtime_trust.validate_run(run.root)
            self.assertEqual("PASS", report["verdict"])
            self.assertEqual("override", report["user_overrides"][0]["action"])
            self.assertIn(
                "reviewer-or-judge-semantic-correctness",
                report["unprovable_claims"],
            )
            self.assertIn(
                "integrity-against-a-fully-compromised-host",
                report["unprovable_claims"],
            )

    def test_forged_or_self_judged_strict_report_is_rejected(self) -> None:
        mutations = (
            {"implementer_actor": None},
            {"judge_actor": "owner-agent"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                run = TrustRun(Path(temp))
                review = copy.deepcopy(run.fixture.documents["review"])
                for field, value in mutation.items():
                    if value is None:
                        review["payload"].pop(field)
                    else:
                        review["payload"][field] = value
                run.replace_artifact("review", review)
                with self.assertRaises(runtime_trust.TrustError):
                    runtime_trust.validate_run(run.root)

    def test_replaced_artifact_and_cross_run_report_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            verify_path = run.root / "artifacts/verify.json"
            verify_path.write_text(
                verify_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(runtime_trust.TrustError, "digest_mismatch"):
                runtime_trust.validate_run(run.root)
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            review = copy.deepcopy(run.fixture.documents["review"])
            review["run_id"] = "other-run"
            run.replace_artifact("review", review)
            with self.assertRaisesRegex(runtime_trust.TrustError, "binding_run_id"):
                runtime_trust.validate_run(run.root)

    def test_duplicate_side_effect_is_deduplicated_or_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir), include_override=False)
            effect = journal_event(
                5,
                "artifact-produced",
                key="publish:artifact",
                config_digest=run.config_digest,
            )
            _, appended = run_journal.append_event(run.journal, effect)
            retry = copy.deepcopy(effect)
            retry["artifact_id"] = "event-retry"
            retry["payload"]["event_id"] = "event-retry"
            retry["payload"]["sequence"] = 6
            _, appended_again = run_journal.append_event(run.journal, retry)
            self.assertTrue(appended)
            self.assertFalse(appended_again)
            conflict = copy.deepcopy(retry)
            conflict["payload"]["output_artifact_ids"] = ["verify"]
            with self.assertRaisesRegex(run_journal.JournalError, "conflict"):
                run_journal.append_event(run.journal, conflict)

    def test_harness_capability_drift_fails_before_trust_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            run.replace_capability(probe_report("run-1", "unsupported"))
            with self.assertRaisesRegex(runtime_trust.TrustError, "capability_gate"):
                runtime_trust.validate_run(run.root)
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            report = probe_report("run-1")
            report["capabilities"]["lifecycle_hooks"]["status"] = "degraded"
            report["degradations"] = []
            run.replace_capability(report)
            with self.assertRaisesRegex(runtime_trust.TrustError, "degradations"):
                runtime_trust.validate_run(run.root)

    def test_capability_degradation_requires_matching_event_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir), include_override=False)
            capabilities = probe_report("run-1")["capabilities"]
            capabilities["lifecycle_hooks"]["status"] = "degraded"
            gated = harness_runtime.gate_capabilities(
                {
                    "schema_version": 1,
                    "harness": "codex",
                    "capabilities": capabilities,
                },
                ["subagents"],
                ["lifecycle_hooks"],
            )
            gated.update(
                {
                    "run_id": "run-1",
                    "evidence_source": "runtime-adapter-probe",
                    "declaration_capabilities": copy.deepcopy(capabilities),
                }
            )
            run.replace_capability(gated)
            with self.assertRaisesRegex(
                runtime_trust.TrustError, "degradation_event_mismatch"
            ):
                runtime_trust.validate_run(run.root)

            degradation = gated["degradations"][0]
            run_journal.append_event(
                run.journal,
                journal_event(
                    5,
                    "capability-degraded",
                    details={
                        key: degradation[key]
                        for key in ("capability", "status", "evidence")
                    },
                    config_digest=run.config_digest,
                ),
            )
            run_journal.write_checkpoint(run.root, run.journal)
            report = runtime_trust.validate_run(run.root)
            self.assertEqual(gated["degradations"], report["capability_degradations"])

    def test_user_override_without_reason_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir), include_override=False)
            run_journal.append_event(
                run.journal,
                journal_event(5, "user-override", config_digest=run.config_digest),
            )
            run_journal.write_checkpoint(run.root, run.journal)
            with self.assertRaisesRegex(runtime_trust.TrustError, "user_override"):
                runtime_trust.validate_run(run.root)

    def test_failed_verify_is_rejected_even_with_user_override(self) -> None:
        for verdict, errors, violations in (("FAIL", 0, 1), ("ERROR", 1, 0)):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                run = TrustRun(Path(temp))
                verify = copy.deepcopy(run.fixture.documents["verify"])
                verify["payload"].update(
                    {
                        "verdict": verdict,
                        "errors": errors,
                        "violations": violations,
                    }
                )
                run.replace_artifact("verify", verify)
                with self.assertRaisesRegex(runtime_trust.TrustError, "verify_gate"):
                    runtime_trust.validate_run(run.root)

    def test_capability_requirements_cannot_be_weakened_by_probe_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            report = probe_report("run-1")
            report["required_capabilities"] = []
            report["optional_capabilities"] = []
            run.replace_capability(report)
            with self.assertRaisesRegex(
                runtime_trust.TrustError, "required_capabilities"
            ):
                runtime_trust.validate_run(run.root)

    def test_reject_or_cancel_latest_user_decision_blocks_pass(self) -> None:
        for action in ("reject", "cancel"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temp:
                run = TrustRun(Path(temp), include_override=False)
                run_journal.append_event(
                    run.journal,
                    journal_event(
                        5,
                        f"user-{action}",
                        details={"reason": "用户终止运行"},
                        config_digest=run.config_digest,
                    ),
                )
                run_journal.write_checkpoint(run.root, run.journal)
                with self.assertRaisesRegex(runtime_trust.TrustError, f"user_{action}"):
                    runtime_trust.validate_run(run.root)

    def test_missing_task_event_is_rejected_by_trust_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            events = [
                item
                for item in run_journal.read_events(run.journal)
                if item["task_id"] is None
            ]
            for sequence, item in enumerate(events, 1):
                item["payload"]["sequence"] = sequence
            run.journal.write_bytes(
                b"".join(run_journal._canonical(item) + b"\n" for item in events)
            )
            for checkpoint in (run.root / "checkpoints").glob("*.json"):
                checkpoint.unlink()
            run_journal.write_checkpoint(run.root, run.journal)
            with self.assertRaisesRegex(runtime_trust.TrustError, "missing_task_event"):
                runtime_trust.validate_run(run.root)

    def test_cli_outputs_machine_report_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir))
            output = run.root / "trust-report.json"
            command = [
                sys.executable,
                str(Path(runtime_trust.__file__)),
                str(run.root),
                "--output",
                str(output),
            ]
            result = run_cli(command)
            self.assertEqual(0, result.returncode)
            self.assertEqual("PASS", json.loads(result.stdout)["verdict"])
            self.assertEqual(
                "PASS",
                json.loads(output.read_text(encoding="utf-8"))["verdict"],
            )

    def test_cli_timeout_reports_command_and_limit(self) -> None:
        command = ["python", "runtime_trust.py"]
        with mock.patch.object(
            subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(command, CLI_TIMEOUT_SECONDS),
        ):
            with self.assertRaisesRegex(
                AssertionError,
                r"runtime_trust\.py.*10 seconds",
            ):
                run_cli(command)


if __name__ == "__main__":
    unittest.main()
