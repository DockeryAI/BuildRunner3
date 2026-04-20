import { test } from '@playwright/test';

test('@ui capture intel workspace', async ({ page }) => {
  await page.goto('http://localhost:4400');
  await page.waitForTimeout(1500);

  // Click Intel icon in sidebar
  await page.click('[data-ws="intel"]');
  await page.waitForTimeout(2500);

  await page.screenshot({ path: '/tmp/intel-workspace.png', fullPage: true });
});
