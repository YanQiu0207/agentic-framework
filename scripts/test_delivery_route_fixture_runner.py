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

    def test_repository_fixtures_cover_native_and_every_runtime_upgrade(self) -> None:
        fixtures_path = (
            Path(__file__).resolve().parents[1]
            / "evaluation"
            / "delivery-route-fixtures.json"
        )
        summary = delivery_route_fixture_runner.run_fixtures(
            delivery_route_fixture_runner.load_fixtures(fixtures_path)
        )
        self.assertEqual("PASS", summary["verdict"])
        self.assertEqual(8, summary["total"])
        paths = {item["actual"]["path"] for item in summary["results"]}
        self.assertEqual({"native-delivery", "runtime-run"}, paths)

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
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            with self.assertRaisesRegex(
                delivery_route_fixture_runner.DeliveryRouteFixtureError, "schema_version"
            ):
                delivery_route_fixture_runner.load_fixtures(path)

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
