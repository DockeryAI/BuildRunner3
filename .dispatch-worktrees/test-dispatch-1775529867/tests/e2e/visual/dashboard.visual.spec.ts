import { test, expect } from '@playwright/test';
import path from 'path';

const SCREENSHOT_CSS = path.join(__dirname, 'screenshot.css');

test.describe('@visual Dashboard Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await page.addStyleTag({ path: SCREENSHOT_CSS });
    // Allow layout to settle after style injection
    await page.waitForTimeout(500);
  });

  test('dashboard full page', async ({ page }) => {
    // Mask dynamic content: timestamps, counters, agent status indicators
    await expect(page).toHaveScreenshot('dashboard-full.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="timestamp"]'),
        page.locator('[data-testid="agent-status"]'),
        page.locator('[data-testid="live-counter"]'),
        page.locator('time'),
      ],
    });
  });

  test('dashboard task list panel', async ({ page }) => {
    const taskList = page.locator('[data-testid="task-list"]');
    if (await taskList.isVisible()) {
      await expect(taskList).toHaveScreenshot('dashboard-task-list.png', {
        mask: [taskList.locator('[data-testid="timestamp"]'), taskList.locator('time')],
      });
    }
  });

  test('dashboard agent pool panel', async ({ page }) => {
    const agentPool = page.locator('[data-testid="agent-pool"]');
    if (await agentPool.isVisible()) {
      await expect(agentPool).toHaveScreenshot('dashboard-agent-pool.png', {
        mask: [
          agentPool.locator('[data-testid="agent-status"]'),
          agentPool.locator('[data-testid="uptime"]'),
        ],
      });
    }
  });

  test('dashboard telemetry timeline', async ({ page }) => {
    const timeline = page.locator('[data-testid="telemetry-timeline"]');
    if (await timeline.isVisible()) {
      await expect(timeline).toHaveScreenshot('dashboard-telemetry.png', {
        mask: [
          timeline.locator('[data-testid="timestamp"]'),
          timeline.locator('time'),
          timeline.locator('[data-testid="live-counter"]'),
        ],
      });
    }
  });
});
