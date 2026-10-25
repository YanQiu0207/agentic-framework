"""Offline contract tests; no model, container, or submitted code executes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import agent_eval as evaluation

EXAMPLE = (
    Path(__file__).resolve().parents[1] / "evaluation/review/experiment.json"
)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def experiment(tmp_path):
    run = tmp_path / "run"
    plan = evaluation.create_plan(EXAMPLE, run)
    return run, plan


def submission(plan, cell="checkout--CONTROL--1", findings=None):
    return {
        "plan_digest": plan["digest"],
        "cell_id": cell,
        "execution_digest": plan["execution_digest"],
        "status": "completed",
        "findings": findings or [],
        "provenance": {
            "producer": "fake",
            "session": "isolated-claim",
            "isolation": "unknown",
        },
    }


def finding(identity="f1", severity="P2"):
    return {
        "id": identity,
        "title": "邮箱泄漏",
        "file": "public/checkout.py",
        "line": 8,
        "severity": severity,
    }


def adjudication(plan, result, decisions):
    return {
        "plan_digest": plan["digest"],
        "cell_id": result["cell_id"],
        "submission_digest": result["digest"],
        "reviewer": "human-claim",
        "decisions": decisions,
    }


def test_plan_reproducible_and_frozen(experiment, tmp_path):
    run, plan = experiment
    other = evaluation.create_plan(EXAMPLE, tmp_path / "other")
    assert plan == other
    assert len(plan["cells"]) == 8
    with pytest.raises(evaluation.ContractError):
        evaluation.create_plan(EXAMPLE, run)


def test_public_input_does_not_leak_expected(experiment, tmp_path):
    run, plan = experiment
    control = evaluation.export_input(
        run, "checkout--CONTROL--1", tmp_path / "c.json"
    )
    knowledge = evaluation.export_input(
        run, "checkout--KNOWLEDGE--1", tmp_path / "k.json"
    )
    assert control["knowledge"] == {}
    assert set(knowledge["knowledge"]) == set(evaluation.CATEGORIES)
    assert control["files"] == knowledge["files"]
    assert control["requirement"] == knowledge["requirement"]
    assert "expected" not in control
    for expected in plan["tasks"]["checkout"]["expected"].values():
        assert expected["description"] not in json.dumps(control)
    assert str(EXAMPLE.parent) not in json.dumps(control)
    with pytest.raises(FileExistsError):
        evaluation.export_input(
            run, "checkout--CONTROL--1", tmp_path / "c.json"
        )


def test_full_import_adjudicate_report(experiment, tmp_path):
    run, plan = experiment
    record = submission(plan, findings=[finding(), finding("f2", "P0")])
    record["usage"] = {"tokens": 35, "cost_usd": 0.01}
    result = evaluation.import_submission(
        run, write_json(tmp_path / "s.json", record)
    )
    pending = evaluation.report(run)
    assert pending["cells"][0]["status"] == "pending"
    evaluation.import_adjudication(
        run,
        write_json(
            tmp_path / "a.json",
            adjudication(plan, result, {"f1": "logging", "f2": None}),
        ),
    )
    report = evaluation.report(run)
    assert "human adjudication" not in report["evidence"]
    assert "supplied adjudication" in report["evidence"]
    assert "reviewer identity" in report["evidence"]
    score = report["cells"][0]["score"]
    assert score["recall"] == 1 / 3
    assert score["precision"] == 0.5
    assert score["severity_accuracy"] == 1
    assert score["false_positives"] == 1
    assert score["missed"] == 2
    assert score["categories"]["conventions"]["recall"] == 1
    assert len(report["cells"]) == 8
    assert all(not pair["complete"] for pair in report["pairs"])
    assert report["treatments"]["CONTROL"]["cost_coverage"] == 0.25
    assert report["treatments"]["KNOWLEDGE"]["observed_cost_usd"] is None
    with pytest.raises(FileExistsError):
        evaluation.import_submission(run, tmp_path / "s.json")
    with pytest.raises(FileExistsError):
        evaluation.import_adjudication(run, tmp_path / "a.json")


def test_clean_task_zero_denominators(experiment, tmp_path):
    run, plan = experiment
    result = evaluation.import_submission(
        run,
        write_json(tmp_path / "s.json", submission(plan, "clean--CONTROL--1")),
    )
    evaluation.import_adjudication(
        run, write_json(tmp_path / "a.json", adjudication(plan, result, {}))
    )
    row = next(
        x
        for x in evaluation.report(run)["cells"]
        if x["id"] == result["cell_id"]
    )
    assert row["status"] == "scored"
    assert row["score"]["recall"] is None
    assert row["score"]["precision"] is None
    assert row["score"]["severity_accuracy"] is None


@pytest.mark.parametrize("status", ["error", "timeout", "cancelled"])
def test_execution_failures_are_not_scored(experiment, tmp_path, status):
    run, plan = experiment
    record = submission(plan)
    record["status"] = status
    result = evaluation.import_submission(
        run, write_json(tmp_path / "s.json", record)
    )
    assert evaluation.report(run)["cells"][0]["status"] == status
    with pytest.raises(evaluation.ContractError):
        evaluation.import_adjudication(
            run, write_json(tmp_path / "a.json", adjudication(plan, result, {}))
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("plan_digest", "wrong"),
        ("execution_digest", "wrong"),
        ("cell_id", "../../escape"),
        ("status", "success"),
        ("usage", {"tokens": -1}),
        ("usage", {"tokens": 1.5}),
        ("usage", {"cost_usd": True}),
        ("usage", {"cost_usd": float("inf")}),
        ("findings", [finding(), finding()]),
    ],
)
def test_invalid_submission_no_write(experiment, tmp_path, field, value):
    run, plan = experiment
    record = submission(plan)
    record[field] = value
    with pytest.raises(evaluation.ContractError):
        evaluation.import_submission(
            run, write_json(tmp_path / "s.json", record)
        )
    assert not (run / "submissions").exists()


@pytest.mark.parametrize(
    "decisions",
    [
        {},
        {"f1": "unknown", "f2": None},
        {"f1": "logging", "f2": "logging"},
        {"f1": "logging", "f2": None, "unknown": None},
    ],
)
def test_bad_adjudication_rejected(experiment, tmp_path, decisions):
    run, plan = experiment
    result = evaluation.import_submission(
        run,
        write_json(
            tmp_path / "s.json",
            submission(plan, findings=[finding(), finding("f2")]),
        ),
    )
    with pytest.raises(evaluation.ContractError):
        evaluation.import_adjudication(
            run,
            write_json(
                tmp_path / "a.json", adjudication(plan, result, decisions)
            ),
        )
    assert not (run / "adjudications").exists()


def test_wrong_adjudication_binding(experiment, tmp_path):
    run, plan = experiment
    result = evaluation.import_submission(
        run, write_json(tmp_path / "s.json", submission(plan))
    )
    decision = adjudication(plan, result, {})
    decision["submission_digest"] = "wrong"
    with pytest.raises(evaluation.ContractError):
        evaluation.import_adjudication(
            run, write_json(tmp_path / "a.json", decision)
        )


def test_tampered_plan_and_submission(experiment, tmp_path):
    run, plan = experiment
    result = evaluation.import_submission(
        run, write_json(tmp_path / "s.json", submission(plan))
    )
    result["status"] = "error"
    write_json(run / "submissions" / (result["cell_id"] + ".json"), result)
    with pytest.raises(evaluation.ContractError):
        evaluation.report(run)
    plan["execution"]["model"] = "changed"
    write_json(run / "plan.json", plan)
    with pytest.raises(evaluation.ContractError):
        evaluation.report(run)


@pytest.mark.parametrize(
    "path",
    [
        "../a.py",
        "C:/a.py",
        "/a.py",
        "a\\b.py",
        "a//b.py",
        "a/./b.py",
        "NUL",
        "x.",
    ],
)
def test_unsafe_paths_rejected(tmp_path, path):
    config = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    config["tasks"][0]["files"] = [path]
    with pytest.raises(evaluation.ContractError):
        evaluation.create_plan(
            write_json(tmp_path / "e.json", config), tmp_path / "run"
        )
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("repeat", [0, -1, 101, True, 1.5])
def test_bad_repeats(tmp_path, repeat):
    config = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    config["repeats"] = repeat
    with pytest.raises(evaluation.ContractError):
        evaluation.create_plan(
            write_json(tmp_path / "e.json", config), tmp_path / "run"
        )


def test_symlink_rejected(experiment, tmp_path):
    run, plan = experiment
    target = write_json(tmp_path / "s.json", submission(plan))
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    with pytest.raises(evaluation.ContractError):
        evaluation.import_submission(run, link)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"id":"first","id":"second"}', encoding="utf-8")
    with pytest.raises(evaluation.ContractError):
        evaluation.create_plan(path, tmp_path / "run")


def test_unicode_cli_cp936_parent(experiment, tmp_path):
    run, _ = experiment
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    # A CP936 consumer can decode ASCII-escaped JSON without losing Unicode.
    result = subprocess.run(
        [sys.executable, str(Path(evaluation.__file__)), "report", str(run)],
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout.encode("ascii").decode("cp936"))["cells"]
    output = tmp_path / "中文.json"
    assert (
        evaluation.main(
            ["export", str(run), "checkout--KNOWLEDGE--1", str(output)]
        )
        == 0
    )
    assert "架构" in output.read_text(encoding="utf-8")


def test_unknown_exception_is_not_echoed(monkeypatch, capsys):
    def fail(_):
        raise RuntimeError("secret-test-token")

    monkeypatch.setattr(evaluation, "report", fail)
    assert evaluation.main(["report", "unused"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "secret-test-token" not in captured.err


def test_complete_pair_and_delta(experiment, tmp_path):
    run, plan = experiment
    for treatment in ("CONTROL", "KNOWLEDGE"):
        findings = [] if treatment == "CONTROL" else [finding()]
        result = evaluation.import_submission(
            run,
            write_json(
                tmp_path / (treatment + ".json"),
                submission(plan, "checkout--" + treatment + "--1", findings),
            ),
        )
        decisions = {} if treatment == "CONTROL" else {"f1": "logging"}
        evaluation.import_adjudication(
            run,
            write_json(
                tmp_path / (treatment + "-judge.json"),
                adjudication(plan, result, decisions),
            ),
        )
    pair = evaluation.report(run)["pairs"][0]
    assert pair["complete"]
    assert pair["reference_treatment"] == "CONTROL"
    assert pair["metric_deltas"]["KNOWLEDGE"]["recall"] == 1 / 3
    assert pair["metric_deltas"]["KNOWLEDGE"]["precision"] is None
    plan["treatments"] = dict(reversed(list(plan["treatments"].items())))
    write_json(run / "plan.json", plan)
    reordered_pair = evaluation.report(run)["pairs"][0]
    assert reordered_pair == pair


def test_file_change_creates_new_digest_and_old_snapshot_stays(tmp_path):
    code = tmp_path / "code.py"
    code.write_text("before", encoding="utf-8")
    config = {
        "id": "minimal",
        "repeats": 1,
        "execution": {"model": "fake"},
        "tasks": [
            {
                "id": "one",
                "requirement": "review",
                "files": ["code.py"],
                "expected": [],
            }
        ],
        "treatments": [{"id": "CONTROL", "knowledge": {}}],
    }
    definition = write_json(tmp_path / "e.json", config)
    first = evaluation.create_plan(definition, tmp_path / "first")
    code.write_text("after", encoding="utf-8")
    second = evaluation.create_plan(definition, tmp_path / "second")
    assert first["digest"] != second["digest"]
    assert (
        evaluation._plan(tmp_path / "first")["tasks"]["one"]["files"]["code.py"]
        == "before"
    )
    config["tasks"].append({**config["tasks"][0], "id": "ONE"})
    write_json(definition, config)
    with pytest.raises(evaluation.ContractError):
        evaluation.create_plan(definition, tmp_path / "third")


def test_reparse_point_is_rejected_without_os_privilege(tmp_path, monkeypatch):
    from types import SimpleNamespace

    original = Path.lstat
    target = tmp_path / "linked.json"
    target.write_text("{}", encoding="utf-8")

    def reparse(path):
        info = original(path)
        if path == target:
            return SimpleNamespace(
                st_mode=info.st_mode, st_file_attributes=1024
            )
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(evaluation.ContractError):
        evaluation._read(target)


def test_cancel_exit_code(monkeypatch, capsys):
    def interrupt(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(evaluation, "report", interrupt)
    assert evaluation.main(["report", "unused"]) == 130
    assert capsys.readouterr().err == "Interrupted.\n"


def test_unexpected_result_file_rejected(experiment):
    run, _ = experiment
    (run / "submissions").mkdir()
    (run / "submissions" / "unknown.json").write_text("{}", encoding="utf-8")
    with pytest.raises(evaluation.ContractError):
        evaluation.report(run)
