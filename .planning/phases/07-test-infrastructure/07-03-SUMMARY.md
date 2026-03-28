---
phase: 07-test-infrastructure
plan: 03
subsystem: testing
tags: [pytest, sqlmodel, fastapi, scheduler, gpu-lock, multiprocessing]
requires:
  - phase: 07-01
    provides: v2 測試基礎設施與隔離策略
provides:
  - Pipeline 狀態機整合測試（fan-out、完整 stage 推進、失敗處理）
  - GPU lock 跨進程互斥測試與 is_gpu_busy 行為測試
  - API submit 到 scheduler 推進 DONE 的 smoke E2E 測試
affects: [07-test-infrastructure, v2-e2e, pipeline-queue]
tech-stack:
  added: []
  patterns: ["mock executor + in-memory sqlite + lifespan TestClient", "multiprocessing 驗證 flock 跨進程互斥"]
key-files:
  created:
    - tests/v2/test_pipeline.py
    - tests/v2/test_gpu_concurrency.py
    - tests/v2/test_smoke_e2e.py
  modified: []
key-decisions:
  - "Pipeline 測試採獨立 session_factory，不依賴 API client fixture，避免 DB state 交叉污染。"
  - "GPU lock 互斥以跨進程行為為主，單進程二次 acquire 依實作斷言為 blocked。"
patterns-established:
  - "Smoke E2E fixture 必須 patch tasks router 副作用與 PlaylistSyncWorker。"
  - "驗證 fan-out 時需在活躍 session 內取出純值，避免 DetachedInstanceError。"
requirements-completed: [TEST-02]
duration: 3min
completed: 2026-03-28
---

# Phase 07 Plan 03: Pipeline/GPU/Smoke 測試 Summary

**以 mock executor 驗證 queue pipeline stage 遞進、跨進程 GPU lock 互斥與 API→Scheduler→DONE 完整資料流。**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-28T01:09:03Z
- **Completed:** 2026-03-28T01:12:14Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- 建立 `tests/v2/test_pipeline.py`，覆蓋 DOWNLOAD→TRANSCRIBE fan-out、4 輪 `_process_next()` 到 DONE、stage 失敗處理。
- 建立 `tests/v2/test_gpu_concurrency.py`，以 `multiprocessing.Process` 驗證 lock 競爭與釋放後可重取。
- 建立 `tests/v2/test_smoke_e2e.py`，覆蓋 `/api/task` 提交、`/api/queue/status`、scheduler 運行狀態與 partial fan-out。

## Task Commits

Each task was committed atomically:

1. **Task 1: 實作 Pipeline 狀態機測試** - `46aa49b` (feat)
2. **Task 2: 實作 GPU 並發鎖定測試** - `9394c9c` (feat)
3. **Task 3: 實作端對端 Smoke Test** - `db597f7` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `tests/v2/test_pipeline.py` - Pipeline fan-out、DONE 遞進、失敗/重試狀態驗證
- `tests/v2/test_gpu_concurrency.py` - flock 跨進程互斥、同進程行為、is_gpu_busy 狀態驗證
- `tests/v2/test_smoke_e2e.py` - lifespan 啟動 scheduler 的整合 smoke 測試與 API 連通驗證

## Decisions Made

- Pipeline 測試使用獨立 in-memory engine + session factory，避免與 API integration 測試互相污染。
- Smoke 測試固定 patch `api.routers.tasks.log_task_event`、`api.routers.tasks.OUTPUT_BASE`、`PlaylistSyncWorker.start/stop`，避免測試副作用寫入生產目錄或啟動背景 loop。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] pytest 指令在 shell PATH 不可用**
- **Found during:** Task 1
- **Issue:** `pytest: command not found`
- **Fix:** 改用專案虛擬環境執行 `/home/budaedu/ai-whisper/.venv/bin/pytest`
- **Files modified:** None
- **Verification:** `tests/v2/test_pipeline.py` 全數通過
- **Committed in:** N/A（執行方式調整）

**2. [Rule 1 - Bug] 同進程 double acquire 斷言與實際 lock 行為不一致**
- **Found during:** Task 2
- **Issue:** 測試初稿假設同進程第二次 acquire 會成功，但目前實作回傳 `None`
- **Fix:** 依現有 `gpu_lock.py` 實際行為調整斷言為 `fd2 is None`
- **Files modified:** `tests/v2/test_gpu_concurrency.py`
- **Verification:** `pytest tests/v2/test_gpu_concurrency.py -v` 6 passed
- **Committed in:** `9394c9c`

**3. [Rule 3 - Blocking] 缺少 itsdangerous 導致 api_server import 失敗**
- **Found during:** Task 3
- **Issue:** `ModuleNotFoundError: No module named 'itsdangerous'`
- **Fix:** 安裝依賴 `itsdangerous==2.2.0` 至 `.venv`
- **Files modified:** None（僅本機 venv）
- **Verification:** `pytest tests/v2/test_smoke_e2e.py -v` 4 passed
- **Committed in:** N/A（環境修復）

---

**Total deviations:** 3 auto-fixed（Rule 1: 1、Rule 3: 2）
**Impact on plan:** 皆為可執行性與正確性必要修正，無額外功能擴張。

## Auth Gates

None.

## Known Stubs

None.

## Issues Encountered

- 測試環境套件與 shell PATH 有落差，改採 `.venv/bin/pytest` 統一執行。
- API server 依賴 `itsdangerous` 未安裝，補齊後 smoke 測試正常。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TEST-02 子項已覆蓋完成，07-test-infrastructure 三個 plan 測試集合齊備。
- 可進入後續驗證與整體里程碑收斂。

## Self-Check: PASSED

- Files verified: `tests/v2/test_pipeline.py`, `tests/v2/test_gpu_concurrency.py`, `tests/v2/test_smoke_e2e.py`, `.planning/phases/07-test-infrastructure/07-03-SUMMARY.md`
- Commits verified: `46aa49b`, `9394c9c`, `db597f7`
