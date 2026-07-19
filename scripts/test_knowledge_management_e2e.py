"""Exercise the unified project and shared knowledge contracts end to end."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
WORKFLOW_SCRIPTS_DIR = REPO_ROOT / "skills" / "workflow-code-generation" / "scripts"
FIXTURE_ROOT = SCRIPTS_DIR / "tests" / "fixtures" / "validate-change" / "valid-standard"
CHANGE = Path("openspec/changes/example-change")

for import_path in (SCRIPTS_DIR, WORKFLOW_SCRIPTS_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

import validate_change  # noqa: E402
import validate_shared_knowledge  # noqa: E402


def _load_workflow_control() -> ModuleType:
    module_path = WORKFLOW_SCRIPTS_DIR / "workflow_control.py"
    spec = importlib.util.spec_from_file_location("e2e_workflow_control", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载工作流控制器：{module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WORKFLOW_CONTROL = _load_workflow_control()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _valid_public_entry() -> str:
    return """---
status: verified
source: official-documentation-and-two-independent-cases
source_version: 2026-07-19
applies_to: Python CLI tools using UTF-8 JSON request bodies
excludes: binary protocols and non-JSON transports
---

# UTF-8 JSON 请求体

## 结论

将非 ASCII JSON 请求体保存为 UTF-8 文件后再传给命令行工具。
"""


class KnowledgeManagementE2ETest(unittest.TestCase):
    """Validate shared project and public knowledge contracts in disposable roots."""

    def test_shared_standard_change_archive_gate_and_delta_sync(self) -> None:
        """A shared Standard Change passes its archive gate and syncs its Delta."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "standard-change-project"
            shutil.copytree(FIXTURE_ROOT, repo)
            change = repo / CHANGE
            tasks_path = change / "tasks.md"
            tasks_path.write_text(
                tasks_path.read_text(encoding="utf-8").replace(
                    "Code Review：Pending", "Code Review：PASS"
                ),
                encoding="utf-8",
            )
            target = (
                repo
                / "openspec"
                / "changes"
                / "archive"
                / f"{date.today().isoformat()}-example-change"
            )

            result = validate_change.validate_change(repo, change, "archive", target)
            self.assertTrue(result.ok, result.to_dict())

            delta = change / "specs" / "business" / "validator" / "spec.md"
            delta_content = delta.read_text(encoding="utf-8")
            long_term = (
                repo / "openspec" / "specs" / "business" / "validator" / "spec.md"
            )
            _write(long_term, delta_content)
            target.parent.mkdir(parents=True, exist_ok=True)
            change.rename(target)

            self.assertEqual(
                delta_content,
                long_term.read_text(encoding="utf-8"),
            )
            self.assertFalse(change.exists())
            self.assertTrue((target / "tasks.md").is_file())

    def test_tooling_standard_uses_unified_artifact_and_controller(self) -> None:
        """Tooling state transitions operate on openspec/changes/tasks.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = (
                Path(temp_dir)
                / "tooling-project"
                / "openspec"
                / "changes"
                / "add-knowledge-route"
                / "tasks.md"
            )
            _write(
                tasks_path,
                """# 实施任务清单

### 任务 1：实现统一知识路由

- 状态：进行中
- attempts：0
- control_stage：running
- depends_on：[]
""",
            )

            verify_report_path = tasks_path.parent / "verify-report.json"
            _write(verify_report_path, json.dumps({"verdict": "PASS"}))
            self.assertEqual(
                0,
                WORKFLOW_CONTROL.main(
                    [
                        str(tasks_path),
                        "event",
                        "1",
                        "quality_passed",
                        "--verify-report",
                        str(verify_report_path),
                        "--write",
                    ]
                ),
            )
            self.assertEqual(
                0,
                WORKFLOW_CONTROL.main(
                    [str(tasks_path), "event", "1", "merge_success", "--write"]
                ),
            )
            persisted = tasks_path.read_text(encoding="utf-8")
            self.assertIn("- 状态：完成", persisted)
            self.assertIn("- control_stage：completed", persisted)

    def test_external_private_link_is_transparent_and_breakage_is_detectable(
        self,
    ) -> None:
        """An external openspec link reads normally and fails closed when broken."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            private_store = root / "private" / "project-a" / "openspec"
            _write(private_store / "index.md", "# 项目知识索引\n")
            project.mkdir()
            link = project / "openspec"
            try:
                link.symlink_to(private_store, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"当前环境无目录符号链接权限：{error}")

            self.assertEqual(
                "# 项目知识索引\n",
                (project / "openspec" / "index.md").read_text(encoding="utf-8"),
            )
            private_store.rename(private_store.with_name("openspec-moved"))
            self.assertTrue(os.path.lexists(link))
            self.assertFalse((project / "openspec" / "index.md").is_file())

    def test_unresolved_knowledge_code_conflict_blocks_archive(self) -> None:
        """The archive gate rejects evidence that has no resolved conclusion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "conflict-project"
            shutil.copytree(FIXTURE_ROOT, repo)
            tasks_path = repo / CHANGE / "tasks.md"
            tasks = tasks_path.read_text(encoding="utf-8")
            tasks = tasks.replace(
                "- 结论：无冲突。",
                """- 知识文件：`openspec/specs/business/validator/spec.md`
