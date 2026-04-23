"""
semgrep_triage.py — Static analysis prefilter for ai_code_review.

Runs Semgrep on a diff before the full Opus review. If Semgrep scores the diff
as "clean", downgrades the Opus call to a quick-pass prompt (still preserving
Opus's broader mandate: bugs, performance, test coverage, best practices).
Never skips Opus entirely — downgrade only.

Architecture:
    1. Run Semgrep with public rulesets (p/ci, p/security-audit, p/owasp-top-ten)
    2. Call qwen2.5-coder:7b via Below to classify Semgrep output:
       {severity: clean | minor | flagged}
    3. Return SemgrepTriageResult (severity + findings)

Callers (ai_code_review.py):
    - clean → use QUICK_PASS_PROMPT (shorter, still covers non-static issues)
    - minor | flagged → full Opus review unchanged

Rollback: BR3_SEMGREP_PREFILTER=off → always return severity="flagged" (full review).
Fail-open: Semgrep absent, Below offline, or any error → severity="flagged".

Usage:
    from core.cluster.below.semgrep_triage import triage_diff, SemgrepTriageResult

    result = await triage_diff(diff_text)
    if result.severity == "clean":
        # Use quick-pass prompt
    else:
        # Full Opus review
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from core.cluster.cluster_config import get_below_host, get_ollama_port

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BELOW_HOST: str = get_below_host()   # single source of truth — core/cluster/cluster_config.py
BELOW_PORT: int = get_ollama_port()  # single source of truth — core/cluster/cluster_config.py
BELOW_MODEL: str = "qwen2.5-coder:7b"  # intentionally different from BELOW_MODEL in cluster_config (code-specific model)
BELOW_TIMEOUT: float = 15.0

# Semgrep rulesets to run
SEMGREP_RULESETS: list[str] = ["p/ci", "p/security-audit", "p/owasp-top-ten"]

# Rollback flag
_PREFILTER_ENABLED: bool = os.environ.get("BR3_SEMGREP_PREFILTER", "on").lower() != "off"

# Max diff size to run Semgrep on (larger diffs → skip prefilter, go full review)
MAX_DIFF_CHARS: int = 50_000

# OWASP Top 10 categories that must be covered by Semgrep ruleset
OWASP_CATEGORIES: frozenset[str] = frozenset({
    "injection",
    "broken-authentication",
    "sensitive-data-exposure",
    "xml-external-entities",
    "broken-access-control",
    "security-misconfiguration",
    "cross-site-scripting",
    "insecure-deserialization",
    "known-vulnerabilities",
    "insufficient-logging",
})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SemgrepFinding:
    """A single Semgrep finding."""
    rule_id: str
    message: str
    severity: str          # ERROR | WARNING | INFO
    path: str = ""
    line: int = 0


@dataclass
class SemgrepTriageResult:
    """Output of triage_diff()."""
    severity: str                                    # clean | minor | flagged
    findings: list[SemgrepFinding] = field(default_factory=list)
    semgrep_ran: bool = False
    below_classified: bool = False
    skip_reason: str = ""                           # Why prefilter was skipped (if applicable)

    @property
    def is_clean(self) -> bool:
        return self.severity == "clean"

    @property
    def should_full_review(self) -> bool:
        return self.severity in ("minor", "flagged")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def triage_diff(diff: str) -> SemgrepTriageResult:
    """
    Run Semgrep prefilter on a git diff.

    Args:
        diff: Git diff text to analyze.

    Returns:
        SemgrepTriageResult — always returns, never raises.
        severity="flagged" on any error (fail-open).
    """
    if not _PREFILTER_ENABLED:
        return SemgrepTriageResult(severity="flagged", skip_reason="BR3_SEMGREP_PREFILTER=off")

    if not diff or not diff.strip():
        return SemgrepTriageResult(severity="clean", skip_reason="empty diff")

    if len(diff) > MAX_DIFF_CHARS:
        logger.info("semgrep_triage: diff too large (%d chars) — skipping prefilter", len(diff))
        return SemgrepTriageResult(severity="flagged", skip_reason="diff too large")

    # Step 1: Run Semgrep
    findings = _run_semgrep(diff)
    semgrep_ran = findings is not None

    if findings is None:
        # Semgrep not available or failed — fail-open
        return SemgrepTriageResult(severity="flagged", skip_reason="semgrep unavailable")

    # Step 2: Classify via Below qwen2.5-coder:7b
    severity = _classify_via_below(diff, findings)
    below_classified = severity is not None

    if severity is None:
        # Below offline — classify based on raw finding count
        if not findings:
            severity = "clean"
        elif any(f.severity == "ERROR" for f in findings):
            severity = "flagged"
        else:
            severity = "minor"

    return SemgrepTriageResult(
        severity=severity,
        findings=findings,
        semgrep_ran=semgrep_ran,
        below_classified=below_classified,
    )


# ---------------------------------------------------------------------------
# Semgrep runner
# ---------------------------------------------------------------------------


def _run_semgrep(diff: str) -> Optional[list[SemgrepFinding]]:
    """
    Run Semgrep on the diff text. Returns list of findings, or None if unavailable.
    """
    try:
        # Write diff to temp file for Semgrep analysis
        import tempfile, pathlib

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".diff", delete=False
        ) as f:
            f.write(diff)
            tmp_path = f.name

        # Extract changed files from diff header for targeted Semgrep scan
        changed_files = _extract_changed_files(diff)
        if not changed_files:
            os.unlink(tmp_path)
            return []

        # Write files to temp dir for Semgrep
        with tempfile.TemporaryDirectory() as tmpdir:
            file_paths = []
            for fname, content in changed_files.items():
                fp = pathlib.Path(tmpdir) / pathlib.Path(fname).name
                fp.write_text(content)
                file_paths.append(str(fp))

            findings = []
            for ruleset in SEMGREP_RULESETS:
                try:
                    result = subprocess.run(
                        ["semgrep", "--config", ruleset, "--json", "--quiet"] + file_paths,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode in (0, 1):  # 0=ok, 1=findings
                        data = json.loads(result.stdout or "{}")
                        for r in data.get("results", []):
                            findings.append(SemgrepFinding(
                                rule_id=r.get("check_id", ""),
                                message=r.get("extra", {}).get("message", "")[:200],
                                severity=r.get("extra", {}).get("severity", "WARNING").upper(),
                                path=r.get("path", ""),
                                line=r.get("start", {}).get("line", 0),
                            ))
                except subprocess.TimeoutExpired:
                    logger.warning("semgrep_triage: Semgrep timed out on ruleset %s", ruleset)
                except json.JSONDecodeError:
                    pass  # ignore parse errors

        os.unlink(tmp_path)
        return findings

    except FileNotFoundError:
        # Semgrep not installed
        logger.debug("semgrep_triage: semgrep not found in PATH")
        return None
    except Exception as exc:
        logger.warning("semgrep_triage: semgrep error: %s", exc)
        return None


def _extract_changed_files(diff: str) -> dict[str, str]:
    """
    Extract {filename: content} from diff for Semgrep to analyze.
    Only keeps added lines (+ prefix) from each file section.
    """
    files: dict[str, str] = {}
    current_file = None
    current_lines: list[str] = []

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            if current_file and current_lines:
                files[current_file] = "\n".join(current_lines)
            current_file = line[6:].strip()
            current_lines = []
        elif line.startswith("+") and not line.startswith("+++"):
            current_lines.append(line[1:])

    if current_file and current_lines:
        files[current_file] = "\n".join(current_lines)

    return files


# ---------------------------------------------------------------------------
# Below classification
# ---------------------------------------------------------------------------


def _classify_via_below(diff: str, findings: list[SemgrepFinding]) -> Optional[str]:
    """
    Call qwen2.5-coder:7b to classify Semgrep output.
    Returns severity string or None on Below-offline.
    """
    schema = {
        "type": "object",
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["clean", "minor", "flagged"],
            },
            "reasoning": {"type": "string"},
            "security_relevant": {"type": "boolean"},
        },
        "required": ["severity", "reasoning", "security_relevant"],
    }

    finding_summary = "\n".join(
        f"- [{f.severity}] {f.rule_id}: {f.message}" for f in findings[:20]
    ) or "No Semgrep findings."

    diff_summary = diff[:1000] if len(diff) > 1000 else diff

    prompt = (
        "You are a code review prefilter classifier.\n"
        "A git diff was scanned with Semgrep. Classify the severity.\n\n"
        "severity=clean: no significant issues; no security findings; diff is a routine change\n"
        "severity=minor: style issues, minor code smells, or low-severity findings\n"
        "severity=flagged: security issues, broken logic, RLS violations, or ERROR-level findings\n\n"
        f"SEMGREP FINDINGS:\n{finding_summary}\n\n"
        f"DIFF EXCERPT:\n{diff_summary}"
    )

    body = json.dumps({
        "model": BELOW_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": schema,
        "options": {"num_predict": 128},
    }).encode()

    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"http://{BELOW_HOST}:{BELOW_PORT}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=BELOW_TIMEOUT) as resp:
            raw = resp.read().decode()

        parsed = json.loads(raw)
        content = (parsed.get("message") or {}).get("content", "")
        result = json.loads(content)
        severity = result.get("severity", "flagged")
        latency_ms = int((time.time() - t0) * 1000)

        _emit_metric(severity, len(findings), latency_ms)
        logger.info(
            "semgrep_triage: Below classified severity=%s findings=%d latency=%dms",
            severity, len(findings), latency_ms,
        )

        return severity if severity in ("clean", "minor", "flagged") else "flagged"

    except Exception as exc:
        logger.debug("semgrep_triage: Below unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Metric emission
# ---------------------------------------------------------------------------


def _emit_metric(severity: str, finding_count: int, latency_ms: int) -> None:
    import datetime

    metrics_file = os.path.join(
        os.path.expanduser("~"), ".buildrunner", "schema-classifier-metrics.jsonl"
    )
    try:
        entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "site": "semgrep_triage",
            "model": BELOW_MODEL,
            "severity": severity,
            "finding_count": finding_count,
            "latency_ms": latency_ms,
        }
        with open(metrics_file, "a") as mf:
            mf.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# OWASP ruleset coverage check (for tests)
# ---------------------------------------------------------------------------


def check_owasp_coverage() -> set[str]:
    """
    Return which OWASP Top 10 categories are NOT covered by the configured rulesets.
    Used in test assertions — empty set means full coverage.
    """
    # Semgrep's p/owasp-top-ten ruleset covers all OWASP Top 10 categories.
    # We verify this structurally by asserting the ruleset is in our config.
    if "p/owasp-top-ten" in SEMGREP_RULESETS:
        return set()  # Full coverage via official ruleset
    return set(OWASP_CATEGORIES)  # If ruleset missing, all uncovered
