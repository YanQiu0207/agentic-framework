"""Tests for the archived Change ticket number suggestion script."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "suggest_ticket_number.py"


class SuggestTicketNumberTest(unittest.TestCase):
    """Exercise ticket extraction from direct archive children."""

    def run_script(self, archive_dir: Path) -> subprocess.CompletedProcess[str]:
        """Run the CLI with the repository's UTF-8 subprocess settings."""
        environment = os.environ.copy()
        environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(archive_dir)],
            check=False,
            capture_output=True,
            encoding="utf-8",
            env=environment,
        )

    def test_returns_maximum_direct_prefix_plus_one(self) -> None:
        """Only numeric prefixes from direct child directories are included."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_dir = Path(temporary_directory)
            for name in (
                "12-2026-07-01-first-change",
                "123-2026-07-02-second-change",
                "7-2026-07-03-third-change",
                "not-a-ticket-2026-07-04-ignored",
                "12x-2026-07-05-ignored",
            ):
                (archive_dir / name).mkdir()
            nested = archive_dir / "nested"
            nested.mkdir()
            (nested / "999-2026-07-06-not-direct").mkdir()

            result = self.run_script(archive_dir)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("124\n", result.stdout)

    def test_returns_one_when_no_numeric_prefix_exists(self) -> None:
        """An empty or non-numeric archive starts the recommendation at one."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive_dir = Path(temporary_directory)
            (archive_dir / "archive-without-ticket").mkdir()
            result = self.run_script(archive_dir)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("1\n", result.stdout)

    def test_rejects_missing_archive_directory(self) -> None:
        """A missing input path is reported as a caller error."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_dir = Path(temporary_directory) / "missing"
            result = self.run_script(missing_dir)

        self.assertEqual(2, result.returncode)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
