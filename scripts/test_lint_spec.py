"""Regression tests for spec completeness linting."""

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "skills" / "workflow-code-generation" / "scripts"
    ),
)
import lint_spec

STANDARD_TEMPLATE = lint_spec.read(lint_spec.STANDARD_TEMPLATE)
QUICK_TEMPLATE = lint_spec.read(lint_spec.QUICK_TEMPLATE)

FILLED_SPEC = """# Feature: 缓存层
**状态**: Approved

## 1. 背景 (Background)
现有查询直接打数据库，高峰期延迟超标。

## 2. 目标 (Goals)
热点查询 P99 延迟降到 10ms 以内。

## 3. 需求细化 (Requirements)
支持按 key 失效，兼容现有接口。

## 4. 设计方案 (Design)
引入两级缓存，本地 LRU + Redis。

## 5. 备选方案 (Alternatives Considered)
N/A - 本需求不适用
"""


class LintSpecTest(unittest.TestCase):
    """Cover status, chapter presence, and placeholder detection."""

    def test_filled_spec_passes_code_phase(self) -> None:
        self.assertEqual([], lint_spec.lint(FILLED_SPEC, "code", STANDARD_TEMPLATE))

    def test_missing_design_chapter_fails_code_but_passes_design(self) -> None:
        spec = FILLED_SPEC.replace(
            "## 4. 设计方案 (Design)\n引入两级缓存，本地 LRU + Redis。\n", ""
        )
        errors = lint_spec.lint(spec, "code", STANDARD_TEMPLATE)
        self.assertTrue(any("第 4 章" in e for e in errors))
        self.assertEqual([], lint_spec.lint(spec, "design", STANDARD_TEMPLATE))

    def test_pristine_template_chapter_is_placeholder(self) -> None:
        errors = lint_spec.lint(
            STANDARD_TEMPLATE.replace(
                "**状态**: Draft / In Review / Approved / Archived", "**状态**: Draft"
            ),
            "code",
            STANDARD_TEMPLATE,
        )
        self.assertTrue(any("第 1 章仅有模板占位" in e for e in errors))

    def test_unpicked_status_placeholder_is_error(self) -> None:
        errors = lint_spec.lint(STANDARD_TEMPLATE, "design", STANDARD_TEMPLATE)
        self.assertTrue(any("未从模板占位中选定单一状态" in e for e in errors))

    def test_quick_draft_requires_core_sections(self) -> None:
        spec = QUICK_TEMPLATE  # 未填写的 Quick Draft 模板
        errors = lint_spec.lint(spec, "code", QUICK_TEMPLATE)
        for name in ("问题", "目标", "整体方案", "验收标准"):
            self.assertTrue(any(name in e for e in errors), name)

    def test_filled_quick_draft_passes(self) -> None:
        spec = """# Tool: 巡检脚本
**状态**: Quick Draft

## 1. 问题与目标
### 问题
现网巡检靠手工，漏检频发。
### 目标
- 每日自动巡检核心链路
### 验收标准
- 巡检结果落盘且失败告警

## 2. 设计方案
### 2.1 整体方案
cron 拉起 Python 脚本，逐项探测后写报告。
"""
        self.assertEqual([], lint_spec.lint(spec, "code", QUICK_TEMPLATE))

    def test_missing_file_returns_cli_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(2, lint_spec.main([str(Path(temp_dir) / "spec.md")]))


if __name__ == "__main__":
    unittest.main()
