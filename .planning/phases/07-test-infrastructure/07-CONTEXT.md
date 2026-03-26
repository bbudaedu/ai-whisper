# Context: Phase 07 - 測試基礎設施與 API/Pipeline 自動化

## 🎯 Phase Goal
建立一套穩定的自動化測試環境，確保 FaYin 後端 API、認證流程與語音處理管線在持續開發中維持正確性，並作為 v2.0 穩定性增強的基石。

## 🛠️ Decisions

### 1. 測試框架與執行 (Test Framework)
- **核心框架**：使用 `pytest` 作為主要執行器。
- **UI 整合**：採用 `pytest-playwright` 插件，方便在 Python 測試中調度瀏覽器。
- **執行指令**：實作 `npm run test:e2e` (前端整合) 與 `pytest tests/v2` (後端獨立)。

### 2. 環境與資料隔離 (Isolation)
- **資料庫**：測試期間強制使用 `sqlite:///:memory:`，確保不寫入實體 `.db` 檔案。
- **設定檔**：建立 `test_config.json`，關閉正式 Webhook、郵件通知與真實 LLM 呼叫。
- **背景任務**：在測試 `lifespan` 中提供開關，確保 `TaskScheduler` 不會因無限循環導致測試懸掛。

### 3. GPU 依賴與外部工具處理 (Stubbing/Mocking)
- **GPU 模擬**：
    - **Unit/API 測試**：使用 `unittest.mock` 攔截 `auto_youtube_whisper` 的執行。
    - **Smoke 測試**：配置 `whisper-model: tiny` 並在 CPU 上跑 5 秒極短音檔驗證端對端連通性。
- **下載工具**：攔截 `yt-dlp` 執行，改為讀取 `tests/fixtures/test_audio.wav`。

### 4. 驗證重點 (Verification Focus)
- **Auth**：確保 JWT Token 簽發、過期與 Role-based 權限正確（特別是內部/外部區隔）。
- **Pipeline**：驗證任務從 `pending` 轉換為 `running` 的資料更新邏輯與 `gpu_lock` 爭搶。
- **Download**：驗證 `zip` 封裝後的檔案結構與名稱對應（Word/Excel）。

## ⚠️ Risks & Mitigation
- **Flaky Tests**：網路下載與異步輪詢可能導致測試不穩定。*對策：在測試環境中使用固定 Local 檔案，不發送真實網路請求。*
- **Resource Leaks**：測試結束後背景進程未關閉。*對策：實作 pytest fixtures 的 teardown 邏輯強制清理。*

## 📅 Next Steps
1. 建立 `tests/v2` 目錄結構。
2. 實作 `test_config.json` 載入邏輯。
3. 撰寫第一組 API 整合測試 (Auth & Task CRUD)。
