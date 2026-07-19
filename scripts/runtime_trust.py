"""Validate the minimum Trust Model for one completed runtime Run."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import harness_runtime
import run_journal
import run_manifest

VERIFIED_CLAIMS = (
    "artifact-schema-path-digest-and-run-binding",
    "event-sequence-checkpoint-and-idempotency-contract",
    "runtime-harness-capability-gate",
    "declared-process-separation-for-strict-judge",
    "reasoned-user-overrides-are-auditable",
)
UNPROVABLE_CLAIMS = (
    "reviewer-or-judge-semantic-correctness",
    "strong-actor-identity-isolation",
    "integrity-against-a-fully-compromised-host",
    "behavior-outside-declared-and-executed-checks",
)
_BINDING_FIELDS = (
    "schema_version",
    "run_id",
    "profile",
    "harness",
    "commit_sha",
    "config_digest",
)


class TrustError(Exception):
    """Raised when Run evidence violates the minimum Trust Model."""

    def __init__(self, issues: Sequence[str]):
        super().__init__("; ".join(issues))
        self.issues = tuple(issues)


def _artifact_documents(
    run_dir: Path, manifest: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    documents = {}
    for entry in manifest["payload"]["artifacts"]:
        path = run_manifest.secure_run_path(run_dir, entry["path"])
        documents[entry["artifact_id"]] = json.loads(path.read_text(encoding="utf-8"))
    return documents


def _validate_strict_review(
    documents: dict[str, dict[str, Any]], issues: list[str]
) -> None:
    reviews = [
        document
        for document in documents.values()
        if document["artifact_type"] == "review-report"
        and document["payload"]["scope"] == "run"
    ]
    if not reviews:
        issues.append("missing_run_review")
        return
    if len(reviews) != 1:
        issues.append("run_review_count")
        return
    payload = reviews[0]["payload"]
    if payload["review_profile"] != "strict":
        issues.append("run_review_not_strict")
    if (
        payload["verdict"] != "PASS"
        or payload["p0_count"] != 0
        or payload["p1_count"] != 0
    ):
        issues.append("run_review_gate_failed")
    implementer = payload.get("implementer_actor")
    judge = payload.get("judge_actor")
    if not implementer or not judge:
        issues.append("missing_review_actor_attestation")
    elif implementer == judge:
        issues.append("judge_not_independent")
    if payload.get("independence_basis") != "process-separated-agent":
        issues.append("invalid_independence_basis")


def _capability_snapshot(
    run_dir: Path, manifest: dict[str, Any], documents: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    candidates = [
        document
        for document in documents.values()
        if document["artifact_type"] == "input-artifact"
        and document["payload"]["input_type"] == "capability-matrix"
    ]
    if len(candidates) != 1:
        raise TrustError(["capability_snapshot_count"])
    path = run_manifest.secure_run_path(run_dir, candidates[0]["payload"]["path"])
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise TrustError(["invalid_capability_snapshot"]) from error
    if not isinstance(value, dict):
        raise TrustError(["invalid_capability_snapshot"])
    if value.get("run_id") != manifest["run_id"]:
        raise TrustError(["capability_snapshot_run_mismatch"])
    if value.get("harness") != manifest["harness"]:
        raise TrustError(["capability_snapshot_harness_mismatch"])
    if value.get("evidence_source") != "runtime-adapter-probe":
        raise TrustError(["capability_snapshot_not_runtime_probed"])
    if value.get("verdict") != "PASS" or value.get("blocking_capabilities"):
        raise TrustError(["capability_gate_failed"])
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict):
        raise TrustError(["invalid_capability_snapshot"])
    try:
        harness_runtime.validate_probe(
            manifest["harness"],
            {
                "contract_version": 1,
                "harness": value.get("harness"),
                "capabilities": capabilities,
            },
        )
        gated = harness_runtime.gate_capabilities(
            {
                "schema_version": 1,
                "harness": manifest["harness"],
                "capabilities": capabilities,
            },
            value.get("required_capabilities", []),
            value.get("optional_capabilities", []),
        )
    except harness_runtime.HarnessError as error:
        raise TrustError(["invalid_capability_snapshot"]) from error
    if gated["verdict"] != "PASS":
        raise TrustError(["capability_gate_failed"])
    for field in ("verdict", "blocking_capabilities", "degradations"):
        if value.get(field) != gated[field]:
            raise TrustError([f"capability_report_{field}_mismatch"])
    return value


def _validate_journal(
    run_dir: Path, manifest: dict[str, Any], artifact_ids: set[str]
) -> list[dict[str, str]]:
    journal_path = run_dir / "events.jsonl"
    events = run_journal.read_events(journal_path)
    if not events:
        raise TrustError(["missing_journal_events"])
    run_journal.replay_events(events)
    checkpoints = sorted((run_dir / "checkpoints").glob("checkpoint-*.json"))
    if not checkpoints:
        raise TrustError(["missing_checkpoint"])
    run_journal.validate_checkpoint(checkpoints[-1], events)
    overrides = []
    for event in events:
        for field in _BINDING_FIELDS:
            if event[field] != manifest[field]:
                raise TrustError([f"event_manifest_{field}_mismatch"])
        references = set(event["payload"]["input_artifact_ids"])
        references.update(event["payload"]["output_artifact_ids"])
        unknown = references - artifact_ids
        if unknown:
            raise TrustError([f"event_unknown_artifact:{min(unknown)}"])
        event_type = event["payload"]["event_type"]
        if not event_type.startswith("user-"):
            continue
        action = event_type.removeprefix("user-")
        if action not in {"approve", "reject", "retry", "cancel", "override"}:
            raise TrustError(["invalid_user_action"])
        reason = event["payload"].get("details", {}).get("reason")
        if (
            event["payload"]["actor"] != "user"
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise TrustError(["invalid_user_override"])
        overrides.append(
            {
                "event_id": event["payload"]["event_id"],
                "action": action,
                "reason": reason,
            }
        )
    return overrides


def validate_run(run_dir: Path) -> dict[str, Any]:
    """Validate evidence consistency and return explicitly bounded claims."""
    try:
        manifest = json.loads(
            (run_dir / "run-manifest.json").read_text(encoding="utf-8")
        )
        run_manifest.validate_manifest(run_dir, manifest)
        documents = _artifact_documents(run_dir, manifest)
        issues: list[str] = []
        _validate_strict_review(documents, issues)
        if issues:
            raise TrustError(issues)
        _capability_snapshot(run_dir, manifest, documents)
        overrides = _validate_journal(run_dir, manifest, set(documents))
    except TrustError:
        raise
    except run_manifest.ManifestError as error:
        raise TrustError(
            tuple(f"manifest:{issue}" for issue in error.issues)
        ) from error
    except run_journal.JournalError as error:
        raise TrustError([f"journal:{error}"]) from error
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as error:
        raise TrustError(["invalid_run_evidence"]) from error
    return {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "verdict": "PASS",
        "verified_claims": list(VERIFIED_CLAIMS),
        "unprovable_claims": list(UNPROVABLE_CLAIMS),
        "user_overrides": overrides,
    }


def _atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=4)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one runtime Trust Model")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Trust Model validator with stable output and exit codes."""
    args = _parse_args(argv)
    try:
        report = validate_run(args.run_dir)
        content = json.dumps(report, ensure_ascii=False, indent=4) + "\n"
        if args.output:
            _atomic_write_json(args.output, report)
        print(content, end="")
        return 0
    except TrustError as error:
        for issue in error.issues:
            print(issue, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("runtime trust validation interrupted", file=sys.stderr)
        return 130
    except Exception:
        print("runtime trust validation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
