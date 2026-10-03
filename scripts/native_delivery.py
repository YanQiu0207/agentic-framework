"""Validate bounded Native evidence without initializing Runtime state."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FORBIDDEN_FIELDS = frozenset(
    {
        "run_id",
        "harness",
        "config_digest",
        "trust_gate",
        "harness_capability_probe",
        "run_manifest_evidence_graph",
        "implementer_actor",
        "judge_actor",
        "independence_basis",
        "strict_independent_review",
    }
)
INDEPENDENCE_FIELDS = frozenset(
    {
        "implementer_actor",
        "judge_actor",
        "independence_basis",
    }
)
UNPROVABLE_CLAIMS = (
    "runtime-trust-gate",
    "harness-capability-probe",
    "run-manifest-evidence-graph",
    "strong-identity-isolation",
    "semantic-correctness",
)


class NativeDeliveryError(Exception):
    """Raised when Native evidence violates its versioned contract."""


def _schema_validate(value: object, schema: dict[str, Any]) -> None:
    for part in schema.get("allOf", []):
        _schema_validate(value, part)
    if "not" in schema:
        try:
            _schema_validate(value, schema["not"])
        except NativeDeliveryError:
            pass
        else:
            raise NativeDeliveryError("forbidden schema branch")
    if "if" in schema:
        try:
            _schema_validate(value, schema["if"])
        except NativeDeliveryError:
            branch = schema.get("else", {})
        else:
            branch = schema.get("then", {})
        _schema_validate(value, branch)
    expected = schema.get("type")
    matches = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if expected is not None and not matches.get(expected, False):
        raise NativeDeliveryError("invalid JSON type")
    if "const" in schema and value != schema["const"]:
        raise NativeDeliveryError("invalid constant")
    if "enum" in schema and value not in schema["enum"]:
        raise NativeDeliveryError("invalid enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise NativeDeliveryError("empty evidence string")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise NativeDeliveryError("invalid evidence format")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            raise NativeDeliveryError("integer below minimum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise NativeDeliveryError("missing array evidence")
        for item in value:
            _schema_validate(item, schema.get("items", {}))
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(set(encoded)) != len(encoded):
                raise NativeDeliveryError("duplicate evidence")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            raise NativeDeliveryError("required evidence missing")
        if schema.get("additionalProperties") is False:
            if value.keys() - properties.keys():
                raise NativeDeliveryError("unexpected evidence field")
        for key, item in value.items():
            _schema_validate(item, properties.get(key, {}))


def _validate(document: object, name: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise NativeDeliveryError("report must be an object")
    try:
        json.dumps(document, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise NativeDeliveryError(
            "report is not finite JSON evidence"
        ) from error
    path = Path(__file__).resolve().parents[1] / "schemas" / "native"
    try:
        schema = json.loads((path / f"{name}.schema.json").read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise NativeDeliveryError("Native schema cannot be loaded") from error
    _schema_validate(document, schema)
    return document


def _reject_claims(value: object) -> None:
    if isinstance(value, dict):
        if FORBIDDEN_FIELDS.intersection(value):
            raise NativeDeliveryError("unsupported Native guarantee field")
        for nested in value.values():
            _reject_claims(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_claims(nested)


def validate_verify_report(report: object) -> None:
    """Validate a v2 standalone report, including failed machine checks.

    Args:
        report: Parsed JSON report; legacy reports require their old reader.

    Raises:
        NativeDeliveryError: The report has invalid or unsupported evidence.
    """
    data = _validate(report, "verify-report")
    _reject_claims(data)
    results = data["results"]
    if data["total"] != len(results):
        raise NativeDeliveryError("total does not match results")
    errors = sum(result["status"] == "error" for result in results)
    violations = sum(result["status"] == "fail" for result in results)
    expected = "ERROR" if errors else "FAIL" if violations else "PASS"
    if (data["errors"], data["violations"], data["verdict"]) != (
        errors,
        violations,
        expected,
    ):
        raise NativeDeliveryError("Verify summary contradicts checks")
    if data["spec_drift"] != results[0]:
        raise NativeDeliveryError("spec_drift does not match first result")


def validate_review_report(
    report: object, expected_profile: str | None = None
) -> None:
    """Validate v2 review shape and declared actor separation.

    Args:
        report: Parsed review JSON; declarations are not identity attestation.
        expected_profile: Optional exact required review profile.

    Raises:
        NativeDeliveryError: Profile, fields or actor separation are invalid.
    """
    data = _validate(report, "review-report")
    if (
        expected_profile is not None
        and data["review_profile"] != expected_profile
    ):
        raise NativeDeliveryError("review profile mismatch")
    present = INDEPENDENCE_FIELDS.intersection(data)
    if data["review_profile"] == "strict":
        if present != INDEPENDENCE_FIELDS:
            raise NativeDeliveryError("strict independence declaration missing")
        if data["implementer_actor"].strip() == data["judge_actor"].strip():
            raise NativeDeliveryError("Judge must differ from implementer")
    elif present:
        raise NativeDeliveryError("non-strict review claims independence")
    _reject_claims(
        {
            key: value
            for key, value in data.items()
            if key not in INDEPENDENCE_FIELDS
        }
    )
    if data["verdict"] == "PASS" and (data["p0_count"] or data["p1_count"]):
        raise NativeDeliveryError("passing review has blocking findings")


def _claims(verdict: str, profile: str) -> list[str]:
    delivery = {
        "native-delivery-pass": "git-clean",
        "svn-pending-commit": "svn-working-copy-verified",
        "svn-revision-verified": "svn-revision-content-verified",
    }[verdict]
    claims = [
        delivery,
        "machine-verify",
        f"{profile}-review",
        "knowledge-impact",
    ]
    if profile == "strict":
        claims.append("strict-actor-separation-declared")
    return claims


def report_digest(report: dict[str, Any]) -> str:
    """Return a canonical content digest without trusting report paths."""
    encoded = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_verdict(
    verdict: object,
    *,
    verify_report: dict[str, Any] | None = None,
    review_report: dict[str, Any] | None = None,
) -> None:
    """Validate v2 structure; optionally compare actual loaded reports.

    Args:
        verdict: Parsed verdict; pending commit is not formal delivery.
        verify_report: Optional actual report loaded by the gate.
        review_report: Optional actual review loaded by the gate.

    Raises:
        NativeDeliveryError: Evidence is inconsistent or unbounded.
    """
    data = _validate(verdict, "native-delivery-verdict")
    evidence = data["evidence"]
    base = {
        "verify_report",
        "review_report",
        "verify_report_digest",
        "review_report_digest",
        "knowledge_impact",
        "knowledge_impact_reason",
    }
    profile = data["review_profile"]
    if profile == "strict":
        base |= INDEPENDENCE_FIELDS
        if not INDEPENDENCE_FIELDS.issubset(evidence):
            raise NativeDeliveryError("strict declaration missing")
        if (
            evidence["implementer_actor"].strip()
            == evidence["judge_actor"].strip()
        ):
            raise NativeDeliveryError("Judge must differ from implementer")
    kind = data["verdict"]
    if kind == "native-delivery-pass":
        fields = {"git_clean", "commit_sha"}
        expected_vcs = "git"
    elif kind == "svn-pending-commit":
        fields = {"repository_uuid", "repository_relative_url"}
        expected_vcs = "svn"
    else:
        fields = {
            "repository_uuid",
            "repository_relative_url",
            "revision",
            "revision_subject_id",
        }
        expected_vcs = "svn"
        if evidence.get("revision_subject_id") != data["subject_id"]:
            raise NativeDeliveryError("revision subject mismatch")
    if set(evidence) != base | fields or data["vcs"] != expected_vcs:
        raise NativeDeliveryError("delivery evidence does not match result")
    if data["verified_claims"] != _claims(kind, profile):
        raise NativeDeliveryError("verified claims do not match evidence")
    if data["unprovable_claims"] != list(UNPROVABLE_CLAIMS):
        raise NativeDeliveryError("Native guarantee boundaries missing")
    if (verify_report is None) != (review_report is None):
        raise NativeDeliveryError("both actual reports are required")
    if verify_report is not None and review_report is not None:
        _validate_bound_reports(
            verify_report, review_report, data["subject_id"], profile
        )
        for name, report in (
            ("verify_report", verify_report),
            ("review_report", review_report),
        ):
            if evidence[name + "_digest"] != report_digest(report):
                raise NativeDeliveryError("referenced report digest mismatch")
        if profile == "strict":
            if any(
                evidence[key] != review_report[key]
                for key in INDEPENDENCE_FIELDS
            ):
                raise NativeDeliveryError(
                    "strict declaration differs from review"
                )


def _validate_bound_reports(
    verify: dict[str, Any],
    review: dict[str, Any],
    subject_id: str,
    profile: str,
) -> None:
    validate_verify_report(verify)
    validate_review_report(review, profile)
    if verify["subject_id"] != subject_id or review["subject_id"] != subject_id:
        raise NativeDeliveryError("subject mismatch")
    if verify["verdict"] != "PASS" or review["verdict"] != "PASS":
        raise NativeDeliveryError("delivery requires passing reports")
    if review["scope"] != "integration":
        raise NativeDeliveryError("delivery requires integration review")


def build_verdict(
    verify_report: dict[str, Any],
    review_report: dict[str, Any],
    *,
    subject_id: str,
    vcs: str,
    delivery_evidence: dict[str, Any],
    verify_report_path: str,
    review_report_path: str,
    knowledge_impact: str,
    knowledge_impact_reason: str,
) -> dict[str, Any]:
    """Build bounded evidence from actual validated, content-matched reports.

    Args:
        verify_report: Machine-generated v2 Verify report.
        review_report: Reviewer's original v2 report.
        subject_id: Current independently captured subject identifier.
        vcs: Selected Git or SVN backend.
        delivery_evidence: Backend-specific gate-verified delivery facts.
        verify_report_path: Existing Verify evidence reference.
        review_report_path: Existing Review evidence reference.
        knowledge_impact: ``none`` or ``updated``.
        knowledge_impact_reason: Reason for the knowledge decision.

    Returns:
        Independent JSON snapshot with references and canonical digests.

    Raises:
        NativeDeliveryError: Any evidence is inconsistent or invalid.
    """
    validate_review_report(review_report)
    profile = review_report["review_profile"]
    _validate_bound_reports(verify_report, review_report, subject_id, profile)
    if vcs == "git":
        kind = "native-delivery-pass"
    elif vcs == "svn":
        kind = (
            "svn-revision-verified"
            if "revision" in delivery_evidence
            else "svn-pending-commit"
        )
    else:
        raise NativeDeliveryError("unsupported VCS")
    reserved = {
        "verify_report",
        "review_report",
        "verify_report_digest",
        "review_report_digest",
        "knowledge_impact",
        "knowledge_impact_reason",
    } | INDEPENDENCE_FIELDS
    if reserved.intersection(delivery_evidence):
        raise NativeDeliveryError("delivery evidence overrides report evidence")
    evidence = copy.deepcopy(delivery_evidence)
    evidence.update(
        verify_report=verify_report_path,
        review_report=review_report_path,
        verify_report_digest=report_digest(verify_report),
        review_report_digest=report_digest(review_report),
        knowledge_impact=knowledge_impact,
        knowledge_impact_reason=knowledge_impact_reason,
    )
    if profile == "strict":
        evidence.update(
            {key: review_report[key] for key in INDEPENDENCE_FIELDS}
        )
    result = {
        "schema_version": 2,
        "artifact_type": "native-delivery-verdict",
        "subject_id": subject_id,
        "vcs": vcs,
        "verdict": kind,
        "review_profile": profile,
        "evidence": evidence,
        "verified_claims": _claims(kind, profile),
        "unprovable_claims": list(UNPROVABLE_CLAIMS),
    }
    validate_verdict(
        result, verify_report=verify_report, review_report=review_report
    )
    return result
