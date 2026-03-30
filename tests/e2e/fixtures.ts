import { test as base, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

type Fixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  analyticsPage: AnalyticsPage;
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  dashboardPage: async ({ page }, use) => {
    const dashboardPage = new DashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.expectLoaded();
    await use(dashboardPage);
  },

  analyticsPage: async ({ page }, use) => {
    const analyticsPage = new AnalyticsPage(page);
    await analyticsPage.goto();
    await analyticsPage.expectLoaded();
    await use(analyticsPage);
  },
});

export { expect };
