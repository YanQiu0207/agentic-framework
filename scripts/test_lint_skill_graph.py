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
            errors = lint_skill_graph.find_command_target_errors(root, {"known-skill"})
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
        self.assertEqual(
            [],
            lint_skill_graph.outgoing_edges(
                text, {"known-skill", "broken-skill"}, "broken-skill"
            ),
        )
        self.assertIn("broken-skill", skills)

    def _skill_root(self, skill_md: Path, body: str) -> dict:
        skill_md.parent.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(
            f"---\nname: {skill_md.parent.name}\ndescription: x\n---\n{body}",
            encoding="utf-8",
        )
        skills, _, _, _ = lint_skill_graph.collect_nodes(skill_md.parents[2])
        return skills

    def test_oversized_skill_md_is_size_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_md = Path(temp_dir) / "skills" / "fat-skill" / "SKILL.md"
            skills = self._skill_root(
                skill_md, "字" * (lint_skill_graph.SKILL_BODY_CHAR_LIMIT + 1)
            )
            errors = lint_skill_graph.find_size_errors(skills)
        self.assertEqual(1, len(errors))
        self.assertIn("fat-skill", errors[0])
        self.assertIn(str(lint_skill_graph.SKILL_BODY_CHAR_LIMIT), errors[0])

    def test_skill_md_at_limit_passes_size_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_md = Path(temp_dir) / "skills" / "lean-skill" / "SKILL.md"
            skill_md.parent.mkdir(parents=True)
            prefix = (
                f"---\nname: {skill_md.parent.name}\ndescription: x\n---\n"
            )
            # 全文（含 frontmatter）恰好在红线内
            skill_md.write_text(
                prefix + "a" * (lint_skill_graph.SKILL_BODY_CHAR_LIMIT - len(prefix)),
                encoding="utf-8",
            )
            skills, _, _, _ = lint_skill_graph.collect_nodes(skill_md.parents[2])
            self.assertEqual([], lint_skill_graph.find_size_errors(skills))

    def test_skill_md_one_char_over_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            skill_md = Path(temp_dir) / "skills" / "edge-skill" / "SKILL.md"
            skills = self._skill_root(
                skill_md, "a" * (lint_skill_graph.SKILL_BODY_CHAR_LIMIT + 1)
            )
            errors = lint_skill_graph.find_size_errors(skills)
        self.assertEqual(1, len(errors))


if __name__ == "__main__":
    unittest.main()
