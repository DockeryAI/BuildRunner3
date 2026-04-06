# Phase 7 Plan: Inline Log Actions + One-Click Rollback

## Tasks

1. **events.mjs: Add `/api/projects/:name/rollback` endpoint** — SSHs to Lomax, deploys previous successful build artifact.
2. **events.mjs: Add `/api/projects/:name/restart` endpoint** — Restarts dev server or service for a given project.
3. **index.html: Restart button in Prod Logs panel header** — Inline action button with toast feedback.
4. **index.html: Rollback button per build in builds table** — Per-row action with confirmation dialog.
5. **index.html: Confirmation dialog + toast notifications** — Reuse existing modal/toast patterns.

## Tests
Non-testable (HTML/mjs dashboard, no vitest). Skip TDD.
