# Build: SupaLog — Supabase Operation Logger

**Created:** 2026-02-26
**Status:** Phase 1 ✅ COMPLETE

## Overview
Instrumented Supabase client that logs all operations (queries, auth, storage, realtime, edge functions) to `.buildrunner/supabase.log` for Claude-accessible debugging. Zero overhead — custom fetch wrapper pattern, dev-only.

## Parallelization Matrix

| Phase | Key Files | Can Parallel With | Blocked By |
|-------|-----------|-------------------|------------|
| 1 | `supabase.ts`, `supabaseLogger.ts`, `package.json` | — | — |
| 2 | `supabaseLogger.ts`, `vite.config.ts`, `sdb.md` | — | Phase 1 (shared files) |
| 3 | `__tests__/*` (NEW) | Phase 2 (different files) | Phase 1 |

## Phases

### Phase 1: Instrumented Supabase Client
**Status:** ✅ COMPLETE
**Goal:** Supabase client exists with full request/response logging to `.buildrunner/supabase.log`
**Files:**
  - `ui/src/lib/supabase.ts` (NEW) — client factory with instrumented fetch
  - `ui/src/lib/supabaseLogger.ts` (NEW) — log formatter, file writer, rotation logic
  - `.buildrunner/supabase.log` (NEW) — output log file
  - `ui/package.json` (MODIFY) — add `@supabase/supabase-js`
**Blocked by:** None
**Deliverables:**
- [x] Install `@supabase/supabase-js`
- [x] Create instrumented client factory with custom `global.fetch` wrapper
- [x] Log format: `[timestamp] [OP_TYPE] [method] [endpoint] [status] [duration_ms] [response_size]`
- [x] Capture all HTTP operations (queries, RPC, auth, storage, edge functions)
- [x] Add auth state change listener — log all auth events
- [x] Add realtime logger callback — log WebSocket events
- [x] Smart warnings: flag empty 200s (potential RLS denial), 4xx/5xx, token refresh failures

**Success Criteria:** Every Supabase operation produces a log line in `.buildrunner/supabase.log`

---

### Phase 2: Log Management + Dev Integration
**Status:** in_progress
**Goal:** Logs rotate automatically, stripped in prod, and accessible via `/sdb` command
**Files:**
  - `ui/src/lib/supabaseLogger.ts` (MODIFY) — add rotation/truncation
  - `ui/vite.config.ts` (MODIFY) — dev-only conditional
  - `~/.claude/commands/sdb.md` (NEW) — Supabase debug skill
  - `CLAUDE.md` (MODIFY) — add to protected files list
**Blocked by:** Phase 1 (modifies same files)
**Deliverables:**
- [ ] Log rotation at 500KB (truncate oldest entries)
- [ ] Dev-only gate — no logging in production builds
- [ ] Create `/sdb` skill that reads and analyzes `.buildrunner/supabase.log`
- [ ] Add `supabase.log` and `supabaseLogger.ts` to CLAUDE.md protected files
- [ ] Update `/dbg` to also reference supabase.log when relevant

**Success Criteria:** Logs stay manageable, `/sdb` returns useful diagnostics, zero presence in prod bundle

---

### Phase 3: Validation + Edge Cases
**Status:** not_started
**Goal:** Logger handles all failure modes gracefully, confirmed zero overhead
**Files:**
  - `ui/src/lib/__tests__/supabaseLogger.test.ts` (NEW)
  - `ui/src/lib/__tests__/supabase.test.ts` (NEW)
**Blocked by:** Phase 1 (tests the client)
**After:** Phase 2
**Deliverables:**
- [ ] Test: all HTTP operations produce log entries
- [ ] Test: auth events logged correctly
- [ ] Test: realtime events logged correctly
- [ ] Test: RLS empty-result warning fires on 200 + empty data
- [ ] Test: log rotation works at threshold
- [ ] Confirm no measurable latency added (fetch wrapper timing)

**Success Criteria:** Full test coverage, confirmed no overhead

---

### Out of Scope (Future)
- Server-side pgAudit integration (adds real DB overhead)
- Log drain to external services (Datadog, Loki)
- Dashboard UI for viewing Supabase logs
- Supabase Management API integration for server-side logs
- Edge function internal logging (separate concern)

## Session Log
<!-- Updated by /begin -->
