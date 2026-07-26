"""Structural tests for the unified workflow profile contract.

change 2045 退役 opsx-* 后，Profile 差异由治理守卫（governance_guards）与
规格（framework-unification.md §5.3／§6.3）承载，不再由独立 SKILL.md 表达。
"""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProfileContractTest(unittest.TestCase):
    """统一执行链下的 Profile 合同：Tooling SKILL + Production 守卫 + 规格三者一致。"""

    def test_production_review_contract_enforced_by_guards_and_spec(self) -> None:
        """Production 逐任务 Review 合同由守卫代码与规格承载（change 2043／2045）。"""
        import sys

        sys.path.insert(
            0, str(ROOT / "skills" / "workflow-code-generation" / "scripts")
        )
        import governance_guards

        # 守卫在 production 下强制逐任务 Review
        self.assertTrue(callable(governance_guards.task_review_guard_errors))
        spec = (
            ROOT
            / "openspec/specs/backend/engineering/tech/framework-unification.md"
        ).read_text(encoding="utf-8")
        for required in (
            "review_profile",
            "comprehensive-reviewer",
            "5 个专项 Reviewer",
        ):
            self.assertIn(required, spec)

    def test_tooling_forbids_task_level_llm_review(self) -> None:
        text = (ROOT / "skills/workflow-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("owner / implementer 禁止在 task 内启动 LLM Review", text)
        self.assertIn("一次最终审核", text)
        self.assertIn("禁止启动第二次全量首审", text)

    def test_unified_skill_carries_change_artifact_contract(self) -> None:
        """统一入口 workflow-code-generation 承载 Artifact 契约（change 2045）。"""
        text = (ROOT / "skills/workflow-code-generation/SKILL.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "openspec/changes/",
            "proposal.md",
            "design.md",
            "tasks.md",
            "specs/",
            "旧 `spec.md`",
            "禁止写入旧 Artifact",
        ):
            self.assertIn(required, text)

    def test_change_templates_include_knowledge_bookkeeping(self) -> None:
        """Proposal 和 Tasks 模板不能省略知识生命周期字段。"""
        templates = (
            ROOT
            / "skills/workflow-requirements-clarification/reference/proposal_template.md",
            ROOT / "skills/workflow-quick-design/reference/quick-proposal-template.md",
        )
        for template in templates:
            with self.subTest(template=template):
                self.assertIn("知识影响", template.read_text(encoding="utf-8"))
        task_guides = (
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

    def test_retired_opsx_skills_are_archived_not_deleted(self) -> None:
        """opsx-* 已退役归档（change 2045），不在活跃 skills/ 但在 archive/。"""
        for name in (
            "opsx-archive",
            "opsx-code-generation",
            "opsx-quick-design",
            "opsx-requirements-clarification",
            "opsx-system-design",
            "opsx-test-generation",
        ):
            self.assertFalse(
                (ROOT / "skills" / name).exists(), f"{name} 应已移出 skills/"
            )
            self.assertTrue(
                (
                    ROOT
                    / "openspec/changes/archive/opsx-retirement-2026-07-27/skills"
                    / name
                ).exists(),
                f"{name} 应在 archive/ 中",
            )

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
