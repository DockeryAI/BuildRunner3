import { test, expect } from './fixtures';

test.describe('Dashboard', () => {
  test('should display dashboard components', async ({ dashboardPage }) => {
    await dashboardPage.expectComponentsVisible();
  });

  test('should show task list', async ({ dashboardPage }) => {
    await expect(dashboardPage.taskList).toBeVisible();
    await dashboardPage.expectTaskListHeaders();
  });

  test('should display agent pool', async ({ dashboardPage }) => {
    await expect(dashboardPage.agentPool).toBeVisible();
    const count = await dashboardPage.getAgentCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should show telemetry timeline', async ({ dashboardPage }) => {
    await expect(dashboardPage.telemetryTimeline).toBeVisible();
    const count = await dashboardPage.getTimelineEntryCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should navigate to analytics', async ({ dashboardPage }) => {
    await dashboardPage.navigateToAnalytics();
    await expect(dashboardPage.page.getByRole('heading', { level: 1 })).toContainText('Analytics');
  });
});
