#!/usr/bin/env bats

setup() {
  export REAL_HOME="$HOME"
  export REAL_USER="${USER:-tester}"
  export SYSTEM_PATH="$PATH"
  export PYTHON_BIN_DIR="$(dirname "$(command -v python3)")"
  export SOURCE_FLIP="$REAL_HOME/.buildrunner/scripts/flip-enforcement.sh"
  export SOURCE_MISS_RATE="$REAL_HOME/.buildrunner/scripts/miss-rate-calc.py"
  export FIXTURE_DIR="$BATS_TEST_DIRNAME/fixtures"

  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME/.buildrunner/scripts" "$HOME/.buildrunner/config" "$HOME/.buildrunner/logs" "$HOME/bin"

  cp "$SOURCE_FLIP" "$HOME/.buildrunner/scripts/flip-enforcement.sh"
  cp "$SOURCE_MISS_RATE" "$HOME/.buildrunner/scripts/miss-rate-calc.py"
  chmod 755 "$HOME/.buildrunner/scripts/flip-enforcement.sh" "$HOME/.buildrunner/scripts/miss-rate-calc.py"

  export FLIP_SCRIPT="$HOME/.buildrunner/scripts/flip-enforcement.sh"
  export MISS_RATE_SCRIPT="$HOME/.buildrunner/scripts/miss-rate-calc.py"
  export STATE_FILE="$BATS_TEST_TMPDIR/rollout-state.yaml"
  export DECISIONS_LOG="$BATS_TEST_TMPDIR/decisions.log"
  export STUB_BIN="$HOME/bin"
  export BATS_STUB_LOG="$BATS_TEST_TMPDIR/bats-stub.log"
  export BR3_NOW="2026-04-22T00:00:00Z"
  export BR3_REPO_ROOT="$BATS_TEST_DIRNAME/../.."

  : > "$BATS_STUB_LOG"
}

copy_fixture() {
  local name="$1"
  cp "$FIXTURE_DIR/$name" "$STATE_FILE"
}

