"""Real local Git/SVN fixtures for the read-only VCS boundary."""

import subprocess
from pathlib import Path

import pytest

from scripts import vcs


def command(root, *args):
    return subprocess.run(
        args, cwd=root, capture_output=True, check=True
    ).stdout


@pytest.fixture
def repository(tmp_path):
    command(tmp_path, "git", "init")
    command(tmp_path, "git", "config", "user.email", "fixture@example.invalid")
    command(tmp_path, "git", "config", "user.name", "Fixture")
    (tmp_path / "原始 file.txt").write_text("base\n", encoding="utf-8")
    command(tmp_path, "git", "add", ".")
    command(tmp_path, "git", "commit", "-m", "base")
    return tmp_path


def head(root):
    return command(root, "git", "rev-parse", "HEAD").decode().strip()


def test_root_and_worktree_identity(repository, tmp_path_factory):
    nested = repository / "nested"
    nested.mkdir()
    first = vcs.inspect_workspace(nested)
    worktree = tmp_path_factory.mktemp("linked") / "checkout"
    command(repository, "git", "worktree", "add", "-b", "linked", str(worktree))
    second = vcs.inspect_workspace(worktree)
    assert first["root"] == str(repository.resolve())
    assert first["repository_identity"] == second["repository_identity"]
    assert first["base"] == second["base"]


def test_changes_unicode_rename_and_untracked(repository):
    base = head(repository)
    command(repository, "git", "mv", "原始 file.txt", "重命名 file.txt")
    (repository / "新 file.txt").write_text("new", encoding="utf-8")
    changes = vcs.collect_changes(repository, base)
    assert {item["path"] for item in changes} == {
        "重命名 file.txt",
        "新 file.txt",
    }
    rename = next(item for item in changes if item["status"].startswith("R"))
    assert rename["old_path"] == "原始 file.txt"


