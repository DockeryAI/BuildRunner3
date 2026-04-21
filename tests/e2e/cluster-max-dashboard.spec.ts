/**
 * cluster-max-dashboard.spec.ts — Phase 11/13 smoke for the Cluster Max dashboard.
 *
 * Targets the standalone dashboard served on Jimmy :4400 (NOT the main BR3 UI on :5173).
 * When :4400 is offline, the test is skipped (not failed) so the broader
 * test:e2e:ui suite remains green in environments without the cluster running.
 */

import { test, expect } from '@playwright/test';

const DASHBOARD_URL = process.env.CLUSTER_MAX_DASHBOARD_URL || 'http://10.0.1.106:4400';

test.describe('@ui Cluster Max Dashboard', () => {
  test.beforeAll(async () => {
    try {
      const res = await fetch(DASHBOARD_URL, { method: 'GET', signal: AbortSignal.timeout(3000) });
      if (!res.ok) test.skip(true, `dashboard at ${DASHBOARD_URL} returned ${res.status}`);
    } catch (e) {
      test.skip(true, `dashboard at ${DASHBOARD_URL} unreachable: ${String(e)}`);
    }
  });

  test('renders title and 4 panels', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await expect(page).toHaveTitle(/Cluster Max/i);

    for (const panel of ['node-health', 'overflow-reserve', 'storage-health', 'consensus']) {
      await expect(page.locator(`[data-panel="${panel}"]`)).toBeVisible();
    }
  });

  test('WebSocket state indicator is present', async ({ page }) => {
    await page.goto(DASHBOARD_URL);
    await expect(page.locator('#ws-state')).toBeVisible();
  });
});
