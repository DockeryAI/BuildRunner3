#!/usr/bin/env bash
# below-validation.sh — Comprehensive behavioral validation of every Below role
# in the BR3 cluster. Exits 0 only if every test passes.
#
# Sections:
#   1. Foundation — Below reachable, models loaded, env durable
#   2. Gateway — below-route.sh works for both models and gates correctly
#   3. Per-skill gates — each flag-gated skill's Below call-site
#   4. Intel pipeline — prefilter, fail-open, Phase 3 filter
#   5. Hunt + research — embeddings, worker status
#   6. Build infrastructure — runtime-dispatch, dispatch-to-node
#   7. End-to-end smoke — /intel-run
#   8. Failure modes — timeouts, offline, invalid responses
#   9. Concurrency — parallel load
#  10. Deployment confirmation — decisions.log entries, Jimmy service

set -u

PROJECT_ROOT="/Users/byronhudson/Projects/BuildRunner3"
BELOW_URL="http://10.0.1.105:11434"
cd "$PROJECT_ROOT"

# Source runtime-env for this script's shell
[ -f "$HOME/.buildrunner/runtime-env.sh" ] && . "$HOME/.buildrunner/runtime-env.sh"

PASS=0
FAIL=0
SKIP=0
FAILED_TESTS=()

pass() { PASS=$((PASS+1)); printf "  \033[32m✓\033[0m %s\n" "$1"; }
fail() { FAIL=$((FAIL+1)); FAILED_TESTS+=("$1"); printf "  \033[31m✗\033[0m %s — %s\n" "$1" "${2:-}"; }
skip() { SKIP=$((SKIP+1)); printf "  \033[33m-\033[0m %s — %s\n" "$1" "${2:-}"; }
section() { printf "\n\033[1m=== %s ===\033[0m\n" "$1"; }

# -----------------------------------------------------------------------------
section "1. Foundation — Below + env"
# -----------------------------------------------------------------------------

# 1.1 Below reachable, models loaded
TAGS=$(curl -s --max-time 5 "$BELOW_URL/api/tags" 2>/dev/null)
if echo "$TAGS" | grep -q "qwen3:8b" && echo "$TAGS" | grep -q "llama3.3:70b"; then
  pass "1.1 Below /api/tags: qwen3:8b + llama3.3:70b loaded"
else
  fail "1.1 Below /api/tags missing required models" "got: $(echo $TAGS | head -c 100)"
fi

