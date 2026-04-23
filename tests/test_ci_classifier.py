"""
tests/test_ci_classifier.py

Accuracy regression tests for ci-classifier.sh.

Tests run the classifier script in regex-only mode (BR3_CI_CLASSIFY=regex-only)
against the labeled fixture set. This ensures no regressions in the fast regex
path, regardless of Below availability.

The labeled fixture file lives at tests/fixtures/ci_failures.jsonl.
Each record has: id, log, expected ("fixable"|"real"), expected_pattern.

Target: ≥90% accuracy on the labeled set.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "ci_failures.jsonl"
CLASSIFIER = Path.home() / ".buildrunner" / "scripts" / "ship" / "ci" / "ci-classifier.sh"


def _load_fixtures():
    if not FIXTURES.exists():
        return []
    records = []
    for line in FIXTURES.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _run_classifier(log_content: str, mode: str = "regex-only") -> tuple[str, int]:
    """Run ci-classifier.sh against log_content. Returns (stdout, exit_code)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tf:
        tf.write(log_content)
        tf.flush()
        env = {**os.environ, "BR3_CI_CLASSIFY": mode}
        result = subprocess.run(
            ["bash", str(CLASSIFIER), tf.name],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        os.unlink(tf.name)
        return result.stdout.strip(), result.returncode


# ---------------------------------------------------------------------------
# Smoke tests (critical patterns always classified correctly)
# ---------------------------------------------------------------------------


class TestClassifierSmoke:
    def test_eslint_is_fixable(self):
        log = "  5:1  error  'React' is defined but never used  @typescript-eslint/no-unused-vars\n✖ 1 error"
        out, rc = _run_classifier(log)
        assert rc == 0, f"Expected fixable (exit 0), got {rc}: {out}"
        assert "fixable" in out

    def test_typescript_error_is_real(self):
        log = "src/api/client.ts:12:5 - error TS2345: Argument mismatch"
        out, rc = _run_classifier(log)
        assert rc == 1, f"Expected real (exit 1), got {rc}: {out}"
        assert "real" in out

    def test_unit_test_failure_is_real(self):
        log = "FAIL src/utils/format.test.ts\n  ● format › should format correctly\n    AssertionError"
        out, rc = _run_classifier(log)
        assert rc == 1, f"Expected real (exit 1), got {rc}: {out}"

    def test_playwright_timeout_is_fixable(self):
        log = "page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000"
        out, rc = _run_classifier(log)
        assert rc == 0, f"Expected fixable (exit 0), got {rc}: {out}"

    def test_migration_failure_is_real(self):
        log = "Migration failed: column 'id' already exists"
        out, rc = _run_classifier(log)
        assert rc == 1

    def test_prettier_failure_is_fixable(self):
        log = "Prettier --check failed\n[warn] src/pages/index.tsx\nCode style issues found in 1 file."
        out, rc = _run_classifier(log)
        assert rc == 0

    def test_unknown_defaults_to_real(self):
        log = "Something totally unrecognized happened in the CI pipeline"
        out, rc = _run_classifier(log)
        assert rc == 1, f"Unknown should default to real, got {rc}: {out}"

    def test_rollback_flag_bypasses_below(self):
        """BR3_CI_CLASSIFY=regex-only must not invoke Below even for novel failures."""
        log = "NOVEL_FAILURE_TYPE_xyz: something weird happened"
        out, rc = _run_classifier(log, mode="regex-only")
        # Should return real (safe default) without hanging
        assert rc == 1
        assert "regex-only" in out or "unclassified" in out


# ---------------------------------------------------------------------------
# Accuracy regression (labeled fixture set ≥90%)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not CLASSIFIER.exists(),
    reason=f"ci-classifier.sh not found at {CLASSIFIER}",
)
class TestClassifierAccuracy:
    def test_accuracy_on_labeled_set(self):
        """Accuracy ≥90% on the labeled CI failure fixture set."""
        records = _load_fixtures()
        if not records:
            pytest.skip("No labeled fixtures found at tests/fixtures/ci_failures.jsonl")

        correct = 0
        total = len(records)
        failures = []

        for record in records:
            log = record["log"]
            expected = record["expected"]  # "fixable" or "real"
            fixture_id = record["id"]

            out, rc = _run_classifier(log)

            # Exit code 0 = fixable, 1 = real
            predicted = "fixable" if rc == 0 else "real"

            if predicted == expected:
                correct += 1
            else:
                failures.append({
                    "id": fixture_id,
                    "expected": expected,
                    "predicted": predicted,
                    "output": out,
                })

        accuracy = correct / total
        failure_summary = "\n".join(
            f"  {f['id']}: expected={f['expected']} predicted={f['predicted']} output={f['output']!r}"
            for f in failures
        )

        assert accuracy >= 0.90, (
            f"CI classifier accuracy {accuracy:.1%} ({correct}/{total}) below 90% threshold.\n"
            f"Failures:\n{failure_summary}"
        )

    def test_no_fixable_misclassified_as_real_for_lint(self):
        """Lint/format patterns must never be misclassified as real."""
        lint_records = [r for r in _load_fixtures() if r.get("expected_pattern") in ("lint", "format")]
        for r in lint_records:
            out, rc = _run_classifier(r["log"])
            assert rc == 0, (
                f"Lint/format pattern {r['id']!r} misclassified as real.\nOutput: {out}"
            )

    def test_no_typescript_misclassified_as_fixable(self):
        """TypeScript errors must always be real — never fixable."""
        ts_records = [r for r in _load_fixtures() if r.get("expected_pattern") == "typescript"]
        for r in ts_records:
            out, rc = _run_classifier(r["log"])
            assert rc == 1, (
                f"TypeScript error {r['id']!r} misclassified as fixable.\nOutput: {out}"
            )

    def test_no_migration_misclassified_as_fixable(self):
        """Migration failures must always be real — never fixable."""
        mig_records = [r for r in _load_fixtures() if r.get("expected_pattern") == "migration"]
        for r in mig_records:
            out, rc = _run_classifier(r["log"])
            assert rc == 1, (
                f"Migration failure {r['id']!r} misclassified as fixable.\nOutput: {out}"
            )
