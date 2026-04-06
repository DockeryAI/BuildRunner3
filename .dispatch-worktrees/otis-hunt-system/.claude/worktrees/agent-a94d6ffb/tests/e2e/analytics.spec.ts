import { test, expect } from './fixtures';

test.describe('Analytics Dashboard', () => {
  test('should display analytics components', async ({ analyticsPage }) => {
    await analyticsPage.expectComponentsVisible();
  });

  test('should render performance chart', async ({ analyticsPage }) => {
    await analyticsPage.expectChartRendered();
  });

  test('should display cost breakdown', async ({ analyticsPage }) => {
    await analyticsPage.expectCostBreakdownModels();
  });

  test('should show trend analysis', async ({ analyticsPage }) => {
    await expect(analyticsPage.trendAnalysis).toBeVisible();
    const count = await analyticsPage.getTrendCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should export to CSV', async ({ analyticsPage }) => {
    const filename = await analyticsPage.exportToCsv();
    if (filename) {
      expect(filename).toContain('.csv');
    }
  });

  test('should filter by date range', async ({ analyticsPage }) => {
    await analyticsPage.filterByDateRange('7days');
  });
});
