"""Real local Git/SVN fixtures for the read-only VCS boundary."""

import subprocess

import pytest

from scripts import vcs


def command(root, *args):
    if args[0] == "svn":
        args = (*args, "--non-interactive")
        if args[1] == "commit":
            args = (*args, "--force-log")
    return subprocess.run(
        args, cwd=root, capture_output=True, check=True, timeout=30
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


def test_pure_svn_empty_repository(svn_workspace):
    facts = vcs.inspect_workspace(svn_workspace)
    assert facts["backend"] == "svn"
    assert facts["repository_identity"]["uuid"]
    assert facts["limitations"] == []
    capture = vcs.capture_subject(svn_workspace, "0")
    assert capture["base"] == "svn:r0"
    assert capture["base_files"][0]["path"] == "."


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


def test_subject_base_files_and_query_time_exclusions(repository, monkeypatch):
    base = head(repository)
    target = repository / ".agentic-framework/tools/input.py"
    target.parent.mkdir(parents=True)
    target.write_text("tracked input", encoding="utf-8")
    command(repository, "git", "add", "-f", str(target))
    command(repository, "git", "commit", "-m", "tracked tool")
    (target.parent / "ignored.py").write_text("generated", encoding="utf-8")
    calls = []
    original = vcs._run

    def spy(root, args, data=None):
        calls.append(args)
        return original(root, args, data)

    monkeypatch.setattr(vcs, "_run", spy)
    facts = vcs.capture_subject(
        repository,
        base,
        excluded_prefixes=[".agentic-framework/tools"],
        excluded_directory_names=["__pycache__"],
    )
    assert "原始 file.txt" in {item["path"] for item in facts["base_files"]}
    assert ".agentic-framework/tools/input.py" in {
        item["path"] for item in facts["files"]
    }
    assert ".agentic-framework/tools/ignored.py" not in {
        item["path"] for item in facts["files"]
    }
    query = next(args for args in calls if "--others" in args)
    assert ":(glob,exclude).agentic-framework/tools/**" in query
    assert "--exclude-standard" not in query


@pytest.mark.parametrize(
    "prefix", ["../outside", "wild*", "magic[x]", "/absolute"]
)
def test_subject_exclusion_rejects_nonliteral_paths(repository, prefix):
    with pytest.raises(vcs.VcsError, match="invalid_scope"):
        vcs.capture_subject(repository, "HEAD", excluded_prefixes=[prefix])


@pytest.fixture
def svn_pair(tmp_path):
    repo = tmp_path / "server"
    command(tmp_path, "svnadmin", "create", str(repo))
    first, second = tmp_path / "first wc", tmp_path / "second wc"
    command(tmp_path, "svn", "checkout", repo.as_uri(), str(first))
    (first / "source.txt").write_text("base\n", encoding="utf-8")
    (first / "empty").mkdir()
    (first / "binary.dat").write_bytes(b"\x00\xff\r\n")
    command(first, "svn", "add", "source.txt", "empty", "binary.dat")
    command(
        first,
        "svn",
        "propset",
        "svn:mime-type",
        "application/octet-stream",
        "binary.dat",
    )
    command(first, "svn", "commit", "-m", "base")
    command(first, "svn", "update")
    command(tmp_path, "svn", "checkout", repo.as_uri(), str(second))
    return first, second, repo


def test_svn_nodes_changes_properties_and_move(svn_pair):
    first, _, _ = svn_pair
    facts = vcs.inspect_workspace(first)
    assert facts["base"] == "svn:r1" and not facts["limitations"]
    assert all(item["revision"] == 1 for item in facts["nodes"])
    command(first, "svn", "propset", "project:flag", "yes", "empty")
    command(first, "svn", "move", "source.txt", "new.txt")
    (first / "untracked.py").write_text("input", encoding="utf-8")
    changes = vcs.collect_changes(first, "svn:r1")
    assert any(
        item["path"] == "empty" and item["property_changes"] for item in changes
    )
    assert any(
        item["path"] == "new.txt" and item["old_path"] == "source.txt"
        for item in changes
    )
    assert any(
        item["path"] == "untracked.py" and item["status"] == "?"
        for item in changes
    )
    capture = vcs.capture_subject(first, "1")
    assert any(
        item["path"] == "empty" and item["kind"] == "dir"
        for item in capture["base_files"]
    )


def test_svn_mixed_revision_and_upstream_update(svn_pair):
    first, second, _ = svn_pair
    (second / "source.txt").write_text("upstream\n", encoding="utf-8")
    command(second, "svn", "commit", "-m", "upstream")
    assert vcs.inspect_workspace(second)["mixed_revisions"]
    assert not vcs.collect_changes(first, "1")
    command(first, "svn", "update")
    assert vcs.inspect_workspace(first)["base"] == "svn:r2"
    assert any(
        item["path"] == "source.txt" for item in vcs.collect_changes(first, "1")
    )
    assert (
        "svn_node_base_mismatch"
        in vcs.capture_subject(first, "1")["limitations"]
    )


def test_svn_stat_forgery_cannot_bypass_revision_verification(svn_pair):
    """伪造 mtime+size 不能绕过确切 revision 内容核验（终审复审实测的捷径）。"""
    import os as _os

    first, _, _ = svn_pair
    assert vcs.verify_delivery(first, "1", "0")["verified"]
    target = first / "source.txt"
    stat_before = target.stat()
    forged = b"forged-but-same-length-content"
    target.write_bytes(forged[: stat_before.st_size].ljust(stat_before.st_size, b"x"))
    _os.utime(target, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns))
    # SVN 的 diff/status 捷径可能认为文件未变；真实字节核验必须拒绝。
    with pytest.raises(vcs.VcsError, match="content_mismatch"):
        vcs.verify_delivery(first, "1", "0")


