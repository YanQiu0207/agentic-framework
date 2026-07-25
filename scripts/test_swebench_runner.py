"""Tests for the explicit-opt-in SWE-bench runner."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

import swebench_runner


class SwebenchRunnerTest(unittest.TestCase):
    """Keep plan mode offline and container execution explicit."""

    def _predictions(self, root: Path) -> Path:
        path = root / "predictions.jsonl"
        path.write_text(
            json.dumps(
                {
                    "instance_id": "repo__case",
                    "model_name_or_path": "codex",
                    "model_patch": "diff --git a/a b/a",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def _official_report(self, root: Path, run_id: str) -> Path:
        path = root / f"codex.{run_id}.json"
        path.write_text(
            json.dumps(
                {
                    "completed_ids": ["repo__case"],
                    "resolved_ids": ["repo__case"],
                    "error_ids": [],
                    "incomplete_ids": [],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_build_plan_uses_verified_dataset_and_selected_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            predictions = self._predictions(Path(temp_dir))
            plan = swebench_runner.build_plan(
                predictions, ["repo__case"], "pilot-1", 2
            )
        self.assertEqual(swebench_runner.DEFAULT_DATASET, plan["dataset"])
        self.assertEqual("not-started", plan["container_execution"])
        self.assertIn("--instance_ids", plan["command"])
        self.assertNotIn("docker", " ".join(plan["command"]).lower())
        self.assertEqual(64, len(plan["predictions_sha256"]))
        self.assertEqual("codex", plan["model_name_or_path"])

    def test_build_command_rejects_unsafe_or_unsupported_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            predictions = self._predictions(Path(temp_dir))
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "at least"):
                swebench_runner.build_official_command(predictions, [], "pilot", 1)
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "repeat"):
                swebench_runner.build_official_command(
                    predictions, ["repo__case", "repo__case"], "pilot", 1
                )
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "Verified"):
                swebench_runner.build_official_command(
                    predictions, ["repo__case"], "pilot", 1, "SWE-bench_Lite"
                )

    def test_build_command_rejects_invalid_or_missing_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            invalid = root / "invalid.jsonl"
            invalid.write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "JSON object"):
                swebench_runner.build_official_command(
                    invalid, ["repo__case"], "pilot", 1
                )

            predictions = self._predictions(root)
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "missing"):
                swebench_runner.build_official_command(
                    predictions, ["repo__other"], "pilot", 1
                )

            predictions.write_text(
                predictions.read_text(encoding="utf-8")
                + json.dumps(
                    {
                        "instance_id": "repo__extra",
                        "model_name_or_path": "codex",
                        "model_patch": "diff --git a/a b/a",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "unselected"):
                swebench_runner.build_official_command(
                    predictions, ["repo__case"], "pilot", 1
                )

    def test_execution_requires_explicit_container_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = swebench_runner.build_plan(
                self._predictions(Path(temp_dir)), ["repo__case"], "pilot", 1
            )
        with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "required"):
            swebench_runner.execute_plan(plan, False)

    @mock.patch("swebench_runner.subprocess.run")
    @mock.patch("swebench_runner.platform.system", return_value="Linux")
    def test_execution_runs_only_the_planned_official_command(
        self, system: mock.Mock, run: mock.Mock
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = swebench_runner.build_plan(
                self._predictions(root), ["repo__case"], "pilot", 1
            )

            def write_report(*args: object, **kwargs: object) -> subprocess.CompletedProcess:
                self._official_report(root, "pilot")
                return subprocess.CompletedProcess(["ignored"], 0, stdout="ok", stderr="")

            run.side_effect = write_report
            result = swebench_runner.execute_plan(plan, True)
        self.assertEqual("completed", result["container_execution"])
        self.assertEqual(0, result["exit_code"])
        self.assertEqual("PASS", result["official_result"]["verdict"])
        self.assertEqual(plan["command"], run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs["capture_output"])

    @mock.patch("swebench_runner.platform.system", return_value="Windows")
    def test_native_execution_rejects_windows_host(self, system: mock.Mock) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = swebench_runner.build_plan(
                self._predictions(Path(temp_dir)), ["repo__case"], "pilot", 1
            )
        with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "POSIX"):
            swebench_runner.execute_plan(plan, True)

    def test_wsl_docker_command_mounts_predictions_parent(self) -> None:
        plan = {
            "dataset": swebench_runner.DEFAULT_DATASET,
            "predictions_path": r"E:\evaluation\predictions.jsonl",
            "instance_ids": ["repo__case"],
            "run_id": "pilot",
            "model_name_or_path": "codex",
            "command": ["python", "--max_workers", "2"],
        }
        command = swebench_runner.build_wsl_docker_command(plan)
        self.assertEqual("wsl", command[0])
        self.assertIn("/mnt/e/evaluation:/work", command[-1])
        self.assertIn("swebench==4.1.0", command[-1])

    def test_official_report_path_uses_swebench_model_name_format(self) -> None:
        plan = {
            "predictions_path": r"E:\evaluation\predictions.jsonl",
            "model_name_or_path": "org/model",
            "run_id": "pilot",
        }
        self.assertEqual(
            Path(r"E:\evaluation\org__model.pilot.json"),
            swebench_runner._official_report_path(plan),
        )

    def test_execution_rejects_unresolved_official_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = swebench_runner.build_plan(
                self._predictions(root), ["repo__case"], "pilot", 1
            )

            def write_unresolved_report(
                *args: object, **kwargs: object
            ) -> subprocess.CompletedProcess:
                report = self._official_report(root, "pilot")
                report.write_text(
                    json.dumps(
                        {
                            "completed_ids": ["repo__case"],
                            "resolved_ids": [],
                            "error_ids": [],
                            "incomplete_ids": [],
                        }
                    ),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(["ignored"], 0, "", "")

            with mock.patch("swebench_runner.platform.system", return_value="Linux"), mock.patch(
                "swebench_runner.subprocess.run", side_effect=write_unresolved_report
            ), self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "did not resolve"):
                swebench_runner.execute_plan(plan, True)

    def test_main_defaults_to_plan_mode_without_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            predictions = self._predictions(Path(temp_dir))
            with mock.patch("swebench_runner.subprocess.run") as run, mock.patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                code = swebench_runner.main(
                    [
                        "--predictions",
                        str(predictions),
                        "--instance-id",
                        "repo__case",
                        "--run-id",
                        "pilot",
                    ]
                )
        self.assertEqual(0, code)
        self.assertFalse(run.called)
        self.assertEqual("not-started", json.loads(stdout.getvalue())["container_execution"])

    def test_main_writes_plan_without_container_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "artifact.json"
            with mock.patch("swebench_runner.subprocess.run") as run:
                code = swebench_runner.main(
                    [
                        "--predictions",
                        str(self._predictions(root)),
                        "--instance-id",
                        "repo__case",
                        "--run-id",
                        "pilot",
                        "--output",
                        str(output),
                    ]
                )
            result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(0, code)
        self.assertFalse(run.called)
        self.assertEqual("not-started", result["container_execution"])

    def test_output_refuses_to_replace_existing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "artifact.json"
            output.write_text("old\n", encoding="utf-8")
            with self.assertRaisesRegex(swebench_runner.SwebenchRunnerError, "overwrite"):
                swebench_runner._atomic_write(output, {"new": True})
            self.assertEqual("old\n", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
