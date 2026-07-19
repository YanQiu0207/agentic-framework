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

    def test_profiles_share_change_artifact_contract(self) -> None:
        """Both profiles create Proposal, Design, Delta, and Tasks artifacts."""
        production = (ROOT / "skills/opsx-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        tooling = (ROOT / "skills/workflow-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        for text in (production, tooling):
            for required in (
                "openspec/changes/",
                "proposal.md",
                "design.md",
                "tasks.md",
                "specs/",
            ):
                self.assertIn(required, text)
        self.assertIn("旧 `spec.md`", tooling)
        self.assertIn("禁止写入旧 Artifact", tooling)

    def test_change_templates_include_knowledge_bookkeeping(self) -> None:
        """Proposal and Tasks templates cannot omit knowledge lifecycle fields."""
        templates = (
            ROOT
            / "skills/opsx-requirements-clarification/reference/proposal_template.md",
            ROOT / "skills/opsx-quick-design/reference/quick-proposal-template.md",
            ROOT
            / "skills/workflow-requirements-clarification/reference/proposal_template.md",
            ROOT / "skills/workflow-quick-design/reference/quick-proposal-template.md",
        )
        for template in templates:
            with self.subTest(template=template):
                self.assertIn("知识影响", template.read_text(encoding="utf-8"))
        task_guides = (
            ROOT / "skills/opsx-code-generation/reference/task_planning_guide.md",
            ROOT / "skills/workflow-code-generation/reference/task_planning_guide.md",
        )
        for guide in task_guides:
            with self.subTest(guide=guide):
                text = guide.read_text(encoding="utf-8")
                self.assertIn("## 知识同步", text)
                self.assertIn("## 知识冲突", text)
                self.assertIn("## 实际 Diff 核对", text)

    def test_removed_knowledge_skills_do_not_exist(self) -> None:
        for name in (
            "bp-cola-ddd",
            "opsx-project-knowledge",
        ):
            self.assertFalse((ROOT / "skills" / name).exists())

    def test_project_knowledge_uses_shared_openspec_contract(self) -> None:
        """Shared project-knowledge 锁定统一读写、冲突与晋升边界。"""
        text = (ROOT / "skills/project-knowledge/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "Production 与 Tooling 的 Shared Core 合同",
            "openspec/index.md",
            "唯一建议写入位置",
            "知识与代码冲突",
            "同时展示双方证据和不确定性",
            "不得覆盖、重写、移动或删除任何 `custom/` 文件",
            "Change Delta 与 Archive",
            "用户明确确认后",
            "公共 `changes/` 只记录公共知识库自身治理",
            "交付前 intent 沉淀检查",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "docs/design-docs/",
            "docs/issues/",
            "候选写入共用库 `changes/",
        ):
            self.assertNotIn(forbidden, text)

    def test_project_init_uses_unified_private_openspec_layout(self) -> None:
        text = (ROOT / "skills/project-init/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "Production",
            "Tooling",
            "openspec/index.md",
            "openspec/specs/index.md",
            "openspec/issues/index.md",
            "外部私有目录",
            "链接恢复",
            "单独询问公共知识库接线",
            "不得覆盖",
            ".agentic-framework/",
        ):
            self.assertIn(required, text)
        self.assertNotIn("docs/design-docs/", text)


if __name__ == "__main__":
    unittest.main()
