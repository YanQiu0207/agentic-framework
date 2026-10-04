"""Real repository coverage, content changes and fixed-base stability tests."""

import copy
import os
from pathlib import Path

import pytest

from scripts import native_subject, vcs
from scripts.test_vcs import command, head, repository


def capture(root, base=None, **kwargs):
    return native_subject.capture_subject(root, base or head(root), **kwargs)


def write(root, name, text):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def test_actual_content_and_config_changes(repository):
    base = head(repository)
    initial = capture(repository, base)
    assert initial["complete"]
    assert initial["subject_id"].startswith("sha256:")
    write(repository, "source.py", "print(1)")
    source = capture(repository, base)
    assert source["subject_id"] != initial["subject_id"]
    write(repository, "verify.config.json", '{"checks":[]}')
    config = capture(repository, base)
    assert config["subject_id"] != source["subject_id"]
    write(repository, "verify.config.json", '{"checks":[{"command":"test"}]}')
    assert capture(repository, base)["subject_id"] != config["subject_id"]


def test_ignored_untracked_build_inputs_included(repository):
    write(repository, ".gitignore", "inputs/\n")
    base = head(repository)
    before = capture(repository, base)
    write(repository, "inputs/config.txt", "one")
    after = capture(repository, base)
    assert "inputs/config.txt" in {entry["path"] for entry in after["entries"]}
    assert before["subject_id"] != after["subject_id"]
    write(repository, "inputs/config.txt", "two")
    assert capture(repository, base)["subject_id"] != after["subject_id"]


def test_staging_committing_and_deleting_under_fixed_base(repository):
    base = head(repository)
    write(repository, "新 source.py", "code")
    before = capture(repository, base)
    command(repository, "git", "add", ".")
    assert capture(repository, base)["subject_id"] == before["subject_id"]
    command(repository, "git", "commit", "-m", "new")
    assert capture(repository, base)["subject_id"] == before["subject_id"]
    command(repository, "git", "rm", "原始 file.txt")
    deleted = capture(repository, base)
    assert (
        next(
            entry
            for entry in deleted["entries"]
            if entry["path"] == "原始 file.txt"
        )["type"]
        == "missing"
    )
    command(repository, "git", "commit", "-m", "delete")
    assert capture(repository, base)["subject_id"] == deleted["subject_id"]


def test_unstaged_deleted_tombstone_stable(repository):
    base = head(repository)
    (repository / "原始 file.txt").unlink()
    before = capture(repository, base)
    command(repository, "git", "add", "-u")
    assert capture(repository, base)["subject_id"] == before["subject_id"]
    command(repository, "git", "commit", "-m", "delete")
    assert capture(repository, base)["subject_id"] == before["subject_id"]


def test_rename_changes_identity(repository):
    base = head(repository)
    before = capture(repository, base)
    command(repository, "git", "mv", "原始 file.txt", "renamed.txt")
    assert capture(repository, base)["subject_id"] != before["subject_id"]


def test_attributes_change_identity_and_commit_stability(repository):
    base = head(repository)
    before = capture(repository, base)
    write(repository, ".gitattributes", "*.txt eol=lf\n")
    after = capture(repository, base)
    assert before["subject_id"] != after["subject_id"]
    assert (
        next(
            entry
            for entry in after["entries"]
            if entry["path"] == "原始 file.txt"
        )["properties"]["eol"]
        == "lf"
    )
    command(repository, "git", "add", ".")
    command(repository, "git", "commit", "-m", "attributes")
    assert capture(repository, base)["subject_id"] == after["subject_id"]


def test_executable_mode_changes_identity(repository):
    base = head(repository)
    before = capture(repository, base)
    if os.name == "nt":
        command(
            repository, "git", "update-index", "--chmod=+x", "原始 file.txt"
        )
    else:
        (repository / "原始 file.txt").chmod(0o755)
    assert before["subject_id"] != capture(repository, base)["subject_id"]


def test_generated_reports_and_caches_no_self_reference(repository):
    base = head(repository)
    before = capture(repository, base)
    for name in [
        ".agentic-framework/verify/report.json",
        ".agentic-framework/review/report.json",
        ".agentic-framework/native-delivery/verdict.json",
        ".agentic-framework/tools/venv/generated.py",
        "nested/__pycache__/code.pyc",
        ".pytest_cache/state",
    ]:
        write(repository, name, "generated")
    after = capture(repository, base)
    assert before["subject_id"] == after["subject_id"]
    assert after["complete"]


def test_manifest_and_governance_config_included(repository):
    base = head(repository)
    before = capture(repository, base)
    write(
        repository, ".agentic-framework/manifest.json", '{"profile":"tooling"}'
    )
    write(
        repository,
        ".agentic-framework/extensions/standards.json",
        '{"files":["*.py"]}',
    )
    after = capture(repository, base)
    assert before["subject_id"] != after["subject_id"]
    assert ".agentic-framework/manifest.json" in {
        entry["path"] for entry in after["entries"]
    }


