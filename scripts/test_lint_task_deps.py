"""Regression tests for task dependency parsing."""

import unittest
import tempfile
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "skills"
        / "workflow-code-generation"
        / "scripts"
    ),
)
import lint_task_deps


class TaskDependencyTest(unittest.TestCase):
    """Cover empty fields and duplicate identifiers."""

    def test_empty_depends_on_is_present(self) -> None:
        self.assertEqual((set(), True), lint_task_deps.parse_deps("", "depends_on"))

    def test_missing_depends_on_is_absent(self) -> None:
        self.assertEqual((set(), False), lint_task_deps.parse_deps(None, None))

    def test_duplicate_task_id_is_rejected(self) -> None:
        text = "### 任务 1：A\n- depends_on: []\n### 任务 1：B\n- depends_on: []\n"
        with self.assertRaisesRegex(ValueError, "重复任务 ID: 1"):
            lint_task_deps.parse_tasks(text)

    def test_duplicate_task_id_returns_cli_error(self) -> None:
        text = "### 任务 1：A\n- depends_on: []\n### 任务 1：B\n- depends_on: []\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = Path(temp_dir) / "tasks.md"
            tasks_file.write_text(text, encoding="utf-8")
            self.assertEqual(2, lint_task_deps.main([str(tasks_file)]))

    def test_self_dependency_is_preserved_and_rejected(self) -> None:
        text = "### 任务 1：A\n- depends_on: [Task 1]\n"
        tasks = lint_task_deps.parse_tasks(text)
        self.assertEqual({1}, tasks[1]["deps"])
        self.assertIn(1, lint_task_deps.reachable(tasks)[1])

    def test_missing_required_fields_are_errors(self) -> None:
        tasks = lint_task_deps.parse_tasks("### 任务 1：A\n- depends_on: []\n")
        errors = lint_task_deps.field_errors(tasks)
        for name in lint_task_deps.REQUIRED_FIELDS:
            self.assertTrue(any(f"缺少 {name} 字段" in e for e in errors), name)

    def test_invalid_profile_and_state_are_errors(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: heavy\n"
            "- context_files:\n- verification:\n- artifacts:\n- 状态: 已完结\n"
        )
        errors = lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))
        self.assertTrue(any("review_profile `heavy` 不合法" in e for e in errors))
        self.assertTrue(any("状态 `已完结` 不含合法值" in e for e in errors))

    def test_valid_fields_pass(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: standard\n"
            "- context_files:\n- verification:\n- artifacts:\n"
            "- 状态: 未开始    （合法值：未开始 / 进行中 / 完成 / 需人工 / 阻塞）\n"
        )
        errors = lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))
        self.assertEqual([], errors)

    def test_field_errors_ignore_state_consistency(self) -> None:
        """一致性不并入 plan 阶段字段校验，避免执行中途重跑 lint 报噪声。"""
        text = (
            "### 任务 1: [ ] A\n- depends_on: []\n- review_profile: standard\n"
            "- context_files:\n- verification:\n- artifacts:\n- 状态: 完成\n"
            "- 验收标准:\n    - [ ] 未勾选项\n"
        )
        errors = lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))
        self.assertEqual([], errors)

    def test_main_parses_tasks_md_with_bom_prefix(self) -> None:
        text = (
            "### 任务 1：A\n- depends_on: []\n- review_profile: standard\n"
            "- context_files:\n- verification:\n- artifacts:\n"
            "- 状态: 未开始\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = Path(temp_dir) / "tasks.md"
            tasks_file.write_bytes(text.encode("utf-8-sig"))
            self.assertEqual(0, lint_task_deps.main([str(tasks_file)]))


class ReviewProfileAliasTest(unittest.TestCase):
    """change 2035 Task 6：review_profile 两种写法归一，取值集合不变。"""

    def _errors(self, profile_lines: str) -> list[str]:
        text = (
            "### 任务 1：A\n- depends_on: []\n"
            f"{profile_lines}"
            "- context_files:\n- verification:\n- artifacts:\n- 状态: 未开始\n"
        )
        return lint_task_deps.field_errors(lint_task_deps.parse_tasks(text))

    def test_spaced_writing_is_accepted(self) -> None:
        self.assertEqual([], self._errors("- Review Profile: standard\n"))

    def test_mixed_case_and_underscore_writing_is_accepted(self) -> None:
        self.assertEqual([], self._errors("- REVIEW_PROFILE: strict\n"))

    def test_value_set_is_unchanged(self) -> None:
        errors = self._errors("- Review Profile: heavy\n")
        self.assertTrue(any("review_profile `heavy` 不合法" in e for e in errors))

    def test_conflicting_writings_are_an_error(self) -> None:
        errors = self._errors(
            "- review_profile: standard\n- Review Profile: strict\n"
        )
        self.assertTrue(any("取值不同的 review_profile" in e for e in errors))

    def test_same_value_duplicates_are_accepted(self) -> None:
        self.assertEqual(
            [],
            self._errors("- review_profile: standard\n- Review Profile: standard\n"),
        )

    def test_no_fuzzy_match(self) -> None:
        errors = self._errors("- review-profile: standard\n")
        self.assertTrue(any("缺少 review_profile 字段" in e for e in errors))


class StateNormalizationTest(unittest.TestCase):
    """change 2035 Task 7：状态取值归一为规范值，写侧不动。"""

    def test_native_states_pass_through(self) -> None:
        for state in lint_task_deps.TASK_STATES:
            self.assertEqual(state, lint_task_deps.parse_state(state))

    def test_completed_aliases_normalize(self) -> None:
        for alias in ("已完成", "completed", "complete", "done", "x", "Completed", "X"):
            self.assertEqual("完成", lint_task_deps.parse_state(alias), alias)

    def test_open_aliases_normalize(self) -> None:
        self.assertEqual("未开始", lint_task_deps.parse_state("pending"))
        self.assertEqual("进行中", lint_task_deps.parse_state("in progress"))
        self.assertEqual("进行中", lint_task_deps.parse_state("in-progress"))
        self.assertEqual("阻塞", lint_task_deps.parse_state("blocked"))

    def test_annotated_values_still_classify(self) -> None:
        self.assertEqual("完成", lint_task_deps.parse_state("已完成（单 worktree）"))
        self.assertEqual("阻塞", lint_task_deps.parse_state("blocked 依赖外部审批"))

    def test_illegal_values_still_rejected(self) -> None:
        self.assertIsNone(lint_task_deps.parse_state("已完结"))
        self.assertIsNone(lint_task_deps.parse_state(""))

    def test_state_prefix_returns_raw_matched_text(self) -> None:
        self.assertEqual("已完成", lint_task_deps.state_prefix("已完成（附注）"))
        self.assertEqual("Blocked", lint_task_deps.state_prefix("Blocked 原因"))
        self.assertEqual("完成", lint_task_deps.state_prefix("完成（附注）"))
        self.assertIsNone(lint_task_deps.state_prefix("已完结"))


class StateConsistencyTest(unittest.TestCase):
    """Cover the three-way agreement between 状态, header mark, and checkboxes."""

    def _task(self, mark: str, state: str, boxes: str = "") -> str:
        return (
            f"### 任务 1: [{mark}] A\n- depends_on: []\n- 状态: {state}\n{boxes}"
        )

    def test_consistent_completed_task_passes(self) -> None:
        text = self._task("x", "完成", "- 验收标准:\n    - [x] 已勾选\n")
        self.assertEqual([], lint_task_deps.state_consistency_errors(text))

    def test_completed_state_with_unchecked_header_fails(self) -> None:
        text = self._task(" ", "完成", "- 验收标准:\n    - [x] 已勾选\n")
        errors = lint_task_deps.state_consistency_errors(text)
        self.assertEqual(1, len(errors))
        self.assertIn("任务头标记为 `[ ]`", errors[0])

    def test_completed_state_with_unchecked_boxes_fails(self) -> None:
        text = self._task("x", "完成", "- 验收标准:\n    - [x] 甲\n    - [ ] 乙\n")
        errors = lint_task_deps.state_consistency_errors(text)
        self.assertEqual(1, len(errors))
        self.assertIn("有 1 个未勾选复选框", errors[0])

    def test_completed_header_with_any_open_state_fails(self) -> None:
        """反方向对每个非完成态都成立——读者按任务头会认为任务已完成。"""
        for state in ("需人工（合并冲突）", "阻塞（上游未合并）", "进行中", "未开始"):
            with self.subTest(state=state):
                errors = lint_task_deps.state_consistency_errors(self._task("x", state))
                self.assertEqual(1, len(errors))
                self.assertIn("任务头标记为 `[x]`（完成）", errors[0])

    def test_manual_state_keeps_unchecked_boxes(self) -> None:
        """需人工 / 阻塞 是终态但非完成态，未勾选项正是未达成记录。"""
        text = self._task(" ", "需人工（合并冲突）", "- 验收标准:\n    - [ ] 乙\n")
        self.assertEqual([], lint_task_deps.state_consistency_errors(text))

    def test_missing_header_mark_is_treated_as_undeclared(self) -> None:
        """标记整体缺失时没有可对立的完成信号，跳过标记比对（保兼容）。"""
        self.assertEqual(
            [], lint_task_deps.state_consistency_errors("### 任务 1: A\n- 状态: 完成\n")
        )

    def test_missing_header_mark_still_checks_boxes(self) -> None:
        """标记缺失不豁免复选框判定——两者是独立信号。"""
        text = "### 任务 1: A\n- 状态: 完成\n- 验收标准:\n    - [ ] 甲\n"
        errors = lint_task_deps.state_consistency_errors(text)
        self.assertEqual(1, len(errors))
        self.assertIn("有 1 个未勾选复选框", errors[0])

    def test_trailing_sections_and_fences_are_excluded(self) -> None:
        text = (
            "### 任务 1: [x] A\n- 状态: 完成\n"
            "```markdown\n- [ ] 围栏内示例\n- 状态: 阻塞\n```\n"
            "## 知识同步\n\n- [ ] 尾部小节未勾选项\n- 状态: Pending\n"
        )
        self.assertEqual([], lint_task_deps.state_consistency_errors(text))

    def test_duplicate_state_declaration_is_reported(self) -> None:
        """`field()` 用 re.search 只读第一行，重复声明在 field_errors 里是
        静默的，因此必须在此判定，否则 `完成` + `阻塞` 的矛盾形态可过门。"""
        text = "### 任务 1: [ ] A\n- 状态: 完成\n- 状态: 阻塞\n"
        errors = lint_task_deps.state_consistency_errors(text)
        self.assertEqual(1, len(errors))
        self.assertIn("声明了 2 个 状态 字段", errors[0])

    def test_invalid_state_value_is_left_to_field_errors(self) -> None:
        """取值非法由 field_errors 报，此处不重复。"""
        self.assertEqual(
            [],
            lint_task_deps.state_consistency_errors("### 任务 1: [x] A\n- 状态: 已完结\n"),
        )
        errors = lint_task_deps.field_errors(
            lint_task_deps.parse_tasks("### 任务 1: [x] A\n- depends_on: []\n- 状态: 已完结\n")
        )
        self.assertTrue(any("状态 `已完结` 不含合法值" in e for e in errors), errors)

    def test_cli_state_consistency_switch_reports_exit_codes(self) -> None:
        good = self._task("x", "完成", "- 验收标准:\n    - [x] 甲\n")
        bad = self._task(" ", "完成", "- 验收标准:\n    - [ ] 甲\n")
        with tempfile.TemporaryDirectory() as temp_dir:
            for name, text, expected in (("ok", good, 0), ("bad", bad, 1)):
                tasks_file = Path(temp_dir) / f"{name}.md"
                tasks_file.write_text(text, encoding="utf-8")
                self.assertEqual(
                    expected,
                    lint_task_deps.main([str(tasks_file), "--state-consistency"]),
                    name,
                )

    def test_cli_state_consistency_skips_dependency_warnings(self) -> None:
        """归档前开关只读状态一致性，不因缺 depends_on 等结构问题退非 0。"""
        text = "### 任务 1: [x] A\n- 状态: 完成\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = Path(temp_dir) / "tasks.md"
            tasks_file.write_text(text, encoding="utf-8")
            self.assertEqual(
                0, lint_task_deps.main([str(tasks_file), "--state-consistency"])
            )
            self.assertEqual(1, lint_task_deps.main([str(tasks_file)]))


if __name__ == "__main__":
    unittest.main()
