#!/usr/bin/env python3
"""Validate the deterministic structure of an OPSX change directory."""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import re
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
SECTION_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]")
CHANGE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
QUICK_STATUS_RE = re.compile(
    r"^\s*(?:\*\*)?状态(?:\*\*)?\s*[:：]\s*Quick\s+Draft\s*$",
    re.IGNORECASE,
)


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


def _nonempty_file(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and bool(_read_text(path).strip())


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


def _completed_status(status: str) -> bool:
    return status.casefold() in {"x", "completed", "complete", "done"}


def _review_status(lines: Sequence[str]) -> tuple[str | None, int]:
    for line_number, line in enumerate(lines, start=1):
        match = REVIEW_RE.search(line)
        if match:
            return match.group(1).upper(), line_number
    return None, 1


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
    central_specs = repo / "openspec" / "specs"
    if central_specs.exists():
        findings.append(
            _finding(
                "OPSX001",
                central_specs,
                repo,
                1,
                "禁止创建 openspec/specs/ 中央规范库。",
                "删除中央规范库；当前实现必须从代码读取。",
            )
        )

    symlink = next((path for path in change.rglob("*") if path.is_symlink()), None)
    if symlink is not None:
        findings.append(
            _finding(
                "OPSX004",
                symlink,
                repo,
                1,
                "Change 目录不得包含符号链接。",
                "将符号链接替换为 Change 目录内的普通文件或目录。",
            )
        )

    expected_parent = (repo / "openspec" / "changes").resolve()
    if change.parent != expected_parent:
        findings.append(
            _finding(
                "OPSX002",
                change,
                repo,
                1,
                "Change 目录必须直接位于 openspec/changes/。",
                "通过 --change openspec/changes/<change-name> 指定活跃变更。",
            )
        )
    if not CHANGE_NAME_RE.fullmatch(change.name):
        findings.append(
            _finding(
                "OPSX003",
                change,
                repo,
                1,
                "Change 名称不符合小写动词-名词 kebab-case 格式。",
                "使用至少两个小写英文片段，例如 add-validation。",
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
            spec_files = list((change / "specs").glob("*/spec.md"))
            if not any(_nonempty_file(path) for path in spec_files):
                findings.append(
                    _finding(
                        "OPSX018",
                        change / "specs",
                        repo,
                        1,
                        "Standard 路径至少需要一个非空 specs/<capability>/spec.md。",
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

    _, lines = _parse_tasks(tasks_path)
    review_status, review_line = _review_status(lines)
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
    change = change if change.is_absolute() else repo / change
    if change.is_symlink():
        raise InvocationError("Change 目录不得是符号链接。")
    change = change.resolve()
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
    findings.extend(_validate_plan(repo, change, change_type))
    if phase == "delivery":
        findings.extend(_validate_delivery(repo, change, "PENDING"))
    elif phase == "archive":
        findings.extend(_validate_delivery(repo, change, "PASS"))
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
        name_match = re.fullmatch(
            rf"(?P<date>\d{{4}}-\d{{2}}-\d{{2}})-{re.escape(change.name)}",
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
                    "Archive 目录名不符合 YYYY-MM-DD-<change-name>。",
                    "按日期前缀和原 Change 名称生成归档目录。",
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
