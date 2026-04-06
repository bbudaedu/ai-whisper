---
phase: 07-test-infrastructure
plan: 02
subsystem: testing
tags: [pytest, fastapi, auth, jwt, rbac, download, zip, api]

# Dependency graph
requires:
  - phase: 07-01
    provides: tests/v2/conftest.py fixtures 與測試隔離環境

provides:
  - tests/v2/test_auth.py：API key 交換、過期 token、external/internal RBAC 測試
  - tests/v2/test_tasks_crud.py：任務建立/查詢/取消/歷史分頁整合測試
  - tests/v2/test_download.py：download zip 格式篩選、token query、RBAC 與錯誤碼測試

affects: [07-03, regression-testing, api-stability]

# Tech tracking
tech-stack:
  added:
    - python-multipart（multipart/form-data 解析依賴）
  patterns:
    - v2 API 測試以 FastAPI TestClient + in-memory SQLModel 驗證端對端行為
    - RBAC 測試固定比對 external 與 internal 權限邊界
    - download 測試使用 zipfile 驗證封裝內容與相對路徑 arcname

key-files:
  created:
    - tests/v2/test_auth.py
    - tests/v2/test_tasks_crud.py
    - tests/v2/test_download.py
  modified: []

key-decisions:
  - "以程式碼實際行為為準，POST /api/tasks/ 回傳 200（非研究筆記中的 201）"
  - "download pending 400 測試使用 internal_auth_header，避開 RBAC 先行 403"
  - "upload/download fixture 皆依賴已 patch 的 router OUTPUT_BASE，避免 tmp_path 不一致"

patterns-established:
  - "Auth 測試以 hash_token 產生 ApiKey.key_hash，確保與 repo.verify_api_key 一致"
  - "Download 驗證同時覆蓋 Bearer header 與 ?token= 查詢參數"

requirements-completed: [TEST-01]

# Metrics
duration: 4min
completed: 2026-03-28
---

# Phase 07 Plan 02: API Core Integration Tests Summary

**建立 Auth/Tasks/Download 三大 API 整合測試組，完整覆蓋 API key 交換、JWT 過期、RBAC 隔離、任務 CRUD 與 zip 下載格式篩選。**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-28T00:43:23Z
- **Completed:** 2026-03-28T00:47:49Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- 新增 `tests/v2/test_auth.py`，覆蓋 `/api/auth/token` 成功/失敗、expired token 401、external/internal 任務可見性邊界。
- 新增 `tests/v2/test_tasks_crud.py`，覆蓋 YouTube/Upload 建立、歷史分頁、單筆查詢、取消任務授權行為。
- 新增 `tests/v2/test_download.py`，覆蓋 download zip 全格式與 alias 篩選、`?token=` 認證、RBAC 與 400/404 錯誤路徑。

## Task Commits

Each task was committed atomically:

1. **Task 1: 實作 Auth 補缺測試** - `27d4d09` (test)
2. **Task 2: 實作 Tasks CRUD 測試** - `7c16fb2` (test)
3. **Task 3: 實作 Download 測試** - `21687fe` (test)

## Files Created/Modified
- `tests/v2/test_auth.py` - API key 換 token、過期 JWT、RBAC 可見性測試。
- `tests/v2/test_tasks_crud.py` - 任務建立、歷史、查詢、取消的整合測試矩陣。
- `tests/v2/test_download.py` - 下載格式、認證、授權、錯誤碼與 zip 結構驗證。

## Decisions Made
- 以實作行為為準：`POST /api/tasks/` 斷言 `status_code == 200`。
- `test_download_pending_task_returns_400` 使用 `internal_auth_header`，避免 RBAC 檢查先回 403。
- fixture 路徑一律取自已 patch 的 `api.routers.tasks.OUTPUT_BASE` / `api.routers.download.OUTPUT_BASE`。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 安裝缺失依賴 python-multipart**
- **Found during:** Task 2 (Tasks CRUD upload 測試)
- **Issue:** multipart 請求在 `request.form()` 觸發 `The python-multipart library must be installed`，導致 upload 測試失敗。
- **Fix:** 在專案 venv 安裝 `python-multipart`，恢復 multipart 表單解析能力。
- **Files modified:** 無（環境依賴）
- **Verification:** 重新執行 `pytest tests/v2/test_tasks_crud.py -v`，11 tests 全部通過。
- **Committed in:** N/A（無檔案變更）

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** 屬於必要環境修復，無範圍擴張；計畫目標全部達成。

## Auth Gates
None.

## Issues Encountered
- 系統缺少 `python-multipart` 導致 upload 測試無法解析 multipart form；已安裝後恢復正常。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 07-02 API 回歸測試已成形，可作為 07-03 pipeline/smoke 測試前置驗證閘。
- 測試現已覆蓋 TEST-01 主要子項，後續可在 CI 直接串接此三檔測試。

## Self-Check: PASSED

- FOUND: /home/budaedu/ai-whisper/tests/v2/test_auth.py
- FOUND: /home/budaedu/ai-whisper/tests/v2/test_tasks_crud.py
- FOUND: /home/budaedu/ai-whisper/tests/v2/test_download.py
- FOUND: /home/budaedu/ai-whisper/.planning/phases/07-test-infrastructure/07-02-SUMMARY.md
- FOUND: commit 27d4d09
- FOUND: commit 7c16fb2
- FOUND: commit 21687fe
