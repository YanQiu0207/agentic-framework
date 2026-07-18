"""Regression tests for the skill graph linter."""

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_skill_graph


class SkillGraphTest(unittest.TestCase):
    """Cover command targets and malformed frontmatter."""

    def test_checks_every_command_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            commands = root / "commands"
            commands.mkdir()
            (commands / "run.md").write_text(
                "调用 `known-skill` skill，再调用 `missing-skill` skill",
                encoding="utf-8",
            )
            errors = lint_skill_graph.find_command_target_errors(
                root, {"known-skill"}
            )
        self.assertEqual(1, len(errors))
        self.assertIn("missing-skill", errors[0])

    def test_unclosed_frontmatter_is_direct_error_and_has_no_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            skill = root / "skills" / "broken-skill"
            skill.mkdir(parents=True)
            text = "---\nname: broken-skill\ndescription: calls known-skill\n"
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            skills, _, _, errors = lint_skill_graph.collect_nodes(root)
        self.assertIn("frontmatter 未闭合", errors[0])
        self.assertEqual([], lint_skill_graph.outgoing_edges(
            text, {"known-skill", "broken-skill"}, "broken-skill"
        ))
        self.assertIn("broken-skill", skills)


if __name__ == "__main__":
    unittest.main()
