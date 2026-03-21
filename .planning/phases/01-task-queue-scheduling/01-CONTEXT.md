# Phase 1: 任務佇列與排程基礎 - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

使用者提交的任務可被佇列化與分段處理，在單 GPU 與內部優先權下穩定執行且不破壞既有內部流程。本階段交付：可持久化任務佇列、單 GPU 排程器、stage 解耦的 pipeline 架構、失敗重試機制。不包含對外 API、認證、Web UI（Phase 2-3 範圍）。

</domain>

<decisions>
## Implementation Decisions

### 佇列持久化策略
- 使用 SQLite 作為任務佇列的持久化層，零外部依賴，適合單機環境
- 使用輕量 ORM（SQLModel）管理資料模型，與 FastAPI + Pydantic 自然整合
- 任務狀態模型：`queued → pending → running → done / failed / canceled`（預留 Phase 2 API 取消）
- 現有 `processed_videos.json` 採漸進遷移：雙寫 JSON + SQLite 一段時間，穩定後停寫 JSON
- 任務識別：DB 主鍵採 UUID，保留既有影片 ID/清單資訊作為外部欄位
- SQLite 存放位置：`/mnt/nas/`

### 排程與優先權機制
- 佇列分級：內部佇列先清空再處理外部佇列，實現內部任務優先
- 排程觸發方式：Polling loop（固定間隔檢查佇列），沿用現有 `auto_youtube_whisper.py` 的 loop 模式
- 保留現有 `gpu_lock.py` 的 `fcntl.flock` 機制，排程器取得佇列鎖後再嘗試 GPU lock
- 排程器以 FastAPI 背景任務（asyncio task）運行，整合至現有 API server

### Pipeline Stage 並行策略
- 每個 stage 是獨立任務，完成後自動排入下一 stage（下載→聽打→校對→排版）
- 父任務 + 子任務模型：播放清單任務為父，每集為子任務，便於查詢整體進度
- 並行限制：全部 stage 僅允許 1 個任務同時執行（下載也不例外）
- 父任務狀態彙總：全部子任務完成才標記 done
- Stage 失敗處理：失敗即停止後續 stage，只重試該 stage
- 現有 `auto_youtube_whisper.py` 核心邏輯抽取為 pipeline 模組，原腳本保留作為 CLI 入口

### 失敗與重試行為
- 固定 3 次指數退避重試
- 僅重試失敗的 stage，不重新執行已完成的 stage
- 任務記錄重試次數（`retry_count`）與最後錯誤訊息（`error_message`），狀態為 `failed` 時帶錯誤資訊

### Claude's Discretion
- SQLite 資料表結構的具體設計（欄位命名、索引策略）
- Polling 間隔的具體秒數
- 指數退避的具體參數（base delay、max delay）
- 日誌格式與 structured logging 的具體方案
- 單元測試的具體框架選擇（pytest vs unittest）
- Pipeline 模組的檔案組織結構

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 核心現有模組
- `gpu_lock.py` — GPU 獨佔鎖機制，使用 `fcntl.flock`，任何涉及 GPU 的排程必須遵循此模式
- `auto_youtube_whisper.py` — 現有主流程，包含下載→轉錄→校對→報表完整 pipeline，需抽取核心邏輯
- `auto_proofread.py` — 校對 stage 實作，使用 Gemini API
- `auto_postprocess.py` — 後處理 stage 實作，產生 Excel/Word 報表

### API 與設定
- `api_server.py` — 現有 FastAPI server，排程器將整合於此
- `config.json` — 播放清單與系統設定
- `processed_videos.json` — 影片處理狀態追蹤，需漸進遷移

### Pipeline 模組
- `pipeline/playlist_manager.py` — 播放清單管理，可重用
- `pipeline/notebooklm_tasks.py` — NotebookLM 排程器，可作為新排程器的參考模式

### 專案規格
- `.planning/PROJECT.md` — 專案約束（單 GPU、內部優先、不破壞現有功能）
- `.planning/REQUIREMENTS.md` §QUEUE — QUEUE-01 至 QUEUE-05 需求定義

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gpu_lock.py`：GPU 獨佔鎖，`acquire_gpu_lock()` / `is_gpu_busy()` — 排程器直接調用
- `PlaylistManager`（`pipeline/playlist_manager.py`）：播放清單 CRUD — 父任務建立時可調用
- `NotebookLMScheduler`：佇列 JSON 持久化模式 — 可作為 SQLite 遷移的參考
- `threading.Semaphore`（`auto_youtube_whisper.py`）：`gpu_semaphore`、`dl_semaphore` — 沿用並行限制邏輯

### Established Patterns
- 狀態追蹤：`processed_videos.json` 以 JSON 檔案記錄每集處理進度，需遷移至 SQLite 但保持 fallback
- API 啟動任務：`api_server.py` 透過 `subprocess.Popen` 啟動處理腳本 — 新排程器應改為直接呼叫 Python 函式
- 命名慣例：Python 端使用 `snake_case`，FastAPI + Pydantic 為主
- 設定管理：`config.json` 集中管理，`PlaylistManager` 統一讀寫

### Integration Points
- `/api/task` 路由：現有任務觸發入口，需擴展為佇列式提交
- `api_server.py` startup event：排程器背景任務的掛載點
- `processed_videos.json`：雙軌遷移期間需同時讀寫
- NAS 儲存路徑（`/mnt/nas/`）：pipeline 輸出目的地，stage 間的檔案傳遞路徑

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Auto mode selected recommended defaults for all decisions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. All queue/scheduling decisions are scoped to Phase 1 requirements (QUEUE-01 through QUEUE-05).

</deferred>

---

*Phase: 01-task-queue-scheduling*
*Context gathered: 2026-03-21*
