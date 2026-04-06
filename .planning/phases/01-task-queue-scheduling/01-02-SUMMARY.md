---
phase: 01-task-queue-scheduling
plan: "02"
subsystem: [database, api, testing]
tags: [sqlmodel, sqlite, repository, backoff, retry, migration]

# Dependency graph
requires:
  - phase: 01-task-queue-scheduling
    provides: task queue models and database session helpers
provides:
  - repository layer with atomic claim and parent/child helpers
  - exponential backoff policy helpers for retry scheduling
  - processed_videos.json fallback lookup with SQLite preference
affects: [queue, scheduling, testing, migration]

# Tech tracking
tech-stack:
  added: []
  patterns: ["atomic claim via update+rowcount", "next_retry_at retry scheduling", "sqlite-first JSON fallback"]

key-files:
  created:
    - pipeline/queue/repository.py
    - pipeline/queue/backoff.py
    - pipeline/queue/migration.py
    - tests/test_task_queue.py
    - tests/test_scheduler_priority.py
    - tests/test_retry_policy.py
    - tests/test_migration_fallback.py
  modified: []

key-decisions:
  - "Align processed_videos.json fallback to repository root path to match auto_youtube_whisper.py"

patterns-established:
  - "Repository encapsulates task/stage creation, claims, and status updates"
  - "Retry backoff uses base delay with jitter and max cap"

requirements-completed: [QUEUE-01, QUEUE-03, QUEUE-05]

# Metrics
duration: 3min
completed: 2026-03-21
---

# Phase 1 Plan 02: Repository 層、退避策略與遷移 Fallback Summary

**Atomic task repository operations, exponential backoff scheduling, and SQLite-first processed_videos.json fallback with test coverage for QUEUE-01/03/05.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-21T01:19:37Z
- **Completed:** 2026-03-21T01:22:33Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- 建立 TaskRepository，提供原子 claim、父子任務與 stage output 支援
- 建立指數退避與重試判斷 helper，供 next_retry_at 排程使用
- 新增 processed_videos.json fallback，先查 SQLite 再讀 JSON

## Task Commits

Each task was committed atomically:

1. **Task 1: 實作 Repository 層 (repository.py)** - `c55c63c` (feat)
2. **Task 2: 實作指數退避模組 (backoff.py)** - `6d5efef` (feat)
3. **Task 3: 實作 processed_videos.json 遷移 fallback (migration.py)** - `554ec0a` (feat)

## Files Created/Modified
- `pipeline/queue/repository.py` - Task/Stage 任務建立、原子 claim 與狀態更新
- `pipeline/queue/backoff.py` - 指數退避與重試判斷 helper
- `pipeline/queue/migration.py` - SQLite 優先、JSON fallback 查詢
- `tests/test_task_queue.py` - 佇列建立與 payload/next_retry_at 測試
- `tests/test_scheduler_priority.py` - internal 優先 claim 測試
- `tests/test_retry_policy.py` - backoff 與 max_retries 測試
- `tests/test_migration_fallback.py` - JSON fallback 測試

## Decisions Made
- 將 migration fallback 的 processed_videos.json 預設路徑對齊 repo 根目錄，確保與 auto_youtube_whisper.py 一致。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修正 processed_videos.json fallback 預設路徑**
- **Found during:** Task 3 (實作 processed_videos.json 遷移 fallback)
- **Issue:** 初版 fallback 指向 pipeline/processed_videos.json，與 auto_youtube_whisper.py 使用的 repo 根目錄路徑不一致，導致查詢不到既有資料。
- **Fix:** 將預設路徑調整為 repo 根目錄的 processed_videos.json。
- **Files modified:** pipeline/queue/migration.py
- **Verification:** /home/budaedu/ai-whisper/venv/bin/python -m pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py tests/test_retry_policy.py tests/test_migration_fallback.py -x
- **Committed in:** 554ec0a (part of task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** 必要修正以維持既有流程相容性，未擴增範圍。

## Issues Encountered
- `python`/`pytest` 不在 PATH，改用 venv 的 /home/budaedu/ai-whisper/venv/bin/python 執行 pytest。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Repository/backoff/migration 基礎已就緒，可供 scheduler 與 API 整合使用
- 退避與 priority 測試已具備，可支撐後續排程驗證

## Self-Check: PASSED

---
*Phase: 01-task-queue-scheduling*
*Completed: 2026-03-21*
