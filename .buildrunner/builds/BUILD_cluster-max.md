# Build: cluster-max

**Created:** 2026-04-12
**Status:** Phase 1 In Progress
**Deploy:** infra — cluster scripts + node services (no web deploy)

## Overview

Upgrade Below to dual RTX 3090 NVLink (48GB VRAM), add Minisforum MS-A2 as combined Memory+Staging node (replacing Lockwood + Lomax roles on 64GB DDR5 with 10GbE), reconfigure all 7 cluster nodes as build workers with priority cascade, and wire Below 70B inference deep into the skill pipeline (/begin, /autopilot, /review, /guard, adversarial-review). Ollama serves all inference — both 70B and 8B models loaded simultaneously (46GB of 48GB VRAM). No vLLM, no model swapping.

## Parallelization Matrix

| Phase | Key Files                                                                   | Can Parallel With | Blocked By             |
| ----- | --------------------------------------------------------------------------- | ----------------- | ---------------------- |
| 1     | Hardware install guide (no code files)                                      | —                 | —                      |
| 2     | below-verify.sh, below-benchmark.sh, ollama-below.env, node_inference.py    | 3                 | 1 (hardware gate only) |
| 3     | ms-a2-bootstrap.sh, migrate-lockwood-data.sh, ms-a2-verify.sh, systemd svcs | 2                 | 1 (hardware gate only) |
| 4     | cluster.json, node-matrix.mjs, events.mjs, ~20 files with hardcoded IPs     | —                 | 2, 3                   |
| 5     | below-route.sh, skill .md files, adversarial-review.sh                      | —                 | 4                      |

**Optimal Execution Waves:**

- **Wave 1:** Phase 1 — hardware installation guide (you do this physically)
- **Wave 2:** Phase 2 + Phase 3 (parallel, independent hardware)
- **Wave 3:** Phase 4 (IP updates + node registration, needs both nodes online)
- **Wave 4:** Phase 5 (Below skill integration)

## Phases

### Phase 1: Hardware Installation, BIOS & Overclocking

**Status:** not_started
**Goal:** Both machines physically assembled, BIOS updated and optimized, GPUs overclocked, everything POST-verified before any software work begins.

**Files:** None (physical hardware phase — documentation output only)
**Blocked by:** None (parts arriving Apr 13-19)

#### Part A: Below — BIOS Update (DO THIS FIRST, before touching any hardware)

The Z390-E is on BIOS v1302 from September 2019. This MUST be updated before installing the 3090s — the 2019 BIOS may not properly initialize Ampere GPUs or support the required PCIe resizable BAR.

**Deliverables:**

