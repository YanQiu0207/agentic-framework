"""Structural tests for the two workflow profile contracts."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProfileContractTest(unittest.TestCase):
    """Prevent Production and Tooling review policies from drifting together."""

    def test_production_has_task_and_integration_reviews(self) -> None:
        text = (ROOT / "skills/opsx-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "review_profile: standard",
            "review_profile: strict",
            "scope: integration",
            "Task Review",
            "5 个专项 Reviewer",
        ):
            self.assertIn(required, text)

    def test_tooling_forbids_task_level_llm_review(self) -> None:
        text = (ROOT / "skills/workflow-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("owner / implementer 禁止在 task 内启动 LLM Review", text)
        self.assertIn("一次最终审核", text)
        self.assertIn("禁止启动第二次全量首审", text)

    def test_removed_knowledge_skills_do_not_exist(self) -> None:
        for name in (
            "bp-cola-ddd",
            "project-knowledge",
            "opsx-project-knowledge",
        ):
            self.assertFalse((ROOT / "skills" / name).exists())


if __name__ == "__main__":
    unittest.main()
