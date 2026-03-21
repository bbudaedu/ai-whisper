---
phase: 02-api
verified: 2026-03-21T00:00:00Z
status: human_needed
score: 16/17 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 15/17
  gaps_closed:
    - "User can upload an audio file via single endpoint."
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "End-to-end 外部 API 流程"
    expected: "API key 交換 token、建立任務（YouTube + upload）、查詢、取消、下載皆回正確狀態與 payload"
    why_human: "需要實際啟動 API 並驗證端到端行為與輸出檔案"
---

# Phase 2: 對外 API 與認證 Verification Report

**Phase Goal:** 外部系統可透過安全 API 建立、查詢、取消與下載任務
**Verified:** 2026-03-21T00:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | System tracks who created which task. | ✓ VERIFIED | `pipeline/queue/models.py` includes `Task.requester`; `api/routers/tasks.py` sets `task.requester`. |
| 2 | Tasks can be tracked in queued and canceled states. | ✓ VERIFIED | `pipeline/queue/models.py` defines `TaskStatus.QUEUED` and `TaskStatus.CANCELED`. |
| 3 | API keys and refresh tokens can be persisted and verified. | ✓ VERIFIED | `api/models.py` tables + `pipeline/queue/database.py` imports + `pipeline/queue/repository.py` verify methods. |
| 4 | Users receive valid short-lived JWTs and refresh tokens. | ✓ VERIFIED | `api/auth.create_access_token` sets `exp`; `/api/auth/token` returns `Token` with refresh token. |
| 5 | API rejects invalid or expired tokens. | ✓ VERIFIED | `api/auth.verify_token` raises 401 and is used by tasks/download routers. |
| 6 | Users can refresh and revoke tokens. | ✓ VERIFIED | `/api/auth/refresh` and `/api/auth/revoke` in `api_server.py`. |
| 7 | Admins can seed/create API keys. | ✓ VERIFIED | `scripts/seed_api_keys.py` uses `TaskRepository.create_api_key/revoke_api_key`. |
| 8 | User can submit a YouTube task via single endpoint. | ✓ VERIFIED | `POST /api/tasks` handles JSON with `payload.url` in `api/routers/tasks.py`. |
| 9 | User can upload an audio file via single endpoint. | ✓ VERIFIED | `api/routers/tasks.py` persists upload to `output/<task_id>` and seeds stage output; `pipeline/queue/stage_runner.py` merges seed output; `pipeline/stages/download.py` bypasses YouTube download. |
| 10 | Response contains task ID and initial status. | ✓ VERIFIED | `TaskCreateResponse` in `api/schemas.py` and response in `api/routers/tasks.py`. |
| 11 | User can check the status of their submitted task. | ✓ VERIFIED | `GET /api/tasks/{task_id}` uses `TaskRepository.get_task` with requester filter. |
| 12 | User can cancel their pending task and see it marked canceled. | ✓ VERIFIED | `TaskRepository.cancel_task` sets `TaskStatus.CANCELED` and updates stages. |
| 13 | Cancel response must include reason code. | ✓ VERIFIED | `TaskCancelResponse` with `status`/`reason` in `api/schemas.py` and router response. |
| 14 | User can download their completed task results. | ✓ VERIFIED | `GET /api/tasks/{task_id}/download` exists in `api/routers/download.py`. |
| 15 | Downloaded file is a ZIP archive containing processing results. | ✓ VERIFIED | `api/routers/download.py` uses `zipfile` and returns `FileResponse` with ZIP. |
| 16 | Internal users can download any task; external users can only download their own tasks. | ✓ VERIFIED | `api/routers/download.py` enforces role/requester check and 403. |
| 17 | Human can verify API endpoints function correctly with correct auth headers. | ? UNCERTAIN | 需要實際啟動 API 進行端到端測試。 |

