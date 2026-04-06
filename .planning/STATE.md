---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: Complete
last_updated: "2026-03-29T08:35:00.000Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
---

# STATE: FaYin 全系統自動化 E2E 測試框架 (v2.0)

## Current Phase

- Phase: 09-refinement
- Phase Status: Complete
- Current Plan: 3 (completed)
- Total Plans in Phase: 3
- Last Updated: 2026-03-29T08:35:00Z

## Last Session

- **Date**: 2026-03-29
- **Action**: Execute Plan 09-03 (LLM Prompt Enhancement)
- **Stopped At**: Completed 09-03-PLAN.md
- **Completed**:
    - 優化 `auto_proofread.py` 的 Prompt 以包含講者名稱。
    - 支援自定義 Prompt 中的 `{{speaker_name}}` 佔位符。
    - 串接 Pipeline 將 DB 中的 `speaker_name` 傳遞至校對腳本。
    - 新增 `tests/v2/test_pipeline_context.py` 驗證端到端參數傳遞。

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
- [Phase 08]: 擴展 TaskTracker 顯示範圍至 done/failed/canceled 狀態以支持端對端驗證。
- [Phase 09]: 在 Task 模型中新增 speaker_name 欄位並建立索引。
- [Phase 09]: 實作 PATCH /api/tasks/{task_id} 端點以支援局部更新。
- [Phase 09]: 更新 TaskStatusResponse 以包含 speaker_name。
- [Phase 09-refinement]: 使用 onBlur 與 Enter 鍵觸發 API 更新
- [Phase 09-refinement]: 在展開列中新增編輯區塊
- [Phase 09-refinement]: 收合時自動清除編輯狀態
- [Phase 09-refinement]: 在 Prompt 中明確區分預設提示詞與講者資訊（speaker_section）
- [Phase 09-refinement]: 支援自定義 Prompt 中的 {{speaker_name}} 佔位符

## Current Blocking Issues

（已解決）

- ~~**GPU Dependency**~~: Phase 07 使用 mock executor，不需要真實 GPU
- ~~**Test Assets**~~: 已複製 tests/fixtures/v2/sample.wav（96KB WAV）

## Milestones

- [x] v1.0: Core Infrastructure & Web UI
- [x] v2.0: E2E Automation & Refinement (Speaker Names, Real LLM)

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 07    | 01   | 30min    | 3     | 5     |
| Phase 07 P02 | 4min | 3 tasks | 3 files |
| Phase 07 P03 | 3min | 3 tasks | 3 files |
| Phase 08-ui-e2e P01 | 1.5h | 3 tasks | 7 files |
| Phase 08-ui-e2e P02 | 45m | 2 tasks | 4 files |
| Phase 09 P01 | 15m | 4 tasks | 4 files |
| Phase 09-refinement P02 | 15m | 1 tasks | 1 files |
| Phase 09-refinement P03 | 15m | 3 tasks | 3 files |
