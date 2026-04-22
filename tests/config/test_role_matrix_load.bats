#!/usr/bin/env bats

setup() {
  export LOADER="$HOME/.buildrunner/scripts/load-role-matrix.sh"
  export DISPATCH_CORE="$HOME/.buildrunner/scripts/_dispatch-core.sh"
  export DEFAULT_MATRIX="$HOME/.buildrunner/config/default-role-matrix.yaml"
  export SCHEMA="$HOME/.buildrunner/config/role-matrix.schema.json"
  export CACHE="$HOME/.buildrunner/config/.resolved-role-matrix.json"
  export TEST_TMPDIR
  TEST_TMPDIR="$(mktemp -d)"
}

teardown() {
  rm -rf "$TEST_TMPDIR"
  rm -f "$CACHE"
}

yaml_to_json() {
  python3 - "$1" <<'PY'
import json
import os
import sys

import yaml

path = os.path.expanduser(sys.argv[1])
with open(path, "r", encoding="utf-8") as handle:
    data = yaml.safe_load(handle)
json.dump(data, sys.stdout)
PY
}

validate_yaml_against_schema() {
  yaml_to_json "$1" | python3 -m jsonschema -i /dev/stdin "$SCHEMA"
}

@test "default matrix parses and contains nine buckets" {
  run python3 -c "import os, yaml; yaml.safe_load(open(os.path.expanduser('$DEFAULT_MATRIX'), encoding='utf-8'))"
  [ "$status" -eq 0 ]

  run yq '.buckets | length' "$DEFAULT_MATRIX"
  [ "$status" -eq 0 ]
  [ "$output" = "9" ]
}

@test "default matrix passes draft-07 schema validation" {
  run validate_yaml_against_schema "$DEFAULT_MATRIX"
  [ "$status" -eq 0 ]
}

@test "tampered matrix missing arbiter fails schema validation" {
  local tampered="$TEST_TMPDIR/missing-arbiter.yaml"

  python3 - "$DEFAULT_MATRIX" "$tampered" <<'PY'
import os
import sys

import yaml

source_path = os.path.expanduser(sys.argv[1])
target_path = sys.argv[2]

with open(source_path, "r", encoding="utf-8") as handle:
    data = yaml.safe_load(handle)

del data["buckets"]["ui-build"]["arbiter"]

with open(target_path, "w", encoding="utf-8") as handle:
    yaml.safe_dump(data, handle, sort_keys=False)
PY

  run validate_yaml_against_schema "$tampered"
  [ "$status" -ne 0 ]
}

@test "loader deep-merges ui-build effort override only" {
  local spec_file="$TEST_TMPDIR/override.yaml"
  local resolved_file="$TEST_TMPDIR/resolved.json"
  cat > "$spec_file" <<'EOF'
inherit: default-role-matrix
overrides:
  buckets:
    ui-build:
      effort: xhigh
EOF

  run bash -c '"$0" "$1" > "$2"' "$LOADER" "$spec_file" "$resolved_file"
  [ "$status" -eq 0 ]

  run jq -r '.buckets["ui-build"].effort' "$resolved_file"
  [ "$status" -eq 0 ]
  [ "$output" = "xhigh" ]

  run jq -r '.buckets["backend-build"].effort' "$resolved_file"
  [ "$status" -eq 0 ]
  [ "$output" = "medium" ]
}

@test "loader warns and ignores required-field removal overrides" {
  local spec_file="$TEST_TMPDIR/remove-required.yaml"
  local stdout_file="$TEST_TMPDIR/stdout.json"
  local stderr_file="$TEST_TMPDIR/stderr.txt"

  cat > "$spec_file" <<'EOF'
inherit: default-role-matrix
overrides:
  buckets:
    ui-build:
      arbiter: null
EOF

  run bash -c '"$0" "$1" > "$2" 2> "$3"' "$LOADER" "$spec_file" "$stdout_file" "$stderr_file"
  [ "$status" -eq 0 ]

  run cat "$stderr_file"
  [ "$status" -eq 0 ]
  [[ "$output" == *"attempted to remove required field 'buckets.ui-build.arbiter'"* ]]

  run jq -r '.buckets["ui-build"].arbiter' "$stdout_file"
  [ "$status" -eq 0 ]
  [ "$output" = "claude-opus-4-7" ]
}

@test "loader writes atomic cache with 0600 mode and fresh resolved_at" {
  run "$LOADER"
  [ "$status" -eq 0 ]

  run test -f "$CACHE"
  [ "$status" -eq 0 ]

  run jq -e . "$CACHE"
  [ "$status" -eq 0 ]

  run stat -f '%Lp' "$CACHE"
  [ "$status" -eq 0 ]
  [ "$output" = "600" ]

  run python3 - "$CACHE" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

cache_path = os.path.expanduser(sys.argv[1])
with open(cache_path, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

resolved_at = payload["resolved_at"]
resolved_dt = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
delta = abs((datetime.now(timezone.utc) - resolved_dt).total_seconds())

if delta > 5:
    raise SystemExit(1)
PY
  [ "$status" -eq 0 ]
}

@test "dispatch-core lookup reads resolved cache" {
  run "$LOADER"
  [ "$status" -eq 0 ]

  run env BUCKET=ui-build "$DISPATCH_CORE" lookup
  [ "$status" -eq 0 ]
  [ "$output" = "gpt-5.4" ]
}

@test "dispatch-core fails closed when cache is missing" {
  rm -f "$CACHE"

  run env BUCKET=ui-build "$DISPATCH_CORE" lookup
  [ "$status" -eq 2 ]
  [[ "$output" == *"role-matrix cache missing"* ]]
}