**Score:** 16/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `pipeline/queue/models.py` | Updated Task/TaskStatus models | ✓ VERIFIED | `requester`, `QUEUED`, `CANCELED` present. |
| `api/models.py` | ApiKey/RefreshToken tables | ✓ VERIFIED | SQLModel tables defined. |
| `pipeline/queue/database.py` | DB initialization includes auth tables | ✓ VERIFIED | Imports ApiKey/RefreshToken before `create_all`. |
| `api/auth.py` | JWT generation/validation | ✓ VERIFIED | `create_access_token`, `verify_token`, `hash_token`. |
| `api/schemas.py` | Auth + task schemas | ✓ VERIFIED | Token, TaskCreateResponse, TaskStatusResponse, TaskCancelResponse. |
| `api/routers/tasks.py` | Task create/status/cancel endpoints | ✓ VERIFIED | POST/GET/cancel routes, upload persistence. |
| `pipeline/queue/stage_runner.py` | Stage context merges seeded output | ✓ VERIFIED | `seed_output = stage_task.get_output()` then `context.update(seed_output)`. |
| `pipeline/stages/download.py` | Upload bypass in download stage | ✓ VERIFIED | Returns upload `audio_path/episode_dir` when present. |
| `api/routers/download.py` | Download endpoint | ✓ VERIFIED | ZIP packaging + RBAC. |
| `api_server.py` | Routers mounted + auth endpoints | ✓ VERIFIED | `include_router(tasks_router/download_router)` + auth endpoints. |
| `scripts/seed_api_keys.py` | API key CLI | ✓ VERIFIED | create/revoke commands. |
| `tests/test_external_api_*.py` | Test stubs | ✓ VERIFIED (intentional stub) | `assert False` placeholders. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `api_server.py` | `api/routers/tasks.py` | `app.include_router` | WIRED | `app.include_router(tasks_router)` present. |
| `api/routers/tasks.py` | `pipeline/queue/repository.py` | Repository methods | WIRED | Uses `TaskRepository` for create/get/cancel. |
| `api_server.py` | `api/routers/download.py` | `app.include_router` | WIRED | `app.include_router(download_router)` present. |
| `api_server.py` | `api/auth.py` | `create_access_token` | WIRED | Auth endpoints call `create_access_token`. |
| `scripts/seed_api_keys.py` | `pipeline/queue/repository.py` | API key methods | WIRED | `create_api_key` / `revoke_api_key`. |
| `api/routers/tasks.py` | `output/<task_id>` | Upload persistence | WIRED | `OUTPUT_BASE / str(task.id)` used with file write. |
| `pipeline/queue/stage_runner.py` | `pipeline/stages/download.py` | Seeded output in context | WIRED | `stage_task.get_output()` merged before stage execution. |
| `pipeline/stages/download.py` | `pipeline/stages/transcribe.py` | `audio_path/episode_dir` | WIRED | Upload bypass returns both keys for downstream stage. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| API-01 | 02-01, 02-03, 02-07 | 建立任務（上傳音檔或 YouTube 連結） | ✓ SATISFIED | `POST /api/tasks` handles JSON/multipart + upload persistence. |
| API-02 | 02-01, 02-04 | 查詢任務狀態 | ✓ SATISFIED | `GET /api/tasks/{task_id}` with requester filter. |
| API-03 | 02-01, 02-04 | 取消任務 | ✓ SATISFIED | `POST /api/tasks/{task_id}/cancel` returns status/reason. |
| API-04 | 02-01, 02-05 | 下載任務結果 | ✓ SATISFIED | `GET /api/tasks/{task_id}/download` zips results. |
| API-05 | 02-01, 02-02 | API 認證（JWT token） | ✓ SATISFIED | `/api/auth/token|refresh|revoke` + JWT verify. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `tests/test_external_api_auth.py` | 1-2 | `assert False, "Not implemented"` | ℹ️ Info | Wave 0 預留測試 stub。 |
| `tests/test_external_api_tasks.py` | 1-10 | `assert False, "Not implemented"` | ℹ️ Info | Wave 0 預留測試 stub。 |
| `tests/test_external_api_download.py` | 1-2 | `assert False, "Not implemented"` | ℹ️ Info | Wave 0 預留測試 stub。 |

### Human Verification Required

### 1. End-to-end 外部 API 流程

**Test:** 以真實 API key 交換 token、提交任務（YouTube + upload）、查詢狀態、取消、下載結果。
**Expected:** 各端點回傳正確狀態碼與 payload；下載可取得 ZIP。
**Why human:** 需要實際啟動 API、依賴真實檔案與輸出結果。

### Gaps Summary

已補上 upload 任務持久化與 pipeline bypass，原先阻塞的 API-01 gap 已關閉。目前僅剩端到端人為驗證需要完成。

---

_Verified: 2026-03-21T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
