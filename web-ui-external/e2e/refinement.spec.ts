import { test, expect } from '@playwright/test';

test.describe('Phase 09 Refinement: Speaker Name Editing', () => {
  // 使用 Phase 08 建立的 Session
  test.use({ storageState: '.auth/user.json' });

  test('should allow editing speaker name in TaskTracker', async ({ page }) => {
    const taskId = 123;
    let currentSpeakerName = '舊講者';
    const newName = '慧能大師';

    // 1. Mock API: 取得歷史記錄 (使用變數以支援動態更新)
    await page.route('**/api/tasks/history', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: taskId,
            url: 'https://youtube.com/watch?v=xxx',
            status: 'done',
            title: '測試任務',
            speaker_name: currentSpeakerName,
            created_at: new Date().toISOString()
          }
        ])
      });
    });

    // 2. Mock API: 監聽並驗證 PATCH 請求，更新模擬資料
    let patchCalled = false;
    await page.route(`**/api/tasks/${taskId}`, async route => {
      if (route.request().method() === 'PATCH') {
        const postData = route.request().postDataJSON();
        expect(postData.speaker_name).toBe(newName);
        patchCalled = true;
        currentSpeakerName = newName; // 更新模擬資料庫的值
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'ok' })
        });
      } else {
        await route.continue();
      }
    });

    // 3. 進入頁面並等待加載
    await page.goto('/track');

    // 4. 展開任務詳情
    const taskItem = page.getByTestId(`task-item-${taskId}`);
    await taskItem.click();

    // 5. 驗證輸入框初始值
    const input = page.getByTestId(`speaker-input-${taskId}`);
    await expect(input).toBeVisible();
    await expect(input).toHaveValue(currentSpeakerName);

    // 6. 模擬編輯行為
    await input.click();
    await input.fill(newName);
    await input.blur(); // 觸發 handleUpdateSpeaker -> manualRefresh

    // 7. 驗證 PATCH 是否被呼叫
    await expect.poll(() => patchCalled).toBe(true);

    // 8. 驗證重新加載後輸入框顯示新值
    await expect(input).toHaveValue(newName);
  });

  test('should show loading spinner while updating', async ({ page }) => {
    const taskId = 456;

    await page.route('**/api/tasks/history', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: taskId, url: '...', status: 'pending', title: 'Loading Test', created_at: new Date().toISOString() }
        ])
      });
    });

    // 延遲返回 PATCH 請求以捕捉 Loading 狀態
    await page.route(`**/api/tasks/${taskId}`, async route => {
      if (route.request().method() === 'PATCH') {
        await new Promise(resolve => setTimeout(resolve, 500));
        await route.fulfill({ status: 200, body: JSON.stringify({ ok: true }) });
      } else {
        await route.continue();
      }
    });

    await page.goto('/track');
    await page.getByTestId(`task-item-${taskId}`).click();

    const input = page.getByTestId(`speaker-input-${taskId}`);
    await input.fill('快速保存');
    await input.blur();

    // 檢查 Spinner 是否出現 (lucide-react 的 RefreshCw 帶有 animate-spin class)
    const spinner = page.locator('.animate-spin');
    await expect(spinner).toBeVisible();

    // 等待 Spinner 消失
    await expect(spinner).not.toBeVisible();
  });
});
