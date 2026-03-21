---
phase: 03
slug: web-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend); frontend 未設定 |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 600 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | UI-01 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | UI-02 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | UI-03 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | UI-04 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | UI-05 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | UI-06 | manual | — | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | UI-07 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | NOTF-01 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | NOTF-02 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | PROC-01 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | PROC-02 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-05 | 02 | 2 | PROC-06 | manual | — | ❌ W0 | ⬜ pending |
| 03-02-06 | 02 | 2 | PROC-07 | manual | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Frontend 測試框架缺失（例如 Vitest 或 Playwright）
- [ ] 缺少 UI 自動化測試覆蓋 UI-01 ~ UI-07
- [ ] 缺少針對 NOTF/PROC UI 行為的測試

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile-first 響應式 UI | UI-01 | 無自動化 UI 測試 | 手動縮放視窗至手機/平板/桌機寬度，確認導覽/排版不破版 |
| Email/Password + Google OAuth 登入 | UI-02 | 需真實 OAuth | 使用測試帳號完成登入、登出、重新整理後仍保留登入 |
| 上傳音檔建立任務 | UI-03 / PROC-01 | 需實際上傳檔案 | 從提交頁上傳音檔，確認任務建立成功 |
| YouTube 播放清單追蹤 | UI-04 / PROC-02 | 需實際播放清單 | 輸入播放清單 URL，確認清單建立與追蹤狀態顯示 |
| 參數設定（Prompt/性質/格式） | UI-05 / PROC-06 / PROC-07 | 需實際表單操作 | 填寫參數後建立任務，確認後端接收值 |
| 任務進度追蹤 | UI-06 | 需真實任務狀態 | 任務進行中/完成時在 UI 顯示狀態與進度 |
| 結果下載 | UI-07 / NOTF-02 | 需實際產出 | 任務完成後可下載 Zip 與格式清單 |
| Email 通知 | NOTF-01 | 需外部郵件 | 任務完成後確認 Email 收到 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 600s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
