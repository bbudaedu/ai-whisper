---
phase: 05-long-term-history
plan: 06
subsystem: web-ui, api
tags: [routing, download, history]
requires: [STOR-01, STOR-02]
provides: [history-navigation, format-filtered-download]
tech-stack: [React, FastAPI]
key-files: [web-ui-external/src/App.tsx, api/routers/download.py]
metrics:
  duration: 15m
  completed_date: 2026-03-24
---

# Phase 05 Plan 06: 修補 Phase 05 驗證缺口 Summary

## Summary
本次執行修補了 Phase 05 的兩個關鍵驗證缺口：
1. **路由註冊**：在 `web-ui-external/src/App.tsx` 正確註冊了 `/history` 路由，確保使用者可以從導覽選單進入歷史任務頁面。
2. **下載 API 增強**：在 `api/routers/download.py` 擴充了支援的副檔名白名單（新增 vtt/json/tsv），並實作了 `format` 參數過濾邏輯，讓 UI 能夠下載單一特定格式的成果檔案。

## Deviations from Plan
None - 按照計劃執行。

## Key Decisions
- **下載行為保留 Zip 封裝**：即使是單一格式下載，後端仍維持使用 Zip 格式回傳，以符合現有前端 `downloadUrl` 的處理邏輯與檔名命名規則（`{task_id}_{timestamp}.zip`）。
- **嚴格白名單過濾**：若請求的 `format` 不在 `ALLOWED_SUFFIXES` 內，回傳 400 Bad Request；若過濾後無檔案，回傳 404 Not Found。

## Self-Check: PASSED
- [x] `web-ui-external/src/App.tsx` 含有 `<Route path="/history" element={<TaskHistory />} />`。
- [x] `api/routers/download.py` 擴充了 `ALLOWED_SUFFIXES`。
- [x] `download_task_results` 函式已加入 `format` 參數與過濾邏輯。
- [x] 已進行 grep 驗證確認程式碼變更。

## Known Stubs
None.