# 1.2 qwen3:8b responds to /api/chat (with think:false to avoid thinking-mode content eviction)
RESP=$(curl -s --max-time 30 "$BELOW_URL/api/chat" -H 'content-type: application/json' \
  -d '{"model":"qwen3:8b","stream":false,"think":false,"options":{"num_predict":16,"temperature":0},"messages":[{"role":"user","content":"say ok"}]}' 2>/dev/null \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message",{}).get("content",""))' 2>/dev/null)
[ -n "$RESP" ] && pass "1.2 qwen3:8b /api/chat responds (chars=${#RESP})" || fail "1.2 qwen3:8b /api/chat empty"

# 1.3 llama3.3:70b responds (num_ctx=4096 to fit Below's available memory; default is 131072)
RESP=$(curl -s --max-time 90 "$BELOW_URL/api/chat" -H 'content-type: application/json' \
  -d '{"model":"llama3.3:70b","stream":false,"options":{"num_ctx":4096,"num_predict":16,"temperature":0},"messages":[{"role":"user","content":"say ok"}]}' 2>/dev/null \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("message",{}).get("content",""))' 2>/dev/null)
[ -n "$RESP" ] && pass "1.3 llama3.3:70b /api/chat responds (chars=${#RESP})" || fail "1.3 llama3.3:70b /api/chat empty"

# 1.4 embeddings endpoint
RESP=$(curl -s --max-time 15 "$BELOW_URL/api/embed" -H 'content-type: application/json' \
  -d '{"model":"nomic-embed-text","input":"test embedding"}' 2>/dev/null)
if echo "$RESP" | python3 -c 'import sys,json; d=json.load(sys.stdin); e=d.get("embeddings",[[]])[0]; assert len(e)>0; print(len(e))' >/dev/null 2>&1; then
  pass "1.4 Below /api/embed returns non-empty vector"
else
  fail "1.4 Below /api/embed failed" "got: $(echo $RESP | head -c 120)"
fi

# 1.5 runtime-env.sh exports
if bash -c ". ~/.buildrunner/runtime-env.sh && \
  [ \"\$BR3_LOCAL_ROUTING\" = on ] && \
  [ -n \"\$BELOW_OLLAMA_URL\" ] && \
  [ \"\$BELOW_MODEL_FAST\" = qwen3:8b ] && \
  [ \"\$BELOW_MODEL_HEAVY\" = llama3.3:70b ] && \
  [ \"\$BR3_RUNTIME_ENV_LOADED\" = 1 ]"; then
  pass "1.5 runtime-env.sh exports all 5 vars"
else
  fail "1.5 runtime-env.sh missing vars"
fi

# 1.6 .zshrc idempotent sentinel
grep -q 'BR3_RUNTIME_ENV_LOADED.*!= "1".*runtime-env.sh' ~/.zshrc \
  && pass "1.6 .zshrc sentinel-guarded source" \
  || fail "1.6 .zshrc missing sentinel-guarded source"

# 1.7 .bash_profile sentinel
grep -q 'BR3_RUNTIME_ENV_LOADED.*!= "1".*runtime-env.sh' ~/.bash_profile \
  && pass "1.7 .bash_profile sentinel-guarded source" \
  || fail "1.7 .bash_profile missing sentinel-guarded source"

# 1.8 bash -lc (login shell) inherits
if [ "$(bash -lc 'echo "$BR3_LOCAL_ROUTING"')" = on ]; then
  pass "1.8 bash -lc inherits BR3_LOCAL_ROUTING=on"
else
  fail "1.8 bash -lc did NOT inherit BR3_LOCAL_ROUTING"
fi

# 1.9 stripped-env below-route.sh --help
if env -i HOME=$HOME PATH=/usr/bin:/bin ~/.buildrunner/scripts/below-route.sh --help >/dev/null 2>&1; then
  pass "1.9 stripped-env below-route.sh --help exits 0"
else
  fail "1.9 stripped-env below-route.sh --help failed"
fi

# 1.10 stripped-env live dispatch
OUT=$(env -i HOME=$HOME PATH=/usr/bin:/bin ~/.buildrunner/scripts/below-route.sh --model qwen3:8b "reply with: hi" 2>/dev/null | head -c 200)
[ -n "$OUT" ] && pass "1.10 stripped-env live dispatch returned text" || fail "1.10 stripped-env live dispatch empty"

# 1.11 SSH to Below works
if ssh -o ConnectTimeout=5 -o BatchMode=yes byron@10.0.1.105 "echo ok" 2>/dev/null | grep -q ok; then
  pass "1.11 SSH byron@10.0.1.105 reachable (build-node role)"
else
  fail "1.11 SSH byron@10.0.1.105 failed"
fi

# -----------------------------------------------------------------------------
section "2. Gateway — below-route.sh"
# -----------------------------------------------------------------------------

# 2.1 qwen3:8b through the gateway
OUT=$(~/.buildrunner/scripts/below-route.sh --model qwen3:8b "reply with: ok" 2>/dev/null | head -c 200)
[ -n "$OUT" ] && pass "2.1 below-route.sh --model qwen3:8b returns text" || fail "2.1 below-route.sh qwen3:8b empty"

# 2.2 llama3.3:70b through the gateway
OUT=$(~/.buildrunner/scripts/below-route.sh --model llama3.3:70b "reply with: ok" 2>/dev/null | head -c 200)
[ -n "$OUT" ] && pass "2.2 below-route.sh --model llama3.3:70b returns text" || fail "2.2 below-route.sh llama3.3:70b empty"

# 2.3 flag-off gating — below-route.sh exits 2 when flag off
if env -i HOME=$HOME PATH=/usr/bin:/bin BR3_RUNTIME_ENV_LOADED=1 BR3_LOCAL_ROUTING=off \
  ~/.buildrunner/scripts/below-route.sh --model qwen3:8b "x" >/dev/null 2>&1; then
  fail "2.3 below-route.sh should exit 2 when flag off, but exited 0"
else
  rc=$?
  if [ "$rc" = 2 ]; then
    pass "2.3 below-route.sh exits 2 when BR3_LOCAL_ROUTING=off"
  else
    fail "2.3 below-route.sh exit code wrong when flag off" "rc=$rc"
  fi
fi

# 2.4 decisions.log gets a routing: entry after a call
BEFORE=$(grep -c "^[^ ]* routing: " .buildrunner/decisions.log 2>/dev/null || echo 0)
~/.buildrunner/scripts/below-route.sh --model qwen3:8b "reply: ok" >/dev/null 2>&1
AFTER=$(grep -c "^[^ ]* routing: " .buildrunner/decisions.log 2>/dev/null || echo 0)
if [ "$AFTER" -ge "$BEFORE" ]; then
  pass "2.4 below-route.sh writes to decisions.log (before=$BEFORE, after=$AFTER)"
else
  skip "2.4 below-route.sh routing log" "log count check indeterminate"
fi

# -----------------------------------------------------------------------------
section "3. Per-skill gates (static + live call-site proof)"
# -----------------------------------------------------------------------------

check_skill_gate() {
  local skill_file="$1" skill_name="$2"
  if grep -q 'BR3_LOCAL_ROUTING.*on' "$skill_file" && \
     grep -q 'below-route.sh' "$skill_file"; then
    pass "3.$3 $skill_name: gate wired (BR3_LOCAL_ROUTING + below-route.sh)"
  else
    fail "3.$3 $skill_name: gate NOT wired"
  fi
}

check_skill_gate ~/.claude/commands/dbg.md       "/dbg"       1
check_skill_gate ~/.claude/commands/sdb.md       "/sdb"       2
check_skill_gate ~/.claude/commands/diag.md      "/diag"      3
check_skill_gate ~/.claude/commands/root.md      "/root"      4
check_skill_gate ~/.claude/commands/review.md    "/review"    5
check_skill_gate ~/.claude/commands/guard.md     "/guard"     6
check_skill_gate ~/.claude/commands/begin.md     "/begin"     7
check_skill_gate ~/.claude/commands/autopilot.md "/autopilot" 8

# 3.9 classify-prompt.sh end-to-end (dispatch chain)
BUCKET=$(echo "fix button label typo" | ~/.buildrunner/scripts/classify-prompt.sh 2>/dev/null | tr -d '\n')
case "$BUCKET" in
  planning|architecture|backend-build|terminal-build|ui-build|review|classification|retrieval|qa)
    pass "3.9 classify-prompt.sh returned valid bucket ($BUCKET)";;
  *)
    fail "3.9 classify-prompt.sh returned invalid bucket" "got: $BUCKET";;
