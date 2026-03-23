# FaYin

## What This Is

FaYin 是一套語音處理平台，將現有的 Whisper 語音轉錄能力 API 化，並提供外部客戶端 Web UI。平台支援會議錄音轉錄、佛學課程校對工作流（下載→聽打→校對→排版），以及 YouTube 播放清單自動監控。內部使用者與外部使用者共享同一組 GPU 資源，透過統一任務佇列依序處理。

## Core Value

任何人都能透過 Web UI 或 API 提交音檔，自動完成語音轉文字、校對與格式化，並在完成後收到通知與結果檔案。

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ YouTube 播放清單監控與自動下載 — existing
- ✓ Whisper (faster-whisper) GPU 語音轉錄 — existing
- ✓ LLM 校對與標點符號修正 — existing
- ✓ 多格式輸出（txt, srt, vtt, tsv, json） — existing
- ✓ 內部 Web UI 監控面板（React + TypeScript） — existing
- ✓ GPU 鎖定機制（gpu_lock.py） — existing
- ✓ FastAPI 後端 API 伺服器 — existing
- ✓ Phase 01: 佇列化任務與單 GPU 排程（含 stage fan-out） — validated in Phase 01
- ✓ Phase 02: RESTful API 端點（建立任務、查詢狀態、取消任務、下載結果）與 JWT 認證 — validated in Phase 02
- ✓ 外部客戶端 Web UI：Mobile-first 響應式設計（手機、平板、PC） — validated in Phase 03
- ✓ 外部客戶端 Web UI：認證登入（Email/Password + Google OAuth） — validated in Phase 03
- ✓ 外部客戶端 Web UI：上傳音檔處理 — validated in Phase 03
- ✓ 外部客戶端 Web UI：YouTube 播放清單追蹤（訂閱後自動偵測新集數排入佇列） — validated in Phase 03
- ✓ 外部客戶端 Web UI：單檔處理模式 — validated in Phase 03
- ✓ 外部客戶端 Web UI：Prompt / 參數設定 — validated in Phase 03
- ✓ 外部客戶端 Web UI：音檔性質選擇（會議、佛學課程） — validated in Phase 03
- ✓ 外部客戶端 Web UI：輸出格式多選（txt, word, excel, json） — validated in Phase 03
- ✓ 外部客戶端 Web UI：任務進度追蹤 UI — validated in Phase 03
- ✓ 外部客戶端 Web UI：完成後 Email 通知 — validated in Phase 03

### Active

<!-- Current scope. Building toward these. -->

**後端 API 化**
- [x] RESTful API 端點：建立任務、查詢狀態、取消任務、下載結果（Validated in Phase 02）
- [x] Webhook / Email 完成通知 (Validated in Phase 03)
- [ ] 說話者辨識標註（Speaker A/B/C/D）

**外部客戶端 Web UI**
- [x] Mobile-first 響應式設計（手機、平板、PC） — Validated in Phase 03
- [x] 認證登入（Email/Password + Google OAuth） — Validated in Phase 03
- [x] 上傳音檔處理 — Validated in Phase 03
- [x] YouTube 播放清單追蹤（訂閱後自動偵測新集數排入佇列） — Validated in Phase 03
- [x] 單檔處理模式 — Validated in Phase 03
- [x] Prompt / 參數設定 — Validated in Phase 03
- [x] 音檔性質選擇（會議、佛學課程） — Validated in Phase 03
- [x] 輸出格式多選（txt, word, excel, json） — Validated in Phase 03
- [x] 任務進度追蹤 UI — Validated in Phase 03
- [x] 完成後 Email 通知 — Validated in Phase 03

**校對增強**
- [ ] 上傳講義 / 文本 / 會議紀錄輔助 LLM 校對（提升正確率）
- [ ] 上傳過的講義可在下次勾選重複使用

**檔案管理**
- [ ] 音檔與輸出成果永久保留
- [ ] 任務紀錄永久保存

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- 說話者名稱編輯 / 人名比對 — v2 功能，v1 先標註 A/B/C/D
- 講義資料庫知識庫 — 日後規劃，v1 先做上傳 + 勾選歷史
- 獨立客戶端 repo — 決定同 repo 獨立 app
- 即時串流轉錄 — v1 僅支援檔案上傳與 YouTube 連結
- 多 GPU 排程 — 目前只有一張 GPU
- 付費方案 / 計費系統 — 日後規劃
- Mobile native app — Web UI Mobile-first 即可

## Context

**現有架構：**
- 後端：Python 3.x + FastAPI + uvicorn
- 前端：React 19 + TypeScript + Vite（位於 `web-ui/`）
- 處理工具：yt-dlp（下載）、ffmpeg（媒體處理）、faster-whisper（轉錄）
- GPU 管理：`gpu_lock.py` 確保資源不衝突
- 設定管理：`config.json`、`processed_videos.json`
- 流水線腳本：`auto_youtube_whisper.py`、`auto_proofread.py`、`auto_punctuation.py`
- 記憶層：`nocturne_memory/` 知識管理

**brownfield 狀態：** 已有完整的內部自動化流程，需要在不破壞現有功能的前提下，新增 API 層與外部 UI。

**使用者類型：**
- 內部使用者：透過現有 `web-ui/` 監控面板操作
- 外部使用者：透過新的客戶端 Web UI 操作（同 repo、獨立 app）

## Constraints

- **GPU**: 只有一張 GPU，一次只執行一個 Whisper 任務，必須統一佇列管理
- **優先級**: 內部任務優先於外部任務
- **Mobile-first**: 外部 Web UI 必須手機友善，這是硬需求不是加分項
- **不破壞現有功能**: 現有內部流程（YouTube 監控、自動校對）必須維持正常運作
- **同 repo**: 外部客戶端 Web UI 與現有專案同一 repo，但作為獨立 app
- **儲存**: 所有檔案與紀錄永久保留

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 外部 UI 與內部 UI 獨立 | 內部 UI 是監控面板，外部 UI 是客戶端操作介面，職責不同 | — Pending |
| 同 repo 獨立 app | 共享型別與 API 客戶端方便，降低管理成本 | — Pending |
| Email/Password + Google OAuth | 外部使用者需要登入認證，兩種方式都支援 | — Pending |
| 說話者辨識 v1 僅標註 A/B/C/D | 降低 MVP 複雜度，日後再做名稱編輯 | — Pending |
| MVP 優先 | 先可以用，增強功能日後完善 | — Pending |
| 內部任務優先 | 確保內部工作流不被外部任務影響 | — Pending |

---
*Last updated: 2026-03-23 after Phase 03 completion*
