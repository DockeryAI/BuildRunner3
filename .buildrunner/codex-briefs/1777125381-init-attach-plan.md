# Second Opinion Brief — BR3 init/attach Overhaul Plan

**Goal:** Make `br init` and `br attach` install the full BR3 capability stack on every web project automatically (matching Synapse parity), auto-detect or prompt for project type (PWA/Capacitor-mobile/Godot/etc.), and add a logging infrastructure for Godot projects (HengeWars) so it can be a standard project type going forward.

**Question:** Where is Claude's plan wrong, missed, or worse than alternatives? Specifically: is the "web baseline + type-deltas" template strategy the right approach? Are the type-detection heuristics in the right order? Is the Godot logger architecture sound? Is anything missing that should block the rollout?

---

## Evidence: Current State of init/attach

### `br init` (cli/main.py:362)

- Path: `~/.local/pipx/venvs/buildrunner/lib/python3.14/site-packages/cli/main.py`
- Creates `.buildrunner/{context,governance,standards}`, `features.json`, `config.yaml`, `CLAUDE.md`, `VISION.md`, `ARCHITECTURE.md`, `PROJECT_SPEC.md`, `ui-libraries.yaml`, `.claude/settings.yaml`, zsh alias.
- **No project-type detection.** Same scaffold for React/Vite, Next.js, PWA, RN, Godot.
- Auto-pastes `"plan new project: <name>"` to Claude via clipboard.

### `br attach` (cli/attach_commands.py)

- Path: `~/.local/pipx/venvs/buildrunner/lib/python3.14/site-packages/cli/attach_commands.py`
- Two modes: quick-register (alias only) and full-scan.
- Full-scan runs `CodebaseScanner` (counts files/langs), `DesignExtractor`, `ConfigGenerator`, 9 Phase-1.8 manifest builders, `FeatureExtractor`, `PRDSynthesizer`, `LeanClaudeMdGenerator`, `FeatureSync`.
- Installs governance tools, slash commands (`/cl`, `/cs`, `/gaps`, `/dbg`, `/bp`, `/why`, `/research`, `/resume`, `/roadmap`, `/later`), context preservation, UI library config.
- Tries to call `~/.buildrunner/scripts/activate-all-systems.sh` — **file does not exist on disk**, fails silently.
- Tries to copy pre-push hook from BR3 root — source path may not exist in installed pipx package.
- `_install_ui_components` only triggers on React in package.json; no other type branching.
- Legacy `~/.br/bin/br-attach` references `~/Projects/build-runner-2.0/.buildrunner` (does not exist). Stale.

### Gaps vs Synapse `.buildrunner/` (gold standard, ~80 files)

Missing from init/attach output, present in Synapse and trailsync and phatti:

- Logger stack: `BRLogger.tsx`, `supabaseLogger.ts`, `brLoggerTransport.ts`, 5 Vite plugins, `br-listen.mjs`
- Edge fn `_debug[]` pipeline: `supabase/functions/_shared/devLog.ts`
- BR3 plumbing: `agents.json`, `skill-state.json`, `behavior.yaml`, `orchestration_state.json`
- Workflow dirs: `plans/`, `codex-briefs/`, `fixit-briefs/`, `adversarial-reviews/`, `validation/`, `verification/`, `reviews/`, `prompts-golden/`, `mockups/`, `specs/`, `design/`
- Real BR3 ship-gate: pre-push hook + `pre-push.d/` pattern + `ship-runner.sh`
- All four surveyed projects (Synapse, trailsync, phatti, HengeWars) still have OLD BR2 `brandock-spec` pre-commit, NOT BR3 ship-gate

---

## Evidence: Existing Project Type Patterns

### PWA (trailsync)

- React 18, Vite 6, `vite-plugin-pwa` v1.2 with `strategies: 'injectManifest'`
- Custom `src/sw.ts` (Workbox: `precacheAndRoute`, `CacheFirst`, `NetworkFirst`, `ExpirationPlugin`)
- `registerType: 'autoUpdate'` with controlled `SKIP_WAITING` multi-tab protocol
- VAPID web push, `PushDebug.tsx` route for iOS diagnostics
- Netlify deploy via `netlify.toml`
- Dexie (IndexedDB) + `@tanstack/react-query-persist-client` offline-first
- `injectManifest.globPatterns` excludes HTML (anti-stale-cache)
- Has `behavior.yaml`, `device.log`, but does NOT have Synapse's `vite-health.log`

### Capacitor mobile (phatti)

- React 19, Vite 8, Tailwind v4, **Capacitor v8** (`@capacitor/{core,ios,camera,preferences}`)
- `vite.config.ts` explicit comment: "VitePWA removed — this is a native Capacitor app. SW caching breaks native deploys"
- `capacitor.config.ts`: `appId: 'com.phatti.app'`, `webContentsDebuggingEnabled: true`
- HTTPS dev server with local certs (`.certs/cert.pem`)
- Build flow: `npm run build && npx cap sync ios` → Xcode → TestFlight
- `.buildrunner/components/captures/capacitor/` — `BRLoggerCapacitor.tsx` + `capacitorCapture.ts` (logs `@capacitor/app` lifecycle, network, device, keyboard)
- `src/lib/device-logger.ts` — console intercept → `device_logs` Supabase table (no-op on web)
- `BRLoggerCapacitor` mounted in `main.tsx` instead of plain `BRLogger`
- `brLoggerTransport.ts` line 58: auto-enables debug on `Capacitor.isNativePlatform()` (no URL param needed)
- Permissions on key files: `-rw-------` (0600) — stricter than trailsync

### Godot (HengeWars, target)

