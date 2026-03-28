import { test as setup, expect } from '@playwright/test';

const authFile = '.auth/user.json';

setup('authenticate', async ({ page, isMobile }) => {
  // Mock the tasks history API to avoid hanging on networkidle
  await page.route('**/api/tasks/history', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });

  // Use addInitScript to pre-fill localStorage before any JS runs
  await page.addInitScript(() => {
    window.localStorage.setItem('auth_token', 'fake-access-token');
    window.localStorage.setItem('auth_user', JSON.stringify({ email: 'test@example.com', role: 'user' }));
  });

  // Go to root page - should NOT redirect to login because we set local storage
  await page.goto('/');

  if (isMobile) {
    // On mobile, check for a nav item in the bottom navigation.
    await expect(page.locator('nav').getByTestId('nav-dashboard')).toBeVisible({ timeout: 10000 });
  } else {
    // Verify we are logged in by checking the navigation is visible
    // Use first() because Desktop layout might have it in both desktop and mobile asides (though only one is visible)
    await expect(page.getByTestId('nav-logout').first()).toBeVisible({ timeout: 10000 });
  }

  // Save storage state to a file
  await page.context().storageState({ path: authFile });
});
