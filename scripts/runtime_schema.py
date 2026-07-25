"""Validate runtime artifacts and derive deterministic runtime identifiers."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

DEFAULT_VERIFY_CONFIG = {"checks": []}
NATIVE_DELIVERY_VERDICT_SCHEMA = "native-delivery-verdict"
NATIVE_DELIVERY_VERIFIED_CLAIMS = (
    "git-clean",
    "machine-verify",
    "standard-review",
    "knowledge-impact",
)
NATIVE_DELIVERY_UNPROVABLE_CLAIMS = (
    "runtime-trust-gate",
    "harness-capability-probe",
    "run-manifest-evidence-graph",
    "strict-independent-review",
)
NON_BUDGET_EVENTS = frozenset(
    {
        "start",
        "quality_passed",
        "merge_success",
        "merge_failure",
        "manual",
        "manual_resolved",
        "unblock",
    }
)


class RuntimeSchemaError(Exception):
    """Raised when a runtime artifact or configuration violates its contract."""


def canonical_json_bytes(value: object) -> bytes:
    """Serialize a JSON value to the canonical UTF-8 form used for digests."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def build_run_config(
    profile: str,
    harness: str,
    workflow: str,
    max_attempts: int,
    verify_config_path: Path | None,
    required_capabilities: Sequence[str] = (),
    optional_capabilities: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the complete run-config document whose bytes define config_digest."""
    if max_attempts < 0:
        raise RuntimeSchemaError("max_attempts must be non-negative")
    if verify_config_path is None:
        verify_config: object = DEFAULT_VERIFY_CONFIG
    else:
        if not verify_config_path.is_file():
            raise RuntimeSchemaError("verify.config.json does not exist")
        try:
            verify_config = json.loads(verify_config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeSchemaError("verify.config.json cannot be parsed") from error
        if not isinstance(verify_config, dict):
            raise RuntimeSchemaError("verify.config.json must contain a JSON object")
    run_config = {
        "harness": harness,
        "max_attempts": max_attempts,
        "profile": profile,
        "required_capabilities": sorted(required_capabilities),
        "optional_capabilities": sorted(optional_capabilities),
        "verify_config": verify_config,
        "workflow": workflow,
    }
    validate_document(run_config, "run-config")
    return run_config


def config_digest(run_config: dict[str, Any]) -> str:
    """Return the SHA-256 digest of a validated canonical run-config document."""
    validate_document(run_config, "run-config")
    digest = hashlib.sha256(canonical_json_bytes(run_config)).hexdigest()
    return f"sha256:{digest}"


def build_native_delivery_verdict(
    review_report: str,
    verify_report: str,
    knowledge_impact: str,
    knowledge_impact_reason: str,
) -> dict[str, Any]:
    """Build the bounded verdict for a Native Delivery without a Runtime Run."""
    verdict = {
        "schema_version": 1,
        "artifact_type": "native-delivery-verdict",
        "verdict": "native-delivery-pass",
        "evidence": {
            "review_report": review_report,
            "verify_report": verify_report,
            "knowledge_impact": knowledge_impact,
            "knowledge_impact_reason": knowledge_impact_reason,
            "git_clean": True,
        },
        "verified_claims": list(NATIVE_DELIVERY_VERIFIED_CLAIMS),
        "unprovable_claims": list(NATIVE_DELIVERY_UNPROVABLE_CLAIMS),
    }
    validate_document(verdict, NATIVE_DELIVERY_VERDICT_SCHEMA)
    return verdict


def attempt_for_attempts(attempts: int) -> int:
    """Map consumed failed retries to the one-based current execution number."""
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        raise RuntimeSchemaError("attempts must be a non-negative integer")
    return attempts + 1


def attempts_after_event(attempts: int, event: str) -> int:
    """Return consumed retries after a workflow-control event."""
    attempt_for_attempts(attempts)
    if event == "failure":
        return attempts + 1
    if event in NON_BUDGET_EVENTS:
        return attempts
    raise RuntimeSchemaError(f"unknown workflow event: {event}")


def _schema_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "runtime"


def _load_schema(name: str) -> dict[str, Any]:
    path = _schema_dir() / f"{name}.schema.json"
    if not path.is_file():
        raise RuntimeSchemaError(f"unknown artifact type: {name}")
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeSchemaError(f"schema cannot be loaded: {name}") from error
    return schema


def _matches_type(value: object, expected: str) -> bool:
    """Return whether a value has one JSON Schema primitive type."""
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _validate_instance(
    value: object,
    schema: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    path: str = "<root>",
) -> None:
    """Validate the JSON Schema subset used by the runtime contracts."""
    if "$ref" in schema:
        reference = schema["$ref"]
        if reference not in registry:
            raise RuntimeSchemaError(f"{path}: unresolved schema reference")
        _validate_instance(value, registry[reference], registry, path)
    for part in schema.get("allOf", []):
        _validate_instance(value, part, registry, path)
    if "if" in schema:
        try:
            _validate_instance(value, schema["if"], registry, path)
            branch = schema.get("then")
        except RuntimeSchemaError:
            branch = schema.get("else")
        if branch is not None:
            _validate_instance(value, branch, registry, path)
    if "const" in schema and value != schema["const"]:
        raise RuntimeSchemaError(f"{path}: value does not match const")
    if "enum" in schema and value not in schema["enum"]:
        raise RuntimeSchemaError(f"{path}: value is not in enum")
    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_matches_type(value, item) for item in expected_types):
            raise RuntimeSchemaError(f"{path}: invalid JSON type")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise RuntimeSchemaError(f"{path}: string is too short")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise RuntimeSchemaError(f"{path}: string does not match pattern")
        if schema.get("format") == "date-time":
            if re.search(r"T.+(?:Z|[+-]\d{2}:\d{2})$", value) is None:
                raise RuntimeSchemaError(f"{path}: invalid date-time")
            try:
                datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise RuntimeSchemaError(f"{path}: invalid date-time") from error
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise RuntimeSchemaError(f"{path}: number is below minimum")
    if isinstance(value, list):
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_instance(item, item_schema, registry, f"{path}.{index}")
        if schema.get("uniqueItems"):
            serialized = [canonical_json_bytes(item) for item in value]
            if len(serialized) != len(set(serialized)):
                raise RuntimeSchemaError(f"{path}: array items are not unique")
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                raise RuntimeSchemaError(
                    f"{path}.{required}: required field is missing"
                )
        properties = schema.get("properties", {})
        for name, property_schema in properties.items():
            if name in value:
                _validate_instance(
                    value[name], property_schema, registry, f"{path}.{name}"
                )
        if schema.get("additionalProperties") is False:
            extras = value.keys() - properties.keys()
            if extras:
                raise RuntimeSchemaError(f"{path}: unexpected field {min(extras)}")


def validate_document(document: object, schema_name: str | None = None) -> None:
    """Validate a document against its versioned runtime JSON Schema."""
    if schema_name is None:
        if not isinstance(document, dict):
            raise RuntimeSchemaError("runtime artifact must be a JSON object")
        artifact_type = document.get("artifact_type")
        if not isinstance(artifact_type, str):
            raise RuntimeSchemaError("artifact_type is required")
        schema_name = artifact_type
    schema = _load_schema(schema_name)
    schemas = [
        json.loads(schema_path.read_text(encoding="utf-8"))
        for schema_path in _schema_dir().glob("*.schema.json")
    ]
    registry = {item["$id"]: item for item in schemas if "$id" in item}
    _validate_instance(document, schema, registry)
    if schema_name == "task-state":
        assert isinstance(document, dict)
        payload = document["payload"]
        if document["attempt"] != attempt_for_attempts(payload["attempts"]):
            raise RuntimeSchemaError(
                "attempt must equal task-state payload attempts + 1"
            )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate runtime protocol artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate one artifact")
    validate_parser.add_argument("artifact", type=Path)
    digest_parser = subparsers.add_parser("config-digest", help="print config digest")
    digest_parser.add_argument(
        "--profile", required=True, choices=("production", "tooling")
    )
    digest_parser.add_argument("--harness", required=True)
    digest_parser.add_argument("--workflow", required=True)
    digest_parser.add_argument("--max-attempts", type=int, required=True)
    digest_parser.add_argument("--verify-config", type=Path)
    digest_parser.add_argument("--required", action="append", default=[])
    digest_parser.add_argument("--optional", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the runtime schema CLI."""
    args = _parse_args(argv)
    try:
        if args.command == "validate":
            document = json.loads(args.artifact.read_text(encoding="utf-8"))
            validate_document(document)
            print("PASS")
            return 0
        run_config = build_run_config(
            args.profile,
            args.harness,
            args.workflow,
            args.max_attempts,
            args.verify_config,
            args.required,
            args.optional,
        )
        print(config_digest(run_config))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeSchemaError):
        print("runtime schema operation failed", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("runtime schema operation interrupted", file=sys.stderr)
        return 130
    except Exception:  # Boundary keeps unknown exception details out of terminals.
        print("runtime schema operation failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
