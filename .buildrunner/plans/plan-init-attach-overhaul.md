# Plan: BR3 init/attach Overhaul — Project-Type-Aware Installer

## Goal

Make `br init` and `br attach` install the full BR3 capability stack on every project automatically, with reliable asset distribution, correct hook policy, and a composable type model that handles React/Vite, Next.js, PWA, Capacitor, Expo/React Native, and Godot — including a logging adapter for Godot so HengeWars and future game projects get observability parity.

## Background and Codex-Reviewed Constraints

The current `br init` and `br attach` install only ~10% of what mature BR3 projects (Synapse, trailsync, phatti) actually contain. The plan was reviewed by Codex (adversarial pass; see `.buildrunner/codex-briefs/1777125381-init-attach-plan.md`). Codex flagged the following blockers, which this plan now corrects:

- **Packaging gap, not missing scripts.** `activate-all-systems.sh` exists at `.buildrunner/scripts/activate-all-systems.sh`. The real problem is `pyproject.toml` only packages `cli*`, `core*`, `templates*` Python sources — not `.buildrunner/**` assets. After `pipx install`, the CLI cannot reach those files.
- **Hook names are stale.** Real hooks are `pre-commit-enforced` and `pre-push-enforced`. Activation script and installer search for the wrong names. Pre-push fragments live at `.git/hooks/pre-push.d/`.
- **Canonical templates cannot live in `~/Projects/BuildRunner3/`.** `br` runs from a pipx path, not a guaranteed clone. Use `importlib.resources` for in-package assets and sync to `~/.buildrunner/templates/` on install/upgrade.
- **"Web baseline" is React/Vite/Supabase baseline.** Real model is `framework + bundler + capabilities[]` — facets composed independently, not exclusive types.
- **PWA detection by `manifest.json + service-worker.*` is too loose.** Require `vite-plugin-pwa` in deps AND custom `sw.ts`. Capacitor detection requires `capacitor.config.*` AND `@capacitor/core` in deps.
- **Init has nothing to detect.** Type selection on `br init` is prompt/flag-based. Detection runs only on `br attach`.
- **Codemods on `vite.config.ts` and `src/main.tsx` are brittle by default.** Use parser/codemod with manual-instructions fallback when confidence is low.
- **PWA delta in earlier draft was overfitted to trailsync** (PushDebug, VAPID, Dexie, Netlify all product choices). These move to opt-in capability modules, not the default PWA delta.
- **Capacitor delta was overfitted to phatti** (HTTPS certs, `device_logs` SQL). Same fix — opt-in capabilities. Forced removal of `vite-plugin-pwa` is the only intrinsic Capacitor rule.
- **Hook fragment location.** `.git/hooks/pre-push.d/` is the working location; the earlier `.buildrunner/hooks/pre-push.d/` would not execute.
- **BR2 hook coexistence policy is required before rollout.** Replace BR2 hooks; back up to `.buildrunner/hooks/legacy/`.
- **Drift detector cannot reuse `br doctor`** — that command already exists and is a host health checker. Use `br audit`.
- **Godot logger needs an instrumentation plan.** GDScript cannot monkey-patch — autoloads must explicitly call `BRLogger.info()`. The Godot adapter ships pre-instrumented `GameState`, `EventBus`, `SaveManager` templates.
- **`project.godot` patching must be parser-based**, not grep+append (autoload section is order-sensitive).
- **Godot wrapper is partial coverage.** Editor-launched sessions and hard crashes before orderly shutdown are not captured. Document the limit in CLAUDE.md template.
- **Phase 9 (research-library prompt polish) is deferred to out-of-scope.** Not on the critical path.

## Phases

### Phase 1: Asset Packaging and Path Resolution

**Goal:** `br` resolves its own assets reliably regardless of install method (pipx, dev install, fresh clone). Eliminates the "asset path silently broken" failure mode.

**Files:**

