"""Tests for Run Manifest generation and evidence graph validation."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_manifest

COMMIT_SHA = "1" * 40
BASE_SHA = "0" * 40
CONFIG_DIGEST = "sha256:" + "2" * 64
CREATED_AT = "2026-07-19T12:00:00Z"


def envelope(
    artifact_type: str,
    artifact_id: str,
    payload: dict,
    task_id: str | None = "3",
) -> dict:
    """Build a valid artifact in one test Run."""
    return {
        "schema_version": 1,
        "artifact_type": artifact_type,
        "artifact_id": artifact_id,
        "run_id": "run-1",
        "task_id": task_id,
        "attempt": 1 if task_id is not None else None,
        "profile": "tooling",
        "harness": "codex",
        "producer": f"test-{artifact_type}",
        "commit_sha": COMMIT_SHA,
        "config_digest": CONFIG_DIGEST,
        "created_at": CREATED_AT,
        "payload": payload,
    }


def write_json(path: Path, value: object) -> None:
    """Write one UTF-8 JSON fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4), encoding="utf-8")


class RunFixture:
    """Create one complete Run evidence graph in a temporary directory."""

    def __init__(self, root: Path):
        self.root = root
        artifacts = root / "artifacts"
        artifacts.mkdir(parents=True)
        spec_path = artifacts / "spec.md"
        spec_path.write_text("# Spec\n", encoding="utf-8")
        self.documents = {
            "spec": envelope(
                "input-artifact",
                "spec",
                {
                    "input_type": "spec",
                    "path": "artifacts/spec.md",
                    "content_digest": run_manifest.file_digest(spec_path),
                },
                None,
            ),
            "task": envelope(
                "task-state", "task", {"state": "completed", "attempts": 0}
            ),
            "verify": envelope(
                "verify-report",
                "verify",
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
            "review": envelope(
                "review-report",
                "review",
                {
                    "verdict": "PASS",
                    "p0_count": 0,
                    "p1_count": 0,
                    "scope": "task",
                    "review_profile": "strict",
                    "round": 0,
                },
            ),
        }
        for name, document in self.documents.items():
            write_json(artifacts / f"{name}.json", document)
        self.metadata = {
            "schema_version": 1,
            "artifact_id": "manifest",
            "run_id": "run-1",
            "profile": "tooling",
            "harness": "codex",
            "producer": "run-manifest",
            "commit_sha": COMMIT_SHA,
            "config_digest": CONFIG_DIGEST,
            "created_at": CREATED_AT,
            "base_commit_sha": BASE_SHA,
            "relations": [
                {
                    "relation_type": "verifies",
                    "source_artifact_id": "verify",
                    "target_artifact_id": "spec",
                },
                {
                    "relation_type": "reviews",
                    "source_artifact_id": "review",
                    "target_artifact_id": "spec",
                },
            ],
        }

    def generate(self) -> dict:
        """Generate and return the fixture manifest."""
        return run_manifest.generate_manifest(self.root, self.metadata)

    def rewrite_artifact(
        self, manifest: dict, name: str, document: dict, update_digest: bool = True
    ) -> None:
        """Replace an artifact fixture and optionally update its manifest digest."""
        path = self.root / "artifacts" / f"{name}.json"
        write_json(path, document)
        if update_digest:
            entry = next(
                item
                for item in manifest["payload"]["artifacts"]
                if item["artifact_id"] == name
            )
            entry["content_digest"] = run_manifest.file_digest(path)


class RunManifestTest(unittest.TestCase):
    """Cover complete evidence and every required failure mode."""

    def test_generate_and_validate_complete_evidence_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            run_manifest.validate_manifest(fixture.root, manifest)
            self.assertEqual(
                ["review", "spec", "task", "verify"],
                [item["artifact_id"] for item in manifest["payload"]["artifacts"]],
            )
            self.assertEqual("completed", manifest["payload"]["tasks"][0]["state"])
            self.assertTrue((fixture.root / "run-manifest.json").is_file())

    def test_missing_and_replaced_artifacts_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            (fixture.root / "artifacts" / "verify.json").unlink()
            with self.assertRaises(run_manifest.ManifestError) as missing:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn(
                "missing_artifact:artifacts/verify.json", missing.exception.issues
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            path = fixture.root / "artifacts" / "verify.json"
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaises(run_manifest.ManifestError) as replaced:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn(
                "digest_mismatch:artifacts/verify.json", replaced.exception.issues
            )

    def test_orphan_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            orphan = envelope(
                "eval-result",
                "orphan",
                {
                    "case_id": "case",
                    "dimension": "recovery",
                    "verdict": "PASS",
                    "assertions": [],
                    "model": "test-model",
                    "evaluation_method": "deterministic-tier-1",
                },
                None,
            )
            write_json(fixture.root / "artifacts" / "orphan.json", orphan)
            with self.assertRaises(run_manifest.ManifestError) as caught:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn(
                "orphan_artifact:artifacts/orphan.json", caught.exception.issues
            )

    def test_cross_run_task_attempt_commit_and_config_are_rejected(self) -> None:
        mutations = {
            "run_id": "other-run",
            "task_id": "other-task",
            "attempt": 2,
            "commit_sha": "3" * 40,
            "config_digest": "sha256:" + "4" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp_dir:
                fixture = RunFixture(Path(temp_dir))
                manifest = fixture.generate()
                document = copy.deepcopy(fixture.documents["verify"])
                document[field] = value
                fixture.rewrite_artifact(manifest, "verify", document)
                with self.assertRaises(run_manifest.ManifestError) as caught:
                    run_manifest.validate_manifest(fixture.root, manifest)
                expected = (
                    f"binding_{field}_mismatch:verify"
                    if field in {"run_id", "commit_sha", "config_digest"}
                    else "task_binding_mismatch:verify"
                )
                self.assertIn(expected, caught.exception.issues)

    def test_spec_snapshot_and_review_verify_spec_bindings_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            (fixture.root / "artifacts" / "spec.md").write_text(
                "replaced", encoding="utf-8"
            )
            with self.assertRaises(run_manifest.ManifestError) as replaced:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn(
                "input_digest_mismatch:artifacts/spec.md", replaced.exception.issues
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            manifest["payload"]["relations"] = []
            with self.assertRaises(run_manifest.ManifestError) as unbound:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn("missing_spec_binding:review", unbound.exception.issues)
            self.assertIn("missing_spec_binding:verify", unbound.exception.issues)

    def test_producer_and_relation_endpoints_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            entry = next(
                item
                for item in manifest["payload"]["artifacts"]
                if item["artifact_id"] == "verify"
            )
            entry["producer"] = "other-producer"
            manifest["payload"]["relations"][0]["target_artifact_id"] = "missing"
            with self.assertRaises(run_manifest.ManifestError) as caught:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn("entry_producer_mismatch:verify", caught.exception.issues)
            self.assertIn("missing_relation_target:missing", caught.exception.issues)

    def test_path_escape_is_rejected_before_file_access(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            manifest = fixture.generate()
            manifest["payload"]["artifacts"][0]["path"] = "artifacts/../../outside.json"
            with self.assertRaises(run_manifest.ManifestError) as caught:
                run_manifest.validate_manifest(fixture.root, manifest)
            self.assertIn(
                "path_escape:artifacts/../../outside.json", caught.exception.issues
            )

    def test_symbolic_link_and_reparse_point_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            target = Path(temp_dir) / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            try:
                os.symlink(target, link)
            except OSError:
                pass
            else:
                with self.assertRaises(run_manifest.ManifestError) as caught:
                    run_manifest.secure_run_path(root, "link.json")
                self.assertIn("reparse_point:link.json", caught.exception.issues)
            nested = root / "artifacts" / "junction" / "artifact.json"
            nested.parent.mkdir(parents=True)
            with mock.patch.object(
                run_manifest,
                "_is_link_or_reparse",
                side_effect=lambda path: path.name == "junction",
            ):
                with self.assertRaises(run_manifest.ManifestError) as caught:
                    run_manifest.secure_run_path(
                        root, nested.relative_to(root).as_posix()
                    )
            self.assertIn(
                "reparse_point:artifacts/junction/artifact.json",
                caught.exception.issues,
            )

    def test_generator_refuses_overwrite_and_cli_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = RunFixture(Path(temp_dir))
            fixture.generate()
            with self.assertRaises(run_manifest.ManifestError) as caught:
                fixture.generate()
            self.assertIn("manifest_already_exists", caught.exception.issues)
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(run_manifest.__file__)),
                    "validate",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("PASS", result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
