---
phase: 03-web-ui
plan: 06
subsystem: web-ui-external
tags: [ui, playlists, settings]
requires: [05, 04]
provides: [UI-01, UI-04, PROC-02, NOTF-01]
tech-stack: [React, Tailwind, Lucide React]
key-files: [web-ui-external/src/pages/Playlists.tsx, web-ui-external/src/pages/Settings.tsx]
decisions: [使用統一的 Playlists 頁面管理 YouTube 播放清單追蹤, 設定頁面整合通知信箱與登出功能]
metrics:
  duration: 20m
  completed_date: 2026-03-22
---

# Phase 03 Plan 06: Playlist & Settings Summary

## Summary
實作了外部 Web UI 的播放清單管理頁面與個人設定頁面。

- **播放清單管理**：使用者可以新增 YouTube 播放清單網址進行追蹤，支援啟用/停用追蹤狀態切換，並可查看各清單的處理統計（總影片、已轉錄、待處理）。
- **個人設定**：提供電子郵件通知信箱配置，並整合登出按鈕以清除認證狀態。
- **路由整合**：在 `App.tsx` 中註冊 `/playlists` 與 `/settings` 路由，取代先前的佔位符。

## Test plan
- [x] 驗證 `web-ui-external` 專案可成功 build。
- [x] 檢查 `Playlists.tsx` 邏輯包含新增 (POST)、切換 (PUT) 與刪除 (DELETE) 呼叫。
- [x] 檢查 `Settings.tsx` 邏輯包含電子郵件輸入與登出 (AuthContext.logout)。

## Deviations from Plan
None - plan executed exactly as written.

## Known Stubs
- `Playlists.tsx` 與 `Settings.tsx` 的 API 呼叫路徑（`/api/playlists`, `/api/config`）已根據計畫實作，但後端對應端點可能尚未完全對接（取決於 Phase 02 的進度）。

## Self-Check: PASSED
- [x] `web-ui-external/src/pages/Playlists.tsx` exists.
- [x] `web-ui-external/src/pages/Settings.tsx` exists.
- [x] Commits `a1a789d` and `26101fc` exist.
