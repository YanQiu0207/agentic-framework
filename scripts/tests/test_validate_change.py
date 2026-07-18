"""Integration tests for the change validator CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts" / "validate_change.py"
FIXTURES = Path(__file__).parent / "fixtures" / "validate-change"
CHANGE = Path("openspec/changes/example-change")


def archive_target() -> Path:
    """Return the valid archive destination for the fixture change."""
    return (
        Path("openspec/changes/archive") / f"{date.today().isoformat()}-example-change"
    )


class ValidateChangeCliTest(unittest.TestCase):
    """Exercises the public CLI against repository-shaped fixtures."""

    def run_validator(
        self,
        fixture: str,
        phase: str,
        *,
        json_output: bool = False,
        change: Path = CHANGE,
        target: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the validator and return its completed process."""
        command = [
            sys.executable,
            str(VALIDATOR),
            "--repo",
            str(FIXTURES / fixture),
            "--change",
            str(change),
            "--phase",
            phase,
        ]
        if json_output:
            command.append("--json")
        if target is not None:
            command.extend(("--archive-target", str(target)))
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            encoding="utf-8",
        )

    def run_repo(
        self,
        repo: Path,
        phase: str,
        *,
        json_output: bool = False,
        target: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the validator against a temporary repository."""
        command = [
            sys.executable,
            str(VALIDATOR),
            "--repo",
            str(repo),
            "--change",
            str(CHANGE),
            "--phase",
            phase,
        ]
        if json_output:
            command.append("--json")
        if target is not None:
            command.extend(("--archive-target", str(target)))
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            encoding="utf-8",
        )

    @contextmanager
    def copied_repo(self, fixture: str) -> Iterator[Path]:
        """Yield a disposable copy of a repository-shaped fixture."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_repo = Path(temporary_directory) / "repo"
            shutil.copytree(FIXTURES / fixture, temporary_repo)
            yield temporary_repo

    def rewrite(
        self,
        repo: Path,
        relative_path: str,
        old: str,
        new: str,
    ) -> None:
        """Replace fixture text and fail when the expected source is absent."""
        path = repo / CHANGE / relative_path
        content = path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new), encoding="utf-8")

    def test_valid_standard_plan_and_delivery(self) -> None:
        """A complete standard change passes plan and delivery gates."""
        for phase in ("plan", "delivery"):
            with self.subTest(phase=phase):
                result = self.run_validator("valid-standard", phase)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_valid_quick_plan_and_delivery(self) -> None:
        """A Quick Draft may omit specs and design."""
        for phase in ("plan", "delivery"):
            with self.subTest(phase=phase):
                result = self.run_validator("valid-quick", phase)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_missing_required_artifacts_fail_plan(self) -> None:
        """Missing required artifacts are deterministic errors."""
        cases = {
            "missing-proposal": "proposal.md",
            "missing-tasks": "tasks.md",
            "missing-specs-standard": "specs",
        }
        for fixture, expected in cases.items():
            with self.subTest(fixture=fixture):
                result = self.run_validator(fixture, "plan")
                self.assertEqual(1, result.returncode)
                self.assertIn(expected, result.stdout + result.stderr)

    def test_cyclic_tasks_fail_plan(self) -> None:
        """A multi-node task dependency cycle is rejected."""
        result = self.run_validator("cyclic-tasks", "plan")
        self.assertEqual(1, result.returncode)
        self.assertRegex(result.stdout + result.stderr, r"(?i)(cycle|cyclic|环)")

    def test_unfinished_delivery_is_rejected(self) -> None:
        """Pending tasks and unchecked subtasks block delivery."""
        result = self.run_validator("unfinished-delivery", "delivery")
        self.assertEqual(1, result.returncode)
        self.assertRegex(
            result.stdout + result.stderr,
            r"(?i)(unfinished|pending|未完成)",
        )

    def test_task_review_contract_is_required_at_plan(self) -> None:
        """Every production task declares its risk-tiered review contract."""
        cases = (
            ("- Review Profile: standard\n", "", "OPSX037"),
            ("- Task Review: PASS\n", "", "OPSX038"),
            ("- Review Profile: standard", "- Review Profile: lightweight", "OPSX037"),
        )
        for old, new, expected_rule in cases:
            with self.subTest(rule=expected_rule, replacement=new):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(temporary_repo, "tasks.md", old, new)
                    result = self.run_repo(temporary_repo, "plan", json_output=True)
                    rules = {
                        item["rule_id"] for item in json.loads(result.stdout)["errors"]
                    }
                    self.assertEqual(1, result.returncode)
                    self.assertIn(expected_rule, rules)

    def test_pending_task_review_blocks_delivery(self) -> None:
        """A completed task cannot pass delivery before its review passes."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- Task Review: PASS",
                "- Task Review: Pending",
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)

    def test_duplicate_task_review_metadata_is_rejected(self) -> None:
        """Conflicting or duplicate review metadata fails closed."""
        cases = (
            (
                "- Task Review: PASS",
                "- Task Review: PASS\n- Task Review: Pending",
                "OPSX038",
            ),
            (
                "- Review Profile: standard",
                "- Review Profile: standard\n- Review Profile: strict",
                "OPSX037",
            ),
        )
        for old, new, expected_rule in cases:
            with self.subTest(rule=expected_rule):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(temporary_repo, "tasks.md", old, new)
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    rules = {
                        item["rule_id"] for item in json.loads(result.stdout)["errors"]
                    }
                    self.assertEqual(1, result.returncode)
                    self.assertIn(expected_rule, rules)

    def test_review_metadata_inside_code_fence_is_ignored(self) -> None:
        """Example text in a fenced block cannot satisfy task metadata."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- Task Review: PASS",
                "```text\n- Task Review: PASS\n```",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)

    def test_review_not_pass_blocks_archive(self) -> None:
        """Archive requires a PASS review state."""
        result = self.run_validator(
            "review-not-pass", "archive", target=archive_target()
        )
        self.assertEqual(1, result.returncode)
        self.assertRegex(
            result.stdout + result.stderr,
            r"(?i)(code review|review|评审)",
        )

    def test_forbidden_central_specs_are_rejected(self) -> None:
        """The repository must not contain an openspec/specs truth store."""
        result = self.run_validator("forbidden-central-specs", "plan")
        self.assertEqual(1, result.returncode)
        self.assertIn("openspec/specs", result.stdout + result.stderr)

    def test_json_output_is_machine_readable(self) -> None:
        """JSON mode emits structured success and failure results."""
        success = self.run_validator("valid-standard", "plan", json_output=True)
        self.assertEqual(0, success.returncode, success.stderr)
        success_payload = json.loads(success.stdout)
        self.assertTrue(success_payload["ok"])
        self.assertEqual("plan", success_payload["phase"])
        self.assertEqual([], success_payload["errors"])

        failure = self.run_validator("missing-proposal", "plan", json_output=True)
        self.assertEqual(1, failure.returncode, failure.stderr)
        failure_payload = json.loads(failure.stdout)
        self.assertFalse(failure_payload["ok"])
        self.assertTrue(failure_payload["errors"])
        error = failure_payload["errors"][0]
        for field in ("rule_id", "path", "line", "message", "hint"):
            self.assertIn(field, error)

    def test_exit_code_two_reports_invocation_error(self) -> None:
        """A nonexistent change path is a caller error, not a rule violation."""
        result = self.run_validator(
            "valid-standard",
            "plan",
            change=Path("openspec/changes/not-found"),
        )
        self.assertEqual(2, result.returncode)

    def test_valid_standard_archive(self) -> None:
        """A reviewed change passes archive with an available destination."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            result = self.run_repo(temporary_repo, "archive", target=archive_target())
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_quick_requires_explicit_status(self) -> None:
        """Only explicit status metadata selects the Quick path."""
        with self.copied_repo("valid-quick") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "proposal.md",
                "# Proposal: Example Change（Quick Draft）",
                "# Proposal: Example Change",
            )
            result = self.run_repo(temporary_repo, "plan")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "proposal.md",
                "现有示例缺少确定性校验。",
                "正文提到 Quick Draft，但状态仍是 Standard。",
            )
            shutil.rmtree(temporary_repo / CHANGE / "specs")
            (temporary_repo / CHANGE / "design.md").unlink()
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            payload = json.loads(result.stdout)
            self.assertEqual(1, result.returncode)
            self.assertEqual("standard", payload["change_type"])

    def test_missing_or_empty_proposal_content_fails_plan(self) -> None:
        """A heading alone does not satisfy required proposal content."""
        cases = (
            ("## 2. 目标\n\n- 增加可执行的校验。", "", "OPSX013"),
            (
                "## 4. 验收标准\n\n" "- 执行测试命令后返回退出码 0。",
                "## 4. 验收标准\n",
                "OPSX015",
            ),
        )
        for old, new, expected_rule in cases:
            with self.subTest(rule=expected_rule):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(temporary_repo, "proposal.md", old, new)
                    result = self.run_repo(temporary_repo, "plan", json_output=True)
                    payload = json.loads(result.stdout)
                    rules = {item["rule_id"] for item in payload["errors"]}
                    self.assertEqual(1, result.returncode)
                    self.assertIn(expected_rule, rules)

        with self.copied_repo("valid-standard") as temporary_repo:
            (temporary_repo / CHANGE / "proposal.md").write_text("", encoding="utf-8")
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertIn("OPSX010", rules)

    def test_invalid_self_and_missing_dependencies_fail_plan(self) -> None:
        """Dependencies must be explicit, external, and resolvable."""
        cases = (
            ("- 依赖：Task 1", "- 依赖：稍后决定", None),
            ("- 依赖：Task 1", "- 依赖：Task 2", "OPSX024"),
            ("- 依赖：Task 1", "- 依赖：Task 99", "OPSX025"),
        )
        for old, new, expected_rule in cases:
            with self.subTest(dependency=new):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(temporary_repo, "tasks.md", old, new)
                    result = self.run_repo(temporary_repo, "plan", json_output=True)
                    payload = json.loads(result.stdout)
                    self.assertEqual(1, result.returncode)
                    if expected_rule:
                        rules = {item["rule_id"] for item in payload["errors"]}
                        self.assertIn(expected_rule, rules)

    def test_utf8_bom_files_are_supported(self) -> None:
        """UTF-8 BOM does not corrupt the first heading or task header."""
        with self.copied_repo("valid-standard") as temporary_repo:
            for relative_path in ("proposal.md", "tasks.md"):
                path = temporary_repo / CHANGE / relative_path
                content = path.read_text(encoding="utf-8")
                path.write_text(content, encoding="utf-8-sig")
            result = self.run_repo(temporary_repo, "delivery")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_failed_or_bare_na_execution_record_fails_delivery(self) -> None:
        """Execution records require successful evidence or an N/A reason."""
        cases = (
            (
                "构建命令：`python -m py_compile scripts/validate_change.py`，"
                "退出码 0。",
                "构建命令：命令失败，退出码 1。",
                "OPSX033",
            ),
            (
                "测试命令：`python -m unittest discover -s scripts/tests "
                '-p "test_*.py"`，退出码 0。',
                "测试命令：N/A",
                "OPSX034",
            ),
        )
        for old, new, expected_rule in cases:
            with self.subTest(rule=expected_rule):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(temporary_repo, "tasks.md", old, new)
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    errors = json.loads(result.stdout)["errors"]
                    self.assertEqual(1, result.returncode)
                    self.assertIn(
                        expected_rule,
                        {item["rule_id"] for item in errors},
                    )

    def test_valid_quick_archive(self) -> None:
        """A completed and reviewed Quick change may be archived."""
        with self.copied_repo("valid-quick") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            result = self.run_repo(temporary_repo, "archive", target=archive_target())
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_archive_target_is_required_and_validated(self) -> None:
        """Archive requires an explicit destination with the exact shape."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )

            missing = self.run_repo(temporary_repo, "archive")
            self.assertEqual(2, missing.returncode)

            cases = (
                (
                    Path("openspec/changes/archive/wrong-example-change"),
                    "name",
                ),
                (
                    Path("openspec/archive")
                    / f"{date.today().isoformat()}-example-change",
                    "parent",
                ),
            )
            for target, label in cases:
                with self.subTest(invalid=label):
                    result = self.run_repo(
                        temporary_repo,
                        "archive",
                        json_output=True,
                        target=target,
                    )
                    payload = json.loads(result.stdout)
                    self.assertEqual(1, result.returncode)
                    self.assertTrue(payload["errors"])
                    self.assertIn(
                        "OPSX041",
                        {item["rule_id"] for item in payload["errors"]},
                    )

    def test_finding_lines_point_to_source(self) -> None:
        """Dependency and checkbox findings report their source lines."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- 依赖：Task 1",
                "- 依赖：Task 99",
            )
            tasks_path = temporary_repo / CHANGE / "tasks.md"
            expected_line = next(
                number
                for number, line in enumerate(
                    tasks_path.read_text(encoding="utf-8").splitlines(), 1
                )
                if line == "- 依赖：Task 99"
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            finding = next(item for item in errors if item["rule_id"] == "OPSX025")
            self.assertEqual(expected_line, finding["line"])

        tasks_path = FIXTURES / "unfinished-delivery" / CHANGE / "tasks.md"
        expected_line = next(
            number
            for number, line in enumerate(
                tasks_path.read_text(encoding="utf-8").splitlines(), 1
            )
            if line == "  - [ ] 2.1：覆盖正常路径。"
        )
        result = self.run_validator("unfinished-delivery", "delivery", json_output=True)
        errors = json.loads(result.stdout)["errors"]
        finding = next(item for item in errors if item["rule_id"] == "OPSX031")
        self.assertEqual(expected_line, finding["line"])

    def test_standard_mapping_must_cover_each_artifact(self) -> None:
        """A nonempty mapping table must cover proposal, spec, and design."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "| `spec.md` 稳定退出码 | Task 1 | 实现退出码 |\n"
                "| `design.md` §1 | Task 1 | 实现设计方案 |",
                "| `proposal.md` §3 | Task 1 | 重复 Proposal 映射 |",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            self.assertEqual(1, result.returncode)
            combined = " ".join(item["message"] for item in errors)
            self.assertRegex(combined, r"(?i)(spec|design|映射)")

    def test_quick_tasks_must_map_acceptance_criteria(self) -> None:
        """Quick tasks must explicitly map the proposal acceptance criteria."""
        with self.copied_repo("valid-quick") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- 文档映射：`proposal.md` 验收标准",
                "- 文档映射：`proposal.md` §2.1",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            self.assertEqual(1, result.returncode)
            combined = " ".join(item["message"] for item in errors)
            self.assertRegex(combined, r"(?i)(acceptance|验收|映射)")

    @unittest.skipUnless(os.name == "nt", "Windows Junction regression test")
    def test_specs_junction_outside_change_fails_plan(self) -> None:
        """A Junction must not let external artifacts satisfy the Plan gate."""
        with self.copied_repo("valid-standard") as temporary_repo:
            change = temporary_repo / CHANGE
            specs = change / "specs"
            outside = temporary_repo.parent / "outside-specs"
            shutil.move(str(specs), str(outside))
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(specs), str(outside)],
                check=False,
                capture_output=True,
                text=True,
            )
            if command.returncode != 0:
                self.skipTest(f"Junction creation failed: {command.stderr}")
            try:
                result = self.run_repo(temporary_repo, "plan", json_output=True)
                payload = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn(
                    "OPSX004", {item["rule_id"] for item in payload["errors"]}
                )
            finally:
                specs.rmdir()


if __name__ == "__main__":
    unittest.main()
