# Roadmap: FaYin

## Overview

本路線圖以不破壞既有內部流程為前提，先建立可持久化任務佇列與單 GPU 排程，接著對外提供安全 API，再交付 mobile-first 外部 Web UI 與通知/下載體驗，之後提升轉錄與校對品質，最後完成長期保存能力。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: 任務佇列與排程基礎** - 以可持久化佇列與單 GPU 排程穩定現有流程
- [ ] **Phase 2: 對外 API 與認證** - 提供安全的任務建立/查詢/取消/下載 API
- [ ] **Phase 3: 外部 Web UI 與提交流程** - mobile-first UI 讓外部使用者提交與追蹤任務
- [ ] **Phase 4: 校對增強與說話者標註** - 提升品質與講義輔助校對
- [ ] **Phase 5: 長期保存與歷史查詢** - 任務與檔案永久保留

## Phase Details

### Phase 1: 任務佇列與排程基礎
**Goal**: 使用者提交的任務可被佇列化與分段處理，在單 GPU 與內部優先權下穩定執行且不破壞既有內部流程
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
**Plans**: 6 plans
- [ ] 02-01-PLAN.md — Models update and Wave 0 Test Stubs
- [ ] 02-02-PLAN.md — Auth API Key Exchange
- [ ] 02-03-PLAN.md — Task Submission API
- [ ] 02-04-PLAN.md — Task Query and Cancellation API
- [ ] 02-05-PLAN.md — Task Result Download API
- [ ] 02-06-PLAN.md — Human Verification

### Phase 3: 外部 Web UI 與提交流程
**Goal**: 外部使用者可在 mobile-first UI 登入、提交與追蹤任務，並取得結果與通知
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, NOTF-01, NOTF-02, PROC-01, PROC-02, PROC-06, PROC-07
**Success Criteria** (what must be TRUE):
  1. 使用者可在手機、平板與 PC 上登入（Email/Password 或 Google OAuth）並順利完成主要操作。
  2. 使用者可在 UI 上傳音檔或輸入 YouTube 播放清單連結建立任務，並選擇音檔性質、Prompt 與輸出格式。
  3. 使用者可在 UI 即時查看任務狀態與進度，並在完成後收到 Email 通知。
  4. 使用者可從 UI 下載多格式結果（txt, srt, word, excel, json）。
  5. 使用者可管理播放清單追蹤狀態，新的集數會自動排入任務清單並可在 UI 看到。
**Plans**: TBD

### Phase 4: 校對增強與說話者標註
**Goal**: 提升轉錄品質並支援講義輔助校對與說話者標註
**Depends on**: Phase 3
**Requirements**: PROC-03, PROC-04, PROC-05
**Success Criteria** (what must be TRUE):
  1. 轉錄結果包含 Speaker A/B/C/D 標註，使用者可在結果檔案中看到。
  2. 使用者可上傳講義/文本並在任務中套用，結果可被使用者確認為校對品質提升。
  3. 使用者可在新任務中勾選已上傳的講義重複使用。
**Plans**: TBD

### Phase 5: 長期保存與歷史查詢
**Goal**: 任務與檔案可長期保存並可持續查詢
**Depends on**: Phase 4
**Requirements**: STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. 使用者可在任務列表中查詢歷史任務，即使完成很久仍可存取狀態與紀錄。
  2. 使用者可在任意時間下載先前任務的輸出成果與原始音檔。
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 任務佇列與排程基礎 | 6/6 | Complete | 2026-03-21 |
| 2. 對外 API 與認證 | 0/6 | Not started | - |
| 3. 外部 Web UI 與提交流程 | 0/TBD | Not started | - |
| 4. 校對增強與說話者標註 | 0/TBD | Not started | - |
| 5. 長期保存與歷史查詢 | 0/TBD | Not started | - |