---
phase: 07-test-infrastructure
verified: 2026-03-28T02:15:00Z
status: passed
score: 16/16 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 14/16
  gaps_closed:
    - "GPU Lock 跨進程互斥：兩個 process 同時 acquire，只有一個成功"
    - "TEST-04: 提供單一指令執行本 phase 測試"
  gaps_remaining: []
  regressions: []
---

# Phase 07: 測試基礎設施與 API/Pipeline 自動化 (Test Infrastructure) Verification Report

**Phase Goal:** 全系統自動化 E2E 測試框架（本 phase 範圍：Test Infrastructure、Backend API tests、Pipeline E2E/GPU tests；Web UI 遞延至 Phase 08）
**Verified:** 2026-03-28T02:15:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | tests/v2 執行不會在專案根目錄產生新 `.db` | ✓ VERIFIED | `tests/v2/test_isolation.py::test_db_session_is_in_memory` 且 `pytest` 全綠 |
| 2 | v2 client fixture 含 auth/tasks/download routers | ✓ VERIFIED | `tests/v2/conftest.py` 內 `app.include_router` 包含所有核心 router |
| 3 | v2 conftest 繼承父層 db_engine/db_session | ✓ VERIFIED | `tests/v2/conftest.py` 正確引用父層定義 |
| 4 | isolation 測試覆蓋 DB/fixture wiring | ✓ VERIFIED | `tests/v2/test_isolation.py` 測試通過 |
| 5 | `/api/auth/token` 可回傳 access/refresh token | ✓ VERIFIED | `tests/v2/test_auth.py` 測試通過 |
| 6 | 過期 JWT 訪問保護端點回 401 + expired detail | ✓ VERIFIED | `tests/v2/test_auth.py` 測試通過 |
| 7 | external 不能看/取消他人任務 | ✓ VERIFIED | `tests/v2/test_auth.py` 與 `test_tasks_crud.py` 測試通過 |
| 8 | internal 可查看所有任務 | ✓ VERIFIED | `tests/v2/test_auth.py` 測試通過 |
| 9 | YouTube 建立任務回 pending + task_id>0 | ✓ VERIFIED | `tests/v2/test_tasks_crud.py` 測試通過 |
| 10 | Upload 任務會寫入 OUTPUT_BASE/{task_id} | ✓ VERIFIED | `tests/v2/test_tasks_crud.py` 測試通過 |
| 11 | Download DONE 任務回 zip，`format=word` 僅 docx | ✓ VERIFIED | `tests/v2/test_download.py` 測試通過 |
| 12 | Download 支援 `?token=` query auth | ✓ VERIFIED | `tests/v2/test_download.py` 測試通過 |
| 13 | Pipeline: DOWNLOAD 成功後 fan-out TRANSCRIBE | ✓ VERIFIED | `tests/v2/test_pipeline.py` 測試通過 |
| 14 | Stage 例外時狀態變 FAILED/PENDING(retry) | ✓ VERIFIED | `tests/v2/test_pipeline.py` 測試通過 |
| 15 | GPU lock 跨進程同時 acquire 僅一個成功 | ✓ VERIFIED | `tests/v2/test_gpu_concurrency.py` 已更新斷言，嚴格驗證 acquired=1, blocked=1 |
| 16 | Smoke E2E: mock executor 下 4 輪推進到 DONE | ✓ VERIFIED | `tests/v2/test_smoke_e2e.py` 測試通過 |

**Score:** 16/16 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tests/v2/conftest.py` | v2 fixtures + dependency patching | ✓ VERIFIED | 內容實作完整，被 v2 測試使用 |
| `tests/v2/test_config.v2.json` | semantic test config | ✓ VERIFIED | 包含必要測試配置 |
| `tests/v2/test_isolation.py` | 基礎隔離驗證 | ✓ VERIFIED | 5 tests 通過 |
| `tests/v2/test_auth.py` | Auth/API key/RBAC 測試 | ✓ VERIFIED | 6 tests 通過 |
| `tests/v2/test_tasks_crud.py` | Task CRUD 測試 | ✓ VERIFIED | 11 tests 通過 |
| `tests/v2/test_download.py` | Download 格式/RBAC/錯誤測試 | ✓ VERIFIED | 11 tests 通過 |
| `tests/v2/test_pipeline.py` | pipeline 狀態機測試 | ✓ VERIFIED | 3 tests 通過 |
| `tests/v2/test_gpu_concurrency.py` | GPU lock 並發測試 | ✓ VERIFIED | 已修正斷言邏輯，確保互斥性驗證有效 |
| `tests/v2/test_smoke_e2e.py` | API→Scheduler→DONE smoke | ✓ VERIFIED | 4 tests 通過 |
| `package.json` | 統一測試入口 | ✓ VERIFIED | 已新增 `test:v2` 與 `test:v2:gpu` 腳本 |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `package.json` | `tests/v2` | `npm run test:v2` | ✓ WIRED | 提供標準化單一入口 |
| `tests/v2/test_gpu_concurrency.py` | `gpu_lock.py` | `acquired/blocked` counters | ✓ WIRED | 嚴格斷言互斥行為 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `tests/v2/test_gpu_concurrency.py` | `results` (`acquired/blocked`) | multiprocessing worker | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Run all v2 tests | `.venv/bin/pytest tests/v2 -v` | `46 passed` | ✓ PASS |
| Unified entry point exists | `grep "test:v2" package.json` | Found script | ✓ PASS |
| GPU mutual exclusion | `.venv/bin/pytest tests/v2/test_gpu_concurrency.py` | `6 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| TEST-01 | 07-02 | API 自動化測試 | ✓ SATISFIED | 涵蓋 Auth/CRUD/Download，測試全數通過 |
| TEST-02 | 07-03 | Pipeline 整合測試 | ✓ SATISFIED | GPU 互斥與 Pipeline 狀態機驗證完成 |
| TEST-04 | 07-01 | 測試環境與自動化執行指令 | ✓ SATISFIED | 隔離環境達成，且已提供 npm script 入口 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `api/auth.py` | - | `datetime.utcnow()` deprecation | ⚠️ Warning | 建議未來改用 `datetime.now(timezone.utc)` |

### Gaps Summary

所有先前識別的缺口已修復：
1. **GPU 互斥驗證**：`test_cross_process_mutual_exclusion` 現在嚴格斷言只有一個進程能取得鎖，另一個必須被阻擋。
2. **單一命令入口**：`package.json` 已補上 `test:v2` 腳本，達成 TEST-04 要求。

---

_Verified: 2026-03-28T02:15:00Z_
_Verifier: Claude (gsd-verifier)_
