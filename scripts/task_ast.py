"""只读公共 Task AST（change 2035）。

拥有四件事（两个解析器当前重复实现的部分）：

1. 任务边界切分：从整份文本定位每个 `### 任务 N` 块的起止。
2. 任务头拆解：编号、状态括号内原文、括号后的描述。
3. 元数据区域切分：任务头下一行起，到下一个标题前，剔除代码围栏内容。
4. 字段定位：`- <名称>: <值>` 的定位与取值，区分「不存在」与「存在但为空」。

不拥有任何裁决：OPSX 编号、错误消息、退出码、状态取值合法性、依赖串
格式判定都留给调用方。本模块不导入 validate_change / lint_task_deps，
无循环依赖。
"""

from __future__ import annotations

import dataclasses
import re

# 任务头核心前缀：取两轨识别集合的并集（Tooling 的宽松间距 `\s*`）。
# Production 委托层凭 strict_header 收紧回 `###\s+任务\s+` 的严格间距。
_HEADER_CORE_RE = re.compile(r"^###\s*任务\s*(?P<number>\d+)\s*[:：]")
# 核心前缀之后：可选状态括号 + 描述。括号不闭合（如 `[abc`）时整体视为描述。
_HEADER_REST_RE = re.compile(r"^(?:\s*\[(?P<status>[^]]*)\])?(?P<description>.*)$")
# Production `TASK_HEADER_RE` 的间距要求：`###` 与「任务」之后都必须有空白。
_HEADER_STRICT_RE = re.compile(r"^###\s+任务\s+")

# 元数据区域的两种标题终止规则。分歧点：孤立 `### ` 空标题行（井号后仅一个
# 空白字符）命中 ANY_HEADING_RE（`\s+` 即可），不命中 SECTION_HEADING_RE
# （要求存在标题字符——一个以上的空白也能充当，与 Production `SECTION_RE`
# 的匹配语义一致）。两个调用方各保留其历史规则，见 metadata_region 的 stop_re。
ANY_HEADING_RE = re.compile(r"^#{1,6}\s+")
SECTION_HEADING_RE = re.compile(r"^#{1,6}\s+.+?\s*$")

# 元数据区字段行：`- <名称>: <值>`。名称不含冒号；半角与全角冒号都接受。
_FIELD_LINE_RE = re.compile(r"^\s*-\s*(?P<name>[^:：]+?)\s*[:：]\s*(?P<value>.*)$")

# 依赖字段的两个候选名：depends_on 优先于遗留「依赖」（Tooling 的既有偏好）。
_DEP_FIELD_NAMES = ("depends_on", "依赖")


@dataclasses.dataclass(frozen=True)
class TaskNode:
    """一个 `### 任务 N` 块的解析结果。

    坐标系同时提供两套（design §2.1）：1-based 行号区间（Production 下游
    按行操作）与字符 offset 区间（Tooling 下游在 body 上跑正则），不变式
    为两者覆盖同一任务。
    """

    number: int
    status_raw: str | None  # 括号整体缺失为 None；空括号为 ""；否则括号内原文
    description: str  # 括号后（无括号则冒号后）剩余文本，已 strip
    line: int  # 任务头行号，1-based
    end_line: int  # 下一任务头行号（末任务为 len(lines)+1），1-based 半开
    body_start: int  # 任务头核心前缀（至冒号）结束处的字符 offset
    body_end: int  # 下一任务头起始处字符 offset（末任务为 len(text)）
    body: str  # text[body_start:body_end]
    strict_header: bool  # 任务头是否满足 `###\s+任务\s+` 严格间距
    dep_field_name: str | None  # 实际出现的依赖字段名：depends_on 或 依赖
    dep_field_raw: str | None  # 依赖字段的原始值（已 strip，未解析）


@dataclasses.dataclass(frozen=True)
class TaskDocument:
    """整份 tasks.md 的解析结果。"""

    tasks: list[TaskNode]  # 按出现顺序
    lines: list[str]  # text.splitlines()
    duplicate_ids: list[int]  # 重复出现的编号，按首次重复顺序


def normalize_field_name(name: str) -> str:
    """字段名归一：仅大小写不敏感、`_` 与空格等价（连续空白/下划线折叠）。

    不引入前缀匹配、缩写、模糊匹配或标点归一（design §7.2）。
    """
    return re.sub(r"[\s_]+", "_", name.strip().casefold())