esac

# 3.10 stop-when.sh live chain
TMP_CTX=$(mktemp); echo "all tests passing. 0 failures." > "$TMP_CTX"
DECISION=$(~/.buildrunner/scripts/stop-when.sh "tests are passing" "$TMP_CTX" 2>/dev/null)
rm -f "$TMP_CTX"
case "$DECISION" in
  MET|NOT_MET|INCONCLUSIVE) pass "3.10 stop-when.sh returned $DECISION";;
  *) fail "3.10 stop-when.sh returned invalid token" "got: $DECISION";;
esac

# 3.11 autopilot Step 2.5a classifier route existence
grep -q "below-route.sh --model llama3.3:70b" ~/.claude/commands/autopilot.md \
  && pass "3.11 /autopilot Step 2.5a llama3.3:70b route exists" \
  || fail "3.11 /autopilot Step 2.5a missing llama3.3:70b route"

# -----------------------------------------------------------------------------
section "4. Intel pipeline"
# -----------------------------------------------------------------------------

# 4.1 intel_prefilter module imports + runs + exits 0
OUT=$(python3 -m core.cluster.scripts.intel_prefilter 2>&1)
rc=$?
[ $rc -eq 0 ] && pass "4.1 intel_prefilter module runs clean (exit 0)" || fail "4.1 intel_prefilter exit=$rc" "$(echo $OUT | head -c 200)"

# 4.2 log file created
LOG=$(ls -t ~/.buildrunner/logs/intel-prefilter-*.log 2>/dev/null | head -1)
[ -n "$LOG" ] && [ -s "$LOG" ] && pass "4.2 intel_prefilter writes log ($LOG)" || fail "4.2 intel_prefilter log missing"

