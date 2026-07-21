#!/usr/bin/env python3
"""Codex harness adapter for the machine-verifiable agent runtime.

The adapter implements the contract consumed by ``SubprocessHarnessAdapter``:
read one JSON request from stdin, write one JSON response to stdout, and exit.

This adapter deliberately reports only the capabilities that this adapter can
establish without assuming product-specific orchestration features. Codex can
therefore use the Runtime in the fallback orchestration mode; unsupported
capabilities fail closed when a workflow marks them as required.
"""

from __future__ import annotations

import json
import sys
from typing import Any

CONTRACT_VERSION = 1

CAPABILITIES: dict[str, dict[str, str]] = {
    "subagents": {
        "status": "unsupported",
        "evidence": (
            "Codex adapter does not claim nested subagent dispatch; use the "
            "workflow fallback orchestration mode."
        ),
    },
    "worktree_isolation": {
        "status": "unsupported",
        "evidence": (
            "Codex adapter does not claim product-provided worktree isolation; "
            "the workflow must establish isolation explicitly."
        ),
    },
    "transcript_access": {
        "status": "supported",
        "evidence": (
            "Codex rollout transcripts are persisted as JSONL session records "
            "and are consumable by the framework telemetry tooling."
        ),
    },
    "lifecycle_hooks": {
        "status": "unsupported",
        "evidence": "Codex adapter does not claim a Claude Code-compatible hook contract.",
    },
    "structured_tool_results": {
        "status": "supported",
        "evidence": "Codex tool invocations expose structured tool results to the host session.",
    },
}


def _probe(harness: str) -> dict[str, Any]:
    """Return the Codex capability matrix for one Runtime probe."""
    return {
        "contract_version": CONTRACT_VERSION,
        "harness": harness,
        "capabilities": CAPABILITIES,
    }


def _evaluate(case: dict[str, Any]) -> dict[str, Any]:
    """Return a valid non-executed evaluation response."""
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "not_executed",
        "reason": "codex adapter does not execute behavior-evaluation cases",
        "case": case,
    }


def main() -> int:
    """Process one JSON request from stdin."""
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        json.dump({"error": f"invalid request json: {error}"}, sys.stdout)
        return 1

    operation = request.get("operation")
    payload = request.get("payload", {})
    if operation == "probe":
        harness = (
            payload.get("harness", "codex")
            if isinstance(payload, dict)
            else "codex"
        )
        response = _probe(harness)
    elif operation == "evaluate":
        response = _evaluate(payload if isinstance(payload, dict) else {})
    else:
        response = {
            "contract_version": CONTRACT_VERSION,
            "error": f"unknown operation: {operation}",
        }
    json.dump(response, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
