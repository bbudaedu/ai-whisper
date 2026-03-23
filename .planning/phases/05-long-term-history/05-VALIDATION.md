---
phase: 05
slug: long-term-history
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_notebooklm_tasks.py` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_notebooklm_tasks.py`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | STOR-01 | unit | `pytest tests/test_notebooklm_tasks.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_notebooklm_tasks.py` — stubs for STOR-01, STOR-02
- [ ] `tests/test_notebooklm_scheduler.py` — shared fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 歷史列表與詳情 API | STOR-01 | 需要手動確認資料在 SQLite 存取的完整性 | 透過 API 查詢並下載歷史結果 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
