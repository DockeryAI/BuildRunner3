# Spec Draft: cluster-max

**Purpose:** Upgrade Below to dual RTX 3090 NVLink, add MS-A2 as combined Memory+Staging node, reconfigure all 7 cluster nodes as build workers with priority cascade, wire Below 70B inference deep into the skill pipeline, add vLLM batch extraction, and create overnight autonomous batch automation.

**Target Users:** Byron (solo dev, BR3 cluster operator)
**Tech Stack:** Bash, Node.js (mjs), Python (FastAPI), Ollama, vLLM, SQLite, LanceDB, launchd

---

## Phase 1: Pre-Hardware Preparation

**Goal:** All software artifacts ready before hardware arrives. Below verification scripts, MS-A2 bootstrap playbook, Ollama config, data migration tooling, and node_inference.py upgrade — everything staged so hardware install days are pure execution.

**Files:**

- ~/.buildrunner/scripts/below-verify.sh (NEW)
- ~/.buildrunner/scripts/below-benchmark.sh (NEW)
- ~/.buildrunner/scripts/ms-a2-bootstrap.sh (NEW)
- ~/.buildrunner/scripts/migrate-lockwood-data.sh (NEW)
- ~/.buildrunner/scripts/ms-a2-verify.sh (NEW)
- ~/.buildrunner/configs/ollama-below.env (NEW)
- core/cluster/node_inference.py (MODIFY)

**Blocked by:** None
**Deliverables:**

- [ ] below-verify.sh — tests nvidia-smi dual GPU detection, NVLink topology (nvidia-smi topo -m), total VRAM (48GB expected), driver version, CUDA version
- [ ] below-benchmark.sh — tok/s measurement on 70B/32B/8B models, NVLink bandwidth test (p2pBandwidthLatencyTest), results written to ~/.buildrunner/logs/below-benchmark.log
- [ ] ollama-below.env — OLLAMA_FLASH_ATTENTION=1, OLLAMA_KEEP_ALIVE=0, OLLAMA_NUM_PARALLEL=4, OLLAMA_MAX_LOADED_MODELS=2, CUDA_VISIBLE_DEVICES=0,1, OLLAMA_MAX_QUEUE=512
- [ ] ms-a2-bootstrap.sh — Ubuntu Server packages (python3, node 22, npm, git, rsync, ollama client, uvicorn, lancedb deps), SSH key deployment, cluster auth setup, systemd service files for node_semantic + node_intelligence + node_staging
- [ ] migrate-lockwood-data.sh — rsync ~/.lockwood/ (LanceDB vectors, memory.db, intel.db) from old Lockwood to MS-A2, verify row counts match, verify vector table dimensions match, verify endpoint responses match
- [ ] node_inference.py update — dual GPU model registry (/api/models endpoint listing loaded models + VRAM usage), 70B capability flag, /api/health extended with gpu_count, nvlink_active, vram_total, vram_used fields

**Success Criteria:** All 6 scripts pass shellcheck. node_inference.py changes pass existing tests. Scripts are idempotent (safe to run multiple times).

---

## Phase 2: Below Activation

**Goal:** Dual 3090 NVLink operational, Ollama serving 70B models at 20+ tok/s, existing scoring pipeline verified against upgraded hardware.

**GATE: User confirms 3090s + RM1200x PSU + 32GB DDR4 physically installed, machine boots.**

**Files:**

- Uses scripts from Phase 1 (no new source files)
- ~/.buildrunner/logs/below-benchmark.log (NEW — output)
- ~/.buildrunner/logs/below-activation.log (NEW — output)

**Blocked by:** Phase 1
**Deliverables:**

- [ ] Run below-verify.sh — dual 3090 detected, NVLink bridge active, 48GB VRAM visible, driver current
- [ ] Deploy Ollama with ollama-below.env — install/update Ollama service, apply environment config, verify service starts
- [ ] Pull models — qwen3:8b (~5GB), llama3.3:70b-instruct-q4_K_M (~41GB), deepseek-r1:70b-q4_K_M (~43GB), nomic-embed-text (~274MB)
- [ ] Run below-benchmark.sh — record baseline tok/s for all models, confirm NVLink speedup over single-GPU (expect 30%+ on 70B)
- [ ] Smoke test — intel_scoring.py scores 5 test items against upgraded Below, results match expected format, latency within 2x of baseline

