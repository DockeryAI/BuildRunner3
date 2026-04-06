# BRLogger v3 — BR3 Canonical Source

**This is the single source of truth for all BR3 logging infrastructure.**
`activate-all-systems.sh` Phase 13 copies from HERE to every project.

## Components

| File                          | What It Captures                                                                       | Output                          |
| ----------------------------- | -------------------------------------------------------------------------------------- | ------------------------------- |
| `BRLogger.tsx`                | Console, fetch (URL+status+duration), errors, auth state                               | `browser.log`                   |
| `supabaseLogger.ts`           | Supabase SDK ops (REST/Auth/Storage/Edge/Realtime), RLS denials, `_debug[]` extraction | `supabase.log`                  |
| `vite-br-logger-plugin.ts`    | Receives browser logs (dev POST + prod Realtime)                                       | `browser.log`                   |
| `vite-supabase-log-plugin.ts` | Receives Supabase op logs from client                                                  | `supabase.log`                  |
| `devLog.ts`                   | Edge function server-side console.log → injects `_debug[]` into JSON response          | `supabase.log` (via extraction) |
| `br-listen.mjs`               | Remote device logs from `br_device_logs` table                                         | All 4 log files                 |

## Data Flow

```
Browser Console/Fetch/Errors
  → BRLogger.tsx (module-level interception)
  → POST /__br_logger (dev) OR Supabase Realtime (prod)
  → vite-br-logger-plugin.ts
  → .buildrunner/browser.log

Supabase SDK Operations
  → supabaseLogger.ts (instrumented fetch wrapper)
  → POST /__supabase_log (dev)
  → vite-supabase-log-plugin.ts
  → .buildrunner/supabase.log

Edge Function Server-Side Logs
  → devLog.ts wraps handler with withDevLogs()
  → console.log captured → injected as _debug[] in JSON response
  → supabaseLogger.ts extracts _debug[] on client
  → .buildrunner/supabase.log

Remote Device Logs (Mobile/PWA)
  → App writes to br_device_logs Supabase table
  → br-listen.mjs subscribes to INSERT events
  → Routes by log_type to browser.log / supabase.log / device.log / query.log
```

## Integration (handled by activate-all-systems.sh Phase 13)

1. BRLogger.tsx → FIRST import in `src/main.tsx`
2. `<BRLogger />` rendered in React tree
3. vite-br-logger-plugin + vite-supabase-log-plugin registered in `vite.config.ts`
4. supabaseLogger `createInstrumentedFetch` wraps Supabase client in `src/lib/supabase.ts`
5. Edge functions wrapped with `withDevLogs()` from `_shared/devLog.ts`

## READONLY — modify here, propagate via activate-all-systems.sh