def test_tracked_build_input_overrides_generated_exclusion(repository):
    base = head(repository)
    target = write(repository, ".agentic-framework/tools/input.py", "build")
    command(repository, "git", "add", "-f", str(target))
    before = capture(repository, base)
    assert target.relative_to(repository).as_posix() in {
        entry["path"] for entry in before["entries"]
    }
    target.write_text("changed", encoding="utf-8")
    assert before["subject_id"] != capture(repository, base)["subject_id"]


def test_explicit_generated_input_overrides_exclusion_and_attributes(
    repository,
):
    base = head(repository)
    target = write(repository, ".agentic-framework/tools/input.txt", "one")
    write(repository, ".gitattributes", "*.txt eol=lf\n")
    required = [target.relative_to(repository).as_posix()]
    before = capture(repository, base, required_inputs=required)
    entry = next(
        entry for entry in before["entries"] if entry["path"] == required[0]
    )
    assert entry["properties"]["eol"] == "lf"
    assert before["coverage_policy"]["required_inputs"] == required
    target.write_text("two", encoding="utf-8")
    assert (
        capture(repository, base, required_inputs=required)["subject_id"]
        != before["subject_id"]
    )


def test_explicit_report_input_fails_closed(repository):
    write(repository, ".agentic-framework/verify/report.json", "{}")
    result = capture(
        repository, required_inputs=[".agentic-framework/verify/report.json"]
    )
    assert not result["complete"]
    with pytest.raises(
        native_subject.SubjectError, match="coverage_incomplete"
    ):
        native_subject.compute_subject_id(
            repository,
            head(repository),
            required_inputs=[".agentic-framework/verify/report.json"],
        )


def test_tracked_report_input_is_not_silently_complete(repository):
    target = write(repository, ".agentic-framework/verify/report.json", "{}")
    command(repository, "git", "add", "-f", str(target))
    assert not capture(repository)["complete"]


def test_explicit_input_tree_and_missing_inputs(repository):
    write(repository, ".agentic-framework/tools/data/one", "one")
    write(repository, ".agentic-framework/tools/data/two", "two")
    result = capture(
        repository, required_inputs=[".agentic-framework/tools/data"]
    )
    assert result["complete"]
    assert ".agentic-framework/tools/data/two" in {
        entry["path"] for entry in result["entries"]
    }
    assert not capture(repository, required_inputs=["missing.py"])["complete"]


def test_external_inputs_and_external_verify_config_reject(
    repository, tmp_path
):
    result = capture(repository, external_inputs=["outside dependency"])
    assert not result["complete"]
    outside = repository.parent / "outside-verify.json"
    assert not capture(repository, config_path=outside)["complete"]
    assert not capture(
        repository, config_path=repository / "missing-config.json"
    )["complete"]


def test_before_after_mismatch_and_base_mismatch(repository):
    base = head(repository)
    before = capture(repository, base)
    write(repository, "code.py", "new")
    after = capture(repository, base)
    assert not native_subject.compare_subjects(before, after)["verified"]
    with pytest.raises(native_subject.SubjectError, match="subject_changed"):
        native_subject.require_same_subject(before, after)
    command(repository, "git", "add", ".")
    command(repository, "git", "commit", "-m", "new")
    assert (
        capture(repository, head(repository))["subject_id"]
        != after["subject_id"]
    )


def test_worktree_identity_and_sorting_repeatable(repository, tmp_path_factory):
    base = head(repository)
    before = capture(repository, base)
    worktree = tmp_path_factory.mktemp("subject-linked") / "copy"
    command(
        repository,
        "git",
        "worktree",
        "add",
        "-b",
        "subject-linked",
        str(worktree),
    )
    after = capture(worktree, base)
    assert before["subject_id"] == after["subject_id"]
    native_subject.require_same_subject(before, after)


def test_tasks_metadata_only_normalized(repository):
    base = head(repository)
    name = "openspec/changes/1-example/tasks.md"
    text = "### 任务 1：[ ] implement\n- 状态：未开始\n- attempts：0\n- control_stage：pending\n- verification:\n  - [ ] run test\n- 说明：real requirement\n```text\n- 状态：sample\n```\n"
    write(repository, name, text)
    before = capture(repository, base)
    write(
        repository,
        name,
        text.replace("[ ]", "[x]")
        .replace("未开始", "完成")
        .replace("attempts：0", "attempts：2")
        .replace("pending", "completed"),
    )
    assert capture(repository, base)["subject_id"] == before["subject_id"]
    write(repository, name, text.replace("real requirement", "new requirement"))
    assert capture(repository, base)["subject_id"] != before["subject_id"]
    write(repository, name, text.replace("状态：sample", "状态：changed"))
    assert capture(repository, base)["subject_id"] != before["subject_id"]


