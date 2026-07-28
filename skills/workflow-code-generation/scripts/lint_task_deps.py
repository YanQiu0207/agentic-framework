"""Lint tasks.md 的依赖关系，提示并行分波的潜在冲突。

按 task_planning_guide.md 的 tasks.md 格式解析每个任务的 `文件` 与
`depends_on` 字段，检查：

- **dangling 依赖**：`depends_on` 指向不存在的任务号（ERROR）。
- **循环依赖**：依赖图存在环，违反 DAG 约定（ERROR）。
- **并行冲突**：两个任务改同一文件、却无依赖关系——会被分到同一波并行执行，
  worktree 合并时冲突或顺序错（WARN，提示确认是否补 `depends_on`）。
- **必填字段**：每个任务须有 `review_profile`（lightweight / standard / strict）、
  `context_files`、`verification`、`artifacts`、`状态`（合法值），缺失或非法（ERROR）。

只查「文件重叠 + 无依赖」这一客观信号；是否真要串行由人判断（重叠可能是有意且已处理）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_FRAMEWORK_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_FRAMEWORK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_FRAMEWORK_SCRIPTS))
import governance_profile
import task_ast

TASK_HEADER = re.compile(r"^###\s*任务\s*(\d+)\s*[:：]", re.MULTILINE)
BACKTICK = re.compile(r"`([^`]+)`")
CHECKBOX = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]")
STATE_FIELD = re.compile(r"^\s*-\s*状态\s*[:：]\s*(?P<value>.*)$")
# 任务头标记里代表「已完成」的取值；其余取值一律按未完成处理。
COMPLETED_MARKS = {"x", "completed", "complete", "done", "已完成", "完成"}

REVIEW_PROFILES = {"lightweight", "standard", "strict"}
# Review Profile 的两种写法归一为同一逻辑字段（change 2035 Task 6）：匹配
# 规则仅大小写不敏感、`_` 与空格等价；取值集合不变。同一任务两种写法取值
# 不同则报错，不静默取其一。
REVIEW_PROFILE_FIELD_NAMES = ("review_profile", "Review Profile")
TASK_STATES = ("未开始", "进行中", "完成", "需人工", "阻塞")
# 状态取值归一（change 2035 Task 7）：读侧接受 Production 超集取值并映射回
# 规范值；英文别名大小写不敏感（与 Production `_state_field_kind` 的归类
# 对齐）。只放宽读侧校验，写侧仍只产出五个规范值。
_STATE_CANONICAL = {
    "已完成": "完成",
    "completed": "完成",
    "complete": "完成",
    "done": "完成",
    "x": "完成",
    "pending": "未开始",
    "in progress": "进行中",
    "in-progress": "进行中",
    "blocked": "阻塞",
}
REQUIRED_FIELDS = ("review_profile", "context_files", "verification", "artifacts", "状态")


def field(body: str, name: str) -> str:
    """取 `- <name>: <值>` 那一行的值，找不到返回空串。"""
    match = re.search(r"^\s*-\s*" + name + r"\s*[:：]\s*(.*)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def has_field(body: str, name: str) -> bool:
    """Return whether a task field is declared, even when its value is empty."""
    return re.search(
        r"^\s*-\s*" + name + r"\s*[:：]", body, re.MULTILINE
    ) is not None


def parse_deps(
    dep_field_raw: str | None, dep_field_name: str | None
) -> tuple[set[int], bool]:
    """把 AST 提供的依赖字段原始值解析为依赖集合，并返回字段是否存在。

    严格式（change 2037）：值必须整体符合 `task_ast.DEP_VALUE_RE`（空值
    `[]`／`无`／`none`，或 `Task N`／`任务 N` 引用列表），从中提取编号。
    不合规值产出空集合——报错由 `dep_format_error` 负责，此处不再用
    `re.findall(r"\\d+")` 静默抓取数字。depends_on 与遗留「依赖」的取舍
    在 AST 层完成（depends_on 优先）。
    """
    field_exists = dep_field_name is not None
    if not dep_field_raw or task_ast.DEP_VALUE_RE.fullmatch(dep_field_raw) is None:
        return set(), field_exists
    if dep_field_raw == "[]" or dep_field_raw.casefold() in {"无", "none"}:
        return set(), field_exists
    return {
        int(n) for n in task_ast.DEP_REFERENCE_RE.findall(dep_field_raw)
    }, field_exists


def dep_format_error(
    tid: int, dep_field_raw: str | None, dep_field_name: str | None
) -> str | None:
    """依赖字段值不合规时返回错误消息，合规或字段缺失时返回 None。"""
    if dep_field_name is None or not dep_field_raw:
        return None
    if task_ast.DEP_VALUE_RE.fullmatch(dep_field_raw) is None:
        return (
            f"任务 {tid} 的 {dep_field_name} `{dep_field_raw}` 不合规"
            f"（合法写法：`[]` / `无` / `none` / `Task N` 或 `任务 N` 列表）"
        )
    return None


def parse_tasks(text: str) -> dict[int, dict]:
    """解析 tasks.md，返回 {task_id: {"files": set, "deps": set}}。"""
    doc = task_ast.parse(text)
    if doc.duplicate_ids:
        raise ValueError(f"重复任务 ID: {doc.duplicate_ids[0]}")
    tasks: dict[int, dict] = {}
    for node in doc.tasks:
        deps, has_dep_field = parse_deps(node.dep_field_raw, node.dep_field_name)
        tasks[node.number] = {
            "files": {p.strip() for p in BACKTICK.findall(field(node.body, "文件"))},
            "deps": deps,
            "has_dep_field": has_dep_field,
            "body": node.body,
            "dep_error": dep_format_error(
                node.number, node.dep_field_raw, node.dep_field_name
            ),
            "review_profile_fields": task_ast.find_fields(
                node.body.splitlines(), REVIEW_PROFILE_FIELD_NAMES
            ),
        }
    return tasks


def state_prefix(value: str) -> str | None:
    """返回 `状态` 字段值中匹配到的原始状态前缀（含别名原文），无则 None。

    原因抽取须按本函数返回的原始前缀长度切片——归一后规范值与原始值
    长度不再对应（如 `已完成` → `完成`）。
    """
    for state in TASK_STATES:
        if value.startswith(state):
            return state
    normalized = value.casefold()
    for alias in _STATE_CANONICAL:
        if normalized.startswith(alias):
            return value[: len(alias)]
    return None


def parse_state(value: str) -> str | None:
    """从 `状态` 字段值里取合法状态词（允许后跟原因等附注），无则返回 None。

    接受 Production 超集取值并归一为规范值（`_STATE_CANONICAL`）。
    """
    prefix = state_prefix(value)
    if prefix is None:
        return None
    if prefix in TASK_STATES:
        return prefix
    return _STATE_CANONICAL[prefix.casefold()]


def field_errors(tasks: dict[int, dict], governance: str | None = None) -> list[str]:
    """校验每个任务的必填字段与合法值。

    `governance` 为当前治理 Profile（`production` / `tooling`）；给出时
    `review_profile` 低于 Profile 下限报错（change 2041）。未给出时不做
    下限判定——非门禁调用方（如 run_journal）不传。
    """
    errors: list[str] = []
    for tid, info in sorted(tasks.items()):
        body = info["body"]
        profile_fields = info["review_profile_fields"]
        for name in REQUIRED_FIELDS:
            if name == "review_profile":
                if not profile_fields:
                    errors.append(f"任务 {tid} 缺少 review_profile 字段")
                continue
            if not has_field(body, name):
                errors.append(f"任务 {tid} 缺少 {name} 字段")
        if profile_fields:
            values = {value for _name, value, _offset in profile_fields}
            if len(values) > 1:
                shown = "、".join(f"`{value}`" for value in sorted(values))
                errors.append(
                    f"任务 {tid} 声明了多个取值不同的 review_profile（{shown}），"
                    f"无法判定真实档位"
                )
            else:
                profile = profile_fields[0][1]
                if profile not in REVIEW_PROFILES:
                    errors.append(
                        f"任务 {tid} 的 review_profile `{profile}` 不合法"
                        f"（lightweight / standard / strict）"
                    )
                elif governance is not None and governance_profile.below_floor(
                    profile, governance
                ):
                    errors.append(
                        f"任务 {tid} 的 review_profile 为 lightweight，"
                        f"低于 {governance} 下限 "
                        f"{governance_profile.review_profile_floor(governance)}"
                    )
        if has_field(body, "状态"):
            status_value = field(body, "状态")
            if parse_state(status_value) is None:
                errors.append(
                    f"任务 {tid} 的 状态 `{status_value}` 不含合法值"
                    f"（{' / '.join(TASK_STATES)}）"
                )
    return errors


def state_consistency_errors(text: str) -> list[str]:
    """校验状态字段、任务头标记与任务块复选框三向一致。

    `完成` 要求任务头标完成且区域内无未勾选复选框；其余状态要求任务头
    不标完成（未勾选复选框正是「哪些验收项没达成」的记录，不作约束）。
    """
    doc = task_ast.parse(text)
    errors: list[str] = []
    for node in doc.tasks:
        tid = node.number
        # 元数据区终止沿用本侧历史规则：任意级别标题（含孤立空标题行）。
        region = task_ast.metadata_region(
            doc.lines, node.line, node.end_line, stop_re=task_ast.ANY_HEADING_RE
        )
        states = [
            found.group("value").strip()
            for line in region
            if (found := STATE_FIELD.match(line))
        ]
        if not states:
            continue  # 缺失由 field_errors 的必填字段校验负责
        if len(states) > 1:
            # 不能交给 field_errors：`field()` 用 re.search 只读第一行，重复
            # 声明在那里是静默的。多个状态本身就是「哪个才算真」的矛盾。
            errors.append(
                f"任务 {tid} 声明了 {len(states)} 个 状态 字段"
                f"（{'、'.join(f'`{s}`' for s in states)}），无法判定真实状态"
            )
            continue
        state = parse_state(states[0])
        if state is None:
            continue  # 取值非法由 field_errors 判定
        mark = node.status_raw
        # 标记整体缺失（`### 任务 1：实现`）视为「未声明」而非矛盾：没有
        # 完成信号可与状态字段对立。复选框判定不受影响，仍照常执行。
        mark_completed = mark is not None and mark.strip().casefold() in COMPLETED_MARKS
        unchecked = sum(
            1
            for line in region
            if (box := CHECKBOX.match(line)) and box.group("mark") == " "
        )
        if state == "完成":
            if mark is not None and not mark_completed:
                errors.append(
                    f"任务 {tid} 状态为 `完成` 但任务头标记为 `[{mark}]`，"
                    f"两处状态矛盾（任务头应标 `[x]`）"
                )
            if unchecked:
                errors.append(
                    f"任务 {tid} 状态为 `完成` 但区域内有 {unchecked} 个未勾选复选框，"
                    f"两处状态矛盾（完成验收项与子任务后勾选，或按实际情况改状态）"
                )
        elif mark_completed:
            errors.append(
                f"任务 {tid} 任务头标记为 `[{mark}]`（完成）但状态为 `{state}`，"
                f"两处状态矛盾（非完成态时任务头不得标完成）"
            )
    return errors


def reachable(tasks: dict[int, dict]) -> dict[int, set[int]]:
    """每个任务经依赖可达的任务集合（传递闭包）。

    每个源点独立做一次 DFS（不跨源点 memo），即使存在环也能算出完整可达集，
    从而把环里的每个成员都标出来。
    """
    reach: dict[int, set[int]] = {}
    for tid in tasks:
        seen: set[int] = set()
        stack = [d for d in tasks[tid]["deps"] if d in tasks]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(d for d in tasks[node]["deps"] if d in tasks)
        reach[tid] = seen
    return reach


def _is_archived_source(source: str) -> bool:
    """判定来源路径是否位于 openspec/changes/archive/ 下（codex 审核 finding 2）。

    不用任意 `archive` 目录段——那会把工作区恰好含 `archive` 目录的活跃
    变更误判为归档，门禁静默返回 0。只认 `openspec/changes/archive` 段，
    且大小写不敏感（Windows 路径大小写不敏感）。
    """
    parts = tuple(p.casefold() for p in Path(source).resolve().parts)
    for i in range(len(parts) - 2):
        if parts[i] == "openspec" and parts[i + 1] == "changes" and parts[i + 2] == "archive":
            return True
    return False


def lint_report(text: str, source: str, governance: str | None = None) -> dict:
    """对 tasks.md 文本跑全部校验，返回结构化报告（change 2037 §6.2 统一合同）。

    规则对所有输入一致；违规仅按来源路径分类：路径含 `archive` 目录段的
    归入 `legacy`（遗留违规，记录不拦截），其余归入 `active`。任何调用方
    对同一输入得到同一份结构化判定，不存在「跳过归档」这一选项。
    `governance` 给出时启用 review_profile 的 Profile 下限判定（change 2041）。
    """
    tasks = parse_tasks(text)
    errors: list[str] = []
    warnings: list[str] = []

    # dangling 依赖与依赖值格式
    for tid, info in sorted(tasks.items()):
        if not info["has_dep_field"]:
            errors.append(f"任务 {tid} 缺少 depends_on 字段")
        if info["dep_error"]:
            errors.append(info["dep_error"])
        for dep in sorted(info["deps"]):
            if dep not in tasks:
                errors.append(f"任务 {tid} 依赖不存在的任务 {dep}")

    # 必填字段与合法值
    errors.extend(field_errors(tasks, governance))

    reach = reachable(tasks)

    # 循环依赖
    for tid in sorted(tasks):
        if tid in reach[tid]:
            errors.append(f"任务 {tid} 存在循环依赖（依赖链回到自身）")

    # 并行冲突：文件重叠但互不可达
    ids = sorted(tasks)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = tasks[a]["files"] & tasks[b]["files"]
            if not shared:
                continue
            if b in reach[a] or a in reach[b]:
                continue  # 有依赖关系 → 串行，安全
            files = "、".join(f"`{f}`" for f in sorted(shared))
            warnings.append(
                f"任务 {a} 与 任务 {b} 都改 {files}，但无依赖关系（会并行）"
                f"→ 确认是否需要加 depends_on"
            )

    legacy = _is_archived_source(source)
    return {
        "tasks": len(tasks),
        "active": {
            "errors": [] if legacy else errors,
            "warnings": [] if legacy else warnings,
        },
        "legacy": {
            "errors": errors if legacy else [],
            "warnings": warnings if legacy else [],
        },
    }


def main(argv: list[str]) -> int:
    """解析 tasks.md 并报告依赖问题。"""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台避免中文乱码

    parser = argparse.ArgumentParser(description="校验 tasks.md 的依赖关系")
    parser.add_argument("tasks_md", type=Path, help="tasks.md 路径")
    parser.add_argument(
        "--state-consistency",
        action="store_true",
        help="只校验状态字段、任务头标记与复选框三向一致（归档前前置检查）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出结构化报告（active／legacy 分类），供机器消费",
    )
    parser.add_argument(
        "--governance-profile",
        choices=("production", "tooling"),
        help="显式指定治理 Profile（覆盖 manifest 读取）",
    )
    args = parser.parse_args(argv)
    if not args.tasks_md.is_file():
        print(f"error: 找不到 {args.tasks_md}", file=sys.stderr)
        return 2

    text = args.tasks_md.read_text(encoding="utf-8-sig", errors="replace")
    try:
        if args.state_consistency:
            consistency = state_consistency_errors(text)
            for message in consistency:
                print(f"ERROR  {message}")
            tasks = parse_tasks(text)
            print(f"\ntasks={len(tasks)} | state_consistency_errors={len(consistency)}")
            return 1 if consistency else 0
        tasks_for_scan = parse_tasks(text)
        # 惰性读取：只在有任务声明 lightweight 时才需要 Profile 判定下限
        needs_profile = any(
            value == "lightweight"
            for info in tasks_for_scan.values()
            for _name, value, _offset in info["review_profile_fields"]
        )
        governance = args.governance_profile
        if needs_profile and governance is None:
            try:
                governance = governance_profile.read_profile(args.tasks_md.parent)
            except governance_profile.GovernanceProfileError as error:
                print(f"error: {error}", file=sys.stderr)
                return 2
        report = lint_report(text, str(args.tasks_md), governance)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not report["tasks"]:
        print("error: 未解析到任何任务（检查 tasks.md 是否符合 `### 任务 N:` 格式）", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for message in report["active"]["errors"]:
            print(f"ERROR  {message}")
        for message in report["active"]["warnings"]:
            print(f"WARN   {message}")
        for message in report["legacy"]["errors"]:
            print(f"LEGACY {message}（归档遗留违规，记录不拦截）")
        for message in report["legacy"]["warnings"]:
            print(f"LEGACY {message}（归档遗留警告，记录不拦截）")
        active_errors = len(report["active"]["errors"])
        active_warnings = len(report["active"]["warnings"])
        legacy_count = len(report["legacy"]["errors"]) + len(
            report["legacy"]["warnings"]
        )
        print(
            f"\ntasks={report['tasks']} | errors={active_errors} "
            f"warnings={active_warnings} legacy={legacy_count}"
        )
    return (
        1
        if report["active"]["errors"] or report["active"]["warnings"]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
