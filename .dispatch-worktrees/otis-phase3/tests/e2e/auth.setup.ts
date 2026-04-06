import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/');

  // Fill login form
  await page.getByRole('textbox', { name: /email/i }).fill('admin@buildrunner.local');
  await page.getByLabel(/password/i).fill('admin');
  await page.getByRole('button', { name: /sign in|log in|submit/i }).click();

  // Wait for redirect to dashboard
  await expect(page).toHaveURL(/\/dashboard/);

  // Save signed-in state
  await page.context().storageState({ path: authFile });
});