- Godot 4.3, GDScript, single bootstrap `scripts/main.gd`
- Autoloads mandated by CLAUDE.md but not yet wired: `GameState`, `EventBus`, `SaveManager`
- GUT testing framework mandated, not yet installed
- No backend in v1
- Godot writes crash logs to `user://logs/godot.log` resolved via `OS.get_user_data_dir()` → `~/Library/Application Support/Godot/app_userdata/HengeWars/logs/` on macOS
- Godot 4.x has no native `--log-file` flag for stdout teeing
- GDScript has no `console.*` to monkey-patch — every system must explicitly call `BRLogger.info(...)`

---

## Claude's Proposed Plan

### Phase A — Repair foundation

- Restore missing `~/.buildrunner/scripts/activate-all-systems.sh`
- Delete legacy `~/.br/bin/br-attach`
- Fix attach's pre-push hook source path

### Phase B — Project-type plugin system

Detection order:

1. `project.godot` exists → `godot`
2. `capacitor.config.ts/js` or `ios/`/`android/` Capacitor folders → `capacitor`
3. `app.json` with `expo` key, or `eas.json` → `expo` (no example yet)
4. `vite-plugin-pwa` in deps OR `manifest.json` + `service-worker.*` → `pwa`
5. `next.config.*` → `nextjs`
6. `vite.config.*` + React → `vite-react`
7. Else → `web-generic`
8. If ambiguous, prompt user

### Phase C — Web baseline installer (every web type)

Idempotent installer dropping:

- `.buildrunner/components/` full logger stack (5 Vite plugins, BRLogger.tsx, supabaseLogger.ts, brLoggerTransport.ts, br-listen.mjs)
- `.buildrunner/br-listen.mjs` at root
- `supabase/functions/_shared/devLog.ts` with `withDevLogs` + `_debug[]` pattern
- `agents.json`, `skill-state.json`, `behavior.yaml`, `orchestration_state.json`
- All workflow dirs
- `.git/hooks/pre-push` + `.buildrunner/hooks/pre-push.d/50-ship-gate.sh`
- `vite.config.ts` patch: register unified BR logger plugin
- `src/main.tsx` patch: mount `<BRLogger />`
- `package.json` script additions
- CLAUDE.md "Protected files" block

Source: `~/Projects/BuildRunner3/.buildrunner/templates/web-baseline/` (canonical store).

### Phase D — Type-specific deltas

- **PWA delta:** vite-plugin-pwa, src/sw.ts (Workbox), VAPID env, PushDebug.tsx, Netlify config, Dexie + react-query-persist deps, HTML exclusion globPattern
- **Capacitor delta:** all of C with BRLoggerCapacitor swap, @capacitor packages, capacitor.config.ts with debug flag, HTTPS certs, captures/capacitor/ folder, src/lib/device-logger.ts, device_logs migration, main.tsx swap, CLAUDE.md cap-sync rule, ensure VitePWA NOT installed
- **Godot delta:** BRLogger.gd autoload at `scripts/autoloads/BRLogger.gd`, `.buildrunner/scripts/godot-{run,test}.sh` wrappers, Makefile targets `run-logged`/`test-logged`/`logs-clean`, `project.godot` autoload patch (idempotent grep-check), `.gitignore` append, /dbg /device skill log-path config

### Phase E — Use research library to optimize prompts

Pull from Jimmy via `/research` (pinned to claude-sonnet-4-6 per global rule). Queries: prompt structure for instruction-following, ENFORCE blocks Claude 4.7, literal instruction following.

### Phase F — Idempotency, doctor, migration

- All installers idempotent (skip if exists, grep before append)
- `br doctor` (or `br attach --scan` extension) — diff existing project vs baseline, report drift
- Migration: doctor across all existing projects, `br attach --upgrade` to backfill

### Phase G — Godot logger architecture (HengeWars-specific)

- `BRLogger.gd` autoload singleton with severity enum (DEBUG/INFO/WARN/ERROR/EVENT)
- Ring buffer of last 500 entries
- File sinks: `user://logs/brlogger.log`, `user://logs/eventbus.log`, `user://logs/engine.log`
- FPS/memory telemetry sampled every 5s via Timer
- Flush on `NOTIFICATION_WM_CLOSE_REQUEST`
- Shell wrapper `.buildrunner/scripts/godot-run.sh` tees stdout to `.buildrunner/godot.log`, copies `user://` sinks after exit, copies crash trace if exit code non-zero
- GUT wrapper for `.buildrunner/gut.log`
- Log mapping: godot.log↔browser.log, engine.log↔device.log, eventbus.log↔query.log, crash.log, gut.log

---

## Claude's Hypothesis & Confidence

I believe the right solution is:

1. A two-tier installer: web-baseline (universal for any web stack) + type-deltas (PWA/Capacitor/Godot/Next.js/etc.)
2. Detection-with-prompt-fallback rather than pure detection or pure prompt
3. Canonical templates living in the BR3 repo (not the pipx package), so updates propagate via git pull
4. `br doctor` as a non-destructive drift detector that any existing project can run
5. Godot port via GDScript autoload + shell wrappers (no native --log-file support, so wrapper is unavoidable)

I'm less sure about:

- Whether the current `CodebaseScanner` should be extended or replaced
- Whether type detection should run on init too (init creates new dirs — what's there to detect?)
- Whether logger components should be **copied** into each project or **symlinked** to a canonical source for centralized updates
- Whether the BR2-era pre-commit hook in all four projects should be removed during migration or left alongside the new pre-push gate
- Whether the "ENFORCE block" rewrite via research-library findings should be its own phase or wait until after the structural work
- Whether the brittleness of `vite.config.ts` and `src/main.tsx` AST patching is acceptable, or if those patches should be left to the user with clear instructions