def test_tasks_optional_metadata_insertion_stable(repository):
    base = head(repository)
    name = "openspec/changes/1-example/tasks.md"
    text = "### 任务 1：implement\n- 状态：未开始\n- 说明：requirement\n"
    write(repository, name, text)
    before = capture(repository, base)
    write(
        repository,
        name,
        text.replace("任务 1：", "任务 1：[ ]").replace(
            "- 说明", "- attempts：0\n- control_stage：pending\n- 说明"
        ),
    )
    assert capture(repository, base)["subject_id"] == before["subject_id"]


def test_tasks_prose_and_other_tasks_not_normalized(repository):
    base = head(repository)
    name = "tasks.md"
    text = "### 任务 1：[ ] item\n- 状态：未开始\n"
    write(repository, name, text)
    before = capture(repository, base)
    write(repository, name, text.replace("未开始", "完成"))
    assert capture(repository, base)["subject_id"] != before["subject_id"]


def test_archive_path_changes_subject(repository):
    base = head(repository)
    source = write(
        repository,
        "openspec/changes/1-task/tasks.md",
        "### 任务 1：[ ] work\n- 状态：未开始\n",
    )
    before = capture(repository, base)
    target = repository / "openspec/changes/archive/1-task/tasks.md"
    target.parent.mkdir(parents=True)
    source.rename(target)
    assert before["subject_id"] != capture(repository, base)["subject_id"]


def test_content_type_changes(repository):
    base = head(repository)
    target = write(repository, "input", "file")
    before = capture(repository, base, required_inputs=["input"])
    target.unlink()
    target.mkdir()
    after = capture(repository, base, required_inputs=["input"])
    assert before["subject_id"] != after["subject_id"]


def test_symlink_content_and_external_limitations(repository):
    base = head(repository)
    target = write(repository, "target.txt", "target")
    link = repository / "link.txt"
    try:
        link.symlink_to(target.name)
    except OSError as error:
        pytest.fail("Symlink fixture unavailable: " + type(error).__name__)
    before = capture(repository, base)
    assert before["complete"]
    link.unlink()
    link.symlink_to("missing.txt")
    missing = capture(repository, base)
    assert not missing["complete"]
    assert before["subject_id"] != missing["subject_id"]
    link.unlink()
    external = write(repository.parent, "external.txt", "outside")
    link.symlink_to(external)
    outside = capture(repository, base)
    assert not outside["complete"]
    assert any(
        item.startswith("external_symlink:") for item in outside["limitations"]
    )
    # A missing external target must stay external: Windows resolves a link
    # to a nonexistent final target back to the link itself.
    external.unlink()
    dangling = capture(repository, base)
    assert not dangling["complete"]
    assert any(
        item.startswith("external_symlink:") for item in dangling["limitations"]
    )


def test_invalid_capture_cannot_compare_as_pass(repository):
    original = capture(repository)
    forged = copy.deepcopy(original)
    forged["entries"] = []
    with pytest.raises(
        native_subject.SubjectError, match="invalid_subject_capture"
    ):
        native_subject.compare_subjects(forged, original)


def test_capture_read_errors_are_not_empty_success(repository, monkeypatch):
    original = Path.read_bytes

    def failed(path):
        if path.name == "原始 file.txt":
            raise PermissionError
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", failed)
    with pytest.raises(native_subject.SubjectError, match="input_read_failed"):
        capture(repository)


def test_capture_time_change_fails(repository, monkeypatch):
    original = Path.read_bytes

    def changing(path):
        content = original(path)
        if path.name == "原始 file.txt":
            path.write_bytes(content + b"changed")
        return content

    monkeypatch.setattr(Path, "read_bytes", changing)
    with pytest.raises(
        native_subject.SubjectError, match="inputs_changed_during_capture"
    ):
        capture(repository)


def test_added_after_base_then_removed_has_no_spurious_tombstone(repository):
    base = head(repository)
    write(repository, "new-input.py", "new")
    command(repository, "git", "add", ".")
    command(repository, "git", "commit", "-m", "new")
    (repository / "new-input.py").unlink()
    before = capture(repository, base)
    command(repository, "git", "add", "-u")
    assert capture(repository, base)["subject_id"] == before["subject_id"]
    command(repository, "git", "commit", "-m", "delete new")
    assert capture(repository, base)["subject_id"] == before["subject_id"]


def test_tasks_metadata_does_not_erase_invalid_fields_or_fenced_examples():
    text = (
        b"### "
        + "任务 1：[ ] item\n".encode("utf-8")
        + b"- attempts: not-a-count\n- control_stage: requirement\n````text\n- attempts: 1\n```\n- attempts: 2\n````\n"
    )
    normalized = native_subject._task_bytes(text)
    assert b"not-a-count" in normalized
    assert b"control_stage: requirement" in normalized
    assert b"- attempts: 1" in normalized and b"- attempts: 2" in normalized


def test_nested_repository_inputs_are_not_claimed_complete(repository):
    nested = repository / "nested-repository"
    nested.mkdir()
    command(nested, "git", "init")
    write(nested, "source.py", "outside nested repo input")
    result = capture(repository)
    assert not result["complete"]
    assert any(
        item.startswith("unexpanded_directory_inputs:")
        for item in result["limitations"]
    )
