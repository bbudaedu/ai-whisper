# FaYin

## What This Is

FaYin 是一套語音處理平台，將現有的 Whisper 語音轉錄能力 API 化，並提供外部客戶端 Web UI。平台支援會議錄音轉錄、佛學課程校對工作流（下載→聽打→校對→排版），以及 YouTube 播放清單自動監控。內部使用者與外部使用者共享同一組 GPU 資源，透過統一任務佇列依序處理。

## Current State

- **v1.0 (Shipped 2026-03-24)**: 已完成核心基礎設施、API 與 Web UI。
- **v2.0 (Shipped 2026-03-29)**: 建立了全系統自動化 E2E 測試框架 (Pytest/Playwright) 與講者編輯功能。

## Next Milestone Goals (v3.0)

- [ ] **多語言支援**: 擴充 API 與 UI 支援多國語言介面與轉譯目標語言。
- [ ] **Webhook 通知**: 支援 API 回調通知外部系統。
- [ ] **自動摘要**: 基於轉錄內容產出重點總結。
- [ ] **效能優化**: 針對大規模並發任務的佇列調優與資源回收。

## Requirements

<details>
<summary>v1.0-v2.0 已驗證需求 (Validated Requirements)</summary>

- ✓ YouTube 播放清單監控與自動下載 — existing
- ✓ Whisper (faster-whisper) GPU 語音轉錄 — existing
- ✓ LLM 校對與標點符號修正 — existing
- ✓ 多格式輸出（txt, srt, vtt, tsv, json, word, excel） — validated in Phase 03/06
- ✓ 內部 Web UI 監控面板（React + TypeScript） — existing
- ✓ GPU 鎖定機制（gpu_lock.py） — existing
- ✓ FastAPI 後端 API 伺服器 — existing
- ✓ Phase 01: 佇列化任務與單 GPU 排程 — validated in Phase 01
- ✓ Phase 02: RESTful API 與 JWT 認證 — validated in Phase 02
- ✓ Phase 03: Mobile-first Web UI (Email/Google OAuth) — validated in Phase 03
- ✓ Phase 04: 校對增強與說話者標註 (A/B/C/D) — validated in Phase 04
- ✓ Phase 05: 長期保存與歷史查詢 — validated in Phase 05
- ✓ Phase 06: 里程碑缺口修復 — validated in Phase 06
- ✓ Phase 07: 測試基礎設施與 API/Pipeline 自動化 — validated in Phase 07
- ✓ Phase 08: Web UI E2E 自動化測試 (Playwright) — validated in Phase 08
- ✓ Phase 09: 說話者編輯與真實 LLM 串接優化 — validated in Phase 09

</details>

### Active

<!-- Use /gsd:new-milestone to start v3.0 planning -->

### Out of Scope

- 即時串流轉錄 — v1/v2 僅支援檔案上傳與 YouTube 連結
- 多 GPU 排程 — 目前只有一張 GPU
- 付費方案 / 計費系統 — 日後規劃
- Mobile native app — Web UI Mobile-first 即可

## Context

**現有架構：**
- 後端：Python 3.x + FastAPI + uvicorn
- 前端：React 19 + TypeScript + Vite（位於 `web-ui-external/` 與 `web-ui/`）
- 處理工具：yt-dlp、ffmpeg、faster-whisper
- GPU 管理：`gpu_lock.py`
- 設定管理：`config.json`、`processed_videos.json`
- 記憶層：`.planning/codebase/`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 雙層自動化測試 | 確保 Backend API 與 Frontend UI 變更不破壞現有流程 | — Validated in v2.0 |
| Speaker Name 編輯 | 提升校對後的可用性，支援真實人名替換標註 | — Validated in v2.0 |
| 外部 UI 與內部 UI 獨立 | 職責不同（監控 vs 操作） | — Validated |
| 同 repo 獨立 app | 共享型別與 API 客戶端方便 | — Validated |

---
*Last updated: 2026-03-29 after Milestone v2.0 completion*
