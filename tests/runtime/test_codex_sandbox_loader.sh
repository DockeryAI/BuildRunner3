#!/usr/bin/env bash
# tests/runtime/test_codex_sandbox_loader.sh
#
# Regression test for ~/.buildrunner/scripts/lib/codex-sandbox-config.sh.
# Asserts:
#   (a) zero --add-dir flags emitted when no .buildrunner/codex-sandbox.toml present
#   (b) expected --add-dir count + values when BR3 config present
#   (c) malformed config exits non-zero
#
# Exit 0 = all assertions pass, non-zero = first failing assertion.

set -euo pipefail

LOADER="${BR3_CODEX_SANDBOX_LOADER:-$HOME/.buildrunner/scripts/lib/codex-sandbox-config.sh}"
if [[ ! -x "$LOADER" ]]; then
  echo "FAIL: loader not executable at $LOADER" >&2
  exit 1
fi

TMPROOT="$(mktemp -d -t codex-sandbox-loader-test-XXXXXX)"
trap 'rm -rf "$TMPROOT"' EXIT

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1" >&2; exit 1; }

# (a) bare project, no .buildrunner/ at all
BARE="$TMPROOT/bare"
mkdir -p "$BARE"
out="$("$LOADER" "$BARE")"
if [[ -n "$out" ]]; then
  fail "(a) bare project should emit zero output, got: $out"
fi
pass "(a) bare project: zero output"

# (a2) project with .buildrunner/ but no codex-sandbox.toml
NOCONFIG="$TMPROOT/noconfig"
mkdir -p "$NOCONFIG/.buildrunner"
out="$("$LOADER" "$NOCONFIG")"
if [[ -n "$out" ]]; then
  fail "(a2) project without sandbox toml should emit zero output, got: $out"
fi
pass "(a2) .buildrunner/ exists but no sandbox toml: zero output"

# (b) BR3-shape config: two writable roots, expect 4 lines (--add-dir + value, x2)
GOOD="$TMPROOT/good"
mkdir -p "$GOOD/.buildrunner"
cat >"$GOOD/.buildrunner/codex-sandbox.toml" <<'TOML'
additional_writable_roots = [
  "~/.buildrunner/",
  "~/Library/LaunchAgents/",
]
TOML
out="$("$LOADER" "$GOOD")"
line_count="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
if [[ "$line_count" != "4" ]]; then
  fail "(b) expected 4 output lines (2 flags + 2 values), got $line_count: $out"
fi
addflag_count="$(printf '%s\n' "$out" | grep -c '^--add-dir$' || true)"
if [[ "$addflag_count" != "2" ]]; then
  fail "(b) expected exactly 2 '--add-dir' flag lines, got $addflag_count"
fi
expected_buildrunner="$HOME/.buildrunner"
expected_launch="$HOME/Library/LaunchAgents"
if ! printf '%s\n' "$out" | grep -qxF "$expected_buildrunner"; then
  fail "(b) expected expanded path '$expected_buildrunner' in output"
fi
if ! printf '%s\n' "$out" | grep -qxF "$expected_launch"; then
  fail "(b) expected expanded path '$expected_launch' in output"
fi
pass "(b) BR3 config: 2 --add-dir flags with expanded paths"

# (c) malformed TOML
BAD="$TMPROOT/bad"
mkdir -p "$BAD/.buildrunner"
cat >"$BAD/.buildrunner/codex-sandbox.toml" <<'TOML'
additional_writable_roots = "not-a-list"
TOML
if "$LOADER" "$BAD" >/dev/null 2>&1; then
  fail "(c) malformed config (string instead of list) should exit non-zero"
fi
pass "(c) malformed config exits non-zero"

# (c2) syntactically broken TOML
BAD2="$TMPROOT/bad2"
mkdir -p "$BAD2/.buildrunner"
cat >"$BAD2/.buildrunner/codex-sandbox.toml" <<'TOML'
additional_writable_roots = [unterminated
TOML
if "$LOADER" "$BAD2" >/dev/null 2>&1; then
  fail "(c2) syntactically broken TOML should exit non-zero"
fi
pass "(c2) broken TOML exits non-zero"

echo "ALL ASSERTIONS PASSED"