- [ ] Download latest Z390-E BIOS from ASUS support (https://rog.asus.com/motherboards/rog-strix/rog-strix-z390-e-gaming/helpdesk_bios/) — get the newest version available. As of 2026 the last release was likely v3004 or later.
- [ ] Copy BIOS file to a FAT32-formatted USB drive (root directory, not in a folder)
- [ ] Boot into BIOS (Del key on POST), go to Tool > ASUS EZ Flash 3, select USB drive, flash the update. DO NOT power off during flash. Takes 3-5 minutes.
- [ ] After reboot, enter BIOS again and load Optimized Defaults (F5) to clear stale settings from the old BIOS version
- [ ] While in BIOS, enable these settings now (saves a trip back later):
  - **Advanced > System Agent Configuration > Above 4G Decoding: Enabled** — required for 48GB VRAM addressing across dual GPUs
  - **Advanced > System Agent Configuration > Re-Size BAR Support: Enabled** (if available on this BIOS version) — improves GPU memory access performance
  - **AI Overclocking > XMP: Enabled** (Profile 1) — enables DDR4-3200 speed for all 4 DIMMs (currently running XMP on 2 DIMMs, need to re-enable after adding 2 more)
  - **Boot > Fast Boot: Disabled** — helps with dual GPU initialization on cold boot
  - **Advanced > PCIe Configuration > PCIEX16_1: Gen3, PCIEX16_2: Gen3** — lock to Gen3 explicitly (prevents auto-negotiation issues with NVLink bridge)
- [ ] Save and exit (F10). Confirm machine boots to Windows normally with the existing 2080 Ti still installed.

#### Part B: Below — PSU Swap (AX860 → RM1200x SHIFT)

The Corsair AX860 cannot safely power dual 3090s (peak draw ~700W for GPUs alone + 125W for i9-9900K). The RM1200x SHIFT provides 1200W with enough headroom.

**Deliverables:**

- [ ] Shut down Below completely. Flip PSU switch off. Unplug power cord. Wait 30 seconds for capacitors to discharge.
- [ ] Photograph all current cable connections before unplugging anything (phone camera — you'll thank yourself later)
- [ ] Remove the AX860: disconnect all cables from motherboard (24-pin ATX, 8-pin CPU, GPU power, SATA, etc.), unscrew PSU from case
- [ ] Install RM1200x SHIFT: the SHIFT design has a different cable management layout — cables connect to the side panel, not the PSU body. Read the RM1200x manual for the SHIFT-specific mounting.
- [ ] Reconnect: 24-pin ATX to motherboard, 8-pin CPU (EPS12V) to top-left of motherboard, SATA power for drives. DO NOT connect GPU power yet (old 2080 Ti stays out — we're going straight to dual 3090s).
- [ ] Test boot WITHOUT any GPU installed — machine should POST to BIOS with onboard display (Z390-E does NOT have integrated graphics unless using an i9-9900K with Intel UHD 630). If the i9-9900K has the iGPU, connect HDMI to the motherboard rear I/O to verify PSU works. If no iGPU output, skip to GPU install and test with first 3090.

#### Part C: Below — RAM Upgrade (32GB → 64GB)

Adding 2×16GB Corsair Vengeance LPX DDR4-3200 (CMW32GX4M2C3200C16) to the empty A1+B1 slots.

**Deliverables:**

- [ ] Install the two new 16GB DIMMs into slots A1 and B1 (the currently empty slots). Match the existing kit: A1 gets a stick, B1 gets a stick. All 4 slots now populated.
- [ ] Boot into BIOS. Verify all 4 DIMMs detected: should show 64GB total. Check memory training passes (no errors on POST).
- [ ] Re-enable XMP Profile 1 — with 4 DIMMs the Z390 memory controller is under more stress. If XMP at 3200MHz fails to POST (3 beeps, auto-recovery), drop to 3000MHz manually: AI Tweaker > DRAM Frequency > DDR4-3000. The 200MHz loss is negligible for LLM inference (memory bandwidth on DDR4 is not the bottleneck — GPU VRAM bandwidth is).
- [ ] Run a quick memory test from Windows (mdsched.exe or MemTest86 USB) to verify stability with 4 DIMMs. 1 pass minimum.

#### Part D: Below — Dual RTX 3090 FE + NVLink Bridge

This is the main event. Two Founders Edition cards with the NVIDIA P3669 3-slot NVLink bridge.

**Deliverables:**

- [ ] Remove the existing RTX 2080 Ti from PCIEX16_1. Set it aside (keep it — spare GPU or sell).
- [ ] Install first RTX 3090 FE into **PCIEX16_1** (top x16 slot, closest to CPU). Secure with bracket screw. Connect **two 8-pin PCIe power cables** from the RM1200x — the 3090 FE uses a 12-pin connector with an included 2×8-pin adapter. Use TWO SEPARATE cables from the PSU, not one daisy-chained cable (each 3090 pulls up to 350W).
- [ ] Install second RTX 3090 FE into **PCIEX16_2** (bottom x16 slot, 3 slots below). Same power cable setup — two separate 8-pin cables from PSU per card. Total: 4 PCIe power cables used.
- [ ] Install the NVIDIA P3669 NVLink bridge — it clips onto the NVLink connectors on the TOP edge of both 3090 FE cards. The 3-slot spacing of the Z390-E matches the P3669 exactly. Press firmly until both sides click. The bridge should sit flat and level.
- [ ] Cable management — with 4 PCIe power cables, route them cleanly to avoid blocking airflow between the two cards. The 3090 FE exhausts heat through the card and out the back — keep the space between cards clear.
- [ ] First boot with dual GPUs: power on, enter BIOS. Verify both GPUs listed in PCIe device list. If only one shows, reseat the second card and check power connections.
- [ ] Boot to Windows. Open Device Manager > Display Adapters — should show two "NVIDIA GeForce RTX 3090" entries. If Windows only sees one, update NVIDIA drivers to latest (clean install via DDU in safe mode first, then fresh driver from nvidia.com).
- [ ] Open nvidia-smi in command prompt — verify both GPUs listed with 24GB each (48GB total). Run `nvidia-smi topo -m` — the NVLink column should show "NV#" (not "PHB" or "SYS") between GPU 0 and GPU 1. If it shows PHB, the NVLink bridge is not seated properly — reseat it.
- [ ] Temperature check: run a GPU stress test (FurMark or 3DMark) for 5 minutes. Both cards should stay under 83°C core. If either throttles, check case airflow — you may need to remove a side panel or add a case fan blowing directly between the cards.

#### Part E: Below — GPU Overclocking & Power Optimization

The 3090 FE has headroom for a mild overclock that squeezes 10-15% more inference throughput at no risk, given the 1200W PSU.

**Deliverables:**

- [ ] Install MSI Afterburner (free, works with all NVIDIA cards including FE)
- [ ] Apply these settings to BOTH GPUs (link them in Afterburner settings):
  - **Power Limit: +15%** (raises from 350W to ~400W per card — well within RM1200x headroom, total GPU draw ~800W + 125W CPU = 925W < 1200W)
  - **Core Clock: +75 MHz** — conservative, stable on nearly all 3090 FE silicon. Start here, test, then try +100 if stable.
  - **Memory Clock: +300 MHz** — GDDR6X on the 3090 responds well to memory OC. This directly improves LLM inference since it increases memory bandwidth. Start at +300, can push to +500 if no artifacts.
  - **Fan Curve: Aggressive** — this is a server, not a gaming PC. Set fans to 70% at 65°C, 85% at 75°C, 100% at 80°C. Noise doesn't matter for a closet/under-desk machine.
  - **Temp Limit: 85°C** — gives 2°C headroom above throttle point (83°C) for transient spikes
- [ ] Save as Profile 1 in Afterburner. Enable "Start with Windows" and "Apply on startup" so the OC persists across reboots.
- [ ] Stability test: run Ollama with qwen3:8b and generate 1000 tokens 10 times. If any generation produces garbled output or Ollama crashes, back off core clock by 25 MHz and retry. Memory OC artifacts usually show as NaN or inf in model output.
- [ ] VRAM thermal check: run `nvidia-smi -q -d TEMPERATURE` — look for "GPU Current Temp" AND "Memory Current Temp" (3090 FE has GDDR6X thermal sensors). Memory should stay under 100°C (throttle at 110°C). If memory is hot (>95°C), consider thermal pad replacement on VRAM (advanced, skip for v1) or reduce memory OC to +200.

#### Part F: MS-A2 Assembly

The Minisforum MS-A2 arrives barebones. Needs DDR5 SODIMM and NVMe installed.

**Deliverables:**

- [ ] Open the MS-A2 bottom panel (4 screws). The SODIMM slots and M.2 slots are accessible.
- [ ] Install the Crucial 64GB DDR5-5600 SODIMM kit (2×32GB) into both SODIMM slots. Press until clips engage on both sides.
- [ ] Install the WD Blue SN5000 2TB NVMe into the primary M.2 slot (the one closest to the CPU/heatsink). The MS-A2 has 3× M.2 slots — use slot 1 for the OS + data drive.
- [ ] Close the panel. Connect power, ethernet (use one of the 2.5GbE ports for now — 10GbE SFP+ requires a switch upgrade later), HDMI to a monitor for initial setup.
- [ ] Power on. Enter BIOS — verify 64GB RAM detected, 2TB NVMe detected. Enable XMP/EXPO for DDR5-5600 if not auto-detected.
- [ ] Install Ubuntu Server 24.04 LTS (or latest LTS). During install: set hostname to "ms-a2" (or the blues name you pick for this node), create user "byronhudson", enable SSH server, set static IP on the 2.5GbE interface (e.g., 10.0.1.106 or take over 10.0.1.101 from Lockwood).
- [ ] After install: verify SSH from Muddy works (`ssh byronhudson@<MS-A2-IP>`), verify 64GB RAM visible (`free -h`), verify 2TB NVMe mounted (`lsblk`).

#### Part G: Verification Checklist

Before moving to Phase 2 (software):

- [ ] Below: 2× RTX 3090 detected, NVLink active, 48GB VRAM, 64GB system RAM, 1200W PSU, BIOS updated, OC applied, stable under load
- [ ] MS-A2: 64GB DDR5, 2TB NVMe, Ubuntu Server installed, SSH accessible from Muddy, static IP assigned
- [ ] Old 2080 Ti: set aside (spare or sell)

**Success Criteria:** Both machines POST, pass stability tests, and are SSH-accessible from Muddy. Below shows NVLink in nvidia-smi topo. MS-A2 shows 64GB RAM and 2TB disk. No thermal throttling under sustained load.

---

### Phase 2: Below Activation

**Status:** not_started
**Goal:** Dual 3090 NVLink operational, Ollama serving 70B models at 20+ tok/s, existing scoring pipeline verified against upgraded hardware.

**HARDWARE GATE:** User confirms 3090s + RM1200x PSU + 32GB DDR4 physically installed, Below machine boots to Windows.

**Files:**

- ~/.buildrunner/scripts/below-verify.sh (NEW)
- ~/.buildrunner/scripts/below-benchmark.sh (NEW)
- ~/.buildrunner/config/ollama-below.env (NEW)
- core/cluster/node_inference.py (MODIFY — update GPU count, VRAM config, NVLink detection)
- ~/.buildrunner/logs/below-benchmark.log (NEW — output artifact)
- ~/.buildrunner/logs/below-activation.log (NEW — output artifact)

**Blocked by:** Phase 1 (hardware gate only — no script dependencies)
**Can parallelize:** Phase 3 (different node, independent hardware gate)
**Deliverables:**

- [ ] Create below-verify.sh — SSH into Below, run nvidia-smi checks: dual 3090 detected, NVLink bridge active (nvidia-smi topo shows NV# link), 48GB VRAM visible, CUDA driver current, Above 4G Decoding confirmed. Exit codes: 0 = all pass, 1 = critical failure, 2 = warning (degraded but functional).
- [ ] Create ollama-below.env — Ollama environment config: OLLAMA_FLASH_ATTENTION=1, OLLAMA_KEEP_ALIVE=0, OLLAMA_NUM_PARALLEL=4, OLLAMA_HOST=0.0.0.0:11434, CUDA_VISIBLE_DEVICES=0,1. Deploy to Below and apply via Windows service or WSL systemd.
- [ ] Deploy Ollama with ollama-below.env — install/update Ollama service on Below, apply environment config, verify Ollama starts and listens on 0.0.0.0:11434
- [ ] Pull models — qwen3:8b (~5GB VRAM), llama3.3:70b-instruct-q4_K_M (~41GB VRAM), deepseek-r1:70b-q4_K_M (~43GB VRAM, swap with llama when needed), nomic-embed-text (~274MB VRAM)
- [ ] Create below-benchmark.sh — runs tok/s benchmarks for 70B (target: 18-25), 8B (target: 80-120), confirms NVLink speedup over single-GPU baseline (expect 30%+ on 70B). Outputs structured log to below-benchmark.log.
- [ ] Update node_inference.py — update GPU count from 1 to 2, VRAM from 11GB to 48GB, add NVLink detection flag, update model capacity calculations for dual-GPU pipeline parallelism
- [ ] Smoke test — intel_scoring.py scores 5 test deal items against upgraded Below, results match expected JSON format (score 0-100, verdict string, assessment string), latency within reasonable range

**Success Criteria:** 70B model generates at 18+ tok/s. NVLink detected in nvidia-smi topo. qwen3:8b stays resident alongside 70B model load (5GB + 41GB = 46GB < 48GB). Scoring pipeline returns valid scores.

---

### Phase 3: MS-A2 Activation

**Status:** not_started
**Goal:** MS-A2 running all Lockwood + Lomax services on systemd, data migrated, all endpoints responding identically to original nodes.

**HARDWARE GATE:** User confirms MS-A2 assembled with 64GB DDR5-5600 + 2TB NVMe, powered on, accessible on network via SSH.

**Files:**

- ~/.buildrunner/scripts/ms-a2-bootstrap.sh (NEW)
- ~/.buildrunner/scripts/migrate-lockwood-data.sh (NEW)
- ~/.buildrunner/scripts/ms-a2-verify.sh (NEW)
- ~/.buildrunner/logs/ms-a2-activation.log (NEW — output artifact)

**Blocked by:** Phase 1 (hardware gate only — no script dependencies)
**Can parallelize:** Phase 2 (different node, independent hardware gate)
**Deliverables:**

- [ ] Create and run ms-a2-bootstrap.sh on MS-A2 — Ubuntu Server packages installed (python3, python3-venv, node 22, npm, git, rsync, build-essential, sqlite3), SSH keys deployed from Muddy, cluster auth working, firewall opened for ports 8100 + 4200
- [ ] Deploy BR3 codebase — git clone BuildRunner3 repo to ~/repos/BuildRunner3 on MS-A2, create Python venv, pip install requirements (fastapi, uvicorn, lancedb, httpx, sentence-transformers, nomic, etc.)
- [ ] Deploy node_semantic.py as systemd service — create /etc/systemd/system/br3-semantic.service, enable on boot, ExecStart=uvicorn on port 8100. LanceDB initialized, embedding models loaded (CodeRankEmbed for code, all-MiniLM-L6-v2 for research), /api/search and /api/brief/{project} responding
- [ ] Deploy node_intelligence.py as systemd service — create /etc/systemd/system/br3-intel.service, enable on boot. Intel API, deals API, all 5 background crons started (pollers, scoring, verifier, sourcer, seller_verifier). Env vars set: BELOW_OLLAMA_URL, EBAY_APP_ID, EBAY_SECRET, APIFY_API_KEY, TRACK17_API_KEY, DISCORD_DEAL_WEBHOOK_URL
- [ ] Deploy node_staging.py as systemd service — create /etc/systemd/system/br3-staging.service, enable on boot. Preview deploy endpoint, build validation working. VRT Docker stack stays on old Lomax for v1 (no Docker required on MS-A2)
- [ ] Create and run migrate-lockwood-data.sh — rsync ~/.lockwood/ from old Lockwood (10.0.1.101) to MS-A2. Verify: LanceDB vector tables exist + row counts match, memory.db tables populated (session_state, build_history, test_results, log_patterns, architecture_notes, plan_outcomes), intel.db tables populated (deal_items, active_hunts, price_history, intel_items, intel_improvements)
- [ ] Create and run ms-a2-verify.sh — all endpoints return 200, SessionStart brief generates correctly from MS-A2 (compare output with old Lockwood brief), semantic search returns relevant results for test query, intel scoring cron fires and connects to Below for LLM scoring. Reboot MS-A2 and verify all 3 systemd services restart automatically.

**Success Criteria:** All Lockwood API endpoints respond on MS-A2. Staging endpoints respond on MS-A2. Data integrity verified (row counts, search quality). All 3 systemd services enabled and surviving reboot test.

---

### Phase 4: Cluster Reconfiguration — 7 Workers

**Status:** not_started
**Goal:** All 7 nodes registered as build workers, hardcoded IPs updated to point at MS-A2 where Lockwood used to be, dispatch works to every node including Linux (MS-A2).

**Nature of the work:** This is a mechanical find-and-replace. A grep across scripts, dashboard, and Python files found ~20 files with hardcoded Lockwood/Lomax/Below IPs. Most changes are one-line IP updates or adding MS-A2 to a node list. The only non-trivial change is adding Linux node detection to the dispatch scripts.

**NOTE:** All ~/.buildrunner/ files live OUTSIDE the git repo at $HOME/.buildrunner/. They are NOT in the project directory.

**Blocked by:** Phase 2, Phase 3
**Deliverables:**

- [ ] cluster.json — add MS-A2 node (roles: [semantic-search, staging-server, parallel-builder], platform: "linux"), update Below spec ("2x RTX 3090 NVLink"), mark Lockwood + Lomax as parallel-builder overflow workers
- [ ] node-matrix.mjs — 7 workers ranked by health + load, not per-node capability filtering (all nodes accept all work types). Priority order: otis, below, ms-a2, lockwood, lomax, muddy, walter
- [ ] dispatch-to-node.sh + \_dispatch-core.sh — add is_linux_node() for MS-A2 (rsync instead of tar+scp, correct SSH paths)
- [ ] Find-and-replace hardcoded IPs — run `grep -r "10.0.1.101\|10.0.1.104" ~/.buildrunner/ core/cluster/` and update every hit: Lockwood refs → MS-A2 IP, add MS-A2 to node lists in events.mjs, dashboard integrations, ssh-warmup.sh, br-token-refresh.sh, Python env var defaults. Approximately 20 files, mostly one-line changes.
- [ ] Smoke test — SessionStart brief from MS-A2, dispatch dry-run to all 7 nodes, grep confirms zero hardcoded Lockwood/Lomax IPs outside cluster.json

**Success Criteria:** cluster-check.sh returns correct URLs for all 7 nodes. Dispatch dry-run succeeds to all nodes. Hooks function via MS-A2.

---

### Phase 5: Below Skill Integration

**Status:** not_started
**Goal:** Below 70B wired into the skill pipeline as the default first choice for verified work. Simple routing table — no complexity scoring algorithm. Below handles every job where something else checks its work. Claude handles implementation and final quality review.

**Routing rule (hardcoded in below-route.sh, not a scoring engine):**

- First pass / draft / structural check → Below
- Implementation / final quality review / frontend → Claude
- Below offline → Claude (graceful fallback, no user-visible error)

**Quality firewall:** Nothing Below produces ships without a Claude verification pass, an automated test pass, or user review.

**Files:**

- ~/.buildrunner/scripts/below-route.sh (NEW)
- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/commands/autopilot.md (MODIFY)
- ~/.claude/commands/review.md (MODIFY)
- ~/.claude/commands/guard.md (MODIFY)
- ~/.buildrunner/scripts/adversarial-review.sh (MODIFY)

**Blocked by:** Phase 4
**Deliverables:**

- [ ] below-route.sh — shell wrapper: checks Below health via cluster-check.sh, calls Ollama /api/chat with prompt + model (default llama3.3:70b), returns response to stdout. Exit code 2 if Below offline or malformed response (lets calling skill fall back to Claude). 30s timeout. --model flag to override (e.g. deepseek-r1:70b for reasoning tasks). No separate inference-router.mjs — the routing decision lives in each skill's own logic as a simple if/else.
- [ ] /begin update — plan generation: call below-route.sh for plan draft on backend/infra phases, present for approval. Claude used for frontend/fullstack/architecture. Log routing to decisions.log.
- [ ] /autopilot update — simple phases (backend, data-migration, ≤3 deliverables, no UI files) route to Below in `go` mode. Complex phases → Claude.
- [ ] /review update — Pass 1 structural compliance via below-route.sh (spec deliverables vs files changed). Claude still does Pass 2 (quality). Fallback: Explore subagents if Below offline.
- [ ] /guard update — governance validation via below-route.sh (governance.yaml rules, BUILD spec boundaries, decisions.log constraints). Fallback: skip if Below offline.
- [ ] adversarial-review.sh --local — routes through Below 70B instead of Otis/Claude API. Free, no SSH overhead. Fallback: Otis dispatch if Below offline.

**Success Criteria:** /begin uses Below for simple backend plan drafts (decisions.log shows routing). /review Pass 1 runs via Below. adversarial-review.sh --local returns valid findings. All fallbacks work cleanly when Below is offline.

---

## Out of Scope (Future / Roadmap)

- vLLM batch pipeline — Ollama handles all inference (70B + 8B loaded simultaneously, 46GB of 48GB). vLLM tensor parallelism is a future optimization if batch extraction volumes exceed ~100 items/cycle where the 30-50s Ollama time matters. No model swapping needed.
- Overnight automation (batch /review + /guard + /dead across all projects) — build overnight-batch.sh and run manually first. If the results are actionable, then automate with launchd, morning reports, and Discord alerts. Don't build the factory before selling the first widget.
- Dashboard 7-node grid with GPU metrics — add MS-A2 and Below GPU monitoring to dashboard after Phase 4 proves the cluster works. Don't spec dashboard UI alongside infrastructure.
- EXO Labs distributed inference (clustering Below + MS-A2 for 120B+ models) — revisit when models exceed 48GB VRAM
- Fine-tuning custom models on dual 3090s — potential but not in v1
- Strix Halo node replacement for any M2 — revisit if M2s become actual bottlenecks
- 10GbE network switch upgrade — MS-A2 has 10GbE SFP+ but current network is gigabit; upgrade switch later if vector search latency is bottleneck
- Mac Studio M4 Max for Muddy daily driver — separate project
- Third Claude subscription — monitor if 7 workers saturate 1-2 subscriptions
- Proxmox/VM isolation on MS-A2 — bare metal Linux is simpler for v1
- VRT Docker stack migration from old Lomax to MS-A2 — stays on Lomax for v1, migrate later if Lomax retired
- React dashboard (ui/) rebuild — active dashboard is vanilla HTML; React port is separate project

## Session Log

[Will be updated by /begin]