**Success Criteria:** 70B model generates at 18+ tok/s. NVLink detected in nvidia-smi topo. Scoring pipeline returns valid JSON scores.

---

## Phase 3: MS-A2 Activation

**Goal:** MS-A2 running all Lockwood + Lomax services, data migrated, all endpoints responding identically to original nodes.

**GATE: User confirms MS-A2 assembled with 64GB DDR5 + 2TB NVMe, powered on, accessible on network.**

**Files:**

- Uses scripts from Phase 1 (no new source files)
- ~/.buildrunner/logs/ms-a2-activation.log (NEW — output)

**Blocked by:** Phase 1
**After:** Phase 1 (different hardware gate than Phase 2 — CAN run parallel with Phase 2)
**Deliverables:**

- [ ] Run ms-a2-bootstrap.sh — Ubuntu Server packages installed (python3, python3-venv, node 22, npm, git, rsync, build-essential, sqlite3), SSH keys deployed from Muddy, cluster auth working, firewall opened for ports 8100 + 4200
- [ ] Deploy BR3 codebase — git clone BuildRunner3 repo to ~/repos/BuildRunner3 on MS-A2, create Python venv, pip install requirements (fastapi, uvicorn, lancedb, httpx, sentence-transformers, etc.)
- [ ] Deploy node_semantic.py as systemd service — create /etc/systemd/system/br3-semantic.service, enable on boot, ExecStart=uvicorn on port 8100. LanceDB initialized, embedding models loaded, /api/search and /api/brief/{project} responding
- [ ] Deploy node_intelligence.py as systemd service — create /etc/systemd/system/br3-intel.service, enable on boot. Intel API, deals API, all 5 background crons started (pollers, scoring, verifier, sourcer, seller_verifier)
- [ ] Deploy node_staging.py as systemd service — create /etc/systemd/system/br3-staging.service, enable on boot. Preview deploy endpoint, build validation working. VRT Docker stack stays on old Lomax for now (Docker not required on MS-A2 in v1)
- [ ] Run migrate-lockwood-data.sh — rsync ~/.lockwood/ from old Lockwood (10.0.1.101) to MS-A2, verify: LanceDB vector tables exist + row counts match, memory.db session_state/build_history/test_results tables populated, intel.db deal_items/active_hunts tables populated
- [ ] Run ms-a2-verify.sh — all endpoints return 200, SessionStart brief generates correctly from MS-A2, semantic search returns relevant results for test query, intel scoring cron fires and connects to Below for LLM scoring

**Success Criteria:** All Lockwood API endpoints respond on MS-A2. Staging endpoints respond on MS-A2. Data integrity verified (row counts, search quality). All 3 systemd services enabled and surviving reboot test. VRT remains on old Lomax (addressed separately if needed).

---

## Phase 4: Cluster Reconfiguration — 7 Workers

**Goal:** Atomic cutover — all 7 nodes registered as build workers with priority cascade, all IP references updated, all hooks point to MS-A2, dispatch works to every node.

**Files:**

- ~/.buildrunner/cluster.json (MODIFY)
- ~/.buildrunner/lib/node-matrix.mjs (MODIFY)
- ~/.buildrunner/scripts/dispatch-to-node.sh (MODIFY)
- ~/.buildrunner/scripts/\_dispatch-core.sh (MODIFY)
- ~/.buildrunner/scripts/build-sidecar.sh (MODIFY)
- ~/.buildrunner/scripts/build-monitor.mjs (MODIFY)
- ~/.buildrunner/scripts/br-token-refresh.sh (MODIFY)
- ~/.buildrunner/scripts/auto-save-session.sh (MODIFY)
- ~/.buildrunner/scripts/ssh-warmup.sh (MODIFY)
- ~/.buildrunner/scripts/br-account-setup.sh (MODIFY)
- ~/.buildrunner/scripts/br-swap-accounts.sh (MODIFY)
- ~/.buildrunner/scripts/walter-setup.sh (MODIFY)
- ~/.buildrunner/scripts/deploy-vrt-lomax.sh (MODIFY)
- ~/.buildrunner/dashboard/events.mjs (MODIFY)
- core/cluster/node_staging.py (MODIFY)
- core/cluster/hunt_sourcer.py (MODIFY)
- core/cluster/delivery_tracker.py (MODIFY)
- core/cluster/intel_scoring.py (MODIFY)
- core/cluster/intel_verifier.py (MODIFY)
- core/cluster/node_tests.py (MODIFY)

