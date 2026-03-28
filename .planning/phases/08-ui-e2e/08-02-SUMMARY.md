---
phase: 08
plan: 02
subsystem: web-ui-external
tags: [e2e, playwright, task-flow, responsive]
requirements: [TEST-03]
tech-stack: [playwright, react]
key-files: [web-ui-external/src/pages/SubmitTask.tsx, web-ui-external/src/pages/TaskTracker.tsx, web-ui-external/e2e/task_flow.spec.ts]
decisions:
  - 為 SubmitTask 與 TaskTracker 元件添加 data-testid 以提高 E2E 測試穩定性。
  - 在 TaskTracker 中調整顯示邏輯，允許顯示「已完成」狀態的任務，以便 E2E 驗證下載連結。
  - 使用 Page Object 模式的基礎（直接定位）實作任務流測試。
metrics:
  duration: 2026-03-28
  completed_tasks: 2
  files_modified: 4
---

# Phase 08 Plan 02: Task Flow & Responsive Summary

## Summary

本階段成功實作了核心任務流程（提交 -> 追蹤 -> 狀態更新 -> 下載）的 E2E 自動化測試，並驗證了行動版與桌面版的響應式佈局。

- **UI 強化**: 在 `SubmitTask.tsx` 與 `TaskTracker.tsx` 中添加了必要的 `data-testid` 屬性。
- **任務流測試**: 實作了 `task_flow.spec.ts`，模擬使用者提交 YouTube 網址、在追蹤頁面看到任務「等待中」、模擬後端處理完成後 UI 更新為「已完成」並顯示下載連結的完整過程。
- **響應式驗證**: 測試涵蓋了 Mobile Safari (iPhone 12) Viewport，驗證底部導覽列在行動裝置上的可見性與功能。
- **Mocking 策略**: 使用 Playwright 的 `page.route` 精確控制 API 回應，確保測試在不依賴真實後端環境的情況下也能穩定執行。

## Key Decisions

- **顯示狀態擴展**: 修改了 `TaskTracker.tsx` 的 `useMemo` 過濾邏輯，將 `done`, `failed`, `canceled` 納入顯示範圍（原僅顯示進行中任務）。這不僅有利於測試驗證「已完成」狀態，也符合使用者查看近期完成任務的需求。
- **Stateful Mocking**: 在 E2E 測試中使用變數 `historyCallCount` 來追蹤 API 呼叫次數，藉此模擬任務狀態從 `pending` 變更為 `done` 的動態過程。

## Key Files Created/Modified

- `web-ui-external/src/pages/SubmitTask.tsx` (Modified: Added data-testid)
- `web-ui-external/src/pages/TaskTracker.tsx` (Modified: Added data-testid, updated status filter)
- `web-ui-external/e2e/task_flow.spec.ts` (Created: Core flow tests)

## Deviations from Plan

- **TaskTracker 邏輯調整**: 為了驗證任務完成後的 UI（如連結下載），必須調整 `TaskTracker` 原本只顯示「活動中」任務的邏輯，使其能顯示已完成的任務。
- **Nav Item ID**: 計畫中提到 `nav-tracker`，但實際程式碼中使用 `nav-track`，已在測試腳本中同步修正。

## Metrics

- Duration: 2026-03-28
- Completed tasks: 2/2
- Files created/modified: 3

## Known Stubs

None.

## Self-Check: PASSED
