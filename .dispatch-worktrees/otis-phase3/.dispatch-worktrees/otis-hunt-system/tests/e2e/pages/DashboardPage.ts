import { type Locator, type Page, expect } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly taskList: Locator;
  readonly agentPool: Locator;
  readonly telemetryTimeline: Locator;
  readonly analyticsLink: Locator;
  readonly logoutButton: Locator;
  readonly wsStatus: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1 });
    this.taskList = page.getByTestId('task-list');
    this.agentPool = page.getByTestId('agent-pool');
    this.telemetryTimeline = page.getByTestId('telemetry-timeline');
    this.analyticsLink = page.getByTestId('analytics-link');
    this.logoutButton = page.getByTestId('logout-button');
    this.wsStatus = page.getByTestId('ws-status');
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async expectLoaded() {
    await expect(this.page).toHaveURL(/\/dashboard/);
    await expect(this.heading).toContainText('Dashboard');
  }

  async expectComponentsVisible() {
    await expect(this.taskList).toBeVisible();
    await expect(this.agentPool).toBeVisible();
    await expect(this.telemetryTimeline).toBeVisible();
  }

  async expectTaskListHeaders() {
    await expect(this.taskList.locator('th')).toContainText(['Task', 'Status', 'Agent']);
  }

  async getAgentCount() {
    const agents = this.agentPool.getByTestId(/^agent-/);
    return agents.count();
  }

  async getTimelineEntryCount() {
    const entries = this.telemetryTimeline.getByTestId(/^timeline-entry-/);
    return entries.count();
  }

  async getTaskCount() {
    const tasks = this.taskList.getByTestId(/^task-/);
    return tasks.count();
  }

  async navigateToAnalytics() {
    await this.analyticsLink.click();
    await expect(this.page).toHaveURL(/\/analytics/);
  }

  async logout() {
    await this.logoutButton.click();
    await expect(this.page).toHaveURL('/');
  }

  async expectWsConnected() {
    if (await this.wsStatus.isVisible()) {
      await expect(this.wsStatus).toContainText(/Connected|Online/);
    }
  }

  async expectAgentStatuses() {
    const agents = this.agentPool.getByTestId(/^agent-/);
    const count = await agents.count();
    if (count > 0) {
      const firstAgent = agents.first();
      await expect(firstAgent).toContainText(/idle|busy|error|offline/);
    }
  }
}
