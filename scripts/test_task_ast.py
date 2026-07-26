"""Unit tests for the read-only common task AST (change 2035 Task 2)."""

from __future__ import annotations

import inspect
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import task_ast


class TaskNodeContractTest(unittest.TestCase):
    """节点契约：字段齐全、status_raw 三态可区分、依赖字段为原始串。"""

    def test_node_fields_match_contract(self) -> None:
        node = task_ast.parse("### 任务 1：[x] 实现\n- depends_on: []\n").tasks[0]
        for name in (
            "number",
            "status_raw",
            "description",
            "line",
            "end_line",
            "body_start",
            "body_end",
            "body",
            "strict_header",
            "dep_field_name",
            "dep_field_raw",
        ):
            self.assertTrue(hasattr(node, name), name)

    def test_missing_bracket_and_empty_bracket_are_distinguishable(self) -> None:
        doc = task_ast.parse("### 任务 1：实现\n### 任务 2：[] 实现\n")
        self.assertIsNone(doc.tasks[0].status_raw)
        self.assertEqual("", doc.tasks[1].status_raw)

    def test_status_raw_is_unstripped_original(self) -> None:
        node = task_ast.parse("### 任务 1：[ x ] 实现\n").tasks[0]
        self.assertEqual(" x ", node.status_raw)
        self.assertEqual("实现", node.description)

    def test_description_falls_back_to_text_after_colon(self) -> None:
        node = task_ast.parse("### 任务 1：裸描述 [没有括号\n").tasks[0]
        self.assertIsNone(node.status_raw)
        self.assertEqual("裸描述 [没有括号", node.description)

    def test_dep_field_raw_is_unparsed_and_name_distinguishes_legacy(self) -> None:
        doc = task_ast.parse(
            "### 任务 1：甲\n- depends_on: Task 2, 3\n"
            "### 任务 2：乙\n- 依赖: Task 1\n"
        )
        self.assertEqual("depends_on", doc.tasks[0].dep_field_name)
        self.assertEqual("Task 2, 3", doc.tasks[0].dep_field_raw)
        self.assertEqual("依赖", doc.tasks[1].dep_field_name)
        self.assertEqual("Task 1", doc.tasks[1].dep_field_raw)

    def test_dep_field_absent_and_empty_are_distinguishable(self) -> None:
        doc = task_ast.parse("### 任务 1：甲\n- depends_on:\n### 任务 2：乙\n")
        self.assertEqual(("depends_on", ""), (
            doc.tasks[0].dep_field_name,
            doc.tasks[0].dep_field_raw,
        ))
        self.assertIsNone(doc.tasks[1].dep_field_name)
        self.assertIsNone(doc.tasks[1].dep_field_raw)

    def test_depends_on_wins_over_legacy_field(self) -> None:
        doc = task_ast.parse(
            "### 任务 1：甲\n- 依赖: Task 2\n- depends_on: Task 3\n"
        )
        self.assertEqual("depends_on", doc.tasks[0].dep_field_name)
        self.assertEqual("Task 3", doc.tasks[0].dep_field_raw)

    def test_duplicate_ids_recorded_without_exception(self) -> None:
        doc = task_ast.parse("### 任务 1：甲\n### 任务 1：乙\n### 任务 1：丙\n")
        self.assertEqual([1], doc.duplicate_ids)
        self.assertEqual(3, len(doc.tasks))

    def test_fenced_fake_header_is_still_a_header(self) -> None:
        # 两侧旧实现都在扫任务头时不剔除围栏，伪任务头会被当真——AST 保持该行为，
        # 分歧是否消除是独立的策略问题（design §8）。
        doc = task_ast.parse(
            "### 任务 1：甲\n```text\n### 任务 99：伪\n```\n### 任务 2：乙\n"
        )
        self.assertEqual([1, 99, 2], [node.number for node in doc.tasks])


class CoordinateInvariantTest(unittest.TestCase):
    """双坐标不变式：行号区间与字符 offset 区间指向同一任务。"""

    TEXT = (
        "# 头部\n\n### 任务 1：[ ] 甲\n- depends_on: []\n\n"
        "### 任务 2：[x] 乙\n- depends_on: Task 1\n- 状态: 完成\n"
    )

    def test_line_range_and_offset_range_cover_same_task(self) -> None:
        doc = task_ast.parse(self.TEXT)
        lines = self.TEXT.splitlines()
        for node in doc.tasks:
            # 独立重算行起始 offset，不依赖实现内部状态。
            line_start = sum(len(lines[i]) + 1 for i in range(node.line - 1))
            region_from_lines = "\n".join(lines[node.line - 1 : node.end_line - 1])
            region_from_offsets = self.TEXT[line_start : node.body_end]
            # 两坐标系覆盖同一任务，仅差末尾换行。
            self.assertIn(
                region_from_offsets,
                (region_from_lines, region_from_lines + "\n"),
                f"任务 {node.number} 的行号区间与 offset 区间不指向同一任务",
            )
            # body 起点落在任务头核心前缀（至冒号）结束处。
            header_prefix = self.TEXT[line_start : node.body_start]
            self.assertTrue(lines[node.line - 1].startswith(header_prefix))
            self.assertRegex(header_prefix, r"^###\s*任务\s*\d+\s*[:：]$")
            self.assertEqual(
                node.body, self.TEXT[node.body_start : node.body_end]
            )

    def test_end_line_is_half_open_and_last_task_reaches_eof(self) -> None:
        doc = task_ast.parse(self.TEXT)
        self.assertEqual(3, doc.tasks[0].line)
        self.assertEqual(6, doc.tasks[0].end_line)  # 下一个任务头的行号
        self.assertEqual(len(doc.lines) + 1, doc.tasks[1].end_line)
        self.assertEqual(len(self.TEXT), doc.tasks[1].body_end)


