"""Opus arbiter for one-round cross-model review."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from core.cluster.log_utils import _append_decision_log
from core.cluster.review_verdict import Verdict, VerdictDict

_CIRCUIT_WINDOW_SECONDS = 60
_CIRCUIT_THRESHOLD = 3
_DEFAULT_ARBITER_MODEL = "claude-opus-4-7"
_DEFAULT_ARBITER_MAX_TOKENS = 2048
_ADAPTIVE_THINKING = {"type": "adaptive", "display": "summarized"}
_BETA_HEADERS = {"anthropic-beta": "task-budgets-2026-03-13"}


def _user_home() -> Path:
    return Path("~").expanduser()


def _circuit_state_path() -> Path:
    return _user_home() / ".buildrunner" / "state" / "arbiter-circuit.json"



def _default_circuit_state() -> dict[str, Any]:
    return {
        "state": "closed",
        "error_timestamps": [],
        "opened_at": None,
        "last_error": None,
        "last_opus_payload": None,
    }


def _load_circuit_state() -> dict[str, Any]:
    path = _circuit_state_path()
    if not path.exists():
        return _default_circuit_state()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "r", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                state = json.loads(fh.read())
            except (OSError, json.JSONDecodeError):
                return _default_circuit_state()
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except OSError:
        return _default_circuit_state()
    merged = _default_circuit_state()
    merged.update(state)
    return merged


def _save_circuit_state(state: dict[str, Any]) -> None:
    path = _circuit_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Open in 'a' mode so the file descriptor exists without premature truncation,
    # acquire LOCK_EX, then truncate + write atomically inside the lock.
    with open(path, "a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            fh.truncate(0)
            fh.write(json.dumps(state, indent=2) + "\n")
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _log_decision(event: str, details: str = "") -> None:
    """Append an arbiter event to decisions.log via log_utils (flock-guarded)."""
    _append_decision_log("ARBITER", event, details)


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", None) or []
    for block in content:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            return block.text
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
            return str(block["text"])
    return getattr(message, "text", "") or ""


def _parse_arbiter_response(raw_text: str) -> dict[str, str]:
    match = re.search(r"\{[\s\S]*\}", raw_text or "")
    if not match:
        raise ValueError("arbiter response did not contain a JSON object")
    payload = json.loads(match.group())
    verdict = str(payload.get("verdict") or "").upper()
    reasoning = str(payload.get("reasoning") or raw_text or "").strip()
    if verdict not in {"PASS", "BLOCK"}:
        raise ValueError("arbiter response verdict must be PASS or BLOCK")
    if not reasoning:
        raise ValueError("arbiter response reasoning missing")
    return {"verdict": verdict, "reasoning": reasoning}


def _plan_hash(plan: str, config: dict[str, Any]) -> str:
    provided = str(config.get("plan_hash") or "").strip()
    if provided:
        return provided
    return hashlib.sha256((plan or "").encode("utf-8")).hexdigest()[:16]


def _collect_blockers(reviewer_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reviewer in reviewer_findings:
        for finding in reviewer.get("findings", []):
            if not isinstance(finding, dict) or finding.get("severity") != "blocker":
                continue
            key = str(finding.get("finding") or finding)
            if key in seen:
                continue
            seen.add(key)
            blockers.append(finding)
    return blockers


def _fallback_verdict(
    *,
    plan_hash: str,
    reviewer_findings: list[dict[str, Any]],
    circuit_state: str,
    reason: str,
    fallback_logic: str,
    last_opus_payload: Any,
    duration_ms: int,
) -> VerdictDict:
    if reason == "circuit_open":
        status = "circuit_open"
        reasoning = "Arbiter circuit is open; committed BLOCK until human reset."
    else:
        status = "error"
        reasoning = "Arbiter failed after one retry; committed BLOCK per Rule #1."

    verdict = Verdict(
        pass_=False,
        verdict="BLOCK",
        reviewers=reviewer_findings,
        arbiter={
            "reasoning": reasoning,
            "duration_ms": duration_ms,
            "status": status,
            "reason": reason,
        },
        circuit_state=circuit_state,
        plan_hash=plan_hash,
        review_round=1,
        escalated=False,
        reason=reason,
        fallback_logic=fallback_logic,
        last_opus_payload=last_opus_payload,
        blockers=_collect_blockers(reviewer_findings),
        arbiter_reasoning=reasoning,
    )
    return verdict.as_dict()


def _record_error(state: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    now = time.time()
    timestamps = [ts for ts in state.get("error_timestamps", []) if now - ts <= _CIRCUIT_WINDOW_SECONDS]
    timestamps.append(now)
    state["error_timestamps"] = timestamps
    state["last_error"] = payload
    state["last_opus_payload"] = payload
    if len(timestamps) >= _CIRCUIT_THRESHOLD and now - timestamps[-_CIRCUIT_THRESHOLD] <= _CIRCUIT_WINDOW_SECONDS:
        state["state"] = "open"
        state["opened_at"] = now
        _save_circuit_state(state)
        _log_decision("circuit_tripped", f"reason=opus-error threshold={_CIRCUIT_THRESHOLD}")
        return state, True
    state["state"] = "closed"
    _save_circuit_state(state)
    return state, False


def _reset_error_streak(state: dict[str, Any]) -> None:
    state["state"] = "closed"
    state["error_timestamps"] = []
    state["opened_at"] = None
    state["last_error"] = None
    state["last_opus_payload"] = None
    _save_circuit_state(state)


def _arbiter_prompt(plan: str, reviewer_findings: list[dict[str, Any]]) -> str:
    serialized = json.dumps(reviewer_findings, indent=2)
    return (
        "You are the final arbiter for a one-round cross-model review.\n"
        "Commit the final verdict now. No follow-up round exists.\n\n"
        "Return ONLY a JSON object with this shape:\n"
        '{"verdict": "PASS"|"BLOCK", "reasoning": "<concise final reasoning>"}\n\n'
        f"Plan:\n{plan}\n\n"
        f"Reviewer findings:\n{serialized}\n"
    )


def arbitrate(plan: str, reviewer_findings: list[dict[str, Any]], config: dict[str, Any] | None = None) -> VerdictDict:
    """Return a final verdict and always commit a result, even on arbiter failure."""
    config = config or {}
    plan_hash = _plan_hash(plan, config)
    state = _load_circuit_state()

    if state.get("state") == "open":
        return _fallback_verdict(
            plan_hash=plan_hash,
            reviewer_findings=reviewer_findings,
            circuit_state="open",
            reason="circuit_open",
            fallback_logic="arbiter circuit open; human reset required",
            last_opus_payload=state.get("last_opus_payload"),
            duration_ms=0,
        )

    arbiter_cfg = config.get("arbiter", {})
    model = arbiter_cfg.get("model", _DEFAULT_ARBITER_MODEL)
    max_tokens = int(arbiter_cfg.get("max_tokens", _DEFAULT_ARBITER_MAX_TOKENS))
    prompt = _arbiter_prompt(plan, reviewer_findings)
    start = time.perf_counter()
    last_payload: dict[str, Any] | None = None

    for attempt in (1, 2):
        request_payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": dict(_ADAPTIVE_THINKING),
        }
        try:
            client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            message = client.messages.create(**request_payload, extra_headers=_BETA_HEADERS)
            raw_text = _extract_text(message)
            parsed = _parse_arbiter_response(raw_text)
            duration_ms = int((time.perf_counter() - start) * 1000)
            _reset_error_streak(state)
            verdict = Verdict(
                pass_=parsed["verdict"] == "PASS",
                verdict=parsed["verdict"],
                reviewers=reviewer_findings,
                arbiter={
                    "reasoning": parsed["reasoning"],
                    "duration_ms": duration_ms,
                    "status": "ok",
                },
                circuit_state="closed",
                plan_hash=plan_hash,
                review_round=1,
                escalated=False,
                blockers=_collect_blockers(reviewer_findings) if parsed["verdict"] == "BLOCK" else [],
                arbiter_reasoning=parsed["reasoning"],
            )
            return verdict.as_dict()
        except Exception as exc:  # noqa: BLE001
            last_payload = {
                "attempt": attempt,
                "request": request_payload,
                "error": str(exc),
            }

    duration_ms = int((time.perf_counter() - start) * 1000)
    state, tripped = _record_error(state, last_payload or {"error": "unknown"})
    if tripped:
        return _fallback_verdict(
            plan_hash=plan_hash,
            reviewer_findings=reviewer_findings,
            circuit_state="open",
            reason="circuit_open",
            fallback_logic="arbiter circuit tripped after three consecutive errors within 60s",
            last_opus_payload=last_payload,
            duration_ms=duration_ms,
        )
    return _fallback_verdict(
        plan_hash=plan_hash,
        reviewer_findings=reviewer_findings,
        circuit_state="closed",
        reason="arbiter-error",
        fallback_logic="arbiter API failed after one retry; BLOCK committed mechanically",
        last_opus_payload=last_payload,
        duration_ms=duration_ms,
    )