- `pyproject.toml` (MODIFY)
- `core/asset_resolver.py` (NEW)
- `cli/main.py` (MODIFY — replace hard-coded paths)
- `cli/attach_commands.py` (MODIFY — replace hard-coded paths)
- `cli/upgrade_commands.py` (NEW — adds `br upgrade` to sync `~/.buildrunner/templates/`)
- `tests/core/test_asset_resolver.py` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Update `pyproject.toml` `[tool.setuptools.package-data]` to include `.buildrunner/templates/**`, `.buildrunner/scripts/**`, and `templates/**` (plus create empty `templates/.gitkeep` so the glob is non-empty before Phases 5–8 populate it; otherwise an interim wheel ships an empty templates package)
- [ ] Implement `core/asset_resolver.py` using `importlib.resources` with a `~/.buildrunner/templates/` overlay
- [ ] Replace hard-coded `~/Projects/BuildRunner3/...` paths in `cli/main.py` with resolver calls
- [ ] Replace hard-coded paths in `cli/attach_commands.py` with resolver calls
- [ ] Add `br upgrade` command that syncs packaged templates → `~/.buildrunner/templates/` (idempotent, diff-aware)
- [ ] Move legacy `~/.br/bin/br-attach` to `~/.br/bin/br-attach.deprecated.bak` with a one-line stub explaining the move
- [ ] Add tests covering pipx-style install, dev install, and overlay precedence

**Success Criteria:** `br init` and `br attach` work in a fresh pipx install with `~/Projects/BuildRunner3/` deleted. `br upgrade` populates `~/.buildrunner/templates/` from the wheel. Resolver tests pass.

### Phase 2: Hook Policy and BR2 Coexistence

**Goal:** Hook installer uses correct names, installs to the location the enforced hook actually reads, and explicitly handles legacy BR2 `brandock-spec` hooks.

**Files:**

- `.buildrunner/scripts/activate-all-systems.sh` (MODIFY)
- `.buildrunner/hooks/pre-commit-enforced` (REVIEW — confirm canonical)
- `.buildrunner/hooks/pre-push-enforced` (REVIEW)
- `core/installer/hook_installer.py` (NEW)
- `docs/hook-policy.md` (NEW)
- `tests/core/installer/test_hook_installer.py` (NEW)

**Blocked by:** None (file-disjoint from Phase 1)

**Deliverables:**

- [ ] Rename hook references in `activate-all-systems.sh` to `pre-commit-enforced` / `pre-push-enforced`
- [ ] Confirm and document `.git/hooks/pre-push.d/` as the canonical fragment location
- [ ] Create `core/installer/hook_installer.py` that detects existing BR2 hooks (`brandock-spec`), backs them up to `.buildrunner/hooks/legacy/`, and replaces with BR3
- [ ] Log every hook swap to `.buildrunner/decisions.log`
- [ ] Write `docs/hook-policy.md` explaining replace-not-chain rationale
- [ ] Add test: simulate BR2 → BR3 transition on a fixture project and verify backup + replacement

**Success Criteria:** Running the installer on a project with BR2 hooks moves them to `legacy/`, installs BR3 enforced hooks under `.git/hooks/`, registers fragments under `.git/hooks/pre-push.d/`, and a manual `git push` runs the BR3 ship gate.

### Phase 3: Project-Type Facet Model

**Goal:** Define the data model that lets the installer compose adapters for mixed-stack projects (Next+PWA, React+Vite+Capacitor, etc.).

**Files:**

- `core/project_type/__init__.py` (NEW)
- `core/project_type/facets.py` (NEW)
- `core/project_type/composition.py` (NEW)
- `tests/core/project_type/test_facets.py` (NEW)

**Blocked by:** None (pure data classes, no runtime deps)

**Deliverables:**

