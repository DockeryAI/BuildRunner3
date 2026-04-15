import { test, expect } from './fixtures';
import { LoginPage } from './pages/LoginPage';

test.describe('@ui Authentication', () => {
  test('should display login page', async ({ page }) => {
    const loginPage = new LoginPage(page);
    // Use a fresh context without storageState for login page tests
    await page.context().clearCookies();
    await loginPage.goto();

    await loginPage.expectHeadingVisible();
    await loginPage.expectLoginFormVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await page.context().clearCookies();
    await loginPage.goto();

    await loginPage.loginAsAdmin();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Dashboard');
  });

  test('should show error with invalid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await page.context().clearCookies();
    await loginPage.goto();

    await loginPage.login('wrong@example.com', 'wrongpassword');

    await loginPage.expectError('Invalid');
  });

  test('should logout successfully', async ({ page }) => {
    // Already authenticated via storageState — navigate to dashboard
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);

    // Click logout
    await page.getByTestId('logout-button').click();

    // Should redirect to login
    await expect(page).toHaveURL('/');
  });
});
