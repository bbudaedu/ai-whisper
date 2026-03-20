---
phase: 1
slug: task-queue-scheduling
status: draft
nyquist_compliant: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | QUEUE-01 | integration | `pytest -q tests/test_task_queue.py::test_enqueue_pending` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | QUEUE-02 | unit | `pytest -q tests/test_scheduler_gpu_lock.py::test_single_gpu_enforced` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | QUEUE-03 | unit | `pytest -q tests/test_scheduler_priority.py::test_internal_before_external` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 1 | QUEUE-04 | integration | `pytest -q tests/test_pipeline_stages.py::test_stage_fanout` | ❌ W0 | ⬜ pending |
| 01-05-01 | 05 | 1 | QUEUE-05 | unit | `pytest -q tests/test_retry_policy.py::test_retry_backoff` | ❌ W0 | ⬜ pending |

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
