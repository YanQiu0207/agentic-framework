"""Tests for durable Run event journal replay and recovery."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import run_journal

NOW = "2026-07-19T00:00:00Z"
SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64


def event(
    sequence: int,
    event_type: str = "task-started",
    *,
    attempt: int = 1,
    task_id: str | None = "1",
    key: str | None = None,
) -> dict:
    value = {
        "schema_version": 1,
        "artifact_type": "event",
        "artifact_id": f"event-{sequence}",
        "run_id": "run-1",
        "task_id": task_id,
        "attempt": attempt if task_id else None,
        "profile": "tooling",
        "harness": "codex",
        "producer": "runtime",
        "commit_sha": SHA,
        "config_digest": DIGEST,
        "created_at": NOW,
        "payload": {
            "event_id": f"event-{sequence}",
            "sequence": sequence,
            "event_type": event_type,
            "actor": "runtime",
            "occurred_at": NOW,
            "input_artifact_ids": [],
            "output_artifact_ids": [],
        },
    }
    if key:
        value["payload"]["idempotency_key"] = key
    return value


def manifest(state: str = "running", attempt: int = 1) -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "run-manifest",
        "artifact_id": "manifest-1",
        "run_id": "run-1",
        "task_id": None,
        "attempt": None,
        "profile": "tooling",
        "harness": "codex",
        "producer": "runtime",
        "commit_sha": SHA,
        "config_digest": DIGEST,
        "created_at": NOW,
        "payload": {
            "base_commit_sha": SHA,
            "artifacts": [],
            "tasks": [
                {
                    "task_id": "1",
                    "attempt": attempt,
                    "state": state,
                    "artifact_ids": [],
                }
            ],
            "relations": [],
        },
    }


def tasks(state: str = "进行中", attempts: int = 0) -> str:
    return f"""### 任务 1：测试

