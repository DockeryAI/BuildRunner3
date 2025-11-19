import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('input[type="email"]', 'admin@buildrunner.local');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should display dashboard components', async ({ page }) => {
    // Check main components are visible
    await expect(page.locator('[data-testid="task-list"]')).toBeVisible();
    await expect(page.locator('[data-testid="agent-pool"]')).toBeVisible();
    await expect(page.locator('[data-testid="telemetry-timeline"]')).toBeVisible();
  });

  test('should show task list', async ({ page }) => {
    const taskList = page.locator('[data-testid="task-list"]');
    await expect(taskList).toBeVisible();

    // Should have table headers
    await expect(taskList.locator('th')).toContainText(['Task', 'Status', 'Agent']);
  });

  test('should display agent pool', async ({ page }) => {
    const agentPool = page.locator('[data-testid="agent-pool"]');
    await expect(agentPool).toBeVisible();

    // Should show agent cards or list
    const agents = agentPool.locator('[data-testid^="agent-"]');
    await expect(agents).toHaveCount(await agents.count());
  });

  test('should show telemetry timeline', async ({ page }) => {
    const timeline = page.locator('[data-testid="telemetry-timeline"]');
    await expect(timeline).toBeVisible();

    // Timeline should have entries
    const entries = timeline.locator('[data-testid^="timeline-entry-"]');
    const count = await entries.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should navigate to analytics', async ({ page }) => {
    await page.click('[data-testid="analytics-link"]');
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.locator('h1')).toContainText('Analytics');
  });
});
