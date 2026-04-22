#!/usr/bin/env bats

setup() {
  export INJECT_SCRIPT="$HOME/.buildrunner/scripts/inject-four-element.sh"
  export FETCH_SCRIPT="$HOME/.buildrunner/scripts/fetch-context-bundle.sh"
  export ROUTE_FIXTURE="$BATS_TEST_DIRNAME/../fixtures/route1.json"
  export OK_BUNDLE_FIXTURE="$BATS_TEST_DIRNAME/../fixtures/context_bundle_ok.json"
  export BAD_BUNDLE_FIXTURE="$BATS_TEST_DIRNAME/../fixtures/context_bundle_malformed.json"
}

@test "help documents injector contract" {
  run "$INJECT_SCRIPT" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"requires_user_confirmation"* ]]
}

@test "route fixture emits four-element keys" {
  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" --route-file "$2"' "$INJECT_SCRIPT" "$OK_BUNDLE_FIXTURE" "$ROUTE_FIXTURE"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
required = {"goal", "context", "constraints", "done_when", "requires_user_confirmation"}
assert required.issubset(data.keys())
PY
  [ "$status" -eq 0 ]
}

@test "ad hoc prompt requires user confirmation" {
  local route_file="$BATS_TEST_TMPDIR/adhoc.json"
  cat > "$route_file" <<'EOF'
{"bucket":"planning","prompt":"help me think about the login flow","user_message":"help me think about the login flow"}
EOF

  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" --route-file "$2"' "$INJECT_SCRIPT" "$OK_BUNDLE_FIXTURE" "$route_file"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["requires_user_confirmation"] is True
assert data["done_when"] == "Done-When: user confirms output in next turn"
PY
  [ "$status" -eq 0 ]
}

@test "spec shaped prompt does not require user confirmation" {
  local route_file="$BATS_TEST_TMPDIR/spec.json"
  cat > "$route_file" <<'EOF'
{"bucket":"backend-build","prompt":"implement the user-roles edge function so that tests/api/test_user_roles.py passes","user_message":"build user-roles edge function; done when tests/api/test_user_roles.py passes"}
EOF

  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" --route-file "$2"' "$INJECT_SCRIPT" "$OK_BUNDLE_FIXTURE" "$route_file"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["requires_user_confirmation"] is False
assert "tests/api/test_user_roles.py passes" in data["done_when"]
PY
  [ "$status" -eq 0 ]
}

@test "fetch fixture returns cache breakpoints" {
  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" claude-opus-4-7' "$FETCH_SCRIPT" "$OK_BUNDLE_FIXTURE"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["cache_breakpoints"] == ["static-system", "static-tools", "sliding-window", "dynamic-tail"]
assert isinstance(data["bundle"], dict)
PY
  [ "$status" -eq 0 ]
}

@test "fetch degrades gracefully when Jimmy unreachable" {
  run bash -lc 'JIMMY_HOST=127.0.0.1 JIMMY_PORT=1 "$0" claude-opus-4-7' "$FETCH_SCRIPT"
  [ "$status" -eq 0 ]
  [ "$output" = '{"bundle": {}, "error": "unreachable"}' ]
}

@test "coder bucket without done when refuses dispatch" {
  run "$INJECT_SCRIPT" --bucket backend-build --no-done-when
  [ "$status" -eq 10 ]
  [[ "$output" == *"DONE-WHEN MISSING: refuse to dispatch"* ]]
}

@test "planning bucket without done when stays soft" {
  run "$INJECT_SCRIPT" --bucket planning --no-done-when
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["requires_user_confirmation"] is True
assert data["done_when"] == "Done-When: user confirms output in next turn"
PY
  [ "$status" -eq 0 ]
}

@test "cache order violation is repaired and warned" {
  local stderr_file="$BATS_TEST_TMPDIR/cache.err"

  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" --route-file "$2" 2>"$3"' "$INJECT_SCRIPT" "$BAD_BUNDLE_FIXTURE" "$ROUTE_FIXTURE" "$stderr_file"
  [ "$status" -eq 0 ]

  run cat "$stderr_file"
  [ "$status" -eq 0 ]
  [[ "$output" == *"cache-order violation"* ]]

  run bash -lc 'env BR3_CONTEXT_BUNDLE_FIXTURE="$1" "$0" --route-file "$2" 2>/dev/null' "$INJECT_SCRIPT" "$BAD_BUNDLE_FIXTURE" "$ROUTE_FIXTURE"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["cache_breakpoints"] == ["static-system", "static-tools", "sliding-window", "dynamic-tail"]
assert data["cache_segments"][-1] == {"marker": "dynamic-tail", "dynamic": True}
PY
  [ "$status" -eq 0 ]
}

@test "injector keeps working when bundle fetch is unreachable" {
  run bash -lc 'JIMMY_HOST=127.0.0.1 JIMMY_PORT=1 "$0" --route-file "$1"' "$INJECT_SCRIPT" "$ROUTE_FIXTURE"
  [ "$status" -eq 0 ]
  run python3 - <<'PY' "$output"
import json
import sys

data = json.loads(sys.argv[1])
assert data["context_bundle_error"] == "unreachable"
assert data["bundle"] == {}
PY
  [ "$status" -eq 0 ]
}
