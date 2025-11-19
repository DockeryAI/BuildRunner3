import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/');

    // Should show login form
    await expect(page.locator('h1')).toContainText('BuildRunner');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/');

    // Fill in login form
    await page.fill('input[type="email"]', 'admin@buildrunner.local');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/');

    // Fill in invalid credentials
    await page.fill('input[type="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('.error')).toContainText('Invalid');
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.goto('/');
    await page.fill('input[type="email"]', 'admin@buildrunner.local');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button[type="submit"]');

    // Wait for dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Click logout button
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login
    await expect(page).toHaveURL('/');
  });
});
