#!/usr/bin/env bats

setup() {
  export REAL_HOME="$HOME"
  export HOOK_SOURCE="$REAL_HOME/.buildrunner/hooks/pre-tool-use-gate.sh"
  export INSTALLER_SOURCE="$REAL_HOME/.buildrunner/scripts/install-pre-tool-use-hook.sh"

  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p \
    "$HOME/.buildrunner/hooks" \
    "$HOME/.buildrunner/scripts" \
    "$HOME/.buildrunner/config" \
    "$HOME/.buildrunner/routes" \
    "$HOME/.buildrunner/logs" \
    "$HOME/.claude"

  cp "$HOOK_SOURCE" "$HOME/.buildrunner/hooks/pre-tool-use-gate.sh"
  cp "$INSTALLER_SOURCE" "$HOME/.buildrunner/scripts/install-pre-tool-use-hook.sh"
  chmod 755 "$HOME/.buildrunner/hooks/pre-tool-use-gate.sh" "$HOME/.buildrunner/scripts/install-pre-tool-use-hook.sh"

  export HOOK_SCRIPT="$HOME/.buildrunner/hooks/pre-tool-use-gate.sh"
  export INSTALLER_SCRIPT="$HOME/.buildrunner/scripts/install-pre-tool-use-hook.sh"
  export ROUTES_DIR="$HOME/.buildrunner/routes"
  export WATCH_LOG="$HOME/.buildrunner/logs/pretool-watch.log"
  export DECISIONS_LOG="$HOME/.buildrunner/decisions.log"
  export ROLLOUT_WATCH="$HOME/.buildrunner/config/rollout-state.yaml"
  export ROLLOUT_ENFORCING="$HOME/.buildrunner/config/rollout-enforcing.yaml"

  cat > "$ROLLOUT_WATCH" <<'EOF'
mode: watch-only
started_at: 2026-01-01T00:00:00Z
flipped_at: null
EOF

  cat > "$ROLLOUT_ENFORCING" <<'EOF'
mode: enforcing
started_at: 2026-01-01T00:00:00Z
flipped_at: 2026-01-08T00:00:00Z
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
    "PreToolUse": [
      {"matcher":"Bash","hooks":[{"type":"command","command":"echo pre"}]},
      {"matcher":"Edit|Write","hooks":[{"type":"command","command":"echo existing"}]}
    ],
    "SessionStart": [{"hooks":[{"type":"command","command":"echo start"}]}],
    "Stop": [{"hooks":[{"type":"command","command":"echo stop"}]}],
    "UserPromptSubmit": [{"hooks":[{"type":"command","command":"echo user"}]}]
  }
}
EOF
}

emit_event() {
  local session_id="$1"
  local tool_name="$2"
  local file_path="$3"
  cat <<EOF
{"session_id":"$session_id","tool_name":"$tool_name","cwd":"$HOME","tool_input":{"file_path":"$file_path"}}
EOF
}

write_route() {
  local session_id="$1"
  local bucket="$2"
  local primary="$3"
  local builder="$4"
  cat > "$ROUTES_DIR/${session_id}.json" <<EOF
{"session_id":"$session_id","bucket":"$bucket","primary":"$primary","builder":"$builder","override":false,"prompt":"fixture"}
EOF
  chmod 600 "$ROUTES_DIR/${session_id}.json"
}

run_gate_with_rollout() {
  local event_path="$1"
  local rollout_path="$2"
  run bash -lc 'cat "$1" | env HOME="$2" BR3_ROLLOUT_STATE="$3" "$4"' -- "$event_path" "$HOME" "$rollout_path" "$HOOK_SCRIPT"
}

run_gate_with_override() {
  local event_path="$1"
  local rollout_path="$2"
  run bash -lc 'cat "$1" | env HOME="$2" BR3_ROLLOUT_STATE="$3" BR3_FORCE_BUILDER=claude "$4"' -- "$event_path" "$HOME" "$rollout_path" "$HOOK_SCRIPT"
}

@test "gate script is executable" {
  run test -x "$HOOK_SCRIPT"
  [ "$status" -eq 0 ]
}

@test "gate script contains no /tmp paths" {
  run grep -rn '/tmp' "$HOOK_SCRIPT"
  [ "$status" -eq 1 ]
}

@test "installer preserves hook keys and increments PreToolUse by one" {
  before_count="$(jq '.hooks.PreToolUse | length' "$HOME/.claude/settings.json")"

  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]

  run jq '.hooks | keys' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"PostToolUse"'* ]]
  [[ "$output" == *'"PreToolUse"'* ]]
  [[ "$output" == *'"SessionStart"'* ]]
  [[ "$output" == *'"Stop"'* ]]
  [[ "$output" == *'"UserPromptSubmit"'* ]]

  run jq '.hooks.PreToolUse | length' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
  [ "$output" -eq $((before_count + 1)) ]
}

