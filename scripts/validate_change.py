#!/usr/bin/env python3
"""Validate the deterministic structure of an OPSX change directory."""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Sequence

PHASES = ("plan", "delivery", "archive")
TASK_HEADER_RE = re.compile(
    r"^###\s+任务\s+(?P<number>\d+)\s*[:：]\s*"
    r"\[(?P<status>[^]]+)\]\s*(?P<description>.*)$",
    re.IGNORECASE,
)
DEPENDENCY_RE = re.compile(
    r"^-\s*(?:依赖|depends_on)\s*[:：]\s*(?P<value>.*)$", re.IGNORECASE
)
TASK_REFERENCE_RE = re.compile(r"(?:Task|任务)\s*(\d+)", re.IGNORECASE)
REVIEW_RE = re.compile(r"Code\s+Review\s*[:：]\s*(Pending|PASS)\b", re.IGNORECASE)
TASK_REVIEW_PROFILE_RE = re.compile(
    r"^-\s*Review\s+Profile\s*[:：]\s*(\S.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
TASK_REVIEW_STATUS_RE = re.compile(
    r"^-\s*Task\s+Review\s*[:：]\s*(\S.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
TASK_REVIEW_REPORT_RE = re.compile(
    r"^-\s*Review\s+Report\s*[:：]\s*(\S.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
SECTION_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]")
TICKETED_CHANGE_RE = re.compile(
    r"^(?P<ticket>[0-9]+)-(?P<change_name>"
    r"[a-z][a-z0-9]*(?:-[a-z0-9]+)+)$"
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
GENERATED_KNOWLEDGE_NAMES = {
    "overview.md",
    "interfaces.md",
    "architecture.md",
    "dependencies.md",
    "storage.md",
    "config.md",
}
QUICK_STATUS_RE = re.compile(
    r"^\s*(?:\*\*)?状态(?:\*\*)?\s*[:：]\s*Quick\s+Draft\s*$",
    re.IGNORECASE,
)
KNOWLEDGE_ROOTS = {"business", "frontend", "backend", "common"}
COMPLETED_SYNC_STATUSES = {"completed", "complete", "done", "pass", "已完成"}


@dataclasses.dataclass(frozen=True)
class Finding:
    """A deterministic validation finding."""

    rule_id: str
    path: str
    line: int
    message: str
    hint: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the finding."""
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """The result of validating one change for one workflow phase."""

    phase: str
    change_type: str
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        """Whether validation completed without deterministic violations."""
        return not self.findings

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the result."""
        return {
            "ok": self.ok,
            "phase": self.phase,
            "change_type": self.change_type,
            "errors": [finding.to_dict() for finding in self.findings],
        }


@dataclasses.dataclass(frozen=True)
class Task:
    """A task parsed from tasks.md."""

    number: int
    status: str
    description: str
    line: int
    end_line: int
    dependencies: tuple[int, ...]


class InvocationError(Exception):
    """Raised when CLI paths or arguments cannot identify a valid change."""


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise InvocationError(f"无法读取 UTF-8 文件 {path}: {error}") from error


def _relative_path(path: Path, repo: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def _finding(
    rule_id: str,
    path: Path,
    repo: Path,
    line: int,
    message: str,
    hint: str,
) -> Finding:
    return Finding(rule_id, _relative_path(path, repo), line, message, hint)


def _validate_review_report(
    path_text: str, repo: Path, expected_scope: str
) -> list[str]:
    """Validate a review-report.json referenced by a Review Report field.

    Returns a list of descriptive error messages; an empty list means the
    referenced report exists, parses as JSON, and records a passing verdict
    with zero P0/P1 findings. Both the legacy flat layout (verdict fields at
    the top level) and the Envelope layout (verdict fields inside ``payload``)
    are accepted.
    """
    path_value = path_text.strip()
    if not path_value or _is_placeholder(path_value):
        return ["Review Report 路径为空或为占位符。"]
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return ["Review Report 路径必须是仓库根目录内的相对路径。"]
    repo_root = repo.resolve()
    report_path = repo_root / relative_path
    reparse_component = _find_reparse_path_component(repo_root, report_path)
    if reparse_component is not None:
        return [
            "Review Report 路径不得经过符号链接或重解析点："
            f"{_relative_path(reparse_component, repo_root)}。"
        ]
    try:
        report_path.resolve().relative_to(repo_root)
    except (OSError, ValueError):
        return ["Review Report 路径必须位于仓库根目录内。"]
    if not report_path.is_file():
        return [f"Review Report 文件不存在：{path_value}。"]
    try:
        raw = report_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        return [f"Review Report 文件无法读取：{path_value}（{error}）。"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        return [f"Review Report 不是合法 JSON：{path_value}（{error}）。"]
    if not isinstance(data, dict):
        return [f"Review Report 顶层结构必须是 JSON 对象：{path_value}。"]

    errors: list[str] = []
    payload = data.get("payload")
    if isinstance(payload, dict):
        label = "Review Report（Envelope 格式）"
        fields = payload
        artifact_type = data.get("artifact_type")
        if artifact_type != "review-report":
            errors.append(
                f"{label}的 artifact_type 必须为 review-report，"
                f"当前为 {artifact_type!r}。"
            )
    else:
        label = "Review Report（扁平格式）"
        fields = data

    verdict = fields.get("verdict")
    if verdict != "PASS":
        errors.append(f"{label}的 verdict 必须为 PASS，当前为 {verdict!r}。")
    for field in ("p0_count", "p1_count"):
        count = fields.get(field)
        if not isinstance(count, int) or isinstance(count, bool) or count != 0:
            errors.append(f"{label}的 {field} 必须为 0，当前为 {count!r}。")
    if fields.get("scope") != expected_scope:
        errors.append(
            f"{label}的 scope 必须为 {expected_scope}，"
            f"当前为 {fields.get('scope')!r}。"
        )
    if fields.get("review_profile") not in {"lightweight", "standard", "strict"}:
        errors.append(
            f"{label}的 review_profile 非法，当前为 "
            f"{fields.get('review_profile')!r}。"
        )
    round_number = fields.get("round")
    if (
        not isinstance(round_number, int)
        or isinstance(round_number, bool)
        or round_number < 0
    ):
        errors.append(
            f"{label}的 round 必须为非负整数，当前为 {round_number!r}。"
        )
    return errors


def _nonempty_file(path: Path) -> bool:
    return (
        not _is_reparse_point(path)
        and path.is_file()
        and bool(_read_text(path).strip())
    )


def _is_reparse_point(path: Path) -> bool:
    """Return whether a path is a symlink, junction, or other reparse point."""
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction and is_junction():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _find_reparse_point(root: Path) -> Path | None:
    """Find a reparse point without descending through it."""
    if _is_reparse_point(root):
        return root
    try:
        children = list(root.iterdir())
    except OSError:
        return None
    for child in children:
        if _is_reparse_point(child):
            return child
        if child.is_dir():
            found = _find_reparse_point(child)
            if found is not None:
                return found
    return None


def _find_reparse_path_component(root: Path, path: Path) -> Path | None:
    """Find a reparse point between an existing root and a lexical child path."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return path
    current = root
    for part in relative.parts:
        current /= part
        if os.path.lexists(current) and _is_reparse_point(current):
            return current
    return None


def _normalized_section_title(title: str) -> str:
    title = re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", title.strip())
    title = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", title)
    return title.strip().casefold()


def _section_has_content(lines: Sequence[str], alternatives: Sequence[str]) -> bool:
    normalized = {_normalized_section_title(item) for item in alternatives}
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if (
            not match
            or _normalized_section_title(match.group("title")) not in normalized
        ):
            continue
        level = len(match.group("marks"))
        for content_line in lines[index + 1 :]:
            next_heading = SECTION_RE.match(content_line)
            if next_heading:
                if len(next_heading.group("marks")) <= level:
                    break
                continue
            stripped = content_line.strip().lstrip("-* ").strip()
            if stripped and not _is_placeholder(stripped):
                return True
    return False


def _section_lines(lines: Sequence[str], title: str) -> tuple[list[str], int]:
    """Return the body and source line of a Markdown section."""
    normalized = _normalized_section_title(title)
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if not match or _normalized_section_title(match.group("title")) != normalized:
            continue
        level = len(match.group("marks"))
        body: list[str] = []
        for content_line in lines[index + 1 :]:
            next_heading = SECTION_RE.match(content_line)
            if next_heading and len(next_heading.group("marks")) <= level:
                break
            body.append(content_line)
        return body, index + 1
    return [], 1


def _is_placeholder(value: str) -> bool:
    stripped = value.strip().strip("`*")
    return not stripped or stripped in {"-", "待填写", "TODO", "TBD"}


def _parse_tasks(tasks_path: Path) -> tuple[list[Task], list[str]]:
    lines = _read_text(tasks_path).splitlines()
    headers: list[tuple[int, re.Match[str]]] = []
    for line_number, line in enumerate(lines, start=1):
        match = TASK_HEADER_RE.match(line)
        if match:
            headers.append((line_number, match))

    tasks: list[Task] = []
    for index, (line_number, match) in enumerate(headers):
        end_line = headers[index + 1][0] - 1 if index + 1 < len(headers) else len(lines)
        block = lines[line_number:end_line]
        dependencies: list[int] = []
        for line in block:
            dependency_match = DEPENDENCY_RE.match(line.strip())
            if dependency_match:
                dependencies.extend(
                    int(value)
                    for value in TASK_REFERENCE_RE.findall(
                        dependency_match.group("value")
                    )
                )
        tasks.append(
            Task(
                number=int(match.group("number")),
                status=match.group("status").strip(),
                description=match.group("description").strip(),
                line=line_number,
                end_line=end_line,
                dependencies=tuple(dict.fromkeys(dependencies)),
            )
        )
    return tasks, lines


def _dependency_cycle(tasks: Sequence[Task]) -> list[int] | None:
    graph = {task.number: task.dependencies for task in tasks}
    state: dict[int, int] = {}

    for start in graph:
        if state.get(start, 0) != 0:
            continue
        state[start] = 1
        path = [start]
        frames = [(start, 0)]
        while frames:
            number, index = frames[-1]
            dependencies = graph[number]
            if index >= len(dependencies):
                state[number] = 2
                frames.pop()
                path.pop()
                continue
            dependency = dependencies[index]
            frames[-1] = (number, index + 1)
            if dependency not in graph or dependency == number:
                continue
            if state.get(dependency, 0) == 0:
                state[dependency] = 1
                path.append(dependency)
                frames.append((dependency, 0))
            elif state.get(dependency) == 1:
                cycle_start = path.index(dependency)
                return path[cycle_start:] + [dependency]
    return None


def _task_block(lines: Sequence[str], task: Task) -> list[str]:
    return list(lines[task.line - 1 : task.end_line])


def _metadata_text(lines: Sequence[str]) -> str:
    """Return task metadata with fenced code blocks removed."""
    result: list[str] = []
    fence: str | None = None
    for line in lines:
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker
            continue
        if fence is None:
            result.append(line)
    return "\n".join(result)


def _completed_status(status: str) -> bool:
    return status.casefold() in {"x", "completed", "complete", "done"}


def _header_review_status(
    lines: Sequence[str], header_end: int
) -> tuple[str | None, int]:
    """Return the unique Code Review status from unfenced header metadata."""
    matches: list[tuple[str, int]] = []
    fence: str | None = None
    for line_number, line in enumerate(lines[:header_end], start=1):
        marker = line.lstrip()[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker
            continue
        if fence is not None:
            continue
        match = REVIEW_RE.search(line)
        if match:
            matches.append((match.group(1).upper(), line_number))
    if len(matches) != 1:
        return None, matches[0][1] if matches else 1
    return matches[0]


def _mapping_rows(lines: Sequence[str]) -> list[tuple[int, list[str]]]:
    in_mapping = False
    rows: list[tuple[int, list[str]]] = []
    for line_number, line in enumerate(lines, start=1):
        match = SECTION_RE.match(line)
        if match:
            if in_mapping:
                break
            in_mapping = (
                _normalized_section_title(match.group("title")) == "文档覆盖映射"
            )
            continue
        if in_mapping and line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and not all(set(cell) <= {"-", ":"} for cell in cells):
                if cells[0] not in {"文档条目", ""} and cells[1] not in {"任务", ""}:
                    rows.append((line_number, cells))
    return rows


def _execution_record(lines: Sequence[str], kind: str) -> tuple[bool, int]:
    pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?{kind}(?:命令|验证|执行记录)?\s*[:：]\s*(.+)$",
        re.IGNORECASE,
    )
    matched_line = 1
    for line_number, line in enumerate(lines, start=1):
        match = pattern.match(line)
        if not match:
            continue
        matched_line = line_number
        value = match.group(1).strip()
        failure = re.search(
            r"(?:失败|\bFAIL(?:ED)?\b|退出码\s*[1-9]\d*)", value, re.IGNORECASE
        )
        if failure:
            return False, line_number
        if re.search(r"(?:退出码\s*0\b|\bPASS(?:ED)?\b)", value, re.IGNORECASE):
            return True, line_number
        na_match = re.match(r"N/A\s*[,，:：;；-]\s*(\S.*)$", value, re.IGNORECASE)
        if na_match and not _is_placeholder(na_match.group(1)):
            return True, line_number
    return False, matched_line


def _validate_common(repo: Path, change: Path) -> list[Finding]:
    findings: list[Finding] = []
    reparse_point = _find_reparse_point(change)
    if reparse_point is not None:
        findings.append(
            _finding(
                "OPSX004",
                reparse_point,
                repo,
                1,
                "Change 目录不得包含符号链接、Junction 或其他重解析点。",
                "将重解析点替换为 Change 目录内的普通文件或目录。",
            )
        )

    expected_parent = (repo / "openspec" / "changes").resolve()
    if change.parent.resolve() != expected_parent:
        findings.append(
            _finding(
                "OPSX002",
                change,
                repo,
                1,
                "Change 目录必须直接位于 openspec/changes/。",
                "通过 --change openspec/changes/<ticket>-<change-name> 指定活跃变更。",
            )
        )
    if not TICKETED_CHANGE_RE.fullmatch(change.name):
        findings.append(
            _finding(
                "OPSX003",
                change,
                repo,
                1,
                "Change 名称不符合 <ticket>-<change-name> 格式。",
                "工单号必须是纯数字，Change 名称使用小写 kebab-case，例如 123-add-validation。",
            )
        )
    return findings


def _frontmatter_fields(path: Path) -> dict[str, str]:
    """Read simple top-level frontmatter fields from a Markdown file."""
    lines = _read_text(path).splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    active_key = ""
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1].isspace():
            if active_key and line.strip().startswith("-"):
                item = line.strip()[1:].strip()
                if item:
                    fields[active_key] = " ".join(
                        value for value in (fields.get(active_key), item) if value
                    )
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        active_key = key.strip()
        fields[active_key] = value.strip()
    return {}


def _yaml_metadata_fields(path: Path, entity_name: str) -> dict[str, str]:
    """Extract source metadata for one module/service from a YAML registry."""
    lines = _read_text(path).splitlines()
    entity_pattern = re.compile(rf"^(?P<indent>\s*){re.escape(entity_name)}\s*:\s*$")
    start = -1
    entity_indent = 0
    for index, line in enumerate(lines):
        match = entity_pattern.match(line)
        if match:
            start = index + 1
            entity_indent = len(match.group("indent"))
            break
    if start < 0:
        return {}

    fields: dict[str, str] = {}
    active_key = ""
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= entity_indent:
            break
        if stripped.startswith("-") and active_key:
            item = stripped[1:].strip()
            if item:
                fields[active_key] = " ".join(
                    value for value in (fields.get(active_key), item) if value
                )
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        active_key = key.strip()
        if active_key in {"source_ref", "source_paths", "generated_at"}:
            fields[active_key] = value.strip()
    return fields


def _generated_metadata(document: Path, root: Path) -> dict[str, str]:
    """Return per-file metadata, falling back to the nearest domain meta.yaml."""
    fields = _frontmatter_fields(document)
    current = document.parent
    while current == root or root in current.parents:
        registry = current / "meta.yaml"
        if registry.is_file():
            entity_name = document.parent.name
            for key, value in _yaml_metadata_fields(registry, entity_name).items():
                if not fields.get(key):
                    fields[key] = value
            break
        if current == root:
            break
        current = current.parent
    return fields


def _validate_project_knowledge(repo: Path) -> list[Finding]:
    """Validate the minimum project knowledge skeleton before archive."""
    findings: list[Finding] = []
    openspec = repo / "openspec"
    required_indexes = (
        openspec / "index.md",
        openspec / "specs" / "index.md",
        openspec / "issues" / "index.md",
    )
    for index in required_indexes:
        if not index.is_file():
            findings.append(
                _finding(
                    "OPSX049",
                    index,
                    repo,
                    1,
                    "项目知识库缺少必需索引。",
                    "创建 openspec/index.md、specs/index.md 和 issues/index.md。",
                )
            )

    for index in openspec.rglob("index.md") if openspec.is_dir() else ():
        for line_number, line in enumerate(_read_text(index).splitlines(), start=1):
            for raw_target in MARKDOWN_LINK_RE.findall(line):
                target = raw_target.strip().strip("<>").split("#", 1)[0]
                if not target or re.match(r"^(?:https?|mailto):", target):
                    continue
                linked = (index.parent / target).resolve()
                if not linked.exists():
                    findings.append(
                        _finding(
                            "OPSX050",
                            index,
                            repo,
                            line_number,
                            f"知识索引链接目标不存在：{raw_target}",
                            "修正索引链接或创建目标条目后再归档。",
                        )
                    )

    specs = openspec / "specs"
    generated_roots = (specs / "frontend", specs / "backend")
    for root in generated_roots:
        if not root.is_dir():
            continue
        for document in root.rglob("*.md"):
            if document.name not in GENERATED_KNOWLEDGE_NAMES:
                continue
            if "custom" in document.relative_to(root).parts:
                continue
            fields = _generated_metadata(document, root)
            missing = [
                field
                for field in ("source_ref", "source_paths", "generated_at")
                if not fields.get(field)
            ]
            if missing:
                findings.append(
                    _finding(
                        "OPSX051",
                        document,
                        repo,
                        1,
                        "自动生成知识缺少来源元数据：" + ", ".join(missing),
                        "补充 source_ref、source_paths 和 generated_at frontmatter。",
                    )
                )
    return findings


def _validate_artifacts(repo: Path, change: Path) -> tuple[list[Finding], str]:
    findings: list[Finding] = []
    proposal_path = change / "proposal.md"
    tasks_path = change / "tasks.md"
    proposal_text = _read_text(proposal_path) if proposal_path.is_file() else ""
    proposal_lines = proposal_text.splitlines()
    change_type = (
        "quick"
        if any(QUICK_STATUS_RE.match(line) for line in proposal_lines)
        else "standard"
    )

    for path, rule_id, label in (
        (proposal_path, "OPSX010", "proposal.md"),
        (tasks_path, "OPSX011", "tasks.md"),
    ):
        if not _nonempty_file(path):
            findings.append(
                _finding(
                    rule_id,
                    path,
                    repo,
                    1,
                    f"{label} 不存在或为空。",
                    f"创建非空的 {label}。",
                )
            )

    if proposal_text:
        required_sections = (
            ("OPSX012", ("背景", "问题"), "问题或背景"),
            ("OPSX013", ("目标", "Goals"), "目标"),
            ("OPSX014", ("非目标", "Non-Goals"), "非目标或范围边界"),
            ("OPSX015", ("验收标准", "成功标准"), "成功标准或验收标准"),
        )
        for rule_id, alternatives, label in required_sections:
            if not _section_has_content(proposal_lines, alternatives):
                findings.append(
                    _finding(
                        rule_id,
                        proposal_path,
                        repo,
                        1,
                        f"Proposal 缺少「{label}」章节。",
                        f"添加明确的「{label}」章节。",
                    )
                )

        if change_type == "quick":
            for rule_id, alternatives, label in (
                ("OPSX016", ("设计方案", "整体方案"), "核心方案"),
                ("OPSX017", ("关键权衡",), "关键权衡"),
            ):
                if not _section_has_content(proposal_lines, alternatives):
                    findings.append(
                        _finding(
                            rule_id,
                            proposal_path,
                            repo,
                            1,
                            f"Quick Proposal 缺少「{label}」章节。",
                            f"在 Proposal 中补充「{label}」。",
                        )
                    )
        else:
            spec_files = list((change / "specs").rglob("*.md"))
            if not any(_nonempty_file(path) for path in spec_files):
                findings.append(
                    _finding(
                        "OPSX018",
                        change / "specs",
                        repo,
                        1,
                        "Standard 路径至少需要一个非空 specs/ 下的 Delta Markdown。",
                        "创建本次变更的 Requirements Spec。",
                    )
                )
            design_path = change / "design.md"
            if not _nonempty_file(design_path):
                findings.append(
                    _finding(
                        "OPSX019",
                        design_path,
                        repo,
                        1,
                        "Standard 路径需要非空 design.md。",
                        "完成详细设计，或将低风险变更明确标记为 Quick Draft。",
                    )
                )
    return findings, change_type


def _delta_targets(repo: Path, change: Path) -> tuple[list[Finding], dict[str, str]]:
    """Validate deterministic Delta paths and return source-to-target mappings."""
    findings: list[Finding] = []
    mappings: dict[str, str] = {}
    specs_root = change / "specs"
    if not specs_root.is_dir():
        return findings, mappings
    for delta in specs_root.rglob("*.md"):
        if not _nonempty_file(delta):
            continue
        relative = delta.relative_to(specs_root)
        if len(relative.parts) < 2 or relative.parts[0] not in KNOWLEDGE_ROOTS:
            findings.append(
                _finding(
                    "OPSX042",
                    delta,
                    repo,
                    1,
                    "Delta 路径不能映射到受控长期 Specs。",
                    "将 Delta 放到 specs/business、frontend、backend 或 common 下，并镜像长期目标路径。",
                )
            )
            continue
        source = delta.relative_to(change).as_posix()
        mappings[source] = (Path("openspec/specs") / relative).as_posix()
    return findings, mappings


def _knowledge_sync_rows(lines: Sequence[str]) -> list[tuple[int, list[str]]]:
    body, heading_line = _section_lines(lines, "知识同步")
    rows: list[tuple[int, list[str]]] = []
    for offset, line in enumerate(body, start=1):
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if cells[0].casefold() in {"delta", "增量"}:
            continue
        rows.append((heading_line + offset, cells))
    return rows


def _validate_archive_knowledge(repo: Path, change: Path) -> list[Finding]:
    """Validate archive knowledge bookkeeping without doing semantic merges."""
    _, mappings = _delta_targets(repo, change)
    findings: list[Finding] = []
    proposal_path = change / "proposal.md"
    tasks_path = change / "tasks.md"
    proposal_lines = (
        _read_text(proposal_path).splitlines() if proposal_path.is_file() else []
    )
    impact_body, impact_line = _section_lines(proposal_lines, "知识影响")
    impact_text = "\n".join(impact_body).strip()
    if not impact_text or _is_placeholder(impact_text):
        findings.append(
            _finding(
                "OPSX043",
                proposal_path,
                repo,
                impact_line,
                "Proposal 缺少明确的知识影响结论。",
                "添加「知识影响」章节，列出受影响长期知识，或写明无影响及理由。",
            )
        )
    no_impact = bool(re.search(r"无长期知识影响\s*[:：,，;；-]\s*\S", impact_text))
    if mappings and no_impact:
        findings.append(
            _finding(
                "OPSX043",
                proposal_path,
                repo,
                impact_line,
                "Proposal 声明无长期知识影响，但 Change 包含 Delta。",
                "修正知识影响结论，或移除不应长期同步的 Delta。",
            )
        )

    tasks_lines = _read_text(tasks_path).splitlines() if tasks_path.is_file() else []
    rows = _knowledge_sync_rows(tasks_lines)
    row_mappings: dict[str, tuple[str, str, str, int]] = {}
    for line_number, cells in rows:
        source, target, action, status, index_update = cells[:5]
        if source in row_mappings:
            findings.append(
                _finding(
                    "OPSX044",
                    tasks_path,
                    repo,
                    line_number,
                    f"知识同步源 {source} 存在重复映射。",
                    "每个 Delta 或知识产物只保留一条同步记录。",
                )
            )
        row_mappings[source] = (target, action, status, line_number)
        if action.casefold() not in {"added", "modified", "removed", "renamed"}:
            findings.append(
                _finding(
                    "OPSX044",
                    tasks_path,
                    repo,
                    line_number,
                    "知识同步动作不是 ADDED、MODIFIED、REMOVED 或 RENAMED。",
                    "记录标准知识同步动作。",
                )
            )
        if status.casefold() not in COMPLETED_SYNC_STATUSES:
            findings.append(
                _finding(
                    "OPSX045",
                    tasks_path,
                    repo,
                    line_number,
                    f"知识 {source} 的同步尚未完成。",
                    "人工核对并同步项目知识后，将状态更新为 Completed。",
                )
            )
        if _is_placeholder(index_update):
            findings.append(
                _finding(
                    "OPSX046",
                    tasks_path,
                    repo,
                    line_number,
                    "知识同步记录缺少索引更新结果或无需更新理由。",
                    "在「索引更新」列记录目标索引，或写明无需更新及理由。",
                )
            )
    for source, expected_target in mappings.items():
        row = row_mappings.get(source)
        if row is None or row[0] != expected_target:
            findings.append(
                _finding(
                    "OPSX044",
                    tasks_path,
                    repo,
                    1,
                    f"Delta {source} 缺少准确的长期目标映射。",
                    f"在「知识同步」表中映射到 {expected_target}。",
                )
            )
            continue
    if not mappings and not no_impact and not rows:
        findings.append(
            _finding(
                "OPSX044",
                tasks_path,
                repo,
                1,
                "知识影响非空，但没有可校验的 Delta 映射。",
                "补充镜像 Delta 和知识同步记录，或在 Proposal 中说明无影响及理由。",
            )
        )

    conflict_body, conflict_line = _section_lines(tasks_lines, "知识冲突")
    conflict_text = "\n".join(conflict_body).strip()
    resolved = "无冲突" in conflict_text or bool(
        re.search(r"状态\s*[:：]\s*(?:Resolved|已解决)\b", conflict_text, re.IGNORECASE)
    )
    if not resolved:
        findings.append(
            _finding(
                "OPSX047",
                tasks_path,
                repo,
                conflict_line,
                "知识冲突检查缺失或仍未解决。",
                "记录「无冲突」，或记录双方证据并将已处理冲突标记为 Resolved。",
            )
        )
    diff_body, diff_line = _section_lines(tasks_lines, "实际 Diff 核对")
    if not re.search(
        r"(?:PASS|退出码\s*0|已核对)", "\n".join(diff_body), re.IGNORECASE
    ):
        findings.append(
            _finding(
                "OPSX048",
                tasks_path,
                repo,
                diff_line,
                "缺少实际 Diff 与 Change/测试证据的核对记录。",
                "在「实际 Diff 核对」章节记录命令或证据及 PASS 结论。",
            )
        )
    return findings


def _validate_tasks(repo: Path, change: Path, require_completed: bool) -> list[Finding]:
    tasks_path = change / "tasks.md"
    if not _nonempty_file(tasks_path):
        return []

    findings: list[Finding] = []
    tasks, lines = _parse_tasks(tasks_path)
    if not tasks:
        return [
            _finding(
                "OPSX020",
                tasks_path,
                repo,
                1,
                "tasks.md 中没有可解析的任务。",
                "使用「### 任务 N：[pending] 描述」格式定义任务。",
            )
        ]

    task_numbers = {task.number for task in tasks}
    if len(task_numbers) != len(tasks):
        findings.append(
            _finding(
                "OPSX021",
                tasks_path,
                repo,
                1,
                "任务编号存在重复。",
                "为每个任务分配唯一编号。",
            )
        )

    for task in tasks:
        block = _task_block(lines, task)
        if not task.description:
            findings.append(
                _finding(
                    "OPSX022",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 缺少说明。",
                    "在任务标题中添加简短说明。",
                )
            )
        dependency_lines = [
            (task.line + offset, DEPENDENCY_RE.match(line.strip()))
            for offset, line in enumerate(block)
            if DEPENDENCY_RE.match(line.strip())
        ]
        if not dependency_lines:
            findings.append(
                _finding(
                    "OPSX023",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 未声明依赖。",
                    "添加「- 依赖：无」或列出前置 Task。",
                )
            )
        else:
            dependency_value = dependency_lines[0][1].group("value").strip()
            valid_dependencies = re.fullmatch(
                r"(?:无|none|(?:(?:Task|任务)\s*\d+\s*(?:[,，、]\s*)?)+)",
                dependency_value,
                re.IGNORECASE,
            )
            if len(dependency_lines) != 1 or valid_dependencies is None:
                findings.append(
                    _finding(
                        "OPSX023",
                        tasks_path,
                        repo,
                        dependency_lines[0][0],
                        f"Task {task.number} 的依赖声明为空或格式无效。",
                        "使用「- 依赖：无」或明确列出 Task 编号。",
                    )
                )
        for dependency in task.dependencies:
            dependency_line = next(
                (
                    line_number
                    for line_number, match in dependency_lines
                    if re.search(
                        rf"(?:Task|任务)\s*{dependency}\b",
                        match.group("value"),
                        re.IGNORECASE,
                    )
                ),
                task.line,
            )
            if dependency == task.number:
                findings.append(
                    _finding(
                        "OPSX024",
                        tasks_path,
                        repo,
                        dependency_line,
                        f"Task {task.number} 不能依赖自身。",
                        "删除自依赖并重新检查任务拆分。",
                    )
                )
            elif dependency not in task_numbers:
                findings.append(
                    _finding(
                        "OPSX025",
                        tasks_path,
                        repo,
                        dependency_line,
                        f"Task {task.number} 引用了不存在的 Task {dependency}。",
                        "修正依赖编号或补充缺失任务。",
                    )
                )

        block_text = "\n".join(block)
        acceptance_index = next(
            (
                offset
                for offset, line in enumerate(block)
                if re.match(r"^-\s*验收标准\s*[:：]", line)
            ),
            None,
        )
        if acceptance_index is None:
            findings.append(
                _finding(
                    "OPSX026",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 缺少验收标准。",
                    "添加可机械执行的「- 验收标准：」清单。",
                )
            )
        else:
            acceptance_lines: list[str] = []
            for line in block[acceptance_index + 1 :]:
                if re.match(r"^-\s*\S[^:：]*\s*[:：]", line):
                    break
                acceptance_lines.append(line)
            if not any(CHECKBOX_RE.match(line) for line in acceptance_lines):
                findings.append(
                    _finding(
                        "OPSX036",
                        tasks_path,
                        repo,
                        task.line + acceptance_index,
                        f"Task {task.number} 的验收标准没有复选项。",
                        "在验收标准下添加至少一个可机械执行的 checkbox。",
                    )
                )

        file_match = re.search(
            r"^-\s*(?:文件|无需修改代码)\s*[:：]\s*(.*)$",
            block_text,
            re.MULTILINE,
        )
        if file_match is None or _is_placeholder(file_match.group(1)):
            findings.append(
                _finding(
                    "OPSX027",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 未声明修改文件或无需修改代码。",
                    "添加「- 文件：...」或「- 无需修改代码：理由」。",
                )
            )
        mapping_match = re.search(
            r"^-\s*文档映射\s*[:：]\s*(.*)$", block_text, re.MULTILINE
        )
        if mapping_match is None or _is_placeholder(mapping_match.group(1)):
            findings.append(
                _finding(
                    "OPSX035",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 缺少非空文档映射。",
                    "添加「- 文档映射：<artifact 条目>」。",
                )
            )
        metadata_text = _metadata_text(block)
        profile_matches = list(TASK_REVIEW_PROFILE_RE.finditer(metadata_text))
        if len(profile_matches) != 1 or profile_matches[0].group(1).casefold() not in {
            "standard",
            "strict",
        }:
            findings.append(
                _finding(
                    "OPSX037",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 缺少合法的 Review Profile。",
                    "添加「- Review Profile: standard」或「strict」。",
                )
            )
        task_review_matches = list(TASK_REVIEW_STATUS_RE.finditer(metadata_text))
        if len(task_review_matches) != 1 or task_review_matches[0].group(
            1
        ).casefold() not in {"pending", "pass"}:
            findings.append(
                _finding(
                    "OPSX038",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 缺少合法的 Task Review 状态。",
                    "添加「- Task Review: Pending」；审核通过后更新为 PASS。",
                )
            )
        elif require_completed and task_review_matches[0].group(1).casefold() != "pass":
            findings.append(
                _finding(
                    "OPSX038",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 的 Task Review 尚未 PASS。",
                    "完成 Task 级独立审核并将状态更新为 PASS。",
                )
            )
        elif require_completed:
            report_matches = list(TASK_REVIEW_REPORT_RE.finditer(metadata_text))
            if len(report_matches) != 1:
                findings.append(
                    _finding(
                        "OPSX038",
                        tasks_path,
                        repo,
                        task.line,
                        f"Task {task.number} 的 Task Review 为 PASS 但缺少合法的 Review Report 字段。",
                        "添加「- Review Report: <path>」指向 Task 级 review-report.json。",
                    )
                )
            else:
                for message in _validate_review_report(
                    report_matches[0].group(1), repo, "task"
                ):
                    findings.append(
                        _finding(
                            "OPSX038",
                            tasks_path,
                            repo,
                            task.line,
                            f"Task {task.number} 的 Review Report 无效：{message}",
                            "确认 review-report.json 存在且 verdict 为 PASS、P0/P1 计数为 0。",
                        )
                    )
        if require_completed and not _completed_status(task.status):
            findings.append(
                _finding(
                    "OPSX030",
                    tasks_path,
                    repo,
                    task.line,
                    f"Task {task.number} 状态不是 Completed。",
                    "完成任务并将状态更新为 [completed] 或 [x]。",
                )
            )
        if require_completed:
            for offset, line in enumerate(block):
                checkbox = CHECKBOX_RE.match(line)
                if checkbox and checkbox.group("mark") == " ":
                    findings.append(
                        _finding(
                            "OPSX031",
                            tasks_path,
                            repo,
                            task.line + offset,
                            f"Task {task.number} 仍有未完成复选框。",
                            "完成该子任务或验收项并勾选复选框。",
                        )
                    )

    cycle = _dependency_cycle(tasks)
    if cycle:
        first = next(task for task in tasks if task.number == cycle[0])
        findings.append(
            _finding(
                "OPSX028",
                tasks_path,
                repo,
                first.line,
                "任务依赖存在环："
                + " -> ".join(f"Task {number}" for number in cycle)
                + "。",
                "重新拆分或调整依赖，使依赖图成为 DAG。",
            )
        )

    return findings


def _validate_plan(repo: Path, change: Path, change_type: str) -> list[Finding]:
    findings = _validate_tasks(repo, change, require_completed=False)
    tasks_path = change / "tasks.md"
    if not _nonempty_file(tasks_path):
        return findings

    tasks, lines = _parse_tasks(tasks_path)
    task_numbers = {task.number for task in tasks}
    if change_type == "standard":
        rows = _mapping_rows(lines)
        mapped_artifacts: set[str] = set()
        invalid_reference_line = 1
        for line_number, cells in rows:
            artifact = cells[0].casefold()
            if "proposal.md" in artifact:
                mapped_artifacts.add("proposal")
            if "spec.md" in artifact:
                mapped_artifacts.add("spec")
            if "design.md" in artifact:
                mapped_artifacts.add("design")
            references = {int(value) for value in TASK_REFERENCE_RE.findall(cells[1])}
            if not references or not references <= task_numbers:
                invalid_reference_line = line_number
        missing = {"proposal", "spec", "design"} - mapped_artifacts
        if not rows or missing or invalid_reference_line != 1:
            detail = ", ".join(sorted(missing)) if missing else "Task 引用无效"
            findings.append(
                _finding(
                    "OPSX029",
                    tasks_path,
                    repo,
                    invalid_reference_line,
                    f"Standard 文档覆盖映射不完整：{detail}。",
                    "添加「文档覆盖映射」并映射 Requirements、Design 与 Tasks。",
                )
            )
    else:
        acceptance_mapping = re.compile(
            r"^-\s*文档映射\s*[:：].*proposal\.md.*(?:验收标准|acceptance criteria)",
            re.IGNORECASE,
        )
        if not any(acceptance_mapping.search(line) for line in lines):
            findings.append(
                _finding(
                    "OPSX029",
                    tasks_path,
                    repo,
                    1,
                    "Quick Tasks 未映射 Proposal 验收标准。",
                    "至少一个任务须明确映射「proposal.md 验收标准」。",
                )
            )
    return findings


def _validate_delivery(
    repo: Path,
    change: Path,
    expected_review: str,
) -> list[Finding]:
    findings = _validate_tasks(repo, change, require_completed=True)
    tasks_path = change / "tasks.md"
    if not _nonempty_file(tasks_path):
        return findings

    tasks, lines = _parse_tasks(tasks_path)
    header_end = tasks[0].line - 1 if tasks else len(lines)
    review_status, review_line = _header_review_status(lines, header_end)
    if review_status != expected_review:
        findings.append(
            _finding(
                "OPSX032",
                tasks_path,
                repo,
                review_line,
                f"Code Review 状态必须为 {expected_review}，当前为 {review_status or '缺失'}。",
                f"将文档头部的 Code Review 状态更新为 {expected_review}。",
            )
        )
    elif expected_review == "PASS":
        header_text = _metadata_text(lines[:header_end])
        report_matches = list(TASK_REVIEW_REPORT_RE.finditer(header_text))
        if len(report_matches) != 1:
            findings.append(
                _finding(
                    "OPSX032",
                    tasks_path,
                    repo,
                    review_line,
                    "Code Review 为 PASS 但变更头部缺少合法的 Review Report 字段。",
                    "在变更头部添加「- Review Report: <path>」指向集成级 review-report.json。",
                )
            )
        else:
            for message in _validate_review_report(
                report_matches[0].group(1), repo, "integration"
            ):
                findings.append(
                    _finding(
                        "OPSX032",
                        tasks_path,
                        repo,
                        review_line,
                        f"变更 Code Review 的 Review Report 无效：{message}",
                        "确认 review-report.json 存在且 verdict 为 PASS、P0/P1 计数为 0。",
                    )
                )
    build_ok, build_line = _execution_record(lines, "构建")
    if not build_ok:
        findings.append(
            _finding(
                "OPSX033",
                tasks_path,
                repo,
                build_line,
                "构建命令执行记录缺失或没有明确成功证据。",
                "记录「退出码 0」或 PASS；N/A 必须附非空理由。",
            )
        )
    test_ok, test_line = _execution_record(lines, "测试")
    if not test_ok:
        findings.append(
            _finding(
                "OPSX034",
                tasks_path,
                repo,
                test_line,
                "测试命令执行记录缺失或没有明确成功证据。",
                "记录「退出码 0」或 PASS；N/A 必须附非空理由。",
            )
        )
    return findings


def validate_change(
    repo: Path,
    change: Path,
    phase: str,
    archive_target: Path | None = None,
) -> ValidationResult:
    """Validate an OPSX change without modifying repository files.

    Args:
        repo: Repository root directory.
        change: Active change directory, absolute or relative to ``repo``.
        phase: One of ``plan``, ``delivery``, or ``archive``.
        archive_target: Intended archive destination for the archive phase.

    Returns:
        The structured validation result.

    Raises:
        InvocationError: If arguments or paths cannot be used for validation.
    """
    if phase not in PHASES:
        raise InvocationError(f"不支持的阶段：{phase}")
    if phase == "archive" and archive_target is None:
        raise InvocationError("Archive 阶段必须提供 --archive-target。")
    repo = repo.resolve()
    if not repo.is_dir():
        raise InvocationError(f"仓库目录不存在：{repo}")
    change = change.absolute() if change.is_absolute() else (repo / change).absolute()
    reparse_component = _find_reparse_path_component(repo, change)
    allowed_openspec_link = (repo / "openspec").absolute()
    if reparse_component is not None and reparse_component != allowed_openspec_link:
        raise InvocationError(
            f"Change 路径不得经过符号链接、Junction 或其他重解析点：{reparse_component}"
        )
    if not change.is_dir():
        raise InvocationError(f"Change 目录不存在：{change}")
    try:
        change.relative_to(repo)
    except ValueError as error:
        raise InvocationError("Change 目录必须位于仓库内。") from error

    findings = _validate_common(repo, change)
    if any(finding.rule_id == "OPSX004" for finding in findings):
        return ValidationResult(phase, "standard", tuple(findings))
    artifact_findings, change_type = _validate_artifacts(repo, change)
    findings.extend(artifact_findings)
    delta_findings, _ = _delta_targets(repo, change)
    findings.extend(delta_findings)
    findings.extend(_validate_plan(repo, change, change_type))
    if phase == "delivery":
        findings.extend(_validate_delivery(repo, change, "PENDING"))
    elif phase == "archive":
        findings.extend(_validate_delivery(repo, change, "PASS"))
        findings.extend(_validate_archive_knowledge(repo, change))
        findings.extend(_validate_project_knowledge(repo))
        assert archive_target is not None
        archive_target = (
            archive_target if archive_target.is_absolute() else repo / archive_target
        )
        expected_parent = (repo / "openspec" / "changes" / "archive").resolve()
        if archive_target.parent.resolve() != expected_parent:
            findings.append(
                _finding(
                    "OPSX041",
                    archive_target,
                    repo,
                    1,
                    "Archive 目标必须直接位于 openspec/changes/archive/。",
                    "将 --archive-target 指向 archive/ 下的直接子目录。",
                )
            )
        if archive_target.exists() or archive_target.is_symlink():
            findings.append(
                _finding(
                    "OPSX040",
                    archive_target,
                    repo,
                    1,
                    "Archive 目标目录已存在，禁止覆盖。",
                    "选择未使用的归档日期或先处理已有目录。",
                )
            )
        change_match = TICKETED_CHANGE_RE.fullmatch(change.name)
        name_match = None
        if change_match:
            name_match = re.fullmatch(
                rf"{re.escape(change_match.group('ticket'))}-"
                rf"(?P<date>\d{{4}}-\d{{2}}-\d{{2}})-"
                rf"{re.escape(change_match.group('change_name'))}",
                archive_target.name,
            )
        valid_date = False
        if name_match:
            try:
                datetime.date.fromisoformat(name_match.group("date"))
                valid_date = True
            except ValueError:
                pass
        if not valid_date:
            findings.append(
                _finding(
                    "OPSX041",
                    archive_target,
                    repo,
                    1,
                    "Archive 目录名不符合 <ticket>-YYYY-MM-DD-<change-name>。",
                    "按工单号、日期和原 Change 名称生成归档目录，例如 123-2026-07-22-add-validation。",
                )
            )
    return ValidationResult(phase, change_type, tuple(findings))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="只读校验 OPSX Change 的确定性结构。",
    )
    parser.add_argument("--repo", type=Path, required=True, help="仓库根目录")
    parser.add_argument("--change", type=Path, required=True, help="活跃 Change 目录")
    parser.add_argument("--phase", choices=PHASES, required=True, help="校验阶段")
    parser.add_argument(
        "--archive-target",
        type=Path,
        help="Archive 阶段将要创建的目标目录",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser


def _print_result(result: ValidationResult, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return
    if result.ok:
        print(f"PASS: {result.phase} ({result.change_type})")
        return
    for finding in result.findings:
        print(
            f"ERROR [{finding.rule_id}] {finding.path}:{finding.line} "
            f"{finding.message}\n    修复提示：{finding.hint}"
        )
    print(f"FAIL: {len(result.findings)} 个确定性违规")


def _configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line validator and return its process exit code."""
    _configure_output_encoding()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = validate_change(
            args.repo,
            args.change,
            args.phase,
            args.archive_target,
        )
    except InvocationError as error:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "rule_id": "INVOCATION_ERROR",
                            "path": "",
                            "line": 0,
                            "message": str(error),
                            "hint": "检查 --repo、--change 和 --phase 参数。",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # pylint: disable=broad-exception-caught
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "rule_id": "VALIDATOR_ERROR",
                            "path": "",
                            "line": 0,
                            "message": str(error),
                            "hint": "报告校验器异常并附上复现命令。",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"ERROR: 校验器异常：{error}", file=sys.stderr)
        return 2

    _print_result(result, args.json)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
