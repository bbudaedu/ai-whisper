# Phase 3: 外部 Web UI 與提交流程 - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

外部使用者可在 mobile-first Web UI 登入、提交與追蹤任務，管理 YouTube 播放清單追蹤，並取得結果與完成通知。範圍包含外部 UI 的登入、提交、追蹤、下載與通知體驗；不包含校對增強（Phase 4）與長期保存（Phase 5）。

</domain>

<decisions>
## Implementation Decisions

### 導覽與版面結構
- **D-01:** 導覽採桌機左側 Sidebar + 行動版底部 Tab，主要區塊：Dashboard / 提交任務 / 任務追蹤 / 播放清單 / 設定
- **D-02:** 登入後預設進入 Dashboard 總覽
- **D-03:** 主要功能採分頁/分頁面呈現（非單頁長捲動），確保 mobile-first 可快速切換
- **D-04:** UI 風格沿用現有 web-ui 的卡片式圓角與淺色系，並保留 dark mode

### 登入與帳戶體驗
- **D-05:** 支援 Email/Password + Google OAuth 雙軌登入
- **D-06:** v1 不開放公開註冊；帳號由內部建立
- **D-07:** 登入狀態可跨重新整理維持，提供明確登出入口
- **D-08:** Email 通知收件人設定放在「設定」頁，任務完成即寄送

### 任務提交與參數設定
- **D-09:** 單一「新增任務」頁，提供 Upload / YouTube 兩種模式切換
- **D-10:** 任務參數包含音檔性質（會議/佛學課程）下拉 + Prompt 欄位（預設值可改）
- **D-11:** 輸出格式採多選勾選，預設全選 txt/srt/word/excel/json
- **D-12:** YouTube URL 單一欄位，自動偵測 playlist/單片並提示

### 播放清單追蹤與任務追蹤/下載
- **D-13:** 播放清單管理提供新增/啟用/停用/刪除，並顯示清單狀態與最新集數
- **D-14:** 任務追蹤以表格清單 + 狀態 badge/步驟呈現，支援展開查看細節
- **D-15:** 任務狀態更新採 10 秒輪詢 + 手動刷新
- **D-16:** 結果下載提供「下載全部(Zip)」主按鈕，並列出可下載格式清單（對應使用者勾選的輸出格式）

### Claude's Discretion
- Loading skeleton、空狀態插圖與文案
- 表單欄位的細節提示（helper text）
- 視覺間距、字級與 icon 分配
- 錯誤提示文案與顯示位置

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 3 需求與範圍
- `.planning/ROADMAP.md` §Phase 3 — 目標與 Success Criteria
- `.planning/REQUIREMENTS.md` §UI/PROC/NOTF — UI-01 ~ UI-07、PROC-01/02/06/07、NOTF-01/02
- `.planning/PROJECT.md` §Constraints / Key Decisions — mobile-first、同 repo、外部 UI 與內部 UI 分離、登入方式

### 既有 UI 參考
- `web-ui/src/App.tsx` — 既有 UI 版型（Sidebar + Header）與風格
- `web-ui/src/components/PlaylistTaskManager.tsx` — 播放清單管理、詳細列表與狀態呈現
- `web-ui/src/components/PlaylistDashboard.tsx` — Dashboard 卡片與 KPI 呈現
- `web-ui/src/components/TaskTracker.tsx` — 任務狀態表格與步驟呈現
- `web-ui/src/components/SettingsPanel.tsx` — 設定頁欄位與 Email 設定
- `web-ui/src/components/LogViewer.tsx` — SSE logs 呈現（樣式參考）
- `web-ui/src/types.ts` — 前端型別定義

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PlaylistTaskManager` / `PlaylistDashboard` / `TaskTracker`：現有清單卡片、表格與狀態視覺
- `SettingsPanel`：Email 與全域設定的表單結構
- `LogViewer`：SSE 串流日誌區塊樣式
- `NotebookLMStatsCard`：卡片化 KPI 呈現樣式

### Established Patterns
- React + TypeScript + axios；`API_BASE = http://{hostname}:8002/api`
- Tailwind utility classes + dark mode class 組合
- `lucide-react` icon 套件

### Integration Points
- 目前內部 UI 使用的 API：
  - `GET /api/status`, `GET /api/dashboard`
  - `GET/POST/PUT/DELETE /api/playlists`, `GET /api/playlists/{id}/episodes`, `POST /api/playlists/{id}/control`
  - `POST /api/task`
  - `GET/POST /api/config`, `GET /api/default-proofread-prompt`
  - `POST /api/url/detect`
  - `GET /api/stream/{logType}`
  - `GET /api/notebooklm/download`, `POST /api/notebooklm/trigger`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Auto mode selected recommended defaults for all decisions.

</specifics>

<deferred>
## Deferred Ideas

- 公開自助註冊 + Email 驗證（改以 v2 或後續 phase）
- WebSocket 即時推播（目前以輪詢滿足需求）
- 任務清單進階搜尋/篩選
- 播放清單完結自動停止追蹤（ENH-05）

</deferred>

---

*Phase: 03-web-ui*
*Context gathered: 2026-03-22*