- depends_on：[]
- 文件：`scripts/example.py`
- review_profile：standard
- context_files：`proposal.md`
- verification：unit
- artifacts：report
- attempts：{attempts}
- 状态：{state}
"""


class RunJournalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.journal = self.root / "events.jsonl"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_atomic_append_has_stable_sequence_and_idempotent_side_effect(self) -> None:
        run_journal.append_event(self.journal, event(1))
        side_effect = event(2, "artifact-produced", key="artifact:1")
        _, appended = run_journal.append_event(self.journal, side_effect)
        duplicate = copy.deepcopy(side_effect)
        duplicate["artifact_id"] = "retry-event"
        duplicate["payload"]["event_id"] = "retry-event"
        duplicate["payload"]["sequence"] = 3
        _, appended_again = run_journal.append_event(self.journal, duplicate)

        self.assertTrue(appended)
        self.assertFalse(appended_again)
        self.assertEqual(2, run_journal.replay_journal(self.journal).sequence)
        self.assertTrue(self.journal.read_bytes().endswith(b"\n"))

    def test_idempotency_conflict_and_missing_key_fail_closed(self) -> None:
        first = event(1, "merge-completed", key="merge:1")
        run_journal.append_event(self.journal, first)
        conflict = event(2, "merge-completed", key="merge:1")
        conflict["payload"]["output_artifact_ids"] = ["different"]
        with self.assertRaisesRegex(run_journal.JournalError, "idempotency_conflict"):
            run_journal.append_event(self.journal, conflict)
        with self.assertRaisesRegex(run_journal.JournalError, "missing_idempotency"):
            run_journal.append_event(self.journal, event(2, "artifact-produced"))

    def test_idempotency_rejects_changed_immutable_envelope_bindings(self) -> None:
        first = event(1, "artifact-produced", key="artifact:1")
        run_journal.append_event(self.journal, first)
        mutations = {
            "schema_version": 2,
            "commit_sha": "c" * 40,
            "config_digest": "sha256:" + "d" * 64,
            "producer": "other-runtime",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                duplicate = copy.deepcopy(first)
                duplicate["artifact_id"] = f"retry-{field}"
                duplicate["payload"]["event_id"] = f"retry-{field}"
                duplicate["payload"]["sequence"] = 2
                duplicate[field] = value
                with self.assertRaises(run_journal.JournalError):
                    run_journal.append_event(self.journal, duplicate)

    def test_interrupted_replace_preserves_previous_journal(self) -> None:
        run_journal.append_event(self.journal, event(1))
        previous = self.journal.read_bytes()
        with mock.patch.object(run_journal.os, "replace", side_effect=OSError("stop")):
            with self.assertRaises(OSError):
                run_journal.append_event(self.journal, event(2, "task-quality-passed"))
        self.assertEqual(previous, self.journal.read_bytes())

    def test_replay_rejects_sequence_gap_and_torn_record(self) -> None:
        self.journal.write_bytes(run_journal._canonical(event(2)) + b"\n")
        with self.assertRaisesRegex(run_journal.JournalError, "sequence_mismatch"):
            run_journal.replay_journal(self.journal)
        self.journal.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(run_journal.JournalError, "torn_journal_record"):
            run_journal.replay_journal(self.journal)

    def test_failure_consumes_retry_and_next_event_uses_next_attempt(self) -> None:
        run_journal.append_event(self.journal, event(1, "task-failed"))
        run_journal.append_event(self.journal, event(2, "task-started", attempt=2))
        replay = run_journal.replay_journal(self.journal)
        self.assertEqual({"state": "running", "attempts": 1}, replay.tasks["1"])

    def test_checkpoint_allows_later_events_and_detects_tampering(self) -> None:
        run_journal.append_event(self.journal, event(1))
        checkpoint = run_journal.write_checkpoint(self.root, self.journal)
        run_journal.append_event(self.journal, event(2, "task-quality-passed"))
        run_journal.validate_checkpoint(
            checkpoint, run_journal.read_events(self.journal)
        )
        value = json.loads(checkpoint.read_text(encoding="utf-8"))
        value["journal_digest"] = DIGEST
        checkpoint.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(run_journal.JournalError, "checkpoint_content"):
            run_journal.validate_checkpoint(
                checkpoint, run_journal.read_events(self.journal)
            )

    def test_recovery_uses_journal_checkpoint_tasks_manifest_and_git(self) -> None:
        run_journal.append_event(self.journal, event(1))
        checkpoint = run_journal.write_checkpoint(self.root, self.journal)
        with mock.patch.object(run_journal.run_manifest, "validate_manifest"):
            actions = run_journal.recovery_plan(
                self.journal, checkpoint, tasks(), manifest(), set()
            )
            self.assertEqual("inspect", actions[0].action)

            cases = []
            wrong_event = run_journal.read_events(self.journal)[0]
            wrong_event["run_id"] = "other"
            other_journal = self.root / "other.jsonl"
            other_journal.write_bytes(run_journal._canonical(wrong_event) + b"\n")
            cases.append((other_journal, checkpoint, tasks(), manifest(), set()))
            cases.append(
                (self.journal, checkpoint, tasks(), manifest("completed"), set())
            )
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    with self.assertRaises(run_journal.JournalError):
                        run_journal.recovery_plan(*arguments)

    def test_recovery_validates_manifest_artifact_digests(self) -> None:
        run_journal.append_event(self.journal, event(1))
        checkpoint = run_journal.write_checkpoint(self.root, self.journal)
        with self.assertRaisesRegex(run_journal.JournalError, "manifest_evidence"):
            run_journal.recovery_plan(
                self.journal, checkpoint, tasks(), manifest(), set()
            )

    def test_recovery_rejects_git_fact_that_conflicts_with_tasks(self) -> None:
        run_journal.append_event(self.journal, event(1, "task-retried"))
        checkpoint = run_journal.write_checkpoint(self.root, self.journal)
        with mock.patch.object(run_journal.run_manifest, "validate_manifest"):
            with self.assertRaisesRegex(run_journal.JournalError, "git_tasks_conflict"):
                run_journal.recovery_plan(
                    self.journal,
                    checkpoint,
                    tasks("未开始"),
                    manifest("pending"),
                    {1},
                )

    def test_recovery_rejects_tasks_missing_from_any_state_source(self) -> None:
        run_journal.append_event(self.journal, event(1))
        checkpoint = run_journal.write_checkpoint(self.root, self.journal)
        cases = []
        manifest_with_extra = manifest()
        manifest_with_extra["payload"]["tasks"].append(
            {
                "task_id": "2",
                "attempt": 1,
                "state": "pending",
                "artifact_ids": [],
            }
        )
        cases.append((tasks(), manifest_with_extra, "missing_task_event:2"))
        cases.append(
            (
                tasks()
                + "\n### 任务 2：额外\n\n"
                + "- depends_on：[1]\n- 文件：`scripts/example.py`\n"
                + "- review_profile：standard\n- context_files：`proposal.md`\n"
                + "- verification：unit\n- artifacts：report\n"
                + "- attempts：0\n- 状态：未开始\n",
                manifest(),
                "missing_task_event:2",
            )
        )
        for tasks_text, value, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(
                run_journal.run_manifest, "validate_manifest"
            ):
                with self.assertRaisesRegex(run_journal.JournalError, expected):
                    run_journal.recovery_plan(
                        self.journal, checkpoint, tasks_text, value, set()
                    )

    def test_user_override_is_an_explicit_reasoned_event(self) -> None:
        base = event(1)
        envelope = {key: value for key, value in base.items() if key != "payload"}
        value = run_journal.make_user_action_event(
            envelope,
            event_id="user-1",
            sequence=1,
            action="override",
            reason="老板确认覆盖",
            occurred_at=NOW,
        )
        self.assertEqual("user-override", value["payload"]["event_type"])
        self.assertEqual("老板确认覆盖", value["payload"]["details"]["reason"])
        with self.assertRaisesRegex(run_journal.JournalError, "reason_required"):
            run_journal.make_user_action_event(
                envelope,
                event_id="user-2",
                sequence=2,
                action="retry",
                reason=" ",
                occurred_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
