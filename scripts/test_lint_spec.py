"""Regression tests for proposal/design completeness linting."""

import tempfile
import unittest
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
import lint_spec

STANDARD_TEMPLATE = lint_spec.read(lint_spec.STANDARD_TEMPLATE)
DESIGN_TEMPLATE = lint_spec.read(lint_spec.DESIGN_TEMPLATE)
QUICK_TEMPLATE = lint_spec.read(lint_spec.QUICK_TEMPLATE)


class TemplatePointerTest(unittest.TestCase):
    """钉死模板指针必须指向现行产物模板，防止回退到已弃用文件。"""

    def test_pointers_target_current_templates(self) -> None:
        self.assertEqual("proposal_template.md", lint_spec.STANDARD_TEMPLATE.name)
        self.assertEqual("design_template.md", lint_spec.DESIGN_TEMPLATE.name)
        self.assertEqual(
            "quick-proposal-template.md", lint_spec.QUICK_TEMPLATE.name
        )
        for path in (
            lint_spec.STANDARD_TEMPLATE,
            lint_spec.DESIGN_TEMPLATE,
            lint_spec.QUICK_TEMPLATE,
        ):
            self.assertTrue(path.is_file(), path)

FILLED_PROPOSAL = """# Proposal: 缓存层
**状态**: Approved

## 1. 背景
现有查询直接打数据库，高峰期延迟超标。

## 2. 目标
热点查询 P99 延迟降到 10ms 以内。

## 3. 需求概览
支持按 key 失效，兼容现有接口。
"""

FILLED_DESIGN = """# Design: 缓存层
**状态**: Approved

## 4. 设计方案
引入两级缓存，本地 LRU + Redis。

## 5. 备选方案
N/A - 本需求不适用

## 6. 业界调研
参考 Redis 与 Guava Cache 的分层实践。

## 7. 测试计划
单元测试覆盖命中 / 未命中 / 过期三条路径。

## 8. 可观测性与运维
新增缓存命中率指标。

## 9. 参考资料（design）
Redis 文档。
"""


class LintSpecTest(unittest.TestCase):
    """Cover status, chapter presence, and placeholder detection."""

    def test_filled_proposal_passes_code_phase(self) -> None:
        self.assertEqual([], lint_spec.lint(FILLED_PROPOSAL, "code", STANDARD_TEMPLATE))

    def test_pristine_proposal_template_is_placeholder(self) -> None:
        """复制 proposal 模板未填写必须被拦下（对照现行 proposal 模板）。"""
        pristine = STANDARD_TEMPLATE.replace(
            "**状态**：Draft", "**状态**：Approved"
        )
        errors = lint_spec.lint(pristine, "code", STANDARD_TEMPLATE)
        self.assertTrue(any("第 1 章" in e for e in errors))
        self.assertTrue(any("第 2 章" in e for e in errors))
        self.assertTrue(any("第 3 章" in e for e in errors))

    def test_pristine_design_template_is_placeholder(self) -> None:
        """复制 design 模板未填写必须被拦下（design-code phase 查 4~9 章）。"""
        errors = lint_spec.lint(
            DESIGN_TEMPLATE.replace(
                "**状态**: Draft / In Review / Approved / Archived", "**状态**: Draft"
            ),
            "design-code",
            DESIGN_TEMPLATE,
        )
        for number in range(4, 10):
            self.assertTrue(any(f"第 {number} 章" in e for e in errors), number)

    def test_filled_design_passes_design_code_phase(self) -> None:
        self.assertEqual(
            [], lint_spec.lint(FILLED_DESIGN, "design-code", DESIGN_TEMPLATE)
        )

    def test_design_missing_chapter_fails_design_code(self) -> None:
        design = FILLED_DESIGN.replace("## 9. 参考资料（design）\nRedis 文档。\n", "")
        errors = lint_spec.lint(design, "design-code", DESIGN_TEMPLATE)
        self.assertTrue(any("第 9 章" in e for e in errors))

    def test_proposal_chapter_4_not_required(self) -> None:
        """proposal 第 4 章起（知识影响 / 参考资料）不在章节校验范围。"""
        spec = FILLED_PROPOSAL + "\n## 4. 知识影响\n无长期知识影响：内部工具。\n"
        self.assertEqual([], lint_spec.lint(spec, "code", STANDARD_TEMPLATE))

    def test_unpicked_status_placeholder_is_error(self) -> None:
        errors = lint_spec.lint(DESIGN_TEMPLATE, "design-code", DESIGN_TEMPLATE)
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
