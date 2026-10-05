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


class NativeFirstRoutingContractTest(unittest.TestCase):
    """change 2048 Task 9：显式路由与 v2 证据的活跃文案合同。"""

    def test_generation_skill_states_explicit_runtime_only(self) -> None:
        text = (ROOT / "skills/workflow-code-generation/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "--execution-mode runtime",
            "不自动升级",
            "独立 Judge",
            "最多十轮",
        ):
            self.assertIn(required, text)
        self.assertNotIn("Runtime 升级条件：** `strict` 风险、并行 worktree 写入、长任务恢复", text)

    def test_delegated_guide_drops_strict_upgrade_and_two_round_rules(self) -> None:
        path = ROOT / "skills/workflow-code-generation/reference/delegated-execution-guide.md"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("必定升级", text)
        self.assertNotIn("最多两轮", text)
        self.assertNotIn("恢复本身是 Runtime 升级条件", text)
        self.assertNotIn("执行恢复前，路由命令必须传 `--long-task-recovery`", text)
        for required in (
            "--execution-mode runtime",
            "最多十轮",
            "恢复按事实进行，本身不是 Runtime 启用条件",
            "implementer_actor",
        ):
            self.assertIn(required, text)
        # 任务自身机器修复预算（两轮 attempts）与复审十轮是两个计数，保留区别表述。
        self.assertIn("attempts 预算", text)

    def test_review_report_format_pins_v2_contract(self) -> None:
        text = (
            ROOT / "skills/workflow-code-review/reference/report-format.md"
        ).read_text(encoding="utf-8")
        for required in (
            "schema_version: 2",
            "subject_id",
            "independence_basis",
            "只按旧合同展示历史",
        ):
            self.assertIn(required, text)
        self.assertNotIn("只接受这 6 个字段", text)

    def test_review_skill_allows_strict_native_scope(self) -> None:
        text = (ROOT / "skills/workflow-code-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("不因此要求 Run", text)
        self.assertIn("不构成降级", text)
        self.assertNotIn("必须升级到完整 Runtime Run", text)

    def test_verification_skill_pins_v2_subject_binding(self) -> None:
        text = (ROOT / "skills/workflow-verification/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "schema_version: 2",
            "subject_id",
            "检查前后核对同一内容主体",
            "--subject-base",
            "不能作为新完成证据",
        ):
            self.assertIn(required, text)

    def test_trigger_cases_cover_new_behavior_rows(self) -> None:
        for relative, marker in (
            ("skills/workflow-code-generation/evaluation/trigger-cases.md", "R-1"),
            ("skills/workflow-code-review/evaluation/trigger-cases.md", "V-1"),
            ("skills/workflow-verification/evaluation/trigger-cases.md", "S-1"),
        ):
            with self.subTest(file=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("## behavior", text)
                self.assertIn(marker, text)


class SvnWorkflowContractTest(unittest.TestCase):
    """change 2048 Task 13：SVN 串行工作流与初始化识别的活跃文案合同。"""

    def test_delivery_guide_pins_svn_serial_workflow(self) -> None:
        text = (
            ROOT
            / "skills/workflow-code-generation/reference/delivery-guide.md"
        ).read_text(encoding="utf-8")
        for required in (
            "SVN 原生交付（串行工作流）",
            "svn-pending-commit",
            "svn-revision-verified",
            "不是正式交付 PASS",
            "不盲目重提",
            "不自动回滚共享版本",
            "git-scoped-delivery-pass",
        ):
            self.assertIn(required, text)

    def test_project_init_detects_vcs_and_recommends_native(self) -> None:
        text = (ROOT / "skills/project-init/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "已有 SVN → 默认推荐原生 SVN",
            "双 VCS 并存时必须显式确认开发后端",
            "不创建镜像/桥接",
            "不删除任何 `.git`、`.svn` 元数据",
            "逐路径 `svn add`",
            "不执行 `svn commit`",
        ):
            self.assertIn(required, text)
        # OPSX 独立入口提法已退役（change 2048 Task 13 修正）。
        self.assertNotIn("使用 OPSX 生命周期和 Production Review 门禁", text)

    def test_execution_and_delegation_state_serial_write(self) -> None:
        for relative in (
            "skills/workflow-code-generation/reference/execution-setup.md",
            "skills/workflow-code-generation/reference/delegated-execution-guide.md",
        ):
            with self.subTest(file=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("不创建 Git 镜像或桥接", text)

    def test_verification_skill_states_explicit_backend(self) -> None:
        text = (ROOT / "skills/workflow-verification/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("--vcs-backend git|svn", text)
        drift = (
            ROOT
            / "skills/workflow-verification/reference/spec-drift-and-scope.md"
        ).read_text(encoding="utf-8")
        self.assertIn("属性列 modified/conflicted 也计入 tracked", drift)
        self.assertIn("git-scoped-delivery-pass", drift)

    def test_trigger_cases_cover_svn_workflow_rows(self) -> None:
        generation = (
            ROOT
            / "skills/workflow-code-generation/evaluation/trigger-cases.md"
        ).read_text(encoding="utf-8")
        for marker in ("R-8", "R-9", "R-10", "R-11"):
            self.assertIn(marker, generation)
        verification = (
            ROOT
            / "skills/workflow-verification/evaluation/trigger-cases.md"
        ).read_text(encoding="utf-8")
        for marker in ("S-7", "S-8", "S-9"):
            self.assertIn(marker, verification)


if __name__ == "__main__":
    unittest.main()
