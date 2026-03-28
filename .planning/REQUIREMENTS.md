# Requirements: v2.0 (全系統自動化 E2E 測試框架)

## 🎯 Goals
建立一套涵蓋 legacy 功能與 v1.0 新功能的自動化測試框架，確保全系統（API, Pipeline, Web UI）在持續疊代中的穩定性。

## 📋 Scoping Questions
- **測試框架選擇**：是否使用 Python (Pytest) 整合 Playwright？還是分開處理？
- **環境模擬**：如何在 CI/測試環境中處理 GPU 依賴？（使用 Mock 還是特定測試 GPU？）
- **測試資料**：是否需要準備一組固定的短音檔/YouTube 連結作為測試基準？
- **覆蓋範圍**：除了現有的 External UI，是否也需覆蓋內部的監控面板？

## 🧩 Requirements

### TEST-01: API 自動化測試 (Backend)
- [x] **Auth 流程測試**：包含 JWT 登入、Token 刷新與 Google OAuth 模擬。
- [x] **任務 CRUD 測試**：建立任務、查詢狀態、取消任務的 API 完整性。
- [x] **下載端點測試**：驗證多格式（word, excel, txt）下載產出的正確性。

### TEST-02: Pipeline 整合測試 (Processing)
- [x] **YouTube 下載測試**：驗證 `yt-dlp` 下載特定短片的路徑與權限。
- [x] **GPU 排程測試**：模擬多任務併發時 `gpu_lock.py` 的序列化邏輯。
- [x] **轉錄與校對測試**：驗證 `faster-whisper` 與 `proofreading` 節點的資料流。

### TEST-03: Web UI E2E 測試 (Frontend)
- [x] **上傳工作流測試**：使用 Playwright 模擬檔案上傳並確認任務出現在列表中。
- [x] **狀態更新測試**：驗證 UI 是否正確輪詢並顯示 `running` 到 `done` 的轉變。
- [x] **歷史記錄操作測試**：模擬展開詳情並點擊各別格式的下載按鈕。

### TEST-04: 環境與基礎設施
- [x] **測試環境配置**：建立獨立的 `test_config.json` 與測試用資料庫（已在 Phase 07 完成）。
- [x] **自動化執行指令**：提供 `npm run test:e2e` 或 `pytest` 指令執行測試。

## 📝 Traceability

| ID | Requirement | Phase | Status |
|----|-------------|-------|--------|
| TEST-01 | API 自動化測試 | 07 | Completed |
| TEST-02 | Pipeline 整合測試 | 07 | Completed |
| TEST-03 | Web UI E2E 測試 | 08 | Completed |
| TEST-04 | 測試基礎設施 | 07 | Completed |