@test "installer is idempotent" {
  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]
  first_count="$(jq '.hooks.PreToolUse | length' "$HOME/.claude/settings.json")"

  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]
  second_count="$(jq '.hooks.PreToolUse | length' "$HOME/.claude/settings.json")"
  [ "$second_count" -eq "$first_count" ]
}

@test "installer adds matcher containing Edit and Write" {
  run "$INSTALLER_SCRIPT"
  [ "$status" -eq 0 ]

  run jq -e '.hooks.PreToolUse[] | select(.hooks[]?.command == "bash ~/.buildrunner/hooks/pre-tool-use-gate.sh") | select((.matcher // "") | contains("Edit")) | select((.matcher // "") | contains("Write"))' "$HOME/.claude/settings.json"
  [ "$status" -eq 0 ]
}

@test "watch-only allows non-claude route and logs would-block" {
  session_id="watch-non-claude"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-watch-non-claude.json"
  emit_event "$session_id" "Edit" "src/components/X.tsx" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_WATCH"
  [ "$status" -eq 0 ]

  run grep 'allow-or-would-block=would-block session=watch-non-claude tool=Edit bucket=backend-build' "$WATCH_LOG"
  [ "$status" -eq 0 ]
}

@test "watch-only allows missing route and logs would-block" {
  event_path="$BATS_TEST_TMPDIR/event-watch-missing.json"
  emit_event "watch-missing-route" "Edit" "src/components/Y.tsx" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_WATCH"
  [ "$status" -eq 0 ]

  run grep 'allow-or-would-block=would-block session=watch-missing-route tool=Edit bucket=missing' "$WATCH_LOG"
  [ "$status" -eq 0 ]
}

@test "watch-only allows claude route and logs allow" {
  session_id="watch-claude"
  write_route "$session_id" "planning" "claude-opus-4-7" "claude"

  event_path="$BATS_TEST_TMPDIR/event-watch-claude.json"
  emit_event "$session_id" "Write" "src/plans/P.md" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_WATCH"
  [ "$status" -eq 0 ]

  run grep 'allow-or-would-block=allow session=watch-claude tool=Write bucket=planning' "$WATCH_LOG"
  [ "$status" -eq 0 ]
}

@test "enforcing blocks non-claude route with block message" {
  session_id="enforce-non-claude"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-enforce-non-claude.json"
  emit_event "$session_id" "Edit" "src/components/BlockMe.tsx" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -ne 0 ]
  [[ "$output" == *'BLOCKED: route=backend-build builder=gpt-5.4; dispatch via codex'* ]]
}

@test "enforcing blocks missing route fail-closed" {
  event_path="$BATS_TEST_TMPDIR/event-enforce-missing.json"
  emit_event "enforce-missing-route" "Edit" "src/components/Z.tsx" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -ne 0 ]
}

@test "enforcing allows claude route" {
  session_id="enforce-claude"
  write_route "$session_id" "planning" "claude-opus-4-7" "claude"

  event_path="$BATS_TEST_TMPDIR/event-enforce-claude.json"
  emit_event "$session_id" "NotebookEdit" "notebooks/demo.ipynb" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -eq 0 ]
}

@test "enforcing allows allow-listed decisions log path" {
  session_id="enforce-allow-decisions"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-enforce-allow-decisions.json"
  emit_event "$session_id" "Edit" ".buildrunner/decisions.log" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -eq 0 ]
}

@test "enforcing allows allow-listed route file path" {
  session_id="enforce-allow-routes"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-enforce-allow-routes.json"
  emit_event "$session_id" "Edit" ".buildrunner/routes/${session_id}.json" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -eq 0 ]
}

@test "BR3_FORCE_BUILDER override always allows and logs decision" {
  session_id="enforce-force-override"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-enforce-force-override.json"
  emit_event "$session_id" "Edit" "src/components/force.tsx" > "$event_path"

  run_gate_with_override "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -eq 0 ]

  run grep 'BR3_FORCE_BUILDER=claude override' "$DECISIONS_LOG"
  [ "$status" -eq 0 ]
}

@test "non-writer tools are ignored" {
  session_id="enforce-non-writer"
  write_route "$session_id" "backend-build" "gpt-5.4" "codex"

  event_path="$BATS_TEST_TMPDIR/event-enforce-non-writer.json"
  emit_event "$session_id" "Bash" "src/components/ignored.tsx" > "$event_path"

  run_gate_with_rollout "$event_path" "$ROLLOUT_ENFORCING"
  [ "$status" -eq 0 ]
}