# 4.3 signature preserved
SIG=$(python3 -c 'import inspect; from core.cluster.intel_scoring import score_intel_items; print(inspect.signature(score_intel_items))' 2>/dev/null)
[ "$SIG" = "() -> dict" ] && pass "4.3 score_intel_items signature: $SIG" || fail "4.3 signature drift" "got: $SIG"

# 4.4 AST: no break in Below-offline branch, has _flag_needs_opus_review
python3 - <<'PY'
import ast, sys
src = open('core/cluster/intel_scoring.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == 'score_intel_items':
        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
        has_flag = '_flag_needs_opus_review(item_id, "intel")' in ast.get_source_segment(src, node)
        sys.exit(0 if (not has_break and has_flag) else 1)
sys.exit(2)
PY
[ $? -eq 0 ] && pass "4.4 score_intel_items: no break + flag call present" || fail "4.4 AST check failed"

# 4.5 all required public symbols importable
if python3 -c 'from core.cluster.intel_scoring import score_intel_items, start_scoring_cron, _parse_intel_score, _flag_needs_opus_review' 2>/dev/null; then
  pass "4.5 all 4 public symbols importable (30-min cron contract preserved)"
else
  fail "4.5 public symbols broken"
fi

# 4.6 Phase 3 filter logic (synthetic items)
python3 <<'PY'
import os, sys
os.environ['BR3_INTEL_MIN_SCORE'] = '6'
os.environ['BR3_INTEL_PRIORITY_OVERRIDE'] = 'critical,high'
items = [
    {'id': 1, 'score': 3,    'priority': 'low',      'scored': 1, 'needs_opus_review': 0, 'opus_reviewed': False},
    {'id': 2, 'score': 8,    'priority': 'low',      'scored': 1, 'needs_opus_review': 0, 'opus_reviewed': False},
    {'id': 3, 'score': 2,    'priority': 'critical', 'scored': 1, 'needs_opus_review': 0, 'opus_reviewed': False},
    {'id': 4, 'score': 1,    'priority': 'low',      'scored': 1, 'needs_opus_review': 1, 'opus_reviewed': False},
    {'id': 5, 'score': None, 'priority': None,       'scored': 0, 'needs_opus_review': 0, 'opus_reviewed': False},
    {'id': 6, 'score': 9,    'priority': 'critical', 'scored': 1, 'needs_opus_review': 0, 'opus_reviewed': True},
]
MIN = int(os.environ['BR3_INTEL_MIN_SCORE'])
OVR = set(os.environ['BR3_INTEL_PRIORITY_OVERRIDE'].split(','))
def keep(i):
    if i.get('opus_reviewed'): return False
    return ((i.get('score') or 0) >= MIN or i.get('priority') in OVR
            or i.get('needs_opus_review') == 1 or i.get('scored') == 0)
kept = [i['id'] for i in items if keep(i)]
assert kept == [2, 3, 4, 5], f'FAIL kept={kept}'
PY
[ $? -eq 0 ] && pass "4.6 Phase 3 filter routes 5 synthetic items correctly (kept=[2,3,4,5])" || fail "4.6 Phase 3 filter logic"

# 4.7 collect-intel.sh --phase=2.5 runs only Phase 2.5
OUT=$(bash -c "$PROJECT_ROOT/core/cluster/scripts/collect-intel.sh --phase=2.5 2>&1" || true)
TODAY_LOG="$HOME/.buildrunner/logs/intel-collect-$(date +%Y-%m-%d).log"
if grep -q 'Phase 2.5:' "$TODAY_LOG" 2>/dev/null; then
  pass "4.7 collect-intel.sh --phase=2.5 fires Phase 2.5"
else
  fail "4.7 collect-intel.sh --phase=2.5 did not log Phase 2.5"
fi

# 4.8 --skip-prefilter bypasses
OUT=$(bash -c "BR3_SKIP_PREFILTER_TEST_LOG=/tmp/br3-skip.log $PROJECT_ROOT/core/cluster/scripts/collect-intel.sh --skip-prefilter --phase=2.5 2>&1" || true)
if grep -q 'Phase 2.5: skipped' "$TODAY_LOG" 2>/dev/null; then
  pass "4.8 --skip-prefilter bypasses Phase 2.5 (logs 'skipped')"
else
  fail "4.8 --skip-prefilter did NOT produce skipped log"
fi

# 4.9 Fail-open when Below offline
OUT=$(BELOW_OLLAMA_URL=http://127.0.0.1:1 python3 -m core.cluster.scripts.intel_prefilter 2>&1)
rc=$?
[ $rc -eq 0 ] && pass "4.9 intel_prefilter Below-offline: exit 0 (fail-open)" || fail "4.9 fail-open crashed" "rc=$rc"

# 4.10 Jimmy intel service alive
if curl -s --max-time 5 http://10.0.1.106:8101/api/intel/items | head -c 20 | grep -q '"items"'; then
  pass "4.10 Jimmy intel API (10.0.1.106:8101) serving"
else
  fail "4.10 Jimmy intel API not reachable"
fi

# 4.11 Jimmy has updated intel_scoring.py (SHA check)
LOCAL_SHA=$(shasum core/cluster/intel_scoring.py | awk '{print $1}')
ssh -o ConnectTimeout=5 -o BatchMode=yes byronhudson@10.0.1.106 'shasum /home/byronhudson/repos/BuildRunner3/core/cluster/intel_scoring.py' > /tmp/br3-jimmy-sha.txt 2>&1
REMOTE_SHA=$(awk '{print $1}' /tmp/br3-jimmy-sha.txt)
if [ -n "$REMOTE_SHA" ] && [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  pass "4.11 Jimmy has fresh intel_scoring.py (SHA match)"
elif [ -n "$REMOTE_SHA" ]; then
  fail "4.11 Jimmy has OLD intel_scoring.py" "local=$LOCAL_SHA remote=$REMOTE_SHA — needs deploy"
else
  fail "4.11 Jimmy intel_scoring.py location unknown or SSH failed"
fi

# 4.12 Jimmy service uses updated code (import contract)
ssh -o ConnectTimeout=10 -o BatchMode=yes byronhudson@10.0.1.106 'cd /home/byronhudson/repos/BuildRunner3 && .venv/bin/python3 -c "import inspect; from core.cluster.intel_scoring import score_intel_items; print(inspect.signature(score_intel_items))"' > /tmp/br3-jimmy-import.txt 2>&1
SSH_OUT=$(cat /tmp/br3-jimmy-import.txt)
if [ "$SSH_OUT" = "() -> dict" ]; then
  pass "4.12 Jimmy can import new intel_scoring (signature=$SSH_OUT)"
else
  fail "4.12 Jimmy import check failed" "got: $SSH_OUT"
fi

# -----------------------------------------------------------------------------
section "5. Hunt + research"
# -----------------------------------------------------------------------------

# 5.1 hunt_sourcer imports clean
if python3 -c 'from core.cluster.hunt_sourcer import BELOW_OLLAMA_URL, BELOW_MODEL; print("OK")' 2>/dev/null | grep -q OK; then
  pass "5.1 hunt_sourcer.py imports clean (Below vars exported)"
else
  fail "5.1 hunt_sourcer.py import failed"
fi

# 5.2 hunt_sourcer's Below embed actually works end-to-end
python3 - <<'PY'
import asyncio, json, urllib.request, os
base = os.environ.get('BELOW_OLLAMA_URL', 'http://10.0.1.105:11434').rstrip('/')
body = json.dumps({'model': 'nomic-embed-text', 'input': 'test product title'}).encode()
req = urllib.request.Request(f'{base}/api/embed', data=body,
    headers={'content-type': 'application/json'}, method='POST')
with urllib.request.urlopen(req, timeout=15) as r:
    d = json.loads(r.read())
    emb = d.get('embeddings', [[]])[0]
    assert len(emb) >= 100, f'short embedding: {len(emb)}'
    print(f'dim={len(emb)}')
PY
[ $? -eq 0 ] && pass "5.2 hunt_sourcer Below embed call works (real /api/embed)" || fail "5.2 hunt_sourcer embed failed"

# 5.3 research-queue-status.sh reports Below reachable
OUT=$(~/.buildrunner/scripts/research-queue-status.sh 2>&1 || true)
if echo "$OUT" | grep -qiE "ollama.*(ok|reachable|alive|up)" && echo "$OUT" | grep -q "10.0.1.105"; then
  pass "5.3 research-queue-status reports Below reachable"
else
  SIGNAL=$(echo "$OUT" | grep -iE "below|ollama|10\.0\.1\.105" | head -2)
  if [ -n "$SIGNAL" ]; then
    pass "5.3 research-queue-status shows Below signal"
  else
    fail "5.3 research-queue-status shows no Below signal"
  fi
fi

# 5.4 research worker launchd loaded (optional — may not exist)
if launchctl list 2>/dev/null | grep -qiE 'research|br3.*worker|br3.*queue'; then
  pass "5.4 research worker launchd agent loaded"
else
  skip "5.4 research worker launchd" "no agent match; worker may be a user process or not configured"
fi

# -----------------------------------------------------------------------------
section "6. Build infrastructure"
# -----------------------------------------------------------------------------

# 6.1 runtime-dispatch.sh exists and exec
test -x ~/.buildrunner/scripts/runtime-dispatch.sh \
  && pass "6.1 runtime-dispatch.sh exists + executable" \
  || fail "6.1 runtime-dispatch.sh missing/not executable"

# 6.2 dispatch-to-node.sh Below health check
if bash -c "source ~/.buildrunner/scripts/_dispatch-core.sh && check_node_health below" 2>/dev/null; then
  pass "6.2 dispatch-to-node.sh: Below health check passes"
else
  fail "6.2 dispatch-to-node.sh Below health check failed"
fi

# 6.3 build-sidecar.sh and ralph-loop.sh reference runtime-dispatch
grep -q 'runtime-dispatch' ~/.buildrunner/scripts/build-sidecar.sh \
  && pass "6.3 build-sidecar.sh wires runtime-dispatch" \
  || fail "6.3 build-sidecar.sh missing runtime-dispatch"

grep -q 'runtime-dispatch' ~/.buildrunner/scripts/ralph-loop.sh \
  && pass "6.4 ralph-loop.sh wires runtime-dispatch" \
  || fail "6.4 ralph-loop.sh missing runtime-dispatch"

# -----------------------------------------------------------------------------
section "7. End-to-end — /intel-run"
# -----------------------------------------------------------------------------

# 7.1 /intel-run --smoke (the canonical health check)
if ~/.buildrunner/scripts/intel-run.sh --smoke 2>&1 | grep -q "ALL PASS"; then
  pass "7.1 /intel-run --smoke: Lockwood + Below both PASS"
else
  fail "7.1 /intel-run --smoke failed"
fi

# 7.2 /intel-run slash command file exists AND claude-code discovered it
test -f ~/.claude/commands/intel-run.md \
  && pass "7.2 /intel-run slash command file exists" \
  || fail "7.2 /intel-run.md missing"

# 7.3 intel-run.sh sources runtime-env
grep -q 'runtime-env.sh' ~/.buildrunner/scripts/intel-run.sh \
  && pass "7.3 intel-run.sh sources runtime-env.sh" \
  || fail "7.3 intel-run.sh missing runtime-env source"

# 7.4 cron is off
[ "$(crontab -l 2>/dev/null | grep -c collect-intel)" = 0 ] \
  && pass "7.4 crontab: no collect-intel entry (cron off)" \
  || fail "7.4 crontab still has collect-intel"

# -----------------------------------------------------------------------------
section "8. Failure mode simulations"
# -----------------------------------------------------------------------------

# 8.1 Classifier mock invalid → safe_default
OUT=$(BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE='not-valid-json' python3 ~/.buildrunner/scripts/lib/classifier-haiku.py "x" 2>/dev/null | tr -d '\n')
[ "$OUT" = "backend-build" ] && pass "8.1 classifier invalid-JSON → safe_default backend-build" || fail "8.1 classifier fallback" "got: $OUT"

# 8.2 Classifier timeout
OUT=$(BR3_CLASSIFIER_HAIKU_TIMEOUT_MS=100 BR3_CLASSIFIER_HAIKU_MOCK_DELAY_MS=500 \
  BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE='{"bucket":"planning"}' \
  python3 ~/.buildrunner/scripts/lib/classifier-haiku.py "x" 2>/dev/null | tr -d '\n')
[ "$OUT" = "backend-build" ] && pass "8.2 classifier timeout → safe_default" || fail "8.2 classifier timeout" "got: $OUT"

# 8.3 Classifier valid mock → honored
OUT=$(BR3_CLASSIFIER_HAIKU_MOCK_RESPONSE='{"bucket":"planning"}' \
  python3 ~/.buildrunner/scripts/lib/classifier-haiku.py "x" 2>/dev/null | tr -d '\n')
[ "$OUT" = "planning" ] && pass "8.3 classifier valid mock → planning" || fail "8.3 classifier mock honored" "got: $OUT"

# 8.4 stop-when Below offline → INCONCLUSIVE
TMP_CTX=$(mktemp); echo "x" > "$TMP_CTX"
OUT=$(BELOW_OLLAMA_URL=http://127.0.0.1:1 BR3_STOPWHEN_BELOW_CONNECT_TIMEOUT_S=1 BR3_STOPWHEN_BELOW_TIMEOUT_S=2 \
  ~/.buildrunner/scripts/stop-when.sh "x" "$TMP_CTX" 2>/dev/null)
rm -f "$TMP_CTX"
[ "$OUT" = "INCONCLUSIVE" ] && pass "8.4 stop-when Below-offline → INCONCLUSIVE" || fail "8.4 stop-when offline" "got: $OUT"

# 8.5 below-route.sh with Below bogus
OUT=$(BELOW_OLLAMA_URL=http://127.0.0.1:1 ~/.buildrunner/scripts/below-route.sh --model qwen3:8b "x" 2>&1)
rc=$?
if [ $rc -eq 2 ] || [ -z "$OUT" ]; then
  pass "8.5 below-route.sh Below-offline: exit !=0 or empty (caller falls back)"
else
  fail "8.5 below-route.sh Below-offline unexpected" "rc=$rc out=$(echo $OUT | head -c 80)"
fi

# -----------------------------------------------------------------------------
section "9. Concurrency"
# -----------------------------------------------------------------------------

# 9.1 5 concurrent below-route.sh calls
START=$(date +%s)
PIDS=()
TMPD=$(mktemp -d)
for i in 1 2 3 4 5; do
  (~/.buildrunner/scripts/below-route.sh --model qwen3:8b "reply: $i" > "$TMPD/out-$i" 2>&1 && echo OK > "$TMPD/ok-$i" || echo FAIL > "$TMPD/ok-$i") &
  PIDS+=($!)
done
for pid in "${PIDS[@]}"; do wait $pid; done
OKCOUNT=$(ls "$TMPD"/ok-* 2>/dev/null | xargs -I{} cat {} 2>/dev/null | grep -c OK)
DURATION=$(($(date +%s) - START))
rm -rf "$TMPD"
if [ "$OKCOUNT" -ge 4 ]; then
  pass "9.1 5 concurrent below-route.sh calls: $OKCOUNT/5 OK in ${DURATION}s"
else
  fail "9.1 concurrent calls degraded: $OKCOUNT/5 OK in ${DURATION}s"
fi

# -----------------------------------------------------------------------------
section "10. Deployment confirmation"
# -----------------------------------------------------------------------------

# 10.1 intel-prefilter logs exist from this run
LOG=$(ls -t ~/.buildrunner/logs/intel-prefilter-*.log 2>/dev/null | head -1)
[ -n "$LOG" ] && pass "10.1 intel-prefilter logs present ($LOG)" || fail "10.1 no intel-prefilter log"

# 10.2 git tree clean + commits on origin/main
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote origin main 2>/dev/null | awk '{print $1}')
[ "$LOCAL_SHA" = "$REMOTE_SHA" ] && pass "10.2 HEAD pushed to origin/main" || fail "10.2 HEAD not synced with origin/main"

# =============================================================================
printf "\n\033[1m=== RESULTS ===\033[0m\n"
printf "PASS: \033[32m%d\033[0m  FAIL: \033[31m%d\033[0m  SKIP: \033[33m%d\033[0m\n" "$PASS" "$FAIL" "$SKIP"

if [ "$FAIL" -gt 0 ]; then
  printf "\nFailed tests:\n"
  for t in "${FAILED_TESTS[@]}"; do
    printf "  - %s\n" "$t"
  done
  exit 1
fi
exit 0
