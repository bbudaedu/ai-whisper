---
phase: 1
slug: task-queue-scheduling
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (repo 現有) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 01-01 | 01 | 0 | QUEUE-01 | unit | `pytest -q tests/test_task_queue.py::test_create_task_smoke tests/test_task_queue.py::test_create_stage_task_smoke -x` | ⬜ pending |
| 01-02 | 01 | 0 | QUEUE-01 | unit | `python -c "from pipeline.queue.database import get_engine, create_db_and_tables, get_session, reset_engine; print('OK')"` | ⬜ pending |
| 01-03 | 01 | 0 | ALL | stub | `pytest -q tests/test_task_queue.py tests/test_scheduler_gpu_lock.py tests/test_scheduler_priority.py tests/test_pipeline_stages.py tests/test_retry_policy.py` | ⬜ pending |
| 01-04 | 01 | 0 | QUEUE-01 | unit | `pytest -q tests/test_task_queue.py -x` | ⬜ pending |
| 02-01 | 02 | 1 | QUEUE-01,03 | unit | `pytest -q tests/test_task_queue.py tests/test_scheduler_priority.py -x` | ⬜ pending |
| 02-02 | 02 | 1 | QUEUE-05 | unit | `pytest -q tests/test_retry_policy.py::test_retry_backoff tests/test_retry_policy.py::test_backoff_max_cap tests/test_retry_policy.py::test_should_retry -x` | ⬜ pending |
| 02-03 | 02 | 1 | QUEUE-01 | unit | `pytest -q tests/test_migration_fallback.py -x` | ⬜ pending |
| 03-01 | 03 | 1 | QUEUE-02,03 | unit+int | `pytest -q tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py -x` | ⬜ pending |
| 03-02 | 03 | 1 | QUEUE-02 | unit+int | `pytest -q tests/test_scheduler_gpu_lock.py tests/test_scheduler_integration.py -x` | ⬜ pending |
| 04-01 | 04 | 1 | QUEUE-04 | unit | `python -c "from pipeline.stages import download, transcribe, proofread, postprocess; print('OK')"` | ⬜ pending |
| 04-02 | 04 | 1 | QUEUE-04 | unit | `pytest -q tests/test_pipeline_stages.py -x` | ⬜ pending |
| 04-03 | 04 | 1 | QUEUE-04 | integration | `pytest -q tests/test_pipeline_stages.py -x` | ⬜ pending |
| 05-01 | 05 | 2 | QUEUE-04 | unit | `python -c "from pipeline.queue.scheduler import TaskScheduler; print('build_default_executors' in dir(TaskScheduler))"` | ⬜ pending |
| 05-02 | 05 | 2 | QUEUE-01 | integration | AST parse check for lifespan, get_queue_status, manage_task | ⬜ pending |
| 05-03 | 05 | 2 | ALL | integration | `pytest -q tests/test_api_task_submission.py -x` | ⬜ pending |
| 05-04 | 05 | 2 | ALL | full suite | `pytest -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_task_queue.py` — stubs for QUEUE-01 (佇列持久化與 pending/running 流程)
- [ ] `tests/test_scheduler_gpu_lock.py` — stubs for QUEUE-02 (GPU lock 互斥行為)
- [ ] `tests/test_scheduler_priority.py` — stubs for QUEUE-03 (內部/外部優先權)
- [ ] `tests/test_pipeline_stages.py` — stubs for QUEUE-04 (stage fan-out 行為)
- [ ] `tests/test_retry_policy.py` — stubs for QUEUE-05 (retry/backoff 行為)
- [ ] `tests/conftest.py` — SQLite 測試 fixture（temp DB + Session）

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 現有 YouTube 監控流程不受影響 | implicit | 需要實際 YouTube 播放清單與 NAS | 手動觸發 `auto_youtube_whisper.py`，確認正常執行完成 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
