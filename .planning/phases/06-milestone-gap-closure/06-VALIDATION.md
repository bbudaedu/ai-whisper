---
phase: 06
slug: milestone-gap-closure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-24
last_updated: 2026-03-24
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_phase_06_integration.py` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_phase_06_integration.py`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | API-01 | integration | `pytest tests/test_phase_06_integration.py` | ✅ | ✅ green |
| 06-01-02 | 01 | 2 | API-04 | automated | `pytest tests/test_download_filter.py` | ✅ | ✅ green |
| 06-01-03 | 01 | 3 | INFRA | manual | - | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_phase_06_integration.py` — Verifies unified API paths and format mapping.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 前端狀態標籤顯示 | UI-06 | 視覺確認狀態與後端對齊 | 提交任務並觀察 UI 顯示正確狀態 |
| 文件同步檢查 | INFRA | 閱讀與邏輯一致性 | 檢查 REQUIREMENTS.md 與 PROJECT.md 的 [x] 標記 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Verified by Claude (gsd-nyquist-auditor)
