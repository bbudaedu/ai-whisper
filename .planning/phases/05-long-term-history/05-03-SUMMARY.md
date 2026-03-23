# Phase 05 Plan 03: 統一持久化資料層 Summary

## Summary
本計畫成功將分散在 `database.db` (sqlite3) 與 `task_queue.db` (SQLModel) 的資料模型整合至單一的 `task_queue.db`。更新了 `pipeline/queue/models.py` 以包含 `TaskEvent` 與 `TaskArtifact`，並擴充了 `TaskRepository` 提供相應的存取介面。同時重構了 `database/persistence.py` 橋接器，使其對外維持相容介面但內部轉向 SQLModel 持久化。

## Key Changes
- **模型擴充**: 在 `pipeline/queue/models.py` 中新增 `TaskEvent` 與 `TaskArtifact` SQLModel，並在 `Task` 模型中新增 `audio_profile` 與 `source_metadata` 欄位。
- **Repository 增強**: `TaskRepository` 新增了 `add_event`, `add_artifact`, `get_events`, `get_artifacts` 方法。
- **橋接器重構**: `database/persistence.py` 全面移除 `sqlite3` 直接調用，改用 `get_session` 與 `TaskRepository` 進行操作，確保與現有流程相容。
- **遷移工具**: 實作了 `scripts/migrate_to_unified_db.py` 用於將舊有 `database.db` 的資料搬移至新系統。
- **測試更新**: 更新了 `tests/test_persistence.py` 驗證重構後的持久化介面在 SQLModel 後端下運作正常。

## Deviations from Plan
### Auto-fixed Issues
**1. [Rule 1 - Bug] SQLAlchemy 保留字衝突**
- **Found during**: Task 3 驗證時。
- **Issue**: `TaskEvent` 模型中的 `metadata` 欄位名稱與 SQLAlchemy 的保留字衝突，導致 `InvalidRequestError`。
- **Fix**: 將 `TaskEvent.metadata` 重新命名為 `TaskEvent.event_metadata`。
- **Files modified**: `pipeline/queue/models.py`, `pipeline/queue/repository.py`, `scripts/migrate_to_unified_db.py`
- **Commit**: `4a409b4`

**2. [Rule 3 - Blocker] 缺少 json import**
- **Found during**: 執行測試時。
- **Issue**: `pipeline/queue/repository.py` 中使用了 `json.dumps` 但未導入 `json` 模組。
- **Fix**: 在檔案開頭加入 `import json`。
- **Files modified**: `pipeline/queue/repository.py`
- **Commit**: `8f6631d`

## Known Stubs
None.

## Self-Check: PASSED
- [x] `pipeline/queue/models.py` 包含新模型: FOUND
- [x] `database/persistence.py` 不再直接使用 sqlite3: FOUND
- [x] `scripts/migrate_to_unified_db.py` 存在: FOUND
- [x] 測試 `tests/test_persistence.py` 通過: PASSED

## Metrics
- **Duration**: ~20 min
- **Tasks**: 3
- **Files Modified**: 6
- **Completed Date**: 2026-03-24
