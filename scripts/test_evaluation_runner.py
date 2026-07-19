"""Tests for deterministic core Agent behavior evaluation."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import evaluation_runner
import runtime_schema

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "evaluation" / "baseline" / "core-agent-behavior.json"
METADATA = {
    "run_id": "eval-run",
    "profile": "tooling",
    "harness": "test",
    "model": "test-model",
    "commit_sha": "1" * 40,
    "config_digest": "sha256:" + "2" * 64,
    "created_at": "2026-07-19T12:00:00Z",
}


def load_baseline() -> dict:
    """Load the committed core regression baseline."""
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def passing_observation(
    case: evaluation_runner.EvalCase,
) -> evaluation_runner.Observation:
    """Return the exact deterministic signals required by one compiled case."""
    transcript = ""
    signals = []
    if case.dimension == "should-trigger":
        transcript = f"Using {case.skill}"
    elif case.dimension == "boundary":
        if "workflow-quick-design" in case.expected:
            transcript = "Using workflow-quick-design"
        elif "先澄清" in case.expected:
            signals.append("action=clarify")
        elif "先定位" in case.expected:
            signals.append("route=troubleshooting")
        elif "Fast-Path" in case.expected:
            signals.append("route=fast-path")
        else:
            signals.append("action=context-dependent")
    elif case.dimension == "profile-routing":
        profiles = {"P-1": "lightweight", "P-2": "standard", "P-3": "strict"}
        reviewers = {
            "P-1": "comprehensive-reviewer",
            "P-2": "comprehensive-reviewer",
            "P-3": "full-5-reviewers",
        }
        signals.extend(
            (
                f"review-profile={profiles[case.local_id]}",
                f"reviewer={reviewers[case.local_id]}",
            )
        )
    else:
        signals.extend(
            f"{key}={value}"
            for key, value in evaluation_runner._SIGNAL_PATTERN.findall(case.expected)
        )
    return evaluation_runner.Observation(transcript, tuple(signals))


class EvaluationRunnerTest(unittest.TestCase):
    """Cover Markdown compilation, execution, schema, and regression gates."""

    def test_compiles_all_existing_sources_and_required_dimensions(self) -> None:
        cases = evaluation_runner.compile_core_cases(REPO_ROOT)
        self.assertEqual(42, len(cases))
        self.assertEqual(
            set(evaluation_runner.DIMENSIONS), {case.dimension for case in cases}
        )
        sources = {case.source_path for case in cases}
        self.assertEqual(set(evaluation_runner.DEFAULT_CASE_PATHS), sources)

    def test_core_cases_execute_to_versioned_machine_results(self) -> None:
        cases = evaluation_runner.compile_core_cases(REPO_ROOT)
        results, summary = evaluation_runner.run_evaluation(
            cases, passing_observation, METADATA, load_baseline()
        )
        self.assertEqual("PASS", summary["verdict"])
        self.assertEqual(len(cases), len(results))
        for result in results:
            runtime_schema.validate_document(result)
            self.assertEqual("PASS", result["payload"]["verdict"])

    def test_one_dimension_regression_cannot_be_masked_by_other_passes(self) -> None:
        cases = evaluation_runner.compile_core_cases(REPO_ROOT)

        def one_failure(
            case: evaluation_runner.EvalCase,
        ) -> evaluation_runner.Observation:
            if case.case_id == "workflow-code-generation:R-1":
                return evaluation_runner.Observation("", ())
            return passing_observation(case)

        _, summary = evaluation_runner.run_evaluation(
            cases, one_failure, METADATA, load_baseline()
        )
        self.assertEqual("FAIL", summary["verdict"])
        self.assertEqual("FAIL", summary["dimensions"]["recovery"]["verdict"])
        self.assertEqual("PASS", summary["dimensions"]["should-trigger"]["verdict"])
        self.assertEqual("PASS", summary["dimensions"]["profile-routing"]["verdict"])

    def test_case_count_decrease_fails_only_affected_dimension(self) -> None:
        cases = [
            case
            for case in evaluation_runner.compile_core_cases(REPO_ROOT)
            if case.case_id != "workflow-code-generation:E-2"
        ]
        _, summary = evaluation_runner.run_evaluation(
            cases, passing_observation, METADATA, load_baseline()
        )
        self.assertEqual("FAIL", summary["verdict"])
        self.assertEqual("FAIL", summary["dimensions"]["evidence-skipping"]["verdict"])

    def test_adapter_error_becomes_error_result_and_closed_gate(self) -> None:
        case = evaluation_runner.compile_core_cases(REPO_ROOT)[0]
        baseline = {
            "schema_version": 1,
            "dimensions": {
                case.dimension: {"minimum_cases": 1, "minimum_pass_rate": 1.0}
            },
        }
        results, summary = evaluation_runner.run_evaluation(
            [case],
            lambda unused: evaluation_runner.Observation("", (), "adapter-failed"),
            METADATA,
            baseline,
        )
        self.assertEqual("ERROR", results[0]["payload"]["verdict"])
        self.assertEqual("FAIL", summary["verdict"])

    def test_outputs_include_jsonl_json_and_markdown(self) -> None:
        cases = evaluation_runner.compile_core_cases(REPO_ROOT)
        results, summary = evaluation_runner.run_evaluation(
            cases, passing_observation, METADATA, load_baseline()
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            evaluation_runner.write_outputs(output_dir, results, summary)
            lines = (
                (output_dir / "eval-results.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            self.assertEqual(len(results), len(lines))
            self.assertEqual("PASS", json.loads(lines[0])["payload"]["verdict"])
            self.assertEqual(
                "PASS",
                json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))[
                    "verdict"
                ],
            )
            self.assertIn(
                "Agent 行为评测摘要",
                (output_dir / "summary.md").read_text(encoding="utf-8"),
            )

    def test_subprocess_adapter_uses_unified_json_contract(self) -> None:
        adapter_source = """
import json
import sys
request = json.load(sys.stdin)
case = request["payload"]
json.dump({"transcript": "Using " + case["skill"], "signals": []}, sys.stdout)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = Path(temp_dir) / "adapter.py"
            adapter.write_text(adapter_source, encoding="utf-8")
            case = next(
                item
                for item in evaluation_runner.compile_core_cases(REPO_ROOT)
                if item.dimension == "should-trigger"
            )
            observation = evaluation_runner.SubprocessAdapter(
                [sys.executable, str(adapter)]
            )(case)
            self.assertEqual(f"Using {case.skill}", observation.transcript)
            self.assertEqual("", observation.error)


if __name__ == "__main__":
    unittest.main()
