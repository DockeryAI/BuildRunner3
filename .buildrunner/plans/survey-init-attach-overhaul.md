# Prior-State Survey — init-attach-overhaul

## Prior BUILDs

- `BUILD_br3-cleanup-wave-abc.md` — touched `core/`. Status unknown; check before modifying. No file overlap declared with this plan; risk: low if completed phases haven't introduced stale resolver assumptions.
- `BUILD_cluster-activation.md`, `BUILD_cluster-build-orchestration.md`, `BUILD_cluster-hardening-v1.md` — touched `.buildrunner/scripts/` and `~/.buildrunner/scripts/`. Phase 1's `activate-all-systems.sh` rename and Phase 2's `hook_installer.py` are downstream of these. Confirm these completed builds did not pin the old hook names elsewhere.
- `BUILD_burnin-harness-reliability.md` (active per SessionStart brief, all 6 phases complete) — touched `core/cluster/` and `core/cluster/cross_model_review.py`. No direct overlap with `cli/` or `core/installer/` paths in this plan.
- No prior BUILDs found with `init`, `attach`, `installer`, `template`, `adapter`, or `detector` in the name. Clean namespace for this build.

## Shared-Surface Impact

- **`cli/main.py` and `cli/attach_commands.py`** — touched by Phase 1, Phase 4, and Phase 5 in this plan. Internal serialization required (already encoded in Parallelization Matrix). External callers: `br` entry-point script in `pyproject.toml` `[project.scripts]`. Verify `br --version` and existing flags (`--scan`, `--register`, `--register-all`) still work after each phase.
- **`pyproject.toml`** — touched by Phase 1 only. External impact: pipx install behavior, package-data globs. Backward compat: existing `pipx install` users will need `pipx reinstall buildrunner` after the package-data change to pick up `.buildrunner/**` assets.
- **`core/retrofit/codebase_scanner.py`** — touched by Phase 4 (MODIFY: add `detect_facets()` hook). Other callers: `cli/attach_commands.py` (existing full-scan flow). Risk: moderate — must preserve existing `scan()` return shape; add new method without breaking.
- **`.buildrunner/scripts/activate-all-systems.sh`** — touched by Phase 2. Called from `br init` and `br attach`. Risk: rename of hook references must be matched everywhere or hook installer breaks silently.
- **`.buildrunner/hooks/pre-{commit,push}-enforced`** — touched by Phase 2 review only (no edits planned). Other consumers: BR3 `/ship` runner, `pre-push.d/` fragment chain.
- **`templates/`** — Phase 1 expands package-data; Phase 5–8 add new template subdirectories. No collision with existing template files.
- **`~/.zshrc`** — Phase 9 appends `henge` via `_br_project`. The `_br_project` macro is already in place; no merge conflict expected.

## Governance Drift

- **`.buildrunner/governance.yaml`** — repo's governance file is present. Plan does not modify governance rules; `br audit` (Phase 9) reports drift but does not auto-edit governance. No drift introduced.
- **`~/.buildrunner/config/default-role-matrix.yaml`** — required by `load-role-matrix.sh` for the role-matrix block in BUILD specs. Not modified by this plan.
- **CLAUDE.md global rule "Research Library — Jimmy only"** — Phase 9 of this plan defers research-library prompt optimization to out-of-scope, so no rule violation.
- **CLAUDE.md "UI Components — mandatory"** — none of the work in this plan introduces UI; all installer code is Python or template assets. No drift.

## Completed-Phase Blast Radius

- `BUILD_burnin-harness-reliability.md` Phases 1–6 complete and touched `core/cluster/cross_model_review.py`. This plan does NOT modify that file. No collision.
- `BUILD_cluster-activation.md` (status unknown) modified `.buildrunner/scripts/cluster-check.sh` historically. Phase 2 does not touch `cluster-check.sh`. No collision.
- No completed phase from any prior BUILD modifies `cli/main.py`, `cli/attach_commands.py`, `pyproject.toml`, `core/retrofit/codebase_scanner.py`, or `.buildrunner/scripts/activate-all-systems.sh` based on filename grep. Risk window is open for this plan to modify them safely.

## Summary

Two areas warrant active attention during execution: (1) `cli/main.py` and `cli/attach_commands.py` modified by three phases (1, 4, 5) — keep changes additive and backward-compatible; (2) `core/retrofit/codebase_scanner.py` extension in Phase 4 must preserve existing `scan()` return shape. No completed-phase blast radius collisions detected. Greenfield namespace for the new `core/installer/` and `core/project_type/` directories.
