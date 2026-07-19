"""Product-neutral Harness capability probing and adapter contract."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

import runtime_schema

CAPABILITIES = (
    "subagents",
    "worktree_isolation",
    "transcript_access",
    "lifecycle_hooks",
    "structured_tool_results",
)
CAPABILITY_STATES = frozenset({"supported", "degraded", "unsupported"})
_PROCESS_CLEANUP_TIMEOUT_SECONDS = 5.0


class HarnessError(Exception):
    """Raised when an Adapter or capability document violates the contract."""


def _kill_process_tree(
    process: subprocess.Popen[str], timeout: float
) -> bool:
    """Bound process-tree termination and report whether tree cleanup succeeded."""
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                timeout=max(0.001, timeout),
                check=False,
            )
            if completed.returncode == 0:
                return True
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                return True
            except ProcessLookupError:
                if process.poll() is not None:
                    return True
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        process.kill()
    except (OSError, ProcessLookupError):
        return process.poll() is not None
    return False


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _close_process_pipes(process: subprocess.Popen[str]) -> None:
    for pipe in (process.stdin, process.stdout, process.stderr):
        try:
            if pipe is not None:
                pipe.close()
        except OSError:
            pass


def _cleanup_timed_out_process(
    process: subprocess.Popen[str], timeout_error: subprocess.TimeoutExpired
) -> tuple[str, str, bool]:
    """Terminate an Adapter tree and collect output within one hard deadline."""
    deadline = time.monotonic() + _PROCESS_CLEANUP_TIMEOUT_SECONDS
    tree_terminated = _kill_process_tree(
        process, max(0.001, deadline - time.monotonic())
    )
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        _close_process_pipes(process)
        return (
            _timeout_output(timeout_error.output),
            _timeout_output(timeout_error.stderr),
            False,
        )
    try:
        stdout, stderr = process.communicate(timeout=remaining)
        return stdout or "", stderr or "", tree_terminated
    except subprocess.TimeoutExpired as cleanup_error:
        stdout = _timeout_output(cleanup_error.output or timeout_error.output)
        stderr = _timeout_output(cleanup_error.stderr or timeout_error.stderr)
        _close_process_pipes(process)
        try:
            process.kill()
        except (OSError, ProcessLookupError):
            pass
        remaining = deadline - time.monotonic()
        if remaining > 0:
            try:
                process.wait(timeout=remaining)
            except (OSError, subprocess.TimeoutExpired):
                pass
        return stdout, stderr, False


def _abort_process(process: subprocess.Popen[str]) -> None:
    """Best-effort cleanup for non-timeout communication failures."""
    deadline = time.monotonic() + _PROCESS_CLEANUP_TIMEOUT_SECONDS
    _kill_process_tree(process, max(0.001, deadline - time.monotonic()))
    _close_process_pipes(process)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return
    try:
        process.wait(timeout=remaining)
    except (OSError, subprocess.TimeoutExpired):
        pass


class SubprocessHarnessAdapter:
    """Exchange product-neutral JSON requests with one Harness process."""

    def __init__(self, command: Sequence[str], timeout_seconds: float = 120.0):
        if not command:
            raise HarnessError("adapter command is required")
        if timeout_seconds <= 0:
            raise HarnessError("adapter timeout must be positive")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds

    def request(self, operation: str, payload: object) -> dict[str, Any]:
        """Send one request and require a JSON object response."""
        request = json.dumps(
            {"contract_version": 1, "operation": operation, "payload": payload},
            ensure_ascii=False,
        )
        child_env = os.environ.copy()
        child_env.update(
            {
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        process_kwargs: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "encoding": "utf-8",
            "errors": "strict",
            "env": child_env,
        }
        if os.name == "nt":
            process_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            process_kwargs["start_new_session"] = True
        try:
            process = subprocess.Popen(self._command, **process_kwargs)
        except OSError as error:
            raise HarnessError("adapter execution failed") from error
        try:
            stdout, stderr = process.communicate(
                input=request, timeout=self._timeout_seconds
            )
        except subprocess.TimeoutExpired as error:
            _, _, cleanup_complete = _cleanup_timed_out_process(process, error)
            detail = "" if cleanup_complete else "; process tree cleanup incomplete"
            raise HarnessError(f"adapter execution timed out{detail}") from error
        except (OSError, UnicodeError) as error:
            _abort_process(process)
            raise HarnessError("adapter execution failed") from error
        if process.returncode != 0:
            raise HarnessError("adapter returned nonzero")
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise HarnessError("adapter output is not JSON") from error
        if not isinstance(response, dict):
            raise HarnessError("adapter response must be an object")
        return response

    def probe(self, harness: str) -> dict[str, Any]:
        """Probe every capability through the executable Adapter contract."""
        return self.request(
            "probe", {"harness": harness, "capabilities": list(CAPABILITIES)}
        )

    def evaluate(self, case: dict[str, Any]) -> dict[str, Any]:
        """Execute one behavior-evaluation case through the same Adapter."""
        return self.request("evaluate", case)


def load_declaration(path: Path) -> dict[str, Any]:
    """Load a static declaration without treating it as runtime evidence."""
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
        runtime_schema.validate_document(declaration, "harness-capability")
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        runtime_schema.RuntimeSchemaError,
    ) as error:
        raise HarnessError("invalid capability declaration") from error
    return declaration


def validate_probe(harness: str, response: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a complete runtime probe response."""
    if response.get("contract_version") != 1 or response.get("harness") != harness:
        raise HarnessError("probe identity mismatch")
    capabilities = response.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != set(CAPABILITIES):
        raise HarnessError("probe must report the complete capability vocabulary")
    for capability, result in capabilities.items():
        if not isinstance(result, dict):
            raise HarnessError(f"invalid probe result: {capability}")
        if result.get("status") not in CAPABILITY_STATES:
            raise HarnessError(f"invalid capability state: {capability}")
        if not isinstance(result.get("evidence"), str) or not result["evidence"]:
            raise HarnessError(f"missing capability evidence: {capability}")
    return {
        "schema_version": 1,
        "harness": harness,
        "capabilities": capabilities,
    }


