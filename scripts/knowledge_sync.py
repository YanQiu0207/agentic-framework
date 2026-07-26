"""共享的 Delta 反推与知识同步表解析（change 2040 Task 2）。

只做解析与反推，不含 OPSX 编号、错误消息或退出码；判定属于调用方。
消费方：`scripts/validate_change.py`（Production 归档知识核对）与
`skills/workflow-code-generation/scripts/check_delivery.py`（Tooling 知识门）。
"""

from __future__ import annotations

import re
from pathlib import Path

KNOWLEDGE_ROOTS = {"business", "frontend", "backend", "common"}
COMPLETED_SYNC_STATUSES = {"completed", "complete", "done", "pass", "已完成"}

_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")


def _normalized_title(title: str) -> str:
    title = re.sub(r"^\d+(?:\.\d+)*[.、]?\s*", "", title.strip())
    title = re.sub(r"\s*[（(][^）)]*[）)]\s*$", "", title)
    return title.strip().casefold()


def section_lines(lines: list[str], title: str) -> tuple[list[str], int]:
    """Return the body and 1-based source line of a Markdown section."""
    normalized = _normalized_title(title)
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if not match or _normalized_title(match.group("title")) != normalized:
            continue
        level = len(match.group("marks"))
        body: list[str] = []
        for content_line in lines[index + 1 :]:
            next_heading = _HEADING_RE.match(content_line)
            if next_heading and len(next_heading.group("marks")) <= level:
                break
            body.append(content_line)
        return body, index + 1
    return [], 1


def delta_map(change: Path) -> tuple[dict[str, str], list[Path]]:
    """从 Change 的 ``specs/`` 反推 source→长期目标映射。

    返回 ``(mappings, invalid)``：mappings 是 Delta 相对 Change 的路径到
    `openspec/specs/` 长期目标的映射；invalid 是存在但不在四个知识根下、
    无法映射的 Delta 路径（如何裁决由调用方定）。
    """
    mappings: dict[str, str] = {}
    invalid: list[Path] = []
    specs_root = change / "specs"
    if not specs_root.is_dir():
        return mappings, invalid
    for delta in specs_root.rglob("*.md"):
        if not delta.is_file() or not delta.read_text(encoding="utf-8-sig").strip():
            continue
        relative = delta.relative_to(specs_root)
        if len(relative.parts) < 2 or relative.parts[0] not in KNOWLEDGE_ROOTS:
            invalid.append(delta)
            continue
        source = delta.relative_to(change).as_posix()
        mappings[source] = (Path("openspec/specs") / relative).as_posix()
    return mappings, invalid


def sync_rows(lines: list[str]) -> list[tuple[int, list[str]]]:
    """解析 tasks.md 的「知识同步」表，返回 ``(行号, 单元格列表)``。"""
    body, heading_line = section_lines(lines, "知识同步")
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