- [ ] Define `Framework` enum: `react`, `vue`, `svelte`, `vanilla`, `godot`, `expo`, `unknown`
- [ ] Define `Bundler` enum: `vite`, `next`, `remix`, `astro`, `sveltekit`, `metro`, `godot_editor`, `none`. (Note: `godot_editor` is the Godot Engine's own asset/scene compiler, treated as a bundler-equivalent for installer dispatch; it is not a webpack/vite/metro-class JS bundler. The enum name uses `godot_editor` rather than `godot_engine` to avoid the engine-vs-bundler semantic clash and to make audit-report strings clearer.)
- [ ] Define `Capability` enum: `pwa`, `capacitor`, `expo_native`, `web_push_vapid`, `dexie_offline`, `react_query_persist`, `supabase_edge`, `netlify_deploy`, `electron`, `tauri`. Document the `Framework.expo` vs `Capability.expo_native` boundary: `Framework.expo` means the project is an Expo-managed React Native app (root has `expo` in `app.json`); `Capability.expo_native` means EAS native build modules / TestFlight/Play Store pipeline are in use. A bare-bones managed Expo app has `framework=expo` and no `expo_native` capability; an EAS Build project has both.
- [ ] Implement `ProjectFacets` dataclass with `framework`, `bundler`, `backend`, `capabilities: set[Capability]`
- [ ] Add validation: `capacitor` capability forces removal of `pwa` capability with a recorded conflict
- [ ] Add `__str__`/serialization for stable snapshots in `agents.json` and audit reports
- [ ] Tests for composition rules and conflict resolution

**Success Criteria:** All four reference projects (Synapse, trailsync, phatti, HengeWars) can be expressed as valid `ProjectFacets` instances. The Capacitor↔PWA conflict surfaces as a structured warning.

### Phase 4: Project Type Detector

**Goal:** Layer a detector on top of the existing `CodebaseScanner` so `br attach` reports facets and `br init` accepts `--type` flags.

**Files:**

- `core/project_type/detector.py` (NEW)
- `core/retrofit/codebase_scanner.py` (MODIFY — add `detect_facets()` hook)
- `cli/attach_commands.py` (MODIFY — call detector and surface facets)
- `cli/main.py` (MODIFY — accept `--type` flag on `br init`)
- `tests/core/project_type/test_detector.py` (NEW)

**Blocked by:** Phase 3 (imports `ProjectFacets`)

**Deliverables:**

- [ ] Implement detection rules with minimum-evidence thresholds: PWA = `vite-plugin-pwa` in deps AND `sw.ts` file; Capacitor = `capacitor.config.*` AND `@capacitor/core` in deps; Expo = `app.json` with `expo` key OR `eas.json` OR `metro.config.*`; Godot = `project.godot` at root; Next = `next.config.*`; Vite-React = `vite.config.*` AND React in deps; Supabase backend = a `supabase/functions` directory present in the target project OR `@supabase/supabase-js` in deps (this is a detection rule applied to other projects; BuildRunner3 itself has no supabase backend)
- [ ] Layer detector on `CodebaseScanner.detect_facets()` (extension, not replacement). The detector module imports from `core.project_type` only; `core.project_type.*` MUST NOT import anything from `core.retrofit` (no circular import). If shared scan utilities are needed, lift them to `core.utils` rather than crossing the package boundary.
- [ ] Add ambiguity prompt when detection returns conflicting or low-confidence signals
- [ ] Wire detector into `br attach` to print detected facets before installing
- [ ] Wire `--type` flag on `br init` (accepts shorthand like `react-vite-pwa-supabase`)
- [ ] Add `--scan` flag to `br attach` argument parser so the success-criterion command (`br attach --scan`) is implemented
- [ ] Tests asserting detector output for Synapse, trailsync, phatti, HengeWars fixtures

**Success Criteria:** Running `br attach --scan` against each reference project prints the correct `ProjectFacets`. `br init --type=godot` produces a Godot scaffold without prompting.

### Phase 5: BR3 Core Baseline Installer

**Goal:** Install the universal, framework-agnostic BR3 stack — no React, Vite, or Supabase assumptions. Every project gets this regardless of facets.

**Files:**

- `core/installer/__init__.py` (NEW)
- `core/installer/core_baseline.py` (NEW)
- `templates/core-baseline/agents.json` (NEW)
- `templates/core-baseline/skill-state.json` (NEW)
- `templates/core-baseline/behavior.yaml` (NEW)
- `templates/core-baseline/orchestration_state.json` (NEW)
- `templates/core-baseline/CLAUDE.md.universal` (NEW — universal ENFORCE blocks)
- `cli/attach_commands.py` (MODIFY — call core baseline installer)
- `cli/main.py` (MODIFY — same)
- `tests/core/installer/test_core_baseline.py` (NEW)

**Blocked by:** Phase 1 (asset resolver), Phase 2 (hook installer)

**Deliverables:**

- [ ] Implement `CoreBaselineInstaller` with idempotent file writers (skip-if-exists, parser-based for structured files)
- [ ] Author universal templates: `agents.json`, `skill-state.json`, `behavior.yaml`, `orchestration_state.json`
- [ ] Create empty workflow dirs: `plans/`, `codex-briefs/`, `fixit-briefs/`, `adversarial-reviews/`, `validation/`, `verification/`, `reviews/`, `prompts-golden/`, `mockups/`, `specs/`, `design/`, `decisions/`
- [ ] Write `bypass-justification.md` skeleton, log-rotation tooling stub
- [ ] Author `CLAUDE.md.universal` containing only stack-agnostic ENFORCE blocks
- [ ] Wire core-baseline call into `br attach` and `br init` flows
- [ ] Tests: install on empty dir, re-install no-ops, audit reports zero drift after install

**Success Criteria:** A fresh dir + `br init` produces all baseline files with correct content. Re-running `br attach --upgrade` does not modify any baseline file. Synapse audit shows existing baseline files match templates (or surface drift).

### Phase 6: Web Framework Adapters

**Goal:** Install framework-specific BR3 logger and entry-point integration for React/Vite, Next.js, and Expo.

**Files:**

- `core/installer/adapters/__init__.py` (NEW)
- `core/installer/adapters/react_vite.py` (NEW)
- `core/installer/adapters/next.py` (NEW)
- `core/installer/adapters/expo.py` (NEW)
- `core/installer/codemod.py` (NEW)
- `templates/adapters/react-vite/components/BRLogger.tsx` (NEW)
- `templates/adapters/react-vite/components/supabaseLogger.ts` (NEW)
- `templates/adapters/react-vite/components/brLoggerTransport.ts` (NEW)
- `templates/adapters/react-vite/components/vite-br-unified-plugin.ts` (NEW)
- `templates/adapters/react-vite/br-listen.mjs` (NEW)
- `templates/adapters/next/components/BRLoggerNext.tsx` (NEW)
- `templates/adapters/next/app/api/br-log/route.ts.template` (NEW — server-side `_debug[]` receiver)
- `templates/adapters/expo/components/BRLoggerNative.tsx` (NEW)
- `tests/core/installer/test_adapters.py` (NEW)

**Blocked by:** Phase 5 (core baseline must run first)

**Deliverables:**

- [ ] Implement `core/installer/codemod.py` using `ts-morph` via subprocess (or hand-rolled AST with parser-tree validator) for `vite.config.ts` and `src/main.tsx` patches; print exact manual instructions when confidence is low
- [ ] Implement `react_vite.py` adapter: drops logger stack, runs codemod, declares Vite-aware `package.json` script additions
- [ ] Implement `next.py` adapter: uses `app/layout.tsx` or `pages/_app.tsx` mount point; routes `_debug[]` through Next API routes if no Supabase. **Adapter MUST drop the receiver template `templates/adapters/next/app/api/br-log/route.ts.template` so the logging pipeline has a server-side endpoint** (otherwise emitted logs are silently dropped)
- [ ] Implement `expo.py` adapter: drops `BRLoggerNative.tsx`, Metro-aware capture, Expo dev-tools tie-in
- [ ] Each adapter is reentrant (re-running on an already-installed project is a no-op)
- [ ] Tests: install adapter on synthetic React/Vite project, Next project, Expo project; assert files dropped and codemods applied (or fallback printed)

**Success Criteria:** Running the adapter produces working logger pipelines (browser.log populated on first dev-server run) on synthetic fixtures. Running twice does not produce duplicate plugin registrations.

### Phase 7: Capability Modules

**Goal:** Opt-in modules that add specific facets independently of framework adapters.

**Files:**

- `core/installer/capabilities/__init__.py` (NEW)
- `core/installer/capabilities/pwa.py` (NEW)
- `core/installer/capabilities/capacitor.py` (NEW)
- `core/installer/capabilities/supabase_edge.py` (NEW)
- `core/installer/capabilities/dexie_offline.py` (NEW)
- `core/installer/capabilities/web_push_vapid.py` (NEW)
- `core/installer/capabilities/netlify.py` (NEW)
- `templates/capabilities/pwa/sw.ts.template` (NEW)
- `templates/capabilities/capacitor/capacitor.config.ts.template` (NEW)
- `templates/capabilities/capacitor/captures/` (NEW — `BRLoggerCapacitor.tsx`, `capacitorCapture.ts`)
- `templates/capabilities/supabase-edge/_shared/devLog.ts` (NEW)
- `templates/capabilities/dexie-offline/db.ts.template` (NEW)
- `templates/capabilities/web-push-vapid/PushDebug.tsx.template` (NEW)
- `templates/capabilities/netlify/netlify.toml.template` (NEW)
- `tests/core/installer/test_capabilities.py` (NEW)

**Blocked by:** Phase 6 (capabilities ride on adapter install)

**Deliverables:**

- [ ] Implement `pwa.py`: installs `vite-plugin-pwa` dep, drops `sw.ts` Workbox template with `injectManifest` strategy and HTML-exclusion globPattern, multi-tab `SKIP_WAITING` pattern
- [ ] Implement `capacitor.py`: installs `@capacitor/{core,cli,ios}`, drops `capacitor.config.ts`, drops `captures/capacitor/` files, swaps `BRLogger` mount → `BRLoggerCapacitor`. Hard-fails if `pwa` capability is also requested (with explicit "SW caching breaks native deploys" message)
- [ ] Implement `supabase_edge.py`: drops a `_shared/devLog.ts` file into the target project's `supabase/functions` tree (target-project path, not a path in BuildRunner3) with `withDevLogs` + `_debug[]` pattern; offers `device_logs` migration if `capacitor` capability is also installed
- [ ] Implement `dexie_offline.py`, `web_push_vapid.py`, `netlify.py` modules
- [ ] Each module reads detected facets and prompts y/n on opt-in capabilities; auto-applies on `--type=...` flag specifying them
- [ ] Tests: each capability installs on a synthetic project; capacitor↔pwa conflict raises the expected error

**Success Criteria:** Running `br attach` on trailsync detects `pwa` capability and offers it (skipping if already installed). Running on phatti installs `capacitor` and refuses to install `pwa` alongside it. supabase-edge `_debug[]` shows up in edge function responses.

### Phase 8: Godot Adapter with Pre-Wired Instrumentation

**Goal:** Godot 4 projects get logging parity through an autoload + pre-wired `GameState`/`EventBus`/`SaveManager` templates + run/test wrappers + parser-based `project.godot` patching.

**Files:**

- `core/installer/adapters/godot.py` (NEW)
- `core/installer/godot_project_patcher.py` (NEW)
- `templates/adapters/godot/scripts/autoloads/BRLogger.gd` (NEW)
- `templates/adapters/godot/scripts/autoloads/GameState.gd.template` (NEW — pre-wired with `BRLogger.info` calls)
- `templates/adapters/godot/scripts/autoloads/EventBus.gd.template` (NEW — `emit_logged()` helper)
- `templates/adapters/godot/scripts/autoloads/SaveManager.gd.template` (NEW — round-trip logging)
- `templates/adapters/godot/scripts/godot-run.sh` (NEW)
- `templates/adapters/godot/scripts/godot-test.sh` (NEW)
- `templates/adapters/godot/Makefile.snippet` (NEW)
- `templates/adapters/godot/CLAUDE.md.godot-addendum` (NEW — partial-coverage caveats)
- `tests/core/installer/test_godot_adapter.py` (NEW)

**Blocked by:** Phase 5 (core baseline) — file-disjoint from Phase 6 and 7 (independent adapter)

**Deliverables:**

- [ ] Implement `godot_project_patcher.py` using a real `project.godot` parser (configparser-style INI with section preservation), idempotent autoload registration
- [ ] Author `BRLogger.gd` with severity enum, ring buffer (last 500), file sinks at `user://logs/{brlogger,eventbus,engine}.log`, FPS/memory sampling timer, flush on `NOTIFICATION_WM_CLOSE_REQUEST`
- [ ] Author pre-instrumented `GameState.gd`, `EventBus.gd`, `SaveManager.gd` templates with `BRLogger.info`/`event` calls at key transitions
- [ ] Author `godot-run.sh` (tees stdout to `.buildrunner/godot.log`, copies `user://logs/` after exit, crash-trap on non-zero exit) and `godot-test.sh` (GUT headless run → `.buildrunner/gut.log`)
- [ ] Append Makefile snippet with `run-logged`, `test-logged`, `logs-clean` targets
- [ ] Document partial-coverage limit in `CLAUDE.md.godot-addendum` (editor-launched sessions, hard crashes before shutdown not captured)
- [ ] Add `henge` zsh alias registration via `_br_project henge /Users/byronhudson/Projects/HengeWars`. Installer MUST verify `_br_project` shell function is present in `~/.zshrc` first; abort with a clear error if missing instead of writing a broken alias. Use a comment-fenced block (`# >>> br3-aliases >>>` … `# <<< br3-aliases <<<`) and `grep -q` before append for idempotency on repeated `br attach --upgrade` runs
- [ ] Tests: install adapter on a clean Godot project fixture; assert `project.godot` autoloads section is correct; run `make run-logged` and assert `.buildrunner/godot.log` is populated

**Success Criteria:** HengeWars after `br attach --upgrade --type=godot` has working autoloads, `make run-logged` produces a populated log, `make test-logged` runs the (currently empty) GUT suite and writes `gut.log`. The Godot project parser preserves all existing sections.

### Phase 9: Drift Audit and Migration

**Goal:** Non-destructive drift detector and upgrade path; migrate Synapse, trailsync, phatti, BuildRunner3, HengeWars to the new baseline.

**Files:**

- `cli/audit_commands.py` (NEW — `br audit`)
- `cli/upgrade_commands.py` (MODIFY — extend Phase 1 stub with `br attach --upgrade`)
- `core/installer/drift_detector.py` (NEW)
- `tests/cli/test_audit.py` (NEW)
- `~/.zshrc` (MODIFY — add `henge` alias via `_br_project`)

**Blocked by:** Phases 5–8 (needs baseline + adapters + capabilities + Godot to compare against)

**Deliverables:**

- [ ] Implement `core/installer/drift_detector.py`: read `ProjectFacets`, compare against baseline + adapter + capability templates, return structured drift report (missing files, modified files, missing entries in structured configs)
- [ ] Implement `br audit` command: print drift report, exit non-zero if drift found
- [ ] Implement `br attach --upgrade`: **first call `br upgrade`** (Phase 1) to refresh `~/.buildrunner/templates/` from the wheel, then run audit, prompt y/n per drift item, apply fixes idempotently. This chains the two upgrade paths so project-level fixes never compare against stale templates.
- [ ] Migrate Synapse (audit + backfill `behavior.yaml` if missing + verify hooks)
- [ ] Migrate trailsync (add `vite-health.log` generator if requested, otherwise verify and document parity)
- [ ] Migrate phatti (backfill `ARCHITECTURE.md`, `DEPLOYMENT.md`, `PROJECT_SPEC.md`, `ROADMAP.md`, `VISION.md`, `behavior.yaml`)
- [ ] Migrate BuildRunner3 self-audit
- [ ] Migrate HengeWars (full Godot adapter install) and add `henge` zsh alias
- [ ] Tests: audit detects drift on a deliberately-broken fixture; upgrade fixes it

**Success Criteria:** `br audit` on each migrated project returns clean. `henge` alias works. `make run-logged` in HengeWars produces logs. CLAUDE.md addendum is present in HengeWars.

## Out of Scope (this BUILD)

- Research-library prompt-template optimization (defer; no concrete rollout failure caused by prompt wording).
- Tauri and Electron capability modules (skeletons only — full implementation deferred).
- Vue and Svelte framework adapters (out of v1; structure must allow them later).
- Live symlinking of project assets (Codex flagged: brittle across CI, archives, machines — copy-only).
- Automatic `henge45`/`henge46` model variants beyond the standard `_br_project` macro output.
- Replacing the existing `cli/doctor_commands.py` host-health checker shipped inside the pipx-installed `buildrunner` package (`~/.local/pipx/venvs/buildrunner/lib/python3.14/site-packages/cli/doctor_commands.py`). Note: this file lives in the installed package, not the repo's source tree — Phase 9 must not introduce a repo-level `cli/doctor_commands.py` that would clobber it on `pip install -e .`.

## Parallelization Matrix

| Phase | Key Files                                                                                                 | Can Parallel With | Blocked By                                          |
| ----- | --------------------------------------------------------------------------------------------------------- | ----------------- | --------------------------------------------------- |
| 1     | pyproject.toml, cli/main.py, cli/attach_commands.py, core/asset_resolver.py                               | —                 | —                                                   |
| 2     | .buildrunner/scripts/activate-all-systems.sh, .buildrunner/hooks/, core/installer/hook_installer.py       | 3                 | —                                                   |
| 3     | core/project_type/{facets,composition}.py                                                                 | 2                 | —                                                   |
| 4     | core/project_type/detector.py, core/retrofit/codebase_scanner.py, cli/main.py, cli/attach_commands.py     | —                 | 3 (imports facets); same files as 1 → must follow 1 |
| 5     | core/installer/core_baseline.py, templates/core-baseline/, cli/main.py, cli/attach_commands.py            | —                 | 1, 2; same CLI files as 1 and 4                     |
| 6     | core/installer/adapters/{react_vite,next,expo}.py, codemod.py, templates/adapters/{react-vite,next,expo}/ | 7, 8              | 5                                                   |
| 7     | core/installer/capabilities/, templates/capabilities/                                                     | 6, 8              | 5                                                   |
| 8     | core/installer/adapters/godot.py, godot_project_patcher.py, templates/adapters/godot/                     | 6, 7              | 5                                                   |
| 9     | cli/audit_commands.py, cli/upgrade_commands.py, core/installer/drift_detector.py                          | —                 | 5–8                                                 |

**Parallelizable groups:**

- Group A (after Phase 1): Phase 2 ‖ Phase 3 (file-disjoint)
- Group B (after Phase 5): Phase 6 ‖ Phase 7 ‖ Phase 8 (each touches its own subdirectory)

## Total Phases

9 phases. Phase 9 is the migration capstone.
