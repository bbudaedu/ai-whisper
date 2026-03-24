# Roadmap: FaYin

## Overview

本路線圖以不破壞既有內部流程為前提，先建立可持久化任務佇列與單 GPU 排程，接著對外提供安全 API，再交付 mobile-first 外部 Web UI 與通知/下載體驗，之後提升轉錄與校對品質，最後完成長期保存能力。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: 任務佇列與排程基礎** - 以可持久化佇列與單 GPU 排程穩定現有流程
- [x] **Phase 2: 對外 API 與認證** - 提供安全的任務建立/查詢/取消/下載 API
- [x] **Phase 02.1: 新增外部使用者登入後端：Email/Password、Google OAuth、使用者與憑證儲存、token 交換與刷新** (INSERTED)
- [x] **Phase 3: 外部 Web UI 與提交流程** - mobile-first UI 讓外部使用者提交與追蹤任務
- [x] **Phase 4: 校對增強與說話者標註** - 提升品質與講義輔助校對 (completed 2026-03-22)
- [x] **Phase 5: 長期保存與歷史查詢** - 任務與檔案永久保留
- [ ] **Phase 6: 里程碑缺口修復** - 修正 API 路徑、統一格式名稱與狀態枚舉、同步文件

## Phase Details

### Phase 1: 任務佇列與排程基礎
**Goal**: 使用者提交任務後可被佇列化與分段處理，在單 GPU 與內部優先權下穩定執行且不破壞既有內部流程
**Depends on**: Nothing (first phase)
**Requirements**: QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-04, QUEUE-05
**Success Criteria** (what must be TRUE):
  1. 使用者提交任務後可看到任務進入排隊狀態並依序進入執行。
  2. 任務同時進來時，系統確保一次只有一個 Whisper 任務在 running，其餘保持 pending。
  3. 內部任務與外部任務同時排隊時，內部任務先被排程執行。
  4. 對同一播放清單，第 1 集完成下載後即可開始聽打，第 2 集仍在下載時前者已進入後續 stage。
  5. 任務失敗時系統自動重試，使用者可看到重試次數或狀態變化。
**Plans**: 6 plans

### Phase 2: 對外 API 與認證
**Goal**: 外部系統可透過安全 API 建立、查詢、取消與下載任務
**Depends on**: Phase 1
**Requirements**: API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. 授權使用者可用 API 建立任務（上傳音檔或提供 YouTube 連結）並取得任務 ID。
  2. 使用者可透過 API 查詢任務狀態（pending/running/done/failed）。
  3. 使用者可取消尚未完成的任務，且狀態立即反映為取消。
  4. 使用者可透過 API 下載結果檔案，未授權請求會被拒絕。
**Plans**: 6/6 plans complete
- [x] 02-01-PLAN.md — Models update and Wave 0 Test Stubs
- [x] 02-02-PLAN.md — Auth API Key Exchange
- [x] 02-03-PLAN.md — Task Submission API
- [x] 02-04-PLAN.md — Task Query and Cancellation API
- [x] 02-05-PLAN.md — Task Result Download API
- [x] 02-06-PLAN.md — Human Verification
(completed 2026-03-21)

### Phase 02.1: 新增外部使用者登入後端：Email/Password、Google OAuth、使用者與憑證儲存、token 交換與刷新 (INSERTED)

**Goal:** 建立外部使用者的 Email/Password 與 Google OAuth 登入機制，並實現持久化的使用者儲存與 token 的輪替撤銷。
**Requirements**: UI-02
**Depends on:** Phase 2
**Plans:** 6/6 plans complete

Plans:
- [x] 02.1-01-PLAN.md — Add User and Identity DB models
- [x] 02.1-02-PLAN.md — Password hashing and User repository methods
- [x] 02.1-03-PLAN.md — Email/Password Login API and Token Management Refactoring
- [x] 02.1-04-PLAN.md — Google OAuth Login Integration
- [x] 02.1-05-PLAN.md — Test cases for Auth Endpoints
- [x] 02.1-06-PLAN.md — Human Verification for Phase 02.1
(completed 2026-03-22)

