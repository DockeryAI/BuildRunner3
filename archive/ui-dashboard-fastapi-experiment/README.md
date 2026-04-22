This directory preserves the retired FastAPI dashboard experiment that originally carried the Phase 6 and Phase 11 cluster panels.

- Retirement date: `2026-04-22`
- Reason: the real operator dashboard runs from `~/.buildrunner/dashboard/` on `:4400`, and the standalone FastAPI surface drifted out of use while still retaining a collision-prone dashboard app export.
- Replacement paths:
  - `~/.buildrunner/dashboard/public/index.html`
  - `~/.buildrunner/dashboard/public/js/ws-cluster-feature-health.js`
  - `~/.buildrunner/dashboard/public/js/ws-cluster-node-health.js`
  - `~/.buildrunner/dashboard/public/js/ws-cluster-overflow-reserve.js`
  - `~/.buildrunner/dashboard/public/js/ws-cluster-storage-health.js`
  - `~/.buildrunner/dashboard/public/js/ws-cluster-consensus.js`
  - `~/.buildrunner/dashboard/events.mjs`

The archive is retained for historical reference only. Do not deploy or bind it on a live port.