def find_fields(
    region_lines: list[str] | tuple[str, ...], names: tuple[str, ...] | list[str] | set[str]
) -> list[tuple[str, str, int]]:
    """在元数据区内定位别名组字段，返回全部匹配 ``(字段名, 值, 区行号)``。

    字段名按 normalize_field_name 归一后比较；值已 strip。空列表表示字段
    不存在；值的空串表示字段存在但为空。
    """
    wanted = {normalize_field_name(name) for name in names}
    found: list[tuple[str, str, int]] = []
    for offset, line in enumerate(region_lines):
        match = _FIELD_LINE_RE.match(line)
        if match and normalize_field_name(match.group("name")) in wanted:
            found.append(
                (match.group("name").strip(), match.group("value").strip(), offset)
            )
    return found


def find_field(
    region_lines: list[str] | tuple[str, ...], names: tuple[str, ...] | list[str] | set[str]
) -> tuple[str, str, int] | None:
    """find_fields 的首个匹配；字段不存在时返回 None。"""
    found = find_fields(region_lines, names)
    return found[0] if found else None


def metadata_region(
    lines: list[str] | tuple[str, ...],
    line: int,
    end_line: int,
    *,
    stop_re: re.Pattern[str] = ANY_HEADING_RE,
) -> list[str]:
    """任务头下一行起、到 stop_re 命中的标题前的元数据区，剔除围栏内容。

    ``line`` / ``end_line`` 是与 TaskNode 一致的 1-based 半开区间。围栏
    标记行本身也被剔除；区域不越过 end_line（下一个任务头总是标题，两种
    stop_re 都会在此终止）。
    """
    region: list[str] = []
    fence: str | None = None
    for content_line in lines[line : end_line - 1]:
        marker = content_line.lstrip()[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker
            continue
        if fence is not None:
            continue
        if stop_re.match(content_line):
            break
        region.append(content_line)
    return region


def _dep_field(region_lines: list[str]) -> tuple[str | None, str | None]:
    """定位依赖字段：depends_on 优先，缺席时退到遗留「依赖」。

    匹配大小写不敏感（与 Production `DEPENDENCY_RE` 的 IGNORECASE 对齐，
    防止大小写变体绕过依赖校验）。
    """
    for candidate in _DEP_FIELD_NAMES:
        found = find_field(region_lines, (candidate,))
        if found is not None:
            return candidate, found[1]
    return None, None


def parse(text: str) -> TaskDocument:
    """把 tasks.md 文本解析为 TaskDocument。重复任务 ID 只记录不抛异常。"""
    lines = text.splitlines()
    headers: list[tuple[re.Match[str], re.Match[str], int, int]] = []
    offset = 0
    for line_number, content_line in enumerate(lines, start=1):
        core = _HEADER_CORE_RE.match(content_line)
        if core:
            rest = _HEADER_REST_RE.match(content_line[core.end() :])
            headers.append((core, rest, line_number, offset))
        offset += len(content_line) + 1  # splitlines 后每行以 "\n" 重新计位

    tasks: list[TaskNode] = []
    seen: set[int] = set()
    duplicate_ids: list[int] = []
    for index, (core, rest, line_number, line_start) in enumerate(headers):
        number = int(core.group("number"))
        if number in seen and number not in duplicate_ids:
            duplicate_ids.append(number)
        seen.add(number)
        if index + 1 < len(headers):
            end_line = headers[index + 1][2]
            body_end = headers[index + 1][3]
        else:
            end_line = len(lines) + 1
            body_end = len(text)
        body_start = line_start + core.end()
        region = metadata_region(lines, line_number, end_line)
        dep_name, dep_raw = _dep_field(region)
        tasks.append(
            TaskNode(
                number=number,
                status_raw=rest.group("status"),
                description=rest.group("description").strip(),
                line=line_number,
                end_line=end_line,
                body_start=body_start,
                body_end=body_end,
                body=text[body_start:body_end],
                strict_header=_HEADER_STRICT_RE.match(lines[line_number - 1])
                is not None,
                dep_field_name=dep_name,
                dep_field_raw=dep_raw,
            )
        )
    return TaskDocument(tasks=tasks, lines=lines, duplicate_ids=duplicate_ids)
