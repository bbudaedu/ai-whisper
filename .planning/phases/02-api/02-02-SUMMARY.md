---
phase: 02-api
plan: 02
subsystem: auth
tags: [jwt, api-keys, fastapi, sqlmodel]

# Dependency graph
requires:
  - phase: 01-task-queue-scheduling
    provides: queue models and database setup
provides:
  - JWT auth helpers with refresh rotation
  - API key lifecycle tooling
  - Auth endpoints for token exchange/refresh/revoke
affects: [api, security, external-clients]

# Tech tracking
tech-stack:
  added: [PyJWT]
  patterns: [refresh token rotation, api-key exchange]

key-files:
  created:
    - api/auth.py
    - api/schemas.py
    - scripts/seed_api_keys.py
  modified:
    - api_server.py
    - pipeline/queue/repository.py
    - api/models.py

key-decisions:
  - "Persist refresh tokens with user role to preserve auth context during rotation."

patterns-established:
  - "API key exchange issues short-lived JWT + refresh token stored hashed in DB."

requirements-completed: [API-05]

# Metrics
duration: 11m
completed: 2026-03-21
---

# Phase 02 Plan 02: API Auth Exchange Summary

**API key 交換 JWT + refresh token 輪替，含 DB 持久化與撤銷端點。**

## Performance

- **Duration:** 11m
- **Started:** 2026-03-21T10:29:54Z
- **Completed:** 2026-03-21T10:40:35Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- 建立 Token/Refresh/Revoke schema 與 JWT helpers
- 實作 API key 建立/驗證/撤銷與 CLI seed 工具
- 整合 /api/auth/token、/api/auth/refresh、/api/auth/revoke 與 refresh rotation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create auth schemas and security dependencies** - `406085b` (feat)
2. **Task 2: Implement API key lifecycle script** - `99b7e70` (feat)
3. **Task 3: Integrate auth endpoints and token persistence into API server** - `268d12d` (feat)

## Files Created/Modified
- `api/schemas.py` - Token/Refresh/Revoke request/response models
- `api/auth.py` - JWT 建立/驗證、token hash 與 refresh expiry helper
- `scripts/seed_api_keys.py` - API key 建立/撤銷 CLI
- `pipeline/queue/repository.py` - API key/refresh token DB 存取
- `api_server.py` - Auth 交換、刷新、撤銷端點
- `api/models.py` - RefreshToken 加入 role 欄位

## Decisions Made
- Persist refresh tokens with user role to preserve auth context during rotation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Preserve role during refresh rotation**
- **Found during:** Task 3 (Integrate auth endpoints and token persistence into API server)
- **Issue:** Plan 未包含 refresh token role 持久化，刷新時會遺失角色資訊，影響 D-03/D-06 權限判斷。
- **Fix:** 在 RefreshToken 增加 role 欄位，建立/刷新時保存與沿用角色。
- **Files modified:** api/models.py, pipeline/queue/repository.py, api_server.py
- **Verification:** 端點與資料流編譯可用，refresh token 仍可輪替。
- **Committed in:** 268d12d (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** 必要的安全修正，未擴大範圍。

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API 認證基礎已完成，可在後續 API 端點套用 Bearer 驗證與權限控制。
- 需確保執行環境設定 JWT_SECRET 與 refresh/access 期限參數。

---
*Phase: 02-api*
*Completed: 2026-03-21*

## Self-Check: PASSED
- FOUND: /home/budaedu/ai-whisper/.planning/phases/02-api/02-02-SUMMARY.md
- FOUND: 406085b
- FOUND: 99b7e70
- FOUND: 268d12d
