import { type Locator, type Page, expect } from '@playwright/test';

export class AnalyticsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly performanceChart: Locator;
  readonly costBreakdown: Locator;
  readonly trendAnalysis: Locator;
  readonly exportCsvButton: Locator;
  readonly dateRangeFilter: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1 });
    this.performanceChart = page.getByTestId('performance-chart');
    this.costBreakdown = page.getByTestId('cost-breakdown');
    this.trendAnalysis = page.getByTestId('trend-analysis');
    this.exportCsvButton = page.getByTestId('export-csv');
    this.dateRangeFilter = page.getByTestId('date-range-filter');
  }

  async goto() {
    await this.page.goto('/analytics');
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/\/analytics/);
    await expect(this.heading).toContainText('Analytics');
  }

  async expectComponentsVisible() {
    await expect(this.performanceChart).toBeVisible();
    await expect(this.costBreakdown).toBeVisible();
    await expect(this.trendAnalysis).toBeVisible();
  }

  async expectChartRendered() {
    await expect(this.performanceChart).toBeVisible();
    const chartElement = this.performanceChart.locator('canvas, svg');
    await expect(chartElement).toBeVisible();
  }

  async expectCostBreakdownModels() {
    await expect(this.costBreakdown).toBeVisible();
    await expect(this.costBreakdown).toContainText(/Haiku/);
    await expect(this.costBreakdown).toContainText(/Sonnet/);
    await expect(this.costBreakdown).toContainText(/Opus/);
  }

  async getTrendCount() {
    const trends = this.trendAnalysis.getByTestId(/^trend-/);
    return trends.count();
  }

  async exportToCsv() {
    if (await this.exportCsvButton.isVisible()) {
      const downloadPromise = this.page.waitForEvent('download');
      await this.exportCsvButton.click();
      const download = await downloadPromise;
      return download.suggestedFilename();
    }
    return null;
  }

  async filterByDateRange(range: string) {
    if (await this.dateRangeFilter.isVisible()) {
      await this.dateRangeFilter.click();
      await this.page.getByTestId(`filter-${range}`).click();
      await expect(this.performanceChart).toBeVisible();
    }
  }
}
