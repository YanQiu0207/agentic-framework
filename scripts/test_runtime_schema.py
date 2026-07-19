"""Tests for the versioned agent runtime artifact contracts."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
import runtime_schema
import workflow_control

COMMIT_SHA = "1" * 40
DIGEST = "sha256:" + "2" * 64


def artifact(artifact_type: str, payload: dict, task_id: str | None = "2") -> dict:
    """Build a valid envelope for one payload contract."""
    return {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "artifact_id": "artifact-1",
        "run_id": "run-1",
        "task_id": task_id,
        "attempt": 1 if task_id is not None else None,
        "profile": "tooling",
        "harness": "codex",
        "producer": "test",
        "commit_sha": COMMIT_SHA,
        "config_digest": DIGEST,
        "created_at": "2026-07-19T12:00:00Z",
        "payload": payload,
    }


class RuntimeSchemaTest(unittest.TestCase):
    """Cover positive, negative, digest, association, and attempt cases."""

    def test_all_artifact_payload_types_validate(self) -> None:
        documents = [
            artifact(
                "run-manifest",
                {
                    "base_commit_sha": COMMIT_SHA,
                    "artifacts": [],
                    "tasks": [],
                    "relations": [],
                },
                None,
            ),
            artifact("task-state", {"state": "running", "attempts": 0}),
            artifact(
                "event",
                {
                    "event_id": "event-1",
                    "sequence": 1,
                    "event_type": "task-started",
                    "actor": "owner",
                    "occurred_at": "2026-07-19T12:00:00Z",
                    "input_artifact_ids": [],
                    "output_artifact_ids": [],
                },
            ),
            artifact(
                "review-report",
                {
                    "verdict": "PASS",
                    "p0_count": 0,
                    "p1_count": 0,
                    "scope": "task",
                    "review_profile": "strict",
                    "round": 0,
                },
            ),
            artifact(
                "verify-report",
                {
                    "verdict": "PASS",
                    "total": 1,
                    "errors": 0,
                    "violations": 0,
                    "spec_drift": None,
                    "warnings": [],
                    "results": [],
                },
            ),
            artifact(
                "eval-result",
                {
                    "case_id": "route-1",
                    "dimension": "should-trigger",
                    "verdict": "PASS",
                    "assertions": [],
                    "model": "test-model",
                    "evaluation_method": "deterministic-tier-1",
                },
                None,
            ),
            artifact(
                "input-artifact",
                {
                    "input_type": "spec",
                    "path": "openspec/changes/example/proposal.md",
                    "content_digest": DIGEST,
                },
                None,
            ),
        ]
        for document in documents:
            with self.subTest(artifact_type=document["artifact_type"]):
                runtime_schema.validate_document(document)

    def test_unknown_version_and_missing_required_field_fail_closed(self) -> None:
        document = artifact("task-state", {"state": "running", "attempts": 0})
        document["schema_version"] = 2
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(document)
        del document["artifact_id"]
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(document)

    def test_illegal_task_attempt_associations_fail_closed(self) -> None:
        run_level = artifact(
            "run-manifest",
            {
                "base_commit_sha": COMMIT_SHA,
                "artifacts": [],
                "tasks": [],
                "relations": [],
            },
            None,
        )
        run_level["attempt"] = 1
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(run_level)
        task_level = artifact("task-state", {"state": "running", "attempts": 0})
        task_level["attempt"] = None
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(task_level)
        mismatched = artifact("task-state", {"state": "running", "attempts": 1})
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(mismatched)

    def test_artifact_type_cannot_use_another_payload_schema(self) -> None:
        document = artifact("task-state", {"state": "running", "attempts": 0})
        document["artifact_type"] = "review-report"
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(document)

    def test_review_scope_must_match_task_association(self) -> None:
        document = artifact(
            "review-report",
            {
                "verdict": "PASS",
                "p0_count": 0,
                "p1_count": 0,
                "scope": "integration",
                "review_profile": "strict",
                "round": 0,
            },
        )
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.validate_document(document)

    def test_config_digest_is_canonical_and_has_fixed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = Path(temp_dir) / "first.json"
            second_path = Path(temp_dir) / "second.json"
            first_path.write_text('{"checks":[],"label":"中文"}', encoding="utf-8")
            second_path.write_text(
                '{\n  "label": "中文",\n  "checks": []\n}', encoding="utf-8"
            )
            first = runtime_schema.build_run_config(
                "tooling", "codex", "workflow-code-generation", 2, first_path
            )
            second = runtime_schema.build_run_config(
                "tooling", "codex", "workflow-code-generation", 2, second_path
            )
            self.assertEqual(
                runtime_schema.config_digest(first),
                runtime_schema.config_digest(second),
            )
            self.assertEqual(
                "sha256:39e034248e0915379a797dde4093341993b1c51f2b9439111043a182dc0870a3",
                runtime_schema.config_digest(first),
            )
            self.assertEqual(
                {"profile", "harness", "workflow", "max_attempts", "verify_config"},
                set(first),
            )
            changed = copy.deepcopy(first)
            changed["max_attempts"] = 3
            self.assertNotEqual(
                runtime_schema.config_digest(first),
                runtime_schema.config_digest(changed),
            )

    def test_missing_verify_config_uses_explicit_default(self) -> None:
        config = runtime_schema.build_run_config(
            "tooling", "codex", "workflow-code-generation", 2, None
        )
        self.assertEqual({"checks": []}, config["verify_config"])

    def test_attempt_mapping_covers_first_retry_and_manual(self) -> None:
        self.assertEqual(1, runtime_schema.attempt_for_attempts(0))
        tasks = lint_task_deps.parse_tasks(
            "### 任务 2：测试\n\n"
            "- 状态：进行中\n"
            "- attempts：0\n"
            "- depends_on：[]\n"
        )
        failed_attempts = workflow_control.apply_event(tasks, 2, "failure").attempts
        self.assertEqual(
            failed_attempts,
            runtime_schema.attempts_after_event(0, "failure"),
        )
        self.assertEqual(2, runtime_schema.attempt_for_attempts(failed_attempts))
        self.assertEqual(
            failed_attempts,
            runtime_schema.attempts_after_event(failed_attempts, "manual"),
        )
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.attempt_for_attempts(-1)
        with self.assertRaises(runtime_schema.RuntimeSchemaError):
            runtime_schema.attempt_for_attempts("0")

    def test_cli_validates_artifact_and_rejects_invalid_json(self) -> None:
        script = Path(__file__).with_name("runtime_schema.py")
        document = artifact("task-state", {"state": "running", "attempts": 0})
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            valid = subprocess.run(
                [sys.executable, str(script), "validate", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, valid.returncode)
            self.assertEqual("PASS", valid.stdout.strip())
            path.write_text("{invalid", encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, str(script), "validate", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, invalid.returncode)
            self.assertEqual("", invalid.stdout)


if __name__ == "__main__":
    unittest.main()
