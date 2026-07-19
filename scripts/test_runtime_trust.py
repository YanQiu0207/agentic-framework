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
    return envelope("event", f"event-{sequence}", payload, None)


class TrustRun:
    """Build one complete Run spanning Tasks 2 through 6 contracts."""

    def __init__(self, root: Path, include_override: bool = True):
        self.root = root
        self.fixture = RunFixture(root)
        review = self.fixture.documents["review"]
        review["task_id"] = None
        review["attempt"] = None
        review["payload"].update(
            {
                "scope": "run",
                "implementer_actor": "owner-agent",
                "judge_actor": "independent-judge-agent",
                "independence_basis": "process-separated-agent",
            }
        )
        write_json(root / "artifacts/review.json", review)

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
        write_json(root / "artifacts/capability.json", capability)
        self.manifest = self.fixture.generate()

        self.journal = root / "events.jsonl"
        run_journal.append_event(self.journal, journal_event(1, "run-started"))
        if include_override:
            run_journal.append_event(
                self.journal,
                journal_event(
                    2,
                    "user-override",
                    details={"reason": "用户承担风险并要求继续"},
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
            effect = journal_event(2, "artifact-produced", key="publish:artifact")
            _, appended = run_journal.append_event(run.journal, effect)
            retry = copy.deepcopy(effect)
            retry["artifact_id"] = "event-retry"
            retry["payload"]["event_id"] = "event-retry"
            retry["payload"]["sequence"] = 3
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

    def test_user_override_without_reason_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = TrustRun(Path(temp_dir), include_override=False)
            run_journal.append_event(run.journal, journal_event(2, "user-override"))
            run_journal.write_checkpoint(run.root, run.journal)
            with self.assertRaisesRegex(runtime_trust.TrustError, "user_override"):
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