**NOTE:** All ~/.buildrunner/ files live OUTSIDE the git repo at $HOME/.buildrunner/. They are NOT in the project directory.

**Blocked by:** Phase 2, Phase 3
**Deliverables:**

- [ ] cluster.json — add MS-A2 node (name, IP, port, roles: [semantic-search, staging-server, parallel-builder]), update Below machine spec ("Windows i9 64GB + 2x RTX 3090 NVLink"), mark old Lockwood and Lomax as role: overflow-builder
- [ ] node-matrix.mjs — 7 workers: otis (priority 1), below (priority 2), ms-a2 (priority 3), lockwood (priority 4), lomax (priority 5), muddy (priority 6), walter (priority 7). All accept ['backend','frontend','fullstack','infra'] except walter also accepts ['testing']
- [ ] dispatch-to-node.sh + \_dispatch-core.sh — add Linux node type detection for MS-A2 (not macOS, not Windows), correct rsync paths, SSH user
- [ ] build-sidecar.sh + build-monitor.mjs — update all hardcoded Muddy dashboard URL references
- [ ] events.mjs — update ~18 hardcoded IP references including NODE_IP_MAP constant, proxy handler URLs, and node status polling endpoints
- [ ] Hook scripts — developer-brief.sh, recall-on-tool.sh, auto-save-session.sh: replace Lockwood endpoint references with MS-A2 IP (or use cluster-check.sh dynamic lookup)
- [ ] Infrastructure scripts — br-token-refresh.sh (add MS-A2 sync target), ssh-warmup.sh (add MS-A2 IP), br-account-setup.sh + br-swap-accounts.sh (add MS-A2 if needed)
- [ ] Python defaults — ALL Python files in core/cluster/ with hardcoded IPs: node_staging.py, hunt_sourcer.py, delivery_tracker.py, intel_scoring.py, intel_verifier.py, node_tests.py — update LOCKWOOD_URL and BELOW_OLLAMA_URL defaults
- [ ] End-to-end smoke test — new Claude Code session generates brief from MS-A2, file edit triggers recall from MS-A2, bash command saves to MS-A2, build dispatch succeeds to all 7 workers (dispatch dry-run or small test phase to each)

**Success Criteria:** All hardcoded IP references updated across scripts, dashboard, and Python files. `grep -r "10.0.1.101\|10.0.1.104" ~/.buildrunner/scripts/ ~/.buildrunner/dashboard/ core/cluster/` returns zero hits (only cluster.json should have IPs). cluster-check.sh returns correct URLs for all roles. Build dispatch dry-run succeeds to all 7 nodes. SessionStart/PreToolUse/PostToolUse hooks all function.

---

## Phase 5: Deep Below Integration

**Goal:** Below 70B model wired into the skill pipeline — simple tasks route to Below (free, unlimited), complex tasks route to Claude. Every skill that uses intelligence gets a local fallback.

**Files:**

- ~/.buildrunner/lib/inference-router.mjs (NEW)
- ~/.buildrunner/scripts/below-route.sh (NEW)
- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/commands/autopilot.md (MODIFY)
- ~/.claude/commands/review.md (MODIFY)
- ~/.claude/commands/guard.md (MODIFY)
- ~/.buildrunner/scripts/adversarial-review.sh (MODIFY)

**Blocked by:** Phase 4
**Can parallelize:** Phase 6 (different files)
**Deliverables:**

