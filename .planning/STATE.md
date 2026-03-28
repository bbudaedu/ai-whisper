---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: Executing Phase 07
last_updated: "2026-03-28T00:49:25.729Z"
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 3
  completed_plans: 2
---

# STATE: FaYin 全系統自動化 E2E 測試框架 (v2.0)

## Current Phase

- Phase: 07-test-infrastructure
- Phase Status: In Progress
- Current Plan: 2 (completed)
- Total Plans in Phase: 3
- Last Updated: 2026-03-28T00:47:49Z

## Last Session

- **Date**: 2026-03-28
- **Action**: Execute Plan 07-02 (API core integration tests)
- **Stopped At**: Plan 07-02 completed, ready for 07-03
- **Completed**:
    - 建立 `tests/v2/test_auth.py`（API key exchange、expired JWT、RBAC 隔離）
    - 建立 `tests/v2/test_tasks_crud.py`（youtube/upload create、history pagination、get/cancel）
    - 建立 `tests/v2/test_download.py`（zip formats、token query、RBAC、error codes）
    - 執行 `pytest tests/v2/test_auth.py tests/v2/test_tasks_crud.py tests/v2/test_download.py -v`，28 tests 全部 PASSED
    - 安裝缺失依賴：python-multipart

## Accumulated Decisions

- **worktree sync**: 並行 agent 的 worktree 分支需先 merge 主分支（gsd/v2.0-milestone）才有 api/ 和 pipeline/queue/ 代碼
- **conftest 繼承策略**: tests/v2/conftest.py 不重複定義 db_engine/db_session，繼承父層 tests/conftest.py
- **ISSUE-02 FIX**: client fixture 中在 SQLModel.metadata.create_all 前 import TaskEvent/TaskArtifact，確保建表完整
- **DB 隔離測試**: 使用 mtime 哨兵排除既有 database.db，只偵測測試中新增的 .db 文件
- **GPU 測試**: 使用 mock executor 不需要真實 GPU（從 test_lifespan_e2e.py 模式繼承）
- [Phase 07]: 07-02 follows runtime behavior: POST /api/tasks/ assertions use status 200
- [Phase 07]: Download pending-status test uses internal_auth_header to bypass RBAC and validate 400 path
- [Phase 07]: Upload and download fixtures derive paths from patched router OUTPUT_BASE to avoid tmp_path mismatch

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
