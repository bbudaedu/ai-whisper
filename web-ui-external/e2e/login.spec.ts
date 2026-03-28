import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  // Test 1: 未登入狀態訪問 / 應重導向至 /login
  test('should redirect unauthenticated users to /login', async ({ page }) => {
    // Force unauthenticated state
    await page.context().clearCookies();
    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  // Test 2: 輸入無效憑證應顯示錯誤訊息
  test('should show error message for invalid credentials', async ({ page }) => {
    // Clear any previous auth state
    await page.context().clearCookies();
    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    // Mock failed login
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: '登入失敗，請檢查電子郵件與密碼。' })
      });
    });

    await page.goto('/login');
    await page.getByTestId('login-email').fill('wrong@example.com');
    await page.getByTestId('login-password').fill('wrongpassword');
    await page.getByTestId('login-submit').click();

    // Check for error message
    await expect(page.locator('div.bg-red-50 p')).toBeVisible();
    // Accept either server error or the specific detail message
    await expect(page.locator('div.bg-red-50 p')).toContainText(/登入失敗|401/);
  });

  // Test 3: 登入成功後應跳轉至首頁，且導覽列顯示使用者 Email
  test('should login successfully and show user email in navigation', async ({ page, isMobile }) => {
    // Clear any previous auth state
    await page.context().clearCookies();
    await page.addInitScript(() => {
      window.localStorage.clear();
    });

    // Mock successful login
    await page.route('**/api/auth/login', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake-access-token',
          refresh_token: 'fake-refresh-token'
        })
      });
    });

    // Mock history to avoid dashboard loading issues
    await page.route('**/api/tasks/history', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.goto('/login');
    await page.getByTestId('login-email').fill('test@example.com');
    await page.getByTestId('login-password').fill('password123');

    await page.getByTestId('login-submit').click();

    if (isMobile) {
      // Mobile uses bottom nav.
      // We look for a visible nav item.
      await expect(page.locator('nav').getByTestId('nav-dashboard')).toBeVisible({ timeout: 10000 });
    } else {
      // Desktop uses sidebar with logout button
      await expect(page.getByTestId('nav-logout').first()).toBeVisible({ timeout: 10000 });
    }

    // Check navigation for user email (only on desktop usually)
    if (!isMobile) {
      await expect(page.locator('p.truncate', { hasText: 'test@example.com' }).first()).toBeVisible();
    }
  });
});
