---
phase: 02
slug: api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — defaults |
| **Quick run command** | `/home/budaedu/ai-whisper/venv/bin/python -m pytest -q` |
| **Full suite command** | `/home/budaedu/ai-whisper/venv/bin/python -m pytest` |
| **Estimated runtime** | ~unknown seconds |

---

## Sampling Rate

- **After every task commit:** Run `/home/budaedu/ai-whisper/venv/bin/python -m pytest -q`
- **After every plan wave:** Run `/home/budaedu/ai-whisper/venv/bin/python -m pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** unknown seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | API-05 | unit/integration | `pytest -q tests/test_external_api_auth.py::test_api_key_exchange -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | API-01 | integration | `pytest -q tests/test_external_api_tasks.py::test_create_task -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | API-02 | unit/integration | `pytest -q tests/test_external_api_tasks.py::test_get_status -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | API-03 | integration | `pytest -q tests/test_external_api_tasks.py::test_cancel_task -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | API-04 | integration | `pytest -q tests/test_external_api_download.py::test_download_zip -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_external_api_auth.py` — stubs for API-05
- [ ] `tests/test_external_api_tasks.py` — stubs for API-01 ~ API-03
- [ ] `tests/test_external_api_download.py` — stubs for API-04

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < unknowns
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
