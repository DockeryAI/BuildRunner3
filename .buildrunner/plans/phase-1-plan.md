# Phase 1 Implementation Plan
## Foundation — Role Matrix schema + context router extraction + :4500 mount

### Health Check Findings
1. `api/routes/context.py` already has NO module-level `app = create_app(...)` — it is only an APIRouter. The spec says to "remove module-level app" but it was never there in the current codebase. The file already has `router = APIRouter(prefix="/context", ...)`.
2. `core/cluster/node_semantic.py` (the actual node_semantic file) does not yet mount `context_router`.
3. No schemas directory exists yet.
4. No `api/services/` directory exists yet.
5. No `scripts/migrate-role-matrix.py` exists yet.

### Task List (9 tasks)

**T1** — Create `.buildrunner/schemas/role-matrix.schema.yaml` (NEW)
**T2** — Create `scripts/migrate-role-matrix.py` (NEW) — converts prose Role Matrix in BUILD_cluster-max.md to YAML block
**T3** — Append `role_matrix` YAML block to `.buildrunner/builds/BUILD_cluster-max.md`
**T4** — Verify `api/routes/context.py` has NO module-level app (already clean — add comment confirming)
**T5** — Create `api/services/context_api_standalone.py` with `if __name__ == "__main__"` guard
**T6** — Mount `context_router` in `core/cluster/node_semantic.py` (BUILD spec says `api/node_semantic.py`, actual file is `core/cluster/node_semantic.py`)
**T7** — Create `tests/cluster/test_role_matrix_schema.py` (NEW)
**T8** — Create `tests/cluster/test_context_router_no_side_effects.py` (NEW)
**T9** — Create `tests/integration/test_context_codex_live.py` (NEW)
**T10** — Update `core/cluster/AGENTS.md` with role_matrix schema documentation (≤500 byte staged-append)

### Critical Ordering
Per BUILD spec Risks #1: create context_api_standalone.py first, verify it boots concept, THEN confirm context.py is clean.
Since context.py already has no module-level app, risk is already mitigated.

### Notes
- `api/node_semantic.py` in the spec is actually `core/cluster/node_semantic.py` (verified)
- The port is :4500 per BUILD spec (Jimmy/node_semantic on port 4500)
- Smoke test: `curl http://10.0.1.106:4500/context/codex?phase=2` — Jimmy is at 10.0.1.106
