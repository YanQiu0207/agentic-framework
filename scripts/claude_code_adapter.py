#!/usr/bin/env python3
"""Claude Code harness adapter for the machine-verifiable agent runtime.

Implements the SubprocessHarnessAdapter contract (contract v1): read one JSON
request from stdin, write one JSON response to stdout, exit 0.

Operations:
- probe: report Claude Code's capability matrix. Used by ``init-run`` to run the
  Harness startup capability gate. This is the only operation on the init-run
  path.
- evaluate: execute one behavior-evaluation case. Not on the init-run path
  (used by skill evaluation); returns a structured not-executed response so any
  caller still gets a well-formed object.

The adapter does NOT dispatch task implementation. Task execution is performed
by the orchestrator (the Claude Code main session, which dispatches owner
subagents via the Task tool). The adapter only reports the harness capabilities
that the runtime protocol probes at startup.
"""

from __future__ import annotations

import json
import sys
from typing import Any

CONTRACT_VERSION = 1

# Claude Code capability matrix. ``status`` reflects the features this run
# actually relies on; ``evidence`` cites the concrete harness feature backing
# each claim, so the capability gate is auditable rather than asserted.
CAPABILITIES: dict[str, dict[str, str]] = {
    "subagents": {
        "status": "supported",
        "evidence": (
            "Task tool dispatches nested subagents "
            "(Claude Code >= 2.1.172, 5-level nesting cap)"
        ),
    },
    "worktree_isolation": {
        "status": "supported",
        "evidence": "EnterWorktree tool backed by git worktree isolates per-task changes",
    },
    "transcript_access": {
        "status": "supported",
        "evidence": "Session transcript is readable within the Claude Code session",
    },
    "lifecycle_hooks": {
        "status": "supported",
        "evidence": (
            "settings.json hooks (SessionStart, UserPromptSubmit, Stop, etc.) "
            "provide lifecycle hooks"
        ),
    },
    "structured_tool_results": {
        "status": "supported",
        "evidence": "Tool calls return structured JSON results consumed by the orchestrator",
    },
}


def _probe(harness: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "harness": harness,
        "capabilities": CAPABILITIES,
    }


def _evaluate(case: dict[str, Any]) -> dict[str, Any]:
    # Behavior evaluation is not on the init-run path (which only probes).
    # Return a structured not-executed response instead of crashing, so any
    # caller exercising evaluate still receives a well-formed object.
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "not_executed",
        "reason": "claude-code adapter does not execute behavior-evaluation cases",
        "case": case,
    }


def main() -> int:
    try:
        request = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        json.dump({"error": f"invalid request json: {error}"}, sys.stdout)
        return 1

    operation = request.get("operation")
    payload = request.get("payload", {})
    if operation == "probe":
        harness = payload.get("harness", "claude-code") if isinstance(payload, dict) else "claude-code"
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
