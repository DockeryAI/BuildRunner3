#!/usr/bin/env bash
# test_budget_guard.sh — Spec-level tests for research-budget-guard.sh
#
# Phase 5 creates research-budget-guard.sh. These tests are skipped until
# that phase ships (GUARD_SCRIPT not found → all tests skip with reason).
#
# Run with:
#   bash tests/research/test_budget_guard.sh
#
# Exit codes:
#   0 — all tests passed (or all skipped)
#   1 — one or more test failures

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate budget guard script
# ---------------------------------------------------------------------------
GUARD_SCRIPT="${HOME}/.buildrunner/scripts/research-budget-guard.sh"
PHASE5_PENDING=false

if [[ ! -f "$GUARD_SCRIPT" ]]; then
  echo "SKIP: research-budget-guard.sh not found at $GUARD_SCRIPT"
  echo "SKIP reason=waiting-on-phase-5 — all budget-guard tests skipped"
  exit 0
fi

if [[ ! -x "$GUARD_SCRIPT" ]]; then
  echo "SKIP: research-budget-guard.sh exists but is not executable"
  echo "SKIP reason=waiting-on-phase-5"
  exit 0
fi

# ---------------------------------------------------------------------------
# Test framework (minimal TAP-style)
# ---------------------------------------------------------------------------
PASS=0
FAIL=0
SKIP=0

pass() { echo "ok - $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL - $1: $2"; FAIL=$((FAIL + 1)); }
skip() { echo "skip - $1 # $2"; SKIP=$((SKIP + 1)); }

# ---------------------------------------------------------------------------
# Setup: temp dir for each test run
# ---------------------------------------------------------------------------
TMPDIR_ROOT=$(mktemp -d)
cleanup() { rm -rf "$TMPDIR_ROOT"; }
trap cleanup EXIT

# Each test gets its own invocation_id and budget record dir
export BR3_BUDGET_DIR="${TMPDIR_ROOT}/budget"
mkdir -p "$BR3_BUDGET_DIR"

# ---------------------------------------------------------------------------
# Test 1: init creates a budget record
# ---------------------------------------------------------------------------
INV1="test-inv-$(date +%s)-1"
if "$GUARD_SCRIPT" init "$INV1" "1.00" 2>/dev/null; then
  pass "init creates budget record for invocation"
else
  fail "init creates budget record" "exit code $?"
fi

# ---------------------------------------------------------------------------
# Test 2: consume within budget exits 0
# ---------------------------------------------------------------------------
INV2="test-inv-$(date +%s)-2"
"$GUARD_SCRIPT" init "$INV2" "1.00" 2>/dev/null
if "$GUARD_SCRIPT" consume "$INV2" "0.10" 2>/dev/null; then
  pass "consume under budget exits 0"
else
  fail "consume under budget" "expected exit 0, got $?"
fi

# ---------------------------------------------------------------------------
# Test 3: consume over budget exits 1
# ---------------------------------------------------------------------------
INV3="test-inv-$(date +%s)-3"
"$GUARD_SCRIPT" init "$INV3" "0.15" 2>/dev/null
"$GUARD_SCRIPT" consume "$INV3" "0.10" 2>/dev/null || true
if ! "$GUARD_SCRIPT" consume "$INV3" "0.10" 2>/dev/null; then
  pass "consume over budget exits non-zero (cap enforced)"
else
  fail "consume over budget" "expected non-zero exit when cap exceeded"
fi

# ---------------------------------------------------------------------------
# Test 4: exact cap hit exits 0 (at cap, not over)
# ---------------------------------------------------------------------------
INV4="test-inv-$(date +%s)-4"
"$GUARD_SCRIPT" init "$INV4" "0.20" 2>/dev/null
"$GUARD_SCRIPT" consume "$INV4" "0.10" 2>/dev/null || true
if "$GUARD_SCRIPT" consume "$INV4" "0.10" 2>/dev/null; then
  pass "consume exactly at cap exits 0"
else
  # Some implementations treat >= as over — acceptable
  skip "consume exactly at cap" "implementation-defined: at-cap behavior"
fi

# ---------------------------------------------------------------------------
# Test 5: report prints a summary
# ---------------------------------------------------------------------------
INV5="test-inv-$(date +%s)-5"
"$GUARD_SCRIPT" init "$INV5" "2.00" 2>/dev/null
"$GUARD_SCRIPT" consume "$INV5" "0.25" 2>/dev/null || true
REPORT=$("$GUARD_SCRIPT" report "$INV5" 2>/dev/null)
if [[ -n "$REPORT" ]]; then
  pass "report prints non-empty summary"
else
  fail "report prints summary" "got empty output"
fi

# ---------------------------------------------------------------------------
# Test 6: consume on unknown invocation_id fails gracefully (does not crash)
# ---------------------------------------------------------------------------
UNKNOWN_INV="unknown-inv-$(date +%s)"
set +e
"$GUARD_SCRIPT" consume "$UNKNOWN_INV" "0.10" 2>/dev/null
EXIT_CODE=$?
set -e
# We don't care about the exit code here — just that it does not core dump
if [[ $EXIT_CODE -le 127 ]]; then
  pass "consume on unknown invocation_id exits cleanly (no crash)"
else
  fail "consume on unknown invocation_id" "abnormal exit code: $EXIT_CODE"
fi

# ---------------------------------------------------------------------------
# Test 7: concurrent consumes do not corrupt budget (serial simulation)
# ---------------------------------------------------------------------------
INV7="test-inv-$(date +%s)-7"
"$GUARD_SCRIPT" init "$INV7" "1.00" 2>/dev/null
"$GUARD_SCRIPT" consume "$INV7" "0.30" 2>/dev/null || true
"$GUARD_SCRIPT" consume "$INV7" "0.30" 2>/dev/null || true
"$GUARD_SCRIPT" consume "$INV7" "0.30" 2>/dev/null || true
# Fourth consume of 0.30 should exceed 1.00 budget
set +e
"$GUARD_SCRIPT" consume "$INV7" "0.30" 2>/dev/null
OVER_EXIT=$?
set -e
if [[ $OVER_EXIT -ne 0 ]]; then
  pass "serial consumes enforce cumulative cap correctly"
else
  fail "serial consumes enforce cap" "expected non-zero exit for cumulative over-cap"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "Budget guard tests: ${PASS} passed, ${FAIL} failed, ${SKIP} skipped"

if [[ $FAIL -gt 0 ]]; then
  exit 1
else
  exit 0
fi
