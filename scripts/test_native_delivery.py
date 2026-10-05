"""Contract regressions for Native v2 report and result guarantees."""

import copy

import native_delivery as native
import pytest

SUBJECT = "sha256:" + "a" * 64


def reports(profile="standard"):
    result = dict(
        name="spec",
        type="exit-code",
        status="pass",
        detail="ok",
        value=None,
        new_items=[],
    )
    verify = dict(
        schema_version=2,
        subject_id=SUBJECT,
        verdict="PASS",
        total=1,
        errors=0,
        violations=0,
        warnings=[],
        results=[result],
        spec_drift=copy.deepcopy(result),
    )
    review = dict(
        schema_version=2,
        subject_id=SUBJECT,
        verdict="PASS",
        p0_count=0,
        p1_count=0,
        scope="integration",
        review_profile=profile,
        round=0,
    )
    if profile == "strict":
        review.update(
            implementer_actor="implementer",
            judge_actor="judge",
            independence_basis="Judge did not implement changes",
        )
    return verify, review


def build(profile="standard", vcs="git", evidence=None, scoped=False):
    verify, review = reports(profile)
    if evidence is None:
        evidence = dict(git_clean=True, commit_sha="b" * 40)
    return native.build_verdict(
        verify,
        review,
        subject_id=SUBJECT,
        vcs=vcs,
        delivery_evidence=evidence,
        verify_report_path="verify.json",
        review_report_path="review.json",
        knowledge_impact="none",
        knowledge_impact_reason="No knowledge impact",
        scoped=scoped,
    )


@pytest.mark.parametrize("profile", ["lightweight", "standard", "strict"])
def test_each_profile_builds_bounded_verdict(profile):
    verdict = build(profile)
    native.validate_verdict(
        verdict,
        verify_report=reports(profile)[0],
        review_report=reports(profile)[1],
    )
    assert isinstance(verdict["evidence"]["review_report"], str)
    assert "strong-identity-isolation" in verdict["unprovable_claims"]


@pytest.mark.parametrize("version", [None, 1, 3, True])
def test_legacy_and_unknown_reports_require_legacy_reader(version):
    verify, review = reports()
    for report, validator in [
        (verify, native.validate_verify_report),
        (review, native.validate_review_report),
    ]:
        if version is None:
            del report["schema_version"]
        else:
            report["schema_version"] = version
        with pytest.raises(native.NativeDeliveryError):
            validator(report)


@pytest.mark.parametrize("field", sorted(native.FORBIDDEN_FIELDS))
def test_verify_rejects_nested_runtime_and_independence_claims(field):
    verify, _ = reports()
    verify["results"][0]["value"] = [{field: True}]
    verify["spec_drift"] = copy.deepcopy(verify["results"][0])
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verify_report(verify)


@pytest.mark.parametrize(
    "mutation", ["missing", "same", "whitespace", "boolean", "extra"]
)
def test_strict_invalid_declarations_rejected(mutation):
    _, review = reports("strict")
    if mutation == "missing":
        del review["independence_basis"]
    elif mutation == "same":
        review["judge_actor"] = " implementer "
    elif mutation == "whitespace":
        review["independence_basis"] = "  "
    elif mutation == "boolean":
        review["independence_basis"] = True
    else:
        review["strict_independent_review"] = True
    with pytest.raises(native.NativeDeliveryError):
        native.validate_review_report(review)


@pytest.mark.parametrize("profile", ["standard", "lightweight"])
def test_other_profiles_cannot_claim_independence(profile):
    _, review = reports(profile)
    review["judge_actor"] = "judge"
    with pytest.raises(native.NativeDeliveryError):
        native.validate_review_report(review)


@pytest.mark.parametrize(
    "mutation", ["subject", "total", "counter", "status", "empty", "bool"]
)
def test_invalid_verify_rejected(mutation):
    verify, _ = reports()
    if mutation == "subject":
        del verify["subject_id"]
    elif mutation == "total":
        verify["total"] = 2
    elif mutation == "counter":
        verify["errors"] = 1
    elif mutation == "status":
        verify["results"][0]["status"] = "fail"
    elif mutation == "empty":
        verify["results"] = []
    else:
        verify["errors"] = False
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verify_report(verify)


