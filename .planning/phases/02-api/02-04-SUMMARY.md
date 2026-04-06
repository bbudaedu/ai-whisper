---
phase: 02-api
plan: 04
subsystem: api
tags: [fastapi, sqlmodel, tasks]

# Dependency graph
requires:
  - phase: 02-api
    provides: task creation endpoint
provides:
  - Task status query endpoint
  - Task cancel endpoint with reason codes
  - Repository helpers for filtered task lookups and cancellation
affects: [api, queue]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Task cancel returns status/reason payload"]

key-files:
  created: []
  modified:
    - pipeline/queue/repository.py
    - api/routers/tasks.py
    - api/schemas.py

key-decisions:
  - "Cancel endpoint returns 200 with status/reason except unauthorized (403)."

patterns-established:
  - "Repository cancel_task updates task + pending stages with client_cancel"

requirements-completed: [API-02, API-03]

# Metrics
duration: 0 min
completed: 2026-03-21
---

# Phase 02 Plan 04: Task Query + Cancel Summary

**Task status 조회與取消端點，並加上 repository 查詢/取消輔助與 reason code 回傳。**

## Performance

- **Duration:** 0 min
- **Started:** 2026-03-21T12:01:42Z
- **Completed:** 2026-03-21T12:01:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 新增 repository `get_task/get_tasks/cancel_task` 支援 requester/status 過濾與取消流程
- 新增 GET `/api/tasks/{task_id}` 狀態查詢與 POST `/api/tasks/{task_id}/cancel`
- 補齊 `TaskStatusResponse` 與 `TaskCancelResponse` schema

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get and cancel methods to repository** - `1b5dc3a` (feat)
2. **Task 2: Add status and cancel endpoints** - `d35a383` (feat)

## Files Created/Modified
- `pipeline/queue/repository.py` - 新增任務查詢與取消邏輯
- `api/routers/tasks.py` - 增加查詢/取消端點
- `api/schemas.py` - 增加回應 schema

## Decisions Made
- 取消任務非授權回 403，其餘情境 200 並回傳 status/reason。

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 取消/查詢端點已就緒，可繼續下載結果端點 (02-05)

---
*Phase: 02-api*
*Completed: 2026-03-21*
