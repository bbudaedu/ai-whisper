import { test, expect } from '@playwright/test';

test.describe('Task Flow', () => {
  // Use the storage state from auth.setup.ts
  test.use({ storageState: '.auth/user.json' });

  test.beforeEach(async ({ page }) => {
    // Initial history mock
    await page.route('**/api/tasks/history', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Mock task submission API
    await page.route('**/api/tasks/', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({ id: 123, status: 'pending' })
        });
      } else {
        await route.continue();
      }
    });
  });

  test('should submit a YouTube task and track it', async ({ page, isMobile }) => {
    let historyCallCount = 0;

    // 1. Submit Task
    await page.goto('/submit');
    await page.getByTestId('mode-youtube').click();
    await page.getByTestId('input-youtube-url').fill('https://www.youtube.com/watch?v=dQw4w9WgXcQ');

    // Intercept history calls
    await page.route('**/api/tasks/history', async route => {
      if (historyCallCount === 0) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 123,
              url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
              status: 'pending',
              title: 'Never Gonna Give You Up',
              created_at: new Date().toISOString()
            }
          ])
        });
        // Only increment if it's the first time we serve the pending state
        // This is a bit fragile if multiple calls happen before we hit the 'refresh'
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 123,
              url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
              status: 'done',
              title: 'Never Gonna Give You Up',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            }
          ])
        });
      }
    });

    await page.getByTestId('btn-submit-task').click();
    await expect(page.getByTestId('success-alert')).toBeVisible();
    await expect(page.getByTestId('success-alert')).toContainText('任務提交成功');

    // 2. Track Task
    await page.goto('/track');
    await expect(page).toHaveURL(/\/track/);

    const taskItem = page.getByTestId('task-item-123');
    await expect(taskItem).toBeVisible({ timeout: 10000 });

    const statusCell = page.getByTestId('task-status-123').first();
    await expect(statusCell).toContainText('等待中', { timeout: 10000 });

    // NOW we are ready for the next state
    historyCallCount = 1;

    // 3. Status Update (Mocking transition to 'done')
    // Manually refresh to trigger status update
    await page.getByTestId('btn-refresh').click();

    // Wait for the status to change
    await expect(statusCell).toContainText('已完成', { timeout: 10000 });

    // Verify download button appears when expanded
    await taskItem.click();
    await expect(page.getByTestId('btn-download-all')).toBeVisible();
  });

  test('should show responsive navigation', async ({ page, isMobile }) => {
    await page.goto('/');

    if (isMobile) {
      // Bottom navigation should be visible
      const bottomNav = page.locator('nav').first();
      await expect(bottomNav).toBeVisible();
      await expect(bottomNav.getByTestId('nav-dashboard')).toBeVisible();
      await expect(bottomNav.getByTestId('nav-submit')).toBeVisible();
      await expect(bottomNav.getByTestId('nav-track')).toBeVisible();
    } else {
      // Sidebar should be visible
      await expect(page.getByTestId('nav-dashboard').first()).toBeVisible();
      await expect(page.getByTestId('nav-submit').first()).toBeVisible();
      await expect(page.getByTestId('nav-track').first()).toBeVisible();
      await expect(page.getByTestId('nav-logout').first()).toBeVisible();
    }
  });
});
