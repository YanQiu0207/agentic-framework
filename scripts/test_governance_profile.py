"""Unit tests for the shared governance profile reader (change 2041)."""

from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import governance_profile


class ReadProfileTest(unittest.TestCase):
    def _manifest_repo(self, profile: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        manifest = repo / ".agentic-framework" / "manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"profile": profile}), encoding="utf-8")
        return repo

    def test_manifest_found_upward_from_nested_dir(self) -> None:
        repo = self._manifest_repo("production")
        nested = repo / "openspec" / "changes" / "2099-x"
        nested.mkdir(parents=True)
        self.assertEqual("production", governance_profile.read_profile(nested))

    def test_override_wins_over_manifest(self) -> None:
        repo = self._manifest_repo("production")
        self.assertEqual(
            "tooling", governance_profile.read_profile(repo, "tooling")
        )

    def test_missing_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 本机用户目录可能装有框架（祖先链继承是特性），用例须确定性隔离。
            from unittest import mock

            with mock.patch("governance_profile.find_manifest", return_value=None):
                with self.assertRaisesRegex(governance_profile.GovernanceProfileError, "未传"):
                    governance_profile.read_profile(Path(temp_dir))

    def test_invalid_manifest_profile_fails_closed(self) -> None:
        repo = self._manifest_repo("bogus")
        with self.assertRaisesRegex(governance_profile.GovernanceProfileError, "非法"):
            governance_profile.read_profile(repo)

    def test_invalid_override_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(governance_profile.GovernanceProfileError, "非法"):
                governance_profile.read_profile(Path(temp_dir), "bogus")

    def test_no_silent_default_branch(self) -> None:
        """静默默认为 tooling 是本 Change 最危险的失败方向，用检索证明不存在。"""
        source = inspect.getsource(governance_profile.read_profile)
        self.assertNotIn('return "tooling"', source)
        self.assertNotIn("return 'tooling'", source)
        self.assertNotIn('return "production"', source)
        self.assertNotIn("return 'production'", source)


class ReviewProfileFloorTest(unittest.TestCase):
    def test_floors(self) -> None:
        self.assertEqual("standard", governance_profile.review_profile_floor("production"))
        self.assertEqual("lightweight", governance_profile.review_profile_floor("tooling"))

    def test_below_floor(self) -> None:
        self.assertTrue(governance_profile.below_floor("lightweight", "production"))
        self.assertFalse(governance_profile.below_floor("standard", "production"))
        self.assertFalse(governance_profile.below_floor("strict", "production"))
        self.assertFalse(governance_profile.below_floor("lightweight", "tooling"))


if __name__ == "__main__":
    unittest.main()