### Phase 3: 外部 Web UI 與提交流程
**Goal**: 外部使用者可在 mobile-first UI 登入、提交與追蹤任務，並取得結果與通知
**Depends on**: Phase 02.1
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, NOTF-01, NOTF-02, PROC-01, PROC-02, PROC-06, PROC-07
**Success Criteria** (what must be TRUE):
  1. 使用者可在手機、平板與 PC 上登入（Email/Password 或 Google OAuth）並順利完成主要操作。
  2. 使用者可在 UI 上傳音檔或輸入 YouTube 播放清單連結建立任務，並選擇音檔性質、Prompt 與輸出格式。
  3. 使用者可在 UI 即時查看任務狀態與進度，並在完成後收到 Email 通知。
  4. 使用者可從 UI 下載多格式結果（txt, srt, word, excel, json）。
  5. 使用者可管理播放清單追蹤狀態，新的集數會自動排入任務清單並可在 UI 看到。
**Plans**: 6/6 plans complete
- [x] 03-01-PLAN.md — Scaffold web-ui-external project
- [x] 03-02-PLAN.md — Setup AuthContext and Login UI
- [x] 03-03-PLAN.md — Build Responsive Navigation and Dashboard
- [x] 03-04-PLAN.md — Build Task Submission Form
- [x] 03-05-PLAN.md — Build Task Tracker with Polling
- [x] 03-06-PLAN.md — Build Playlist Manager and Settings
(completed 2026-03-24)

### Phase 4: 校對增強與說話者標註
**Goal**: 提升轉錄品質並支援講義輔助校對與說話者標註
**Depends on**: Phase 3
**Requirements**: PROC-03, PROC-04, PROC-05
**Success Criteria** (what must be TRUE):
  1. 轉錄結果包含 Speaker A/B/C/D 標註，使用者可在結果檔案中看到。
  2. 使用者可上傳講義/文本並在任務中套用，結果可被使用者確認為校對品質提升。
  3. 使用者可在新任務中勾選已上傳的講義重複使用。
**Plans:** 2/2 plans complete
Plans:
- [x] 04-01-PLAN.md — Speaker Diarization Module
- [x] 04-02-PLAN.md — LLM Proofreading with RAG
(completed 2026-03-22)

### Phase 5: 長期保存與歷史查詢
**Goal**: 任務與檔案可長期保存並可持續查詢
**Depends on**: Phase 4
**Requirements**: STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. 使用者可在任務列表中查詢歷史任務，即使完成很久仍可存取狀態與紀錄。
  2. 使用者可在任意時間下載先前任務的輸出成果與原始音檔。
**Plans**: 4/4 plans complete
- [x] 05-03-PLAN.md — 整合持久化資料模型與資料庫
- [x] 05-04-PLAN.md — 擴充 API 回傳詳細歷史與產出資訊
- [x] 05-05-PLAN.md — 建立外部 Web UI 歷史頁面
- [x] 05-06-PLAN.md — 修補驗證缺口（路由註冊與下載 API 增強）
(completed 2026-03-24)

### Phase 6: 里程碑缺口修復
**Goal**: 修復 v1.0 稽核發現的整合斷鏈與文件不同步問題
**Depends on**: Phase 5
**Requirements**: QUEUE-01 to STOR-02 (maintenance)
**Success Criteria** (what must be TRUE):
  1. 前端歷史頁面與下載按鈕 API 路徑正確且可成功獲取資料。
  2. 下載 API 支援 frontend 傳送的 word/excel 並正確對應至 docx/xlsx。
  3. 前端 UI 狀態標籤與後端 TaskStatus 完全一致。
  4. REQUIREMENTS.md 與 PROJECT.md 反映最新實作進度。
**Plans**: 1 plan

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 02.1 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 任務佇列與排程基礎 | 6/6 | Complete | 2026-03-21 |
| 2. 對外 API 與認證 | 6/6 | Complete | 2026-03-21 |
| 02.1. 新增外部使用者登入後端 | 6/6 | Complete   | 2026-03-22 |
| 3. 外部 Web UI 與提交流程 | 6/6 | Complete | 2026-03-24 |
| 4. 校對增強與說話者標註 | 2/2 | Complete    | 2026-03-22 |
| 5. 長期保存與歷史查詢 | 4/4 | Complete | 2026-03-24 |
| 6. 里程碑缺口修復 | 0/1 | Pending | - |
