# Phase 5: 長期保存與歷史查詢 - Context

**Gathered:** 2026-03-22  
**Status:** Ready for planning

<domain>
## Phase Boundary

本階段負責為 FaYin 建立長期保存與歷史查詢能力，確保任務紀錄、原始音檔、轉錄結果與衍生成果可被永久保留，並讓內部與外部使用者在既有 API 與 Web UI 脈絡下持續查詢與下載。

本階段不重新設計轉錄、校對、播放清單監控或認證流程，而是在既有任務佇列、單 GPU 排程、外部 API 與外部 Web UI 基礎上，補齊持久化儲存、歷史列表、結果回溯與下載能力。
</domain>

<decisions>
## Implementation Decisions

### 儲存範圍
- **D-01:** 採取永久保留策略，任務紀錄、原始輸入音檔、轉錄輸出與衍生成果不主動清理或刪除。
- **D-02:** 長期保存的核心對象為「任務」而不是「單集 Notebook」，資料模型必須以 task/job 為主體。
- **D-03:** 必須同時覆蓋外部使用者提交的任務，以及既有內部工作流產生的任務，並維持內部優先的既有排程規則不變。

### 任務與檔案資料模型
- **D-04:** 必須保存 `task_id`、`owner/user_id`、`source_type`（upload / youtube / playlist-detected）、`audio_profile`（會議 / 佛學課程）、建立時間、完成時間、狀態、重試次數與錯誤訊息。
- **D-05:** 必須保存任務的輸入來源資訊，例如原始檔名、儲存路徑或物件鍵、YouTube URL、playlist subscription 關聯與觸發方式。
- **D-06:** 必須保存任務輸出成果資訊，包括可下載檔案清單、格式（txt / srt / vtt / tsv / json / word / excel）、檔案路徑或物件鍵、產生時間與可用狀態。
- **D-07:** 必須保存可供歷史查詢的流程事件，例如 pending、running、done、failed、cancelled 與各 stage 的時間點，供 UI 與 API 顯示歷程。

### 查詢與下載介面
- **D-08:** Phase 5 的主要使用面為既有 FastAPI 與外部 Web UI 的歷史查詢與下載能力，不以 CLI 作為主要交付介面。
- **D-09:** 外部使用者只能查詢與下載自己擁有或被授權的任務與檔案；內部使用者則依既有管理權限查看。
- **D-10:** 歷史任務必須可依任務狀態、建立時間、來源類型與關鍵字查詢，至少支援列表、詳情與結果下載三種基本操作。

### 儲存實作
- **D-11:** 關聯式中繼資料可使用 SQLite 作為 v1 落地方案，但 schema 必須圍繞 FaYin task 與 artifact 設計，而非 episode/notebook 結構。
- **D-12:** 檔案保存層需與資料庫中繼資料明確對應，避免只有紀錄沒有實體檔案，或有檔案但無法追蹤來源與擁有者。
- **D-13:** 若沿用 SQLite，需考慮併發寫入時的 timeout、transaction 邊界與單寫入序列化策略，以降低 database locked 風險。

### Claude's Discretion
- SQLite schema 的具體表結構與索引設計，例如 `tasks`、`task_artifacts`、`task_events`、`playlist_subscriptions` 是否拆表。
- 長期保存檔案的實體路徑規劃，例如 `data/tasks/`、`storage/raw/`、`storage/artifacts/`。
- 歷史列表與詳情 API 的分頁、排序與篩選參數。
- 外部 Web UI 歷史頁面的資訊密度與下載入口呈現方式。
</decisions>

<specifics>
## Specific Ideas

- 歷史列表應優先顯示任務名稱或來源、提交者、建立時間、最新狀態、輸出格式與最近一次錯誤摘要。
- 任務詳情頁可顯示 stage timeline，讓使用者看見下載、轉錄、校對、格式化與通知等節點。
- 對播放清單自動偵測產生的任務，應保留其來自哪一個 subscription 與哪一支影片，避免歷史紀錄失去來源脈絡。
- 對講義/文本輔助校對任務，應保存當次使用了哪些附件或可重用參考資料，方便日後重跑或比對品質。
</specifics>

<canonical_refs>
## Canonical References

### 需求來源
- `.gsd/PROJECT.md` — Active scope 明確列出「音檔與輸出成果永久保留」與「任務紀錄永久保存」。
- `.gsd/ROADMAP.md` — 明列 **Phase 5: 長期保存與歷史查詢**，成功標準包含歷史任務持續可查與任意時間下載先前成果與原始音檔。

### 前置成果
- `.gsd/ROADMAP.md` Phase 1 — 已建立任務佇列與單 GPU 排程，為長期保存的任務主體提供基礎。
- `.gsd/PROJECT.md` 與 `.gsd/ROADMAP.md` Phase 2 / 02.1 / 3 — 已有對外 API、登入認證與外部 Web UI，可作為歷史查詢與下載能力的承接介面。
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- FastAPI 後端已具備任務建立、查詢、取消與結果下載脈絡，Phase 5 應優先擴充既有 task/result 相關資料層與查詢介面。
- 既有任務佇列與 stage fan-out 流程已存在，適合在任務生命週期各節點補寫持久化事件與 artifact metadata。
- 外部 Web UI 已具備登入、提交、追蹤與通知流程，適合新增「歷史任務列表 / 任務詳情 / 檔案下載」頁面與 API client。

### Integration Points
- 任務建立時：寫入 `tasks` 初始紀錄與輸入來源 metadata。
- 各 stage 狀態變化時：追加 `task_events` 或更新狀態欄位。
- 結果產出時：寫入 `task_artifacts` 並綁定可下載格式。
- 使用者查詢歷史時：由 FastAPI 提供列表、詳情、下載授權與檔案串流。
</code_context>

<deferred>
## Deferred Ideas

- 全文檢索與進階搜尋條件。
- 管理員跨使用者統計報表。
- 分層儲存、冷資料歸檔與未來可能的保留政策調整。
- 額外的 CLI 匯出或靜態報表功能，可作為內部維運輔助，但不列為本階段主要交付。
</deferred>

---

*Phase: 05-long-term-retention-and-history*  
*Context gathered: 2026-03-22*
