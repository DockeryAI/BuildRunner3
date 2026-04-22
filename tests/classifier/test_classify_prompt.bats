#!/usr/bin/env bats

setup() {
  export SCRIPT="$HOME/.buildrunner/scripts/classify-prompt.sh"
  export FIXTURES="$BATS_TEST_DIRNAME/fixtures/labeled.tsv"
}

@test "help documents stdin stdout contract" {
  run "$SCRIPT" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"stdout: single line bucket name only"* ]]
}

@test "review prompt routes to review" {
  run "$SCRIPT" "review this diff"
  [ "$status" -eq 0 ]
  [ "$output" = "review" ]
}

@test "ui prompt routes to ui-build" {
  run "$SCRIPT" "build a react component for login"
  [ "$status" -eq 0 ]
  [ "$output" = "ui-build" ]
}

@test "planning prompt routes to planning" {
  run "$SCRIPT" "plan the next sprint"
  [ "$status" -eq 0 ]
  [ "$output" = "planning" ]
}

@test "architecture prompt routes to architecture" {
  run "$SCRIPT" "refactor the dispatch layer"
  [ "$status" -eq 0 ]
  [ "$output" = "architecture" ]
}

@test "terminal prompt routes to terminal-build" {
  run "$SCRIPT" "write a bash cron job"
  [ "$status" -eq 0 ]
  [ "$output" = "terminal-build" ]
}

@test "backend prompt routes to backend-build" {
  run "$SCRIPT" "add a supabase edge function"
  [ "$status" -eq 0 ]
  [ "$output" = "backend-build" ]
}

@test "classification prompt routes to classification" {
  run "$SCRIPT" "tag these prompts"
  [ "$status" -eq 0 ]
  [ "$output" = "classification" ]
}

@test "retrieval prompt routes to retrieval" {
  run "$SCRIPT" "find the user service"
  [ "$status" -eq 0 ]
  [ "$output" = "retrieval" ]
}

@test "qa prompt routes to qa" {
  run "$SCRIPT" "write playwright tests"
  [ "$status" -eq 0 ]
  [ "$output" = "qa" ]
}

@test "stdin contract accepts piped prompt" {
  run bash -lc 'printf %s "review this diff" | "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" = "review" ]
}

@test "ambiguous prompt escalates and defaults to backend-build when helper is unreachable" {
  run bash -lc 'env -u ANTHROPIC_API_KEY -u BR3_ANTHROPIC_API_KEY "$0" "do the thing" 2>"$1"' "$SCRIPT" "$BATS_TEST_TMPDIR/fallback.err"
  [ "$status" -eq 0 ]
  [ "$output" = "backend-build" ]
  run cat "$BATS_TEST_TMPDIR/fallback.err"
  [ "$status" -eq 0 ]
  [[ "$output" == *"AMBIGUOUS → haiku"* ]]
  [[ "$output" == *"fallback=backend-build"* ]]
}

@test "mocked haiku valid json wins" {
  run bash -lc 'env BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE="{\"bucket\":\"ui-build\"}" "$0" "do the thing" 2>"$1"' "$SCRIPT" "$BATS_TEST_TMPDIR/mock-valid.err"
  [ "$status" -eq 0 ]
  [ "$output" = "ui-build" ]
  run cat "$BATS_TEST_TMPDIR/mock-valid.err"
  [ "$status" -eq 0 ]
  [[ "$output" == *"AMBIGUOUS → haiku"* ]]
}

@test "mocked haiku timeout falls back to backend-build" {
  run bash -lc 'env BR3_CLASSIFIER_HAIKU_TIMEOUT_MS=50 BR3_CLASSIFIER_HAIKU_MOCK_DELAY_MS=150 BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE="{\"bucket\":\"ui-build\"}" "$0" "do the thing" 2>"$1"' "$SCRIPT" "$BATS_TEST_TMPDIR/mock-timeout.err"
  [ "$status" -eq 0 ]
  [ "$output" = "backend-build" ]
  run cat "$BATS_TEST_TMPDIR/mock-timeout.err"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fallback=backend-build reason=timeout"* ]]
}

@test "mocked truncated json falls back to backend-build" {
  run bash -lc 'env BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE="{\"bucket\":\"ui-build\"" "$0" "do the thing" 2>"$1"' "$SCRIPT" "$BATS_TEST_TMPDIR/mock-invalid.err"
  [ "$status" -eq 0 ]
  [ "$output" = "backend-build" ]
  run cat "$BATS_TEST_TMPDIR/mock-invalid.err"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fallback=backend-build reason=invalid_json"* ]]
}

@test "heuristic path stays under 50ms" {
  run python3 - "$SCRIPT" <<'PY'
import subprocess
import sys
import time

script = sys.argv[1]
start = time.perf_counter()
result = subprocess.run([script, "review this diff"], capture_output=True, text=True, check=False)
elapsed_ms = (time.perf_counter() - start) * 1000
print(f"elapsed_ms={elapsed_ms:.3f}")

if result.returncode != 0:
    raise SystemExit(result.returncode)
if result.stdout.strip() != "review":
    raise SystemExit(3)
if elapsed_ms >= 50.0:
    raise SystemExit(4)
PY
  [ "$status" -eq 0 ]
}

@test "fixtures cover forty prompts with at least ninety percent accuracy" {
  run python3 - "$SCRIPT" "$FIXTURES" <<'PY'
import csv
import subprocess
import sys

script = sys.argv[1]
fixtures = sys.argv[2]
rows = []

with open(fixtures, "r", encoding="utf-8") as handle:
    reader = csv.reader(handle, delimiter="\t")
    for row in reader:
        if not row:
            continue
        rows.append((row[0], row[1]))

if len(rows) < 40:
    raise SystemExit(2)

correct = 0
for prompt, expected in rows:
    result = subprocess.run([script, prompt], capture_output=True, text=True, check=False)
    actual = result.stdout.strip()
    if result.returncode == 0 and actual == expected:
        correct += 1

accuracy = correct / len(rows)
print(f"fixtures={len(rows)} accuracy={accuracy:.3f}")
if accuracy < 0.90:
    raise SystemExit(1)
PY
  [ "$status" -eq 0 ]
}