- [ ] inference-router.mjs — complexity scoring module: analyzes phase description, work_type, file count, and dependency depth to produce a routing decision (below | claude). Threshold configurable. Exports `routeInference(phaseDescription, workType) → {target, reason}`
- [ ] below-route.sh — shell wrapper for skills: checks Below health via cluster-check.sh, calls Ollama /api/chat with prompt, returns response. Falls back to "SKIP" (let skill use Claude) if Below offline or response malformed. 10s timeout.
- [ ] /begin update — Step 3 (plan generation): if inference-router routes to below AND phase is backend/infra, call below-route.sh for plan draft, present to user for approval. Claude used for frontend/fullstack/architecture phases.
- [ ] /autopilot update — batch dispatch: simple phases (backend, data-migration, ≤3 deliverables) route to Below for plan+execute when in `go` mode. Complex phases escalate to Claude. Routing logged to decisions.log.
- [ ] /review update — Pass 1 structural compliance: below-route.sh generates checklist of spec deliverables vs actual files changed. Human-readable diff. Claude still does Pass 2 (quality judgment).
- [ ] /guard update — governance validation: below-route.sh checks file list against governance.yaml rules, BUILD spec phase boundaries, and decisions.log constraints. Returns violations list.
- [ ] adversarial-review.sh --local flag — routes adversarial review through Below 70B instead of dispatching to Otis via Claude API. Faster (no API latency), free (no Claude tokens). Falls back to Otis dispatch if Below offline.

**Success Criteria:** /begin on a simple backend phase uses Below for plan generation (verified by checking decisions.log for routing entry). /review Pass 1 runs via Below. adversarial-review.sh --local returns structured findings. Below offline gracefully falls back to Claude with no user-visible error.

---

## Phase 6: vLLM Batch Pipeline

**Goal:** Hunt sourcer batch extraction runs on vLLM tensor parallelism — 100x throughput improvement over Ollama for batch HTML extraction cycles.

**Files:**

- ~/.buildrunner/scripts/below-vllm-setup.sh (NEW)
- ~/.buildrunner/scripts/below-model-swap.sh (NEW)
- core/cluster/hunt_sourcer.py (MODIFY)
- core/cluster/hunt_sources/newegg.py (MODIFY)
- core/cluster/hunt_sources/bhphoto.py (MODIFY)

**Blocked by:** Phase 4
**Can parallelize:** Phase 5 (different files)
**Deliverables:**

- [ ] below-vllm-setup.sh — install vLLM in WSL2 on Below, configure tensor parallelism for dual 3090, pull AWQ-INT4 models (Qwen3-8B-AWQ for extraction), create systemd service, expose on port 8000
- [ ] below-model-swap.sh — VRAM arbitration: stops Ollama 70B model, starts vLLM for batch, reverses when batch complete. Prevents OOM from both running simultaneously. Accepts "ollama" or "vllm" argument.
- [ ] hunt_sourcer.py — add VLLM_BATCH_MODE: when enabled, collect all HTML extraction tasks in cycle, send as batch to vLLM /v1/completions endpoint (OpenAI-compatible), parse batch response. Fall back to Ollama sequential if vLLM unavailable.
- [ ] newegg.py + bhphoto.py — refactor extraction to return raw HTML + prompt instead of calling Ollama directly, allowing hunt_sourcer to batch all HTML extractions into single vLLM call
- [ ] Benchmark — run 100-item extraction cycle on both Ollama (sequential) and vLLM (batch), log timing comparison to ~/.buildrunner/logs/vllm-benchmark.log

**Success Criteria:** vLLM serves on port 8000 with tensor parallelism across both 3090s. Batch extraction of 100 items completes in <10 seconds. Model swap script transitions cleanly without VRAM errors.

---

## Phase 7: Overnight Automation & Dashboard

**Goal:** Launchd-scheduled overnight batch runs /review, /guard, /dead across all projects. Morning report aggregates results. Dashboard updated for 7-node cluster with GPU monitoring.

**Files:**

- ~/.buildrunner/scripts/overnight-batch.sh (NEW)
- ~/.buildrunner/scripts/morning-report.sh (NEW)
- ~/.buildrunner/launchd/com.buildrunner.overnight.plist (NEW)
- ~/.buildrunner/scripts/overnight-discord-alert.sh (NEW)
- ~/.buildrunner/dashboard/events.mjs (MODIFY)
- ~/.buildrunner/dashboard/index.html (MODIFY — active dashboard is vanilla HTML, not React ui/)

