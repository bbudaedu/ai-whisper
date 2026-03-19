# ROADMAP: NotebookLM 後製功能完善

## Phase 1: Fork & 擴充 MCP Server
**目標**：在 `notebooklm-mcp` 中新增筆記本管理與檔案上傳工具

### 1.1 Fork 設定
- [ ] Fork `notebooklm-mcp` 至本地 `/mnt/nas/workspaces/notebooklm-mcp`
- [ ] 確認 build 環境（npm install、npm run build）
- [ ] 更新 `ai-whisper/config.json` 指向本地 fork

### 1.2 探索 NotebookLM UI
- [ ] 用瀏覽器截圖記錄「建立筆記本」流程的 DOM 結構
- [ ] 記錄「上傳來源」按鈕與 file chooser 的 selector
- [ ] 記錄「刪除筆記本」的 UI 操作流程
- [ ] 記錄 Studio tab 各項原生工具的 selector

### 1.3 實作新工具
- [ ] `create_notebook` — 瀏覽器自動化建立新筆記本
- [ ] `upload_source` — 使用 Patchright file chooser API 上傳檔案
- [ ] `delete_notebook` — 刪除指定筆記本
- [ ] `list_sources` — 列出筆記本來源
- [ ] 更新 `definitions.ts` 與 `handlers.ts`
- [ ] 本地測試（手動呼叫各工具）

### 驗收標準
- 能透過 MCP JSON-RPC 成功建立筆記本、上傳 .docx、看到來源、刪除筆記本

---

## Phase 2: Python Pipeline 整合
**目標**：`ai-whisper` Python 層串接新的 MCP 工具

### 2.1 Client 更新
- [ ] `notebooklm_client.py` 新增 `create_notebook()`
- [ ] `notebooklm_client.py` 新增 `upload_source()`
- [ ] `notebooklm_client.py` 新增 `delete_notebook()`

### 2.2 Scheduler 更新
- [ ] 新增筆記本 metadata 追蹤（`notebooklm_notebooks.json`）
- [ ] 實作 LRU 筆記本清理邏輯
- [ ] 重寫 `process_next()` 流程：建立筆記本 → 上傳 → Studio 產出

### 2.3 Task 更新
- [ ] 更新 `OutputType` — 移除 prompt-based 類型，保留 Studio-native 類型
- [ ] 移除 `build_prompt()` 相關邏輯
- [ ] 新增 Studio output type 定義

### 驗收標準
- 能自動為一集完成：建立筆記本 → 上傳 .docx → 觸發 Studio 產出

---

## Phase 3: `auto_notebooklm.py` 主程式更新
**目標**：端對端自動化流程

### 3.1 掃描邏輯
- [ ] 新增 `.docx` 檔案定位（優先校對版 → 原始版）
- [ ] 更新 `scan_eligible_episodes()` 以偵測 `.docx` 來源

### 3.2 流程整合
- [ ] 整合筆記本建立 → 上傳 → Studio 產出的完整流程
- [ ] 配額管理：每日免費額度用完自動暫停
- [ ] 超過筆記本上限時 LRU 刪除

### 驗收標準
- 執行 `python3 auto_notebooklm.py` 可端對端完成整個流程
- 執行 `--status` 可顯示佇列、配額、筆記本數量

---

## Phase 4: 測試與驗證
- [ ] 單集手動測試（`--episode T097V017`）
- [ ] 多集批次測試
- [ ] 配額耗盡＋隔日恢復測試
- [ ] LRU 刪除測試
- [ ] 錯誤恢復測試（上傳失敗、網路中斷）
