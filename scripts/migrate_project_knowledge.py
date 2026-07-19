#!/usr/bin/env python3
"""Build a read-only migration plan for legacy project knowledge.

The first version deliberately has no apply mode.  It inventories legacy
knowledge, proposes deterministic destinations where the contract is
unambiguous, and records references that must be reviewed before any copy.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import unquote, urlparse

SOURCE_AREAS = (
    "docs/design-docs",
    "docs/adr",
    "docs/incidents",
    "docs/issues",
    "docs/arch-snapshots",
)
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


@dataclasses.dataclass(frozen=True)
class Reference:
    """One repository-local reference to a legacy knowledge file."""

    path: str
    line: int
    text: str


@dataclasses.dataclass(frozen=True)
class Mapping:
    """One source file and its proposed migration disposition."""

    source: str
    proposed_target: str | None
    status: str
    reason: str
    superseded_marker: str
    references: tuple[Reference, ...]


def _as_posix(path: Path, repo: Path) -> str:
    return path.relative_to(repo).as_posix()


def _slug(parts: tuple[str, ...]) -> str:
    value = "-".join(parts).lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-") or "legacy-change"


def _proposed_target(source: str) -> tuple[str | None, str, str]:
    path = Path(source)
    relative = path.relative_to(*path.parts[:2])
    if source.startswith("docs/design-docs/"):
        parent_parts = relative.parent.parts
        change_name = f"legacy-{_slug(parent_parts)}"
        return (
            (Path("openspec/changes/archive") / change_name / relative.name).as_posix(),
            "review-required",
            "设计文档生命周期必须逐项审核；确认已完成或退役后，才可按原目录聚合为只读 Legacy Change。",
        )
    if source.startswith("docs/adr/"):
        return (
            (Path("openspec/specs/backend/engineering/tech/adr") / relative).as_posix(),
            "review-required",
            "ADR 的最终位置取决于作用域；该位置仅作为项目工程决策候选。",
        )
    if source.startswith("docs/incidents/"):
        return (
            (Path("openspec/issues/incidents") / relative).as_posix(),
            "mapped",
            "已验证 Incident 迁入项目 Issues，并保留 incidents 分类避免重名。",
        )
    if source.startswith("docs/issues/"):
        return (
            (Path("openspec/issues") / relative).as_posix(),
            "mapped",
            "项目 Issue 保持相对路径迁入统一 Issues。",
        )
    return (
        None,
        "classification-required",
        "架构快照必须先确认 frontend/backend、业务域和模块，禁止猜测目标。",
    )


def _legacy_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for area in SOURCE_AREAS:
        root = repo / area
        if not root.is_dir():
            continue
        files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(files), key=lambda path: _as_posix(path, repo))


def _markdown_files(repo: Path) -> list[Path]:
    ignored = {".git", ".worktrees", ".venv", "node_modules"}
    return sorted(
        (
            path
            for path in repo.rglob("*.md")
            if path.is_file() and not ignored.intersection(path.relative_to(repo).parts)
        ),
        key=lambda path: _as_posix(path, repo),
    )


def _resolve_link(source: Path, target: str) -> Path | None:
    raw = target.strip().strip("<>").split("#", 1)[0]
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme:
        return None
    return (source.parent / Path(unquote(raw))).resolve()


def _reference_index(repo: Path, legacy: set[Path]) -> dict[Path, list[Reference]]:
    references = {path.resolve(): [] for path in legacy}
    seen: set[tuple[Path, str, int]] = set()
    for document in _markdown_files(repo):
        lines = document.read_text(encoding="utf-8-sig").splitlines()
        document_name = _as_posix(document, repo)
        for line_number, line in enumerate(lines, start=1):
            targets: set[Path] = set()
            for raw_target in LINK_PATTERN.findall(line):
                target = _resolve_link(document, raw_target)
                if target in references:
                    targets.add(target)
            for legacy_path in legacy:
                relative = _as_posix(legacy_path, repo)
                if relative in line:
                    targets.add(legacy_path.resolve())
            for target in targets:
                key = (target, document_name, line_number)
                if key in seen or target == document.resolve():
                    continue
                seen.add(key)
                references[target].append(
                    Reference(document_name, line_number, line.strip())
                )
    return references


def build_plan(repo: Path) -> dict[str, object]:
    """Return a deterministic, read-only migration plan for ``repo``."""
    repo = repo.resolve()
    if not repo.is_dir():
        raise ValueError(f"仓库目录不存在：{repo}")
    legacy_files = _legacy_files(repo)
    reference_index = _reference_index(repo, set(legacy_files))
    mappings: list[Mapping] = []
    for source_path in legacy_files:
        source = _as_posix(source_path, repo)
        target, status, reason = _proposed_target(source)
        mappings.append(
            Mapping(
                source=source,
                proposed_target=target,
                status=status,
                reason=reason,
                superseded_marker=(
                    "复制并核对引用后，在旧文档头部标记 Superseded；"
                    "未经用户授权不得修改。"
                ),
                references=tuple(reference_index[source_path.resolve()]),
            )
        )
    return {
        "schema_version": 1,
        "mode": "plan-only",
        "repo": str(repo),
        "safety": {
            "writes_source": False,
            "copies_files": False,
            "deletes_files": False,
            "overwrites_files": False,
            "apply_supported": False,
        },
        "source_areas": list(SOURCE_AREAS),
        "summary": {
            "files": len(mappings),
            "references": sum(len(item.references) for item in mappings),
            "classification_required": sum(
                item.status == "classification-required" for item in mappings
            ),
        },
        "mappings": [dataclasses.asdict(item) for item in mappings],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="只读生成项目知识库逐文件迁移映射与引用清单"
    )
    parser.add_argument("--repo", type=Path, required=True, help="项目仓库根目录")
    parser.add_argument(
        "--output",
        type=Path,
        help="可选的 JSON 计划输出文件；不提供时写入标准输出",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the plan-only command."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        plan = build_plan(args.repo)
        output = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
