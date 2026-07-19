"""Contract tests for Harness capability probing and adapters."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import harness_runtime
import runtime_schema

REPO_ROOT = Path(__file__).resolve().parents[1]


def probe_response(harness: str, states: dict[str, str] | None = None) -> dict:
    """Build a complete executable probe response."""
    states = states or {}
    return {
        "contract_version": 1,
        "harness": harness,
        "capabilities": {
            capability: {
                "status": states.get(capability, "supported"),
                "evidence": f"probe:{capability}",
            }
            for capability in harness_runtime.CAPABILITIES
        },
    }


class FakeAdapter:
    """Return one prebuilt probe response without product assumptions."""

    def __init__(self, response: dict):
        self.response = response

    def probe(self, harness: str) -> dict:
        del harness
        return self.response


class HarnessRuntimeTest(unittest.TestCase):
    """Cover vocabulary, runtime truth, fail-close, downgrade evidence, and CLI."""

    def test_codex_and_claude_use_same_unverified_vocabulary(self) -> None:
        declarations = []
        for harness in ("codex", "claude-code"):
            path = REPO_ROOT / "harness" / "capabilities" / f"{harness}.json"
            declaration = harness_runtime.load_declaration(path)
            runtime_schema.validate_document(declaration, "harness-capability")
            declarations.append(declaration)
            self.assertEqual(
                set(harness_runtime.CAPABILITIES), set(declaration["capabilities"])
            )
            self.assertEqual(
                {"unsupported"},
                {value["status"] for value in declaration["capabilities"].values()},
            )
        self.assertEqual(
            set(declarations[0]["capabilities"]),
            set(declarations[1]["capabilities"]),
        )

    def test_runtime_probe_overrides_static_default_and_passes_required(self) -> None:
        declaration = harness_runtime.load_declaration(
            REPO_ROOT / "harness" / "capabilities" / "codex.json"
        )
        report = harness_runtime.startup_probe(
            declaration,
            FakeAdapter(probe_response("codex")),
            ["subagents", "structured_tool_results"],
            ["transcript_access"],
        )
        self.assertEqual("PASS", report["verdict"])
        self.assertEqual([], report["degradations"])
        self.assertEqual("runtime-adapter-probe", report["evidence_source"])
        self.assertEqual(
            "unsupported",
            report["declaration_capabilities"]["subagents"]["status"],
        )
        self.assertEqual("supported", report["capabilities"]["subagents"]["status"])

    def test_required_degraded_or_unsupported_fails_closed(self) -> None:
        for state in ("degraded", "unsupported"):
            with self.subTest(state=state):
                snapshot = harness_runtime.validate_probe(
                    "test", probe_response("test", {"subagents": state})
                )
                report = harness_runtime.gate_capabilities(snapshot, ["subagents"], [])
                self.assertEqual("FAIL", report["verdict"])
                self.assertEqual(["subagents"], report["blocking_capabilities"])

    def test_optional_downgrades_continue_with_observable_evidence(self) -> None:
        snapshot = harness_runtime.validate_probe(
            "test",
            probe_response(
                "test",
                {"transcript_access": "degraded", "lifecycle_hooks": "unsupported"},
            ),
        )
        report = harness_runtime.gate_capabilities(
            snapshot, [], ["transcript_access", "lifecycle_hooks"]
        )
        self.assertEqual("PASS", report["verdict"])
        self.assertEqual(2, len(report["degradations"]))
        self.assertEqual(
            {"capability-degraded"},
            {item["event_type"] for item in report["degradations"]},
        )

    def test_incomplete_or_illegal_probe_fails_closed(self) -> None:
        incomplete = probe_response("test")
        del incomplete["capabilities"]["subagents"]
        with self.assertRaises(harness_runtime.HarnessError):
            harness_runtime.validate_probe("test", incomplete)
        illegal = probe_response("test")
        illegal["capabilities"]["subagents"]["status"] = "unknown"
        with self.assertRaises(harness_runtime.HarnessError):
            harness_runtime.validate_probe("test", illegal)

    def test_core_evaluation_runner_has_no_product_specific_branch(self) -> None:
        source = (
            (REPO_ROOT / "scripts" / "evaluation_runner.py")
            .read_text(encoding="utf-8")
            .casefold()
        )
        self.assertNotIn('== "codex"', source)
        self.assertNotIn('== "claude-code"', source)
        self.assertIn("subprocessharnessadapter", source)

    def test_cli_writes_probe_evidence_before_returning_failed_gate(self) -> None:
        adapter_source = """
import json
import sys
request = json.load(sys.stdin)
harness = request["payload"]["harness"]
capabilities = request["payload"]["capabilities"]
result = {
    "contract_version": 1,
    "harness": harness,
    "capabilities": {
        name: {
            "status": "unsupported" if name == "subagents" else "supported",
            "evidence": "executable-probe:" + name,
        }
        for name in capabilities
    },
}
json.dump(result, sys.stdout)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = root / "adapter.py"
            adapter.write_text(adapter_source, encoding="utf-8")
            output = root / "probe-report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "harness_runtime.py"),
                    "--declaration",
                    str(REPO_ROOT / "harness" / "capabilities" / "codex.json"),
                    "--adapter",
                    sys.executable,
                    "--adapter-arg",
                    str(adapter),
                    "--required",
                    "subagents",
                    "--optional",
                    "lifecycle_hooks",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("FAIL", report["verdict"])
            self.assertEqual(["subagents"], report["blocking_capabilities"])


if __name__ == "__main__":
    unittest.main()
