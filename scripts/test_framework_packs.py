"""Regression tests for fail-closed optional capability lookup."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import framework_packs as packs


def write_manifest(root: Path, **overrides) -> Path:
    """Write a structurally valid installation without executable assets."""
    manifest = {
        "schema_version": 3,
        "framework_version": "test",
        "pack_selection_version": 1,
        "source": str(root / "untrusted-source"),
        "profile": "tooling",
        "packs": [],
        "links": [],
        "extensions": [],
    }
    manifest.update(overrides)
    path = root / packs.MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_core_and_explicit_capabilities(tmp_path: Path) -> None:
    write_manifest(tmp_path)
    assert packs.enabled_packs(tmp_path) == set()
    with pytest.raises(packs.FrameworkPackError, match="--with runtime"):
        packs.require_pack(tmp_path, "runtime")
    write_manifest(tmp_path, packs=["runtime"])
    packs.require_pack(tmp_path, "runtime")
    assert packs.enabled_packs(tmp_path) == {"runtime"}


def test_legacy_selection_preserves_implicit_capabilities(
    tmp_path: Path,
) -> None:
    path = write_manifest(tmp_path, packs=["frontend"])
    value = json.loads(path.read_text(encoding="utf-8"))
    del value["pack_selection_version"]
    path.write_text(json.dumps(value), encoding="utf-8")
    assert packs.enabled_packs(tmp_path) == {
        "frontend",
        "runtime",
        "knowledge-advanced",
    }
    assert packs.pack_status(tmp_path)["source"] == "legacy-manifest"


@pytest.mark.parametrize("value", [None, [], {}, "bad", {"packs": []}])
def test_invalid_manifest_fails_closed(tmp_path: Path, value: object) -> None:
    path = write_manifest(tmp_path)
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(packs.FrameworkPackError):
        packs.enabled_packs(tmp_path)


@pytest.mark.parametrize(
    "overrides",
    [
        {"pack_selection_version": None},
        {"pack_selection_version": True},
        {"pack_selection_version": 2},
        {"packs": ["unknown"]},
        {"packs": ["runtime", "runtime"]},
        {"packs": [{}]},
        {"schema_version": 99},
        {"profile": "invalid"},
        {"links": [{"path": "README.md", "source": "x", "type": "file"}]},
    ],
)
def test_invalid_selection_or_installation(
    tmp_path: Path, overrides: dict
) -> None:
    write_manifest(tmp_path, **overrides)
    with pytest.raises(packs.FrameworkPackError):
        packs.enabled_packs(tmp_path)


def test_ancestor_selection_and_nearest_invalid_manifest(
    tmp_path: Path,
) -> None:
    write_manifest(tmp_path, packs=["runtime"])
    child = tmp_path / "child"
    child.mkdir()
    assert packs.enabled_packs(child) == {"runtime"}
    path = write_manifest(child)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(packs.FrameworkPackError):
        packs.enabled_packs(child)


def test_only_executing_source_tree_has_implicit_capabilities(
    tmp_path: Path, monkeypatch
) -> None:
    for marker in (
        "scripts/install_agentic_framework.py",
        "skills/workflow-code-generation/SKILL.md",
        "harness/capabilities/codex.json",
    ):
        path = tmp_path / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fake", encoding="utf-8")
    # The real user home may itself contain an installation. Isolate this
    # missing-installation case from that legitimate ancestor inheritance.
    with monkeypatch.context() as patch:
        patch.setattr(packs.os.path, "lexists", lambda path: False)
        with pytest.raises(packs.FrameworkPackError):
            packs.enabled_packs(tmp_path)
    source = Path(packs.__file__).resolve().parents[1]
    assert packs.enabled_packs(source) == packs.KNOWN_PACKS
    assert packs.pack_status(source / "scripts")["source"] == "framework-source"


def test_invalid_source_manifest_cannot_use_source_exception(
    tmp_path: Path, monkeypatch
) -> None:
    module = tmp_path / "scripts/framework_packs.py"
    module.parent.mkdir()
    monkeypatch.setattr(packs, "__file__", str(module))
    path = write_manifest(tmp_path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(packs.FrameworkPackError):
        packs.enabled_packs(tmp_path)


def test_manifest_source_is_never_executed(tmp_path: Path) -> None:
    source = tmp_path / "untrusted-source"
    source.mkdir()
    (source / "install_agentic_framework.py").write_text(
        "raise AssertionError('must not execute')", encoding="utf-8"
    )
    write_manifest(tmp_path, packs=["runtime"])
    assert packs.enabled_packs(tmp_path) == {"runtime"}


def test_utf8_cli_capture_and_cp936_output(tmp_path: Path) -> None:
    root = tmp_path / "中文项目"
    root.mkdir()
    write_manifest(root, packs=["runtime"])
    script = Path(packs.__file__).with_name("install_agentic_framework.py")
    result = subprocess.run(
        [sys.executable, str(script), "--show-packs", str(root)],
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    status = json.loads(result.stdout)
    assert status["enabled"] == ["runtime"]
    assert "中文项目" in status["path"]
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp936")
    stream.write(json.dumps(status, ensure_ascii=False))
    stream.flush()
    assert json.loads(buffer.getvalue().decode("cp936")) == status
