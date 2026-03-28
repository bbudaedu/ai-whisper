---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: Phase 08 In Progress
last_updated: "2026-03-28T05:00:00.000Z"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 5
  completed_plans: 5
---

# STATE: FaYin 全系統自動化 E2E 測試框架 (v2.0)

## Current Phase

- Phase: 08-ui-e2e
- Phase Status: In Progress
- Current Plan: 1 (completed)
- Total Plans in Phase: 2
- Last Updated: 2026-03-28T05:00:00Z

## Last Session

- **Date**: 2026-03-28
- **Action**: Execute Plan 08-01 (Playwright Setup & Auth)
- **Stopped At**: Completed 08-01-PLAN.md
- **Completed**:
    - 在 `web-ui-external` 安裝並配置 Playwright。
    - 為 `Login.tsx` 與 `Navigation.tsx` 添加 `data-testid`。
    - 實作 `auth.setup.ts` 與 `login.spec.ts` (使用 API Mocking)。
    - 驗證跨瀏覽器 (Chromium/Mobile Safari) 的登入與重導向邏輯。

## Accumulated Decisions

- **worktree sync**: 並行 agent 的 worktree 分支需先 merge 主分支（gsd/v2.0-milestone）才有 api/ 和 pipeline/queue/ 代碼
- **conftest 繼承策略**: tests/v2/conftest.py 不重複定義 db_engine/db_session，繼承父層 tests/conftest.py
- **ISSUE-02 FIX**: client fixture 中在 SQLModel.metadata.create_all 前 import TaskEvent/TaskArtifact，確保建表完整
- **DB 隔離測試**: 使用 mtime 哨兵排除既有 database.db，只偵測測試中新增的 .db 文件
- **GPU 測試**: 使用 mock executor 不需要真實 GPU（從 test_lifespan_e2e.py 模式繼承）
- [Phase 07]: 07-02 follows runtime behavior: POST /api/tasks/ assertions use status 200
- [Phase 07]: Download pending-status test uses internal_auth_header to bypass RBAC and validate 400 path
- [Phase 07]: Upload and download fixtures derive paths from patched router OUTPUT_BASE to avoid tmp_path mismatch
- [Phase 07]: Pipeline tests use isolated in-memory session factory to avoid cross-test DB contamination
- [Phase 07]: Smoke fixture patches task-event/output paths and PlaylistSyncWorker to prevent side effects
- [Phase 08]: 使用 API Mocking 確保 UI E2E 測試的獨立性與執行速度。
- [Phase 08]: 針對行動版 Viewport 調整定位邏輯以識別底部的 nav 元素。

## Current Blocking Issues

（已解決）

- ~~**GPU Dependency**~~: Phase 07 使用 mock executor，不需要真實 GPU
- ~~**Test Assets**~~: 已複製 tests/fixtures/v2/sample.wav（96KB WAV）

## Milestones

- [x] v1.0: Core Infrastructure & Web UI
- [ ] v2.0: E2E Automation & Refinement (Speaker Names, Real LLM)

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 07    | 01   | 30min    | 3     | 5     |
| Phase 07 P02 | 4min | 3 tasks | 3 files |
| Phase 07 P03 | 3min | 3 tasks | 3 files |
| Phase 08-ui-e2e P01 | 1.5h | 3 tasks | 7 files |
