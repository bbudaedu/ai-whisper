---
phase: 07-test-infrastructure
plan: 01
subsystem: testing
tags: [pytest, fastapi, sqlmodel, sqlite, jwt, fixtures, conftest]

# Dependency graph
requires:
  - phase: 06-milestone-gap-fix
    provides: api/routers/tasks.py, api/routers/download.py, api/routers/auth.py, pipeline/queue/models.py

provides:
  - tests/v2/conftest.py：client/auth_header/internal_auth_header fixtures，繼承父層 db_engine/db_session
  - tests/v2/test_config.v2.json：語義測試設定記錄（database_url, enable_webhook=false, jwt_secret）
  - tests/v2/test_isolation.py：5 個環境隔離驗證測試全部 PASSED
  - tests/fixtures/v2/sample.wav：96KB 測試音訊資產

affects: [07-02, 07-03]

# Tech tracking
tech-stack:
  added:
    - email-validator（pydantic[email] 依賴）
    - argon2-cffi（passlib argon2 backend）
  patterns:
    - 繼承父層 conftest.py fixtures，不重複定義 db_engine/db_session
    - OAuth stub 安裝（authlib/google）使用 sys.modules.setdefault
    - monkeypatch.setattr 覆蓋 get_session/OUTPUT_BASE/log_task_event
    - FastAPI TestClient 不使用 api_server.app（避免 lifespan scheduler）

key-files:
  created:
    - tests/v2/__init__.py
    - tests/v2/conftest.py
    - tests/v2/test_config.v2.json
    - tests/v2/test_isolation.py
    - tests/fixtures/v2/sample.wav

key-decisions:
  - "v2/conftest.py 繼承父層 db_engine/db_session/user_fixture，不重複定義"
  - "test_db_session_is_in_memory 使用 mtime 哨兵排除既有 database.db"
  - "安裝 email-validator + argon2-cffi 作為缺失的測試依賴"
  - "client fixture 在 SQLModel.metadata.create_all 前 import TaskEvent/TaskArtifact（ISSUE-02 FIX）"

patterns-established:
  - "OAuth stub: sys.modules.setdefault 模式，在 conftest module-level 安裝"
  - "_get_session() 回傳 Session(db_engine)，不使用 context manager wrapper"
  - "auth_header 依賴 user_fixture（DB 中需有真實 user）；internal_auth_header 不需要"

requirements-completed: [TEST-04]

# Metrics
duration: 30min
completed: 2026-03-27
---

# Phase 07-01: Test Infrastructure Summary

**v2 測試基礎設施：帶 OAuth stub 的 conftest.py、語義設定檔、5 個隔離驗證測試全部 PASSED**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-27T16:10:00Z
- **Completed:** 2026-03-27T16:40:00Z
- **Tasks:** 3
- **Files modified:** 5 created

## Accomplishments

- 建立 `tests/v2/conftest.py`：包含 client/auth_header/internal_auth_header fixtures，繼承父層 db_engine/db_session，完整 patch tasks/download/auth router 依賴
- 建立語義設定檔 `tests/v2/test_config.v2.json`，明確記錄測試環境配置
- 建立 `tests/v2/test_isolation.py`，5 個測試全部通過，確認 DB 隔離、JWT 認證、OUTPUT_BASE patch 均正常

## Task Commits

每個 task 獨立 commit：

1. **Task 1: 建立目錄結構與語義設定檔** - `dec3f0e` (feat)
2. **Task 2: 實作 tests/v2/conftest.py** - `7e527c9` (feat)
3. **Task 3: 實作 test_isolation.py** - `8599f59` (feat)

## Files Created/Modified

- `tests/v2/__init__.py` — 空檔案，讓 pytest 識別 v2 為 package
- `tests/v2/conftest.py` — client/auth_header/internal_auth_header fixtures，OAuth stubs
- `tests/v2/test_config.v2.json` — 語義設定記錄（sqlite memory, jwt_secret 等）
- `tests/v2/test_isolation.py` — 5 個環境隔離驗證測試
- `tests/fixtures/v2/sample.wav` — 96KB 測試音訊資產

## Decisions Made

- **繼承策略**：v2/conftest.py 不重複定義 db_engine/db_session，直接繼承父層 tests/conftest.py
- **TaskEvent/TaskArtifact import**：[ISSUE-02] client fixture 中先 import 確保建表完整
- **test_db_session_is_in_memory 調整**：使用 mtime 哨兵方式排除已存在的 database.db，只偵測新增 .db 文件

## Deviations from Plan

### Auto-fixed Issues

**1. [Blocking] worktree 缺少 api/ 和 pipeline/queue/ 代碼**
- **Found during:** 開始前的環境分析
- **Issue:** worktree-agent-a7bcb04f 分支基於舊版代碼（無 api/ 目錄），而計劃依賴這些代碼
- **Fix:** 執行 `git merge gsd/v2.0-milestone`（fast-forward），同步主分支代碼
- **Verification:** api/ 和 pipeline/queue/ 目錄正確出現
- **Committed in:** 合併 commit（fast-forward，無需額外 commit）

**2. [Blocking] email-validator 套件未安裝**
- **Found during:** Task 3 - 執行 pytest 時
- **Issue:** api/schemas.py 使用 EmailStr 需要 pydantic[email]
- **Fix:** `pip install 'pydantic[email]'`
- **Verification:** import 成功，測試通過

**3. [Blocking] argon2-cffi 套件未安裝**
- **Found during:** Task 3 - 執行 pytest 時
- **Issue:** passlib 使用 argon2 hash 需要 argon2-cffi backend
- **Fix:** `pip install argon2-cffi`
- **Verification:** user_fixture 建立成功，test_auth_header_is_valid_jwt PASSED

**4. [Logic] test_db_session_is_in_memory 斷言需調整**
- **Found during:** Task 3 - 第一次執行測試
- **Issue:** worktree 根目錄存在既有 database.db（非測試產生），計劃的斷言會誤判
- **Fix:** 改用 mtime 哨兵方式，只檢查測試期間新增的 .db 文件
- **Verification:** 測試通過，確認既有 database.db 被正確排除

---

**Total deviations:** 4 auto-fixed (2 環境準備, 1 套件安裝, 1 邏輯修正)
**Impact on plan:** 全部修正均為必要調整，無功能範圍擴展。

## Issues Encountered

- worktree 分支缺少現代代碼結構（api/, pipeline/queue/）— 透過 merge gsd/v2.0-milestone 解決
- 缺少 email-validator 和 argon2-cffi 依賴 — 透過 pip install 解決
- database.db 既有文件導致 .db 隔離測試誤判 — 修正斷言邏輯解決

## Next Phase Readiness

- tests/v2/ 基礎設施就緒，client/auth_header/internal_auth_header fixtures 可直接使用
- 07-02（API 測試）和 07-03（Pipeline 測試）可基於這些 fixtures 展開
- 所有 v2 測試的三大 patch 目標（get_session/OUTPUT_BASE/log_task_event）均已在 client fixture 中處理

---
*Phase: 07-test-infrastructure*
*Completed: 2026-03-27*
