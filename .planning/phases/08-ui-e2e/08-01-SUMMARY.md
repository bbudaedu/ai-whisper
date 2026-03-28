# Phase 08 Plan 01: Playwright Setup & Auth Summary

## Summary

本階段成功建立了 Playwright E2E 測試基礎設施，並實作了針對登入流程與身份驗證保護的自動化測試。測試涵蓋了桌面版 (Chromium) 與行動版 (Mobile Safari) 的響應式導覽行為。

- 成功安裝 `@playwright/test` 並配置 `playwright.config.ts` 以自動啟動 Vite 開發伺服器。
- 為 `Login.tsx` 與 `Navigation.tsx` 添加了 `data-testid` 屬性，確保測試定位的穩定性。
- 實作了 `auth.setup.ts` 用於 Mock 登入狀態並持久化 Session，提高後續測試效率。
- 實作了 `login.spec.ts`，驗證了：
    1. 未登入使用者訪問受保護路徑會被重導向至 `/login`。
    2. 輸入無效憑證時顯示正確的錯誤訊息。
    3. 登入成功後跳轉至首頁，且導覽列顯示使用者資訊。

## Key Decisions

- **Mock API Calls**: 為了確保 E2E 測試的獨立性與執行速度，在 Auth 測試中使用了 Playwright 的 `page.route` 來 Mock 後端 API 回應。這避免了對後端資料庫狀態的依賴。
- **Init Scripts for Auth**: 在 `auth.setup.ts` 中使用 `page.addInitScript` 直接注入 `localStorage` 以模擬已登入狀態，這比點擊登入介面更為穩定且快速。
- **Mobile-Aware Testing**: 針對行動版 Viewport (iPhone 12)，調整了定位邏輯以識別底部的 `nav` 元素，而非桌面版的側邊欄。

## Tech Stack

- `@playwright/test` ^1.58.2
- Playwright Browsers: Chromium, WebKit (Mobile Safari)

## Key Files Created/Modified

- `web-ui-external/playwright.config.ts` (Created)
- `web-ui-external/package.json` (Modified)
- `web-ui-external/src/pages/Login.tsx` (Modified)
- `web-ui-external/src/components/Navigation.tsx` (Modified)
- `web-ui-external/e2e/auth.setup.ts` (Created)
- `web-ui-external/e2e/login.spec.ts` (Created)
- `web-ui-external/.gitignore` (Created)

## Deviations from Plan

- **Mocked Backend**: 原計畫建議使用 Phase 07 建立的後端測試環境，但考量到 UI E2E 測試的穩定性，決定改用 API Mocking 方式進行，確保前端開發與後端服務解耦。
- **initScript for Auth**: 原計畫建議透過 UI 流程進行 `auth.setup.ts`，改為使用 `addInitScript` 直接注入 localStorage 狀態，以獲得更快的執行速度。

## Metrics

- Duration: 2026-03-28
- Completed tasks: 3/3
- Files created/modified: 7

## Known Stubs

- **Google Login**: 目前 E2E 測試僅 Mock 了標準 Email 登入，未針對 Google 登入按鈕點擊後的外部導向流程進行測試（受限於第三方 Mocking 複雜度，已在 `Login.tsx` 驗證其渲染）。

## Self-Check: PASSED
