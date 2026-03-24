# Global Rules (All Projects)

## UI Components - MANDATORY

**ALWAYS use `~/Projects/ui-libraries/`:**

- shadcn - Buttons, Cards, Dialogs, Inputs, Forms
- aceternity - Animations, 3D effects, text animations
- magic-ui - Particles, gradients, visual effects
- catalyst-ui - Tables, complex forms
- radix-components - Accessible primitives

**NEVER install:** chakra-ui, mui, antd, nextui, mantine, headlessui, react-bootstrap, semantic-ui, primereact

## Frontend Design

When building UI:

1. Check ui-libraries for existing components first
2. Bold aesthetic choices - no generic "AI slop"
3. Dark theme default
4. Use `cn()` for class merging

## BR3 Universal Observability

All BR3 projects have automatic logging. **Check logs BEFORE asking the user for debug info.**

### CRITICAL: Debug in the Right Environment

**When debugging an issue, ALWAYS match the environment where the problem occurs:**

- If the user reports a **phone/PWA issue** → get logs from the phone, not desktop
- If the user reports a **prod issue** → get logs from prod, not localhost
- If logs are empty or stale → the BRLogger code may not be deployed to that environment yet

**Before debugging, verify:**

1. Are the `.buildrunner/*.log` files recent? (check timestamps)
2. Is the issue on prod? → BRLogger must be deployed. Use `npx netlify deploy --dir=dist --alias=br-debug` for preview, or deploy to prod.
3. Is the issue on a phone? → Phone must hit a URL with BRLogger code. Either deploy to prod with `?br_debug=1`, or point phone at dev server network URL.
4. Is the app a PWA? → Test AS a PWA (installed, standalone mode), not in a regular browser tab. SW behavior differs.

**Never test a phone/PWA issue on a desktop browser and call it done.**

### RULE: BRLogger Goes to Prod Immediately

BRLogger is zero-cost when inactive. There is NEVER a reason to leave it on a feature branch. When building or updating BRLogger for any project:

1. Commit directly to the working branch
2. Build and deploy to prod IMMEDIATELY
3. Never wait — the whole point is to debug prod issues, which requires the code to BE in prod
4. The activate script auto-commits and auto-deploys. If it fails, deploy manually before doing anything else.

### Log Files (in `.buildrunner/`)

| File           | Contents                                                                          |
| -------------- | --------------------------------------------------------------------------------- |
| `browser.log`  | Console, network requests, errors, navigation                                     |
| `supabase.log` | DB calls, auth, storage, edge functions, realtime channels                        |
| `device.log`   | Device info, app lifecycle, SW, visibility, memory, network, battery, performance |
| `query.log`    | React Query cache hit/miss/stale/fetch, invalidations, hydration, IndexedDB ops   |

### Debug Commands

- `/dbg` — analyze browser.log
- `/sdb` — analyze supabase.log
- `/device` — analyze device.log (SW, visibility, memory, network)
- `/query` — analyze query.log (cache efficiency, anti-patterns)
- `/diag` — cross-file correlation across all 4 logs

### Activating Prod Debug

- **Web/Capacitor:** Add `?br_debug=1` to URL (auto-expires 30 min). Logs flow via edge function → Realtime → dev machine.
- **React Native/Electron:** Set env `BR_DEBUG=1`
- **Deploy preview for testing:** `npm run build && npx netlify deploy --dir=dist --alias=br-debug`
- Dev server is also available on the network (check `--host` output for IP)

### Platform Captures

Auto-detected by project type. Covers: Web, React Native, Electron, Capacitor, Tauri, Flutter, Swift/iOS, Kotlin/Android, Node.js, Deno.
