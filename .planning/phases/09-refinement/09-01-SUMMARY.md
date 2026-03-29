---
phase: 09-refinement
plan: 01
subsystem: Backend
tags: [database, api, speaker-name]
requirements: [DB-01, API-01]
tech-stack: [SQLModel, FastAPI, SQLite]
key-files: [pipeline/queue/models.py, api/routers/tasks.py, api/schemas.py, tests/v2/test_task_update.py]
decisions:
  - 在 Task 模型中新增 speaker_name 欄位並建立索引。
  - 實作 PATCH /api/tasks/{task_id} 端點以支援局部更新。
  - 更新 TaskStatusResponse 以包含 speaker_name。
metrics:
  duration: 15m
  completed_date: 2026-03-28
---

# Phase 09 Plan 01: Backend (Speaker Name DB & API) Summary

## Summary
本次變更成功在後端系統中引入了「說話者名稱（speaker_name）」的儲存與編輯功能。這包括資料庫結構的擴充、API Schema 的更新，以及新增一個用於更新任務資訊的 PATCH 端點。所有的變更皆已通過新編寫的單元測試與整合測試。

## Key Changes
- **資料庫擴充**: 在 `tasks` 表中新增了 `speaker_name` 欄位（TEXT 類型）並建立了索引，以利後續查詢與優化。
- **API Schema 更新**: 在 `TaskStatusResponse` 中新增了 `speaker_name` 欄位，並新增了 `TaskUpdatePayload` 供 PATCH 端點使用。
- **PATCH API 實作**: 在 `api/routers/tasks.py` 中新增了 `PATCH /api/tasks/{task_id}` 端點，目前支援更新 `speaker_name`。該端點具備權限檢查，僅限 `internal` 角色或任務擁有者可執行更新。
- **測試覆蓋**: 建立了 `tests/v2/test_task_update.py`，涵蓋了成功更新、404 未找到、401 未授權、403 禁止訪問以及 GET 回傳驗證。

## Deviations from Plan
None - plan executed exactly as written.

## Self-Check: PASSED
- [x] 檔案 `pipeline/queue/models.py` 已更新
- [x] 檔案 `api/schemas.py` 已更新
- [x] 檔案 `api/routers/tasks.py` 已更新
- [x] 資料庫遷移已執行
- [x] 測試 `tests/v2/test_task_update.py` 全部通過