def test_svn_conflicts_and_readonly_queries(svn_pair, monkeypatch):
    first, second, _ = svn_pair
    (second / "source.txt").write_text("remote\n", encoding="utf-8")
    command(second, "svn", "commit", "-m", "remote")
    (first / "source.txt").write_text("local\n", encoding="utf-8")
    command(first, "svn", "update")
    calls = []
    original = vcs._run

    def spy(root, args, data=None):
        calls.append(args)
        return original(root, args, data)

    monkeypatch.setattr(vcs, "_run", spy)
    assert vcs.inspect_workspace(first)["conflicts"] == ["source.txt"]
    vcs.capture_subject(first, "2")
    assert all(
        not {"update", "commit", "revert", "checkout", "export"}.intersection(
            args[1:]
        )
        for args in calls
    )
    with pytest.raises(vcs.VcsError, match="conflicts"):
        vcs.verify_delivery(first, "2", "1")


def test_svn_sparse_switched_and_externals(svn_pair, tmp_path):
    first, _, repo = svn_pair
    sparse = tmp_path / "sparse"
    command(
        tmp_path,
        "svn",
        "checkout",
        "--depth",
        "empty",
        repo.as_uri(),
        str(sparse),
    )
    assert vcs.inspect_workspace(sparse)["sparse"]
    command(first, "svn", "copy", "empty", "other")
    command(first, "svn", "commit", "-m", "other")
    command(first, "svn", "update")
    command(
        first,
        "svn",
        "switch",
        "--ignore-ancestry",
        repo.as_uri() + "/other",
        "empty",
    )
    assert vcs.inspect_workspace(first)["switched"]
    command(first, "svn", "propset", "svn:externals", "^/other external", ".")
    assert vcs.inspect_workspace(first)["externals"]


def test_svn_revision_delivery_actual_bytes_identity_and_scope(svn_pair):
    first, _, _ = svn_pair
    identity = vcs.inspect_workspace(first)["repository_identity"]
    result = vcs.verify_delivery(first, "1", "0", repository_identity=identity)
    assert result["verified"] and result["revision"] == 1
    with pytest.raises(vcs.VcsError, match="repository_mismatch"):
        vcs.verify_delivery(
            first,
            "1",
            "0",
            repository_identity={"uuid": "wrong", "relative_url": "^/"},
        )
    with pytest.raises(vcs.VcsError, match="scope_mismatch"):
        vcs.verify_delivery(first, "1", "0", scope=["source.txt"])
    (first / "source.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(vcs.VcsError, match="content_mismatch"):
        vcs.verify_delivery(first, "1", "0")


def test_svn_invalid_revision_network_and_xml_fail_closed(
    svn_pair, monkeypatch
):
    first, _, _ = svn_pair
    for revision in ("HEAD", "-1", "bad"):
        with pytest.raises(vcs.VcsError, match="invalid_revision"):
            vcs.capture_subject(first, revision)
    with pytest.raises(vcs.VcsError, match="invalid_revision"):
        vcs.capture_subject(first, "999")
    monkeypatch.setattr(vcs, "_run", lambda *args, **kwargs: b"broken XML")
    with pytest.raises(vcs.VcsError, match="parse_error"):
        vcs.inspect_workspace(first)


def test_svn_network_error_is_structured_without_credentials(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        vcs.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 1, b"", b"svn: E170013 credential-secret"
        ),
    )
    with pytest.raises(vcs.VcsError, match="network_error") as error:
        vcs._run(tmp_path, ["svn", "info", "https://unavailable.invalid/path"])
    assert "credential-secret" not in str(error.value)


def test_svn_unicode_at_path_and_repository_unavailable(svn_pair):
    first, _, repo = svn_pair
    name = "\u7a7a \u683c@.txt"
    (first / name).write_text("unicode input", encoding="utf-8")
    command(first, "svn", "add", ".", "--force")
    command(first, "svn", "commit", "-m", "unicode")
    command(first, "svn", "update")
    assert vcs.verify_delivery(first, "2", "1")["verified"]
    repo.rename(repo.with_name("unavailable"))
    with pytest.raises(vcs.VcsError, match="network_error"):
        vcs.capture_subject(first, "2")
