# /fixit Brief — Below utilization + json_invalid fix

## Problem

Three defects found during this session's Below utilization review. Bundling for one dispatch because they are all small, deterministic, and share the Below/cluster domain.

1. **Orphan models on Below.** Three installed Ollama models are not declared in `~/.buildrunner/cluster.json` under `nodes.below.inference.models`, so the router never dispatches to them. Dark capacity.
2. **BUILD_cluster-visibility-sharding Phase 1 missing sync_path.** Phase 1 modifies `core/cluster/below/research_worker.py` (a file that runs on Below) but the phase's router `sync_paths` is empty, so the change won't reach Below after the edit on Muddy.
3. **developer-brief.sh:491 sends invalid JSON to Below's `/api/summarize`.** `$LOG_PATTERNS` is shell-interpolated directly into a JSON string literal; log lines contain raw newlines + quotes → pydantic rejects with `json_invalid` at `body[101]` (`Invalid control character`). This is the `Below Analysis` block that reliably appears broken in the developer brief.

## Evidence

- `~/.buildrunner/cluster.json` → `nodes.below.inference.models` lists: `llama3.3:70b`, `qwen3:8b`, `nomic-embed-text`. Actual `curl http://10.0.1.105:11434/api/tags` returns those **plus** `deepseek-r1:70b-llama-distill-q4_K_M`, `qwen2.5:14b`, `llama3.3:70b-instruct-q4_K_M`.
- `.buildrunner/agents.json` → `routing.phases.phase_1` = `{assigned_node: muddy, sync_paths: []}` despite phase touching `core/cluster/below/research_worker.py` (see `.buildrunner/builds/BUILD_cluster-visibility-sharding.md:51`).
- `~/.buildrunner/scripts/developer-brief.sh:489-491`:
  ```
  SUMMARY=$(curl -s --max-time 10 -X POST "$BELOW_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"$LOG_PATTERNS\"}" 2>/dev/null)
  ```
  `$LOG_PATTERNS` contains newline-separated log summaries (see lines 481-487). Error observed in session-start brief: `{'detail':[{'type':'json_invalid','loc':['body',101],'msg':'JSON decode error','ctx':{'error':'Invalid control character at'}}]}`.

## Success Criteria

- [ ] `~/.buildrunner/cluster.json` → `nodes.below.inference.models` contains all 6 models from `curl http://10.0.1.105:11434/api/tags` (no duplicates; exact names as returned by Ollama).
- [ ] `.buildrunner/builds/BUILD_cluster-visibility-sharding.md` Phase 1 section declares a sync path for Below covering `core/cluster/below/` (whatever field/format the build spec uses; match sibling phases' style).
- [ ] `~/.buildrunner/scripts/developer-brief.sh` line ~491 JSON-encodes `$LOG_PATTERNS` properly (via `python3 -c 'import json,sys,os; print(json.dumps({"text": os.environ["LOG_PATTERNS"]}))'` or `jq -Rs '{text: .}'`) — no raw shell interpolation of log content into JSON string literals.
- [ ] After the fix, a manual `curl` to `http://10.0.1.105:8100/api/summarize` with a multi-line payload containing newlines/quotes returns **not** a `json_invalid` error (it may still error on something else — that's out of scope; the goal is "pydantic accepts the body").

## Scope

- **In (edit):**
  - `~/.buildrunner/cluster.json` (absolute path — outside repo)
  - `~/.buildrunner/scripts/developer-brief.sh` (absolute path — outside repo)
  - `.buildrunner/builds/BUILD_cluster-visibility-sharding.md` (inside worktree)
- **Out (do NOT touch):**
  - Any other file under `core/`, `src/`, `supabase/`.
  - Schema / migrations / RLS / auth.
  - Any other BUILD spec.
  - Other scripts under `~/.buildrunner/scripts/`.
  - The orphan models' Ollama install (already installed; only declaration changes).

## Verification Command

```bash
bash -c '
set -e
# 1. cluster.json contains all 6 Below models
DECLARED=$(python3 -c "import json; print(sorted(json.load(open(\"$HOME/.buildrunner/cluster.json\"))[\"nodes\"][\"below\"][\"inference\"][\"models\"]))")
ACTUAL=$(curl -sS --max-time 5 http://10.0.1.105:11434/api/tags | python3 -c "import json,sys; print(sorted(m[\"name\"] for m in json.load(sys.stdin)[\"models\"]))")
[ "$DECLARED" = "$ACTUAL" ] || { echo "FAIL: declared=$DECLARED actual=$ACTUAL"; exit 1; }

# 2. BUILD spec phase 1 mentions sync for below
grep -A 20 "Phase 1" .buildrunner/builds/BUILD_cluster-visibility-sharding.md | grep -qiE "sync.*below|below.*sync|core/cluster/below" || { echo "FAIL: no below sync in phase 1"; exit 1; }

# 3. developer-brief.sh JSON encoding fix present
grep -q "json.dumps\|jq -Rs" "$HOME/.buildrunner/scripts/developer-brief.sh" || { echo "FAIL: developer-brief.sh not json-safe"; exit 1; }
# And the bare naive form is gone
grep -q "\\\\\\\"text\\\\\\\":\\\\\\\"\\\$LOG_PATTERNS\\\\\\\"" "$HOME/.buildrunner/scripts/developer-brief.sh" && { echo "FAIL: naive interpolation still present"; exit 1; }

# 4. live smoke test: POST a payload with newlines and ensure no json_invalid
PAYLOAD=$(python3 -c "import json; print(json.dumps({\"text\": \"line1\nline2\\\"quoted\\\"\nline3\"}))")
RESP=$(curl -sS --max-time 10 -X POST http://10.0.1.105:8100/api/summarize -H "Content-Type: application/json" -d "$PAYLOAD" 2>&1 || true)
echo "$RESP" | grep -q "json_invalid" && { echo "FAIL: still json_invalid on well-formed body"; exit 1; }

echo "VERIFY OK"
'
```

## Notes

- Two of the three files are outside the repo (`$HOME/.buildrunner/...`). Edit them by absolute path. The worktree isolation only protects the in-repo change (the BUILD spec). This is intentional for this dispatch; do not try to copy files into the worktree.
- The orphan models' exact names (from the Ollama API, exact strings):
  - `llama3.3:70b`
  - `llama3.3:70b-instruct-q4_K_M`
  - `deepseek-r1:70b-llama-distill-q4_K_M`
  - `nomic-embed-text:latest` (note the `:latest` suffix — preserve it)
  - `qwen3:8b`
  - `qwen2.5:14b`
- For the JSON-encoding fix in `developer-brief.sh`: the simplest safe form is:
  ```bash
  PAYLOAD=$(LOG_PATTERNS="$LOG_PATTERNS" python3 -c 'import json,os; print(json.dumps({"text": os.environ["LOG_PATTERNS"]}))')
  SUMMARY=$(curl -s --max-time 10 -X POST "$BELOW_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>/dev/null)
  ```
  Use that pattern; do not introduce `jq` as a new dependency.
- The project mirrors `developer-brief.sh` at `.buildrunner/scripts/developer-brief.sh` too. Check if the bug exists there and fix it if so — but the canonical runtime path is `~/.buildrunner/scripts/developer-brief.sh` (the session-start hook invokes this one).
- Do **not** change what Below does, or its endpoint, or anything about the `/api/summarize` handler. This is a caller-side fix only.

## Execution Mode

Use Plan Mode. Before any edit, output a numbered plan (≤10 steps). Each step must name the file and the behavior changed. Execute against the plan only. Do not refactor code outside the plan's stated scope.
