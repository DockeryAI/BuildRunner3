# Phase 4 Plan: Dashboard — Intelligence Tab

## Tasks

### Task 4.1: TypeScript interfaces in types/index.ts
Add IntelItem, IntelAlerts, IntelImprovement interfaces.

### Task 4.2: Intel API methods in api.ts
Add intelAPI object with: getIntelItems(filters), getIntelAlerts(), dismissIntelItem(id), markIntelRead(id), getIntelImprovements(). Uses separate axios instance for Lockwood.

### Task 4.3: IntelligenceTab component
Priority-sorted feed with critical pinned (red border), high (amber), medium/low scrollable. Each item shows priority dot, title, summary, source badge, category badge, timestamp. Click to expand: opus synthesis, raw content, source link. Filter bar: source_type, category, priority, time range. Auto-refresh 30s items, 15s alerts.

### Task 4.4: IntelligenceTab.css
Styling following Dashboard.css patterns. Priority border colors, badges, filter bar, expandable cards with generous padding.

### Task 4.5: Dashboard.tsx modifications
Add 4th "Intelligence" tab with alert badge (red circle + unread count). Import IntelligenceTab.

### Task 4.6: BR3 Improvement items
Green "Build This" badge, expandable /setlist prompt, complexity badge, "Copy Command" button. Improvement counter in tab header.

## Tests
- IntelligenceTab renders with mock data
- Filter changes update displayed items
- Alert badge shows correct count
- Dismiss/read actions call API
