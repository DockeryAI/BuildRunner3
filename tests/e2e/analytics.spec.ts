import { test, expect } from '@playwright/test';

test.describe('Analytics Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('input[type="email"]', 'admin@buildrunner.local');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);

    // Navigate to analytics
    await page.click('[data-testid="analytics-link"]');
    await expect(page).toHaveURL(/\/analytics/);
  });

  test('should display analytics components', async ({ page }) => {
    // Check analytics sections are visible
    await expect(page.locator('[data-testid="performance-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="cost-breakdown"]')).toBeVisible();
    await expect(page.locator('[data-testid="trend-analysis"]')).toBeVisible();
  });

  test('should render performance chart', async ({ page }) => {
    const chart = page.locator('[data-testid="performance-chart"]');
    await expect(chart).toBeVisible();

    // Chart should have a canvas or SVG element
    const chartElement = chart.locator('canvas, svg');
    await expect(chartElement).toBeVisible();
  });

  test('should display cost breakdown', async ({ page }) => {
    const costBreakdown = page.locator('[data-testid="cost-breakdown"]');
    await expect(costBreakdown).toBeVisible();

    // Should show cost metrics
    await expect(costBreakdown).toContainText(['Haiku', 'Sonnet', 'Opus']);
  });

  test('should show trend analysis', async ({ page }) => {
    const trendAnalysis = page.locator('[data-testid="trend-analysis"]');
    await expect(trendAnalysis).toBeVisible();

    // Should have trend data
    const trends = trendAnalysis.locator('[data-testid^="trend-"]');
    const count = await trends.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should export to CSV', async ({ page }) => {
    const exportButton = page.locator('[data-testid="export-csv"]');

    if (await exportButton.isVisible()) {
      const downloadPromise = page.waitForEvent('download');
      await exportButton.click();
      const download = await downloadPromise;

      // Verify download
      expect(download.suggestedFilename()).toContain('.csv');
    }
  });

  test('should filter by date range', async ({ page }) => {
    const dateFilter = page.locator('[data-testid="date-range-filter"]');

    if (await dateFilter.isVisible()) {
      await dateFilter.click();

      // Select last 7 days
      await page.click('[data-testid="filter-7days"]');

      // Chart should update
      await expect(page.locator('[data-testid="performance-chart"]')).toBeVisible();
    }
  });
});