**Blocked by:** Phase 5, Phase 6
**Deliverables:**

- [ ] overnight-batch.sh — iterates ~/Projects/\*, runs headless Claude Code with /review + /guard + /dead on each project using Below inference, writes per-project JSON results to ~/.buildrunner/overnight-results/{date}/
- [ ] morning-report.sh — aggregates overnight JSON results into markdown summary: projects reviewed, issues found (critical/warning), dead code detected, governance violations. Writes to ~/.buildrunner/overnight-results/{date}/morning-report.md
- [ ] com.buildrunner.overnight.plist — launchd agent running overnight-batch.sh at 2:00 AM daily, logs to ~/.buildrunner/logs/overnight.log
- [ ] overnight-discord-alert.sh — POST critical findings (governance violations, dead code in production paths) to DISCORD_DEAL_WEBHOOK_URL. Non-critical findings saved for morning report only.
- [ ] events.mjs update — add health polling for MS-A2 (Linux node type), add Below GPU metrics endpoint polling (nvidia-smi JSON output via SSH), store in health history
- [ ] Dashboard index.html — update vanilla HTML dashboard 7-node grid: online/offline status, current role, active build (if any), CPU/memory for all nodes, GPU temp/VRAM/loaded model for Below, index freshness for MS-A2
- [ ] Dashboard smoke test — all 7 nodes visible, Below GPU metrics updating, MS-A2 search latency shown, overnight results accessible from dashboard
- [ ] End-to-end — overnight batch runs on 3 test projects, morning report generates, Discord alert fires for injected test violation

**Success Criteria:** Overnight batch completes across all projects before 6 AM. Morning report is human-readable with actionable items. Dashboard shows all 7 nodes with accurate real-time metrics.

---

## Out of Scope (Future)

- EXO Labs distributed inference (clustering Below + MS-A2 for 120B+ models) — revisit when models exceed 48GB VRAM
- Fine-tuning on dual 3090s — potential but not in v1
- Strix Halo replacement for any node — revisit if M2s become actual bottlenecks
- 10GbE switch/infrastructure — MS-A2 has 10GbE but current network is gigabit; upgrade switch later if vector search latency is bottleneck
- Mac Studio M4 Max for Muddy — daily driver upgrade is separate project
- Third Claude subscription — monitor if 7 workers saturate 1-2 subscriptions
- Proxmox/VM isolation on MS-A2 — bare metal Linux is simpler for v1

---

## Parallelization Matrix

| Phase | Key Files                                                      | Can Parallel With | Blocked By                          |
| ----- | -------------------------------------------------------------- | ----------------- | ----------------------------------- |
| 1     | node_inference.py, 5 new scripts                               | —                 | —                                   |
| 2     | (uses Phase 1 scripts, output logs)                            | 3                 | 1 + HARDWARE GATE (3090s installed) |
| 3     | (uses Phase 1 scripts, output logs)                            | 2                 | 1 + HARDWARE GATE (MS-A2 assembled) |
| 4     | cluster.json, node-matrix.mjs, 13 scripts, 2 Python files      | —                 | 2, 3                                |
| 5     | skill .md files, inference-router.mjs, below-route.sh          | 6                 | 4                                   |
| 6     | hunt_sourcer.py, newegg.py, bhphoto.py, vLLM scripts           | 5                 | 4                                   |
| 7     | overnight scripts, launchd plist, dashboard, ClusterHealth.tsx | —                 | 5, 6                                |

**Optimal Execution Waves:**

- **Wave 1:** Phase 1 (start immediately, no hardware needed)
- **Wave 2:** Phase 2 + Phase 3 (parallel, independent hardware gates)
- **Wave 3:** Phase 4 (atomic reconfiguration, needs both nodes online)
- **Wave 4:** Phase 5 + Phase 6 (parallel, different file sets)
- **Wave 5:** Phase 7 (overnight automation + dashboard)

---

**Total Phases:** 7
**Parallelizable:** Phase 2 || Phase 3, Phase 5 || Phase 6
**Hardware Gates:** Phase 2 (3090s installed), Phase 3 (MS-A2 assembled)
**Estimated Total:** 44 deliverables across 7 phases, 5 execution waves
