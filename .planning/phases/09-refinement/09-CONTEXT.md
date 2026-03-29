---
phase: 09
title: 說話者名稱編輯與真實 LLM 串接 (Refinement)
status: discussed
last_update: 2026-03-29T03:00:00Z
---

## 決策摘要

### 1. 資料庫與模型擴充 (DB-01)
- **變更**: 在 `Task` 模型 (`pipeline/queue/models.py`) 新增 `speaker_name: Optional[str] = Field(default=None, index=True)`。
- **遷移策略**: 由於目前 SQLite 檔案較小且處於開發階段，將優先使用手動 SQL 腳本執行 `ALTER TABLE tasks ADD COLUMN speaker_name TEXT;`。若後續需求複雜，再引入 Alembic。

### 2. API 介面優化 (API-01)
- **端點**: 在 `api/routers/tasks.py` 新增 `PATCH /api/tasks/{task_id}` 支援局部更新。
- **欄位**: 支援更新 `speaker_name` 以及其他潛在的 metadata。
- **權限**: 僅限 Internal 角色或任務擁有者（External）可編輯。

### 3. LLM 校對增強 (LLM-01)
- **串接**: 維持目前的 Google Gemini (via `ResilientAPIClient`)，但優化 `auto_proofread.py`。
- **Prompt 注入**: 在校對時將 `speaker_name` 作為 Context 傳給 LLM，以提升對特定人名的識別率。
- **穩定性**: 確認 `ResilientAPIClient` 的指數退避機制在並發情況下的表現。

### 4. Web UI 編輯功能 (UI-01)
- **位置**: 在 `web-ui-external/src/pages/TaskTracker.tsx` 的任務展開詳情（Expanded Row）中新增「說話者人名」編輯欄位。
- **交互**: 採用 **Inline Edit (onBlur 儲存)** 模式，並顯示儲存狀態（Loading/Success）。
- **圖示**: 使用 Lucide 的 `User` 或 `UserCog` 圖示標註。

## 待辦事項 (下一個階段)
1. 執行資料庫 ALTER 腳本。
2. 更新 `pipeline/queue/models.py` 與 `TaskResponse` schema。
3. 實作 API PATCH 端點。
4. 更新 `auto_proofread.py` 整合 `speaker_name`。
5. 實作 UI 編輯欄位與 API 連接。

## 預期產出
- 支援人名索引的資料庫表結構。
- 可遠端編輯任務資訊的 API。
- 整合講者資訊的 AI 校對品質提升。
- 更具管理價值的任務追蹤介面。
