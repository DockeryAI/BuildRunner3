import { test, expect } from '@playwright/test';
import path from 'path';

const SCREENSHOT_CSS = path.join(__dirname, 'screenshot.css');

test.describe('@visual Login Visual Regression', () => {
  test.beforeEach(async ({ page, context }) => {
    // Clear auth state to see the login page
    await context.clearCookies();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.addStyleTag({ path: SCREENSHOT_CSS });
    await page.waitForTimeout(500);
  });

  test('login page full view', async ({ page }) => {
    await expect(page).toHaveScreenshot('login-full.png', {
      fullPage: true,
    });
  });

  test('login form', async ({ page }) => {
    const form = page.locator('form');
    if (await form.isVisible()) {
      await expect(form).toHaveScreenshot('login-form.png');
    }
  });

  test('login error state', async ({ page }) => {
    // Trigger validation error
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    const passwordInput = page.locator('input[type="password"], input[name="password"]');
    const submitButton = page.locator('button[type="submit"]');

    if (await emailInput.isVisible()) {
      await emailInput.fill('invalid@test.com');
      await passwordInput.fill('wrongpassword');
      await submitButton.click();

      // Wait for error message to appear
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot('login-error.png', {
        fullPage: true,
      });
    }
  });
});