def test_capture_attributes_modes_and_ignored_inputs(repository):
    (repository / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    (repository / "ignored.txt").write_text("build input", encoding="utf-8")
    (repository / ".gitattributes").write_text(
        "*.txt text eol=lf\n", encoding="utf-8"
    )
    facts = vcs.capture_subject(repository, "HEAD")
    assert "ignored.txt" in {item["path"] for item in facts["files"]}
    assert facts["properties"]["原始 file.txt"]["eol"] == "lf"
    assert facts["base"] == head(repository)
    assert "subject_id" not in facts


def test_conflicts_are_visible_and_delivery_rejected(repository):
    base = head(repository)
    command(repository, "git", "checkout", "-b", "other")
    (repository / "原始 file.txt").write_text("other\n", encoding="utf-8")
    command(repository, "git", "commit", "-am", "other")
    command(repository, "git", "checkout", "-")
    (repository / "原始 file.txt").write_text("main\n", encoding="utf-8")
    command(repository, "git", "commit", "-am", "main")
    subprocess.run(
        ["git", "merge", "other"], cwd=repository, capture_output=True
    )
    assert vcs.inspect_workspace(repository)["conflicts"] == ["原始 file.txt"]
    with pytest.raises(vcs.VcsError, match="conflicts"):
        vcs.verify_delivery(repository, "HEAD", base)


def test_delivery_exact_head_content_scope_and_identity(repository):
    base = head(repository)
    (repository / "原始 file.txt").write_text("changed\n", encoding="utf-8")
    command(repository, "git", "commit", "-am", "change")
    target = head(repository)
    result = vcs.verify_delivery(repository, target, base, ["原始 file.txt"])
    assert result["verified"] and result["commit"] == target
    with pytest.raises(vcs.VcsError, match="head_mismatch"):
        vcs.verify_delivery(repository, base, base)
    with pytest.raises(vcs.VcsError, match="scope_mismatch"):
        vcs.verify_delivery(repository, target, base, ["unrelated"])
    with pytest.raises(vcs.VcsError, match="repository_mismatch"):
        vcs.verify_delivery(
            repository,
            target,
            base,
            repository_identity={"common_dir": "wrong"},
        )
    (repository / "原始 file.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(vcs.VcsError, match="content_mismatch"):
        vcs.verify_delivery(repository, target, base)


def test_untracked_delivery_rejected(repository):
    (repository / "new.py").write_text("input", encoding="utf-8")
    with pytest.raises(vcs.VcsError, match="untracked_content"):
        vcs.verify_delivery(repository, "HEAD", "HEAD")


@pytest.mark.parametrize("value", ["missing", "--help", "", "deadbeef"])
def test_invalid_commit(repository, value):
    with pytest.raises(vcs.VcsError, match="invalid_revision"):
        vcs.capture_subject(repository, value)


def test_missing_tool_and_readonly_queries(repository, monkeypatch):
    original = subprocess.run
    calls = []

    def spy(args, **kwargs):
        calls.append(args)
        return original(args, **kwargs)

    monkeypatch.setattr(vcs.subprocess, "run", spy)
    vcs.capture_subject(repository, "HEAD")
    vcs.verify_delivery(repository, "HEAD", "HEAD")
    assert all(
        not {"update", "commit", "revert", "add", "reset"}.intersection(
            args[1:]
        )
        for args in calls
    )

    def missing(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(vcs.subprocess, "run", missing)
    with pytest.raises(vcs.VcsError, match="tool_missing"):
        vcs.collect_changes(repository, "HEAD")


def test_query_failure_and_bad_records(repository, monkeypatch):
    monkeypatch.setattr(
        vcs.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 1, b"", b"secret"
        ),
    )
    with pytest.raises(vcs.VcsError, match="query_failed") as error:
        vcs.inspect_workspace(repository)
    assert "secret" not in str(error.value)
    for value in [b"missing delimiter", b"100644 bad 0\tpath\0"]:
        if b"\0" not in value:
            with pytest.raises(vcs.VcsError, match="parse_error"):
                vcs._records(value)
        else:
            monkeypatch.setattr(vcs, "_git", lambda *args: value)
            with pytest.raises(vcs.VcsError, match="parse_error"):
                vcs._index(repository)


@pytest.fixture
def svn_workspace(tmp_path):
    repo = tmp_path / "svnrepo"
    command(tmp_path, "svnadmin", "create", str(repo))
    workspace = tmp_path / "svn wc"
    command(tmp_path, "svn", "checkout", repo.as_uri(), str(workspace))
    return workspace


def test_pure_svn_and_unsupported(svn_workspace):
    facts = vcs.inspect_workspace(svn_workspace)
    assert facts["backend"] == "svn"
    assert facts["repository_identity"]["uuid"]
    assert facts["limitations"]
    with pytest.raises(vcs.VcsError, match="unsupported"):
        vcs.capture_subject(svn_workspace, "0")
    with pytest.raises(vcs.VcsError, match="unsupported"):
        vcs.verify_delivery(svn_workspace, "0", "0")


def test_dual_backend_requires_choice(svn_workspace):
    command(svn_workspace, "git", "init")
    with pytest.raises(vcs.VcsError, match="ambiguous_backend"):
        vcs.inspect_workspace(svn_workspace)
    assert vcs.inspect_workspace(svn_workspace, "svn")["backend"] == "svn"


def test_parent_git_around_svn(repository, tmp_path):
    svnrepo = tmp_path / "server"
    command(tmp_path, "svnadmin", "create", str(svnrepo))
    wc = repository / "nested-svn"
    command(tmp_path, "svn", "checkout", svnrepo.as_uri(), str(wc))
    with pytest.raises(vcs.VcsError, match="ambiguous_backend"):
        vcs.inspect_workspace(wc)
    assert vcs.inspect_workspace(wc, "git")["root"] == str(repository.resolve())
    assert vcs.inspect_workspace(wc, "svn")["root"] == str(wc.resolve())


def test_visible_svn_missing_tool_not_ignored(svn_workspace, monkeypatch):
    monkeypatch.setattr(
        vcs.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(vcs.VcsError, match="tool_missing"):
        vcs.inspect_workspace(svn_workspace)


def test_no_backend(tmp_path):
    with pytest.raises(vcs.VcsError, match="not_working_copy"):
        vcs.inspect_workspace(tmp_path)


def test_rename_delivery_requires_both_paths(repository):
    base = head(repository)
    command(repository, "git", "mv", "原始 file.txt", "new.txt")
    command(repository, "git", "commit", "-m", "rename")
    with pytest.raises(vcs.VcsError, match="scope_mismatch"):
        vcs.verify_delivery(repository, "HEAD", base, ["new.txt"])
    assert vcs.verify_delivery(
        repository, "HEAD", base, ["new.txt", "原始 file.txt"]
    )["verified"]


def test_delivery_index_and_worktree_content(repository):
    base = head(repository)
    (repository / "原始 file.txt").write_text("staged\n", encoding="utf-8")
    command(repository, "git", "add", ".")
    with pytest.raises(vcs.VcsError, match="content_mismatch"):
        vcs.verify_delivery(repository, "HEAD", base)


def test_nonancestor_base_rejected(repository):
    base = head(repository)
    command(repository, "git", "checkout", "-b", "future")
    (repository / "extra").write_text("extra", encoding="utf-8")
    command(repository, "git", "add", ".")
    command(repository, "git", "commit", "-m", "future")
    future = head(repository)
    command(repository, "git", "checkout", base)
    with pytest.raises(vcs.VcsError, match="base_not_ancestor"):
        vcs.verify_delivery(repository, base, future)


def test_git_environment_does_not_redirect(repository, monkeypatch):
    expected = head(repository)
    monkeypatch.setenv("GIT_DIR", "missing-directory")
    assert vcs.inspect_workspace(repository)["head"] == expected


def test_query_timeout_is_classified(repository, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 30)

    monkeypatch.setattr(vcs.subprocess, "run", timeout)
    with pytest.raises(vcs.VcsError, match="query_timeout"):
        vcs.inspect_workspace(repository)


@pytest.mark.parametrize(
    "scope", [[], ["."], ["../other"], ["bad\0path"], ["--help"]]
)
def test_invalid_scope_rejected(repository, scope):
    with pytest.raises(vcs.VcsError, match="invalid_scope"):
        vcs.verify_delivery(repository, "HEAD", "HEAD", scope)