def test_failed_verify_is_readable_but_cannot_build_delivery():
    verify, review = reports()
    verify["results"][0]["status"] = "fail"
    verify["spec_drift"] = copy.deepcopy(verify["results"][0])
    verify.update(verdict="FAIL", violations=1)
    native.validate_verify_report(verify)
    with pytest.raises(native.NativeDeliveryError):
        native.build_verdict(
            verify,
            review,
            subject_id=SUBJECT,
            vcs="git",
            delivery_evidence=dict(git_clean=True, commit_sha="b" * 40),
            verify_report_path="v",
            review_report_path="r",
            knowledge_impact="none",
            knowledge_impact_reason="reason",
        )


@pytest.mark.parametrize("revision", [None, 4])
def test_svn_states_require_identity_and_exact_subject(revision):
    evidence = dict(repository_uuid="uuid", repository_relative_url="^/trunk")
    if revision is not None:
        evidence.update(revision=revision, revision_subject_id=SUBJECT)
    verdict = build(vcs="svn", evidence=evidence)
    assert verdict["verdict"] == (
        "svn-pending-commit" if revision is None else "svn-revision-verified"
    )
    verdict["evidence"]["git_clean"] = True
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verdict(verdict)


@pytest.mark.parametrize(
    "mutation", ["digest", "subject", "profile", "scope", "p1", "actor"]
)
def test_actual_report_recheck_prevents_forged_verdict(mutation):
    verdict = build("strict")
    verify, review = reports("strict")
    if mutation == "digest":
        verify["warnings"].append("changed")
    elif mutation == "subject":
        review["subject_id"] = "sha256:" + "c" * 64
    elif mutation == "profile":
        verdict["review_profile"] = "standard"
    elif mutation == "scope":
        review["scope"] = "task"
    elif mutation == "p1":
        review["p1_count"] = 1
    else:
        verdict["evidence"]["judge_actor"] = "someone_else"
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verdict(
            verdict, verify_report=verify, review_report=review
        )


def test_expected_profile_is_exact_and_verdict_is_snapshot():
    verify, review = reports()
    with pytest.raises(native.NativeDeliveryError):
        native.validate_review_report(review, "strict")
    verdict = build()
    verify["warnings"].append("later change")
    native.validate_verdict(verdict)
    assert "strict-actor-separation-declared" not in verdict["verified_claims"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object()])
def test_verify_rejects_non_json_values(value):
    verify, _ = reports()
    verify["results"][0]["value"] = value
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verify_report(verify)


def test_only_one_actual_report_is_not_partial_attestation():
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verdict(build(), verify_report=reports()[0])


def test_svn_revision_subject_mismatch_is_not_formal_delivery():
    with pytest.raises(native.NativeDeliveryError):
        build(
            vcs="svn",
            evidence=dict(
                repository_uuid="uuid",
                repository_relative_url="^/trunk",
                revision=2,
                revision_subject_id="sha256:" + "d" * 64,
            ),
        )


def test_git_scoped_delivery_binds_scope_and_residue_digest():
    """Scoped Git v2 终态：冻结范围与残留摘要入证据，不伪造 git_clean。"""
    verify, review = reports()
    verdict = build(
        evidence=dict(
            commit_sha="b" * 40,
            scope_paths=["scripts", "docs"],
            residue_snapshot_digest="sha256:" + "e" * 64,
        ),
        scoped=True,
    )
    assert verdict["verdict"] == "git-scoped-delivery-pass"
    assert "git-scoped-delivery" in verdict["verified_claims"]
    assert "git-clean" not in verdict["verified_claims"]
    assert "git_clean" not in verdict["evidence"]
    native.validate_verdict(verdict, verify_report=verify, review_report=review)

    forged = copy.deepcopy(verdict)
    forged["evidence"]["git_clean"] = True
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verdict(forged)

    emptied = copy.deepcopy(verdict)
    emptied["evidence"]["scope_paths"] = []
    with pytest.raises(native.NativeDeliveryError):
        native.validate_verdict(emptied)

    with pytest.raises(native.NativeDeliveryError):
        build(
            vcs="svn",
            evidence=dict(
                repository_uuid="uuid",
                repository_relative_url="^/trunk",
            ),
            scoped=True,
        )
