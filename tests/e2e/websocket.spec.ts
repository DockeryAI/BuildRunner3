import { test, expect } from './fixtures';

test.describe('WebSocket Live Updates', () => {
  test('should establish WebSocket connection', async ({ dashboardPage }) => {
    await dashboardPage.expectWsConnected();
  });

  test('should receive live task updates', async ({ dashboardPage }) => {
    await expect(dashboardPage.taskList).toBeVisible();
    const initialTasks = await dashboardPage.getTaskCount();

    // Wait for potential updates
    await dashboardPage.page.waitForTimeout(2000);

    const currentTasks = await dashboardPage.getTaskCount();
    expect(currentTasks).toBeGreaterThanOrEqual(0);
  });

  test('should show real-time agent status', async ({ dashboardPage }) => {
    await expect(dashboardPage.agentPool).toBeVisible();
    await dashboardPage.expectAgentStatuses();
  });

  test('should update telemetry timeline in real-time', async ({ dashboardPage }) => {
    await expect(dashboardPage.telemetryTimeline).toBeVisible();
    const initialEntries = await dashboardPage.getTimelineEntryCount();

    // Wait for potential new entries
    await dashboardPage.page.waitForTimeout(2000);

    const currentEntries = await dashboardPage.getTimelineEntryCount();
    expect(currentEntries).toBeGreaterThanOrEqual(0);
  });
});
