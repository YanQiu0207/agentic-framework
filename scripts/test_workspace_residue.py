"""Regression tests for Scoped Delivery workspace residue snapshots."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "skills"
        / "workflow-code-generation"
        / "scripts"
    ),
)

import check_delivery
import workspace_residue


class WorkspaceResidueTest(unittest.TestCase):
    """Keep S0/S1 and Git/SVN delivery scopes fail-closed."""

    def _git_repo(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".gitignore").write_text(".agentic-framework/\n", encoding="utf-8")
        (repo / "code.py").write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(repo), "add", ".gitignore", "code.py"], check=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.email=t@example.test",
                "-c",
                "user.name=test",
                "commit",
                "-qm",
                "initial",
            ],
            check=True,
        )
        return repo

    def test_git_snapshot_detects_untracked_content_change(self) -> None:
        repo = self._git_repo()
        residue = repo / "residue.txt"
        residue.write_text("before\n", encoding="utf-8")

        snapshot = workspace_residue.capture_workspace_residue(
            repo, "HEAD", ["code.py"]
        )
        self.assertEqual("git", snapshot["vcs"])
        self.assertEqual(["residue.txt"], [item["path"] for item in snapshot["entries"]])
        self.assertEqual([], workspace_residue.compare_workspace_residue(repo, snapshot))

        residue.write_text("after\n", encoding="utf-8")
        self.assertEqual(
            ["residue.txt"],
            workspace_residue.compare_workspace_residue(repo, snapshot),
        )

    def test_snapshot_rejects_residue_overlapping_scope(self) -> None:
        repo = self._git_repo()
        (repo / "generated").mkdir()
        (repo / "generated" / "stale.txt").write_text("stale\n", encoding="utf-8")

        with self.assertRaisesRegex(
            workspace_residue.WorkspaceResidueError, "重叠"
        ):
            workspace_residue.capture_workspace_residue(
                repo, "HEAD", ["generated"]
            )

    def test_git_scoped_delivery_accepts_commit_and_unchanged_residue(self) -> None:
        repo = self._git_repo()
        (repo / "residue.txt").write_text("keep\n", encoding="utf-8")
        snapshot = workspace_residue.capture_workspace_residue(
            repo, "HEAD", ["code.py"]
        )
        baseline = repo / ".agentic-framework" / "verify" / "baseline.json"
        baseline.parent.mkdir(parents=True)
        baseline.write_text(
            json.dumps({"workspace_residue_snapshot": snapshot}), encoding="utf-8"
        )
        (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "code.py"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.email=t@example.test",
                "-c",
                "user.name=test",
                "commit",
                "-qm",
                "scope",
            ],
            check=True,
        )
        commit = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()

        self.assertEqual(
            [], check_delivery.check_scoped_delivery(repo, baseline, commit, None)
        )

    def test_svn_snapshot_excludes_framework_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".agentic-framework" / "verify").mkdir(parents=True)
            (root / ".agentic-framework" / "verify" / "baseline.json").write_text(
                "{}", encoding="utf-8"
            )
            (root / "residue.txt").write_text("keep\n", encoding="utf-8")

            def run_bytes(_root: Path, args: list[str]) -> bytes:
                if args[:2] == ["svn", "status"]:
                    return b"?       .agentic-framework\n?       residue.txt\n"
                raise AssertionError(args)

            with mock.patch.object(
                workspace_residue, "_run_bytes", side_effect=run_bytes
            ):
                entries = workspace_residue._svn_entries(root)
        self.assertEqual(["residue.txt"], [entry["path"] for entry in entries])

    def test_svn_scoped_delivery_requires_revision_and_uses_scope(self) -> None:
        snapshot = {
            "version": 1,
            "vcs": "svn",
            "base_ref": "7",
            "scope_paths": ["code.py"],
            "entries": [],
            "residue_digest": workspace_residue._canonical_digest([]),
        }
        snapshot["snapshot_digest"] = workspace_residue._canonical_digest(snapshot)
        with tempfile.TemporaryDirectory() as temp_dir:
            baseline = Path(temp_dir) / "baseline.json"
            baseline.write_text(
                json.dumps({"workspace_residue_snapshot": snapshot}),
                encoding="utf-8",
            )
            self.assertIn(
                "--delivery-revision",
                check_delivery.check_scoped_delivery(
                    Path(temp_dir), baseline, None, None
                )[0],
            )
            with mock.patch.object(
                check_delivery.workspace_residue,
                "svn_revision_paths",
                return_value=["code.py"],
            ), mock.patch.object(
                check_delivery.workspace_residue,
                "compare_workspace_residue",
                return_value=[],
            ):
                self.assertEqual(
                    [],
                    check_delivery.check_scoped_delivery(
                        Path(temp_dir), baseline, None, "8"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
