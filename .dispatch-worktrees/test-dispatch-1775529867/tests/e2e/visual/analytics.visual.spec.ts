import { test, expect } from '@playwright/test';
import path from 'path';

const SCREENSHOT_CSS = path.join(__dirname, 'screenshot.css');

test.describe('@visual Analytics Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/analytics');
    await page.waitForLoadState('networkidle');
    await page.addStyleTag({ path: SCREENSHOT_CSS });
    // Allow charts to finish rendering
    await page.waitForTimeout(1000);
  });

  test('analytics full page', async ({ page }) => {
    await expect(page).toHaveScreenshot('analytics-full.png', {
      fullPage: true,
      mask: [
        page.locator('[data-testid="timestamp"]'),
        page.locator('[data-testid="live-counter"]'),
        page.locator('[data-testid="date-display"]'),
        page.locator('time'),
      ],
    });
  });

  test('analytics performance chart', async ({ page }) => {
    const chart = page.locator('[data-testid="performance-chart"]');
    if (await chart.isVisible()) {
      await expect(chart).toHaveScreenshot('analytics-performance-chart.png', {
        mask: [
          chart.locator('[data-testid="timestamp"]'),
          chart.locator('[data-testid="live-value"]'),
        ],
      });
    }
  });

  test('analytics cost breakdown', async ({ page }) => {
    const costBreakdown = page.locator('[data-testid="cost-breakdown"]');
    if (await costBreakdown.isVisible()) {
      await expect(costBreakdown).toHaveScreenshot('analytics-cost-breakdown.png', {
        mask: [
          costBreakdown.locator('[data-testid="cost-value"]'),
          costBreakdown.locator('[data-testid="timestamp"]'),
        ],
      });
    }
  });

  test('analytics trend analysis', async ({ page }) => {
    const trendAnalysis = page.locator('[data-testid="trend-analysis"]');
    if (await trendAnalysis.isVisible()) {
      await expect(trendAnalysis).toHaveScreenshot('analytics-trend-analysis.png', {
        mask: [
          trendAnalysis.locator('[data-testid="trend-value"]'),
          trendAnalysis.locator('[data-testid="timestamp"]'),
          trendAnalysis.locator('time'),
        ],
      });
    }
  });
});
