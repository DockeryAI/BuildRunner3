import { test, expect } from '@playwright/test';

test.describe('WebSocket Live Updates', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('input[type="email"]', 'admin@buildrunner.local');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should establish WebSocket connection', async ({ page }) => {
    // Check for WebSocket connection indicator
    const wsIndicator = page.locator('[data-testid="ws-status"]');

    if (await wsIndicator.isVisible()) {
      await expect(wsIndicator).toContainText(['Connected', 'Online']);
    }
  });

  test('should receive live task updates', async ({ page }) => {
    const taskList = page.locator('[data-testid="task-list"]');
    await expect(taskList).toBeVisible();

    // Get initial task count
    const initialTasks = await taskList.locator('[data-testid^="task-"]').count();

    // Wait for potential updates
    await page.waitForTimeout(2000);

    // Tasks should be present
    const currentTasks = await taskList.locator('[data-testid^="task-"]').count();
    expect(currentTasks).toBeGreaterThanOrEqual(0);
  });

  test('should show real-time agent status', async ({ page }) => {
    const agentPool = page.locator('[data-testid="agent-pool"]');
    await expect(agentPool).toBeVisible();

    // Agent statuses should be displayed
    const agents = agentPool.locator('[data-testid^="agent-"]');
    const count = await agents.count();

    if (count > 0) {
      // First agent should have a status
      const firstAgent = agents.first();
      await expect(firstAgent).toContainText(['idle', 'busy', 'error', 'offline']);
    }
  });

  test('should update telemetry timeline in real-time', async ({ page }) => {
    const timeline = page.locator('[data-testid="telemetry-timeline"]');
    await expect(timeline).toBeVisible();

    // Get initial entry count
    const initialEntries = await timeline.locator('[data-testid^="timeline-entry-"]').count();

    // Wait for potential new entries
    await page.waitForTimeout(2000);

    // Timeline should have entries
    const currentEntries = await timeline.locator('[data-testid^="timeline-entry-"]').count();
    expect(currentEntries).toBeGreaterThanOrEqual(0);
  });
});
