---
phase: 05-long-term-history
plan: 04
subsystem: api
tags: [history, api, schemas]
requirements: [STOR-01, STOR-02]
status: complete
completed_date: "2026-03-24"
duration: 15m
key_files: [api/schemas.py, api/routers/tasks.py]
decisions:
  - Extended TaskStatusResponse to include events and artifacts for full history visibility.
  - Mapped TaskEvent and TaskArtifact DB models to API schemas in the task detail endpoint.
---

# Phase 05 Plan 04: 擴充 API 回傳詳細歷史與產出資訊 Summary

## Summary
擴充了任務相關的 API Schema 與端點，使任務詳情 API (`GET /api/tasks/{task_id}`) 能回傳完整的事件歷程 (Events) 與產出檔案列表 (Artifacts)。這為前端顯示任務的時間軸與提供檔案下載連結奠定了基礎。

## Key Changes
- **api/schemas.py**: 新增 `TaskEventSchema` 與 `TaskArtifactSchema`，並更新 `TaskStatusResponse` 包含這兩個列表。
- **api/routers/tasks.py**: 更新 `get_task_status` 端點，從資料庫讀取事件與產出資料並填充至回應模型中。

## Known Stubs
None.

## Deviations from Plan
None.

## Self-Check: PASSED
- [x] Created/Modified files exist.
- [x] Commits exist in git history.
- [x] Schema includes events and artifacts.
- [x] API endpoint retrieves and returns the data.
