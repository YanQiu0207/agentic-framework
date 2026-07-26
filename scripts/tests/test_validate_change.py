"""Integration tests for the change validator CLI."""

from __future__ import annotations

import json
import locale
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
CHANGE = Path("openspec/changes/1-example-change")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(
    0,
    str(
        REPO_ROOT / "skills" / "workflow-code-generation" / "scripts"
    ),
)
import check_delivery
import validate_change
import workspace_residue


def archive_target() -> Path:
    """Return the valid archive destination for the fixture change."""
    return (
        Path("openspec/changes/archive")
        / f"1-{date.today().isoformat()}-example-change"
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
        change: Path = CHANGE,
        target: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run the validator against a temporary repository."""
        command = [
            sys.executable,
            str(VALIDATOR),
            "--repo",
            str(repo),
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

    def test_plan_json_reports_stable_dependency_waves(self) -> None:
        """A valid plan exposes deterministic waves for the Production executor."""
        result = self.run_validator("valid-standard", "plan", json_output=True)
        payload = json.loads(result.stdout)

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual([[1], [2]], payload["waves"])

    def test_ticket_number_is_required_in_active_change_name(self) -> None:
        """An active Change must begin with a numeric ticket prefix."""
        for invalid_name in (
            "example-change",
            "abc-example-change",
            "12x-example-change",
        ):
            with self.subTest(invalid_name=invalid_name):
                with self.copied_repo("valid-standard") as temporary_repo:
                    invalid_change = Path("openspec/changes") / invalid_name
                    (temporary_repo / CHANGE).rename(temporary_repo / invalid_change)
                    result = self.run_repo(
                        temporary_repo,
                        "plan",
                        json_output=True,
                        change=invalid_change,
                    )

                self.assertEqual(1, result.returncode)
                rules = {
                    item["rule_id"] for item in json.loads(result.stdout)["errors"]
                }
                self.assertIn("OPSX003", rules)

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

    def test_long_term_specs_are_allowed(self) -> None:
        """A project may keep auxiliary long-term knowledge under openspec/specs."""
        with self.copied_repo("valid-standard") as temporary_repo:
            long_term_spec = (
                temporary_repo / "openspec/specs/business/validator/spec.md"
            )
            long_term_spec.parent.mkdir(parents=True)
            long_term_spec.write_text("# Auxiliary knowledge\n", encoding="utf-8")
            result = self.run_repo(temporary_repo, "plan")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_delta_path_must_mirror_a_controlled_knowledge_root(self) -> None:
        """A Change Delta must map deterministically into long-term Specs."""
        with self.copied_repo("valid-standard") as temporary_repo:
            valid = temporary_repo / CHANGE / "specs/business/validator/spec.md"
            invalid = temporary_repo / CHANGE / "specs/validator/spec.md"
            invalid.parent.mkdir(parents=True, exist_ok=True)
            valid.replace(invalid)
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX042", rules)

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

    def test_archive_requires_completed_knowledge_sync(self) -> None:
        """A mapped Delta cannot be archived while its sync is pending."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "| specs/business/validator/spec.md | "
                "openspec/specs/business/validator/spec.md | ADDED | Completed |",
                "| specs/business/validator/spec.md | "
                "openspec/specs/business/validator/spec.md | ADDED | Pending |",
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX045", rules)

    def test_archive_requires_exact_delta_target_and_conflict_record(self) -> None:
        """Archive fails closed on a wrong target or unresolved conflict record."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "openspec/specs/business/validator/spec.md",
                "openspec/specs/business/wrong/spec.md",
            )
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- 结论：无冲突。",
                "- 状态：Pending",
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX044", rules)
            self.assertIn("OPSX047", rules)

    def test_archive_requires_knowledge_impact_index_and_diff_records(self) -> None:
        """Archive bookkeeping must be complete before the directory is moved."""
        cases = (
            ("proposal.md", "## 5. 知识影响", "## 5. 任务影响", "OPSX043"),
            (
                "tasks.md",
                "openspec/specs/index.md 已更新",
                "TODO",
                "OPSX046",
            ),
            (
                "tasks.md",
                "- 已核对实际 Diff、Change 和测试证据：PASS。",
                "- 核对状态：Pending。",
                "OPSX048",
            ),
        )
        for relative_path, old, new, expected_rule in cases:
            with self.subTest(rule=expected_rule):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(
                        temporary_repo,
                        "tasks.md",
                        "Code Review：Pending",
                        "Code Review：PASS",
                    )
                    self.rewrite(temporary_repo, relative_path, old, new)
                    result = self.run_repo(
                        temporary_repo,
                        "archive",
                        json_output=True,
                        target=archive_target(),
                    )
                    rules = {
                        item["rule_id"] for item in json.loads(result.stdout)["errors"]
                    }
                    self.assertEqual(1, result.returncode)
                    self.assertIn(expected_rule, rules)

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
                    Path("openspec/changes/archive")
                    / f"2-{date.today().isoformat()}-example-change",
                    "ticket",
                ),
                (
                    Path("openspec/changes/archive") / "1-2026-02-30-example-change",
                    "date",
                ),
                (
                    Path("openspec/archive")
                    / f"1-{date.today().isoformat()}-example-change",
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

    def test_archive_requires_project_knowledge_indexes(self) -> None:
        """Archive fails when the minimum openspec index skeleton is incomplete."""
        with self.copied_repo("valid-standard") as temporary_repo:
            (temporary_repo / "openspec" / "specs" / "index.md").unlink()
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            errors = json.loads(result.stdout)["errors"]
            self.assertIn("OPSX049", {item["rule_id"] for item in errors})

    def test_archive_validates_generated_knowledge_metadata(self) -> None:
        """Generated frontend/backend documents identify their code sources."""
        with self.copied_repo("valid-standard") as temporary_repo:
            generated = (
                temporary_repo
                / "openspec"
                / "specs"
                / "backend"
                / "orders"
                / "order-service"
                / "interfaces.md"
            )
            generated.parent.mkdir(parents=True)
            generated.write_text("# Interfaces\n", encoding="utf-8")
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            errors = json.loads(result.stdout)["errors"]
            self.assertIn("OPSX051", {item["rule_id"] for item in errors})

            (generated.parent.parent / "meta.yaml").write_text(
                """services:
    order-service:
        source_ref: git:abc123
        source_paths:
            - services/orders/
        generated_at: 2026-07-19
""",
                encoding="utf-8",
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            errors = json.loads(result.stdout)["errors"]
            self.assertNotIn("OPSX051", {item["rule_id"] for item in errors})

            other = generated.parent.parent / "other-service" / "interfaces.md"
            other.parent.mkdir()
            other.write_text("# Other interfaces\n", encoding="utf-8")
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            errors = json.loads(result.stdout)["errors"]
            self.assertIn("OPSX051", {item["rule_id"] for item in errors})

    def test_external_openspec_link_is_allowed(self) -> None:
        """The project-level openspec link is the sole allowed path reparse point."""
        with self.copied_repo("valid-standard") as temporary_repo:
            openspec = temporary_repo / "openspec"
            external = temporary_repo.parent / "external-openspec"
            shutil.move(str(openspec), str(external))
            try:
                openspec.symlink_to(external, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlink unavailable: {error}")
            result = self.run_repo(temporary_repo, "plan", json_output=True)
            self.assertEqual(0, result.returncode, result.stdout)

    @unittest.skipUnless(os.name == "nt", "Windows Junction regression test")
    def test_external_openspec_junction_is_allowed(self) -> None:
        """A Windows Junction may implement the project-level openspec link."""
        with self.copied_repo("valid-standard") as temporary_repo:
            openspec = temporary_repo / "openspec"
            external = temporary_repo.parent / "external-openspec-junction"
            shutil.move(str(openspec), str(external))
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(openspec), str(external)],
                check=False,
                capture_output=True,
                text=True,
                encoding=locale.getencoding(),
                errors="replace",
            )
            if command.returncode != 0:
                self.skipTest(f"Junction creation failed: {command.stderr}")
            try:
                result = self.run_repo(temporary_repo, "plan", json_output=True)
                self.assertEqual(0, result.returncode, result.stdout)
            finally:
                openspec.rmdir()

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
                encoding=locale.getencoding(),
                errors="replace",
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

    def write_report(self, repo: Path, name: str, payload: str) -> None:
        """Overwrite a review-report fixture under the repository review dir."""
        path = repo / "review-reports" / name
        self.assertTrue(path.parent.is_dir(), path.parent)
        path.write_text(payload, encoding="utf-8")

    def envelope_report(self, scope: str) -> dict[str, object]:
        """Return a schema-shaped Envelope review report for ``scope``."""
        task_scoped = scope == "task"
        return {
            "schema_version": 1,
            "artifact_type": "review-report",
            "artifact_id": "review-1",
            "run_id": "run-1",
            "task_id": "1" if task_scoped else None,
            "attempt": 1 if task_scoped else None,
            "profile": "tooling",
            "harness": "claude-code",
            "producer": "workflow-code-review",
            "commit_sha": "0" * 40,
            "config_digest": "sha256:" + "0" * 64,
            "created_at": "2026-07-25T00:00:00Z",
            "payload": {
                "verdict": "PASS",
                "p0_count": 0,
                "p1_count": 0,
                "scope": scope,
                "review_profile": "standard",
                "round": 0,
            },
        }

    def break_envelope_report(self, report: dict[str, object], case: str) -> None:
        """Mutate an Envelope report into one deterministic failure case."""
        payload = report["payload"]
        assert isinstance(payload, dict)
        if case == "bad_verdict":
            payload["verdict"] = "NEEDS_CHANGES"
        elif case == "p0_positive":
            payload["p0_count"] = 1
        elif case == "p1_positive":
            payload["p1_count"] = 1
        elif case == "wrong_scope":
            payload["scope"] = "integration" if payload["scope"] == "task" else "task"
            task_scoped = payload["scope"] == "task"
            report["task_id"] = "1" if task_scoped else None
            report["attempt"] = 1 if task_scoped else None
        elif case == "bad_profile":
            payload["review_profile"] = "extreme"
        elif case == "negative_round":
            payload["round"] = -1
        elif case == "missing_artifact_type":
            del report["artifact_type"]
        elif case == "wrong_artifact_type":
            report["artifact_type"] = "verify-report"
        else:
            raise AssertionError(f"unknown case: {case}")

    def test_task_review_report_evidence_is_enforced_at_delivery(self) -> None:
        """A PASS Task Review requires a real passing review-report.json."""
        needs_changes = json.dumps(
            {"verdict": "NEEDS_CHANGES", "p0_count": 0, "p1_count": 0}
        )
        p0_positive = json.dumps({"verdict": "PASS", "p0_count": 1, "p1_count": 0})
        p1_positive = json.dumps({"verdict": "PASS", "p0_count": 0, "p1_count": 2})
        wrong_scope = json.dumps(
            {
                "verdict": "PASS",
                "p0_count": 0,
                "p1_count": 0,
                "scope": "integration",
                "review_profile": "standard",
                "round": 0,
            }
        )
        for case in (
            "missing_field",
            "missing_file",
            "invalid_json",
            "bad_verdict",
            "p0_positive",
            "p1_positive",
            "wrong_scope",
            "absolute_path",
            "parent_path",
        ):
            with self.subTest(case=case):
                with self.copied_repo("valid-standard") as temporary_repo:
                    if case == "missing_field":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "- Review Report: review-reports/task-1-review.json\n",
                            "",
                        )
                    elif case == "missing_file":
                        (
                            temporary_repo / "review-reports" / "task-1-review.json"
                        ).unlink()
                    elif case == "invalid_json":
                        self.write_report(
                            temporary_repo, "task-1-review.json", "{ not json"
                        )
                    elif case == "bad_verdict":
                        self.write_report(
                            temporary_repo, "task-1-review.json", needs_changes
                        )
                    elif case == "p0_positive":
                        self.write_report(
                            temporary_repo, "task-1-review.json", p0_positive
                        )
                    elif case == "p1_positive":
                        self.write_report(
                            temporary_repo, "task-1-review.json", p1_positive
                        )
                    elif case == "wrong_scope":
                        self.write_report(
                            temporary_repo, "task-1-review.json", wrong_scope
                        )
                    elif case in {"absolute_path", "parent_path"}:
                        external_report = temporary_repo.parent / "external-review.json"
                        external_report.write_text(
                            json.dumps(
                                {
                                    "verdict": "PASS",
                                    "p0_count": 0,
                                    "p1_count": 0,
                                    "scope": "task",
                                    "review_profile": "standard",
                                    "round": 0,
                                }
                            ),
                            encoding="utf-8",
                        )
                        path_text = (
                            str(external_report)
                            if case == "absolute_path"
                            else "../external-review.json"
                        )
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "review-reports/task-1-review.json",
                            path_text,
                        )
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    errors = json.loads(result.stdout)["errors"]
                    rules = {item["rule_id"] for item in errors}
                    self.assertEqual(1, result.returncode)
                    self.assertIn("OPSX038", rules)
                    if case in {"absolute_path", "parent_path"}:
                        self.assertTrue(
                            any("相对路径" in item["message"] for item in errors),
                            errors,
                        )

    def test_valid_task_review_report_produces_no_new_finding(self) -> None:
        """A satisfied Task Review report leaves delivery clean of OPSX038."""
        result = self.run_validator("valid-standard", "delivery", json_output=True)
        rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("OPSX038", rules)

    def test_change_review_report_evidence_is_enforced_at_archive(self) -> None:
        """A PASS Code Review requires a real passing integration report."""
        needs_changes = json.dumps(
            {"verdict": "NEEDS_CHANGES", "p0_count": 0, "p1_count": 0}
        )
        p0_positive = json.dumps({"verdict": "PASS", "p0_count": 3, "p1_count": 0})
        p1_positive = json.dumps({"verdict": "PASS", "p0_count": 0, "p1_count": 1})
        wrong_scope = json.dumps(
            {
                "verdict": "PASS",
                "p0_count": 0,
                "p1_count": 0,
                "scope": "task",
                "review_profile": "standard",
                "round": 0,
            }
        )
        for case in (
            "missing_field",
            "missing_file",
            "invalid_json",
            "bad_verdict",
            "p0_positive",
            "p1_positive",
            "wrong_scope",
            "duplicate_field",
            "fenced_only",
            "duplicate_review_status",
            "fenced_review_status",
        ):
            with self.subTest(case=case):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(
                        temporary_repo,
                        "tasks.md",
                        "Code Review：Pending",
                        "Code Review：PASS",
                    )
                    if case == "missing_field":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "- Review Report: review-reports/review-report.json\n",
                            "",
                        )
                    elif case == "missing_file":
                        (
                            temporary_repo / "review-reports" / "review-report.json"
                        ).unlink()
                    elif case == "invalid_json":
                        self.write_report(
                            temporary_repo, "review-report.json", "not json"
                        )
                    elif case == "bad_verdict":
                        self.write_report(
                            temporary_repo, "review-report.json", needs_changes
                        )
                    elif case == "p0_positive":
                        self.write_report(
                            temporary_repo, "review-report.json", p0_positive
                        )
                    elif case == "p1_positive":
                        self.write_report(
                            temporary_repo, "review-report.json", p1_positive
                        )
                    elif case == "wrong_scope":
                        self.write_report(
                            temporary_repo, "review-report.json", wrong_scope
                        )
                    elif case == "duplicate_field":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "## 任务列表",
                            "- Review Report: review-reports/review-report.json\n\n## 任务列表",
                        )
                    elif case == "fenced_only":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "- Review Report: review-reports/review-report.json\n",
                            "",
                        )
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "## 任务列表",
                            "```text\n- Review Report: review-reports/review-report.json\n```\n\n## 任务列表",
                        )
                    elif case == "duplicate_review_status":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "## 任务列表",
                            "> Code Review：Pending\n\n## 任务列表",
                        )
                    elif case == "fenced_review_status":
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "> Code Review：PASS\n",
                            "",
                        )
                        self.rewrite(
                            temporary_repo,
                            "tasks.md",
                            "## 任务列表",
                            "```text\nCode Review: PASS\n```\n\n## 任务列表",
                        )
                    result = self.run_repo(
                        temporary_repo,
                        "archive",
                        json_output=True,
                        target=archive_target(),
                    )
                    rules = {
                        item["rule_id"] for item in json.loads(result.stdout)["errors"]
                    }
                    self.assertEqual(1, result.returncode)
                    self.assertIn("OPSX032", rules)
                    if case in {
                        "duplicate_review_status",
                        "fenced_review_status",
                    }:
                        self.assertTrue(
                            any(
                                "Code Review 状态" in item["message"]
                                for item in json.loads(result.stdout)["errors"]
                            )
                        )

    def test_valid_change_review_report_allows_archive(self) -> None:
        """A satisfied integration report keeps archive clean of OPSX032."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("OPSX032", rules)

    def test_envelope_task_review_report_passes_delivery(self) -> None:
        """An Envelope-format task report passes the delivery gate."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.write_report(
                temporary_repo,
                "task-1-review.json",
                json.dumps(self.envelope_report("task")),
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("OPSX038", rules)

    def test_envelope_change_review_report_passes_archive(self) -> None:
        """An Envelope-format integration report passes the archive gate."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            self.write_report(
                temporary_repo,
                "review-report.json",
                json.dumps(self.envelope_report("integration")),
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("OPSX032", rules)

    def test_envelope_task_review_report_failures_block_delivery(self) -> None:
        """Envelope task reports face the same verdict checks as flat reports."""
        cases = (
            "bad_verdict",
            "p0_positive",
            "p1_positive",
            "wrong_scope",
            "bad_profile",
            "negative_round",
            "missing_artifact_type",
            "wrong_artifact_type",
        )
        for case in cases:
            with self.subTest(case=case):
                with self.copied_repo("valid-standard") as temporary_repo:
                    report = self.envelope_report("task")
                    self.break_envelope_report(report, case)
                    self.write_report(
                        temporary_repo,
                        "task-1-review.json",
                        json.dumps(report),
                    )
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    errors = json.loads(result.stdout)["errors"]
                    rules = {item["rule_id"] for item in errors}
                    self.assertEqual(1, result.returncode)
                    self.assertIn("OPSX038", rules)
                    self.assertTrue(
                        any("（Envelope 格式）" in item["message"] for item in errors),
                        errors,
                    )

    def test_envelope_change_review_report_failures_block_archive(self) -> None:
        """Envelope integration reports face the same checks as flat reports."""
        cases = (
            "bad_verdict",
            "p0_positive",
            "p1_positive",
            "wrong_scope",
            "bad_profile",
            "negative_round",
            "missing_artifact_type",
            "wrong_artifact_type",
        )
        for case in cases:
            with self.subTest(case=case):
                with self.copied_repo("valid-standard") as temporary_repo:
                    self.rewrite(
                        temporary_repo,
                        "tasks.md",
                        "Code Review：Pending",
                        "Code Review：PASS",
                    )
                    report = self.envelope_report("integration")
                    self.break_envelope_report(report, case)
                    self.write_report(
                        temporary_repo,
                        "review-report.json",
                        json.dumps(report),
                    )
                    result = self.run_repo(
                        temporary_repo,
                        "archive",
                        json_output=True,
                        target=archive_target(),
                    )
                    errors = json.loads(result.stdout)["errors"]
                    rules = {item["rule_id"] for item in errors}
                    self.assertEqual(1, result.returncode)
                    self.assertIn("OPSX032", rules)
                    self.assertTrue(
                        any("（Envelope 格式）" in item["message"] for item in errors),
                        errors,
                    )

    def test_polyglot_task_review_report_blocks_delivery(self) -> None:
        """Verdict fields at both top level and payload are a format conflict."""
        with self.copied_repo("valid-standard") as temporary_repo:
            report = self.envelope_report("task")
            report["verdict"] = "NEEDS_CHANGES"
            report["p0_count"] = 3
            self.write_report(
                temporary_repo,
                "task-1-review.json",
                json.dumps(report),
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            rules = {item["rule_id"] for item in errors}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)
            self.assertTrue(
                any("格式冲突" in item["message"] for item in errors),
                errors,
            )

    def test_polyglot_change_review_report_blocks_archive(self) -> None:
        """A polyglot integration report is rejected as a format conflict."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "Code Review：Pending",
                "Code Review：PASS",
            )
            report = self.envelope_report("integration")
            report["verdict"] = "NEEDS_CHANGES"
            report["p0_count"] = 3
            self.write_report(
                temporary_repo,
                "review-report.json",
                json.dumps(report),
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            errors = json.loads(result.stdout)["errors"]
            rules = {item["rule_id"] for item in errors}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX032", rules)
            self.assertTrue(
                any("格式冲突" in item["message"] for item in errors),
                errors,
            )

    def test_broken_envelope_payload_is_rejected(self) -> None:
        """A non-object payload gets a directed error, not a flat fallback."""
        for broken_payload in (None, ["not", "a", "report"], "broken"):
            with self.subTest(payload=broken_payload):
                with self.copied_repo("valid-standard") as temporary_repo:
                    report = self.envelope_report("task")
                    report["payload"] = broken_payload
                    self.write_report(
                        temporary_repo,
                        "task-1-review.json",
                        json.dumps(report),
                    )
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    errors = json.loads(result.stdout)["errors"]
                    rules = {item["rule_id"] for item in errors}
                    self.assertEqual(1, result.returncode)
                    self.assertIn("OPSX038", rules)
                    self.assertTrue(
                        any(
                            "payload 必须为 JSON 对象" in item["message"]
                            for item in errors
                        ),
                        errors,
                    )

    def test_envelope_top_level_uppercase_variant_key_is_rejected(self) -> None:
        """A stray uppercase 'Verdict' key alongside payload.verdict is rejected."""
        with self.copied_repo("valid-standard") as temporary_repo:
            report = self.envelope_report("task")
            report["Verdict"] = "PASS"
            self.write_report(
                temporary_repo,
                "task-1-review.json",
                json.dumps(report),
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            rules = {item["rule_id"] for item in errors}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)
            self.assertTrue(
                any(
                    "未知字段" in item["message"] and "Verdict" in item["message"]
                    for item in errors
                ),
                errors,
            )

    def test_envelope_top_level_unknown_stray_key_is_rejected(self) -> None:
        """An arbitrary unknown top-level key on an Envelope report is rejected."""
        with self.copied_repo("valid-standard") as temporary_repo:
            report = self.envelope_report("task")
            report["extra_field"] = "x"
            self.write_report(
                temporary_repo,
                "task-1-review.json",
                json.dumps(report),
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            rules = {item["rule_id"] for item in errors}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)
            self.assertTrue(
                any(
                    "未知字段" in item["message"] and "extra_field" in item["message"]
                    for item in errors
                ),
                errors,
            )

    def test_flat_report_with_stray_payload_key_is_rejected(self) -> None:
        """A passing flat report carrying a non-object payload is rejected."""
        with self.copied_repo("valid-standard") as temporary_repo:
            report = {
                "verdict": "PASS",
                "p0_count": 0,
                "p1_count": 0,
                "scope": "task",
                "review_profile": "standard",
                "round": 0,
                "payload": None,
            }
            self.write_report(
                temporary_repo,
                "task-1-review.json",
                json.dumps(report),
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]
            rules = {item["rule_id"] for item in errors}
            self.assertEqual(1, result.returncode)
            self.assertIn("OPSX038", rules)
            self.assertTrue(
                any("payload 必须为 JSON 对象" in item["message"] for item in errors),
                errors,
            )

    def test_escalated_task_requires_granted_approval_at_delivery(self) -> None:
        """Delivery rejects a completed task whose escalation is still pending."""
        with self.copied_repo("valid-standard") as temporary_repo:
            tasks_path = temporary_repo / CHANGE / "tasks.md"
            content = tasks_path.read_text(encoding="utf-8")
            tasks_path.write_text(
                content.replace(
                    "- Task Review: PASS\n- Review Report: review-reports/task-1-review.json",
                    "- Task Review: PASS\n"
                    "- Escalation: irreversible\n"
                    "- Approval: pending (irreversible)\n"
                    "- Review Report: review-reports/task-1-review.json",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]

        self.assertEqual(1, result.returncode)
        self.assertIn("OPSX052", {item["rule_id"] for item in errors})
        self.assertTrue(
            any(
                "Task 1" in item["message"] and "irreversible" in item["message"]
                for item in errors
            ),
            errors,
        )

    def test_approval_condition_mismatch_or_unknown_is_rejected(self) -> None:
        """Approval conditions must match the escalation and the stable whitelist."""
        cases = (
            (
                "irreversible",
                "granted (scope-change)",
                "Approval 条件与 Escalation 不一致",
            ),
            (
                "unknown-risk",
                "granted (unknown-risk)",
                "unknown-risk",
            ),
        )
        for escalation, approval, expected_message in cases:
            with self.subTest(escalation=escalation, approval=approval):
                with self.copied_repo("valid-standard") as temporary_repo:
                    tasks_path = temporary_repo / CHANGE / "tasks.md"
                    content = tasks_path.read_text(encoding="utf-8")
                    tasks_path.write_text(
                        content.replace(
                            "- Task Review: PASS\n"
                            "- Review Report: review-reports/task-1-review.json",
                            "- Task Review: PASS\n"
                            f"- Escalation: {escalation}\n"
                            f"- Approval: {approval}\n"
                            "- Review Report: review-reports/task-1-review.json",
                            1,
                        ),
                        encoding="utf-8",
                    )
                    result = self.run_repo(temporary_repo, "delivery", json_output=True)
                    errors = json.loads(result.stdout)["errors"]

                self.assertEqual(1, result.returncode)
                self.assertIn("OPSX053", {item["rule_id"] for item in errors})
                self.assertTrue(
                    any(expected_message in item["message"] for item in errors),
                    errors,
                )

    def test_per_task_mode_requires_each_completed_task_to_be_approved(self) -> None:
        """Per-task mode preserves an explicit approval record for every task."""
        with self.copied_repo("valid-standard") as temporary_repo:
            tasks_path = temporary_repo / CHANGE / "tasks.md"
            content = tasks_path.read_text(encoding="utf-8")
            content = content.replace(
                "> Code Review：Pending",
                "> Code Review：Pending\n> 批准模式：per-task",
            )
            tasks_path.write_text(
                content.replace(
                    "- Task Review: PASS\n- Review Report: review-reports/task-1-review.json",
                    "- Task Review: PASS\n"
                    "- Approval: granted (per-task-mode)\n"
                    "- Review Report: review-reports/task-1-review.json",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_repo(temporary_repo, "delivery", json_output=True)
            errors = json.loads(result.stdout)["errors"]

        self.assertEqual(1, result.returncode)
        self.assertIn("OPSX054", {item["rule_id"] for item in errors})
        self.assertTrue(any("Task 2" in item["message"] for item in errors), errors)

    def test_missing_approval_does_not_block_plan_or_non_escalated_delivery(
        self,
    ) -> None:
        """Approval evidence is delivery-only and optional without escalation."""
        with self.copied_repo("valid-standard") as temporary_repo:
            plan = self.run_repo(temporary_repo, "plan", json_output=True)
            delivery = self.run_repo(temporary_repo, "delivery", json_output=True)

        self.assertEqual(0, plan.returncode, plan.stdout + plan.stderr)
        self.assertEqual(0, delivery.returncode, delivery.stdout + delivery.stderr)

    def test_approval_evidence_rules_do_not_run_at_archive(self) -> None:
        """Archive preserves its existing evidence contract without OPSX052-054."""
        with self.copied_repo("valid-standard") as temporary_repo:
            tasks_path = temporary_repo / CHANGE / "tasks.md"
            content = tasks_path.read_text(encoding="utf-8")
            tasks_path.write_text(
                content.replace(
                    "- Task Review: PASS\n- Review Report: review-reports/task-1-review.json",
                    "- Task Review: PASS\n"
                    "- Escalation: irreversible\n"
                    "- Review Report: review-reports/task-1-review.json",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.run_repo(
                temporary_repo,
                "archive",
                json_output=True,
                target=archive_target(),
            )
            rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}

        self.assertNotIn("OPSX052", rules)
        self.assertNotIn("OPSX053", rules)
        self.assertNotIn("OPSX054", rules)


    def _delivery_rules(self, repo: Path) -> set[str]:
        """Run the delivery gate and return the reported rule identifiers."""
        result = self.run_repo(repo, "delivery", json_output=True)
        if result.returncode == 0:
            return set()
        return {item["rule_id"] for item in json.loads(result.stdout)["errors"]}

    def test_strict_without_irreversible_blocks_at_plan(self) -> None:
        """OPSX055: a strict task that declares no irreversible is high-risk yet
        never pauses — the one weakening path the risk-triggered gate must close."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: strict\n"
                "- Escalation: scope-change\n",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
        self.assertEqual(1, result.returncode)
        rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
        self.assertIn("OPSX055", rules)

    def test_irreversible_without_strict_blocks_at_plan(self) -> None:
        """OPSX055 forward direction: irreversible must pair with strict."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n"
                "- Escalation: irreversible\n",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
        self.assertEqual(1, result.returncode)
        rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
        self.assertIn("OPSX055", rules)

    def test_strict_with_irreversible_passes_at_plan(self) -> None:
        """A correctly paired strict + irreversible task passes the coupling."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: strict\n"
                "- Escalation: irreversible\n",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_coupling_skips_tasks_without_escalation_field(self) -> None:
        """A strict task predating this contract keeps validating unchanged."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: strict\n",
            )
            result = self.run_repo(temporary_repo, "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_explicit_none_escalation_participates_in_coupling(self) -> None:
        """An explicit 「无」 counts as declaring the field, so strict still
        must pair with irreversible."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: standard\n",
                "### 任务 1：[completed] 实现校验器\n- Review Profile: strict\n"
                "- Escalation: 无\n",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
        self.assertEqual(1, result.returncode)
        rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
        self.assertIn("OPSX055", rules)

    def test_indented_escalation_blocks_at_plan(self) -> None:
        """An indented field must fail closed, not silently drop the gate."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n  - Escalation: irreversible\n",
            )
            result = self.run_repo(temporary_repo, "plan", json_output=True)
        self.assertEqual(1, result.returncode)
        rules = {item["rule_id"] for item in json.loads(result.stdout)["errors"]}
        self.assertIn("OPSX053", rules)

    def test_list_style_approval_mode_blocks_at_delivery(self) -> None:
        """`- 批准模式：` mimics the header's own field style and must not be
        ignored — silently falling back to risk-triggered would drop a gate the
        user asked for."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "> 任务总数：2\n",
                "> 任务总数：2\n- 批准模式：per-task\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX053", rules)

    def test_misplaced_approval_mode_blocks_at_delivery(self) -> None:
        """A mode declaration after the first task header would silently
        disable per-task mode; it must fail closed instead."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n> 批准模式：per-task\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX053", rules)

    def test_fenced_approval_mode_example_not_flagged(self) -> None:
        """A declaration inside a code fence is documentation, not a real one."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "> 任务总数：2\n",
                "> 任务总数：2\n\n```text\n> 批准模式：per-task\n```\n\n",
            )
            result = self.run_repo(temporary_repo, "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_state_field_absent_skips_opsx056(self) -> None:
        """OPSX056 is opt-in: changes that never carried `- 状态：` keep passing."""
        result = self.run_validator("valid-standard", "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_completed_state_field_with_pending_header_blocks(self) -> None:
        """OPSX056: the shape glm-5.2 produced — only the 状态 field updated."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[pending] 实现校验器\n- 状态：完成\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX056", rules)

    def test_completed_header_with_open_state_field_blocks(self) -> None:
        """Reverse direction: readers trust the header, so this is worse."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n- 状态：阻塞（上游未合并）\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX056", rules)

    def test_consistent_state_field_passes(self) -> None:
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n- 状态：已完成\n",
            )
            result = self.run_repo(temporary_repo, "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_unclassifiable_state_field_fails_closed(self) -> None:
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n- 状态：已收工\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX056", rules)

    def test_duplicate_state_field_blocks(self) -> None:
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n- 状态：完成\n- 状态：阻塞\n",
            )
            rules = self._delivery_rules(temporary_repo)
        self.assertIn("OPSX056", rules)

    def test_trailing_section_state_not_read_as_task_state(self) -> None:
        """`## 知识冲突` carries its own `- 状态: Resolved`; the last task must
        not adopt it. Two archived changes already have this shape."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "- 结论：无冲突。\n",
                "- 状态: Resolved。无冲突。\n",
            )
            result = self.run_repo(temporary_repo, "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_fenced_state_field_example_not_flagged(self) -> None:
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n\n```text\n- 状态：阻塞\n```\n\n",
            )
            result = self.run_repo(temporary_repo, "delivery")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_state_field_not_checked_at_plan(self) -> None:
        """Plan-phase tasks are legitimately 未开始 beside a pending header."""
        with self.copied_repo("valid-standard") as temporary_repo:
            self.rewrite(
                temporary_repo,
                "tasks.md",
                "### 任务 1：[completed] 实现校验器\n",
                "### 任务 1：[completed] 实现校验器\n- 状态：进行中\n",
            )
            result = self.run_repo(temporary_repo, "plan")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


class ReviewProfileAliasRegexTest(unittest.TestCase):
    """change 2035 Task 6：TASK_REVIEW_PROFILE_RE 接受两种写法。

    别名规则仅限大小写不敏感、`_` 与空格等价；取值集合与重复即报错的
    基数检查不变。
    """

    def test_underscore_writing_matches(self) -> None:
        text = "- review_profile: strict\n"
        matches = list(validate_change.TASK_REVIEW_PROFILE_RE.finditer(text))
        self.assertEqual(1, len(matches))
        self.assertEqual("strict", matches[0].group("value"))

    def test_spaced_writing_matches(self) -> None:
        text = "- Review Profile: standard\n"
        matches = list(validate_change.TASK_REVIEW_PROFILE_RE.finditer(text))
        self.assertEqual(1, len(matches))
        self.assertEqual("standard", matches[0].group("value"))

    def test_same_value_two_writings_accepted(self) -> None:
        # 归档实例：`- review_profile:` 与 `- Review Profile:` 同值并存（归档
        # 2028 / knowledge-management-review-fixes），取值相同则接受。
        text = "- review_profile: standard\n- Review Profile: standard\n"
        self.assertEqual(
            "standard", validate_change._review_profile_value(text)
        )

    def test_conflicting_writings_rejected(self) -> None:
        text = "- review_profile: standard\n- Review Profile: strict\n"
        self.assertIsNone(validate_change._review_profile_value(text))

    def test_same_writing_duplicate_still_rejected(self) -> None:
        text = "- Review Profile: standard\n- Review Profile: standard\n"
        self.assertIsNone(validate_change._review_profile_value(text))

    def test_no_fuzzy_or_prefix_match(self) -> None:
        for text in (
            "- review-profile: strict\n",
            "- review_profile_extra: strict\n",
            "- Review Profilex: strict\n",
        ):
            self.assertEqual(
                [], list(validate_change.TASK_REVIEW_PROFILE_RE.finditer(text)), text
            )


class DeliveryEvidenceTest(unittest.TestCase):
    """change 2038：OPSX057-061 交付范围与工作区残留证据。"""

    TASKS = (
        "# 实施任务清单\n\n### 任务 1：[completed] 实现\n"
        "- 依赖: 无\n- 文件: `code.py`\n"
    )

    def _git_repo(self, tasks_text: str | None = None) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        repo = Path(temp_dir.name)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".gitignore").write_text(".agentic-framework/\n", encoding="utf-8")
        change = repo / "openspec" / "changes" / "2099-evidence"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text(tasks_text or self.TASKS, encoding="utf-8")
        (repo / "code.py").write_text("print('v1')\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@example.test",
             "-c", "user.name=test", "commit", "-qm", "initial"],
            check=True,
        )
        return repo

    def _commit(self, repo: Path, message: str, paths: list[str]) -> str:
        subprocess.run(["git", "-C", str(repo), "add", "--"] + paths, check=True)
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@example.test",
             "-c", "user.name=test", "commit", "-qm", message],
            check=True,
        )
        return subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()

    def _baseline(self, repo: Path) -> Path:
        (repo / "residue.txt").write_text("keep\n", encoding="utf-8")
        snapshot = workspace_residue.capture_workspace_residue(
            repo, "HEAD", ["code.py"]
        )
        baseline = repo / ".agentic-framework" / "verify" / "baseline.json"
        baseline.parent.mkdir(parents=True)
        baseline.write_text(
            json.dumps({"workspace_residue_snapshot": snapshot}), encoding="utf-8"
        )
        return baseline

    def _deliver(self, repo: Path, extra: str | None = None) -> tuple[Path, str]:
        baseline = self._baseline(repo)
        (repo / "code.py").write_text("print('v2')\n", encoding="utf-8")
        paths = ["code.py"]
        if extra:
            (repo / extra).write_text("outside\n", encoding="utf-8")
            paths.append(extra)
        commit = self._commit(repo, "scope", paths)
        return baseline, commit

    def _run(self, repo, baseline=None, commit=None, revision=None):
        return validate_change._validate_delivery_evidence(
            repo,
            repo / "openspec" / "changes" / "2099-evidence",
            baseline,
            commit,
            revision,
        )

    def test_missing_baseline_param_fails_closed(self) -> None:
        repo = self._git_repo()
        findings = self._run(repo)
        self.assertEqual(["OPSX057"], [f.rule_id for f in findings])

    def test_missing_delivery_commit_fails_closed(self) -> None:
        repo = self._git_repo()
        baseline = self._baseline(repo)
        findings = self._run(repo, baseline)
        self.assertEqual(["OPSX057"], [f.rule_id for f in findings])

    def test_unreadable_baseline_fails_closed(self) -> None:
        repo = self._git_repo()
        findings = self._run(repo, repo / "nonexistent.json", "HEAD")
        self.assertEqual(["OPSX058"], [f.rule_id for f in findings])

    def test_no_vcs_fails_closed(self) -> None:
        source_repo = self._git_repo()
        baseline = self._baseline(source_repo)
        with tempfile.TemporaryDirectory() as temp_dir:
            plain = Path(temp_dir)
            change = plain / "openspec" / "changes" / "2099-evidence"
            change.mkdir(parents=True)
            (change / "tasks.md").write_text(self.TASKS, encoding="utf-8")
            findings = validate_change._validate_delivery_evidence(
                plain, change, baseline, "HEAD", None
            )
        self.assertEqual(["OPSX058"], [f.rule_id for f in findings])
        self.assertIn("版本控制", findings[0].message + findings[0].hint)

    def test_out_of_scope_delivery_fails_closed(self) -> None:
        repo = self._git_repo()
        baseline, commit = self._deliver(repo, extra="other.py")
        findings = self._run(repo, baseline, commit)
        self.assertEqual(["OPSX059"], [f.rule_id for f in findings])
        self.assertIn("other.py", findings[0].message)

    def test_residue_difference_fails_closed(self) -> None:
        repo = self._git_repo()
        baseline, commit = self._deliver(repo)
        (repo / "residue.txt").write_text("changed\n", encoding="utf-8")
        findings = self._run(repo, baseline, commit)
        self.assertEqual(["OPSX060"], [f.rule_id for f in findings])
        self.assertIn("residue.txt", findings[0].message)

    def test_in_scope_delivery_passes(self) -> None:
        repo = self._git_repo()
        baseline, commit = self._deliver(repo)
        self.assertEqual([], self._run(repo, baseline, commit))

    def test_cross_track_same_baseline_both_pass(self) -> None:
        """同一份基线文件，Production 与 Tooling 都能成功校验（跨轨互认）。"""
        repo = self._git_repo()
        baseline, commit = self._deliver(repo)
        production = self._run(repo, baseline, commit)
        tooling = check_delivery.check_scoped_delivery(repo, baseline, commit, None)
        self.assertEqual([], production)
        self.assertEqual([], tooling)

    def test_waiver_skips_evidence(self) -> None:
        tasks = self.TASKS.replace(
            "### 任务 1", "- 交付证据豁免: 纯文档变更，无代码交付\n\n### 任务 1"
        )
        repo = self._git_repo(tasks)
        self.assertEqual([], self._run(repo))

    def test_duplicate_waiver_fails_closed(self) -> None:
        tasks = self.TASKS.replace(
            "### 任务 1",
            "- 交付证据豁免: 甲\n- 交付证据豁免: 乙\n\n### 任务 1",
        )
        repo = self._git_repo(tasks)
        findings = self._run(repo)
        self.assertEqual(["OPSX061"], [f.rule_id for f in findings])

    def test_misplaced_waiver_fails_closed(self) -> None:
        tasks = self.TASKS.replace(
            "### 任务 1", "  - 交付证据豁免: 缩进错位\n\n### 任务 1"
        )
        repo = self._git_repo(tasks)
        findings = self._run(repo)
        self.assertEqual(["OPSX061"], [f.rule_id for f in findings])

    def test_new_check_is_read_only(self) -> None:
        import inspect

        source = inspect.getsource(validate_change._validate_delivery_evidence)
        for token in ("write_text", "mkstemp", "os.link", "os.rename", "shutil"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
