# PLAN: Multi-Playlist GUI

## 1. Goal Description
實作 AI Whisper 的 "多播放清單 (Multi-Playlist)" 管理介面。
原先系統只有單一播放清單的設定，現需在 `web-ui` (React + Tailwind) 的 `SettingsPanel.tsx` 擴充為「播放清單管理列表 (Data-Dense Dashboard 樣式)」，並提供對應的 API 支持。

## 2. Design System & UX Guidelines (From ui-ux-pro-max)
- **Style:** Data-Dense Dashboard (Space-efficient, grid layout, KPI visibility)
- **Colors:**
  - Primary: `#3B82F6` (藍色 - 用於主要操作如啟動/儲存)
  - Secondary: `#60A5FA` (淺藍 - 次要提示)
  - CTA/Warning: `#F97316` (橘色 - 用於刪除、停用警告)
  - Background: `#F8FAFC` (極淺灰紫底色)
  - Text: `#1E293B` (深岩灰文字)
- **Typography:** `Fira Code` (數據/Monospace) & `Fira Sans` (UI 介面)
- **Key Effects:** Row highlighting on hover, smooth transitions (150-300ms), interactive hover tooltips.
- **Layout:** 一個 Comparison Table 或 Data Grid 顯示所有清單 (URL, 名稱, 狀態, 模型等)，右上角提供 "Add Playlist" 按鈕。

## 3. Agent Assignments (Orchestration Phase 2)
本計畫將動員以下 Agent 協同進行：
1. **frontend-specialist**: 負責修改 `web-ui/src/components/SettingsPanel.tsx`，實作 Grid Table 與 CRUD 視窗，並套用上述顏色與特效設定。
2. **backend-specialist**: 負責修改 `api_server.py` 與整合 `pipeline/playlist_manager.py`，開放 `GET/POST/PUT/DELETE /api/playlists` 等端點。
3. **test-engineer**: 驗證前後端 API 連線狀態、測試多清單在 `auto_youtube_whisper.py` 的實際運行狀況。

## 4. Proposed Changes

### Frontend (`web-ui`)
#### `src/components/SettingsPanel.tsx`
- 移除原本單一 `playlist_url` 的純文字輸入框。
- 引入一個 Data Table 顯示所有清單。包含：
  - 清單名稱 (Name)
  - URL (連結)
  - 目標模型 (Whisper Model)
  - 狀態 (Enabled/Disabled Switch)
  - 操作 (Edit, Delete)
- 新增一個 Modal Dialog 用於新增/編輯清單設定。

#### `index.html` 或 `index.css`
- 引入 `Fira Sans` 與 `Fira Code` 字體。

### Backend (`api_server.py` & `pipeline`)
#### `api_server.py`
- 新增 API routes `/api/playlists` 系列，對接並封裝 `playlist_manager.py`。
- 確保向後相容舊的 `config.json` 格式（如讀取舊單一 URL 並轉換為預設清單）。

#### `auto_youtube_whisper.py`
- 修改主迴圈，從抓取單一設定改為向 `PlaylistManager` 取出所有 enabled 清單並依序執行。

## 5. Verification Plan
### Automated & Manual Testing
1. **API 測試 (Manual/Script)**: 啟動 `api_server.py` 後，使用 curl 或瀏覽器呼叫 `/api/playlists` 確認資料正確回傳。
2. **UI 操作驗證 (Manual)**: 在 `5173` 前端頁面中，實際點擊「新增清單」、「修改狀態」、「刪除」，並確認變化有即時更新至後端 (及 `config.json` 或關聯 DB)。
3. **Pipeline 測試 (Automated)**: 觸發一輪 `whisper` 任務，觀察 `auto_youtube_whisper.log` 是否依序對兩個以上的啟用清單進行爬取。
4. **UX Audit**: 由 `frontend-specialist` 執行 `python .agent/skills/frontend-design/scripts/ux_audit.py web-ui` 確保 Tailwind 類別無誤並符合 Accessibility 標準。

## 6. User Review Required
- 請確認此 Table 佈局與字體 (Fira 家族) / 顏色策略是否符合您的期待？
- 關於任務調度，目前規劃是**當按下 Whisper 執行時，主迴圈會自動遍歷所有 Enabled 的清單**，同意此設計嗎？