class MetadataRegionTest(unittest.TestCase):
    """区域切分：围栏剔除、标题终止、两种终止规则的显式分歧。"""

    def test_fences_and_marker_lines_are_removed(self) -> None:
        doc = task_ast.parse(
            "### 任务 1：甲\n- 状态: 未开始\n```\n- 状态: 围栏内\n```\n- 文件: `a.py`\n"
        )
        region = task_ast.metadata_region(
            doc.lines, doc.tasks[0].line, doc.tasks[0].end_line
        )
        self.assertEqual(["- 状态: 未开始", "- 文件: `a.py`"], region)

    def test_region_stops_at_next_heading_of_any_level(self) -> None:
        doc = task_ast.parse(
            "### 任务 1：甲\n- 状态: 未开始\n#### 子节\n- 状态: 子节内\n"
        )
        region = task_ast.metadata_region(
            doc.lines, doc.tasks[0].line, doc.tasks[0].end_line
        )
        self.assertEqual(["- 状态: 未开始"], region)

    def test_orphan_heading_divergence_is_explicit(self) -> None:
        # 结论：孤立 `### ` 空标题行命中 ANY_HEADING_RE（`\s+` 即终止），
        # 不命中 SECTION_HEADING_RE（要求非空白标题字符，继续扫描）。
        # 两个调用方各保留其历史规则：Tooling 的 state_consistency_errors 用
        # ANY_HEADING_RE，Production 的 OPSX056 用 SECTION_HEADING_RE。
        doc = task_ast.parse(
            "### 任务 1：甲\n- 状态: 未开始\n### \n- 状态: 空标题后\n"
        )
        node = doc.tasks[0]
        any_region = task_ast.metadata_region(
            doc.lines, node.line, node.end_line, stop_re=task_ast.ANY_HEADING_RE
        )
        section_region = task_ast.metadata_region(
            doc.lines, node.line, node.end_line, stop_re=task_ast.SECTION_HEADING_RE
        )
        self.assertEqual(["- 状态: 未开始"], any_region)
        # SECTION 规则不停在空标题行：该行本身作为普通内容留在区域内。
        self.assertEqual(
            ["- 状态: 未开始", "### ", "- 状态: 空标题后"], section_region
        )

    def test_section_heading_matches_multi_blank_title_like_section_re(self) -> None:
        # 与 Production `SECTION_RE` 的匹配语义对齐：`###  `（两个空白）中一个
        # 空白可充当标题字符，两种规则都视为标题；`### `（单个空白）则分歧。
        self.assertIsNotNone(task_ast.ANY_HEADING_RE.match("###  "))
        self.assertIsNotNone(task_ast.SECTION_HEADING_RE.match("###  "))
        self.assertIsNotNone(task_ast.ANY_HEADING_RE.match("### "))
        self.assertIsNone(task_ast.SECTION_HEADING_RE.match("### "))
        for line in ("###", "####### 超出六级"):
            self.assertIsNone(task_ast.ANY_HEADING_RE.match(line))
            self.assertIsNone(task_ast.SECTION_HEADING_RE.match(line))


class FieldLocationTest(unittest.TestCase):
    """字段定位：缺失与空值可区分；别名归一仅限大小写与 `_`/空格等价。"""

    def test_missing_field_vs_empty_value(self) -> None:
        region = ["- 状态: 未开始", "- review_profile:"]
        self.assertIsNone(task_ast.find_field(region, ("context_files",)))
        name, value, _offset = task_ast.find_field(region, ("review_profile",))
        self.assertEqual("review_profile", name)
        self.assertEqual("", value)

    def test_alias_group_matches_case_and_underscore_space(self) -> None:
        region = ["- Review Profile: strict"]
        found = task_ast.find_field(region, ("review_profile", "Review Profile"))
        self.assertIsNotNone(found)
        self.assertEqual("Review Profile", found[0])
        self.assertEqual("strict", found[1])

    def test_alias_rules_do_not_fuzzy_match(self) -> None:
        region = ["- review_profile_extra: strict", "- my review_profile: x"]
        self.assertEqual([], task_ast.find_fields(region, ("review_profile",)))

    def test_find_fields_returns_all_matches(self) -> None:
        region = ["- review_profile: standard", "- Review Profile: strict"]
        found = task_ast.find_fields(region, ("review_profile", "Review Profile"))
        self.assertEqual(2, len(found))
        self.assertEqual(["standard", "strict"], [value for _n, value, _o in found])


class ModulePurityTest(unittest.TestCase):
    """AST 只做解析：无 OPSX 编号、无退出码、无 argparse、无反向导入。"""

    def test_no_verdict_or_cli_vocabulary_in_source(self) -> None:
        source = inspect.getsource(task_ast)
        # 文档串允许提及「OPSX 编号」一类职责说明；禁止的是裁决实现本身。
        self.assertIsNone(re.search(r"OPSX\d", source))
        for token in ("argparse", "sys.exit", "exit_code"):
            self.assertNotIn(token, source)

    def test_no_import_of_callers(self) -> None:
        source = inspect.getsource(task_ast)
        for name in ("validate_change", "lint_task_deps", "check_delivery"):
            self.assertIsNone(re.search(rf"^\s*(import|from)\s+{name}", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
