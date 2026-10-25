"""Offline experiment snapshots and externally adjudicated Review evaluation.

No model, submitted code, or external command is executed by this module.
Digests detect accidental drift, not malicious rewriting by the host owner.
"""

import argparse
import hashlib
import json
import math
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Optional, Sequence

CATEGORIES = ("business", "architecture", "conventions")
SEVERITIES = ("P0", "P1", "P2", "P3")
LIMIT = 10 * 1024 * 1024


class ContractError(ValueError):
    """A safe, fixed-message contract validation failure."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _keys(value: Any, required: set, optional: set = frozenset()) -> None:
    _require(isinstance(value, dict), "Expected an object.")
    _require(
        required <= value.keys() <= required | optional,
        "Missing or unknown object fields.",
    )


def _identifier(value: Any) -> str:
    _require(
        isinstance(value, str)
        and bool(re.fullmatch(r"[a-zA-Z0-9_]{1,64}", value)),
        "Invalid identifier.",
    )
    return value


def _text(value: Any) -> None:
    _require(
        isinstance(value, str) and bool(value.strip()),
        "Expected nonempty text.",
    )


def _relative(value: Any) -> str:
    _text(value)
    path = PurePosixPath(value)
    _require(
        not path.is_absolute()
        and "\\" not in value
        and ":" not in value
        and all(part not in ("", ".", "..") for part in value.split("/")),
        "Unsafe relative path.",
    )
    _require(
        all(not part.endswith((".", " ")) for part in path.parts),
        "Unsafe relative path.",
    )
    _require(
        all(
            not re.fullmatch(
                r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])", part.split(".")[0]
            )
            for part in path.parts
        ),
        "Reserved file name.",
    )
    return value


def _safe(path: Path) -> Path:
    path = path.absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            _require(
                not stat.S_ISLNK(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & 1024,
                "Links and reparse points are not allowed.",
            )
    return path


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key.")
        result[key] = value
    return result


def _read(path: Path) -> Any:
    path = _safe(path)
    _require(
        path.is_file() and path.stat().st_size <= LIMIT,
        "Expected a bounded regular file.",
    )
    _require(stat.S_ISREG(path.stat().st_mode), "Special files forbidden.")
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_constant=lambda _: _require(False, "Invalid number."),
    )


def _digest(value: Any) -> str:
    data = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _write(path: Path, value: Any) -> None:
    serialized = (
        json.dumps(value, ensure_ascii=False, indent=4, allow_nan=False) + "\n"
    )
    _require(len(serialized.encode("utf-8")) <= LIMIT, "Snapshot too large.")
    path = _safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)


def _seal(value: dict) -> dict:
    return {**value, "digest": _digest(value)}


def _unseal(value: dict) -> dict:
    _require(
        isinstance(value, dict) and "digest" in value,
        "Missing snapshot digest.",
    )
    payload = {key: item for key, item in value.items() if key != "digest"}
    _require(value["digest"] == _digest(payload), "Snapshot digest mismatch.")
    return payload


def _files(root: Path, values: Any) -> dict:
    _require(isinstance(values, list) and bool(values), "Files list required.")
    result = {}
    for name in values:
        name = _relative(name)
        _require(
            name.casefold() not in {key.casefold() for key in result},
            "Duplicate file path.",
        )
        path = _safe(root / name)
        _require(
            path.is_file()
            and stat.S_ISREG(path.stat().st_mode)
            and path.stat().st_size <= LIMIT,
            "Invalid input file.",
        )
        result[name] = path.read_text(encoding="utf-8")
    _require(
        sum(len(x.encode("utf-8")) for x in result.values()) <= LIMIT,
        "Snapshot too large.",
    )
    return result


def create_plan(definition: Path, output: Path) -> dict:
    """Freeze a trusted experiment definition and all referenced text files."""
    config = _read(definition)
    _keys(config, {"id", "repeats", "execution", "tasks", "treatments"})
    _identifier(config["id"])
    _require(
        type(config["repeats"]) is int and 1 <= config["repeats"] <= 100,
        "Repeats must be an integer between 1 and 100.",
    )
    _require(
        isinstance(config["execution"], dict) and config["execution"],
        "Execution conditions are required.",
    )
    root = _safe(definition).parent
    _require(
        isinstance(config["tasks"], list)
        and isinstance(config["treatments"], list),
        "Lists required.",
    )
    tasks = {}
    for task in config["tasks"]:
        _keys(task, {"id", "requirement", "files", "expected"})
        identity = _identifier(task["id"])
        _require(
            identity.casefold() not in {key.casefold() for key in tasks},
            "Duplicate task.",
        )
        _text(task["requirement"])
        expected = {}
        _require(isinstance(task["expected"], list), "Expected list required.")
        for item in task["expected"]:
            _keys(item, {"id", "description", "severity", "category"})
            _identifier(item["id"])
            _text(item["description"])
            _require(item["id"] not in expected, "Duplicate expected issue.")
            _require(
                item["severity"] in SEVERITIES
                and item["category"] in CATEGORIES,
                "Invalid expected severity or category.",
            )
            expected[item["id"]] = item
        tasks[identity] = {
            "requirement": task["requirement"],
            "files": _files(root, task["files"]),
            "expected": expected,
        }
    treatments = {}
    for treatment in config["treatments"]:
        _keys(treatment, {"id", "knowledge"})
        identity = _identifier(treatment["id"])
        _require(
            identity.casefold() not in {key.casefold() for key in treatments},
            "Duplicate treatment.",
        )
        _require(
            isinstance(treatment["knowledge"], dict)
            and treatment["knowledge"].keys() <= set(CATEGORIES),
            "Invalid knowledge categories.",
        )
        treatments[identity] = {
            category: _files(root, files)
            for category, files in treatment["knowledge"].items()
        }
    _require(bool(tasks) and bool(treatments), "Empty experiment.")
    cells = [
        {
            "id": f"{task}--{treatment}--{repeat}",
            "task": task,
            "treatment": treatment,
            "repeat": repeat,
        }
        for task in tasks
        for treatment in treatments
        for repeat in range(1, config["repeats"] + 1)
    ]
    payload = {
        "version": 1,
        "id": config["id"],
        "scenario": "review",
        "execution": config["execution"],
        "execution_digest": _digest(config["execution"]),
        "tasks": tasks,
        "treatments": treatments,
        "cells": cells,
    }
    plan = _seal(payload)
    _require(not _safe(output).exists(), "Output already exists.")
    _write(output / "plan.json", plan)
    return plan


def _plan(run: Path) -> dict:
    value = _read(run / "plan.json")
    _unseal(value)
    _require(
        value.get("version") == 1 and value.get("scenario") == "review",
        "Unsupported plan version or scenario.",
    )
    return value


def _cell(plan: dict, cell_id: str) -> dict:
    matches = [item for item in plan["cells"] if item["id"] == cell_id]
    _require(len(matches) == 1, "Unknown cell.")
    return matches[0]


def export_input(run: Path, cell_id: str, output: Path) -> dict:
    """Export only public task text, code, and selected knowledge."""
    plan = _plan(run)
    cell = _cell(plan, cell_id)
    task = plan["tasks"][cell["task"]]
    public = {
        "plan_digest": plan["digest"],
        "cell_id": cell_id,
        "execution_digest": plan["execution_digest"],
        "requirement": task["requirement"],
        "files": task["files"],
        "knowledge": plan["treatments"][cell["treatment"]],
        "response_contract": {
            "binding": "Copy plan_digest, cell_id and execution_digest unchanged.",
            "status": ["completed", "error", "timeout", "cancelled"],
            "findings": "Array of objects: id (unique alphanumeric/underscore), title, file (exact supplied path), line (positive integer), severity (P0/P1/P2/P3). Failed executions require an empty array.",
            "provenance": "Object with nonempty producer, session and isolation strings; declare unknown conditions honestly.",
            "usage": "Optional object: tokens (nonnegative integer or null), cost_usd (nonnegative number or null). Unknown is null, not zero.",
            "format": "Return only a JSON object with binding fields, status, findings, provenance and optional usage; no other fields.",
        },
    }
    _write(output, public)
    return public


def _binding(record: dict, plan: dict) -> dict:
    _require(record["plan_digest"] == plan["digest"], "Plan binding mismatch.")
    return _cell(plan, record["cell_id"])


def _submission(record: dict, plan: dict) -> None:
    _keys(
        record,
        {
            "plan_digest",
            "cell_id",
            "execution_digest",
            "status",
            "findings",
            "provenance",
        },
        {"usage"},
    )
    cell = _binding(record, plan)
    _require(
        record["execution_digest"] == plan["execution_digest"],
        "Execution declaration mismatch.",
    )
    _require(
        record["status"] in ("completed", "error", "timeout", "cancelled"),
        "Invalid execution status.",
    )
    _keys(record["provenance"], {"producer", "session", "isolation"})
    for value in record["provenance"].values():
        _text(value)
    _require(isinstance(record["findings"], list), "Findings list required.")
    _require(
        record["status"] == "completed" or not record["findings"],
        "Failed execution cannot submit scored findings.",
    )
    identities = set()
    for finding in record["findings"]:
        _keys(finding, {"id", "title", "file", "line", "severity"})
        identity = _identifier(finding["id"])
        _require(identity not in identities, "Duplicate finding.")
        identities.add(identity)
        _text(finding["title"])
        _relative(finding["file"])
        _require(
            finding["file"] in plan["tasks"][cell["task"]]["files"],
            "Finding references an unknown file.",
        )
        _require(
            type(finding["line"]) is int and finding["line"] > 0,
            "Invalid finding line.",
        )
        _require(finding["severity"] in SEVERITIES, "Invalid severity.")
    usage = record.get("usage", {})
    _keys(usage, set(), {"tokens", "cost_usd"})
    for key, value in usage.items():
        _require(
            value is None
            or (
                type(value) in (int, float)
                and math.isfinite(value)
                and value >= 0
            ),
            "Invalid usage.",
        )
        if key == "tokens":
            _require(
                value is None or type(value) is int, "Invalid token count."
            )


def import_submission(run: Path, source: Path) -> dict:
    """Import a result as an immutable, unverified source declaration."""
    plan = _plan(run)
    record = _read(source)
    _submission(record, plan)
    sealed = _seal(record)
    _write(run / "submissions" / (record["cell_id"] + ".json"), sealed)
    return sealed


def _load_submission(run: Path, plan: dict, cell_id: str) -> dict:
    record = _read(run / "submissions" / (cell_id + ".json"))
    _submission(_unseal(record), plan)
    _require(record["cell_id"] == cell_id, "Submission identity mismatch.")
    return record


def _adjudication(record: dict, plan: dict, submission: dict) -> None:
    _keys(
        record,
        {
            "plan_digest",
            "cell_id",
            "submission_digest",
            "reviewer",
            "decisions",
        },
    )
    cell = _binding(record, plan)
    _text(record["reviewer"])
    _require(
        record["cell_id"] == submission["cell_id"]
        and record["submission_digest"] == submission["digest"],
        "Adjudication submission binding mismatch.",
    )
    _require(submission["status"] == "completed", "Execution did not complete.")
    _require(
        isinstance(record["decisions"], dict), "Decisions object required."
    )
    findings = {item["id"] for item in submission["findings"]}
    _require(
        record["decisions"].keys() == findings,
        "Every finding requires exactly one decision.",
    )
    matched = []
    expected = plan["tasks"][cell["task"]]["expected"]
    for value in record["decisions"].values():
        _require(
            value is None or isinstance(value, str) and value in expected,
            "Unknown expected issue; use null for false positive.",
        )
        if value is not None:
            matched.append(value)
    _require(
        len(matched) == len(set(matched)),
        "Multiple findings cannot claim the same expected issue.",
    )


def import_adjudication(run: Path, source: Path) -> dict:
    """Import supplied decisions; reviewer identity is not verified."""
    plan = _plan(run)
    record = _read(source)
    _require(
        isinstance(record, dict) and "cell_id" in record,
        "Missing adjudication cell.",
    )
    _cell(plan, record["cell_id"])
    submission = _load_submission(run, plan, record["cell_id"])
    _adjudication(record, plan, submission)
    sealed = _seal(record)
    _write(run / "adjudications" / (record["cell_id"] + ".json"), sealed)
    return sealed


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    return numerator / denominator if denominator else None


def _score(task: dict, submission: dict, decisions: dict) -> dict:
    expected = task["expected"]
    matches = {value for value in decisions.values() if value is not None}
    count = len(matches)
    severity_correct = sum(
        finding["severity"] == expected[decisions[finding["id"]]]["severity"]
        for finding in submission["findings"]
        if decisions[finding["id"]] is not None
    )
    return {
        "detected": count,
        "missed": len(expected) - count,
        "false_positives": len(decisions) - count,
        "recall": _ratio(count, len(expected)),
        "precision": _ratio(count, len(decisions)),
        "severity_accuracy": _ratio(severity_correct, count),
        "categories": {
            category: {
                "expected": sum(
                    x["category"] == category for x in expected.values()
                ),
                "detected": sum(
                    expected[x]["category"] == category for x in matches
                ),
                "recall": _ratio(
                    sum(expected[x]["category"] == category for x in matches),
                    sum(x["category"] == category for x in expected.values()),
                ),
            }
            for category in CATEGORIES
        },
    }


def report(run: Path) -> dict:
    """Report every predeclared cell, including missing and pending results."""
    plan = _plan(run)
    valid_names = {cell["id"] + ".json" for cell in plan["cells"]}
    for directory in ("submissions", "adjudications"):
        folder = _safe(run / directory)
        if folder.exists():
            _require(
                all(
                    path.name in valid_names and path.is_file()
                    for path in folder.iterdir()
                ),
                "Unexpected result file.",
            )
    rows = []
    for cell in plan["cells"]:
        row = {
            **cell,
            "status": "missing",
            "score": None,
            "usage": {"tokens": None, "cost_usd": None},
        }
        submission_path = _safe(run / "submissions" / (cell["id"] + ".json"))
        decision_path = _safe(run / "adjudications" / (cell["id"] + ".json"))
        if submission_path.exists():
            submission = _load_submission(run, plan, cell["id"])
            row["usage"].update(submission.get("usage", {}))
            row["status"] = submission["status"]
            if submission["status"] == "completed":
                row["status"] = "pending"
            if decision_path.exists():
                decision = _read(decision_path)
                _adjudication(_unseal(decision), plan, submission)
                row["score"] = _score(
                    plan["tasks"][cell["task"]],
                    submission,
                    decision["decisions"],
                )
                row["status"] = "scored"
        else:
            _require(not decision_path.exists(), "Orphan adjudication.")
        rows.append(row)
    pairs = []
    for task in plan["tasks"]:
        repeats = sorted({cell["repeat"] for cell in plan["cells"]})
        for repeat in repeats:
            paired = {
                row["treatment"]: row
                for row in rows
                if row["task"] == task and row["repeat"] == repeat
            }
            reference = plan["cells"][0]["treatment"]
            comparisons = {}
            for treatment in plan["treatments"]:
                if treatment == reference:
                    continue
                before = paired[reference]["score"]
                after = paired[treatment]["score"]
                comparisons[treatment] = {
                    metric: (
                        after[metric] - before[metric]
                        if before is not None
                        and after is not None
                        and before[metric] is not None
                        and after[metric] is not None
                        else None
                    )
                    for metric in ("recall", "precision", "severity_accuracy")
                }
            pairs.append(
                {
                    "task": task,
                    "repeat": repeat,
                    "reference_treatment": reference,
                    "metric_deltas": comparisons,
                    "complete": all(
                        x["status"] == "scored" for x in paired.values()
                    ),
                    "cells": {
                        key: value["id"] for key, value in paired.items()
                    },
                }
            )
    summary = {}
    for treatment in plan["treatments"]:
        selected = [row for row in rows if row["treatment"] == treatment]
        scored = [row["score"] for row in selected if row["score"] is not None]
        costs = [
            row["usage"]["cost_usd"]
            for row in selected
            if row["usage"]["cost_usd"] is not None
        ]
        summary[treatment] = {
            "expected_cells": len(selected),
            "scored_cells": len(scored),
            "cost_coverage": _ratio(len(costs), len(selected)),
            "observed_cost_usd": sum(costs) if costs else None,
            "status_counts": {
                status: sum(x["status"] == status for x in selected)
                for status in (
                    "missing",
                    "pending",
                    "scored",
                    "error",
                    "timeout",
                    "cancelled",
                )
            },
        }
    return {
        "plan_digest": plan["digest"],
        "scenario": "review",
        "evidence": "Imported declarations and supplied adjudication; isolation, reviewer identity and reviewer independence are unverified.",
        "cells": rows,
        "pairs": pairs,
        "treatments": summary,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the JSON CLI; failures never print arbitrary input or exceptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("plan")
    command.add_argument("definition", type=Path)
    command.add_argument("output", type=Path)
    command = commands.add_parser("export")
    command.add_argument("run", type=Path)
    command.add_argument("cell_id")
    command.add_argument("output", type=Path)
    for name in ("import", "adjudicate"):
        command = commands.add_parser(name)
        command.add_argument("run", type=Path)
        command.add_argument("source", type=Path)
    command = commands.add_parser("report")
    command.add_argument("run", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = create_plan(args.definition, args.output)
            result = {"plan_digest": result["digest"], "cells": result["cells"]}
        elif args.command == "export":
            export_input(args.run, args.cell_id, args.output)
            result = {"exported": True}
        elif args.command == "import":
            result = {
                "submission_digest": import_submission(args.run, args.source)[
                    "digest"
                ]
            }
        elif args.command == "adjudicate":
            result = {
                "adjudication_digest": import_adjudication(
                    args.run, args.source
                )["digest"]
            }
        else:
            result = report(args.run)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except ContractError as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception:
        print(
            "Evaluation failed; check input contract and filesystem.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