write_dispatch_metrics_db() {
  local db_path="$1"
  local total_rows="$2"
  local overridden_rows="$3"

  python3 - "$db_path" "$total_rows" "$overridden_rows" <<'PY'
from __future__ import annotations

import datetime as dt
import sqlite3
import sys

db_path = sys.argv[1]
total_rows = int(sys.argv[2])
overridden_rows = int(sys.argv[3])
now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

conn = sqlite3.connect(db_path)
try:
    conn.execute(
        """
        CREATE TABLE dispatch_metrics (
          timestamp TEXT NOT NULL,
          session_id TEXT NOT NULL,
          bucket TEXT NOT NULL,
          builder TEXT NOT NULL,
          model TEXT NOT NULL,
          effort TEXT NOT NULL,
          prompt_tokens INTEGER NOT NULL DEFAULT 0,
          output_tokens INTEGER NOT NULL DEFAULT 0,
          latency_ms INTEGER NOT NULL DEFAULT 0,
          done_when_passed INTEGER NOT NULL DEFAULT 0,
          verdict TEXT NOT NULL,
          override_reason TEXT,
          route_file_path TEXT NOT NULL DEFAULT ''
        )
        """
    )
    rows = []
    for index in range(total_rows):
        verdict = "overridden" if index < overridden_rows else "passed"
        reason = "manual" if verdict == "overridden" else None
        timestamp = (now - dt.timedelta(hours=1, minutes=index)).isoformat().replace("+00:00", "Z")
        rows.append(
            (
                timestamp,
                f"session-{index}",
                "build",
                "codex",
                "gpt-5.4",
                "xhigh",
                1,
                1,
                1,
                1,
                verdict,
                reason,
                "",
            )
        )
    conn.executemany(
        """
        INSERT INTO dispatch_metrics (
          timestamp, session_id, bucket, builder, model, effort,
          prompt_tokens, output_tokens, latency_ms, done_when_passed,
          verdict, override_reason, route_file_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
finally:
    conn.close()
PY
}

install_stub_bats() {
  local mode="$1"
  cat > "$STUB_BIN/bats" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "${BATS_STUB_LOG}"
case "${BR3_BATS_MODE:-pass}" in
  pass)
    exit 0
    ;;
  fail)
    echo "stubbed bats failure" >&2
    exit 1
    ;;
  *)
    echo "unknown bats stub mode" >&2
    exit 1
    ;;
esac
EOF
  chmod 755 "$STUB_BIN/bats"
  export BR3_BATS_MODE="$mode"
}

run_flip() {
  run env \
    HOME="$HOME" \
    USER="$REAL_USER" \
    PATH="$STUB_BIN:$SYSTEM_PATH" \
    BR3_NOW="$BR3_NOW" \
    BR3_REPO_ROOT="$BR3_REPO_ROOT" \
    BR3_DECISIONS_LOG="$DECISIONS_LOG" \
    BR3_METRICS_SOURCE="${BR3_METRICS_SOURCE:-sqlite://$BATS_TEST_TMPDIR/metrics.db}" \
    BATS_STUB_LOG="$BATS_STUB_LOG" \
    bash "$FLIP_SCRIPT" "$@"
}

@test "day-1 without override fails watch period gate" {
  copy_fixture "day1-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 10 0
  install_stub_bats pass

  run_flip --state-file "$STATE_FILE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"WATCH-PERIOD:"* ]]
  [[ "$output" == *"6 day(s) remaining"* ]]
}

@test "day-8 with five percent miss rate flips to enforcing" {
  copy_fixture "day8-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 20 1
  install_stub_bats pass

  run_flip --state-file "$STATE_FILE"
  [ "$status" -eq 0 ]

  run grep '^mode: enforcing$' "$STATE_FILE"
  [ "$status" -eq 0 ]
  run grep '^flipped_at: 2026-04-22T00:00:00Z$' "$STATE_FILE"
  [ "$status" -eq 0 ]
}

@test "day-8 with fifteen percent miss rate fails miss rate gate" {
  copy_fixture "day8-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 20 3
  install_stub_bats pass

  run_flip --state-file "$STATE_FILE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"MISS-RATE:"* ]]
}

@test "day-1 override with justification succeeds and logs override" {
  copy_fixture "day1-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 10 0
  install_stub_bats pass

  run_flip --state-file "$STATE_FILE" --override-watch-period --justification "reason"
  [ "$status" -eq 0 ]

  run grep 'flip-override watch-period justification="reason"' "$DECISIONS_LOG"
  [ "$status" -eq 0 ]
  run grep '^mode: enforcing$' "$STATE_FILE"
  [ "$status" -eq 0 ]
}

@test "override without justification exits non-zero" {
  copy_fixture "day1-watch-only.yaml"
  install_stub_bats pass

  run_flip --state-file "$STATE_FILE" --override-watch-period
  [ "$status" -ne 0 ]
  [[ "$output" == *"USAGE:"* ]]
}

@test "rollback with reason reverts to watch-only and logs rollback" {
  copy_fixture "enforcing.yaml"

  run_flip --state-file "$STATE_FILE" --rollback --reason "operator rollback"
  [ "$status" -eq 0 ]

  run grep '^mode: watch-only$' "$STATE_FILE"
  [ "$status" -eq 0 ]
  run grep '^flipped_at: null$' "$STATE_FILE"
  [ "$status" -eq 0 ]
  run grep 'flip-rollback reason="operator rollback"' "$DECISIONS_LOG"
  [ "$status" -eq 0 ]
}

@test "rollback without reason exits non-zero" {
  copy_fixture "enforcing.yaml"

  run_flip --state-file "$STATE_FILE" --rollback
  [ "$status" -ne 0 ]
  [[ "$output" == *"USAGE:"* ]]
}

@test "validate-schema succeeds for valid fixture and does not rewrite file" {
  copy_fixture "day8-watch-only.yaml"
  original_contents="$(cat "$STATE_FILE")"

  run_flip --validate-schema --state-file "$STATE_FILE"
  [ "$status" -eq 0 ]
  [ "$(cat "$STATE_FILE")" = "$original_contents" ]
}

@test "validate-schema fails for corrupt fixture" {
  copy_fixture "invalid-missing-mode.yaml"

  run_flip --validate-schema --state-file "$STATE_FILE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"SCHEMA:"* ]]
}

@test "phase-5 gate fails when bats reports failure" {
  copy_fixture "day8-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 10 0
  install_stub_bats fail

  run_flip --state-file "$STATE_FILE"
  [ "$status" -ne 0 ]
  [[ "$output" == *"PHASE-5-TESTS:"* ]]
}

@test "phase-5 gate fails closed when bats is missing" {
  copy_fixture "day8-watch-only.yaml"
  write_dispatch_metrics_db "$BATS_TEST_TMPDIR/metrics.db" 10 0

  local ISOLATED_BIN="$BATS_TEST_TMPDIR/isolated-bin"
  mkdir -p "$ISOLATED_BIN"
  ln -sf "$(command -v python3)" "$ISOLATED_BIN/python3"
  [ ! -e "$ISOLATED_BIN/bats" ]

  run env \
    HOME="$HOME" \
    USER="$REAL_USER" \
    PATH="$ISOLATED_BIN:/usr/bin:/bin:/usr/sbin:/sbin" \
    BR3_NOW="$BR3_NOW" \
    BR3_REPO_ROOT="$BR3_REPO_ROOT" \
    BR3_DECISIONS_LOG="$DECISIONS_LOG" \
    BR3_METRICS_SOURCE="sqlite://$BATS_TEST_TMPDIR/metrics.db" \
    bash "$FLIP_SCRIPT" --state-file "$STATE_FILE"

  [ "$status" -ne 0 ]
  [[ "$output" == *"PHASE-5-TESTS: bats not installed"* ]]
}
