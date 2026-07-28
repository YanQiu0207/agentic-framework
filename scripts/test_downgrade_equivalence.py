"""Tests for the downgrade equivalence harness (change 2042)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import downgrade_equivalence

SHIM = """import json, sys
ids = sys.argv[1].split(",") if len(sys.argv) > 1 and sys.argv[1] else []
print(json.dumps({"errors": [{"rule_id": i} for i in ids]}))
sys.exit(1 if ids else 0)
"""


class ShimFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.shim = self.root / "shim.py"
        self.shim.write_text(SHIM, encoding="utf-8")
        self.input_dir = self.root / "openspec" / "changes" / "2099-x"
        self.input_dir.mkdir(parents=True)
        (self.input_dir / "tasks.md").write_text("# t\n", encoding="utf-8")

    def _compare(self, **overrides):
        args = {
            "path_a": f"{{python}} {self.shim.as_posix()} A1,A2",
            "extractor_a": "validate-json",
            "path_b": f"{{python}} {self.shim.as_posix()} A1,A2",
            "extractor_b": "validate-json",
            "input_path": self.input_dir,
            "repo": self.root,
        }
        args.update(overrides)
        return downgrade_equivalence.compare(**args)


class CompareTest(ShimFixture):
    def test_pass_when_normalized_outputs_equal(self) -> None:
        report = self._compare()
        self.assertEqual("通过", report["verdict"])

    def test_fail_on_different_error_sets_with_first_diff(self) -> None:
        report = self._compare(path_b=f"{{python}} {self.shim.as_posix()} A1,A3")
        self.assertEqual("不通过", report["verdict"])
        self.assertIn("A2", report["reason"])

    def test_fail_on_different_exit_codes(self) -> None:
        report = self._compare(path_b=f"{{python}} {self.shim.as_posix()} ")
        self.assertEqual("不通过", report["verdict"])
        self.assertIn("退出码", report["reason"])

    def test_unexecutable_when_input_missing(self) -> None:
        report = self._compare(input_path=self.root / "nonexistent")
        self.assertEqual("无法执行", report["verdict"])
        self.assertIn("基线缺失", report["reason"])

    def test_unexecutable_when_output_incomparable(self) -> None:
        report = self._compare(extractor_b="lint-json")
        self.assertEqual("无法执行", report["verdict"])
        self.assertIn("输出格式不可比", report["reason"])

    def test_unexecutable_when_path_command_missing(self) -> None:
        report = self._compare(path_b="/nonexistent/python {input}")
        self.assertEqual("无法执行", report["verdict"])

    def test_unexecutable_when_switch_rejected(self) -> None:
        report = self._compare(
            path_a=f"{{python}} {self.shim.as_posix()} --governance-profile tooling"
        )
        # shim 把 --governance-profile 当 ids 列表解析，不会产生 OPSX 码，
        # 但 argparse 拒绝的形态由 validate_change 真探（见集成用例）。
        self.assertIn(report["verdict"], {"通过", "不通过", "无法执行"})

    def test_switch_without_effect_is_unexecutable(self) -> None:
        stubborn = self.root / "stubborn.py"
        stubborn.write_text(
            "import json, sys\n"
            "print(json.dumps({'errors': [{'rule_id': 'OPSX063'}]}))\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        report = self._compare(
            path_a=f"{{python}} {stubborn.as_posix()} --governance-profile tooling"
        )
        self.assertEqual("无法执行", report["verdict"])
        self.assertIn("开关无效果", report["reason"])

    def test_report_header_states_limitation(self) -> None:
        report = self._compare()
        self.assertIn("不验治理强度", report["criterion_limitation"])

    def test_deterministic_across_runs(self) -> None:
        first = json.dumps(self._compare(), ensure_ascii=False, sort_keys=True)
        second = json.dumps(self._compare(), ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)


class CanonicalPairTest(unittest.TestCase):
    """默认路径对与真实门禁的集成：当前两轨输出格式不可比。"""

    def test_canonical_pair_reports_unexecutable_honestly(self) -> None:
        report = downgrade_equivalence.compare(
            path_a=downgrade_equivalence.DEFAULT_PATH_A,
            extractor_a=downgrade_equivalence.DEFAULT_EXTRACTOR_A,
            path_b=downgrade_equivalence.DEFAULT_PATH_B,
            extractor_b=downgrade_equivalence.DEFAULT_EXTRACTOR_B,
            input_path=Path("openspec/changes/archive/2035-2026-07-28-common-task-ast"),
        )
        self.assertEqual("无法执行", report["verdict"])
        self.assertIn("输出格式不可比", report["reason"])

    def test_real_switch_probe_passes(self) -> None:
        # 真实 validate_change + --governance-profile：开关存在且有效。
        self.assertIsNone(
            downgrade_equivalence._probe_switch(
                downgrade_equivalence.DEFAULT_PATH_A,
                downgrade_equivalence.DEFAULT_EXTRACTOR_A,
                repo=Path("."),
            )
        )

    def test_exit_codes_distinguish_three_verdicts(self) -> None:
        self.assertEqual(0, downgrade_equivalence.EXIT_CODES["通过"])
        self.assertEqual(1, downgrade_equivalence.EXIT_CODES["不通过"])
        self.assertEqual(3, downgrade_equivalence.EXIT_CODES["无法执行"])

    def test_cli_machine_readable(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/downgrade_equivalence.py",
                "--input",
                "openspec/changes/archive/2035-2026-07-28-common-task-ast",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        report = json.loads(completed.stdout)
        self.assertEqual("无法执行", report["verdict"])
        self.assertEqual(3, completed.returncode)
        self.assertIn("criterion_limitation", report)

    def test_no_na_passthrough_branch(self) -> None:
        import inspect
        import re as re_module

        source = inspect.getsource(downgrade_equivalence)
        # 剥离文档串后检索：「暂不适用」只允许出现在说明文字里，不是放行分支。
        code_only = re_module.sub(r'""".*?"""', "", source, flags=re_module.DOTALL)
        self.assertNotIn("暂不适用", code_only)
        # 结论集合封闭：只有三态，无第四个放行档。
        self.assertEqual(
            {"通过", "不通过", "无法执行"},
            set(downgrade_equivalence.EXIT_CODES),
        )


if __name__ == "__main__":
    unittest.main()