def gate_capabilities(
    snapshot: dict[str, Any],
    required: Sequence[str],
    optional: Sequence[str],
) -> dict[str, Any]:
    """Fail closed for required capabilities and record every optional downgrade."""
    required_set = set(required)
    optional_set = set(optional)
    unknown = (required_set | optional_set) - set(CAPABILITIES)
    if unknown:
        raise HarnessError(f"unknown capability: {min(unknown)}")
    overlap = required_set & optional_set
    if overlap:
        raise HarnessError(
            f"capability cannot be both required and optional: {min(overlap)}"
        )
    capabilities = snapshot["capabilities"]
    blockers = [
        capability
        for capability in sorted(required_set)
        if capabilities[capability]["status"] != "supported"
    ]
    degradations = []
    for capability in sorted(optional_set):
        result = capabilities[capability]
        if result["status"] == "supported":
            continue
        degradations.append(
            {
                "event_type": "capability-degraded",
                "capability": capability,
                "status": result["status"],
                "evidence": result["evidence"],
            }
        )
    return {
        **snapshot,
        "required_capabilities": sorted(required_set),
        "optional_capabilities": sorted(optional_set),
        "blocking_capabilities": blockers,
        "degradations": degradations,
        "verdict": "PASS" if not blockers else "FAIL",
    }


def startup_probe(
    declaration: dict[str, Any],
    adapter: SubprocessHarnessAdapter,
    required: Sequence[str],
    optional: Sequence[str],
    run_id: str = "",
) -> dict[str, Any]:
    """Probe at startup; static declarations never override observed results."""
    harness = declaration["harness"]
    observed = validate_probe(harness, adapter.probe(harness))
    report = gate_capabilities(observed, required, optional)
    report["declaration_capabilities"] = declaration["capabilities"]
    report["evidence_source"] = "runtime-adapter-probe"
    if run_id:
        report["run_id"] = run_id
    return report


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
    parser = argparse.ArgumentParser(description="Probe a Harness capability contract")
    parser.add_argument("--declaration", required=True, type=Path)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--adapter-arg", action="append", default=[])
    parser.add_argument("--adapter-timeout", type=float, default=120.0)
    parser.add_argument("--required", action="append", default=[])
    parser.add_argument("--optional", action="append", default=[])
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Probe capabilities before workflow side effects and write the evidence report."""
    args = _parse_args(argv)
    try:
        declaration = load_declaration(args.declaration)
        adapter = SubprocessHarnessAdapter(
            [args.adapter, *args.adapter_arg], args.adapter_timeout
        )
        report = startup_probe(
            declaration,
            adapter,
            args.required,
            args.optional,
            args.run_id or "",
        )
        _atomic_write_json(args.output, report)
        print(report["verdict"])
        return 0 if report["verdict"] == "PASS" else 1
    except (OSError, HarnessError):
        print("Harness capability probe failed", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Harness capability probe interrupted", file=sys.stderr)
        return 130
    except Exception:
        print("Harness capability probe failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
