"""Validate the cross-project shared knowledge-base contract.

The validator is intentionally read-only.  It checks structural boundaries that
can be decided without interpreting project-specific prose; semantic
generalisation and redaction remain an explicit human review step.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from markdown_links import LINK_PATTERN, resolve_local_link

ENTRY_DIRS = ("domains", "issues")
REQUIRED_ENTRY_FIELDS = (
    "status",
    "source",
    "source_version",
    "applies_to",
    "excludes",
)
ALLOWED_STATUSES = {"provisional", "verified", "uncertain", "deprecated"}
PROJECT_CANDIDATE_HEADINGS = re.compile(
    r"^#{1,6}\s*(?:跨项目|项目)?知识(?:晋升)?候选(?:[:：].*)?$", re.MULTILINE
)
PROJECT_CANDIDATE_KINDS = {
    "project-candidate",
    "project_candidate",
    "promotion-candidate",
    "promotion_candidate",
}


def _read_file(path: Path) -> str:
    """Read a UTF-8 Markdown file, accepting an optional BOM."""
    return path.read_text(encoding="utf-8-sig")


def _read(path: Path, cache: dict[Path, str]) -> str:
    """Return cached UTF-8 text so each document is read at most once."""
    key = path.resolve()
    if key not in cache:
        cache[key] = _read_file(path)
    return cache[key]


def _frontmatter(
    path: Path, problems: list[str], cache: dict[Path, str]
) -> dict[str, str] | None:
    """Return simple top-level frontmatter fields or report malformed input."""
    relative = path.as_posix()
    lines = _read(path, cache).splitlines()
    if not lines or lines[0].strip() != "---":
        problems.append(f"{relative}：缺少 frontmatter")
        return None

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")

    problems.append(f"{relative}：frontmatter 未闭合")
    return None


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _check_entries(
    root: Path, problems: list[str], cache: dict[Path, str]
) -> None:
    """Check the metadata contract for public knowledge entries."""
    for area in ENTRY_DIRS:
        directory = root / area
        if not directory.is_dir():
            continue
        for entry in sorted(directory.rglob("*.md")):
            if entry.name == "index.md":
                continue
            relative = _relative(entry, root)
            fields = _frontmatter(entry, problems, cache)
            if fields is None:
                continue
            missing = [key for key in REQUIRED_ENTRY_FIELDS if not fields.get(key)]
            if missing:
                problems.append(
                    f"{relative}：frontmatter 缺少或未填写字段 {', '.join(missing)}"
                )
            status = fields.get("status")
            if status and status not in ALLOWED_STATUSES:
                allowed = ", ".join(sorted(ALLOWED_STATUSES))
                problems.append(
                    f"{relative}：status `{status}` 不在允许值中：{allowed}"
                )
            if fields.get("scope", "").lower() == "project":
                problems.append(f"{relative}：公共条目禁止 scope: project")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _points_to_projects(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return bool(relative.parts and relative.parts[0].lower() == "projects")


def _check_index_boundaries(
    root: Path, problems: list[str], cache: dict[Path, str]
) -> None:
    """Reject private or project-scoped targets from public indexes."""
    for index in sorted(root.rglob("index.md")):
        relative = _relative(index, root)
        for line_number, line in enumerate(
            _read(index, cache).splitlines(), start=1
        ):
            for raw_target in LINK_PATTERN.findall(line):
                target = resolve_local_link(index, raw_target)
                if target is None:
                    continue
                if not _is_within(target, root):
                    problems.append(
                        f"{relative}:{line_number}：公共索引链接越出公共库 -> "
                        f"{raw_target}"
                    )
                elif _points_to_projects(target, root):
                    problems.append(
                        f"{relative}:{line_number}：公共索引不得链接 projects/ -> "
                        f"{raw_target}"
                    )


def _check_entry_boundaries(
    root: Path, problems: list[str], cache: dict[Path, str]
) -> None:
    """Reject project-private or repository-external links from public entries."""
    for area in ENTRY_DIRS:
        directory = root / area
        if not directory.is_dir():
            continue
        for entry in sorted(directory.rglob("*.md")):
            relative = _relative(entry, root)
            for line_number, line in enumerate(
                _read(entry, cache).splitlines(), start=1
            ):
                for raw_target in LINK_PATTERN.findall(line):
                    target = resolve_local_link(entry, raw_target)
                    if target is None:
                        continue
                    if not _is_within(target, root):
                        problems.append(
                            f"{relative}:{line_number}：公共条目链接越出公共库 -> "
                            f"{raw_target}"
                        )
                    elif _points_to_projects(target, root):
                        problems.append(
                            f"{relative}:{line_number}：公共条目不得链接 projects/ -> "
                            f"{raw_target}"
                        )


def _check_root_index(
    root: Path, problems: list[str], cache: dict[Path, str]
) -> None:
    """Ensure the retired projects area is absent from daily navigation."""
    index = root / "index.md"
    if not index.is_file():
        problems.append("index.md：根索引不存在")
        return
    for line_number, line in enumerate(_read(index, cache).splitlines(), start=1):
        for raw_target in LINK_PATTERN.findall(line):
            target = resolve_local_link(index, raw_target)
            if target is not None and _points_to_projects(target, root):
                problems.append(
                    f"index.md:{line_number}：projects/ 不得作为日常索引入口"
                )


def _check_changes(
    root: Path, problems: list[str], cache: dict[Path, str]
) -> None:
    """Reject deterministic markers of project promotion candidates."""
    changes = root / "changes"
    if not changes.is_dir():
        return
    for entry in sorted(changes.rglob("*.md")):
        relative = _relative(entry, root)
        text = _read(entry, cache)
        local_problems: list[str] = []
        fields = _frontmatter(entry, local_problems, cache)
        if fields:
            if fields.get("scope", "").lower() == "project":
                problems.append(f"{relative}：公共 changes/ 禁止 scope: project")
            kind = fields.get("kind", fields.get("type", "")).lower()
            if kind in PROJECT_CANDIDATE_KINDS:
                problems.append(
                    f"{relative}：公共 changes/ 禁止项目知识候选类型 `{kind}`"
                )
        if PROJECT_CANDIDATE_HEADINGS.search(text):
            problems.append(f"{relative}：公共 changes/ 禁止保存项目知识候选")


def validate(root: Path) -> list[str]:
    """Return all deterministic shared knowledge contract violations."""
    root = root.resolve()
    problems: list[str] = []
    cache: dict[Path, str] = {}
    _check_root_index(root, problems, cache)
    _check_index_boundaries(root, problems, cache)
    _check_entry_boundaries(root, problems, cache)
    _check_entries(root, problems, cache)
    _check_changes(root, problems, cache)
    return problems


def main(argv: list[str]) -> int:
    """Run the read-only validator."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="只读校验跨项目公共知识库的作用域与元数据契约"
    )
    parser.add_argument("--root", type=Path, required=True, help="公共知识库根目录")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if not root.is_dir() or not (root / "domains").is_dir():
            print(f"error: {root} 不是可用的公共知识库", file=sys.stderr)
            return 2
        problems = validate(root)
    except (OSError, UnicodeError, RecursionError, RuntimeError) as error:
        print(f"error: 无法校验公共知识库：{error}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"violation: {problem}")
    print(f"checked root={root} | violations={len(problems)} | mode=read-only")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
