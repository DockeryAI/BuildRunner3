# Phase 4: Test Infrastructure Upgrade — Plan

## Tasks

### Task 4.1: Create Page Object Models
- LoginPage.ts: email/password fields (getByRole), submit button, error message locator
- DashboardPage.ts: task list, agent pool, telemetry timeline, analytics link, logout button, ws-status
- AnalyticsPage.ts: performance chart, cost breakdown, trend analysis, export CSV, date range filter

### Task 4.2: Create shared fixtures (fixtures.ts)
- authenticatedPage: extends base test with storageState from auth setup
- dashboardPage: authenticated + navigated to /dashboard
- apiContext: request context with auth token

### Task 4.3: Create auth setup project (auth.setup.ts)
- Login once, save storageState to playwright/.auth/user.json
- Add playwright/.auth/ to .gitignore

### Task 4.4: Update playwright.config.ts
- Add 'setup' project that runs auth.setup.ts
- Add dependency on 'setup' for all browser projects
- Configure storageState path

### Task 4.5: Migrate all 5 spec files to POMs
- authentication.spec.ts: use LoginPage, remove CSS selectors
- dashboard.spec.ts: use DashboardPage, remove beforeEach login, use fixtures
- analytics.spec.ts: use AnalyticsPage + DashboardPage, remove beforeEach login
- websocket.spec.ts: use DashboardPage, remove beforeEach login
- api-health.spec.ts: use apiContext fixture for auth tests

## Tests
- All existing test assertions preserved after migration
- No CSS selectors remain in spec files
- Login via setup project, not per-test
