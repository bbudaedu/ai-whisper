# Requirements: FaYin

**Defined:** 2026-03-21
**Core Value:** 任何人都能透過 Web UI 或 API 提交音檔，自動完成語音轉文字、校對與格式化，並在完成後收到通知與結果檔案。

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Task Queue & Scheduling (QUEUE)

- [x] **QUEUE-01**: 系統提供異步任務佇列，任務提交後排隊等待 GPU 資源
- [x] **QUEUE-02**: 單 GPU 排程機制，一次只執行一個 Whisper 任務
- [x] **QUEUE-03**: 內部任務優先於外部任務執行
- [x] **QUEUE-04**: 工作流模組化為獨立 stage（下載→聽打→校對→排版），各 stage 可並行（下載完第 1 集即交付聽打，同時下載第 2 集）
- [x] **QUEUE-05**: 失敗任務自動重試（可設定重試次數）

### API (API)

- [x] **API-01**: RESTful API 端點：建立任務（上傳音檔或提供 YouTube 連結）
- [x] **API-02**: RESTful API 端點：查詢任務狀態（pending/running/done/failed）
- [x] **API-03**: RESTful API 端點：取消任務
- [x] **API-04**: RESTful API 端點：下載任務結果
- [x] **API-05**: API 認證（JWT token）

### Transcription & Processing (PROC)

- [ ] **PROC-01**: 使用者可上傳音檔進行語音轉錄
- [ ] **PROC-02**: 使用者可追蹤 YouTube 播放清單，自動偵測新集數排入佇列
- [ ] **PROC-03**: 說話者分離標註（Speaker A/B/C/D）
- [ ] **PROC-04**: 使用者可上傳講義/文本/會議紀錄輔助 LLM 校對，提升正確率
- [ ] **PROC-05**: 上傳過的講義可在下次勾選重複使用
- [ ] **PROC-06**: 使用者可選擇音檔性質（會議、佛學課程）套用對應處理流程
- [ ] **PROC-07**: 使用者可選擇 Prompt 與參數設定

### External Web UI (UI)

- [x] **UI-01**: Mobile-first 響應式設計（手機、平板、PC），手機友善是硬需求
- [x] **UI-02**: 認證登入（Email/Password + Google OAuth）
- [ ] **UI-03**: 上傳音檔介面
- [ ] **UI-04**: YouTube 播放清單追蹤介面（輸入清單 URL，管理追蹤狀態）
- [ ] **UI-05**: 參數設定介面（Prompt、音檔性質、輸出格式選擇）
- [x] **UI-06**: 任務進度追蹤介面（即時顯示任務狀態與進度）
- [x] **UI-07**: 結果下載介面

### Notification & Delivery (NOTF)

- [ ] **NOTF-01**: 任務完成後發送 Email 通知
- [x] **NOTF-02**: 多格式輸出（txt, srt, word, excel, json）

### Storage (STOR)

- [ ] **STOR-01**: 音檔與輸出成果永久保留
- [ ] **STOR-02**: 任務紀錄永久保存

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Speaker Recognition

- **SPKR-01**: 說話者名稱可編輯（替換 A/B/C/D 為真實人名）
- **SPKR-02**: 說話者聲紋比對（與已知人名資料庫配對）

### Enhanced Features

- **ENH-01**: Webhook callback 通知（API 回調）
- **ENH-02**: 自動摘要 / 重點整理
- **ENH-03**: 專有詞彙表（Custom vocabulary）
- **ENH-04**: 講義資料庫 / 知識庫（長期累積）
- **ENH-05**: 播放清單完結自動偵測（停止追蹤已完結清單）

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| 即時串流轉錄 | 架構成本高、GPU 競爭、延遲與準確率難平衡。v1 僅支援檔案上傳與 YouTube 連結 |
| 多 GPU 排程 | 目前只有一張 GPU，排程複雜度不值得 |
| 付費方案 / 計費系統 | 需合規、稅務與客服配套，日後規劃 |
| Mobile native app | Web UI Mobile-first 即可 |
| 獨立客戶端 repo | 決定同 repo 獨立 app |
| 協作與批註功能 | 使用者規模尚小，日後再加 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUEUE-01 | Phase 1 | Complete |
| QUEUE-02 | Phase 1 | Complete |
| QUEUE-03 | Phase 1 | Complete |
| QUEUE-04 | Phase 1 | Complete |
| QUEUE-05 | Phase 1 | Complete |
| API-01 | Phase 2 | Complete |
| API-02 | Phase 2 | Complete |
| API-03 | Phase 2 | Complete |
| API-04 | Phase 2 | Complete |
| API-05 | Phase 2 | Complete |
| PROC-01 | Phase 3 | Pending |
| PROC-02 | Phase 3 | Pending |
| PROC-03 | Phase 4 | Pending |
| PROC-04 | Phase 4 | Pending |
| PROC-05 | Phase 4 | Pending |
| PROC-06 | Phase 3 | Pending |
| PROC-07 | Phase 3 | Pending |
| UI-01 | Phase 3 | Complete |
| UI-02 | Phase 3 | Complete |
| UI-03 | Phase 3 | Pending |
| UI-04 | Phase 3 | Pending |
| UI-05 | Phase 3 | Pending |
| UI-06 | Phase 3 | Complete |
| UI-07 | Phase 3 | Complete |
| NOTF-01 | Phase 3 | Pending |
| NOTF-02 | Phase 3 | Complete |
| STOR-01 | Phase 5 | Pending |
| STOR-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after roadmap creation*
