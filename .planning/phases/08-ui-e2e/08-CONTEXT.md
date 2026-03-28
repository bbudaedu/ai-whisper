---
phase: 08
title: Web UI E2E 自動化測試 (UI E2E)
status: discussed
last_update: 2026-03-28T02:30:00Z
---

## 決策摘要

### 1. 測試框架與工具
- **框架**: 使用 **Playwright** 作為 UI E2E 測試引擎。
- **路徑**: 測試程式碼將放在 `web-ui-external/e2e/` 目錄。
- **執行**: 透過 `npm run test:e2e` 在 `web-ui-external` 目錄執行。
- **配置**: `playwright.config.ts` 將定義 `webServer` 自動啟動 Vite dev server。

### 2. 測試範圍
- **Auth (登入流程)**:
  - 驗證 Google 登入按鈕存在。
  - 驗證成功登入後 Token 正確存入 LocalStorage。
  - 驗證未登入時訪問保護頁面會重導向至 `/login`。
- **Task Flow (任務提交與追蹤)**:
  - 模擬提交 YouTube URL。
  - 驗證任務出現在 Dashboard 或 History 中。
  - 驗證狀態從 PENDING 到 DONE 的 UI 反饋。
- **Responsive (響應式佈局)**:
  - 在 **Desktop Chrome** (1280x720) 與 **Mobile Safari** (iPhone 12 寬度) 兩種 Viewport 執行。
  - 驗證行動版導覽列 (Mobile Nav) 與桌面版側邊欄 (Sidebar) 的切換。

### 3. 穩定性與實作策略
- **data-testid**: 將在 `web-ui-external/src/` 的關鍵元件（如登入按鈕、URL 輸入框、提交按鈕、導覽連結）手動添加 `data-testid` 屬性。
- **Auth State**: 使用 Playwright 的 `storageState` 功能，僅在 Auth 測試中執行登入，其他測試則重用 Session。
- **Backend Coupling**: 測試時後端 API Server 必須運行中。建議在執行 UI E2E 前先確保後端已使用測試專用的 `database.db` 啟動。

## 待辦事項 (下一個階段)
1. 安裝 `@playwright/test` 及其相依套件。
2. 配置 `playwright.config.ts`。
3. 為 React 元件添加 `data-testid`。
4. 實作基礎登入測試腳本。
5. 實作任務流測試腳本。

## 預期產出
- `web-ui-external/e2e/` 測試套件。
- `web-ui-external/playwright.config.ts` 配置文件。
- 修正後的 React 元件 (含 `data-testid`)。
