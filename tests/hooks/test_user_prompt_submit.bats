#!/usr/bin/env bats

setup() {
  export REAL_HOME="$HOME"
  export HOOK_SOURCE="$REAL_HOME/.buildrunner/hooks/user-prompt-submit-route.sh"
  export INSTALLER_SOURCE="$REAL_HOME/.buildrunner/scripts/install-user-prompt-hook.sh"

  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME/.buildrunner/hooks" "$HOME/.buildrunner/scripts" "$HOME/.buildrunner/config" "$HOME/.claude"

  cp "$HOOK_SOURCE" "$HOME/.buildrunner/hooks/user-prompt-submit-route.sh"
  cp "$INSTALLER_SOURCE" "$HOME/.buildrunner/scripts/install-user-prompt-hook.sh"
  chmod 755 "$HOME/.buildrunner/hooks/user-prompt-submit-route.sh" "$HOME/.buildrunner/scripts/install-user-prompt-hook.sh"

  export HOOK_SCRIPT="$HOME/.buildrunner/hooks/user-prompt-submit-route.sh"
  export INSTALLER_SCRIPT="$HOME/.buildrunner/scripts/install-user-prompt-hook.sh"
  export CLASSIFIER_STUB="$BATS_TEST_TMPDIR/classify-prompt.sh"
  export MATRIX_PATH="$HOME/.buildrunner/config/default-role-matrix.yaml"
  export ROUTES_DIR="$HOME/.buildrunner/routes"
  export ROUTING_LOG="$HOME/.buildrunner/logs/routing.log"
  export DECISIONS_LOG="$HOME/.buildrunner/decisions.log"

  cat > "$CLASSIFIER_STUB" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${BR3_CLASSIFIER_STUB_BUCKET:-}" ]]; then
  printf '%s\n' "$BR3_CLASSIFIER_STUB_BUCKET"
  exit 0
fi
if [[ "${BR3_CLASSIFIER_STUB_MODE:-ok}" == 'fail' ]]; then
  printf 'classifier boom\n' >&2
  exit 2
fi
printf 'review\n'
EOF
  chmod 755 "$CLASSIFIER_STUB"

  cat > "$MATRIX_PATH" <<'EOF'
version: 1
buckets:
  review:
    primary: claude-sonnet-4-6
  planning:
    primary: claude-opus-4-7
  backend-build:
    primary: gpt-5.4
EOF

  cat > "$HOME/.claude/settings.json" <<'EOF'
{
  "permissions": {
    "allow": ["Bash"],
    "deny": [],
    "ask": []
  },
  "model": "claude-opus-4-7",
  "hooks": {
    "PostToolUse": [{"matcher":"Bash","hooks":[{"type":"command","command":"echo post"}]}],
    "PreToolUse": [{"matcher":"Bash","hooks":[{"type":"command","command":"echo pre"}]}],
    "SessionStart": [{"hooks":[{"type":"command","command":"echo start"}]}],
    "Stop": [{"hooks":[{"type":"command","command":"echo stop"}]}],
    "UserPromptSubmit": [{"hooks":[{"type":"command","command":"bash ~/.buildrunner/hooks/auto-context.sh","timeout":8}]}]
  }
}
EOF
}

perm_octal() {
  if stat -f '%OLp' "$1" >/dev/null 2>&1; then
    stat -f '%OLp' "$1"
  else
    stat -c '%a' "$1"
  fi
}

route_event() {
  cat <<EOF
{"session_id":"$1","prompt":"$2","user_message":"$2"}
EOF
}

@test "installer merges UserPromptSubmit hook idempotently and preserves hook keys" {
  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]

  run jq '.hooks | keys' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"PostToolUse"'* ]]
  [[ "$output" == *'"PreToolUse"'* ]]
  [[ "$output" == *'"SessionStart"'* ]]
  [[ "$output" == *'"Stop"'* ]]
  [[ "$output" == *'"UserPromptSubmit"'* ]]

  run jq '.hooks.UserPromptSubmit | length' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
  [ "$output" -eq 2 ]

  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]
  run jq '.hooks.UserPromptSubmit | length' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
  [ "$output" -eq 2 ]
}

@test "hook writes secure route file from JSON event" {
  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-review","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$MATRIX_PATH" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  [ -d "$ROUTES_DIR" ]
  [ "$(perm_octal "$ROUTES_DIR")" = "700" ]
  [ -f "$ROUTES_DIR/s-review.json" ]
  [ "$(perm_octal "$ROUTES_DIR/s-review.json")" = "600" ]

  run jq -r '.bucket,.prompt,.override,.builder' "$ROUTES_DIR/s-review.json"
  [ "$status" -eq 0 ]
  [ "$output" = $'review
review this diff
false
claude' ]
}

@test "override writes route file and decision log" {
  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-override","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" BR3_FORCE_BUILDER=claude BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$MATRIX_PATH" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  run jq -r '.override,.builder' "$ROUTES_DIR/s-override.json"
  [ "$status" -eq 0 ]
  [ "$output" = $'true
claude' ]

  run cat "$DECISIONS_LOG"
  [ "$status" -eq 0 ]
  [[ "$output" == *'BR3_FORCE_BUILDER=claude override'* ]]
}

@test "classifier failure fails open with log entry" {
  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-fail","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" BR3_CLASSIFIER_STUB_MODE=fail BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$MATRIX_PATH" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ ! -f "$ROUTES_DIR/s-fail.json" ]

  run cat "$ROUTING_LOG"
  [ "$status" -eq 0 ]
  [[ "$output" == *'routing failed open'* ]]
}

@test "unreadable matrix fails open and does not break" {
  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-matrix","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$HOME/.buildrunner/config/missing-matrix.yaml" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ ! -f "$ROUTES_DIR/s-matrix.json" ]

  run cat "$ROUTING_LOG"
  [ "$status" -eq 0 ]
  [[ "$output" == *'routing failed open'* ]]
}

@test "Jimmy-down does not block routing" {
  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-jimmy","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" JIMMY_HOST=127.0.0.1 JIMMY_PORT=1 BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$MATRIX_PATH" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
  [ -f "$ROUTES_DIR/s-jimmy.json" ]
}

@test "route rotation keeps last 200 files" {
  run python3 - <<'PY' "$ROUTES_DIR"
import os
import sys
import time

route_dir = sys.argv[1]
os.makedirs(route_dir, exist_ok=True)
for index in range(205):
    path = os.path.join(route_dir, f'old-{index:03d}.json')
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('{}\n')
    os.chmod(path, 0o600)
    ts = 1_700_000_000 + index
    os.utime(path, (ts, ts))
PY
  [ "$status" -eq 0 ]

  run bash -lc 'route_event() { cat <<EOF
{"session_id":"s-rotate","prompt":"review this diff","user_message":"review this diff"}
EOF
}; route_event | env HOME="$0" BR3_CLASSIFIER_SCRIPT="$1" BR3_ROLE_MATRIX_PATH="$2" "$3"' "$HOME" "$CLASSIFIER_STUB" "$MATRIX_PATH" "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]

  run bash -lc 'find "$0" -maxdepth 1 -type f -name "*.json" | wc -l | tr -d " "' "$ROUTES_DIR"
  [ "$status" -eq 0 ]
  [ "$output" -eq 200 ]
  [ -f "$ROUTES_DIR/s-rotate.json" ]
}
