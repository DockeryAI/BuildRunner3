# Build: BR3 Cluster Infrastructure

**Created:** 2026-04-03
**Status:** Phase 6 blocked on Below hardware (Phases 4, 5, 7, 8 complete — 2026-04-05)
**Deploy:** local network — 6 machines via gigabit switch, REST APIs on each node

## Overview

Six machines operating as a development team. Persistent memory, continuous testing, live staging, parallel Claude Code building, and local inference — all coordinated by BR3 with instant disconnect/reconnect.

## Hardware Map — The Blues Cluster

| Name         | Machine           | IP         | Role                                                    |
| ------------ | ----------------- | ---------- | ------------------------------------------------------- |
| **Muddy**    | M5 32GB           | 10.0.1.100 | Command — primary dev + log analysis + deployments      |
| **Lockwood** | M2 8GB            | 10.0.1.101 | Memory — vector DB, semantic search, session state      |
| **Walter**   | M2 8GB            | 10.0.1.102 | Sentinel — continuous testing (vitest + Playwright)     |
| **Lomax**    | M2 8GB            | 10.0.1.104 | Forge — staging server (live apps) + build validation   |
| **Otis**     | M2 8GB            | 10.0.1.103 | Second builder — parallel Claude Code via BR3 dispatch  |
| **Below**    | Windows i9+2080Ti | 10.0.1.105 | Workhorse — local inference + Supabase sandbox + builds |

**Network:** Cluster uses `10.0.1.x` subnet (ethernet/switch). WiFi stays on `192.168.1.x` (internet).

**Future upgrade:** Mac Mini M4 Pro 48GB ($1,999) — adds as 7th node, runs 32B models, replaces Below for inference.

## Completed Phases

### Phase 0: Foundation ✅

Disconnect switch, cluster-check.sh, /cluster skill, base_service.py, developer brief, SessionStart hook.

### Phase 1: Lockwood — Memory ✅

CodeRankEmbed + LanceDB + AST chunking. 82K chunks, 3,942 files. Persistent memory, build history, session state. All research applied.

### Phase 2: Walter — Testing ✅

Continuous vitest + Playwright (WebKit, pin v1.56). SQLite results. Flaky detection. LaunchAgent auto-restart.

### Phase 3: Crawford — Log Analysis ✅ (role moving to Muddy)

Pattern detection, cross-file correlation, error fingerprinting. Will be moved to Muddy in Phase 4.

---

## Remaining Phases

### Phase 4: Crawford → Otis Conversion + Log Analysis to Muddy ✅

**Status:** complete (2026-04-05)

**What happens:**

1. Move Crawford's log analysis service to run on Muddy as a background process (logs are already local — no SSH sync needed)
2. Rename Crawford → Otis in cluster.json, CLAUDE.md, all references
3. Wipe Crawford's analysis service from the M2
4. Install Claude Code on Otis
5. Configure headless mode (`-p` flag + API key)
6. Set up SSH key auth so Muddy can dispatch work to Otis
7. Configure Lockwood's SessionStart hook on Otis so Claude starts warm

**BR3 changes:**

- Developer brief runs log analysis locally on Muddy instead of calling Crawford API
- `/diag`, `/dbg`, `/sdb` fall back to local analysis (already the fallback path)
- cluster.json updated: Crawford removed, Otis added with role "parallel-builder"

**Files:**

- `~/.buildrunner/cluster.json` (MODIFY — rename Crawford → Otis, change role)
- `~/.claude/CLAUDE.md` (MODIFY — update node table)
- `.buildrunner/scripts/developer-brief.sh` (MODIFY — run log analysis locally)
- `core/cluster/node_analysis.py` (MODIFY — remove SSH tail, run locally)

**Success Criteria:**

- Log analysis runs on Muddy, patterns still appear in developer brief
- Otis responds to SSH from Muddy
- Claude Code headless mode works on Otis
- `/cluster` shows Otis as "parallel-builder" online

---

### Phase 5: Lomax — Staging Server + Build Validation ✅

**Status:** complete (2026-04-05)
**Hardware:** M2 #4 (Lomax) at 10.0.1.104

**YOU do:**

1. Cable Lomax to switch, enable SSH
2. Tell Claude: "Lomax hardware ready"

**What gets built:**

- Live Vite preview servers for all projects (npm run dev on each, ~50-100MB each)
- Continuous build validation: `tsc --noEmit` + `vite build` on file changes
- Netlify preview deploy on demand via `/preview`
- pnpm with global virtual store for shared node_modules
- Build result API: `/api/build/status`, `/api/build/errors`, `/api/preview`

**BR3 changes:**

- `/preview` command — triggers Netlify deploy from Lomax, returns URL
- `/begin` post-phase check includes "does it build?" from Lomax
- Developer brief shows build pass/fail from Lomax
- `/guard` pulls build status

**Success Criteria:**

- All projects accessible on network (phone can reach `10.0.1.104:5173`)
- `tsc --noEmit` catches type errors dev server misses
- `/preview` returns working Netlify URL
- Disconnect → builds run locally on Muddy

---

