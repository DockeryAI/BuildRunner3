---
name: restart
description: "[Quick] Kill port 3000 and restart npm dev server"
allowed-tools: Bash
model: haiku
---

# R - Quick Server Restart

Fast dev server restart - no frills.

```bash
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
npm run dev
```
