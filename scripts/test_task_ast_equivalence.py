"""Golden 基线：冻结两侧 tasks.md 解析器的当前行为（change 2035 Task 1）。

两层语料：

- 合成 fixtures（``scripts/tests/fixtures/task_ast/*.md``）：不可变语料，
  本文件以 pytest 永久回归——重跑解析器，输出须与 ``golden.json`` 逐字节相同。
- 全仓库 ``openspec/changes/**/tasks.md``（活跃与归档，不抽样）：活体语料，
  随 change 推进而变化，不能做冻结断言。只在 change 2035 交付期内以
  ``--repo-corpus`` / ``--gate-snapshot`` 各抓一次前后快照，对照证据存入
  ``openspec/changes/2035-common-task-ast/``。

记录内容（design.md §5）：

- Production 侧 ``_parse_tasks``：``(number, status, description, line,
  end_line, dependencies)``。
- Tooling 侧 ``parse_tasks``：``(tid, sorted(deps), has_dep_field, len(body))``。
- 解析抛异常的输入记录异常类型与消息，不跳过。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = (
    REPO_ROOT
    / "skills"
    / "workflow-code-generation"
    / "scripts"
)
for _path in (str(REPO_ROOT / "scripts"), str(SKILL_SCRIPTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import lint_task_deps
import validate_change

FIXTURES = Path(__file__).resolve().parent / "tests" / "fixtures" / "task_ast"
GOLDEN_PATH = FIXTURES / "golden.json"


def _production_record(tasks_path: Path) -> dict:
    """记录 Production 侧解析输出；异常转为类型与消息。"""
    try:
        tasks, _lines = validate_change._parse_tasks(tasks_path)
    except Exception as error:  # 异常本身是基线的一部分
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "tasks": [
            [
                task.number,
                task.status,
                task.description,
                task.line,
                task.end_line,
                list(task.dependencies),
            ]
            for task in tasks
        ]
    }


def _tooling_record(tasks_path: Path) -> dict:
    """记录 Tooling 侧解析输出；读取方式与 lint_task_deps.main 一致。"""
    text = tasks_path.read_text(encoding="utf-8-sig", errors="replace")
    try:
        tasks = lint_task_deps.parse_tasks(text)
    except Exception as error:  # 异常本身是基线的一部分（如重复任务 ID）
        return {"error": f"{type(error).__name__}: {error}"}
    return {
        "tasks": [
            [tid, sorted(info["deps"]), info["has_dep_field"], len(info["body"])]
            for tid, info in sorted(tasks.items())
        ]
    }


def generate_baseline(inputs: dict[str, Path]) -> dict:
    """对一组 ``{标签: tasks.md 路径}`` 生成双轨解析基线。"""
    labels = sorted(inputs)
    return {
        "inputs": labels,
        "production": {label: _production_record(inputs[label]) for label in labels},
        "tooling": {label: _tooling_record(inputs[label]) for label in labels},
    }


def _dump(data: dict) -> str:
    """规范化 JSON 序列化：排序键、UTF-8、末尾换行，保证逐字节稳定。"""
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def fixture_inputs() -> dict[str, Path]:
    return {path.name: path for path in sorted(FIXTURES.glob("*.md"))}


def repo_corpus_inputs() -> dict[str, Path]:
    """全仓库 tasks.md（活跃与归档，不抽样），键为仓库相对路径。"""
    root = REPO_ROOT / "openspec" / "changes"
    return {
        path.relative_to(REPO_ROOT).as_posix(): path
        for path in sorted(root.rglob("tasks.md"))
    }


class TaskAstGoldenTest(unittest.TestCase):
    """合成 fixtures 的 golden 回归：迁移前后输出必须逐字节相同。"""

    def test_golden_baseline_reproduced(self) -> None:
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        current = generate_baseline(fixture_inputs())
        self.assertEqual(
            _dump(golden),
            _dump(current),
            "解析输出与 golden 基线不一致——零行为变更被破坏",
        )

    def test_baseline_generation_is_deterministic(self) -> None:
        inputs = fixture_inputs()
        self.assertEqual(
            _dump(generate_baseline(inputs)),
            _dump(generate_baseline(inputs)),
            "连续两次生成基线输出不一致（存在字典序或路径序不稳定）",
        )


def _write_repo_corpus_snapshot(out_path: Path) -> None:
    out_path.write_text(
        _dump(generate_baseline(repo_corpus_inputs())), encoding="utf-8"
    )
    print(f"已写入仓库语料快照：{out_path}")


def _change_dirs() -> list[Path]:
    """全部活跃与归档 Change 目录（以 proposal.md 为准），排序保证稳定。"""
    root = REPO_ROOT / "openspec" / "changes"
    dirs = [
        path.parent
        for path in sorted(root.rglob("proposal.md"))
    ]
    return dirs


def _gate_snapshot(out_path: Path) -> None:
    """对全部 Change 跑 validate_change 的 plan/delivery 阶段并记录结果。

    记录退出码、错误编号排序集合与错误数（design.md §5 第 4 步）；子进程
    方式与真实门禁调用一致，置 PYTHONUTF8=1 与 verify.py 环境对齐。
    """
    import os

    env = dict(os.environ, PYTHONUTF8="1")
    snapshot: dict[str, dict] = {}
    for change in _change_dirs():
        relative = change.relative_to(REPO_ROOT).as_posix()
        entry: dict[str, dict] = {}
        for phase in ("plan", "delivery", "archive"):
            command = [
                sys.executable,
                str(REPO_ROOT / "scripts" / "validate_change.py"),
                "--repo",
                str(REPO_ROOT),
                "--change",
                str(change),
                "--phase",
                phase,
                "--json",
            ]
            if phase == "archive":
                command.extend(
                    (
                        "--archive-target",
                        str(
                            REPO_ROOT
                            / "openspec"
                            / "changes"
                            / "archive"
                            / f"probe-{change.name}"
                        ),
                    )
                )
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
            )
            payload = json.loads(completed.stdout)
            findings = payload.get("errors") or []
            error = payload.get("error")
            entry[phase] = {
                "exit": completed.returncode,
                "count": len(findings),
                "rules": sorted({item["rule_id"] for item in findings}),
                "error": error["rule_id"] if error else None,
            }
        snapshot[relative] = entry
        print(f"  {relative}: {entry}")
    out_path.write_text(_dump(snapshot), encoding="utf-8")
    print(f"已写入门禁快照：{out_path}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-golden",
        action="store_true",
        help="以当前解析器重生成 fixtures 的 golden.json（仅 Task 1 冻结时使用）",
    )
    parser.add_argument(
        "--repo-corpus",
        type=Path,
        metavar="OUT",
        help="对全仓库 tasks.md 生成一次性解析快照写入 OUT",
    )
    parser.add_argument(
        "--gate-snapshot",
        type=Path,
        metavar="OUT",
        help="对全部 Change 跑 plan/delivery 门禁并把结果快照写入 OUT",
    )
    args = parser.parse_args(argv)
    if args.write_golden:
        GOLDEN_PATH.write_text(
            _dump(generate_baseline(fixture_inputs())), encoding="utf-8"
        )
        print(f"已写入 golden 基线：{GOLDEN_PATH}")
    if args.repo_corpus:
        _write_repo_corpus_snapshot(args.repo_corpus)
    if args.gate_snapshot:
        _gate_snapshot(args.gate_snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