### Phase 6: Below — Inference + Supabase Sandbox

**Status:** not_started
**Hardware:** Windows i9+32GB+2080Ti at 10.0.1.105

**YOU do:**

1. Cable Below to switch
2. Set static IP `10.0.1.105` in Windows network settings
3. Install Ollama, pull Qwen 2.5 14B model
4. Set OLLAMA_HOST=0.0.0.0, open firewall ports
5. Install Docker Desktop + Supabase CLI
6. Tell Claude: "Below hardware ready"

**What gets built:**

- Ollama on GPU (Qwen 2.5 14B Q4 on 11GB VRAM)
- FastAPI wrapper with task-specific prompts: `/api/classify`, `/api/draft`, `/api/summarize`
- Full Supabase Docker stack (all 13 services — 32GB handles it easily)
- Migration dry-run endpoint: `/api/migration/dryrun`
- Heavy build capability: route large `tsc` + `vite build` to i9

**BR3 changes:**

- Model routing gains local tier — simple phases route to Below for first draft
- `/autopilot` can route simple phases to Below's local model
- Migration safety: `/begin` validates migrations against Below's Supabase before prod push
- Developer brief shows Below inference status and Supabase sandbox state

**Success Criteria:**

- Classification within 5 seconds, >85% accuracy
- `nvidia-smi` confirms GPU usage
- `supabase start` runs all 13 services (verify with `supabase status`)
- Migration dry-run passes/fails correctly
- Disconnect → everything routes to Opus, migrations tested on prod directly

---

### Phase 7: BR3 Orchestration — Parallel Build Dispatch ✅

**Status:** complete (2026-04-05) — opt-in dispatch via `dispatch-phase-to-otis.sh`

**What gets built:**
This is the phase that ties everything together. BR3 learns to use Otis.

**`/begin` changes:**

1. Before starting a phase, check if Otis is available: `cluster-check.sh parallel-builder`
2. If the current phase is backend-only (no frontend files), offer to dispatch to Otis
3. Dispatch via: `ssh otis "cd ~/repos/PROJECT && claude -p 'Execute Phase N: [deliverables]' --auto-accept"`
4. Monitor progress via SSH or Claude Code channels
5. When Otis completes, pull changes via git: `git fetch otis-remote && git merge`
6. Record outcome to Lockwood

**`/autopilot` changes:**

1. In batch execution (Step 4.3), classify phases as backend/frontend
2. Backend phases → dispatch to Otis (headless Claude Code via SSH)
3. Frontend phases → run on Muddy (main agent, needs design context)
4. Both run simultaneously within a batch
5. Wait for both to complete before advancing to next batch
6. If Otis fails, fall back to running on Muddy (same as today)

**New: Git sync between Muddy and Otis:**

- Otis clones repos from Muddy (or GitHub) into ~/repos/
- After each phase, Otis commits and pushes to a branch
- Muddy pulls and merges (or reviews before merging)
- BR3's existing phase locking prevents file conflicts

**Files:**

- `~/.claude/commands/begin.md` (MODIFY — add Otis dispatch logic)
- `~/.claude/commands/autopilot.md` (MODIFY — add parallel dispatch to Otis)
- `~/.buildrunner/scripts/dispatch-to-otis.sh` (NEW — SSH + headless Claude Code wrapper)
- `~/.claude/commands/cluster.md` (MODIFY — show Otis work status)

**Success Criteria:**

1. `/begin` on a backend phase → dispatches to Otis automatically
2. Otis completes the phase, commits to branch, Muddy merges
3. `/autopilot` runs 2 phases simultaneously (frontend on Muddy, backend on Otis)
4. If Otis is offline, everything runs on Muddy as today
5. Lockwood records outcomes from both Muddy and Otis
6. Walter tests changes from both sources

---

### Phase 8: Integration + Polish ✅

**Status:** complete (2026-04-05) — brief/cluster/reset-cluster updated for all node types

**What gets built:**

- Developer brief aggregates from all 6 nodes
- Lockwood's SessionStart hook configured on Otis and Below
- `/cluster` shows full health dashboard with all roles
- Cross-project regression: Lockwood detects impact → Walter tests → Lomax builds
- Full disconnect/reconnect test: pull ethernet, everything local, plug back in, cluster resumes
- `/reset-cluster` updated for new node names

**Success Criteria:**

1. `/cluster` — all 6 nodes green with correct roles
2. New Claude session on any project — full brief with data from all nodes
3. Pull ethernet cable mid-build — everything works locally
4. Plug back in — all nodes recover within 10 seconds

---

## Out of Scope (Future)

- Mac Mini M4 Pro 48GB (7th node — adds 32B local inference)
- Multi-repo Agent Teams coordination
- Container orchestration (k3s/Nomad — research says skip)
- MCP server registration for cluster nodes
- Distributed file system between nodes

## Session Log

- 2026-04-04: Phases 0-3 complete. Research identified role reallocation: Crawford→Otis (parallel builder), log analysis→Muddy, Lomax→staging+builds. 5 research documents saved to library. /cluster-research skill created. Monthly auto-update cron on all nodes. /reset-cluster skill created.
