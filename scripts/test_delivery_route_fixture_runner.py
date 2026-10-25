"""Tests for the zero-network delivery route fixture runner."""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import delivery_route_fixture_runner


class DeliveryRouteFixtureRunnerTest(unittest.TestCase):
    """Assert fixture validation and production route integration."""

    def test_repository_fixtures_cover_route_matrix_and_rejections(self) -> None:
        fixtures_path = (
            Path(__file__).resolve().parents[1]
            / "evaluation"
            / "delivery-route-fixtures.json"
        )
        summary = delivery_route_fixture_runner.run_fixtures(
            delivery_route_fixture_runner.load_fixtures(fixtures_path)
        )
        self.assertEqual("PASS", summary["verdict"])
        self.assertEqual(19, summary["total"])
        paths = {
            item["actual"]["path"]
            for item in summary["results"]
            if "path" in item["actual"]
        }
        self.assertEqual({"native-delivery", "runtime-run"}, paths)
        # 冲突与不支持场景必须以显式错误断言存在，不静默降级。
        errors = {
            item["id"]
            for item in summary["results"]
            if "error" in item["actual"]
        }
        self.assertEqual(
            {
                "runtime-explicit-on-svn-rejected",
                "runtime-audit-on-svn-rejected",
                "runtime-on-unknown-vcs-rejected",
                "runtime-on-unknown-vcs-without-explicit-vcs-rejected",
                "conflict-native-with-audit-required",
                "conflict-native-with-cross-host",
                "invalid-execution-mode-rejected",
            },
            errors,
        )
        self.assertEqual(7, len(errors))
        # strict / 并行 / 恢复在无 Runtime 需求时保持 Native。
        native_ids = {
            item["id"]
            for item in summary["results"]
            if item["actual"].get("path") == "native-delivery"
        }
        self.assertIn("native-strict-risk-no-longer-upgrades", native_ids)
        self.assertIn("native-parallel-worktree-need", native_ids)
        self.assertIn("native-long-task-recovery-need", native_ids)

    def test_mismatched_expected_route_fails_without_hiding_actual_value(self) -> None:
        result = delivery_route_fixture_runner.evaluate_fixture(
            {
                "id": "wrong-route",
                "input": {"review_profile": "standard"},
                "expected": {
                    "path": "runtime-run",
                    "runtime_upgrade_reasons": [],
                },
            }
        )
        self.assertEqual("FAIL", result["verdict"])
        self.assertEqual("native-delivery", result["actual"]["path"])

    def test_fixture_contract_rejects_unknown_flags_and_bad_booleans(self) -> None:
        with self.assertRaisesRegex(
            delivery_route_fixture_runner.DeliveryRouteFixtureError, "unsupported"
        ):
            delivery_route_fixture_runner.evaluate_fixture(
                {
                    "id": "unknown",
                    "input": {"review_profile": "standard", "unknown": True},
                    "expected": {
                        "path": "native-delivery",
                        "runtime_upgrade_reasons": [],
                    },
                }
            )
        with self.assertRaisesRegex(
            delivery_route_fixture_runner.DeliveryRouteFixtureError, "boolean"
        ):
            delivery_route_fixture_runner.evaluate_fixture(
                {
                    "id": "bad-bool",
                    "input": {
                        "review_profile": "standard",
                        "audit_required": "true",
                    },
                    "expected": {
                        "path": "native-delivery",
                        "runtime_upgrade_reasons": [],
                    },
                }
            )

    def test_load_rejects_invalid_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fixtures.json"
            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaisesRegex(
                delivery_route_fixture_runner.DeliveryRouteFixtureError, "schema_version"
            ):
                delivery_route_fixture_runner.load_fixtures(path)

    def test_expected_error_fixture_matches_and_mismatch_fails(self) -> None:
        matched = delivery_route_fixture_runner.evaluate_fixture(
            {
                "id": "svn-runtime",
                "input": {
                    "review_profile": "standard",
                    "execution_mode": "runtime",
                    "vcs": "svn",
                },
                "expected": {"error": "仅支持 Git"},
            }
        )
        self.assertEqual("PASS", matched["verdict"])
        mismatched = delivery_route_fixture_runner.evaluate_fixture(
            {
                "id": "svn-runtime-wrong-message",
                "input": {
                    "review_profile": "standard",
                    "execution_mode": "runtime",
                    "vcs": "svn",
                },
                "expected": {"error": "别的错误"},
            }
        )
        self.assertEqual("FAIL", mismatched["verdict"])
        no_error = delivery_route_fixture_runner.evaluate_fixture(
            {
                "id": "expected-error-not-raised",
                "input": {
                    "review_profile": "standard",
                    "execution_mode": "runtime",
                    "vcs": "git",
                },
                "expected": {"error": "仅支持 Git"},
            }
        )
        self.assertEqual("FAIL", no_error["verdict"])
        self.assertEqual("runtime-run", no_error["actual"]["path"])

    def test_main_writes_new_result_and_refuses_to_replace_it(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "evaluation"
            / "delivery-route-fixtures.json"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "route-result.json"
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                code = delivery_route_fixture_runner.main(
                    ["--fixtures", str(source), "--output", str(output)]
                )
            self.assertEqual(0, code)
            self.assertEqual("PASS", json.loads(output.read_text(encoding="utf-8"))["verdict"])
            with mock.patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(
                    2,
                    delivery_route_fixture_runner.main(
                        ["--fixtures", str(source), "--output", str(output)]
                    ),
                )


if __name__ == "__main__":
    unittest.main()
