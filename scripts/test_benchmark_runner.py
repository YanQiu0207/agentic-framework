"""Regression tests for real-task benchmark collection and reporting."""

import json
import tempfile
import unittest
from pathlib import Path

import benchmark_runner as runner


def case(task_id: str = "task-1", route: str = "fast-path") -> dict:
    return {
        "schema_version": 1,
        "task_id": task_id,
        "title": "测试任务",
        "route": route,
        "risk_level": "low",
        "acceptance_criteria": ["测试通过"],
    }


def outcome(task_id: str = "task-1", session: str = "s1") -> dict:
    return {
        "schema_version": 1,
        "task_id": task_id,
        "final_verdict": "accepted",
        "first_acceptance": True,
        "review": {"p0_count": 0, "p1_count": 1, "rounds": 2},
        "follow_up": {"window_days": 7, "status": "no-rework"},
        "session_refs": [{"source": "codex", "session": session}],
    }


class BenchmarkRunnerTest(unittest.TestCase):
    def test_validate_rejects_unknown_route(self) -> None:
        with self.assertRaises(runner.BenchmarkError):
            runner.validate_case(case(route="unknown"), outcome())

    def test_report_joins_outcome_to_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task_dir = root / "cases" / "task-1"
            task_dir.mkdir(parents=True)
            (task_dir / "case.json").write_text(json.dumps(case()), encoding="utf-8")
            (task_dir / "outcome.json").write_text(json.dumps(outcome()), encoding="utf-8")
            history = root / "history.jsonl"
            history.write_text(
                json.dumps({"source": "codex", "session": "s1", "wall_seconds": 100,
                            "idle_seconds": 25, "model_tokens": {"model": {"input": 2, "output": 3}}}) + "\n",
                encoding="utf-8",
            )
            report = runner.build_report(runner.load_records(root / "cases"), runner.load_history(history))
        summary = report["routes"]["fast-path"]
        self.assertEqual(1, summary["tasks"])
        self.assertEqual(1.0, summary["acceptance_rate"])
        self.assertEqual(75, summary["active_seconds"])
        self.assertEqual(3, summary["tokens"]["output"])

    def test_report_rejects_duplicate_session_assignment(self) -> None:
        records = [(case("task-1"), outcome("task-1", "same"), Path("one")),
                   (case("task-2"), outcome("task-2", "same"), Path("two"))]
        history = {("codex", "same"): {"wall_seconds": 1, "idle_seconds": 0}}
        with self.assertRaises(runner.BenchmarkError):
            runner.build_report(records, history)

    def test_report_rejects_negative_token_count(self) -> None:
        records = [(case(), outcome(), Path("one"))]
        history = {
            ("codex", "s1"): {
                "wall_seconds": 1,
                "idle_seconds": 0,
                "model_tokens": {"model": {"output": -1}},
            }
        }
        with self.assertRaises(runner.BenchmarkError):
            runner.build_report(records, history)