- 知识结论：退出码始终为 0。
- 代码证据：`scripts/validate_change.py:1211`
- 当前实现：校验失败返回非零退出码。
- 状态：待确认。""",
            )
            tasks_path.write_text(tasks, encoding="utf-8")
            target = (
                repo
                / "openspec"
                / "changes"
                / "archive"
                / f"{date.today().isoformat()}-example-change"
            )

            result = validate_change.validate_change(
                repo, repo / CHANGE, "archive", target
            )
            self.assertFalse(result.ok)
            self.assertIn("OPSX047", {finding.rule_id for finding in result.findings})

    def test_public_validator_rejects_private_links_and_candidates(self) -> None:
        """Public indexes and governance changes cannot expose project knowledge."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "shared"
            _write(
                root / "index.md", "# 公共知识库\n\n- [项目 A](projects/a/index.md)\n"
            )
            _write(root / "domains" / "index.md", "# 领域索引\n")
            _write(root / "projects" / "a" / "index.md", "# 私有项目正文\n")
            _write(
                root / "changes" / "candidate.md",
                """---
scope: project
kind: promotion-candidate
---

# 跨项目知识晋升候选
""",
            )

            problems = validate_shared_knowledge.validate(root)
            self.assertTrue(any("projects/" in problem for problem in problems))
            self.assertTrue(any("项目知识候选" in problem for problem in problems))

    def test_public_index_cannot_bridge_two_projects_private_content(self) -> None:
        """Public indexes exclude both projects and reject bridge links."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shared = root / "shared"
            project_a = root / "project-a"
            project_b = root / "project-b"
            _write(project_a / "openspec" / "index.md", "# A\n\nprivate-token-a\n")
            _write(project_b / "openspec" / "index.md", "# B\n\nprivate-token-b\n")
            _write(
                shared / "index.md", "# 公共知识库\n\n- [工具知识](domains/tooling/)\n"
            )
            _write(shared / "domains" / "index.md", "# 领域索引\n")
            _write(
                shared / "domains" / "tooling" / "utf8-json.md",
                _valid_public_entry(),
            )
            (shared / "issues").mkdir(parents=True)
            (shared / "changes").mkdir()

            public_text = "\n".join(
                path.read_text(encoding="utf-8") for path in shared.rglob("*.md")
            )
            self.assertNotIn("private-token-a", public_text)
            self.assertNotIn("private-token-b", public_text)
            self.assertEqual([], validate_shared_knowledge.validate(shared))

            _write(
                shared / "index.md",
                "# 公共知识库\n\n"
                "- [项目 A](../project-a/openspec/index.md)\n"
                "- [项目 B](../project-b/openspec/index.md)\n",
            )
            self.assertEqual(
                [
                    "index.md:3：公共索引链接越出公共库 -> "
                    "../project-a/openspec/index.md",
                    "index.md:4：公共索引链接越出公共库 -> "
                    "../project-b/openspec/index.md",
                ],
                validate_shared_knowledge.validate(shared),
            )

    def test_confirmed_generalised_public_entry_passes_validator(self) -> None:
        """A reviewed, generalised public entry satisfies the public contract."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "shared"
            _write(
                root / "index.md", "# 公共知识库\n\n- [工具知识](domains/tooling/)\n"
            )
            _write(root / "domains" / "index.md", "# 领域索引\n")
            _write(root / "domains" / "tooling" / "utf8-json.md", _valid_public_entry())
            (root / "issues").mkdir(parents=True)
            (root / "changes").mkdir()

            self.assertEqual([], validate_shared_knowledge.validate(root))


if __name__ == "__main__":
    unittest.main()
